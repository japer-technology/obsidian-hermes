import json
from pathlib import Path

import pytest

from obsidian_hermes.domain.errors import ResourceValidationError
from obsidian_hermes.resources.loader import load_resource
from obsidian_hermes.resources.validation import SchemaRegistry
from obsidian_hermes.schemas import SCHEMA_FILENAMES

FIXTURES = Path(__file__).parents[1] / "fixtures" / "v2"


@pytest.fixture(scope="module")
def registry() -> SchemaRegistry:
    return SchemaRegistry.bundled()


def test_complete_fixture_exists_and_passes_for_every_schema(registry: SchemaRegistry) -> None:
    fixture_names = {path.name for path in (FIXTURES / "valid").glob("*.json")}
    expected_names = {name.replace(".schema.json", ".json") for name in SCHEMA_FILENAMES.values()}
    assert fixture_names == expected_names

    for path in sorted((FIXTURES / "valid").glob("*.json")):
        document = load_resource(path, registry=registry)
        expected_schema = path.name.removesuffix("-v2.json")
        assert document.metadata["schema"] == f"{expected_schema}/v2"


def test_complete_markdown_resources_cross_the_full_loader(registry: SchemaRegistry) -> None:
    json_task = load_resource(FIXTURES / "valid" / "hermes.task-v2.json", registry=registry)
    markdown_task = load_resource(FIXTURES / "valid" / "hermes.task-v2.md", registry=registry)
    approval = load_resource(
        FIXTURES / "valid" / "hermes.approval-v2.md", registry=registry
    )

    assert markdown_task.metadata["schema"] == "hermes.task/v2"
    assert markdown_task.spec_hash == json_task.spec_hash
    assert markdown_task.body.startswith("\n# Goal")
    assert approval.metadata["schema"] == "hermes.approval/v2"
    assert "## Human decision" in approval.body


def test_focused_invalid_json_fixtures_fail_closed(registry: SchemaRegistry) -> None:
    paths = sorted((FIXTURES / "invalid").glob("*.json"))
    assert paths
    for path in paths:
        with pytest.raises(ResourceValidationError):
            load_resource(path, registry=registry)


def test_terminal_routine_change_requires_signature(registry: SchemaRegistry) -> None:
    path = FIXTURES / "invalid" / "unsigned-routine-change.approval.json"
    with pytest.raises(ResourceValidationError, match="/attestation/method"):
        load_resource(path, registry=registry)


def test_schema_documents_are_offline_and_self_consistent(registry: SchemaRegistry) -> None:
    assert set(registry.schemas) == set(SCHEMA_FILENAMES)
    for schema_name, schema in registry.schemas.items():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["properties"]["schema"]["const"] == schema_name
        assert schema["properties"]["schema_version"]["const"] == 2
        assert schema["additionalProperties"] is False


def test_loaded_resource_metadata_cannot_mutate_after_hash(registry: SchemaRegistry) -> None:
    path = FIXTURES / "valid" / "hermes.task-v2.json"
    document = load_resource(path, registry=registry)
    digest = document.spec_hash

    with pytest.raises(TypeError):
        document.metadata["title"] = "Changed after validation"  # type: ignore[index]
    permissions = document.metadata["permissions"]
    with pytest.raises(TypeError):
        permissions["write"] = ()  # type: ignore[index]
    assert document.spec_hash == digest
    assert specification_hash(document.metadata, body=document.body) == digest


def test_valid_fixture_json_has_no_contract_placeholders() -> None:
    forbidden = {"...", "PINNED_PROVIDER", "PINNED_MODEL", "SIGNATURE_PLACEHOLDER"}

    def values(value: object) -> list[object]:
        if isinstance(value, dict):
            return [child for item in value.values() for child in values(item)]
        if isinstance(value, list):
            return [child for item in value for child in values(item)]
        return [value]

    for path in (FIXTURES / "valid").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert forbidden.isdisjoint(values(data))


def _valid_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / "valid" / name).read_text(encoding="utf-8"))


def test_semantic_timezone_and_schedule_fail_closed(registry: SchemaRegistry) -> None:
    bad_timezone = _valid_fixture("hermes.routine-v2.json")
    bad_timezone["schedule"] = {"expression": "every 5m", "timezone": "../etc/passwd"}
    with pytest.raises(ResourceValidationError):
        registry.validate(bad_timezone)

    unbounded_schedule = _valid_fixture("hermes.routine-v2.json")
    unbounded_schedule["schedule"] = {"expression": "every 1441m", "timezone": "Etc/UTC"}
    with pytest.raises(ResourceValidationError, match="exceeds one day"):
        registry.validate(unbounded_schedule)


