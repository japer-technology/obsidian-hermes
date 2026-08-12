"""Bounded filesystem adapter for canonical Markdown control-room state."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from obsidian_hermes.domain.errors import FrontmatterError, ResourceValidationError
from obsidian_hermes.resources.loader import ResourceDocument, load_resource

from .ports import JsonObject, VaultState

_CONTROL_ROOM_SCHEMAS = frozenset(
    {
        "hermes.task/v2",
        "hermes.routine/v2",
        "hermes.run/v2",
        "hermes.approval/v2",
        "hermes.event/v2",
    }
)
_CANDIDATE_SCAN_BYTES = 65_536
_SCHEMA_DISCRIMINATOR = re.compile(
    rb"^schema:[ \t]*(hermes\.(?:task|routine|run|approval|event)/v2)[ \t]*\r?\n?$"
)


def _source(note_path: str, specification_hash: str | None) -> JsonObject:
    return {
        "kind": "markdown",
        "canonical_note_path": note_path,
        "durable": True,
        "specification_hash": specification_hash,
    }


def _field_sources(*names: str) -> JsonObject:
    return {name: "markdown" for name in names}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _is_control_room_candidate(path: Path) -> bool:
    """Recognise only an exact supported discriminator in bounded frontmatter.

    This check never accepts a resource; it only decides whether the strict
    parser and schema validator should inspect it. Ordinary Obsidian YAML is
    therefore invisible to the API, including YAML conventions outside the v2
    resource profile.
    """

    consumed = 0
    with path.open("rb") as resource_file:
        first = resource_file.readline()
        consumed += len(first)
        if first not in {b"---\n", b"---\r\n"}:
            return False
        for line in resource_file:
            consumed += len(line)
            if consumed > _CANDIDATE_SCAN_BYTES:
                return False
            if line in {b"---\n", b"---\r\n", b"---"}:
                return False
            if _SCHEMA_DISCRIMINATOR.fullmatch(line) is not None:
                return True
    return False


def _task(document: ResourceDocument, note_path: str, runtime_id: str) -> JsonObject:
    data = document.metadata
    observed = _mapping(data.get("observed"))
    return {
        "task_id": data["id"],
        "runtime_id": runtime_id,
        "title": data["title"],
        "desired_state": data["desired_state"],
        "observed_state": observed.get("state"),
        "priority": data["priority"],
        "operation": data["operation"],
        "agent_profile": data["agent_profile"],
        "model_selection": {
            "provider": None,
            "model": None,
            "depth": None,
            "source": "runtime_resolution",
        },
        "budget": dict(_mapping(data.get("budgets"))),
        "queue": None,
        "canonical_note_path": note_path,
        "source_of_truth": _source(note_path, document.spec_hash),
        "field_sources": _field_sources(
            "title",
            "desired_state",
            "priority",
            "operation",
            "agent_profile",
            "budget",
        ),
    }


def _routine(document: ResourceDocument, note_path: str, runtime_id: str) -> JsonObject:
    data = document.metadata
    schedule = _mapping(data.get("schedule"))
    execution = _mapping(data.get("execution"))
    observed = _mapping(data.get("observed"))
    return {
        "routine_id": data["id"],
        "runtime_id": runtime_id,
        "name": data["name"],
        "desired_state": data["desired_state"],
        "observed_state": observed.get("state"),
        "schedule": {
            "expression": schedule.get("expression"),
            "timezone": schedule.get("timezone"),
            "next_run_at": None,
        },
        "model_selection": {
            "provider": execution.get("provider"),
            "model": execution.get("model"),
            "depth": None,
            "source": "routine",
        },
        "last_run": None,
        "canonical_note_path": note_path,
        "source_of_truth": _source(note_path, document.spec_hash),
        "field_sources": _field_sources(
            "name", "desired_state", "schedule", "model_selection"
        ),
    }


def _run(document: ResourceDocument, note_path: str, runtime_id: str) -> JsonObject:
    data = document.metadata
    usage = dict(_mapping(data.get("usage")))
    return {
        "run_id": data["id"],
        "runtime_id": runtime_id,
        "task_id": data["task_id"],
        "command_id": data["command_id"],
        "trace_id": data["trace_id"],
        "state": data["state"],
        "model": dict(_mapping(data.get("model"))),
        "usage": usage,
        "cost": {
            "estimated_usd": None,
            "actual_usd": None,
            "status": "unavailable",
        },
        "created_at": data["created_at"],
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
        "canonical_note_path": note_path,
        "source_of_truth": _source(note_path, document.spec_hash),
        "field_sources": _field_sources(
            "task_id", "state", "model", "usage", "created_at", "started_at", "finished_at"
        ),
    }


def _approval(document: ResourceDocument, note_path: str, runtime_id: str) -> JsonObject:
    data = document.metadata
    subject = _mapping(data.get("subject"))
    return {
        "approval_id": data["id"],
        "runtime_id": runtime_id,
        "trace_id": data["trace_id"],
        "action_class": data["action_class"],
        "risk_tier": data["risk_tier"],
        "decision": data["decision"],
        "subject": dict(subject),
        "requested_at": data["requested_at"],
        "expires_at": data["expires_at"],
        "canonical_note_path": note_path,
        "source_of_truth": _source(note_path, document.spec_hash),
        "field_sources": _field_sources(
            "action_class", "risk_tier", "decision", "subject", "requested_at", "expires_at"
        ),
    }


def _activity(document: ResourceDocument, note_path: str, runtime_id: str) -> JsonObject:
    data = document.metadata
    event_data = _mapping(data.get("data"))
    commit = event_data.get("commit")
    summary = event_data.get("summary")
    return {
        "event_id": data["event_id"],
        "runtime_id": runtime_id,
        "occurred_at": data["occurred_at"],
        "type": data["type"],
        "outcome": data["outcome"],
        "actor": data["actor"],
        "trace_id": data["trace_id"],
        "task_id": data.get("task_id"),
        "run_id": data.get("run_id"),
        "commit": commit if isinstance(commit, str) else None,
        "summary": summary if isinstance(summary, str) else None,
        "canonical_note_path": note_path,
        "source_of_truth": _source(note_path, document.spec_hash),
        "field_sources": _field_sources(
            "occurred_at", "type", "outcome", "actor", "trace_id", "commit", "summary"
        ),
    }


class FilesystemVaultStateReader:
    """Read validated Markdown resources without following symlinked files."""

    def __init__(
        self,
        vault_roots: Mapping[str, Path],
        *,
        runtime_by_agent_profile: Mapping[str, str] | None = None,
        max_resource_bytes: int = 1_048_576,
        max_scanned_entries: int = 20_000,
    ) -> None:
        if max_resource_bytes < 1:
            raise ValueError("max_resource_bytes must be positive")
        if max_scanned_entries < 1:
            raise ValueError("max_scanned_entries must be positive")
        roots = dict(vault_roots)
        if not roots:
            raise ValueError("at least one labelled vault root is required")
        for label, root in roots.items():
            if (
                not label
                or "/" in label
                or "\\" in label
                or label.casefold() == "private"
                or not isinstance(root, Path)
            ):
                raise ValueError("vault roots require safe, non-Private labels and Path values")
        self._vault_roots = MappingProxyType(roots)
        mapping = dict(runtime_by_agent_profile or {})
        if any(not profile or not runtime_id for profile, runtime_id in mapping.items()):
            raise ValueError("runtime profile mappings must contain non-empty strings")
        self._runtime_by_agent_profile = MappingProxyType(mapping)
        self._max_resource_bytes = max_resource_bytes
        self._max_scanned_entries = max_scanned_entries

    def _runtime_for_profile(self, profile: Any) -> str:
        if not isinstance(profile, str):
            return "unresolved"
        return self._runtime_by_agent_profile.get(profile, "unresolved")

    def _markdown_paths(self) -> tuple[list[tuple[Path, str]], bool, list[JsonObject]]:
        """Enumerate without following symlinks or materialising an unbounded tree."""

        paths: list[tuple[Path, str]] = []
        warnings: list[JsonObject] = []
        scanned = 0
        truncated = False
        for label, configured_root in sorted(self._vault_roots.items()):
            if not configured_root.is_dir() or configured_root.is_symlink():
                if len(warnings) < 50:
                    warnings.append(
                        {
                            "code": "vault_zone_unavailable",
                            "message": "canonical Markdown vault zone is unavailable",
                            "path": label,
                        }
                    )
                continue
            try:
                root = configured_root.resolve(strict=True)
            except OSError:
                if len(warnings) < 50:
                    warnings.append(
                        {
                            "code": "vault_zone_unavailable",
                            "message": "canonical Markdown vault zone cannot be resolved safely",
                            "path": label,
                        }
                    )
                continue
            stack = [root]
            while stack:
                directory = stack.pop()
                try:
                    entries = os.scandir(directory)
                except OSError:
                    if len(warnings) < 50:
                        warnings.append(
                            {
                                "code": "directory_unavailable",
                                "message": "vault directory cannot be read safely",
                                "path": label,
                            }
                        )
                    continue
                with entries:
                    for entry in entries:
                        scanned += 1
                        if scanned > self._max_scanned_entries:
                            truncated = True
                            stack.clear()
                            break
                        try:
                            if entry.is_symlink():
                                continue
                            path = Path(entry.path)
                            resolved = path.resolve(strict=True)
                            if not resolved.is_relative_to(root):
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(resolved)
                            elif (
                                entry.is_file(follow_symlinks=False)
                                and path.suffix.casefold() == ".md"
                            ):
                                relative = resolved.relative_to(root).as_posix()
                                paths.append((resolved, f"{label}/{relative}"))
                        except OSError:
                            if len(warnings) < 50:
                                warnings.append(
                                    {
                                        "code": "entry_unavailable",
                                        "message": "vault entry cannot be resolved safely",
                                        "path": label,
                                    }
                                )
            if truncated:
                break
        return paths, truncated, warnings

    def read_vault_state(self, *, limit: int) -> VaultState:
        if limit < 1:
            raise ValueError("limit must be positive")
        tasks: list[JsonObject] = []
        routines: list[JsonObject] = []
        runs: list[JsonObject] = []
        approvals: list[JsonObject] = []
        activity: list[JsonObject] = []
        paths, truncated, warnings = self._markdown_paths()

        documents: list[tuple[ResourceDocument, str]] = []

        # The list is capped by max_scanned_entries before sorting, so stable
        # selection cannot become an unbounded filesystem amplification.
        for path, note_path in sorted(paths, key=lambda item: item[1]):
            if len(documents) >= limit:
                truncated = True
                break
            try:
                if path.is_symlink():
                    raise OSError("symlinked resources are not read by the control-room API")
                if path.stat().st_size > self._max_resource_bytes:
                    raise OSError("resource exceeds the configured size limit")
                if not _is_control_room_candidate(path):
                    continue
                document = load_resource(path)
            except (OSError, FrontmatterError, ResourceValidationError) as error:
                if len(warnings) < 50:
                    warnings.append(
                        {
                            "code": "resource_unavailable",
                            "message": str(error)[:240],
                            "path": note_path,
                        }
                    )
                continue

            schema = document.metadata.get("schema")
            if schema not in _CONTROL_ROOM_SCHEMAS:
                continue
            documents.append((document, note_path))

        task_runtime: dict[str, str] = {}
        run_runtime: dict[str, str] = {}
        for document, _ in documents:
            data = document.metadata
            schema = data["schema"]
            if schema == "hermes.task/v2":
                task_runtime[str(data["id"])] = self._runtime_for_profile(data["agent_profile"])
            elif schema == "hermes.run/v2":
                runtime_id = self._runtime_for_profile(data["agent_profile"])
                run_runtime[str(data["id"])] = runtime_id
                task_runtime.setdefault(str(data["task_id"]), runtime_id)

        for document, note_path in documents:
            data = document.metadata
            schema = data["schema"]
            if schema == "hermes.task/v2":
                runtime_id = task_runtime[str(data["id"])]
                tasks.append(_task(document, note_path, runtime_id))
            elif schema == "hermes.routine/v2":
                execution = _mapping(data.get("execution"))
                runtime_id = self._runtime_for_profile(execution.get("agent_profile"))
                routines.append(_routine(document, note_path, runtime_id))
            elif schema == "hermes.run/v2":
                runtime_id = run_runtime[str(data["id"])]
                runs.append(_run(document, note_path, runtime_id))
            elif schema == "hermes.approval/v2":
                subject = _mapping(data.get("subject"))
                runtime_id = run_runtime.get(str(subject.get("run_id")))
                if runtime_id is None:
                    runtime_id = task_runtime.get(str(subject.get("task_id")), "unresolved")
                approvals.append(_approval(document, note_path, runtime_id))
            elif schema == "hermes.event/v2":
                runtime_id = run_runtime.get(str(data.get("run_id")))
                if runtime_id is None:
                    runtime_id = task_runtime.get(str(data.get("task_id")), "unresolved")
                activity.append(_activity(document, note_path, runtime_id))

        # Keep deterministic ordering even when filesystem traversal differs.
        tasks.sort(key=lambda item: (-int(item["priority"]), str(item["task_id"])))
        routines.sort(key=lambda item: str(item["routine_id"]))
        runs.sort(key=lambda item: (str(item["created_at"]), str(item["run_id"])), reverse=True)
        approvals.sort(key=lambda item: (str(item["requested_at"]), str(item["approval_id"])))
        activity.sort(
            key=lambda item: (str(item["occurred_at"]), str(item["event_id"])), reverse=True
        )
        return VaultState(
            tasks=tuple(tasks),
            routines=tuple(routines),
            runs=tuple(runs),
            approvals=tuple(approvals),
            activity=tuple(activity),
            warnings=tuple(warnings),
            truncated=truncated,
        )
