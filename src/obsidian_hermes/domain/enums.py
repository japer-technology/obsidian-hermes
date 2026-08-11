"""Normative closed vocabularies from specification v2.0."""

from enum import StrEnum


class TaskOperation(StrEnum):
    SOURCE_INGEST = "source.ingest"
    BRIEF_GENERATE = "brief.generate"


class TaskDesiredState(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TaskObservedState(StrEnum):
    PENDING = "pending"
    INVALID = "invalid"
    QUEUED = "queued"
    RUNNING = "running"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommandState(StrEnum):
    QUEUED = "queued"
    VALIDATED = "validated"
    CLAIMED = "claimed"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    RETRY_SCHEDULED = "retry_scheduled"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"
    SUPERSEDED = "superseded"


TERMINAL_COMMAND_STATES = frozenset(
    {
        CommandState.COMPLETED,
        CommandState.BLOCKED,
        CommandState.FAILED,
        CommandState.CANCELLED,
        CommandState.DEAD_LETTER,
        CommandState.SUPERSEDED,
    }
)


class RoutineDesiredState(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ABSENT = "absent"


class ControlOperation(StrEnum):
    TASK_CANCEL = "task.cancel"
    TASK_RETRY = "task.retry"
    TASK_SNOOZE = "task.snooze"
    ROUTINE_RUN_ONCE = "routine.run-once"
    SYSTEM_RECONCILE = "system.reconcile"
    SYSTEM_VALIDATE = "system.validate"
    SYSTEM_VERIFY_MOUNTS = "system.verify-mounts"


class TaskMode(StrEnum):
    EXECUTE = "execute"
    DRY_RUN = "dry-run"
