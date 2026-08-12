"""Runtime-neutral ports used to compose a control-room snapshot.

Markdown is the canonical application protocol.  The operational store is a
disposable coordination overlay, and Git is historical shared memory.  Keeping
those roles separate in the ports prevents a UI adapter from accidentally
promoting queue or lease state into durable vault truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, TypeAlias

JsonObject: TypeAlias = dict[str, Any]


@dataclass(frozen=True, slots=True)
class VaultState:
    """Canonical facts read from validated Markdown resources."""

    tasks: tuple[JsonObject, ...] = ()
    routines: tuple[JsonObject, ...] = ()
    runs: tuple[JsonObject, ...] = ()
    approvals: tuple[JsonObject, ...] = ()
    activity: tuple[JsonObject, ...] = ()
    warnings: tuple[JsonObject, ...] = ()
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class StoreOverlay:
    """Volatile coordination facts; never a replacement for vault Markdown."""

    queue: tuple[JsonObject, ...] = ()
    runs: tuple[JsonObject, ...] = ()
    approvals: tuple[JsonObject, ...] = ()
    activity: tuple[JsonObject, ...] = ()
    observed_at: str | None = None
    warnings: tuple[JsonObject, ...] = ()
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class RuntimeDescriptor:
    """One discoverable agent runtime without an executable adapter."""

    runtime_id: str
    runtime_type: str
    display_name: str
    profile: str
    capabilities: tuple[str, ...]
    health: str
    validation_only: bool
    models: tuple[JsonObject, ...] = ()
    details: JsonObject = field(default_factory=dict)

    def as_json(self, *, model_limit: int | None = None) -> JsonObject:
        models = self.models if model_limit is None else self.models[:model_limit]
        return {
            "runtime_id": self.runtime_id,
            "runtime_type": self.runtime_type,
            "display_name": self.display_name,
            "profile": self.profile,
            "capabilities": list(self.capabilities),
            "health": self.health,
            "validation_only": self.validation_only,
            "models": [dict(model) for model in models],
            "details": dict(self.details),
        }


class VaultStateReader(Protocol):
    """Read canonical human-and-agent state from the vault."""

    def read_vault_state(self, *, limit: int) -> VaultState: ...


class StoreOverlayReader(Protocol):
    """Read bounded, concurrency-sensitive state from a coordination store."""

    def read_store_overlay(self, *, limit: int) -> StoreOverlay: ...


class RuntimeCatalogPort(Protocol):
    """Describe available runtimes without invoking or mutating them."""

    def list_runtimes(self) -> tuple[RuntimeDescriptor, ...]: ...


class RepositoryProvenanceReader(Protocol):
    """Read optional Git provenance supplied by a trusted host integration."""

    def read_repository_provenance(self) -> JsonObject | None: ...
