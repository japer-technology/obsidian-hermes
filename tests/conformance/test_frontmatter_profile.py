from pathlib import Path

import pytest

from obsidian_hermes.domain.errors import FrontmatterError
from obsidian_hermes.resources.frontmatter import read_frontmatter

INVALID = Path(__file__).parents[1] / "fixtures" / "v2" / "invalid"


@pytest.mark.parametrize("path", sorted(INVALID.glob("*.md")), ids=lambda path: path.name)
def test_unsafe_yaml_fixtures_are_rejected(path: Path) -> None:
    with pytest.raises(FrontmatterError):
        read_frontmatter(path)
