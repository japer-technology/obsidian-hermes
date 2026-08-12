"""Typed bridge configuration with fail-closed deployment defaults."""

from __future__ import annotations

import ipaddress
import os
import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from obsidian_hermes.domain.errors import ConfigurationError

_WORKER_PATHS = {
    "vault_root": "/workspace/obsidian",
    "read_write_root": "/workspace/obsidian/ReadWrite",
    "read_only_root": "/workspace/obsidian/ReadOnly",
    "private_mask_root": "/workspace/obsidian/Private",
}


@dataclass(frozen=True, slots=True)
class BridgeSettings:
    validation_only: bool
    dispatch_enabled: bool
    reconcile_interval_seconds: int
    state_directory: Path
    database_path: Path
    lock_path: Path
    policy_directory: Path


@dataclass(frozen=True, slots=True)
class HermesSettings:
    executable: Path
    profile: str
    timezone: str
    gateway_restart_enabled: bool


@dataclass(frozen=True, slots=True)
class VaultSettings:
    read_write_root: Path
    read_only_root: Path
    private_mask_root: Path


@dataclass(frozen=True, slots=True)
class LimitSettings:
    max_files_per_scan: int
    max_resource_bytes: int
    max_items_per_dispatch: int
    lease_seconds: int
    bulk_change_files: int


@dataclass(frozen=True, slots=True)
class ModelPinSettings:
    provider: str
    name: str


@dataclass(frozen=True, slots=True)
class CapabilitySettings:
    ingest_gate: str
    queue_watchdog: str
    permitted_models: tuple[ModelPinSettings, ...]


@dataclass(frozen=True, slots=True)
class SecuritySettings:
    network_enforcement: str
    attestation_key_ref: str


@dataclass(frozen=True, slots=True)
class ControlRoomSettings:
    bind_host: str
    port: int
    max_items_per_collection: int
    max_response_bytes: int
    runtime_profiles: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class DeploymentConfig:
    schema_version: int
    executor_id: str
    bridge: BridgeSettings
    hermes: HermesSettings
    vault: VaultSettings
    worker_paths: dict[str, str]
    limits: LimitSettings
    capabilities: CapabilitySettings
    security: SecuritySettings
    control_room: ControlRoomSettings


def _only_keys(table: dict[str, Any], allowed: set[str], section: str) -> None:
    unknown = sorted(set(table).difference(allowed))
    if unknown:
        label = f"[{section}]" if section else "configuration"
        raise ConfigurationError(f"{label} contains unknown fields: {', '.join(unknown)}")


def _table(document: dict[str, Any], key: str) -> dict[str, Any]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise ConfigurationError(f"missing [{key}] configuration table")
    return value


def _string(table: dict[str, Any], key: str, section: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"[{section}].{key} must be a non-empty string")
    return value


def _boolean(table: dict[str, Any], key: str, section: str) -> bool:
    value = table.get(key)
    if not isinstance(value, bool):
        raise ConfigurationError(f"[{section}].{key} must be a boolean")
    return value


def _positive_integer(table: dict[str, Any], key: str, section: str) -> int:
    value = table.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigurationError(f"[{section}].{key} must be a positive integer")
    return value


def _absolute_path(table: dict[str, Any], key: str, section: str) -> Path:
    path = Path(_string(table, key, section))
    if not path.is_absolute():
        raise ConfigurationError(f"[{section}].{key} must be an absolute host path")
    return path


def _is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((path.resolve(strict=False), root.resolve(strict=False))) == str(
            root.resolve(strict=False)
        )
    except ValueError:
        return False


