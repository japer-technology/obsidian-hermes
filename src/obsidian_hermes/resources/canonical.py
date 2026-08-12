"""Versioned resource and plan hashing from specification section 5.4."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from importlib.resources import files
from typing import Any

from obsidian_hermes.domain.errors import ResourceValidationError, SchemaError
from obsidian_hermes.domain.ids import CATALOGUE_ID_RE, validate_id

SPECIFICATION_SCHEMAS = frozenset(
    {
        "hermes.task/v2",
        "hermes.routine/v2",
        "hermes.control/v2",
        "hermes.agent/v2",
        "hermes.skill/v2",
    }
)


def normalize_markdown_body(body: str) -> str:
    """Normalise Markdown to LF endings and exactly one final newline."""

    return body.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def _assert_canonical_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ResourceValidationError(
                f"{path}: Unicode surrogate code points are not canonical UTF-8 strings"
            )
        return
    if isinstance(value, float):
        raise ResourceValidationError(
            f"{path}: floating-point values are not accepted by the v2 canonical profile"
        )
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ResourceValidationError(f"{path}: canonical mapping keys must be strings")
            _assert_canonical_value(key, f"{path}.<key>")
            _assert_canonical_value(child, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _assert_canonical_value(child, f"{path}[{index}]")
        return
    raise ResourceValidationError(f"{path}: unsupported canonical value {type(value).__name__}")


def _json_compatible(value: Any) -> Any:
    """Copy generic immutable mappings/sequences into JSON encoder containers."""

    if isinstance(value, Mapping):
        return {key: _json_compatible(child) for key, child in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_compatible(child) for child in value]
    return value


def canonical_json(value: Mapping[str, Any]) -> bytes:
    """Encode a mapping as sorted, compact UTF-8 JSON while preserving arrays."""

    _assert_canonical_value(value)
    return json.dumps(
        _json_compatible(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _load_hash_contracts() -> Mapping[str, Any]:
    contract_path = files("obsidian_hermes.contracts").joinpath("hash-contracts-v2.json")
    loaded = json.loads(contract_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("contract_version") != 2:
        raise SchemaError("invalid bundled v2 hash contract")
    contracts = loaded.get("contracts")
    if not isinstance(contracts, dict):
        raise SchemaError("bundled v2 hash contract has no contracts mapping")
    return contracts


def _remove_pointer(document: dict[str, Any], pointer: str) -> None:
    parts = pointer.removeprefix("/").split("/")
    current: dict[str, Any] = document
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            return
        current = child
    current.pop(parts[-1], None)


def specification_hash(metadata: Mapping[str, Any], *, body: str = "") -> str:
    """Hash one validated human-authored resource using its exact v2 contract.

    Callers must perform JSON Schema and semantic validation before invoking
    this function. Generated resources intentionally have no specification
    hash contract and fail closed here.
    """

    schema = metadata.get("schema")
    if not isinstance(schema, str):
        raise ResourceValidationError("resource has no string schema discriminator")
    contract = _load_hash_contracts().get(schema)
    if not isinstance(contract, dict):
        raise SchemaError(f"no v2 specification-hash contract for {schema}")

    selected = _json_compatible(metadata)
    assert isinstance(selected, dict)
    exclude_paths = contract.get("exclude_paths", [])
    if not isinstance(exclude_paths, list) or not all(
        isinstance(item, str) for item in exclude_paths
    ):
        raise SchemaError(f"invalid exclusion list for {schema}")
    for pointer in exclude_paths:
        _remove_pointer(selected, pointer)

    if contract.get("include_body") is True:
        payload: Mapping[str, Any] = {
            "frontmatter": selected,
            "body": normalize_markdown_body(body),
        }
    else:
        payload = selected
    return sha256_digest(canonical_json(payload))


def plan_hash(plan: Mapping[str, Any]) -> str:
    """Hash a complete ordered action plan, failing closed on partial plans."""

    required = {"actions", "permissions", "budgets", "expected_outputs"}
    missing = sorted(required.difference(plan))
    if missing:
        raise ResourceValidationError(f"plan hash is missing required fields: {', '.join(missing)}")

    actions = plan["actions"]
    if not isinstance(actions, list) or not actions:
        raise ResourceValidationError("plan actions must be a non-empty ordered list")
    permissions = plan["permissions"]
    budgets = plan["budgets"]
    expected_outputs = plan["expected_outputs"]
    if not isinstance(permissions, Mapping):
        raise ResourceValidationError("plan permissions must be a mapping")
    if not isinstance(budgets, Mapping):
        raise ResourceValidationError("plan budgets must be a mapping")
    if not isinstance(expected_outputs, list):
        raise ResourceValidationError("plan expected_outputs must be an ordered list")

    idempotency_keys: set[str] = set()
    for index, action in enumerate(actions):
        if not isinstance(action, Mapping):
            raise ResourceValidationError(f"plan action {index} must be a mapping")
        for field in ("step_id", "arguments", "idempotency_key"):
            if field not in action:
                raise ResourceValidationError(f"plan action {index} is missing {field}")
        if not isinstance(action["step_id"], str) or not action["step_id"]:
            raise ResourceValidationError(f"plan action {index} has an invalid step_id")
        if not isinstance(action["arguments"], Mapping):
            raise ResourceValidationError(f"plan action {index} arguments must be a mapping")
        idempotency_key = action["idempotency_key"]
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise ResourceValidationError(f"plan action {index} has an invalid idempotency_key")
        if idempotency_key in idempotency_keys:
            raise ResourceValidationError("plan action idempotency keys must be unique")
        idempotency_keys.add(idempotency_key)

    return sha256_digest(canonical_json(plan))


def approval_attestation_payload(approval: Mapping[str, Any]) -> bytes:
    """Build the exact authority payload named by specification section 6.6.

    The containing approval must already have passed its executable schema;
    this boundary defensively validates every signable field again.
    """

    if approval.get("schema") != "hermes.approval/v2":
        raise ResourceValidationError("approval attestation requires hermes.approval/v2")
    selected_fields = ("id", "decision", "subject", "expires_at", "decided_by")
    missing = [field for field in selected_fields if field not in approval]
    if missing:
        raise ResourceValidationError(
            f"approval attestation is missing required fields: {', '.join(missing)}"
        )
    decision = approval["decision"]
    if not isinstance(decision, str) or decision not in {"approved", "rejected"}:
        raise ResourceValidationError("pending approval decisions cannot be attested")
    if not isinstance(approval["id"], str) or not validate_id(approval["id"], prefix="approval"):
        raise ResourceValidationError("approval attestation requires a valid approval ID")
    if not isinstance(approval["decided_by"], str) or not approval["decided_by"]:
        raise ResourceValidationError("approval attestation requires a non-empty approver")
    if not isinstance(approval["subject"], Mapping):
        raise ResourceValidationError("approval attestation requires the complete subject")
    if not isinstance(approval["expires_at"], str) or not approval["expires_at"]:
        raise ResourceValidationError("approval attestation requires an expiry")
    if (
        re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})",
            approval["expires_at"],
        )
        is None
    ):
        raise ResourceValidationError("approval attestation requires an RFC 3339 expiry")
    try:
        expiry = datetime.fromisoformat(approval["expires_at"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ResourceValidationError("approval attestation requires an RFC 3339 expiry") from error
    if expiry.tzinfo is None:
        raise ResourceValidationError("approval attestation expiry must contain an offset")
    _validate_approval_subject(approval["subject"])
    selected = {field: approval[field] for field in selected_fields}
    return canonical_json(selected)


def approval_attestation_hash(approval: Mapping[str, Any]) -> str:
    return sha256_digest(approval_attestation_payload(approval))


def _validate_approval_subject(subject: Mapping[str, Any]) -> None:
    subject_type = subject.get("type")
    if subject_type == "task-plan":
        expected = {
            "type",
            "task_id",
            "run_id",
            "task_generation",
            "hash_kind",
            "hash",
        }
        valid_identity = (
            isinstance(subject.get("task_id"), str)
            and validate_id(subject["task_id"], prefix="task")
            and isinstance(subject.get("run_id"), str)
            and validate_id(subject["run_id"], prefix="run")
            and isinstance(subject.get("task_generation"), int)
            and not isinstance(subject["task_generation"], bool)
            and subject["task_generation"] > 0
            and subject.get("hash_kind") == "plan"
        )
    elif subject_type == "routine-spec":
        expected = {"type", "routine_id", "revision", "hash_kind", "hash"}
        valid_identity = (
            isinstance(subject.get("routine_id"), str)
            and CATALOGUE_ID_RE.fullmatch(subject["routine_id"]) is not None
            and isinstance(subject.get("revision"), int)
            and not isinstance(subject["revision"], bool)
            and subject["revision"] > 0
            and subject.get("hash_kind") == "specification"
        )
    else:
        raise ResourceValidationError("approval attestation has an unknown subject type")

    digest = subject.get("hash")
    if set(subject) != expected or not valid_identity:
        raise ResourceValidationError("approval attestation subject is incomplete or invalid")
    if not isinstance(digest, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None:
        raise ResourceValidationError("approval attestation subject has an invalid hash")
