"""Closed Phase One schedule grammar."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ScheduleKind(StrEnum):
    INTERVAL = "interval"
    DAILY = "daily"


@dataclass(frozen=True, slots=True)
class ParsedSchedule:
    kind: ScheduleKind
    expression: str


_INTERVAL = re.compile(r"^every (?P<count>[1-9][0-9]*)(?P<unit>[mh])$")
_DAILY = re.compile(r"^(?P<minute>[0-5]?[0-9]) (?P<hour>[01]?[0-9]|2[0-3]) \* \* \*$")


def parse_schedule(expression: str) -> ParsedSchedule:
    """Accept bounded minute/hour intervals or one daily cron time."""

    interval = _INTERVAL.fullmatch(expression)
    if interval is not None:
        count = int(interval.group("count"))
        maximum = 1_440 if interval.group("unit") == "m" else 24
        if count > maximum:
            raise ValueError("Phase One interval exceeds one day")
        return ParsedSchedule(ScheduleKind.INTERVAL, expression)

    if _DAILY.fullmatch(expression) is not None:
        return ParsedSchedule(ScheduleKind.DAILY, expression)
    raise ValueError("unsupported Phase One schedule expression")
