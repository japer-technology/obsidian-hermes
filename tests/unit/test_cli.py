import json
from pathlib import Path

import pytest

from obsidian_hermes.cli import main


def test_validate_schemas_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", "schemas"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["valid"] is True
    assert len(output["schemas"]) == 11


def test_validate_valid_resource(capsys: pytest.CaptureFixture[str]) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "v2" / "valid" / "hermes.task-v2.json"
    assert main(["validate", "resource", str(fixture)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["resources"][0]["schema"] == "hermes.task/v2"


def test_migration_plan_never_marks_v1_work_executable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["migrate-v1", "plan", "--operation", "source.ingest"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["executable"] is False
    assert output["mutates_source"] is False


def test_lifecycle_doctor_reports_uninstalled_vault(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".obsidian").mkdir()
    source_root = Path(__file__).parents[2]

    assert (
        main(
            [
                "lifecycle",
                "--vault",
                str(tmp_path),
                "--source-root",
                str(source_root),
                "doctor",
            ]
        )
        == 2
    )
    output = json.loads(capsys.readouterr().out)
    assert output["installed"] is False
    assert output["issues"][0]["code"] == "not_installed"
