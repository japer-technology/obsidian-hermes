from pathlib import Path

import pytest

from obsidian_hermes.domain.errors import FrontmatterError
from obsidian_hermes.resources.frontmatter import parse_frontmatter


def test_parses_frontmatter_and_keeps_timestamp_as_string() -> None:
    document = parse_frontmatter(
        "---\nschema: hermes.task/v2\ncreated_at: 2026-08-11T03:09:00Z\n---\n# Goal\r\n"
    )

    assert document.metadata["created_at"] == "2026-08-11T03:09:00Z"
    assert document.body == "# Goal\r\n"


@pytest.mark.parametrize(
    "text, message",
    [
        ("schema: hermes.task/v2\n", "must begin"),
        ("---\nschema: hermes.task/v2\n", "not terminated"),
        ("---\n---\n", "cannot be empty"),
        ("---\na: 1\na: 2\n---\n", "duplicate mapping key"),
        ("---\na: &value 1\nb: *value\n---\n", "aliases and anchors"),
        ("---\na: !custom value\n---\n", "explicit YAML tags"),
        ("---\na: 1\n...\n---\n", "multiple YAML documents"),
        ("---\n1: value\n---\n", "keys must be strings"),
    ],
)
def test_rejects_unsafe_frontmatter(text: str, message: str) -> None:
    with pytest.raises(FrontmatterError, match=message):
        parse_frontmatter(text)


def test_rejects_invalid_utf8() -> None:
    with pytest.raises(FrontmatterError, match="not valid UTF-8"):
        parse_frontmatter(b"---\nvalue: \xff\n---\n", source=Path("bad.md"))


def test_markdown_body_may_contain_thematic_rules() -> None:
    document = parse_frontmatter("---\nschema: hermes.task/v2\n---\n---\nBody\n---\n")

    assert document.body == "---\nBody\n---\n"
