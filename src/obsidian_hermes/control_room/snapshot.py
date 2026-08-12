"""Compose the versioned, Markdown-first control-room snapshot."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from .ports import (
    JsonObject,
    RepositoryProvenanceReader,
    RuntimeCatalogPort,
    StoreOverlay,
    StoreOverlayReader,
    VaultState,
    VaultStateReader,
)

SNAPSHOT_SCHEMA = "obsidian-hermes.control-room-snapshot/v1"
HEALTH_SCHEMA = "obsidian-hermes.control-room-health/v1"


@dataclass(frozen=True, slots=True)
class SnapshotLimits:
    """Hard bounds applied before an API response is serialized."""

    max_items_per_collection: int = 250
    max_response_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if not 1 <= self.max_items_per_collection <= 2_000:
            raise ValueError("max_items_per_collection must be between 1 and 2000")
        if not 4_096 <= self.max_response_bytes <= 8_388_608:
            raise ValueError("max_response_bytes must be between 4096 and 8388608")


def _iso_now(clock: Callable[[], datetime]) -> str:
    value = clock()
    if value.tzinfo is None:
        raise ValueError("snapshot clock must return a timezone-aware datetime")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _unavailable_repository() -> JsonObject:
    return {
        "available": False,
        "role": "historical_shared_memory",
        "head": None,
        "ref": None,
        "dirty": None,
        "ahead": None,
        "behind": None,
        "upstream_status": "unavailable",
        "last_commit": None,
        "observed_at": None,
    }


def _merge_overlay_records(
    canonical: Iterable[JsonObject],
    overlay: Iterable[JsonObject],
    *,
    identifier: str,
    volatile_fields: tuple[str, ...],
) -> list[JsonObject]:
    merged: dict[str, JsonObject] = {
        str(record[identifier]): dict(record) for record in canonical
    }
    for overlay_record in overlay:
        key = str(overlay_record[identifier])
        if key not in merged:
            merged[key] = dict(overlay_record)
            continue
        record = merged[key]
        sources = dict(record.get("field_sources", {}))
        for field in volatile_fields:
            if field in overlay_record:
                record[field] = overlay_record[field]
                sources[field] = "sqlite-overlay"
        record["field_sources"] = sources
        record["coordination_overlay"] = {
            "kind": "sqlite-overlay",
            "durable": False,
            "observed": True,
        }
        record["projection"] = {
            "status": "current",
            "canonical_note_path": record.get("canonical_note_path"),
            "observed_at": None,
        }
    return list(merged.values())


def _descending_time_key(record: JsonObject, field: str, identifier: str) -> tuple[str, str]:
    return (str(record.get(field) or ""), str(record.get(identifier) or ""))


class ControlRoomSnapshotAssembler:
    """Combine canonical Markdown with a replaceable coordination overlay."""

    def __init__(
        self,
        *,
        vault: VaultStateReader,
        store: StoreOverlayReader,
        runtimes: RuntimeCatalogPort,
        repository: RepositoryProvenanceReader | None = None,
        limits: SnapshotLimits | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._vault = vault
        self._store = store
        self._runtimes = runtimes
        self._repository = repository
        self.limits = limits or SnapshotLimits()
        self._clock = clock or (lambda: datetime.now(UTC))

    def _read(
        self,
    ) -> tuple[VaultState, StoreOverlay, tuple[JsonObject, ...], JsonObject, bool]:
        limit = self.limits.max_items_per_collection
        vault = self._vault.read_vault_state(limit=limit)
        store = self._store.read_store_overlay(limit=limit)
        runtime_descriptors = self._runtimes.list_runtimes()
        runtime_truncated = (
            len(runtime_descriptors) > limit
            or any(len(runtime.models) > limit for runtime in runtime_descriptors[:limit])
            or sum(len(runtime.models) for runtime in runtime_descriptors[:limit]) > limit
        )
        runtimes = tuple(
            runtime.as_json(model_limit=limit) for runtime in runtime_descriptors[:limit]
        )
        repository = (
            self._repository.read_repository_provenance()
            if self._repository is not None
            else None
        )
        return (
            vault,
            store,
            runtimes,
            repository or _unavailable_repository(),
            runtime_truncated,
        )

    def assemble(self) -> JsonObject:
        generated_at = _iso_now(self._clock)
        vault, store, runtimes, repository, runtime_truncated = self._read()
        limit = self.limits.max_items_per_collection

        task_links = {
            str(task["task_id"]): (
                task.get("canonical_note_path"),
                task.get("runtime_id", "unresolved"),
            )
            for task in vault.tasks
        }
        queue_unbounded = [dict(item) for item in store.queue]
        queue_unbounded.sort(
            key=lambda item: (
                -int(item.get("priority", 0)),
                str(item.get("not_before") or ""),
                str(item.get("command_id") or ""),
            )
        )
        queue = queue_unbounded[:limit]
        for item in queue:
            canonical_path, runtime_id = task_links.get(
                str(item["task_id"]), (None, "unresolved")
            )
            item["runtime_id"] = runtime_id
            if canonical_path is not None:
                item["canonical_note_path"] = canonical_path
                source = dict(item["source_of_truth"])
                source["canonical_note_path"] = canonical_path
                item["source_of_truth"] = source

        queue_by_task = {str(item["task_id"]): item for item in queue}
        tasks_unbounded = [dict(item) for item in vault.tasks]
        tasks_unbounded.sort(
            key=lambda item: (
                -int(item.get("priority", 0)),
                str(item.get("task_id") or ""),
            )
        )
        tasks = tasks_unbounded[:limit]
        for task in tasks:
            overlay = queue_by_task.get(str(task["task_id"]))
            if overlay is not None:
                task["queue"] = {
                    "command_id": overlay["command_id"],
                    "state": overlay["state"],
                    "attempt": overlay["attempt"],
                    "max_attempts": overlay["max_attempts"],
                    "not_before": overlay["not_before"],
                    "updated_at": overlay["updated_at"],
                    "source": "sqlite-overlay",
                }
                task["field_sources"] = {
                    **dict(task["field_sources"]),
                    "queue": "sqlite-overlay",
                }

        runs_unbounded = _merge_overlay_records(
            vault.runs,
            store.runs,
            identifier="run_id",
            volatile_fields=("state", "usage", "started_at", "finished_at"),
        )
        runs_unbounded.sort(
            key=lambda item: _descending_time_key(item, "created_at", "run_id"),
            reverse=True,
        )
        runs = runs_unbounded[:limit]
        approvals_unbounded = _merge_overlay_records(
            vault.approvals,
            store.approvals,
            identifier="approval_id",
            volatile_fields=("decision",),
        )
        approvals_unbounded.sort(
            key=lambda item: (
                item.get("decision") != "pending",
                str(item.get("requested_at") or ""),
                str(item.get("approval_id") or ""),
            )
        )
        approvals = approvals_unbounded[:limit]
        activity_unbounded = _merge_overlay_records(
            vault.activity,
            store.activity,
            identifier="event_id",
            volatile_fields=(),
        )
        activity_unbounded.sort(
            key=lambda item: _descending_time_key(item, "occurred_at", "event_id"),
            reverse=True,
        )
        activity = activity_unbounded[:limit]

        routines_unbounded = [dict(item) for item in vault.routines]
        routines_unbounded.sort(key=lambda item: str(item.get("routine_id") or ""))
        routines = routines_unbounded[:limit]

        models: list[JsonObject] = []
        for runtime in runtimes:
            for model in runtime["models"]:
                entry = dict(model)
                entry["runtime_id"] = runtime["runtime_id"]
                models.append(entry)
                if len(models) >= limit:
                    break
            if len(models) >= limit:
                break

        warnings_unbounded = [*vault.warnings, *store.warnings]
        warnings = warnings_unbounded[:limit]
        collection_truncated = any(
            len(collection) > limit
            for collection in (
                queue_unbounded,
                tasks_unbounded,
                routines_unbounded,
                runs_unbounded,
                approvals_unbounded,
                activity_unbounded,
                warnings_unbounded,
            )
        )
        status = "degraded" if warnings else "validation_only"
        return {
            "schema": SNAPSHOT_SCHEMA,
            "api_version": 1,
            "generated_at": generated_at,
            "status": status,
            "state_model": {
                "canonical": "markdown",
                "coordination_overlay": "sqlite",
                "history": "git",
                "dispatch_enabled": False,
            },
            "freshness": {
                "canonical_markdown_scanned_at": generated_at,
                "store_overlay_observed_at": store.observed_at,
                "git_observed_at": repository.get("observed_at"),
                "projection_status": "partial" if store.runs or store.approvals else "not_required",
            },
            "runtimes": list(runtimes),
            "models": models,
            "tasks": tasks,
            "routines": routines,
            "queue": queue,
            "runs": runs,
            "approvals": approvals,
            "activity": activity,
            "repository": repository,
            "warnings": warnings,
            "truncated": (
                vault.truncated
                or store.truncated
                or runtime_truncated
                or collection_truncated
            ),
        }

    def health(self, *, auth_required: bool) -> JsonObject:
        generated_at = _iso_now(self._clock)
        vault, store, runtimes, repository, _ = self._read()
        warnings = [*vault.warnings, *store.warnings]
        return {
            "schema": HEALTH_SCHEMA,
            "api_version": 1,
            "generated_at": generated_at,
            "status": "degraded" if warnings else "validation_only",
            "validation_only": True,
            "dispatch_enabled": False,
            "auth": "required" if auth_required else "disabled",
            "canonical_source": "markdown",
            "coordination_overlay": "sqlite",
            "repository_available": bool(repository.get("available")),
            "runtimes": [
                {
                    "runtime_id": runtime["runtime_id"],
                    "health": runtime["health"],
                    "validation_only": runtime["validation_only"],
                }
                for runtime in runtimes
            ],
            "warnings": warnings,
        }
