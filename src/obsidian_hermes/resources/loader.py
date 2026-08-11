"""Resource loading facade used before reconciliation, routing, or dispatch."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

from obsidian_hermes.domain.errors import FrontmatterError, ResourceValidationError
from obsidian_hermes.resources.canonical import SPECIFICATION_SCHEMAS, specification_hash
from obsidian_hermes.resources.frontmatter import read_frontmatter
from obsidian_hermes.resources.validation import SchemaRegistry


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ResourceValidationError(f"duplicate JSON mapping key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class ResourceDocument:
    """A parsed and fully validated v2 resource."""

    metadata: Mapping[str, Any]
    body: str
    source: Path
    spec_hash: str | None


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(child) for child in value)
    return value


def load_resource(path: Path, *, registry: SchemaRegistry | None = None) -> ResourceDocument:
    """Load a Markdown or JSON resource and validate it against bundled schemas."""

    if path.suffix.casefold() == ".md":
        parsed = read_frontmatter(path)
        metadata = dict(parsed.metadata)
        body = parsed.body
    elif path.suffix.casefold() == ".json":
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
        except UnicodeDecodeError as error:
            raise FrontmatterError(f"{path} is not valid UTF-8") from error
        except json.JSONDecodeError as error:
            raise ResourceValidationError(f"invalid JSON resource {path}: {error}") from error
        if not isinstance(loaded, dict):
            raise ResourceValidationError("JSON resource root must be a mapping")
        metadata = cast(dict[str, Any], loaded)
        body = ""
    else:
        raise ResourceValidationError(f"unsupported resource extension: {path.suffix}")

    active_registry = registry or SchemaRegistry.bundled()
    active_registry.validate(metadata)

    if metadata["schema"] in SPECIFICATION_SCHEMAS:
        digest = specification_hash(metadata, body=body)
    else:
        digest = None
    return ResourceDocument(
        metadata=_freeze(metadata),
        body=body,
        source=path,
        spec_hash=digest,
    )
