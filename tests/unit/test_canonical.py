import json
from importlib.resources import files

import pytest

from obsidian_hermes.domain.errors import ResourceValidationError, SchemaError
from obsidian_hermes.resources.canonical import (
    SPECIFICATION_SCHEMAS,
    approval_attestation_hash,
    canonical_json,
    normalize_markdown_body,
    plan_hash,
    specification_hash,
)


def test_canonical_json_sorts_mappings_and_preserves_array_order() -> None:
    assert canonical_json({"z": [2, 1], "a": {"y": 2, "x": 1}}) == (
        b'{"a":{"x":1,"y":2},"z":[2,1]}'
    )


def test_body_normalization_uses_one_final_lf() -> None:
    assert normalize_markdown_body("first\r\nsecond\r\n\r\n") == "first\nsecond\n"


def test_task_observation_does_not_change_specification_hash() -> None:
    base = {"schema": "hermes.task/v2", "schema_version": 2, "id": "task_0" + "1" * 25}
    left = {**base, "observed": {"state": "pending"}}
    right = {**base, "observed": {"state": "running"}}

    assert specification_hash(left) == specification_hash(right)


def test_material_task_field_changes_specification_hash() -> None:
    base = {"schema": "hermes.task/v2", "schema_version": 2, "title": "First"}

    assert specification_hash(base) == (
        "sha256:d05efa1b5bd41a172d1d2baa6ba8d5238d3ffad60382a647fa34f275f5f20fdc"
    )
    assert specification_hash(base) != specification_hash({**base, "title": "Second"})


def test_generated_resources_have_no_specification_contract() -> None:
    with pytest.raises(SchemaError, match="no v2 specification-hash contract"):
        specification_hash({"schema": "hermes.run/v2", "schema_version": 2})


def test_hash_contract_manifest_exactly_covers_specification_resources() -> None:
    path = files("obsidian_hermes.contracts").joinpath("hash-contracts-v2.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))

    assert set(manifest["contracts"]) == SPECIFICATION_SCHEMAS


def test_routine_and_control_generated_fields_do_not_change_specification_hash() -> None:
    routine = {
        "schema": "hermes.routine/v2",
        "approval": {
            "required_for_change": True,
            "approval_id": "approval_01ARZ3NDEKTSV4RRFFQ69G5FB0",
            "approved_spec_hash": "sha256:" + "a" * 64,
        },
        "observed": {"state": "in_sync"},
    }
    changed_routine = {
        **routine,
        "approval": {
            **routine["approval"],
            "approval_id": "approval_01ARZ3NDEKTSV4RRFFQ69G5FB1",
            "approved_spec_hash": "sha256:" + "b" * 64,
        },
        "observed": {"state": "out_of_sync"},
    }
    control = {
        "schema": "hermes.control/v2",
        "operation": "system.validate",
        "attestation": {"signature": "first"},
        "observed": {"state": "pending"},
    }
    changed_control = {
        **control,
        "attestation": {"signature": "second"},
        "observed": {"state": "applied"},
    }

    assert specification_hash(routine) == specification_hash(changed_routine)
    assert specification_hash(control) == specification_hash(changed_control)


def test_plan_hash_is_order_sensitive_and_requires_complete_actions() -> None:
    plan = {
        "actions": [
            {"step_id": "one", "arguments": {}, "idempotency_key": "cmd:one:v1"},
            {"step_id": "two", "arguments": {}, "idempotency_key": "cmd:two:v1"},
        ],
        "permissions": {"write": []},
        "budgets": {"max_runtime_minutes": 1},
        "expected_outputs": ["report"],
    }

    assert plan_hash(plan) != plan_hash({**plan, "actions": list(reversed(plan["actions"]))})
    changed_arguments = {
        **plan,
        "actions": [
            {**plan["actions"][0], "arguments": {"path": "ReadWrite/output.md"}},
            plan["actions"][1],
        ],
    }
    assert plan_hash(plan) != plan_hash(changed_arguments)
    assert plan_hash(plan) != plan_hash({**plan, "permissions": {"write": ["ReadWrite/**"]}})
    with pytest.raises(ResourceValidationError, match="idempotency_key"):
        plan_hash({**plan, "actions": [{"step_id": "one", "arguments": {}}]})

    with pytest.raises(ResourceValidationError, match="permissions must be a mapping"):
        plan_hash({**plan, "permissions": None})
    with pytest.raises(ResourceValidationError, match="arguments must be a mapping"):
        plan_hash(
            {
                **plan,
                "actions": [
                    {"step_id": "one", "arguments": None, "idempotency_key": "cmd:one:v1"}
                ],
            }
        )
    with pytest.raises(ResourceValidationError, match="must be unique"):
        plan_hash(
            {
                **plan,
                "actions": [
                    {"step_id": "one", "arguments": {}, "idempotency_key": "same"},
                    {"step_id": "two", "arguments": {}, "idempotency_key": "same"},
                ],
            }
        )


def test_floats_fail_closed_until_number_canonicalization_is_normative() -> None:
    with pytest.raises(ResourceValidationError, match="floating-point"):
        canonical_json({"confidence": 0.5})


def test_lone_unicode_surrogates_fail_as_validation_errors() -> None:
    with pytest.raises(ResourceValidationError, match="surrogate"):
        canonical_json({"title": "\ud800"})


def test_approval_attestation_covers_exact_subject_and_decision() -> None:
    approval = {
        "schema": "hermes.approval/v2",
        "id": "approval_01ARZ3NDEKTSV4RRFFQ69G5FB0",
        "decision": "approved",
        "subject": {
            "type": "routine-spec",
            "routine_id": "ingest-worker",
            "revision": 1,
            "hash_kind": "specification",
            "hash": "sha256:" + "a" * 64,
        },
        "expires_at": "2026-08-12T03:15:00Z",
        "decided_by": "user:local-owner",
        "trace_id": "trace_01ARZ3NDEKTSV4RRFFQ69G5FAY",
        "attestation": {"signature": "first"},
    }

    digest = approval_attestation_hash(approval)
    assert digest == approval_attestation_hash(
        {**approval, "trace_id": "trace_01ARZ3NDEKTSV4RRFFQ69G5FAZ"}
    )
    assert digest != approval_attestation_hash(
        {**approval, "subject": {**approval["subject"], "hash": "sha256:" + "b" * 64}}
    )
    with pytest.raises(ResourceValidationError, match="pending"):
        approval_attestation_hash({**approval, "decision": "pending", "decided_by": None})
    with pytest.raises(ResourceValidationError, match="cannot be attested"):
        approval_attestation_hash({**approval, "decision": []})
    with pytest.raises(ResourceValidationError, match="incomplete"):
        approval_attestation_hash(
            {**approval, "subject": {"type": "routine-spec", "hash": "sha256:" + "a" * 64}}
        )
