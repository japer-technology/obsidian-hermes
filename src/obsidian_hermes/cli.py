"""Single deterministic command-line surface for the bridge scaffold."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from obsidian_hermes import __version__
from obsidian_hermes.bridge import ValidationOnlyBridge
from obsidian_hermes.config import load_config
from obsidian_hermes.control_room.api import (
    ControlRoomApi,
    bearer_token_from_environment,
    create_server,
)
from obsidian_hermes.control_room.runtimes import (
    NoRepositoryProvenance,
    validation_only_runtime_catalog,
)
from obsidian_hermes.control_room.snapshot import (
    ControlRoomSnapshotAssembler,
    SnapshotLimits,
)
from obsidian_hermes.control_room.store_overlay import SqliteStoreOverlayReader
from obsidian_hermes.control_room.vault import FilesystemVaultStateReader
from obsidian_hermes.domain.errors import ConfigurationError, HermesError
from obsidian_hermes.lifecycle import LifecycleManager
from obsidian_hermes.migration import classify_operation
from obsidian_hermes.resources.loader import load_resource
from obsidian_hermes.resources.validation import SchemaRegistry
from obsidian_hermes.schemas import SCHEMA_FILENAMES
from obsidian_hermes.store import apply_migrations, current_version, open_database


def _emit(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _add_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, required=True, help="bridge TOML configuration")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="obsidian-hermes")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate schemas, resources, or a vault")
    validate_commands = validate.add_subparsers(dest="validate_command", required=True)
    validate_commands.add_parser("schemas", help="check every bundled schema")
    resource = validate_commands.add_parser("resource", help="validate resource files")
    resource.add_argument("paths", nargs="+", type=Path)
    vault = validate_commands.add_parser("vault", help="run one read-only resource scan")
    _add_config(vault)

    doctor = commands.add_parser("doctor", help="check static safety boundaries")
    _add_config(doctor)

    database = commands.add_parser("db", help="inspect or migrate the operational store")
    database_commands = database.add_subparsers(dest="db_command", required=True)
    db_status = database_commands.add_parser("status")
    _add_config(db_status)
    db_migrate = database_commands.add_parser("migrate")
    _add_config(db_migrate)

    bridge = commands.add_parser("bridge", help="run the validation-only bridge")
    bridge_commands = bridge.add_subparsers(dest="bridge_command", required=True)
    bridge_run = bridge_commands.add_parser("run")
    _add_config(bridge_run)
    bridge_run.add_argument("--once", action="store_true", help="validate once and exit")

    control_room = commands.add_parser(
        "control-room", help="serve the read-only Obsidian control-room API"
    )
    control_room_commands = control_room.add_subparsers(dest="control_room_command", required=True)
    control_room_serve = control_room_commands.add_parser("serve")
    _add_config(control_room_serve)

    lifecycle = commands.add_parser(
        "lifecycle", help="install and maintain vault-facing capabilities"
    )
    lifecycle.add_argument("--vault", type=Path, required=True, help="Obsidian vault directory")
    lifecycle.add_argument(
        "--source-root",
        type=Path,
        help="release checkout containing apps/obsidian-hermes (default: bundled release assets)",
    )
    lifecycle_commands = lifecycle.add_subparsers(dest="lifecycle_command", required=True)
    lifecycle_install = lifecycle_commands.add_parser("install")
    lifecycle_install.add_argument(
        "--force", action="store_true", help="adopt existing plugin files after backing them up"
    )
    lifecycle_commands.add_parser("update")
    lifecycle_commands.add_parser("repair")
    lifecycle_commands.add_parser("doctor")
    lifecycle_uninstall = lifecycle_commands.add_parser("uninstall")
    lifecycle_uninstall.add_argument(
        "--purge-state", action="store_true", help="also remove lifecycle backups and state"
    )

    migration = commands.add_parser("migrate-v1", help="plan a non-mutating v1 migration")
    migration_commands = migration.add_subparsers(dest="migration_command", required=True)
    migration_plan = migration_commands.add_parser("plan")
    migration_plan.add_argument("--operation", required=True)
    return parser


def _scan_payload(bridge: ValidationOnlyBridge) -> tuple[dict[str, Any], int]:
    report = bridge.scan_once()
    payload = {
        "mode": "validation-only",
        "safe": report.safe,
        "scanned": report.scanned,
        "valid": report.valid,
        "issues": [{"path": issue.path, "message": issue.message} for issue in report.issues],
    }
    return payload, 0 if report.safe else 2


def _report_scan(bridge: ValidationOnlyBridge) -> int:
    payload, result = _scan_payload(bridge)
    _emit(payload)
    return result


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "lifecycle":
        manager = LifecycleManager(vault=args.vault, source_root=args.source_root)
        if args.lifecycle_command == "install":
            _emit(manager.install(force=args.force))
            return 0
        if args.lifecycle_command == "update":
            _emit(manager.update())
            return 0
        if args.lifecycle_command == "repair":
            _emit(manager.repair())
            return 0
        if args.lifecycle_command == "doctor":
            payload, healthy = manager.doctor()
            _emit(payload)
            return 0 if healthy else 2
        if args.lifecycle_command == "uninstall":
            _emit(manager.uninstall(purge_state=args.purge_state))
            return 0

    if args.command == "validate" and args.validate_command == "schemas":
        SchemaRegistry.bundled()
        _emit({"valid": True, "schema_version": 2, "schemas": sorted(SCHEMA_FILENAMES)})
        return 0

    if args.command == "validate" and args.validate_command == "resource":
        registry = SchemaRegistry.bundled()
        results = []
        for path in args.paths:
            document = load_resource(path, registry=registry)
            results.append(
                {
                    "path": str(path),
                    "schema": document.metadata["schema"],
                    "specification_hash": document.spec_hash,
                }
            )
        _emit({"valid": True, "resources": results})
        return 0

    if args.command in {"doctor", "validate"}:
        config = load_config(args.config)
        bridge = ValidationOnlyBridge(config)
        payload, result = _scan_payload(bridge)
        if args.command == "doctor":
            payload.update(
                {
                    "validation_ready": result == 0,
                    "execution_ready": False,
                    "blocked_checks": [
                        "Hermes runtime discovery adapter",
                        "effective Docker mount inspection",
                        "platform no-follow file operations",
                        "dispatch attestation and transport",
                        "network allowlist enforcement",
                    ],
                }
            )
        _emit(payload)
        return result

    if args.command == "db":
        config = load_config(args.config)
        database_path = config.bridge.database_path
        if args.db_command == "status" and not database_path.exists():
            _emit({"path": str(database_path), "exists": False, "version": 0})
            return 0
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = open_database(database_path)
        try:
            if args.db_command == "migrate":
                applied = apply_migrations(connection, app_version=__version__)
                version = applied[-1].version if applied else 0
            else:
                version = current_version(connection)
        finally:
            connection.close()
        _emit({"path": str(database_path), "exists": True, "version": version})
        return 0

    if args.command == "bridge" and args.bridge_command == "run":
        bridge = ValidationOnlyBridge(load_config(args.config))
        if args.once:
            return _report_scan(bridge)
        bridge.run_forever()
        return 0

    if args.command == "control-room" and args.control_room_command == "serve":
        config = load_config(args.config)
        if not config.bridge.validation_only or config.bridge.dispatch_enabled:
            raise ConfigurationError("control-room scaffold requires validation-only bridge mode")
        settings = config.control_room
        assembler = ControlRoomSnapshotAssembler(
            vault=FilesystemVaultStateReader(
                {
                    "ReadWrite": config.vault.read_write_root,
                    "ReadOnly": config.vault.read_only_root,
                },
                runtime_by_agent_profile=settings.runtime_profiles,
                max_resource_bytes=config.limits.max_resource_bytes,
                max_scanned_entries=config.limits.max_files_per_scan,
            ),
            store=SqliteStoreOverlayReader(config.bridge.database_path),
            runtimes=validation_only_runtime_catalog(
                hermes_profile=config.hermes.profile,
                include_openclaw=True,
            ),
            repository=NoRepositoryProvenance(),
            limits=SnapshotLimits(
                max_items_per_collection=settings.max_items_per_collection,
                max_response_bytes=settings.max_response_bytes,
            ),
        )
        api = ControlRoomApi(
            assembler,
            bearer_token=bearer_token_from_environment(),
        )
        server = create_server(api, host=settings.bind_host, port=settings.port)
        url_host = f"[{settings.bind_host}]" if ":" in settings.bind_host else settings.bind_host
        _emit(
            {
                "api": "obsidian-hermes.control-room/v1",
                "url": f"http://{url_host}:{settings.port}/api/v1/snapshot",
                "auth": "required" if api.auth_required else "disabled",
                "validation_only": True,
                "dispatch_enabled": False,
            }
        )
        try:
            server.serve_forever()
        finally:
            server.server_close()
        return 0

    if args.command == "migrate-v1" and args.migration_command == "plan":
        _emit(
            {
                "operation": args.operation,
                "disposition": classify_operation(args.operation).value,
                "mutates_source": False,
                "executable": False,
            }
        )
        return 0

    raise AssertionError("argparse accepted an unhandled command")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and convert expected safety failures to a stable exit code."""

    try:
        return _dispatch(_parser().parse_args(argv))
    except (HermesError, OSError, sqlite3.Error) as error:
        print(f"obsidian-hermes: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
