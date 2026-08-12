"""Deterministic command-state transition policy."""

from __future__ import annotations

from collections.abc import Mapping

from obsidian_hermes.domain.enums import TERMINAL_COMMAND_STATES, CommandState

_FORWARD_TRANSITIONS: Mapping[CommandState, frozenset[CommandState]] = {
    CommandState.QUEUED: frozenset(
        {CommandState.VALIDATED, CommandState.BLOCKED, CommandState.CANCELLED}
    ),
    CommandState.VALIDATED: frozenset(
        {
            CommandState.CLAIMED,
            CommandState.BLOCKED,
            CommandState.CANCELLED,
            CommandState.RETRY_SCHEDULED,
        }
    ),
    CommandState.CLAIMED: frozenset(
        {
            CommandState.VALIDATED,
            CommandState.RUNNING,
            CommandState.BLOCKED,
            CommandState.CANCELLED,
            CommandState.RETRY_SCHEDULED,
            CommandState.DEAD_LETTER,
        }
    ),
    CommandState.RUNNING: frozenset(
        {
            CommandState.AWAITING_APPROVAL,
            CommandState.RETRY_SCHEDULED,
            CommandState.VERIFYING,
            CommandState.BLOCKED,
            CommandState.FAILED,
            CommandState.CANCELLED,
            CommandState.DEAD_LETTER,
        }
    ),
    CommandState.AWAITING_APPROVAL: frozenset(
        {CommandState.QUEUED, CommandState.BLOCKED, CommandState.CANCELLED}
    ),
    CommandState.RETRY_SCHEDULED: frozenset(
        {
            CommandState.QUEUED,
            CommandState.BLOCKED,
            CommandState.CANCELLED,
            CommandState.DEAD_LETTER,
        }
    ),
    CommandState.VERIFYING: frozenset(
        {
            CommandState.COMPLETED,
            CommandState.RETRY_SCHEDULED,
            CommandState.BLOCKED,
            CommandState.FAILED,
            CommandState.CANCELLED,
            CommandState.DEAD_LETTER,
        }
    ),
}


def can_transition(current: CommandState, target: CommandState) -> bool:
    """Return whether the v2 lifecycle permits a direct state transition."""

    if current in TERMINAL_COMMAND_STATES:
        return False
    if target is CommandState.SUPERSEDED:
        return True
    return target in _FORWARD_TRANSITIONS.get(current, frozenset())


def require_transition(current: CommandState, target: CommandState) -> None:
    """Raise when a component attempts an undefined lifecycle edge."""

    if not can_transition(current, target):
        raise ValueError(f"invalid command transition: {current.value} -> {target.value}")
