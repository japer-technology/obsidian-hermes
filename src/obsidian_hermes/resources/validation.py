"""Offline JSON Schema registry and cross-field semantic validation."""

from __future__ import annotations

import ipaddress
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from obsidian_hermes.domain.errors import PathPolicyError, ResourceValidationError, SchemaError
from obsidian_hermes.domain.schedule import parse_schedule
from obsidian_hermes.schemas import ALL_SCHEMA_FILENAMES, SCHEMA_FILENAMES
from obsidian_hermes.security.paths import VaultPath, find_case_unicode_collisions

_PATH_FIELDS: Mapping[str, tuple[tuple[tuple[str, ...], bool], ...]] = {
    "hermes.task/v2": (
        (("context_roots",), False),
        (("permissions", "read"), True),
        (("permissions", "write"), True),
        (("output", "path"), False),
    ),
    "hermes.run/v2": ((("outputs",), False),),
    "hermes.routine/v2": (
        (("permissions_maximum", "read"), True),
        (("permissions_maximum", "write"), True),
    ),
    "hermes.agent/v2": (
        (("prompt_sources",), False),
        (("context_roots_maximum",), True),
        (("permissions_maximum", "read"), True),
        (("permissions_maximum", "write"), True),
    ),
    "hermes.skill/v2": (
        (("permissions", "read"), True),
        (("permissions", "write"), True),
    ),
    "hermes.receipt/v2": ((("outputs",), False),),
    "hermes.event/v2": ((("data", "path"), False),),
}


def _json_pointer(path: Any) -> str:
    parts = [str(part).replace("~", "~0").replace("/", "~1") for part in path]
    return "/" + "/".join(parts) if parts else "/"


