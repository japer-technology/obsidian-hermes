import pytest

from obsidian_hermes.domain.schedule import ScheduleKind, parse_schedule


@pytest.mark.parametrize("expression", ["every 5m", "every 1h", "30 6 * * *"])
def test_accepts_closed_phase_one_schedules(expression: str) -> None:
    assert parse_schedule(expression).kind in {ScheduleKind.INTERVAL, ScheduleKind.DAILY}


@pytest.mark.parametrize(
    "expression",
    ["every 0m", "every 1441m", "every 25h", "* * * * *", "at sunrise", "every 5s"],
)
def test_rejects_unknown_or_unbounded_schedules(expression: str) -> None:
    with pytest.raises(ValueError):
        parse_schedule(expression)
