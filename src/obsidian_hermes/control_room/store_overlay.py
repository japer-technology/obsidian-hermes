"""Read-only SQLite adapter for volatile queue and run coordination state."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .ports import JsonObject, StoreOverlay

_TERMINAL_STATES = (
    "completed",
    "blocked",
    "failed",
    "cancelled",
    "dead_letter",
    "superseded",
)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _overlay_source(note_path: str | None) -> JsonObject:
    return {
        "kind": "sqlite-overlay",
        "canonical_note_path": note_path,
        "durable": False,
        "specification_hash": None,
    }


def _json_value(value: Any, fallback: Any) -> Any:
    if not isinstance(value, str):
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


class SqliteStoreOverlayReader:
    """Project bounded coordination state from a read-only database handle.

    SQLite rows are labelled as an ephemeral overlay.  They can enrich a
    canonical Markdown record, but are never presented as durable task or
    routine truth.
    """

    def __init__(self, database_path: Path, *, default_runtime_id: str = "unresolved") -> None:
        self._database_path = database_path
        self._default_runtime_id = default_runtime_id

    def _connect(self) -> sqlite3.Connection:
        resolved = self._database_path.resolve(strict=True)
        connection = sqlite3.connect(
            f"{resolved.as_uri()}?mode=ro",
            uri=True,
            isolation_level=None,
            check_same_thread=True,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA busy_timeout = 1000")
        return connection

    def read_store_overlay(self, *, limit: int) -> StoreOverlay:
        if limit < 1:
            raise ValueError("limit must be positive")
        observed_at = _now()
        try:
            connection = self._connect()
        except (OSError, sqlite3.Error):
            return StoreOverlay(
                observed_at=observed_at,
                warnings=(
                    {
                        "code": "store_unavailable",
                        "message": "coordination store is unavailable",
                        "path": None,
                    },
                ),
            )

        try:
            queue_rows = connection.execute(
                """
                SELECT c.command_id, c.task_id, c.task_generation, c.state,
                       c.priority, c.not_before, c.attempt, c.max_attempts,
                       c.updated_at, r.vault_path AS task_note_path
                FROM commands AS c
                LEFT JOIN resources AS r
                  ON r.schema_name = c.task_schema
                 AND r.resource_id = c.task_id
                 AND r.generation = c.task_generation
                WHERE c.state NOT IN (?, ?, ?, ?, ?, ?)
                ORDER BY c.priority DESC, c.created_at, c.command_id
                LIMIT ?
                """,
                (*_TERMINAL_STATES, limit + 1),
            ).fetchall()
            run_rows = connection.execute(
                """
                SELECT x.run_id, x.command_id, x.task_id, x.trace_id, x.state,
                       x.agent_profile, x.model_provider, x.model_name,
                       x.input_tokens, x.output_tokens, x.network_requests,
                       x.created_at, x.started_at, x.finished_at,
                       r.vault_path AS task_note_path
                FROM runs AS x
                LEFT JOIN resources AS r
                  ON r.schema_name = 'hermes.task/v2'
                 AND r.resource_id = x.task_id
                 AND r.generation = x.task_generation
                ORDER BY x.created_at DESC, x.run_id DESC
                LIMIT ?
                """,
                (limit + 1,),
            ).fetchall()
            approval_rows = connection.execute(
                """
                SELECT a.approval_id, a.trace_id, a.action_class, a.risk_tier,
                       a.decision, a.subject_json, a.requested_at, a.expires_at,
                       a.task_id, a.run_id, a.routine_id,
                       task.vault_path AS task_note_path,
                       routine.vault_path AS routine_note_path
                FROM approvals AS a
                LEFT JOIN resources AS task
                  ON task.schema_name = 'hermes.task/v2'
                 AND task.resource_id = a.task_id
                 AND task.generation = a.task_generation
                LEFT JOIN resources AS routine
                  ON routine.schema_name = 'hermes.routine/v2'
                 AND routine.resource_id = a.routine_id
                 AND routine.revision = a.routine_revision
                 AND routine.is_current = 1
                ORDER BY (a.decision = 'pending') DESC, a.requested_at, a.approval_id
                LIMIT ?
                """,
                (limit + 1,),
            ).fetchall()
            event_rows = connection.execute(
                """
                SELECT e.event_id, e.occurred_at, e.type, e.outcome, e.actor,
                       e.trace_id, e.task_id, e.run_id, e.data,
                       r.vault_path AS task_note_path
                FROM events AS e
                LEFT JOIN resources AS r
                  ON r.schema_name = e.task_schema
                 AND r.resource_id = e.task_id
                 AND r.generation = e.task_generation
                ORDER BY e.occurred_at DESC, e.event_id DESC
                LIMIT ?
                """,
                (limit + 1,),
            ).fetchall()
        except sqlite3.Error:
            return StoreOverlay(
                observed_at=observed_at,
                warnings=(
                    {
                        "code": "store_schema_unavailable",
                        "message": "coordination store schema is unavailable",
                        "path": None,
                    },
                ),
            )
        finally:
            connection.close()

        truncated = any(
            len(rows) > limit for rows in (queue_rows, run_rows, approval_rows, event_rows)
        )
        queue: list[JsonObject] = []
        for row in queue_rows[:limit]:
            note_path = row["task_note_path"]
            queue.append(
                {
                    "command_id": row["command_id"],
                    "task_id": row["task_id"],
                    "runtime_id": self._default_runtime_id,
                    "state": row["state"],
                    "priority": row["priority"],
                    "not_before": row["not_before"],
                    "attempt": row["attempt"],
                    "max_attempts": row["max_attempts"],
                    "updated_at": row["updated_at"],
                    "canonical_note_path": note_path,
                    "source_of_truth": _overlay_source(note_path),
                    "field_sources": {
                        "state": "sqlite-overlay",
                        "attempt": "sqlite-overlay",
                        "not_before": "sqlite-overlay",
                        "priority": "markdown-validated-overlay",
                    },
                }
            )

        runs: list[JsonObject] = []
        for row in run_rows[:limit]:
            note_path = row["task_note_path"]
            runs.append(
                {
                    "run_id": row["run_id"],
                    "runtime_id": self._default_runtime_id,
                    "task_id": row["task_id"],
                    "command_id": row["command_id"],
                    "trace_id": row["trace_id"],
                    "state": row["state"],
                    "model": {
                        "provider": row["model_provider"],
                        "name": row["model_name"],
                        "source": "resolved-overlay",
                    },
                    "usage": {
                        "input_tokens": row["input_tokens"],
                        "output_tokens": row["output_tokens"],
                        "network_requests": row["network_requests"],
                    },
                    "cost": {
                        "estimated_usd": None,
                        "actual_usd": None,
                        "status": "unavailable",
                    },
                    "created_at": row["created_at"],
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                    "canonical_note_path": None,
                    "related_task_note_path": note_path,
                    "projection": {
                        "status": "missing",
                        "canonical_note_path": None,
                        "observed_at": observed_at,
                    },
                    "source_of_truth": _overlay_source(None),
                    "field_sources": {
                        "state": "sqlite-overlay",
                        "usage": "sqlite-overlay",
                        "model": "resolved-overlay",
                    },
                }
            )

        approvals: list[JsonObject] = []
        for row in approval_rows[:limit]:
            note_path = row["task_note_path"] or row["routine_note_path"]
            approvals.append(
                {
                    "approval_id": row["approval_id"],
                    "runtime_id": self._default_runtime_id,
                    "trace_id": row["trace_id"],
                    "action_class": row["action_class"],
                    "risk_tier": row["risk_tier"],
                    "decision": row["decision"],
                    "subject": _json_value(row["subject_json"], {}),
                    "requested_at": row["requested_at"],
                    "expires_at": row["expires_at"],
                    "canonical_note_path": None,
                    "related_note_path": note_path,
                    "projection": {
                        "status": "missing",
                        "canonical_note_path": None,
                        "observed_at": observed_at,
                    },
                    "source_of_truth": _overlay_source(None),
                    "field_sources": {"decision": "sqlite-overlay"},
                }
            )

        activity: list[JsonObject] = []
        for row in event_rows[:limit]:
            data = _json_value(row["data"], {})
            commit = data.get("commit") if isinstance(data, dict) else None
            summary = data.get("summary") if isinstance(data, dict) else None
            activity.append(
                {
                    "event_id": row["event_id"],
                    "runtime_id": self._default_runtime_id,
                    "occurred_at": row["occurred_at"],
                    "type": row["type"],
                    "outcome": row["outcome"],
                    "actor": row["actor"],
                    "trace_id": row["trace_id"],
                    "task_id": row["task_id"],
                    "run_id": row["run_id"],
                    "commit": commit if isinstance(commit, str) else None,
                    "summary": summary if isinstance(summary, str) else None,
                    "canonical_note_path": None,
                    "related_note_path": row["task_note_path"],
                    "projection": {
                        "status": "missing",
                        "canonical_note_path": None,
                        "observed_at": observed_at,
                    },
                    "source_of_truth": _overlay_source(None),
                    "field_sources": {
                        "occurred_at": "sqlite-overlay",
                        "type": "sqlite-overlay",
                        "outcome": "sqlite-overlay",
                    },
                }
            )

        return StoreOverlay(
            queue=tuple(queue),
            runs=tuple(runs),
            approvals=tuple(approvals),
            activity=tuple(activity),
            observed_at=observed_at,
            truncated=truncated,
        )
