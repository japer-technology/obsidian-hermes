"""Validation-only runtime discovery descriptors.

This module deliberately contains no process spawning, credentials, network
clients, or dispatch behaviour.  Runtime adapters can implement the catalog
port later without widening the read-only API boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ports import JsonObject, RuntimeDescriptor


def unavailable_pricing() -> JsonObject:
    """Return an explicit unknown-price record instead of inventing a price."""

    return {
        "currency": "USD",
        "unit": "per_1m_tokens",
        "input": None,
        "cached_input": None,
        "output": None,
        "status": "unavailable",
        "as_of": None,
        "source": None,
    }


@dataclass(frozen=True, slots=True)
class StaticRuntimeCatalog:
    """A dependency-free runtime catalog suitable for local configuration."""

    runtimes: tuple[RuntimeDescriptor, ...]

    def list_runtimes(self) -> tuple[RuntimeDescriptor, ...]:
        return self.runtimes


def validation_only_runtime_catalog(
    *, hermes_profile: str = "default", include_openclaw: bool = True
) -> StaticRuntimeCatalog:
    """Describe scaffolded runtimes while making non-execution unambiguous."""

    descriptors = [
        RuntimeDescriptor(
            runtime_id=f"hermes:{hermes_profile}",
            runtime_type="hermes",
            display_name="Hermes Agent",
            profile=hermes_profile,
            capabilities=(
                "read_status",
                "read_model_catalog",
                "supports_tasks",
                "supports_routines",
            ),
            health="validation_only",
            validation_only=True,
            details={"adapter": "not_configured", "dispatch_enabled": False},
        )
    ]
    if include_openclaw:
        descriptors.append(
            RuntimeDescriptor(
                runtime_id="openclaw:default",
                runtime_type="openclaw",
                display_name="OpenClaw",
                profile="default",
                capabilities=(
                    "read_status",
                    "read_model_catalog",
                    "supports_tasks",
                    "supports_routines",
                ),
                health="unconfigured",
                validation_only=True,
                details={"adapter": "not_configured", "dispatch_enabled": False},
            )
        )
    return StaticRuntimeCatalog(tuple(descriptors))


class NoRepositoryProvenance:
    """Default Git port: provenance is unavailable rather than guessed."""

    def read_repository_provenance(self) -> JsonObject | None:
        return None
