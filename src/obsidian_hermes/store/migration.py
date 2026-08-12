"""Ordered, checksum-verified migrations packaged with the store."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from importlib import resources
from importlib.resources.abc import Traversable

from .connection import transaction

_MIGRATION_NAME = re.compile(
    r"^(?P<version>[0-9]{4})_(?P<name>[a-z][a-z0-9_]*)\.(?P<direction>up|down)\.sql$"
)
_MIGRATIONS_PACKAGE = f"{__package__}.migrations"


class MigrationError(RuntimeError):
    """Raised for an invalid migration set or migration state."""


class MigrationChecksumError(MigrationError):
    """Raised when an already-applied migration no longer matches its source."""


@dataclass(frozen=True, slots=True)
class Migration:
    """One reversible packaged schema migration."""

    version: int
    name: str
    up_sql: str
    down_sql: str
    checksum: str
    down_checksum: str


@dataclass(frozen=True, slots=True)
class AppliedMigration:
    """Migration metadata retained by the operational database."""

    version: int
    name: str
    app_version: str
    checksum: str
    down_checksum: str
    applied_at: str


@dataclass(slots=True)
class _MigrationParts:
    name: str
    up: tuple[str, str] | None = None
    down: tuple[str, str] | None = None


def _digest(content: bytes) -> str:
    return f"sha256:{sha256(content).hexdigest()}"


def _read_utf8(resource: Traversable) -> tuple[str, str]:
    content = resource.read_bytes()
    try:
        return content.decode("utf-8"), _digest(content)
    except UnicodeDecodeError as error:
        raise MigrationError(f"migration is not UTF-8: {resource.name}") from error


def discover_migrations() -> tuple[Migration, ...]:
    """Load the complete ordered migration set from package resources."""

    root = resources.files(_MIGRATIONS_PACKAGE)
    discovered: dict[int, _MigrationParts] = {}

    for resource in root.iterdir():
        if not resource.is_file():
            continue
        match = _MIGRATION_NAME.fullmatch(resource.name)
        if match is None:
            continue

        version = int(match.group("version"))
        name = match.group("name")
        direction = match.group("direction")
        sql, checksum = _read_utf8(resource)
        entry = discovered.setdefault(version, _MigrationParts(name=name))
        if entry.name != name:
            raise MigrationError(f"migration {version:04d} has inconsistent names")
        if direction == "up":
            if entry.up is not None:
                raise MigrationError(f"migration {version:04d} has duplicate up scripts")
            entry.up = (sql, checksum)
        else:
            if entry.down is not None:
                raise MigrationError(f"migration {version:04d} has duplicate down scripts")
            entry.down = (sql, checksum)

    if not discovered:
        raise MigrationError("no packaged migrations were found")

    versions = sorted(discovered)
    expected = list(range(1, versions[-1] + 1))
    if versions != expected:
        raise MigrationError(f"migration versions must be contiguous from 0001: {versions}")

    migrations: list[Migration] = []
    for version in versions:
        entry = discovered[version]
        if entry.up is None or entry.down is None:
            raise MigrationError(f"migration {version:04d} requires up and down scripts")
        up_sql, checksum = entry.up
        down_sql, down_checksum = entry.down
        migrations.append(
            Migration(
                version=version,
                name=entry.name,
                up_sql=up_sql,
                down_sql=down_sql,
                checksum=checksum,
                down_checksum=down_checksum,
            )
        )
    return tuple(migrations)


def _execute_script(connection: sqlite3.Connection, script: str) -> None:
    """Execute a SQL script without sqlite3.executescript's implicit commit.

    ``sqlite3.complete_statement`` keeps trigger bodies intact while allowing
    every DDL statement and the migration record to share one transaction.
    """

    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if not sqlite3.complete_statement(pending):
            continue
        statement = pending.strip()
        pending = ""
        if statement:
            connection.execute(statement)

    if pending.strip():
        raise MigrationError("migration ends with an incomplete SQL statement")


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    statement = """
        CREATE TABLE IF NOT EXISTS migrations (
            version INTEGER PRIMARY KEY CHECK (version > 0),
            name TEXT NOT NULL,
            app_version TEXT NOT NULL,
            checksum TEXT NOT NULL,
            down_checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        ) STRICT
    """
    with transaction(connection):
        connection.execute(statement)


def _applied_migrations(connection: sqlite3.Connection) -> tuple[AppliedMigration, ...]:
    rows = connection.execute(
        """
        SELECT version, name, app_version, checksum, down_checksum, applied_at
        FROM migrations
        ORDER BY version
        """
    ).fetchall()
    return tuple(
        AppliedMigration(
            version=row["version"],
            name=row["name"],
            app_version=row["app_version"],
            checksum=row["checksum"],
            down_checksum=row["down_checksum"],
            applied_at=row["applied_at"],
        )
        for row in rows
    )


def _validate_applied(
    applied: tuple[AppliedMigration, ...],
    packaged: tuple[Migration, ...],
) -> None:
    by_version = {migration.version: migration for migration in packaged}
    expected_version = 1
    for record in applied:
        if record.version != expected_version:
            raise MigrationError("applied migrations are not a contiguous ordered prefix")
        expected_version += 1
        migration = by_version.get(record.version)
        if migration is None:
            raise MigrationError(f"database contains unknown migration {record.version:04d}")
        if record.name != migration.name:
            raise MigrationError(
                f"migration {record.version:04d} name differs from packaged source"
            )
        if record.checksum != migration.checksum:
            raise MigrationChecksumError(
                f"migration {record.version:04d} checksum differs from packaged source"
            )
        if record.down_checksum != migration.down_checksum:
            raise MigrationChecksumError(
                f"migration {record.version:04d} rollback checksum differs from packaged source"
            )


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def apply_migrations(
    connection: sqlite3.Connection,
    *,
    app_version: str,
    target_version: int | None = None,
) -> tuple[AppliedMigration, ...]:
    """Apply each pending migration and its metadata atomically."""

    if not app_version.strip():
        raise ValueError("app_version must be non-empty")
    packaged = discover_migrations()
    latest = packaged[-1].version
    target = latest if target_version is None else target_version
    if target < 0 or target > latest:
        raise MigrationError(f"target version must be between 0 and {latest}")

    _ensure_migration_table(connection)
    applied = _applied_migrations(connection)
    _validate_applied(applied, packaged)
    current = applied[-1].version if applied else 0
    if target < current:
        raise MigrationError("use rollback_migrations when targeting an older version")

    for migration in packaged:
        if migration.version <= current or migration.version > target:
            continue
        with transaction(connection):
            _execute_script(connection, migration.up_sql)
            connection.execute(
                """
                INSERT INTO migrations(
                    version, name, app_version, checksum, down_checksum, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    migration.version,
                    migration.name,
                    app_version,
                    migration.checksum,
                    migration.down_checksum,
                    _timestamp(),
                ),
            )

    return _applied_migrations(connection)


def rollback_migrations(
    connection: sqlite3.Connection,
    *,
    target_version: int,
) -> tuple[AppliedMigration, ...]:
    """Revert applied migrations down to ``target_version``."""

    packaged = discover_migrations()
    latest = packaged[-1].version
    if target_version < 0 or target_version > latest:
        raise MigrationError(f"target version must be between 0 and {latest}")

    _ensure_migration_table(connection)
    applied = _applied_migrations(connection)
    _validate_applied(applied, packaged)
    by_version = {migration.version: migration for migration in packaged}

    for record in reversed(applied):
        if record.version <= target_version:
            continue
        migration = by_version[record.version]
        with transaction(connection):
            _execute_script(connection, migration.down_sql)
            connection.execute(
                "DELETE FROM migrations WHERE version = ?",
                (record.version,),
            )

    return _applied_migrations(connection)


def current_version(connection: sqlite3.Connection) -> int:
    """Return the current ordered schema version, bootstrapping metadata if needed."""

    _ensure_migration_table(connection)
    applied = _applied_migrations(connection)
    _validate_applied(applied, discover_migrations())
    return applied[-1].version if applied else 0
