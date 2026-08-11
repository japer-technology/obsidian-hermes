import json
from datetime import datetime
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parents[1] / "fixtures" / "v2" / "valid"


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_shared_fixture_trace_is_coherent() -> None:
    task = _fixture("hermes.task-v2.json")
    run = _fixture("hermes.run-v2.json")
    event = _fixture("hermes.event-v2.json")
    raw_source = _fixture("hermes.raw-source-v2.json")
    receipt = _fixture("hermes.receipt-v2.json")

    assert task["id"] == run["task_id"] == event["task_id"] == raw_source["task_id"]
    assert task["observed"]["generation"] == run["task_generation"]
    assert task["observed"]["active_run_id"] == run["id"]
    assert run["id"] == event["run_id"] == receipt["run_id"]
    assert run["command_id"] == event["command_id"] == receipt["command_id"]
    assert run["trace_id"] == event["trace_id"] == raw_source["trace_id"] == receipt["trace_id"]
    assert _time(run["created_at"]) <= _time(event["occurred_at"]) <= _time(run["started_at"])
    assert _time(run["started_at"]) <= _time(raw_source["retrieved_at"])
    assert _time(raw_source["retrieved_at"]) <= _time(receipt["completed_at"])


def test_draft_routine_does_not_claim_unattested_approval() -> None:
    routine = _fixture("hermes.routine-v2.json")

    assert routine["desired_state"] == "draft"
    assert routine["approval"]["approval_id"] is None
    assert routine["approval"]["approved_spec_hash"] is None
