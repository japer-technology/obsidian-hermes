from datetime import UTC, datetime

import pytest

from obsidian_hermes.domain.ids import new_id, source_id, validate_id


def test_generates_valid_typed_ulid() -> None:
    identifier = new_id("task", at=datetime(2026, 8, 11, tzinfo=UTC))

    assert identifier.startswith("task_")
    assert len(identifier) == len("task_") + 26
    assert validate_id(identifier, prefix="task")
    assert not validate_id(identifier, prefix="run")


def test_rejects_unknown_system_prefix() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        new_id("job")


def test_rejects_ulid_that_overflows_128_bits() -> None:
    assert not validate_id("task_8" + "0" * 25, prefix="task")


def test_source_identity_is_content_derived() -> None:
    identifier = source_id(b"source bytes")

    assert identifier == (
        "src_sha256_"
        "4d4823794cbed3c4ee0bbc684c8f66e1dfd5afa6f078d494ce254ec5a4671753"
    )
    assert validate_id(identifier)
