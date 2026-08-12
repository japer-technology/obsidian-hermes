from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from http.client import HTTPConnection
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from obsidian_hermes.control_room.api import (
    ControlRoomApi,
    ResponseTooLargeError,
    create_server,
)
from obsidian_hermes.control_room.ports import StoreOverlay, VaultState
from obsidian_hermes.control_room.runtimes import StaticRuntimeCatalog
from obsidian_hermes.control_room.snapshot import (
    ControlRoomSnapshotAssembler,
    SnapshotLimits,
)
from obsidian_hermes.control_room.vault import FilesystemVaultStateReader

ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "api" / "v1" / "control-room-snapshot.json"
CONTRACT = (
    ROOT
    / "src"
    / "obsidian_hermes"
    / "contracts"
    / "control-room-snapshot-v1.schema.json"
)
NOW = datetime(2026, 8, 12, 1, 30, tzinfo=UTC)


class _VaultReader:
    def __init__(self, state: VaultState | None = None) -> None:
        self.state = state or VaultState()

    def read_vault_state(self, *, limit: int) -> VaultState:
        assert limit > 0
        return self.state


class _StoreReader:
    def __init__(self, overlay: StoreOverlay | None = None) -> None:
        self.overlay = overlay or StoreOverlay(observed_at="2026-08-12T01:29:58Z")

    def read_store_overlay(self, *, limit: int) -> StoreOverlay:
        assert limit > 0
        return self.overlay


class _RepositoryReader:
    def read_repository_provenance(self) -> dict[str, Any]:
        return {
            "available": True,
            "role": "historical_shared_memory",
            "head": "abc123",
            "ref": "refs/heads/main",
            "dirty": False,
            "ahead": None,
            "behind": None,
            "upstream_status": "unavailable",
            "last_commit": None,
            "observed_at": "2026-08-12T01:29:55Z",
        }


def _assembler(
    *,
    vault: VaultState | None = None,
    store: StoreOverlay | None = None,
    max_response_bytes: int = 1_048_576,
) -> ControlRoomSnapshotAssembler:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    runtimes = StaticRuntimeCatalog(
        tuple(
            # The fixture is also the representative runtime discovery payload.
            _runtime_descriptor(item) for item in fixture["runtimes"]
        )
    )
    return ControlRoomSnapshotAssembler(
        vault=_VaultReader(vault),
        store=_StoreReader(store),
        runtimes=runtimes,
        repository=_RepositoryReader(),
        limits=SnapshotLimits(max_response_bytes=max_response_bytes),
        clock=lambda: NOW,
    )


def _runtime_descriptor(item: dict[str, Any]) -> Any:
    from obsidian_hermes.control_room.ports import RuntimeDescriptor

    return RuntimeDescriptor(
        runtime_id=item["runtime_id"],
        runtime_type=item["runtime_type"],
        display_name=item["display_name"],
        profile=item["profile"],
        capabilities=tuple(item["capabilities"]),
        health=item["health"],
        validation_only=item["validation_only"],
        models=tuple(item["models"]),
        details=item["details"],
    )


def test_representative_snapshot_satisfies_v1_contract() -> None:
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(fixture)

    nested_models = {
        (runtime["runtime_id"], model["model_id"])
        for runtime in fixture["runtimes"]
        for model in runtime["models"]
    }
    flat_models = {
        (model["runtime_id"], model["model_id"]) for model in fixture["models"]
    }
    assert flat_models == nested_models
    assert {item["runtime_id"] for item in fixture["tasks"]} <= {
        item["runtime_id"] for item in fixture["runtimes"]
    }
    assert {item["task_id"] for item in fixture["queue"]} <= {
        item["task_id"] for item in fixture["tasks"]
    }
    assert {item["task_id"] for item in fixture["runs"]} <= {
        item["task_id"] for item in fixture["tasks"]
    }


def test_snapshot_marks_markdown_as_canonical_and_sqlite_as_overlay() -> None:
    source = {
        "kind": "markdown",
        "canonical_note_path": "ReadWrite/02 Tasks/Example.md",
        "durable": True,
        "specification_hash": None,
    }
    vault = VaultState(
        tasks=(
            {
                "task_id": "task_example",
                "runtime_id": "openclaw:default",
                "title": "Example",
                "desired_state": "ready",
                "observed_state": "pending",
                "priority": 50,
                "operation": "brief.generate",
                "agent_profile": "operator",
                "model_selection": {
                    "provider": None,
                    "model": None,
                    "depth": None,
                    "source": "runtime_resolution",
                },
                "budget": {},
                "queue": None,
                "canonical_note_path": "ReadWrite/02 Tasks/Example.md",
                "source_of_truth": source,
                "field_sources": {"title": "markdown"},
            },
        )
    )
    overlay_source = {
        "kind": "sqlite-overlay",
        "canonical_note_path": None,
        "durable": False,
        "specification_hash": None,
    }
    store = StoreOverlay(
        queue=(
            {
                "command_id": "cmd_example",
                "task_id": "task_example",
                "runtime_id": "unresolved",
                "state": "queued",
                "priority": 50,
                "not_before": "2026-08-12T01:30:00Z",
                "attempt": 0,
                "max_attempts": 3,
                "updated_at": "2026-08-12T01:29:58Z",
                "canonical_note_path": None,
                "source_of_truth": overlay_source,
                "field_sources": {"state": "sqlite-overlay"},
            },
        ),
        observed_at="2026-08-12T01:29:58Z",
    )

    snapshot = _assembler(vault=vault, store=store).assemble()

    assert snapshot["state_model"] == {
        "canonical": "markdown",
        "coordination_overlay": "sqlite",
        "history": "git",
        "dispatch_enabled": False,
    }
    assert snapshot["queue"][0]["runtime_id"] == "openclaw:default"
    assert snapshot["queue"][0]["canonical_note_path"] == source["canonical_note_path"]
    assert snapshot["tasks"][0]["source_of_truth"]["kind"] == "markdown"
    assert snapshot["tasks"][0]["queue"]["source"] == "sqlite-overlay"