def load_config(path: Path) -> DeploymentConfig:
    """Load and statically validate one bridge TOML configuration."""

    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(f"cannot load configuration {path}: {error}") from error

    if document.get("schema_version") != 2:
        raise ConfigurationError("configuration schema_version must be exactly 2")
    _only_keys(
        document,
        {
            "schema_version",
            "executor_id",
            "bridge",
            "hermes",
            "vault",
            "worker",
            "limits",
            "capabilities",
            "security",
            "control_room",
        },
        "",
    )
    executor_id = document.get("executor_id")
    if (
        not isinstance(executor_id, str)
        or re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", executor_id) is None
    ):
        raise ConfigurationError("executor_id must be a stable lowercase slug")

    bridge_data = _table(document, "bridge")
    hermes_data = _table(document, "hermes")
    vault_data = _table(document, "vault")
    worker_data = _table(document, "worker")
    limits_data = _table(document, "limits")
    capabilities_data = _table(document, "capabilities")
    security_data = _table(document, "security")
    control_room_data = _table(document, "control_room")

    _only_keys(
        bridge_data,
        {
            "validation_only",
            "dispatch_enabled",
            "reconcile_interval_seconds",
            "state_directory",
            "database_path",
            "lock_path",
            "policy_directory",
        },
        "bridge",
    )
    _only_keys(
        hermes_data,
        {"executable", "profile", "timezone", "gateway_restart_enabled"},
        "hermes",
    )
    _only_keys(
        vault_data,
        {"read_write_root", "read_only_root", "private_mask_root"},
        "vault",
    )
    _only_keys(worker_data, {*_WORKER_PATHS, "network_default"}, "worker")
    _only_keys(
        limits_data,
        {
            "max_files_per_scan",
            "max_resource_bytes",
            "max_items_per_dispatch",
            "lease_seconds",
            "bulk_change_files",
        },
        "limits",
    )
    _only_keys(
        capabilities_data,
        {"ingest_gate", "queue_watchdog", "permitted_models"},
        "capabilities",
    )
    _only_keys(
        security_data,
        {"network_enforcement", "attestation_key_ref"},
        "security",
    )
    _only_keys(
        control_room_data,
        {
            "bind_host",
            "port",
            "max_items_per_collection",
            "max_response_bytes",
            "runtime_profiles",
        },
        "control_room",
    )

    reconcile_interval = bridge_data.get("reconcile_interval_seconds")
    if not isinstance(reconcile_interval, int) or not 1 <= reconcile_interval <= 600:
        raise ConfigurationError("[bridge].reconcile_interval_seconds must be between 1 and 600")

    bridge = BridgeSettings(
        validation_only=_boolean(bridge_data, "validation_only", "bridge"),
        dispatch_enabled=_boolean(bridge_data, "dispatch_enabled", "bridge"),
        reconcile_interval_seconds=reconcile_interval,
        state_directory=_absolute_path(bridge_data, "state_directory", "bridge"),
        database_path=_absolute_path(bridge_data, "database_path", "bridge"),
        lock_path=_absolute_path(bridge_data, "lock_path", "bridge"),
        policy_directory=_absolute_path(bridge_data, "policy_directory", "bridge"),
    )
    if bridge.validation_only and bridge.dispatch_enabled:
        raise ConfigurationError("dispatch cannot be enabled while validation_only is true")

    timezone = _string(hermes_data, "timezone", "hermes")
    try:
        ZoneInfo(timezone)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise ConfigurationError(
            f"[hermes].timezone is not an installed IANA timezone: {timezone}"
        ) from error
    hermes = HermesSettings(
        executable=_absolute_path(hermes_data, "executable", "hermes"),
        profile=_string(hermes_data, "profile", "hermes"),
        timezone=timezone,
        gateway_restart_enabled=_boolean(hermes_data, "gateway_restart_enabled", "hermes"),
    )

    vault = VaultSettings(
        read_write_root=_absolute_path(vault_data, "read_write_root", "vault"),
        read_only_root=_absolute_path(vault_data, "read_only_root", "vault"),
        private_mask_root=_absolute_path(vault_data, "private_mask_root", "vault"),
    )
    host_roots = (vault.read_write_root, vault.read_only_root, vault.private_mask_root)
    if len({root.resolve(strict=False) for root in host_roots}) != len(host_roots):
        raise ConfigurationError("vault access-zone roots must be distinct")
    for index, root in enumerate(host_roots):
        for other in host_roots[index + 1 :]:
            if _is_within(root, other) or _is_within(other, root):
                raise ConfigurationError("vault access-zone roots must not contain each other")
    if any(_is_within(bridge.database_path, root) for root in host_roots):
        raise ConfigurationError("bridge database must remain outside every worker mount")
    if not _is_within(bridge.database_path, bridge.state_directory):
        raise ConfigurationError("bridge database must be inside its profile state directory")

    worker_paths = {key: _string(worker_data, key, "worker") for key in _WORKER_PATHS}
    if worker_paths != _WORKER_PATHS:
        raise ConfigurationError("worker container paths must match the fixed v2 contract")
    if worker_data.get("network_default") != "deny":
        raise ConfigurationError("worker network_default must be deny")

    limits = LimitSettings(
        max_files_per_scan=_positive_integer(limits_data, "max_files_per_scan", "limits"),
        max_resource_bytes=_positive_integer(limits_data, "max_resource_bytes", "limits"),
        max_items_per_dispatch=_positive_integer(limits_data, "max_items_per_dispatch", "limits"),
        lease_seconds=_positive_integer(limits_data, "lease_seconds", "limits"),
        bulk_change_files=_positive_integer(limits_data, "bulk_change_files", "limits"),
    )

    raw_models = capabilities_data.get("permitted_models")
    if not isinstance(raw_models, list):
        raise ConfigurationError("[capabilities].permitted_models must be an array")
    model_pins: list[ModelPinSettings] = []
    for index, item in enumerate(raw_models):
        if not isinstance(item, dict) or set(item) != {"provider", "name"}:
            raise ConfigurationError(
                f"[capabilities].permitted_models[{index}] must contain provider and name"
            )
        model_pins.append(
            ModelPinSettings(
                provider=_string(item, "provider", "capabilities.permitted_models"),
                name=_string(item, "name", "capabilities.permitted_models"),
            )
        )
    capabilities = CapabilitySettings(
        ingest_gate=_string(capabilities_data, "ingest_gate", "capabilities"),
        queue_watchdog=_string(capabilities_data, "queue_watchdog", "capabilities"),
        permitted_models=tuple(model_pins),
    )

    network_enforcement = _string(security_data, "network_enforcement", "security")
    if network_enforcement not in {"unconfigured", "allowlist-proxy"}:
        raise ConfigurationError(
            "[security].network_enforcement must be unconfigured or allowlist-proxy"
        )
    attestation_key_ref = _string(security_data, "attestation_key_ref", "security")
    if not attestation_key_ref.startswith("secret://"):
        raise ConfigurationError("[security].attestation_key_ref must be an opaque secret:// ref")
    security = SecuritySettings(
        network_enforcement=network_enforcement,
        attestation_key_ref=attestation_key_ref,
    )
    if bridge.dispatch_enabled and network_enforcement == "unconfigured":
        raise ConfigurationError("dispatch requires an enforced network policy")
    if bridge.dispatch_enabled and not capabilities.permitted_models:
        raise ConfigurationError("dispatch requires at least one exact permitted model pin")

    bind_host = _string(control_room_data, "bind_host", "control_room")
    try:
        bind_address = ipaddress.ip_address(bind_host)
    except ValueError as error:
        raise ConfigurationError(
            "[control_room].bind_host must be a literal loopback IP address"
        ) from error
    if not bind_address.is_loopback:
        raise ConfigurationError("[control_room].bind_host must be a loopback address")
    port = _positive_integer(control_room_data, "port", "control_room")
    if port > 65_535:
        raise ConfigurationError("[control_room].port must be between 1 and 65535")
    max_items = _positive_integer(control_room_data, "max_items_per_collection", "control_room")
    if max_items > 2_000:
        raise ConfigurationError("[control_room].max_items_per_collection must be at most 2000")
    max_response_bytes = _positive_integer(control_room_data, "max_response_bytes", "control_room")
    if not 4_096 <= max_response_bytes <= 8_388_608:
        raise ConfigurationError(
            "[control_room].max_response_bytes must be between 4096 and 8388608"
        )
    raw_runtime_profiles = control_room_data.get("runtime_profiles")
    if not isinstance(raw_runtime_profiles, dict):
        raise ConfigurationError("[control_room].runtime_profiles must be a TOML table")
    runtime_profiles: dict[str, str] = {}
    for profile, runtime_id in raw_runtime_profiles.items():
        if (
            not isinstance(profile, str)
            or re.fullmatch(r"[a-z][a-z0-9-]*", profile) is None
            or not isinstance(runtime_id, str)
            or re.fullmatch(r"[a-z][a-z0-9-]*:[a-z][a-z0-9-]*", runtime_id) is None
        ):
            raise ConfigurationError(
                "[control_room].runtime_profiles must map profile slugs to runtime:profile ids"
            )
        runtime_profiles[profile] = runtime_id
    control_room = ControlRoomSettings(
        bind_host=str(bind_address),
        port=port,
        max_items_per_collection=max_items,
        max_response_bytes=max_response_bytes,
        runtime_profiles=MappingProxyType(runtime_profiles),
    )

    return DeploymentConfig(
        schema_version=2,
        executor_id=executor_id,
        bridge=bridge,
        hermes=hermes,
        vault=vault,
        worker_paths=worker_paths,
        limits=limits,
        capabilities=capabilities,
        security=security,
        control_room=control_room,
    )
