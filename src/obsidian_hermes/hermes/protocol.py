"""Narrow bridge-to-Hermes port defined without runtime implementation guesses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ModelPin:
    provider: str
    model: str


@dataclass(frozen=True, slots=True)
class RuntimeDiscovery:
    hermes_home: str
    profile: str
    gateway_version: str
    gateway_available: bool
    cron_available: bool
    terminal_backend: str
    timezone: str
    models: tuple[ModelPin, ...]
    native_job_ids: tuple[str, ...]


class HermesRuntime(Protocol):
    """Only supported Hermes configuration/command interfaces belong here."""

    def discover(self) -> RuntimeDiscovery:
        """Discover effective runtime state without reading internal cron files."""
        ...

    def validate_native_mounts(self) -> None:
        """Inspect effective Docker mounts and raise on forbidden exposure."""
        ...
