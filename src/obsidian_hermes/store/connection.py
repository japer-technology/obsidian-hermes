"""Connection and transaction primitives for the operational SQLite store."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

TransactionMode = Literal["DEFERRED", "IMMEDIATE", "EXCLUSIVE"]
_TRANSACTION_MODES = frozenset({"DEFERRED", "IMMEDIATE", "EXCLUSIVE"})


class StoreConfigurationError(RuntimeError):
    """Raised when SQLite cannot provide the required safety settings."""


class TransactionError(RuntimeError):
    """Raised when an explicit transaction cannot be started safely."""


def open_database(
    path: str | Path,
    *,
    busy_timeout_ms: int = 5_000,
) -> sqlite3.Connection:
    """Open a file-backed operational database with fail-closed pragmas.

    Autocommit is enabled at the driver boundary (``isolation_level=None``) so
    every state transition must opt into :func:`transaction`.  In-memory and
    URI databases are deliberately rejected: the v2 operational store is a
    durable, profile-scoped file which must be backed up alongside the vault.
    """

    path_text = str(path)
    if path_text == ":memory:" or path_text.startswith("file:"):
        raise StoreConfigurationError(
            "the operational store must be a file-backed database, not memory or URI"
        )
    if busy_timeout_ms < 0:
        raise ValueError("busy_timeout_ms must be non-negative")

    database_path = Path(path_text)
    if not database_path.parent.exists():
        raise StoreConfigurationError(
            f"database parent directory does not exist: {database_path.parent}"
        )

    connection = sqlite3.connect(
        database_path,
        timeout=busy_timeout_ms / 1_000,
        isolation_level=None,
        check_same_thread=True,
    )
    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
        connection.execute("PRAGMA wal_autocheckpoint = 1000")
        connection.execute("PRAGMA trusted_schema = OFF")

        if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise StoreConfigurationError("SQLite foreign-key enforcement is unavailable")
        if str(journal_mode).lower() != "wal":
            raise StoreConfigurationError(
                f"SQLite refused WAL journaling (effective mode: {journal_mode!r})"
            )
        # SQLite reports FULL as the integer value 2.
        if connection.execute("PRAGMA synchronous").fetchone()[0] != 2:
            raise StoreConfigurationError("SQLite refused FULL synchronous mode")
    except BaseException:
        connection.close()
        raise

    return connection


@contextmanager
def transaction(
    connection: sqlite3.Connection,
    mode: TransactionMode = "IMMEDIATE",
) -> Iterator[sqlite3.Connection]:
    """Run one explicit, non-nested SQLite transaction.

    ``IMMEDIATE`` is the default because bridge state changes and claims are
    write transactions.  Refusing accidental nesting keeps event/state writes
    inside one clearly owned transaction rather than silently committing an
    inner unit of work.
    """

    if mode not in _TRANSACTION_MODES:
        raise ValueError(f"unsupported transaction mode: {mode!r}")
    if connection.in_transaction:
        raise TransactionError("nested operational-store transactions are not allowed")

    connection.execute(f"BEGIN {mode}")
    try:
        yield connection
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    else:
        if not connection.in_transaction:
            raise TransactionError("transaction ended before the unit of work completed")
        connection.commit()
