"""Typed Crockford ULID and content-derived identifier helpers."""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from datetime import datetime
from typing import Final

CROCKFORD_ALPHABET: Final = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
SYSTEM_PREFIXES: Final = frozenset(
    {"task", "cmd", "run", "control", "approval", "receipt", "event", "trace", "span"}
)
SYSTEM_ID_RE: Final = re.compile(
    rf"^(?P<prefix>{'|'.join(sorted(SYSTEM_PREFIXES))})_[0-7][{CROCKFORD_ALPHABET}]{{25}}$"
)
CATALOGUE_ID_RE: Final = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SOURCE_ID_RE: Final = re.compile(r"^src_sha256_[0-9a-f]{64}$")


def _encode_crockford(value: int, length: int) -> str:
    chars = ["0"] * length
    for index in range(length - 1, -1, -1):
        value, remainder = divmod(value, 32)
        chars[index] = CROCKFORD_ALPHABET[remainder]
    if value:
        raise ValueError("value does not fit the requested Crockford width")
    return "".join(chars)


def new_id(prefix: str, *, at: datetime | None = None) -> str:
    """Create a typed ULID using a 48-bit millisecond time and 80 random bits."""

    if prefix not in SYSTEM_PREFIXES:
        raise ValueError(f"unsupported system identifier prefix: {prefix}")

    timestamp_ms = int(at.timestamp() * 1000) if at is not None else time.time_ns() // 1_000_000
    if not 0 <= timestamp_ms < 2**48:
        raise ValueError("ULID timestamp is outside the 48-bit range")

    value = (timestamp_ms << 80) | secrets.randbits(80)
    return f"{prefix}_{_encode_crockford(value, 26)}"


def source_id(content: bytes) -> str:
    """Return the immutable identity of exact raw source bytes."""

    return f"src_sha256_{hashlib.sha256(content).hexdigest()}"


def validate_id(value: str, *, prefix: str | None = None) -> bool:
    """Return whether *value* is a known typed ID, catalogue slug, or source ID."""

    system_match = SYSTEM_ID_RE.fullmatch(value)
    if system_match:
        return prefix is None or system_match.group("prefix") == prefix
    if prefix is not None:
        return False
    return SOURCE_ID_RE.fullmatch(value) is not None or CATALOGUE_ID_RE.fullmatch(value) is not None
