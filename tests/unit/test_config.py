from pathlib import Path

import pytest

from obsidian_hermes.config import load_config
from obsidian_hermes.domain.errors import ConfigurationError


def _write_config(path: Path, *, dispatch: bool = False, validation_only: bool = True) -> None:
    root = path.parent
    state = (root / "state").as_posix()
    vault = (root / "vault").as_posix()
    mask = (root / "private-mask").as_posix()
    executable = (root / "bin" / "hermes").as_posix()
    path.write_text(
        f'''schema_version = 2
executor_id = "test-host"

[bridge]
validation_only = {str(validation_only).lower()}
dispatch_enabled = {str(dispatch).lower()}
reconcile_interval_seconds = 30
state_directory = "{state}"
database_path = "{state}/bridge.sqlite3"
lock_path = "{state}/bridge.lock"
policy_directory = "{vault}/ReadOnly/Policies"

[hermes]
executable = "{executable}"
profile = "default"
timezone = "Etc/UTC"
gateway_restart_enabled = false

[vault]
read_write_root = "{vault}/ReadWrite"
read_only_root = "{vault}/ReadOnly"
private_mask_root = "{mask}"

[worker]
vault_root = "/workspace/obsidian"
read_write_root = "/workspace/obsidian/ReadWrite"
read_only_root = "/workspace/obsidian/ReadOnly"
private_mask_root = "/workspace/obsidian/Private"
network_default = "deny"

[limits]
max_files_per_scan = 100
max_resource_bytes = 1000
max_items_per_dispatch = 3
lease_seconds = 900
bulk_change_files = 10

[capabilities]
ingest_gate = "obsidian-ingest-gate"
queue_watchdog = "obsidian-queue-watchdog"
permitted_models = []

[security]
network_enforcement = "unconfigured"
attestation_key_ref = "secret://bridge/test-key"
''',
        encoding="utf-8",
    )


def test_loads_validation_only_config(tmp_path: Path) -> None:
    path = tmp_path / "hermes.toml"
    _write_config(path)

    config = load_config(path)

    assert config.bridge.validation_only
    assert not config.bridge.dispatch_enabled
    assert config.hermes.timezone == "Etc/UTC"


def test_refuses_dispatch_in_validation_only_mode(tmp_path: Path) -> None:
    path = tmp_path / "hermes.toml"
    _write_config(path, dispatch=True)

    with pytest.raises(ConfigurationError, match="dispatch cannot be enabled"):
        load_config(path)


def test_invalid_timezone_is_a_configuration_error(tmp_path: Path) -> None:
    path = tmp_path / "hermes.toml"
    _write_config(path)
    content = path.read_text(encoding="utf-8").replace("Etc/UTC", "../etc/passwd")
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigurationError, match="IANA timezone"):
        load_config(path)
