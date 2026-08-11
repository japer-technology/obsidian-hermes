"""Bundled executable schemas for Obsidian Hermes resources."""

from collections.abc import Mapping
from importlib.resources import files
from importlib.resources.abc import Traversable
from types import MappingProxyType
from typing import Final

COMMON_SCHEMA_FILENAME: Final = "common.schema.json"
SCHEMA_FILENAMES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "hermes.task/v2": "hermes.task-v2.schema.json",
        "hermes.run/v2": "hermes.run-v2.schema.json",
        "hermes.routine/v2": "hermes.routine-v2.schema.json",
        "hermes.control/v2": "hermes.control-v2.schema.json",
        "hermes.approval/v2": "hermes.approval-v2.schema.json",
        "hermes.agent/v2": "hermes.agent-v2.schema.json",
        "hermes.skill/v2": "hermes.skill-v2.schema.json",
        "hermes.raw-source/v2": "hermes.raw-source-v2.schema.json",
        "hermes.receipt/v2": "hermes.receipt-v2.schema.json",
        "hermes.status/v2": "hermes.status-v2.schema.json",
        "hermes.event/v2": "hermes.event-v2.schema.json",
    }
)
ALL_SCHEMA_FILENAMES: Final[tuple[str, ...]] = (
    COMMON_SCHEMA_FILENAME,
    *SCHEMA_FILENAMES.values(),
)


def schema_resource(schema_name: str) -> Traversable:
    """Return the package resource for a registered v2 schema."""

    try:
        filename = SCHEMA_FILENAMES[schema_name]
    except KeyError as exc:
        raise KeyError(f"unknown Hermes schema: {schema_name}") from exc
    return files("obsidian_hermes.schemas").joinpath(filename)


__all__ = [
    "ALL_SCHEMA_FILENAMES",
    "COMMON_SCHEMA_FILENAME",
    "SCHEMA_FILENAMES",
    "schema_resource",
]