def test_filesystem_reader_resolves_runtime_from_immutable_profile_map(
    tmp_path: Path,
) -> None:
    source = ROOT / "tests" / "fixtures" / "v2" / "valid" / "hermes.task-v2.md"
    target = tmp_path / "ReadWrite" / "02 Tasks" / "Example.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())

    reader = FilesystemVaultStateReader(
        {"ReadWrite": tmp_path / "ReadWrite"},
        runtime_by_agent_profile={"researcher": "openclaw:research"},
    )
    state = reader.read_vault_state(limit=10)

    assert state.tasks[0]["runtime_id"] == "openclaw:research"
    assert state.tasks[0]["canonical_note_path"] == "ReadWrite/02 Tasks/Example.md"
    assert state.tasks[0]["source_of_truth"]["kind"] == "markdown"


def test_filesystem_reader_does_not_guess_an_unmapped_runtime(tmp_path: Path) -> None:
    source = ROOT / "tests" / "fixtures" / "v2" / "valid" / "hermes.task-v2.md"
    target = tmp_path / "task.md"
    target.write_bytes(source.read_bytes())

    state = FilesystemVaultStateReader({"Vault": tmp_path}).read_vault_state(limit=10)

    assert state.tasks[0]["runtime_id"] == "unresolved"


def test_filesystem_reader_labels_allowed_zones_and_never_enumerates_private(
    tmp_path: Path,
) -> None:
    task_source = ROOT / "tests" / "fixtures" / "v2" / "valid" / "hermes.task-v2.md"
    approval_source = (
        ROOT / "tests" / "fixtures" / "v2" / "valid" / "hermes.approval-v2.md"
    )
    read_write = tmp_path / "ReadWrite"
    read_only = tmp_path / "ReadOnly"
    private = tmp_path / "Private"
    read_write.mkdir()
    read_only.mkdir()
    private.mkdir()
    (read_write / "Task.md").write_bytes(task_source.read_bytes())
    (read_only / "Approval.md").write_bytes(approval_source.read_bytes())
    (private / "Secret task.md").write_bytes(task_source.read_bytes())

    state = FilesystemVaultStateReader(
        {"ReadWrite": read_write, "ReadOnly": read_only}
    ).read_vault_state(limit=10)

    assert [task["canonical_note_path"] for task in state.tasks] == ["ReadWrite/Task.md"]
    assert [approval["canonical_note_path"] for approval in state.approvals] == [
        "ReadOnly/Approval.md"
    ]
    assert all("Private" not in str(record) for record in (*state.tasks, *state.approvals))


def test_filesystem_reader_rejects_private_as_an_explicit_zone(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-Private"):
        FilesystemVaultStateReader({"Private": tmp_path})


def test_filesystem_reader_ignores_ordinary_frontmatter_without_warning(
    tmp_path: Path,
) -> None:
    note = tmp_path / "Ordinary note.md"
    note.write_text(
        "---\ntags: [project, personal]\naliases: &names [Example]\n---\n# Note\n",
        encoding="utf-8",
    )

    state = FilesystemVaultStateReader({"ReadWrite": tmp_path}).read_vault_state(limit=10)

    assert state.tasks == ()
    assert state.warnings == ()


def test_control_room_api_uses_optional_constant_time_bearer_auth() -> None:
    api = ControlRoomApi(_assembler(), bearer_token="test-secret")

    assert api.auth_required
    assert api.authorized("Bearer test-secret")
    assert not api.authorized("Bearer wrong")
    assert not api.authorized(None)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.0.2.1", "localhost", "example.test"])
def test_server_refuses_nonliteral_or_nonloopback_bindings(host: str) -> None:
    with pytest.raises(ValueError, match="loopback"):
        create_server(ControlRoomApi(_assembler()), host=host)


def test_server_exposes_only_read_only_versioned_routes() -> None:
    server = create_server(ControlRoomApi(_assembler(), bearer_token="test-secret"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        connection = HTTPConnection(host, port, timeout=2)
        connection.request("GET", "/api/v1/health")
        response = connection.getresponse()
        assert response.status == 401
        response.read()

        connection.request(
            "GET",
            "/api/v1/snapshot",
            headers={"Authorization": "Bearer test-secret"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        assert response.status == 200
        assert payload["schema"] == "obsidian-hermes.control-room-snapshot/v1"
        assert response.getheader("Cache-Control") == "no-store"

        connection.request(
            "POST",
            "/api/v1/snapshot",
            body=b"{}",
            headers={"Authorization": "Bearer test-secret"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        assert response.status == 405
        assert payload["error"]["code"] == "read_only"
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_response_byte_limit_is_enforced_before_transport() -> None:
    vault = VaultState(
        warnings=(
            {"code": "large", "message": "x" * 10_000, "path": None},
        )
    )
    api = ControlRoomApi(_assembler(vault=vault, max_response_bytes=4_096))

    with pytest.raises(ResponseTooLargeError):
        api.snapshot()
