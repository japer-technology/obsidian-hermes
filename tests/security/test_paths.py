import os
from pathlib import Path

import pytest

from obsidian_hermes.domain.errors import PathPolicyError
from obsidian_hermes.security.paths import (
    VaultPath,
    find_case_unicode_collisions,
    resolve_existing,
    verify_private_mask,
)


@pytest.mark.parametrize(
    "value",
    [
        "../Private/secret.md",
        "ReadOnly/../Private/secret.md",
        "ReadOnly/Projects/./secret.md",
        "/etc/passwd",
        "C:/Users/example/secret.txt",
        "Private/secret.md",
        "ReadWrite\\note.md",
        "ReadWrite/e\u0301.md",
        "ReadWrite/.git/config",
        "ReadWrite/.GIT/config",
    ],
)
def test_rejects_escape_and_ambiguous_paths(value: str) -> None:
    with pytest.raises(PathPolicyError):
        VaultPath.parse(value)


def test_permission_globs_are_explicit() -> None:
    with pytest.raises(PathPolicyError, match="globs"):
        VaultPath.parse("ReadOnly/10 Projects/**")
    parsed = VaultPath.parse("ReadOnly/10 Projects/**", allow_glob=True)
    assert parsed.has_glob


def test_private_mask_must_be_empty(tmp_path: Path) -> None:
    verify_private_mask(tmp_path)
    (tmp_path / "visible.txt").write_text("must not be visible", encoding="utf-8")
    with pytest.raises(PathPolicyError, match="empty"):
        verify_private_mask(tmp_path)


def test_detects_case_and_unicode_collisions() -> None:
    collisions = find_case_unicode_collisions(
        ["ReadOnly/Project.md", "readonly/project.md", "ReadWrite/café.md", "ReadWrite/cafe.md"]
    )
    assert ("ReadOnly/Project.md", "readonly/project.md") in collisions


@pytest.mark.skipif(os.name == "nt", reason="symlink creation requires platform policy on Windows")
def test_resolution_rejects_symlink_components(tmp_path: Path) -> None:
    read_write = tmp_path / "ReadWrite"
    read_only = tmp_path / "ReadOnly"
    outside = tmp_path / "outside"
    read_write.mkdir()
    read_only.mkdir()
    outside.mkdir()
    (outside / "secret.md").write_text("secret", encoding="utf-8")
    (read_only / "link").symlink_to(outside, target_is_directory=True)

    with pytest.raises(PathPolicyError, match="symlink"):
        resolve_existing(
            VaultPath.parse("ReadOnly/link/secret.md"),
            read_write_root=read_write,
            read_only_root=read_only,
        )