def _parse_datetime(value: Any, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ResourceValidationError(f"/{field}: expected an RFC 3339 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ResourceValidationError(f"/{field}: invalid RFC 3339 timestamp") from error
    if parsed.tzinfo is None:
        raise ResourceValidationError(f"/{field}: timestamp must contain an offset")
    return parsed


@dataclass(frozen=True, slots=True)
class SchemaRegistry:
    """The complete bundled v2 registry; references never use the network."""

    schemas: Mapping[str, Mapping[str, Any]]
    registry: Registry[Any]

    @classmethod
    def bundled(cls) -> SchemaRegistry:
        package = files("obsidian_hermes.schemas")
        by_id: dict[str, Mapping[str, Any]] = {}
        offline_registry: Registry[Any] = Registry()

        for filename in ALL_SCHEMA_FILENAMES:
            raw = package.joinpath(filename).read_text(encoding="utf-8")
            document = json.loads(raw)
            if not isinstance(document, dict) or not isinstance(document.get("$id"), str):
                raise SchemaError(f"bundled schema {filename} has no absolute $id")
            try:
                Draft202012Validator.check_schema(document)
                resource = Resource.from_contents(document)
            except Exception as error:
                # Resource.from_contents has implementation-specific exception
                # types; all are converted at this package boundary.
                raise SchemaError(f"invalid bundled schema {filename}: {error}") from error
            schema_id = document["$id"]
            by_id[schema_id] = document
            offline_registry = offline_registry.with_resource(schema_id, resource)

        by_name: dict[str, Mapping[str, Any]] = {}
        for schema_name, filename in SCHEMA_FILENAMES.items():
            schema_id = json.loads(package.joinpath(filename).read_text(encoding="utf-8"))["$id"]
            by_name[schema_name] = by_id[schema_id]
        return cls(schemas=by_name, registry=offline_registry)

    def validate(self, instance: Mapping[str, Any]) -> None:
        schema_name = instance.get("schema")
        if not isinstance(schema_name, str) or schema_name not in self.schemas:
            raise ResourceValidationError(f"unknown resource schema: {schema_name!r}")

        validator = Draft202012Validator(
            self.schemas[schema_name],
            registry=self.registry,
            format_checker=FormatChecker(),
        )
        errors = sorted(
            validator.iter_errors(instance), key=lambda error: list(error.absolute_path)
        )
        if errors:
            error = errors[0]
            raise ResourceValidationError(
                f"{_json_pointer(error.absolute_path)}: violates {error.validator} constraint"
            )
        _validate_semantics(instance)


def _validate_semantics(instance: Mapping[str, Any]) -> None:
    schema_name = instance["schema"]
    assert isinstance(schema_name, str)
    _validate_no_control_scalars(instance)
    _validate_resource_paths(instance, schema_name)

    if schema_name == "hermes.task/v2":
        _validate_task(instance)

    if schema_name == "hermes.routine/v2":
        schedule = instance["schedule"]
        assert isinstance(schedule, Mapping)
        timezone = schedule["timezone"]
        assert isinstance(timezone, str)
        try:
            ZoneInfo(timezone)
        except (ValueError, ZoneInfoNotFoundError) as error:
            raise ResourceValidationError(
                f"/schedule/timezone: unknown IANA timezone {timezone}"
            ) from error
        expression = schedule["expression"]
        assert isinstance(expression, str)
        try:
            parse_schedule(expression)
        except ValueError as error:
            raise ResourceValidationError(f"/schedule/expression: {error}") from error

    if schema_name == "hermes.approval/v2":
        requested = _parse_datetime(instance["requested_at"], "requested_at")
        expires = _parse_datetime(instance["expires_at"], "expires_at")
        assert requested is not None and expires is not None
        if expires <= requested:
            raise ResourceValidationError("/expires_at: approval must expire after it is requested")
        if instance["decision"] != "pending":
            decided = _parse_datetime(instance["decided_at"], "decided_at")
            assert decided is not None
            if decided < requested or decided >= expires:
                raise ResourceValidationError(
                    "/decided_at: approval decision must occur before expiry"
                )

    if schema_name == "hermes.control/v2":
        created = _parse_datetime(instance["created_at"], "created_at")
        expires = _parse_datetime(instance["expires_at"], "expires_at")
        assert created is not None and expires is not None
        if expires <= created:
            raise ResourceValidationError("/expires_at: control must expire after it is created")

    if schema_name == "hermes.raw-source/v2":
        source_id = instance["source_id"]
        content_hash = instance["content_sha256"]
        assert isinstance(source_id, str) and isinstance(content_hash, str)
        if source_id.removeprefix("src_sha256_") != content_hash.removeprefix("sha256:"):
            raise ResourceValidationError("/source_id: source identity must match content_sha256")

    if schema_name == "hermes.run/v2":
        _validate_run(instance)


def _validate_resource_paths(instance: Mapping[str, Any], schema_name: str) -> None:
    parsed_paths: list[str] = []
    for parts, allow_glob in _PATH_FIELDS.get(schema_name, ()):
        value: Any = instance
        for part in parts:
            if not isinstance(value, Mapping) or part not in value:
                value = None
                break
            value = value[part]
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        for index, item in enumerate(values):
            if not isinstance(item, str):
                continue  # Structural validation reports the exact type error.
            pointer = "/" + "/".join(parts)
            if isinstance(value, list):
                pointer += f"/{index}"
            try:
                VaultPath.parse(item, allow_glob=allow_glob)
            except PathPolicyError as error:
                raise ResourceValidationError(f"{pointer}: {error}") from error
            parsed_paths.append(item)

    collisions = find_case_unicode_collisions(parsed_paths)
    if collisions:
        left, right = sorted(collisions)[0]
        raise ResourceValidationError(
            f"resource paths collide under Unicode/case folding: {left!r} and {right!r}"
        )


def _validate_no_control_scalars(value: Any, pointer: str = "") -> None:
    """Reject controls in metadata, including regular-expression end-anchor bypasses."""

    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ResourceValidationError(
                f"{pointer or '/'}: Unicode surrogate code points are not valid UTF-8 metadata"
            )
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ResourceValidationError(
                f"{pointer or '/'}: control characters are not allowed in resource metadata"
            )
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            escaped_key = str(key).replace("~", "~0").replace("/", "~1")
            _validate_no_control_scalars(child, f"{pointer}/{escaped_key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_no_control_scalars(child, f"{pointer}/{index}")


def _validate_task(task: Mapping[str, Any]) -> None:
    permissions = task["permissions"]
    budgets = task["budgets"]
    output = task["output"]
    assert isinstance(permissions, Mapping)
    assert isinstance(budgets, Mapping)
    assert isinstance(output, Mapping)

    read_grants = permissions["read"]
    write_grants = permissions["write"]
    assert isinstance(read_grants, list) and isinstance(write_grants, list)
    for index, root in enumerate(task["context_roots"]):
        if not _scope_allows(root, read_grants):
            raise ResourceValidationError(
                f"/context_roots/{index}: context root is outside task read permissions"
            )
    if not _scope_allows(output["path"], write_grants):
        raise ResourceValidationError("/output/path: output is outside task write permissions")

    network = permissions["network"]
    assert isinstance(network, Mapping)
    if task["operation"] == "brief.generate":
        if network["mode"] != "deny" or budgets["max_network_requests"] != 0:
            raise ResourceValidationError(
                "/permissions/network: brief.generate must use the local network-denied profile"
            )
        return

    inputs = task["inputs"]
    destinations = network["destinations"]
    assert isinstance(inputs, list) and isinstance(destinations, list)
    if network["mode"] != "allowlist":
        raise ResourceValidationError("/permissions/network: URL ingestion requires an allowlist")
    if budgets["max_network_requests"] < len(inputs):
        raise ResourceValidationError(
            "/budgets/max_network_requests: budget cannot retrieve every declared URL"
        )

    parsed_destinations = [_parse_destination(item) for item in destinations]
    for index, item in enumerate(inputs):
        assert isinstance(item, Mapping)
        url = urlsplit(item["value"])
        if url.username is not None or url.password is not None or url.hostname is None:
            raise ResourceValidationError(f"/inputs/{index}/value: URL authority is not allowed")
        try:
            default_port = 443 if url.scheme == "https" else 80
            port = default_port if url.port is None else url.port
        except ValueError as error:
            raise ResourceValidationError(f"/inputs/{index}/value: invalid URL port") from error
        if port < 1:
            raise ResourceValidationError(f"/inputs/{index}/value: invalid URL port")
        host = _normalize_host(url.hostname)
        if not any(
            host == allowed_host
            and (port == allowed_port or (allowed_port is None and port == default_port))
            for allowed_host, allowed_port in parsed_destinations
        ):
            raise ResourceValidationError(
                f"/inputs/{index}/value: URL destination is not in the task allowlist"
            )


def _scope_allows(path: Any, grants: list[Any]) -> bool:
    if not isinstance(path, str):
        return False
    normalized = path.rstrip("/")
    for grant in grants:
        if not isinstance(grant, str):
            continue
        if grant.endswith("/**"):
            root = grant.removesuffix("/**").rstrip("/")
            if normalized == root or normalized.startswith(f"{root}/"):
                return True
        elif normalized == grant.rstrip("/"):
            return True
    return False


def _normalize_host(host: str) -> str:
    try:
        return ipaddress.ip_address(host).compressed.casefold()
    except ValueError:
        return host.casefold()


def _parse_destination(value: Any) -> tuple[str, int | None]:
    if not isinstance(value, str):
        raise ResourceValidationError("/permissions/network/destinations: invalid destination")
    try:
        parsed = urlsplit(f"//{value}")
        host = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ResourceValidationError(
            f"/permissions/network/destinations: invalid destination {value}"
        ) from error
    if host is None or parsed.username is not None or parsed.password is not None:
        raise ResourceValidationError(
            f"/permissions/network/destinations: invalid destination {value}"
        )
    if port is not None and port < 1:
        raise ResourceValidationError(
            f"/permissions/network/destinations: invalid destination {value}"
        )
    return _normalize_host(host), port


def _validate_run(run: Mapping[str, Any]) -> None:
    created = _parse_datetime(run["created_at"], "created_at")
    started = _parse_datetime(run["started_at"], "started_at")
    finished = _parse_datetime(run["finished_at"], "finished_at")
    assert created is not None
    if started is not None and started < created:
        raise ResourceValidationError("/started_at: run cannot start before creation")
    if finished is not None and finished < (started or created):
        raise ResourceValidationError("/finished_at: run cannot finish before it starts")

    terminal = {"completed", "blocked", "failed", "cancelled", "dead_letter", "superseded"}
    started_required = terminal | {
        "running",
        "awaiting_approval",
        "retry_scheduled",
        "verifying",
    }
    if run["state"] in started_required and started is None:
        raise ResourceValidationError("/started_at: run state requires a start timestamp")
    if run["state"] in terminal and (finished is None or run["receipt_id"] is None):
        raise ResourceValidationError(
            "/state: terminal run requires finished_at and a terminal receipt"
        )
    if run["state"] not in terminal and finished is not None:
        raise ResourceValidationError("/finished_at: non-terminal run cannot already be finished")
