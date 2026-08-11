"""Read-only startup and rescan loop for the pre-alpha bridge scaffold."""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from obsidian_hermes.config import DeploymentConfig
from obsidian_hermes.domain.errors import PathPolicyError, SafetyBlock
from obsidian_hermes.resources.loader import load_resource
from obsidian_hermes.resources.validation import SchemaRegistry
from obsidian_hermes.security.paths import find_case_unicode_collisions, verify_private_mask

_RESOURCE_DIRECTORIES: Mapping[str, str] = {
    "30 Knowledge/raw": "hermes.raw-source/v2",
    "50 Agents": "hermes.agent/v2",
    "60 Skills": "hermes.skill/v2",
    "70 Tasks": "hermes.task/v2",
    "80 Runs": "hermes.run/v2",
    "90 Automations": "hermes.routine/v2",
    "95 Approvals": "hermes.approval/v2",
    "99 Control": "hermes.control/v2",
    "99 System/Receipts": "hermes.receipt/v2",
    "99 System/State": "hermes.status/v2",
    "99 System/Logs": "hermes.event/v2",
}
_SYNC_CONFLICT_MARKERS = ("conflicted copy", "sync-conflict", "sync conflict")


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    scanned: int
    valid: int
    issues: tuple[ValidationIssue, ...]

    @property
    def safe(self) -> bool:
        return not self.issues


class ValidationOnlyBridge:
    """A model-free full-rescan loop that performs no reconciliation writes."""

    def __init__(self, config: DeploymentConfig) -> None:
        if config.bridge.dispatch_enabled or not config.bridge.validation_only:
            raise SafetyBlock(
                "this scaffold supports validation-only operation; dispatch remains disabled"
            )
        self._config = config
        self._registry = SchemaRegistry.bundled()

    def verify_static_boundaries(self) -> None:
        for zone in (
            self._config.vault.read_write_root,
            self._config.vault.read_only_root,
        ):
            if zone.is_symlink() or not zone.is_dir():
                raise PathPolicyError(f"configured vault zone is unavailable or a symlink: {zone}")
        verify_private_mask(self._config.vault.private_mask_root)

        expected_policy = self._config.vault.read_only_root / "Policies"
        if self._config.bridge.policy_directory.resolve(strict=False) != expected_policy.resolve(
            strict=False
        ):
            raise PathPolicyError("trusted policy directory must be ReadOnly/Policies")
        for policy in ("AGENTS.md", "SCHEMA.md"):
            path = expected_policy / policy
            if path.is_symlink() or not path.is_file():
                raise PathPolicyError(f"trusted policy is missing or a symlink: {path}")

    def scan_once(self) -> ValidationReport:
        self.verify_static_boundaries()
        issues: list[ValidationIssue] = []
        candidates: list[tuple[Path, str]] = []
        file_limit_reached = False
        seen_entries = 0
        for directory, expected_schema in _RESOURCE_DIRECTORIES.items():
            root = self._config.vault.read_only_root / directory
            if not root.is_dir():
                issues.append(ValidationIssue(str(root), "required resource directory is missing"))
                continue
            if root.is_symlink():
                issues.append(
                    ValidationIssue(str(root), "resource directory must not be a symlink")
                )
                continue
            if file_limit_reached:
                continue
            for path in root.rglob("*"):
                seen_entries += 1
                if seen_entries > self._config.limits.max_files_per_scan:
                    issues.append(
                        ValidationIssue(
                            str(self._config.vault.read_only_root),
                            "resource tree exceeds the configured entry-count limit",
                        )
                    )
                    file_limit_reached = True
                    break
                if path.is_symlink():
                    issues.append(ValidationIssue(str(path), "resource tree contains a symlink"))
                    continue
                if not path.is_file():
                    continue
                if path.suffix.casefold() in {".md", ".json"}:
                    candidates.append((path, expected_schema))

        relative_names = [
            path.relative_to(self._config.vault.read_only_root).as_posix()
            for path, _expected_schema in candidates
        ]
        for left, right in find_case_unicode_collisions(relative_names):
            issues.append(ValidationIssue(left, f"case/Unicode collision with {right}"))

        valid = 0
        for path, expected_schema in sorted(candidates):
            relative = path.relative_to(self._config.vault.read_only_root).as_posix()
            if any(marker in path.name.casefold() for marker in _SYNC_CONFLICT_MARKERS):
                issues.append(ValidationIssue(relative, "synchronisation conflict requires review"))
                continue
            if path.stat(follow_symlinks=False).st_size > self._config.limits.max_resource_bytes:
                issues.append(
                    ValidationIssue(relative, "resource exceeds the configured size limit")
                )
                continue
            try:
                document = load_resource(path, registry=self._registry)
                if document.metadata["schema"] != expected_schema:
                    issues.append(
                        ValidationIssue(
                            relative,
                            f"resource schema does not belong in {path.parent.name}",
                        )
                    )
                    continue
            except Exception as error:
                issues.append(
                    ValidationIssue(
                        relative,
                        f"{type(error).__name__}: resource rejected by strict validation",
                    )
                )
            else:
                valid += 1

        return ValidationReport(scanned=len(candidates), valid=valid, issues=tuple(issues))

    def run_forever(self) -> None:
        """Rescan periodically until interrupted; filesystem notifications are pending."""

        while True:
            report = self.scan_once()
            if not report.safe:
                details = "; ".join(f"{issue.path}: {issue.message}" for issue in report.issues)
                raise SafetyBlock(f"validation-only bridge blocked: {details}")
            time.sleep(self._config.bridge.reconcile_interval_seconds)
