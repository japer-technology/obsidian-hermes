"""Explicit non-model interfaces for the five-component Phase One boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from obsidian_hermes.bridge.ports import DispatchEnvelope

PHASE_ONE_OPERATIONS = frozenset({"source.ingest", "brief.generate"})


@dataclass(frozen=True, slots=True)
class StagedResult:
    run_id: str
    manifest_path: str
    checkpoint: str


@dataclass(frozen=True, slots=True)
class WatchdogFinding:
    kind: str
    resource_id: str | None
    trace_id: str | None
    detail_code: str


class CommandRouter(Protocol):
    def compile(self, task: Mapping[str, Any], *, generation: int) -> Mapping[str, Any]:
        """Compile validated intent without performing substantive work."""
        ...


class IngestWorker(Protocol):
    def execute(self, envelope: DispatchEnvelope) -> StagedResult:
        """Write one result manifest only beneath the allocated staging path."""
        ...


class QueueWatchdog(Protocol):
    def inspect(self) -> Sequence[WatchdogFinding]:
        """Return bounded deterministic findings without invoking a model."""
        ...


class DailyBriefWorker(Protocol):
    def generate(self, envelope: DispatchEnvelope) -> StagedResult:
        """Generate a linked brief from one authenticated, pinned-model run."""
        ...
