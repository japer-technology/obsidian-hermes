import json
import os
from pathlib import Path

import pytest

from obsidian_hermes.domain.errors import LifecycleError
from obsidian_hermes.lifecycle import LifecycleManager

SOURCE_ROOT = Path(__file__).parents[2]
PLUGIN_PATH = Path(".obsidian/plugins/agent-control-room")


def manager(tmp_path: Path) -> LifecycleManager:
    (tmp_path / ".obsidian").mkdir()
    return LifecycleManager(vault=tmp_path, source_root=SOURCE_ROOT)


def test_install_seeds_once_and_records_only_plugin_artifacts(tmp_path: Path) -> None:
    lifecycle = manager(tmp_path)

    result = lifecycle.install()

    assert result["operation"] == "install"
    assert (tmp_path / PLUGIN_PATH / "main.js").is_file()
    assert (tmp_path / "ReadWrite/01 Dashboard/Home.md").is_file()
    manifest = json.loads((tmp_path / ".obsidian-hermes/installation.json").read_text())
    assert set(manifest["artifacts"]) == {
        ".obsidian/plugins/agent-control-room/manifest.json",
        ".obsidian/plugins/agent-control-room/main.js",
        ".obsidian/plugins/agent-control-room/styles.css",
    }

    home = tmp_path / "ReadWrite/01 Dashboard/Home.md"
    home.write_text("# My dashboard\n", encoding="utf-8")
    lifecycle.update()

    assert home.read_text(encoding="utf-8") == "# My dashboard\n"


def test_default_source_root_uses_checkout_assets(tmp_path: Path) -> None:
    (tmp_path / ".obsidian").mkdir()

    result = LifecycleManager(vault=tmp_path).install()

    assert result["changed"] == [
        ".obsidian/plugins/agent-control-room/manifest.json",
        ".obsidian/plugins/agent-control-room/main.js",
        ".obsidian/plugins/agent-control-room/styles.css",
    ]


def test_install_refuses_unmanaged_plugin_conflict_without_force(tmp_path: Path) -> None:
    lifecycle = manager(tmp_path)
    target = tmp_path / PLUGIN_PATH / "main.js"
    target.parent.mkdir(parents=True)
    target.write_text("custom", encoding="utf-8")

    with pytest.raises(LifecycleError, match="unmanaged plugin files"):
        lifecycle.install()

    result = lifecycle.install(force=True)

    assert result["backups"]
    assert target.read_bytes() == (SOURCE_ROOT / "apps/obsidian-hermes/main.js").read_bytes()


def test_doctor_repair_and_uninstall_protect_changed_artifact(tmp_path: Path) -> None:
    lifecycle = manager(tmp_path)
    lifecycle.install()
    target = tmp_path / PLUGIN_PATH / "styles.css"
    target.write_text("changed", encoding="utf-8")

    report, healthy = lifecycle.doctor()
    assert not healthy
    assert report["issues"] == [
        {"code": "artifact_changed", "message": (PLUGIN_PATH / "styles.css").as_posix()}
    ]

    repaired = lifecycle.repair()
    assert repaired["repaired"] == [(PLUGIN_PATH / "styles.css").as_posix()]
    _, healthy = lifecycle.doctor()
    assert healthy

    target.write_text("local style", encoding="utf-8")
    result = lifecycle.uninstall()
    assert (PLUGIN_PATH / "styles.css").as_posix() in result["preserved"]
    assert target.exists()
    assert (tmp_path / "ReadWrite/01 Dashboard/Home.md").exists()
    assert (tmp_path / ".obsidian-hermes/installation.json").exists()


def test_repair_preserves_seed_history_and_uninstall_preserves_unknown_state(
    tmp_path: Path,
) -> None:
    lifecycle = manager(tmp_path)
    lifecycle.install()
    manifest_path = tmp_path / ".obsidian-hermes/installation.json"
    seeded = json.loads(manifest_path.read_text(encoding="utf-8"))["seeded"]

    lifecycle.repair()

    assert json.loads(manifest_path.read_text(encoding="utf-8"))["seeded"] == seeded
    unknown_state = tmp_path / ".obsidian-hermes/operator-note.txt"
    unknown_state.write_text("retain", encoding="utf-8")
    result = lifecycle.uninstall(purge_state=True)

    assert result["state_purged"] is False
    assert unknown_state.read_text(encoding="utf-8") == "retain"


def test_doctor_reports_unsafe_manifest_without_following_paths(tmp_path: Path) -> None:
    lifecycle = manager(tmp_path)
    lifecycle.install()
    manifest_path = tmp_path / ".obsidian-hermes/installation.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"] = {"../outside": "sha256:" + "0" * 64}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report, healthy = lifecycle.doctor()

    assert not healthy
    assert report["issues"][0]["code"] == "manifest_invalid"


def test_install_does_not_follow_a_precreated_temporary_symlink(tmp_path: Path) -> None:
    lifecycle = manager(tmp_path)
    target = tmp_path / PLUGIN_PATH / "manifest.json"
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.write_text("safe", encoding="utf-8")
    temporary = target.parent / ".manifest.json.attacker.obsidian-hermes-tmp"

    if os.name == "nt":
        pytest.skip("symlink creation requires platform policy on Windows")
    temporary.symlink_to(outside)

    lifecycle.install()

    assert outside.read_text(encoding="utf-8") == "safe"


@pytest.mark.skipif(os.name == "nt", reason="symlink creation requires platform policy on Windows")
def test_install_rejects_a_symlinked_plugin_directory(tmp_path: Path) -> None:
    lifecycle = manager(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    plugin_parent = tmp_path / ".obsidian/plugins"
    plugin_parent.mkdir()
    (plugin_parent / "agent-control-room").symlink_to(outside, target_is_directory=True)

    with pytest.raises(LifecycleError, match="contains a symlink"):
        lifecycle.install()