def test_concrete_paths_cannot_contain_globs_or_ambiguous_segments(
    registry: SchemaRegistry,
) -> None:
    receipt = _valid_fixture("hermes.receipt-v2.json")
    receipt["outputs"] = ["ReadOnly/30 Knowledge/raw/**"]
    with pytest.raises(ResourceValidationError):
        registry.validate(receipt)

    agent = _valid_fixture("hermes.agent-v2.json")
    agent["prompt_sources"] = ["ReadOnly/Policies//AGENTS.md"]
    with pytest.raises(ResourceValidationError):
        registry.validate(agent)

    non_normalized = _valid_fixture("hermes.agent-v2.json")
    non_normalized["prompt_sources"] = ["ReadOnly/Policies/e\u0301.md"]
    with pytest.raises(ResourceValidationError, match="NFC"):
        registry.validate(non_normalized)


def test_typed_ulid_cannot_exceed_128_bits(registry: SchemaRegistry) -> None:
    task = _valid_fixture("hermes.task-v2.json")
    task["id"] = "task_8" + "0" * 25
    with pytest.raises(ResourceValidationError):
        registry.validate(task)


def test_metadata_control_characters_cannot_bypass_patterns(registry: SchemaRegistry) -> None:
    task = _valid_fixture("hermes.task-v2.json")
    task["id"] = f"{task['id']}\n"
    with pytest.raises(ResourceValidationError, match="control characters"):
        registry.validate(task)


def test_generated_metadata_rejects_lone_unicode_surrogates(registry: SchemaRegistry) -> None:
    raw_source = _valid_fixture("hermes.raw-source-v2.json")
    raw_source["title"] = "\ud800"
    with pytest.raises(ResourceValidationError, match="surrogate"):
        registry.validate(raw_source)


def test_git_metadata_and_case_colliding_grants_are_denied(
    registry: SchemaRegistry,
) -> None:
    git_task = _valid_fixture("hermes.task-v2.json")
    git_task["permissions"]["write"] = ["ReadWrite/.git/**"]
    git_task["output"]["path"] = "ReadWrite/.git/config"
    with pytest.raises(ResourceValidationError, match="Git metadata"):
        registry.validate(git_task)

    colliding_task = _valid_fixture("hermes.task-v2.json")
    colliding_task["permissions"]["read"] = [
        "ReadOnly/10 Projects/**",
        "ReadOnly/10 projects/**",
    ]
    with pytest.raises(ResourceValidationError, match="collide"):
        registry.validate(colliding_task)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"destination": "other.invalid"}, "allowlist"),
        ({"output": "ReadWrite/98 Archive/result.md"}, "write permissions"),
        ({"context": "ReadOnly/20 Areas"}, "read permissions"),
        ({"requests": 0}, "budget"),
        ({"url": "https://example.invalid:0/source"}, "invalid URL port"),
        ({"destination": "example.invalid:0"}, "invalid destination"),
        ({"destination": "example.invalid:99999"}, "invalid destination"),
    ],
)
def test_task_permissions_and_network_are_locally_consistent(
    registry: SchemaRegistry, mutation: dict[str, object], message: str
) -> None:
    task = _valid_fixture("hermes.task-v2.json")
    if "destination" in mutation:
        task["permissions"]["network"]["destinations"] = [mutation["destination"]]
    if "output" in mutation:
        task["output"]["path"] = mutation["output"]
    if "context" in mutation:
        task["context_roots"] = [mutation["context"]]
    if "requests" in mutation:
        task["budgets"]["max_network_requests"] = mutation["requests"]
    if "url" in mutation:
        task["inputs"][0]["value"] = mutation["url"]

    with pytest.raises(ResourceValidationError, match=message):
        registry.validate(task)


def test_approval_decision_must_precede_expiry(registry: SchemaRegistry) -> None:
    approval = _valid_fixture("hermes.approval-v2.json")
    approval.update(
        {
            "decision": "approved",
            "decided_by": "user:local-owner",
            "decided_at": "2026-08-12T03:15:00Z",
            "attestation": {
                "method": "local-bridge",
                "key_id": "local-owner",
                "signature": "test-signature-not-for-production",
            },
        }
    )
    with pytest.raises(ResourceValidationError, match="before expiry"):
        registry.validate(approval)


def test_run_timestamps_and_terminal_receipt_are_coherent(registry: SchemaRegistry) -> None:
    run = _valid_fixture("hermes.run-v2.json")
    run["started_at"] = "2026-08-11T03:09:00Z"
    with pytest.raises(ResourceValidationError, match="before creation"):
        registry.validate(run)

    terminal = _valid_fixture("hermes.run-v2.json")
    terminal["state"] = "completed"
    terminal["finished_at"] = "2026-08-11T03:17:00Z"
    with pytest.raises(ResourceValidationError, match="terminal receipt"):
        registry.validate(terminal)

    unstarted = _valid_fixture("hermes.run-v2.json")
    unstarted["started_at"] = None
    with pytest.raises(ResourceValidationError, match="start timestamp"):
        registry.validate(unstarted)
