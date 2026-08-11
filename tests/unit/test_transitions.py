import pytest

from obsidian_hermes.domain.enums import CommandState
from obsidian_hermes.domain.transitions import can_transition, require_transition


def test_normative_happy_path_edges_are_allowed() -> None:
    path = [
        CommandState.QUEUED,
        CommandState.VALIDATED,
        CommandState.CLAIMED,
        CommandState.RUNNING,
        CommandState.VERIFYING,
        CommandState.COMPLETED,
    ]

    assert all(
        can_transition(current, target) for current, target in zip(path, path[1:], strict=False)
    )


def test_terminal_state_cannot_transition() -> None:
    assert not can_transition(CommandState.COMPLETED, CommandState.QUEUED)
    with pytest.raises(ValueError, match="completed -> queued"):
        require_transition(CommandState.COMPLETED, CommandState.QUEUED)


def test_expired_claim_with_no_effect_can_return_to_validated() -> None:
    assert can_transition(CommandState.CLAIMED, CommandState.VALIDATED)
