"""Fail-closed Hermes gate entry points for the pre-dispatch scaffold."""

from __future__ import annotations

import json
from collections.abc import Sequence


def _idle(component: str) -> int:
    print(json.dumps({"wakeAgent": False, "component": component}, separators=(",", ":")))
    return 0


def ingest_main(argv: Sequence[str] | None = None) -> int:
    """Report no eligible work until attested dispatch verification is implemented."""

    del argv
    return _idle("ingest-worker")


def watchdog_main(argv: Sequence[str] | None = None) -> int:
    """Remain model-free; bridge/store watchdog integration is not yet enabled."""

    del argv
    return _idle("queue-watchdog")
