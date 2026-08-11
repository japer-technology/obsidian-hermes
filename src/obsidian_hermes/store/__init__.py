"""SQLite operational store for Obsidian Hermes.

The store is intentionally small and model-free.  Callers receive a connection
configured for explicit transactions, then apply the packaged, checksum-verified
migrations before using it.
"""

from .connection import (
    StoreConfigurationError,
    TransactionError,
    open_database,
    transaction,
)
from .migration import (
    AppliedMigration,
    Migration,
    MigrationChecksumError,
    MigrationError,
    apply_migrations,
    current_version,
    discover_migrations,
    rollback_migrations,
)

__all__ = [
    "AppliedMigration",
    "Migration",
    "MigrationChecksumError",
    "MigrationError",
    "StoreConfigurationError",
    "TransactionError",
    "apply_migrations",
    "current_version",
    "discover_migrations",
    "open_database",
    "rollback_migrations",
    "transaction",
]
