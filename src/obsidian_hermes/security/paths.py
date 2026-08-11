"""Fail-closed lexical and host filesystem path checks."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from obsidian_hermes.domain.errors import PathPolicyError

_GLOB_RE = re.compile(r"[*?[]")
_HOST_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_ALLOWED_ZONES = frozenset({"ReadWrite", "ReadOnly"})


@dataclass(frozen=True, slots=True)
class VaultPath:
    """A normalized worker-visible path that cannot name Private."""

    zone: str
    relative: PurePosixPath
    has_glob: bool = False

    @classmethod
    def parse(cls, value: str, *, allow_glob: bool = False) -> VaultPath:
        if not value or "\x00" in value or "\\" in value:
            raise PathPolicyError("vault paths must be non-empty POSIX paths")
        if "//" in value:
            raise PathPolicyError("empty vault path segments are not allowed")
        if unicodedata.normalize("NFC", value) != value:
            raise PathPolicyError("vault path must already be Unicode NFC normalized")
        if value.startswith("/") or _HOST_DRIVE_RE.match(value):
            raise PathPolicyError("absolute host or container paths are not resource paths")
        has_glob = _GLOB_RE.search(value) is not None
        if has_glob and not allow_glob:
            raise PathPolicyError("globs are not allowed for a concrete file operation")
        if has_glob and not value.endswith("/**"):
            raise PathPolicyError("only a terminal /** permission glob is supported")

        raw_parts = value.split("/")
        if any(part in {".", ".."} for part in raw_parts):
            raise PathPolicyError("dot segments and traversal are not allowed")
        if any(part.casefold() == ".git" for part in raw_parts):
            raise PathPolicyError("Git metadata paths are never worker-accessible")
        path = PurePosixPath(value)
        if len(path.parts) < 2 or path.parts[0] not in _ALLOWED_ZONES:
            raise PathPolicyError("path must begin with ReadWrite/ or ReadOnly/")
        if any(
            any(ord(character) < 32 or ord(character) == 127 for character in part)
            for part in raw_parts
        ):
            raise PathPolicyError("control characters are not allowed in vault paths")
        return cls(zone=path.parts[0], relative=PurePosixPath(*path.parts[1:]), has_glob=has_glob)

    def __str__(self) -> str:
        return f"{self.zone}/{self.relative.as_posix()}"


def resolve_existing(path: VaultPath, *, read_write_root: Path, read_only_root: Path) -> Path:
    """Resolve an existing concrete path while rejecting symlink and hard-link escapes.

    The opened-file no-follow primitive remains platform-specific and is a
    prerequisite for dispatch; this helper is suitable for validation and
    mount-boundary diagnostics only.
    """

    if path.has_glob:
        raise PathPolicyError("cannot resolve a permission glob as a concrete path")
    root = read_write_root if path.zone == "ReadWrite" else read_only_root
    if root.is_symlink():
        raise PathPolicyError(f"configured {path.zone} root must not be a symlink")
    root_resolved = root.resolve(strict=True)
    candidate = root_resolved
    for part in path.relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise PathPolicyError("symlink path components are not allowed")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root_resolved):
        raise PathPolicyError("resolved path escapes its configured access zone")
    stat = resolved.stat(follow_symlinks=False)
    if resolved.is_file() and stat.st_nlink > 1:
        raise PathPolicyError("hard-linked files are not accepted across access classes")
    return resolved


def verify_private_mask(path: Path) -> None:
    """Require an existing, empty, non-symlink directory for the worker mask."""

    if path.is_symlink():
        raise PathPolicyError("private mask must not be a symlink")
    if not path.is_dir():
        raise PathPolicyError("private mask must be an existing directory")
    try:
        next(path.iterdir())
    except StopIteration:
        return
    raise PathPolicyError("private mask must be empty")


def find_case_unicode_collisions(paths: list[str]) -> set[tuple[str, str]]:
    """Return path pairs that collide under Unicode normalization/case folding."""

    seen: dict[str, str] = {}
    collisions: set[tuple[str, str]] = set()
    for path in paths:
        key = unicodedata.normalize("NFC", path).casefold()
        previous = seen.get(key)
        if previous is not None and previous != path:
            collisions.add(tuple(sorted((previous, path))))
        else:
            seen[key] = path
    return collisions


def same_filesystem(left: Path, right: Path) -> bool:
    """Check the device boundary needed for atomic projection promotion."""

    return os.stat(left).st_dev == os.stat(right).st_dev
