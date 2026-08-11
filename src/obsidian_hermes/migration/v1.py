"""Deterministic v1 operation mapping from specification section 14.2."""

from __future__ import annotations

from enum import StrEnum


class MigrationDisposition(StrEnum):
    DRAFT_TASK = "draft_task_requires_review"
    BLOCKED_ACTION = "blocked_action_requires_review"
    DEFERRED_PROPOSAL = "non_executable_deferred_proposal"
    QUARANTINE = "quarantined_finding"


class RoutineDisposition(StrEnum):
    BRIDGE_CONFIGURATION = "bridge_configuration_proposal"
    ROUTER_CONFIGURATION = "router_configuration_proposal"
    DISABLED_PHASE_ONE = "disabled_phase_one_routine_requires_fresh_approval"
    DISABLED_DEFERRED = "disabled_deferred_extension_proposal"


_DRAFT_TASKS = frozenset({"source.ingest", "brief.generate"})
_DEFERRED = frozenset(
    {
        "capture.triage",
        "source.refresh",
        "knowledge.query",
        "wiki.ripple",
        "wiki.lint",
        "project.reconcile",
        "task.reconcile",
        "plan.create",
        "doctrine.synthesise",
        "armory.propose",
        "outcome.evaluate",
        "system.audit",
    }
)


def classify_operation(operation: str) -> MigrationDisposition:
    """Classify intent without transforming or executing the v1 source."""

    if operation in _DRAFT_TASKS:
        return MigrationDisposition.DRAFT_TASK
    if operation == "action.execute":
        return MigrationDisposition.BLOCKED_ACTION
    if operation in _DEFERRED:
        return MigrationDisposition.DEFERRED_PROPOSAL
    return MigrationDisposition.QUARANTINE


def classify_routine(routine: str) -> RoutineDisposition:
    """Map a normalized v1 routine name without enabling native work."""

    if routine == "control-reconciler":
        return RoutineDisposition.BRIDGE_CONFIGURATION
    if routine == "command-router":
        return RoutineDisposition.ROUTER_CONFIGURATION
    if routine in {"ingest-worker", "queue-watchdog", "daily-brief"}:
        return RoutineDisposition.DISABLED_PHASE_ONE
    return RoutineDisposition.DISABLED_DEFERRED
