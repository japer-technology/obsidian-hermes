"""Strict YAML frontmatter profile for v2 Markdown resources."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode
from yaml.tokens import AliasToken, AnchorToken, DocumentEndToken, DocumentStartToken, TagToken

from obsidian_hermes.domain.errors import FrontmatterError

_TIMESTAMP_TAG: Final = "tag:yaml.org,2002:timestamp"


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader variant that retains timestamps as RFC 3339 strings."""


_StrictSafeLoader.yaml_implicit_resolvers = {
    key: [entry for entry in entries if entry[0] != _TIMESTAMP_TAG]
    for key, entries in copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers).items()
}


def _construct_mapping(
    loader: _StrictSafeLoader, node: MappingNode, deep: bool = False
) -> dict[str, Any]:
    loader.flatten_mapping(node)
    result: dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "frontmatter mapping keys must be strings",
                key_node.start_mark,
            )
        if key in result:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate mapping key: {key}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True, slots=True)
class FrontmatterDocument:
    """One parsed Markdown resource before JSON Schema validation."""

    metadata: Mapping[str, Any]
    body: str
    source: Path | None = None


def _decode_utf8(content: bytes, source: Path | None) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as error:
        label = str(source) if source else "resource"
        raise FrontmatterError(f"{label} is not valid UTF-8") from error


def parse_frontmatter(content: bytes | str, *, source: Path | None = None) -> FrontmatterDocument:
    """Parse exactly one leading, safe YAML frontmatter document.

    Aliases and anchors are rejected together so a later edit cannot activate a
    previously inert anchor. Explicit tags are rejected, including YAML's
    standard tags, to keep the accepted scalar profile unambiguous.
    """

    text = _decode_utf8(content, source) if isinstance(content, bytes) else content
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise FrontmatterError("resource must begin with a YAML frontmatter delimiter")

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            closing_index = index
            break
    if closing_index is None:
        raise FrontmatterError("leading YAML frontmatter is not terminated")

    yaml_text = "".join(lines[1:closing_index])
    if not yaml_text.strip():
        raise FrontmatterError("leading YAML frontmatter cannot be empty")

    try:
        for token in yaml.scan(yaml_text, Loader=_StrictSafeLoader):
            if isinstance(token, (AliasToken, AnchorToken)):
                raise FrontmatterError("YAML aliases and anchors are not allowed")
            if isinstance(token, TagToken):
                raise FrontmatterError("explicit YAML tags are not allowed")
            if isinstance(token, (DocumentStartToken, DocumentEndToken)):
                raise FrontmatterError("multiple YAML documents are not allowed")
        loaded = yaml.load(yaml_text, Loader=_StrictSafeLoader)
    except FrontmatterError:
        raise
    except yaml.YAMLError as error:
        problem = getattr(error, "problem", "")
        if "duplicate mapping key" in problem:
            detail = "duplicate mapping key"
        elif "mapping keys must be strings" in problem:
            detail = "frontmatter mapping keys must be strings"
        else:
            mark = getattr(error, "problem_mark", None)
            detail = (
                f"syntax error at line {mark.line + 1}, column {mark.column + 1}"
                if mark is not None
                else "syntax error"
            )
        raise FrontmatterError(f"invalid YAML frontmatter: {detail}") from error

    if not isinstance(loaded, dict):
        raise FrontmatterError("frontmatter root must be a mapping")

    metadata = cast(dict[str, Any], loaded)
    body = "".join(lines[closing_index + 1 :])
    return FrontmatterDocument(metadata=metadata, body=body, source=source)


def read_frontmatter(path: Path) -> FrontmatterDocument:
    """Read and parse a Markdown resource without following an alternate path API."""

    return parse_frontmatter(path.read_bytes(), source=path)
