"""Install and maintain the vault-facing Obsidian Hermes capabilities.

The lifecycle manager intentionally owns only files that it records in its
manifest.  Vault Markdown is seeded once, then remains user-owned.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path, PurePosixPath
from typing import Any

from obsidian_hermes import __version__
from obsidian_hermes.domain.errors import LifecycleError

_STATE_DIRECTORY = ".obsidian-hermes"
_MANIFEST_NAME = "installation.json"
_PLUGIN_ID = "agent-control-room"
_PLUGIN_FILES = ("manifest.json", "main.js", "styles.css")
_MANIFEST_VERSION = 1
_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _digest(content: bytes) -> str:
    return f"sha256:{sha256(content).hexdigest()}"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _safe_relative(value: str) -> Path:
    if "\\" in value or "\x00" in value or ":" in value:
        raise LifecycleError(f"unsafe managed path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or not value or any(part in {"", ".", ".."} for part in path.parts):
        raise LifecycleError(f"unsafe managed path: {value!r}")
    return Path(*path.parts)


@dataclass(frozen=True, slots=True)
class ManagedFile:
    relative_path: str
    content: bytes

    @property
    def digest(self) -> str:
        return _digest(self.content)


class LifecycleManager:
    """Manage an Obsidian-vault installation without taking ownership of notes."""

    def __init__(self, *, vault: Path, source_root: Path | None = None) -> None:
        self.vault = vault.absolute()
        if source_root is not None:
            self.source_root: Path | Traversable = source_root.resolve(strict=False)
        else:
            bundled = resources.files(__package__).joinpath("assets")
            self.source_root = bundled if bundled.is_dir() else Path(__file__).parents[3]

    @staticmethod
    def _artifact_path(filename: str) -> str:
        return (Path(".obsidian") / "plugins" / _PLUGIN_ID / filename).as_posix()

    def _vault_path(self, relative_path: str) -> Path:
        """Resolve a controlled vault-relative path without traversing symlinks."""

        relative = _safe_relative(relative_path)
        current = self.vault
        if current.is_symlink():
            raise LifecycleError(f"vault root must not be a symlink: {current}")
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise LifecycleError(f"managed path contains a symlink: {current}")
        return current

    @property
    def state_directory(self) -> Path:
        return self._vault_path(_STATE_DIRECTORY)

    @property
    def manifest_path(self) -> Path:
        return self._vault_path(f"{_STATE_DIRECTORY}/{_MANIFEST_NAME}")

    def _ensure_vault(self) -> None:
        if not self.vault.is_dir():
            raise LifecycleError(f"vault directory does not exist: {self.vault}")
        if not (self.vault / ".obsidian").is_dir():
            raise LifecycleError(f"not an Obsidian vault (missing .obsidian): {self.vault}")

    def _source_file(self, relative: Path) -> Traversable:
        path: Traversable = self.source_root
        for part in relative.parts:
            path = path.joinpath(part)
        if not path.is_file():
            raise LifecycleError(f"release artifact is missing: {path}")
        return path

    def _source_tree_files(self, root: Traversable) -> Iterator[tuple[PurePosixPath, Traversable]]:
        """Yield files from either an on-disk checkout or packaged resources."""

        def visit(
            directory: Traversable, relative: PurePosixPath
        ) -> Iterator[tuple[PurePosixPath, Traversable]]:
            for child in sorted(directory.iterdir(), key=lambda entry: entry.name):
                child_relative = relative / child.name
                if child.is_file():
                    yield child_relative, child
                elif child.is_dir():
                    yield from visit(child, child_relative)

        yield from visit(root, PurePosixPath())

    def _managed_files(self) -> tuple[ManagedFile, ...]:
        return tuple(
            ManagedFile(
                relative_path=self._artifact_path(filename),
                content=self._source_file(Path("apps") / "obsidian-hermes" / filename).read_bytes(),
            )
            for filename in _PLUGIN_FILES
        )

    def _load_manifest(self, *, required: bool) -> dict[str, Any] | None:
        if not self.manifest_path.exists():
            if required:
                raise LifecycleError(
                    "no Obsidian Hermes installation manifest at "
                    f"{self.manifest_path}; run install first"
                )
            return None
        try:
            value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LifecycleError(f"cannot read installation manifest: {error}") from error
        if not isinstance(value, dict) or value.get("manifest_version") != _MANIFEST_VERSION:
            raise LifecycleError("installation manifest has an unsupported format")
        if value.get("plugin_id") != _PLUGIN_ID:
            raise LifecycleError("installation manifest belongs to a different plugin")
        artifacts = value.get("artifacts")
        expected_paths = {self._artifact_path(filename) for filename in _PLUGIN_FILES}
        if not isinstance(artifacts, dict) or not all(
            isinstance(path, str)
            and isinstance(digest, str)
            and _SHA256.fullmatch(digest) is not None
            for path, digest in artifacts.items()
        ):
            raise LifecycleError("installation manifest has invalid artifact records")
        if set(artifacts) != expected_paths:
            raise LifecycleError("installation manifest has an unexpected managed artifact set")
        seeded = value.get("seeded")
        if not isinstance(seeded, list) or not all(isinstance(path, str) for path in seeded):
            raise LifecycleError("installation manifest has invalid seeded-file records")
        for path in seeded:
            _safe_relative(path)
        if not isinstance(value.get("installed_version"), str):
            raise LifecycleError("installation manifest has no installed version")
        return value

    def _write_atomic(self, target: Path, content: bytes) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, raw_temporary = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".obsidian-hermes-tmp", dir=target.parent
        )
        temporary = Path(raw_temporary)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _backup(self, relative_path: str, target: Path) -> str | None:
        if not target.is_file():
            return None
        backup = self._vault_path(f"{_STATE_DIRECTORY}/backups/{_timestamp()}/{relative_path}")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        return backup.relative_to(self.vault).as_posix()

    def _write_manifest(self, *, artifacts: tuple[ManagedFile, ...], seeded: list[str]) -> None:
        payload = {
            "manifest_version": _MANIFEST_VERSION,
            "installed_version": __version__,
            "plugin_id": _PLUGIN_ID,
            "artifacts": {file.relative_path: file.digest for file in artifacts},
            "seeded": seeded,
        }
        self._write_atomic(
            self.manifest_path,
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )

    def _seed_reference_vault(self) -> list[str]:
        root = self.source_root.joinpath("reference-vault")
        if not root.is_dir():
            return []
        seeded: list[str] = []
        for relative, source in self._source_tree_files(root):
            target = self._vault_path(relative.as_posix())
            if target.exists():
                continue
            self._write_atomic(target, source.read_bytes())
            seeded.append(relative.as_posix())
        return seeded

    def install(self, *, force: bool = False) -> dict[str, Any]:
        """Install assets and seed missing reference notes without replacing user notes."""

        self._ensure_vault()
        if self._load_manifest(required=False) is not None:
            return self.update()
        artifacts = self._managed_files()
        conflicts: list[str] = []
        for file in artifacts:
            target = self._vault_path(file.relative_path)
            if target.exists() and not target.is_file():
                raise LifecycleError(f"managed artifact is not a regular file: {target}")
            if target.is_file() and target.read_bytes() != file.content:
                conflicts.append(file.relative_path)
        if conflicts and not force:
            raise LifecycleError(
                "refusing to replace unmanaged plugin files; rerun with --force to back them up "
                "and adopt: " + ", ".join(conflicts)
            )
        backups: list[str] = []
        changed: list[str] = []
        for file in artifacts:
            target = self._vault_path(file.relative_path)
            if target.is_file() and target.read_bytes() == file.content:
                continue
            if target.is_file():
                backup = self._backup(file.relative_path, target)
                if backup is not None:
                    backups.append(backup)
            self._write_atomic(target, file.content)
            changed.append(file.relative_path)
        seeded = self._seed_reference_vault()
        self._write_manifest(artifacts=artifacts, seeded=seeded)
        return {
            "operation": "install",
            "changed": changed,
            "seeded": seeded,
            "backups": backups,
        }

    def update(self) -> dict[str, Any]:
        """Update known managed assets, preserving a backup of every replacement."""

        self._ensure_vault()
        manifest = self._load_manifest(required=True)
        assert manifest is not None
        artifacts = self._managed_files()
        changed: list[str] = []
        backups: list[str] = []
        for file in artifacts:
            target = self._vault_path(file.relative_path)
            if target.is_file() and target.read_bytes() == file.content:
                continue
            if target.exists() and not target.is_file():
                raise LifecycleError(f"managed artifact is not a regular file: {target}")
            backup = self._backup(file.relative_path, target)
            if backup is not None:
                backups.append(backup)
            self._write_atomic(target, file.content)
            changed.append(file.relative_path)
        seeded = self._seed_reference_vault()
        self._write_manifest(artifacts=artifacts, seeded=list(manifest["seeded"]) + seeded)
        return {"operation": "update", "changed": changed, "seeded": seeded, "backups": backups}

    def repair(self) -> dict[str, Any]:
        """Restore missing or changed managed assets, keeping a backup of changed files."""

        self._ensure_vault()
        manifest = self._load_manifest(required=True)
        assert manifest is not None
        artifacts = self._managed_files()
        repaired: list[str] = []
        backups: list[str] = []
        for file in artifacts:
            target = self._vault_path(file.relative_path)
            if target.is_file() and target.read_bytes() == file.content:
                continue
            if target.exists() and not target.is_file():
                raise LifecycleError(f"managed artifact is not a regular file: {target}")
            backup = self._backup(file.relative_path, target)
            if backup is not None:
                backups.append(backup)
            self._write_atomic(target, file.content)
            repaired.append(file.relative_path)
        self._write_manifest(artifacts=artifacts, seeded=list(manifest["seeded"]))
        return {"operation": "repair", "repaired": repaired, "backups": backups}

    def doctor(self) -> tuple[dict[str, Any], bool]:
        """Report installation health without making any changes."""

        issues: list[dict[str, str]] = []
        if not self.vault.is_dir():
            issues.append(
                {
                    "code": "vault_missing",
                    "message": f"vault directory does not exist: {self.vault}",
                }
            )
        elif not (self.vault / ".obsidian").is_dir():
            issues.append(
                {"code": "obsidian_missing", "message": "vault has no .obsidian directory"}
            )
        manifest: dict[str, Any] | None = None
        try:
            manifest = self._load_manifest(required=False)
        except LifecycleError as error:
            issues.append({"code": "manifest_invalid", "message": str(error)})
        if manifest is None and not issues:
            issues.append(
                {"code": "not_installed", "message": "no Obsidian Hermes installation manifest"}
            )
        if manifest is not None:
            for relative_path, expected in sorted(manifest["artifacts"].items()):
                try:
                    target = self._vault_path(relative_path)
                except LifecycleError as error:
                    issues.append({"code": "artifact_unsafe", "message": str(error)})
                    continue
                if not target.is_file():
                    issues.append({"code": "artifact_missing", "message": relative_path})
                elif _digest(target.read_bytes()) != expected:
                    issues.append({"code": "artifact_changed", "message": relative_path})
        source_issues: list[dict[str, str]] = []
        try:
            current_artifacts = self._managed_files()
        except LifecycleError as error:
            source_issues.append({"code": "release_artifact_missing", "message": str(error)})
            current_artifacts = ()
        updates_available = (
            manifest is not None
            and {file.relative_path: file.digest for file in current_artifacts}
            != manifest["artifacts"]
        )
        issues.extend(source_issues)
        return (
            {
                "operation": "doctor",
                "vault": str(self.vault),
                "installed": manifest is not None,
                "healthy": not issues,
                "updates_available": updates_available,
                "issues": issues,
            },
            not issues,
        )

    def uninstall(self, *, purge_state: bool = False) -> dict[str, Any]:
        """Remove only unmodified tracked assets; never remove seeded vault content."""

        self._ensure_vault()
        manifest = self._load_manifest(required=True)
        assert manifest is not None
        removed: list[str] = []
        preserved: list[str] = []
        for relative_path, expected in sorted(manifest["artifacts"].items()):
            target = self._vault_path(relative_path)
            if not target.exists():
                continue
            if not target.is_file() or _digest(target.read_bytes()) != expected:
                preserved.append(relative_path)
                continue
            target.unlink()
            removed.append(relative_path)
        if not preserved:
            self.manifest_path.unlink(missing_ok=True)
        state_purged = False
        if purge_state and not preserved:
            backup_root = self._vault_path(f"{_STATE_DIRECTORY}/backups")
            if backup_root.exists():
                shutil.rmtree(backup_root)
            with suppress(OSError):
                self.state_directory.rmdir()
            state_purged = not self.state_directory.exists()
        return {
            "operation": "uninstall",
            "removed": removed,
            "preserved": preserved,
            "state_purged": state_purged,
        }
