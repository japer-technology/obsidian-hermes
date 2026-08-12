"""Read-only, Markdown-first control-room API for Obsidian clients."""

from .api import ControlRoomApi, ControlRoomServer, create_server
from .ports import (
    RepositoryProvenanceReader,
    RuntimeCatalogPort,
    StoreOverlayReader,
    VaultStateReader,
)
from .snapshot import ControlRoomSnapshotAssembler, SnapshotLimits
from .store_overlay import SqliteStoreOverlayReader
from .vault import FilesystemVaultStateReader

__all__ = [
    "ControlRoomApi",
    "ControlRoomServer",
    "ControlRoomSnapshotAssembler",
    "FilesystemVaultStateReader",
    "RepositoryProvenanceReader",
    "RuntimeCatalogPort",
    "SnapshotLimits",
    "SqliteStoreOverlayReader",
    "StoreOverlayReader",
    "VaultStateReader",
    "create_server",
]
