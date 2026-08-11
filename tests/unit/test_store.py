from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from obsidian_hermes.store import (
    MigrationChecksumError,
    StoreConfigurationError,
    TransactionError,
    apply_migrations,
    current_version,
    open_database,
    rollback_migrations,
    transaction,
)


HASH_A = "sha256:" + ("a" * 64)
HASH_B = "sha256:" + ("b" * 64)
NOW = "2026-08-11T03:00:00Z"


@pytest.fixture
def database(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_database(tmp_path / "operational.sqlite3")
    apply_migrations(connection, app_version="0.1.0-test")
    try:
        yield connection
    finally:
        connection.close()


def _insert_task(
    connection: sqlite3.Connection,
    *,
    task_id: str = "task_01K2ABCDEFGHJKMNPQRSTVWXYZ",
    generation: int = 1,
    current: int = 1,
) -> None:
    connection.execute(
        """
        INSERT INTO resources(
            schema_name,
            schema_version,
            resource_id,
            revision,
            generation,
            vault_path,
            specification_hash,
            desired_state,
            observed_state,
            is_current,
            first_seen_at,
            last_seen_at
        ) VALUES ('hermes.task/v2', 2, ?, 1, ?, ?, ?, 'ready', 'pending', ?, ?, ?)
        """,
        (
            task_id,
            generation,
            f"ReadOnly/70 Tasks/{task_id}-{generation}.md",
            HASH_A,
            current,
            NOW,
            NOW,
        ),
    )


def _insert_command(
    connection: sqlite3.Connection,
    *,
    command_id: str = "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
    task_id: str = "task_01K2ABCDEFGHJKMNPQRSTVWXYZ",
    generation: int = 1,
    trace_id: str = "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
) -> None:
    connection.execute(
        """
        INSERT INTO commands(
            command_id,
            task_id,
            task_generation,
            operation,
            mode,
            state,
            priority,
            trace_id,
            specification_hash,
            dedupe_hash,
            command_payload,
            not_before,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, 'source.ingest', 'execute', 'queued', 50, ?, ?, ?, '{}', ?, ?, ?)
        """,
        (
            command_id,
            task_id,
            generation,
            trace_id,
            HASH_A,
            HASH_B,
            NOW,
            NOW,
            NOW,
        ),
    )


def _insert_run(
    connection: sqlite3.Connection,
    *,
    run_id: str = "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
    command_id: str = "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
    task_id: str = "task_01K2ABCDEFGHJKMNPQRSTVWXYZ",
    generation: int = 1,
    trace_id: str = "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
    attempt: int = 1,
) -> None:
    connection.execute(
        """
        INSERT INTO runs(
            run_id,
            command_id,
            task_id,
            task_generation,
            trace_id,
            attempt_number,
            state,
            agent_profile,
            model_provider,
            model_name,
            model_source,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'running', 'researcher', 'provider', 'model', 'routine', ?)
        """,
        (run_id, command_id, task_id, generation, trace_id, attempt, NOW),
    )


def _insert_fence(
    connection: sqlite3.Connection,
    *,
    epoch: int = 1,
) -> None:
    connection.execute(
        """
        INSERT INTO fence(
            fence_id, profile, vault_id, executor_id, epoch,
            acquired_at, heartbeat_at, expires_at
        ) VALUES (1, 'default', 'vault', 'executor-a', ?, ?, ?, ?)
        """,
        (epoch, NOW, NOW, "2026-08-11T03:05:00Z"),
    )


def _insert_task_approval(
    connection: sqlite3.Connection,
    *,
    approval_id: str = "approval_01K2ABCDEFGHJKMNPQRSTVWXY4",
    action_class: str = "external_write",
    risk_tier: int = 3,
    subject_json: str | None = None,
) -> None:
    task_id = "task_01K2ABCDEFGHJKMNPQRSTVWXYZ"
    run_id = "run_01K2ABCDEFGHJKMNPQRSTVWXY1"
    if subject_json is None:
        subject_json = (
            '{"type":"task-plan","task_id":"'
            + task_id
            + '","run_id":"'
            + run_id
            + '","task_generation":1,"hash_kind":"plan","hash":"'
            + HASH_A
            + '"}'
        )
    connection.execute(
        """
        INSERT INTO approvals(
            approval_id, revision, trace_id, action_class, risk_tier,
            subject_type, subject_json, subject_hash, decision,
            requested_at, expires_at, task_schema, task_id,
            task_generation, run_id
        ) VALUES (?, 1, ?, ?, ?, 'task-plan', ?, ?, 'pending', ?, ?,
                  'hermes.task/v2', ?, 1, ?)
        """,
        (
            approval_id,
            "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
            action_class,
            risk_tier,
            subject_json,
            HASH_A,
            NOW,
            "2026-08-12T03:00:00Z",
            task_id,
            run_id,
        ),
    )


def _seed_run(database: sqlite3.Connection) -> None:
    with transaction(database):
        _insert_task(database)
        _insert_command(database)
        _insert_run(database)


def test_connection_enforces_durable_pragmas(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "state.sqlite3", busy_timeout_ms=1_234)
    try:
        assert connection.isolation_level is None
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 1_234
        assert connection.execute("PRAGMA trusted_schema").fetchone()[0] == 0
    finally:
        connection.close()


@pytest.mark.parametrize("path", [":memory:", Path(":memory:"), "file:state?mode=memory"])
def test_connection_rejects_non_durable_database_paths(path: str | Path) -> None:
    with pytest.raises(StoreConfigurationError, match="file-backed"):
        open_database(path)


def test_transaction_commits_rolls_back_and_refuses_nesting(
    database: sqlite3.Connection,
) -> None:
    with transaction(database):
        database.execute(
            """
            INSERT INTO fence(
                fence_id, profile, vault_id, executor_id, epoch,
                acquired_at, heartbeat_at, expires_at
            ) VALUES (1, 'default', 'vault', 'executor-a', 1, ?, ?, ?)
            """,
            (NOW, NOW, NOW),
        )
    assert database.execute("SELECT epoch FROM fence").fetchone()[0] == 1

    with pytest.raises(RuntimeError, match="force rollback"), transaction(database):
        database.execute("UPDATE fence SET epoch = 2")
        raise RuntimeError("force rollback")
    assert database.execute("SELECT epoch FROM fence").fetchone()[0] == 1

    with (
        pytest.raises(TransactionError, match="nested"),
        transaction(database),
        transaction(database),
    ):
        pass
    assert not database.in_transaction


def test_initial_migration_records_version_app_and_checksum(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "state.sqlite3")
    try:
        applied = apply_migrations(connection, app_version="2.0.0-alpha")
        assert current_version(connection) == 1
        assert len(applied) == 1
        assert applied[0].version == 1
        assert applied[0].name == "initial"
        assert applied[0].app_version == "2.0.0-alpha"
        assert applied[0].checksum.startswith("sha256:")
        assert len(applied[0].checksum) == 71
        assert applied[0].down_checksum.startswith("sha256:")
        assert len(applied[0].down_checksum) == 71

        required_tables = {
            "resources",
            "commands",
            "runs",
            "leases",
            "approvals",
            "receipts",
            "events",
            "outbox",
            "fence",
            "migrations",
        }
        actual_tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE type = 'table'"
            )
        }
        assert required_tables <= actual_tables
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()


def test_applied_migration_checksum_is_verified(database: sqlite3.Connection) -> None:
    with transaction(database):
        database.execute(
            "UPDATE migrations SET checksum = ? WHERE version = 1",
            (HASH_B,),
        )

    with pytest.raises(MigrationChecksumError, match="checksum"):
        apply_migrations(database, app_version="0.1.1-test")


def test_migration_can_roll_back_and_reapply(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "state.sqlite3")
    try:
        apply_migrations(connection, app_version="before")
        assert rollback_migrations(connection, target_version=0) == ()
        assert current_version(connection) == 0
        assert connection.execute(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'commands'"
        ).fetchone() is None

        reapplied = apply_migrations(connection, app_version="after")
        assert reapplied[0].app_version == "after"
        assert current_version(connection) == 1
    finally:
        connection.close()


def test_foreign_keys_and_one_command_per_task_generation(
    database: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"), transaction(database):
        _insert_command(database)

    with transaction(database):
        _insert_task(database)
        _insert_command(database)

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"), transaction(database):
        _insert_command(
            database,
            command_id="cmd_01K2ABCDEFGHJKMNPQRSTVWXY9",
            trace_id="trace_01K2ABCDEFGHJKMNPQRSTVWXY9",
        )


def test_state_event_and_outbox_share_one_transaction(database: sqlite3.Connection) -> None:
    with transaction(database):
        _insert_task(database)
        _insert_command(database)

    def transition_with_event() -> None:
        database.execute(
            """
            UPDATE commands
            SET state = 'validated', updated_at = ?
            WHERE command_id = 'cmd_01K2ABCDEFGHJKMNPQRSTVWXY2'
            """,
            (NOW,),
        )
        database.execute(
            """
            INSERT INTO events(
                event_id, trace_id, span_id, sequence, occurred_at, type, actor,
                task_id, task_generation, command_id, outcome
            ) VALUES (
                'event_01K2ABCDEFGHJKMNPQRSTVWXY5',
                'trace_01K2ABCDEFGHJKMNPQRSTVWXY3',
                'span_01K2ABCDEFGHJKMNPQRSTVWXY6',
                1,
                ?,
                'command.validated',
                'bridge:local',
                'task_01K2ABCDEFGHJKMNPQRSTVWXYZ',
                1,
                'cmd_01K2ABCDEFGHJKMNPQRSTVWXY2',
                'success'
            )
            """,
            (NOW,),
        )
        database.execute(
            """
            INSERT INTO outbox(event_id, destination, payload, available_at)
            VALUES (
                'event_01K2ABCDEFGHJKMNPQRSTVWXY5',
                'vault-projection',
                '{}',
                ?
            )
            """,
            (NOW,),
        )

    with pytest.raises(RuntimeError, match="abort transition"), transaction(database):
        transition_with_event()
        raise RuntimeError("abort transition")

    assert database.execute(
        "SELECT state FROM commands WHERE command_id = 'cmd_01K2ABCDEFGHJKMNPQRSTVWXY2'"
    ).fetchone()[0] == "queued"
    assert database.execute("SELECT count(*) FROM events").fetchone()[0] == 0
    assert database.execute("SELECT count(*) FROM outbox").fetchone()[0] == 0

    with transaction(database):
        transition_with_event()
    assert database.execute(
        "SELECT state FROM commands WHERE command_id = 'cmd_01K2ABCDEFGHJKMNPQRSTVWXY2'"
    ).fetchone()[0] == "validated"
    assert database.execute("SELECT count(*) FROM events").fetchone()[0] == 1
    assert database.execute("SELECT count(*) FROM outbox").fetchone()[0] == 1


def test_historical_resource_generations_remain_referentially_valid(
    database: sqlite3.Connection,
) -> None:
    task_id = "task_01K2ABCDEFGHJKMNPQRSTVWXYZ"
    with transaction(database):
        _insert_task(database, task_id=task_id, generation=1)
        _insert_command(database, task_id=task_id, generation=1)
        database.execute(
            """
            UPDATE resources
            SET is_current = 0
            WHERE schema_name = 'hermes.task/v2' AND resource_id = ? AND generation = 1
            """,
            (task_id,),
        )
        _insert_task(database, task_id=task_id, generation=2)

    assert database.execute("PRAGMA foreign_key_check").fetchall() == []
    generations = database.execute(
        """
        SELECT generation, is_current
        FROM resources
        WHERE schema_name = 'hermes.task/v2' AND resource_id = ?
        ORDER BY generation
        """,
        (task_id,),
    ).fetchall()
    assert [tuple(row) for row in generations] == [(1, 0), (2, 1)]


def test_only_one_current_lease_exists_per_command(
    database: sqlite3.Connection,
) -> None:
    _seed_run(database)
    with transaction(database):
        _insert_fence(database)
        _insert_run(
            database,
            run_id="run_01K2ABCDEFGHJKMNPQRSTVWXY9",
            attempt=2,
        )
        database.execute(
            """
            INSERT INTO leases(
                command_id, run_id, owner, issued_at, expires_at,
                heartbeat_at, fence_epoch
            ) VALUES (?, ?, 'bridge:a', ?, ?, ?, 1)
            """,
            (
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
                "run_01K2ABCDEFGHJKMNPQRSTVWXY9",
                NOW,
                "2026-08-11T03:05:00Z",
                NOW,
            ),
        )

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"), transaction(database):
        database.execute(
            """
            INSERT INTO leases(
                command_id, run_id, owner, issued_at, expires_at,
                heartbeat_at, fence_epoch
            ) VALUES (?, ?, 'bridge:b', ?, ?, ?, 1)
            """,
            (
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
                "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
                NOW,
                "2026-08-11T03:05:00Z",
                NOW,
            ),
        )


def test_lease_requires_the_current_fence_row(database: sqlite3.Connection) -> None:
    _seed_run(database)
    lease_sql = """
        INSERT INTO leases(
            command_id, run_id, owner, issued_at, expires_at,
            heartbeat_at, fence_epoch
        ) VALUES (?, ?, 'bridge:a', ?, ?, ?, ?)
    """
    lease_values = (
        "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
        "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
        NOW,
        "2026-08-11T03:05:00Z",
        NOW,
    )

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"), transaction(
        database
    ):
        database.execute(lease_sql, (*lease_values, 1))

    with transaction(database):
        _insert_fence(database, epoch=2)

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"), transaction(
        database
    ):
        database.execute(lease_sql, (*lease_values, 1))

    with transaction(database):
        database.execute(lease_sql, (*lease_values, 2))
    assert database.execute("SELECT fence_epoch FROM leases").fetchone()[0] == 2


def test_approval_action_risk_and_subject_must_agree(
    database: sqlite3.Connection,
) -> None:
    _seed_run(database)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"), transaction(database):
        _insert_task_approval(
            database,
            action_class="bulk_vault_write",
            risk_tier=3,
        )

    wrong_subject = (
        '{"type":"task-plan","task_id":"task_other",'
        '"run_id":"run_01K2ABCDEFGHJKMNPQRSTVWXY1",'
        '"task_generation":1,"hash_kind":"plan","hash":"'
        + HASH_A
        + '"}'
    )
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"), transaction(database):
        _insert_task_approval(database, subject_json=wrong_subject)


def test_routine_approval_has_no_task_schema(database: sqlite3.Connection) -> None:
    subject = (
        '{"type":"routine-spec","routine_id":"ingest-worker",'
        '"revision":1,"hash_kind":"specification","hash":"'
        + HASH_A
        + '"}'
    )
    with transaction(database):
        database.execute(
            """
            INSERT INTO approvals(
                approval_id, revision, trace_id, action_class, risk_tier,
                subject_type, subject_json, subject_hash, decision,
                requested_at, expires_at, routine_id, routine_revision
            ) VALUES (?, 1, ?, 'routine_change', 4, 'routine-spec', ?, ?,
                      'pending', ?, ?, 'ingest-worker', 1)
            """,
            (
                "approval_01K2ABCDEFGHJKMNPQRSTVWXY4",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
                subject,
                HASH_A,
                NOW,
                "2026-08-12T03:00:00Z",
            ),
        )
    assert database.execute("SELECT task_schema FROM approvals").fetchone()[0] is None

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"), transaction(database):
        database.execute(
            """
            INSERT INTO approvals(
                approval_id, revision, trace_id, action_class, risk_tier,
                subject_type, subject_json, subject_hash, decision,
                requested_at, expires_at, task_schema, routine_id,
                routine_revision
            ) VALUES (?, 1, ?, 'routine_change', 4, 'routine-spec', ?, ?,
                      'pending', ?, ?, 'hermes.task/v2', 'other-routine', 1)
            """,
            (
                "approval_01K2ABCDEFGHJKMNPQRSTVWXY5",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY5",
                subject.replace("ingest-worker", "other-routine"),
                HASH_A,
                NOW,
                "2026-08-12T03:00:00Z",
            ),
        )


def test_approval_subject_is_immutable_and_decision_is_one_way(
    database: sqlite3.Connection,
) -> None:
    _seed_run(database)
    approval_id = "approval_01K2ABCDEFGHJKMNPQRSTVWXY4"
    with transaction(database):
        _insert_task_approval(database, approval_id=approval_id)

    with pytest.raises(sqlite3.IntegrityError, match="subject is immutable"), transaction(
        database
    ):
        database.execute(
            "UPDATE approvals SET subject_hash = ? WHERE approval_id = ?",
            (HASH_B, approval_id),
        )

    with transaction(database):
        database.execute(
            """
            UPDATE approvals
            SET decision = 'approved', decided_by = 'user:local-owner',
                decided_at = ?, attestation_method = 'local-action',
                attestation_key_id = 'bridge-key', attestation_signature = 'signed'
            WHERE approval_id = ?
            """,
            (NOW, approval_id),
        )

    with pytest.raises(sqlite3.IntegrityError, match="one-way"), transaction(database):
        database.execute(
            "UPDATE approvals SET decision = 'rejected' WHERE approval_id = ?",
            (approval_id,),
        )

    with pytest.raises(sqlite3.IntegrityError, match="immutable"), transaction(database):
        database.execute("DELETE FROM approvals WHERE approval_id = ?", (approval_id,))


def test_receipt_idempotency_is_unique_and_receipts_are_immutable(
    database: sqlite3.Connection,
) -> None:
    _seed_run(database)
    with transaction(database):
        database.execute(
            """
            INSERT INTO receipts(
                receipt_id, trace_id, command_id, run_id, step_id, receipt_kind,
                idempotency_key, status, completed_at
            ) VALUES (?, ?, ?, ?, 'preserve-source', 'step', ?, 'completed', ?)
            """,
            (
                "receipt_01K2ABCDEFGHJKMNPQRSTVWXY7",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
                "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2:preserve-source:v1",
                NOW,
            ),
        )

    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"), transaction(database):
        database.execute(
            """
            INSERT INTO receipts(
                receipt_id, trace_id, command_id, run_id, step_id, receipt_kind,
                idempotency_key, status, completed_at
            ) VALUES (?, ?, ?, ?, 'other-step', 'step', ?, 'completed', ?)
            """,
            (
                "receipt_01K2ABCDEFGHJKMNPQRSTVWXY8",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
                "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2:preserve-source:v1",
                NOW,
            ),
        )

    with pytest.raises(sqlite3.IntegrityError, match="immutable"), transaction(database):
        database.execute(
            "UPDATE receipts SET status = 'changed' WHERE receipt_id = ?",
            ("receipt_01K2ABCDEFGHJKMNPQRSTVWXY7",),
        )


def test_terminal_state_requires_a_terminal_receipt(database: sqlite3.Connection) -> None:
    _seed_run(database)
    command_id = "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2"
    with pytest.raises(
        sqlite3.IntegrityError, match="terminal receipt"
    ), transaction(database):
        database.execute(
            "UPDATE commands SET state = 'completed', updated_at = ? WHERE command_id = ?",
            (NOW, command_id),
        )

    with transaction(database):
        database.execute(
            """
            INSERT INTO receipts(
                receipt_id, trace_id, command_id, run_id, step_id, receipt_kind,
                idempotency_key, status, completed_at
            ) VALUES (?, ?, ?, ?, 'terminal', 'terminal', ?, 'completed', ?)
            """,
            (
                "receipt_01K2ABCDEFGHJKMNPQRSTVWXY7",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
                command_id,
                "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
                f"{command_id}:terminal:v1",
                NOW,
            ),
        )
        database.execute(
            "UPDATE commands SET state = 'completed', updated_at = ? WHERE command_id = ?",
            (NOW, command_id),
        )
    assert database.execute(
        "SELECT state FROM commands WHERE command_id = ?", (command_id,)
    ).fetchone()[0] == "completed"


def test_command_cannot_be_inserted_in_a_terminal_state(database: sqlite3.Connection) -> None:
    with transaction(database):
        _insert_task(database)

    with pytest.raises(sqlite3.IntegrityError, match="cannot start"), transaction(database):
        database.execute(
            """
            INSERT INTO commands(
                command_id, task_id, task_generation, operation, mode, state,
                priority, trace_id, specification_hash, dedupe_hash,
                command_payload, not_before, created_at, updated_at
            ) VALUES (?, ?, 1, 'source.ingest', 'execute', 'completed', 50, ?, ?, ?, '{}', ?, ?, ?)
            """,
            (
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY9",
                "task_01K2ABCDEFGHJKMNPQRSTVWXYZ",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY9",
                HASH_A,
                HASH_B,
                NOW,
                NOW,
                NOW,
            ),
        )


def test_pre_run_cancellation_can_receive_a_terminal_receipt(
    database: sqlite3.Connection,
) -> None:
    command_id = "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2"
    with transaction(database):
        _insert_task(database)
        _insert_command(database)
        database.execute(
            """
            INSERT INTO receipts(
                receipt_id, trace_id, command_id, run_id, step_id, receipt_kind,
                idempotency_key, status, completed_at
            ) VALUES (?, ?, ?, NULL, 'terminal', 'terminal', ?, 'cancelled', ?)
            """,
            (
                "receipt_01K2ABCDEFGHJKMNPQRSTVWXY7",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
                command_id,
                f"{command_id}:terminal:v1",
                NOW,
            ),
        )
        database.execute(
            "UPDATE commands SET state = 'cancelled', updated_at = ? WHERE command_id = ?",
            (NOW, command_id),
        )

    assert database.execute(
        "SELECT state FROM commands WHERE command_id = ?", (command_id,)
    ).fetchone()[0] == "cancelled"


def test_pre_run_receipt_trace_must_match_its_command(
    database: sqlite3.Connection,
) -> None:
    with transaction(database):
        _insert_task(database)
        _insert_command(database)

    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"), transaction(
        database
    ):
        database.execute(
            """
            INSERT INTO receipts(
                receipt_id, trace_id, command_id, run_id, step_id, receipt_kind,
                idempotency_key, status, completed_at
            ) VALUES (?, 'trace_wrong', ?, NULL, 'terminal', 'terminal', ?,
                      'cancelled', ?)
            """,
            (
                "receipt_01K2ABCDEFGHJKMNPQRSTVWXY7",
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2:terminal:v1",
                NOW,
            ),
        )


def test_receipt_json_fields_have_the_required_shapes(
    database: sqlite3.Connection,
) -> None:
    _seed_run(database)
    values = (
        "receipt_01K2ABCDEFGHJKMNPQRSTVWXY7",
        "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
        "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
        "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
        "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2:preserve-source:v1",
        NOW,
    )
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"), transaction(database):
        database.execute(
            """
            INSERT INTO receipts(
                receipt_id, trace_id, command_id, run_id, step_id, receipt_kind,
                idempotency_key, status, completed_at, outputs
            ) VALUES (?, ?, ?, ?, 'preserve-source', 'step', ?, 'completed', ?, '{}')
            """,
            values,
        )

    with pytest.raises(sqlite3.IntegrityError, match="CHECK"), transaction(database):
        database.execute(
            """
            INSERT INTO receipts(
                receipt_id, trace_id, command_id, run_id, step_id, receipt_kind,
                idempotency_key, status, completed_at, metadata
            ) VALUES (?, ?, ?, ?, 'preserve-source', 'step', ?, 'completed', ?, '[]')
            """,
            values,
        )


def test_terminal_receipt_status_must_match_terminal_command_state(
    database: sqlite3.Connection,
) -> None:
    _seed_run(database)
    command_id = "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2"
    with transaction(database):
        database.execute(
            """
            INSERT INTO receipts(
                receipt_id, trace_id, command_id, run_id, step_id, receipt_kind,
                idempotency_key, status, completed_at
            ) VALUES (?, ?, ?, ?, 'terminal', 'terminal', ?, 'failed', ?)
            """,
            (
                "receipt_01K2ABCDEFGHJKMNPQRSTVWXY7",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
                command_id,
                "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
                f"{command_id}:terminal:v1",
                NOW,
            ),
        )

    with pytest.raises(
        sqlite3.IntegrityError, match="terminal receipt"
    ), transaction(database):
        database.execute(
            "UPDATE commands SET state = 'completed', updated_at = ? WHERE command_id = ?",
            (NOW, command_id),
        )

    with transaction(database):
        database.execute(
            "UPDATE commands SET state = 'failed', updated_at = ? WHERE command_id = ?",
            (NOW, command_id),
        )
    assert database.execute(
        "SELECT state FROM commands WHERE command_id = ?", (command_id,)
    ).fetchone()[0] == "failed"


def test_events_are_monotonic_and_append_only(database: sqlite3.Connection) -> None:
    _seed_run(database)
    event_values = (
        "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
        "task_01K2ABCDEFGHJKMNPQRSTVWXYZ",
        1,
        "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
        "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
        NOW,
    )
    with transaction(database):
        database.execute(
            """
            INSERT INTO events(
                event_id, trace_id, span_id, sequence, occurred_at, type, actor,
                task_id, task_generation, command_id, run_id, outcome
            ) VALUES (?, ?, ?, ?, ?, 'command.claimed', 'bridge:local', ?, ?, ?, ?, 'success')
            """,
            (
                "event_01K2ABCDEFGHJKMNPQRSTVWXY5",
                event_values[0],
                "span_1",
                1,
                event_values[5],
                event_values[1],
                event_values[2],
                event_values[3],
                event_values[4],
            ),
        )
        database.execute(
            """
            INSERT INTO events(
                event_id, trace_id, span_id, sequence, occurred_at, type, actor,
                task_id, task_generation, command_id, run_id, outcome
            ) VALUES (?, ?, ?, ?, ?, 'command.running', 'bridge:local', ?, ?, ?, ?, 'success')
            """,
            (
                "event_01K2ABCDEFGHJKMNPQRSTVWXY6",
                event_values[0],
                "span_2",
                2,
                event_values[5],
                event_values[1],
                event_values[2],
                event_values[3],
                event_values[4],
            ),
        )

    with pytest.raises(sqlite3.IntegrityError, match="sequence"), transaction(database):
        database.execute(
            """
            INSERT INTO events(
                event_id, trace_id, span_id, sequence, occurred_at, type, actor,
                task_id, task_generation, command_id, run_id, outcome
            ) VALUES (?, ?, 'span_3', 0, ?, 'command.claimed', 'bridge:local',
                      ?, ?, ?, ?, 'success')
            """,
            (
                "event_01K2ABCDEFGHJKMNPQRSTVWXY7",
                event_values[0],
                event_values[5],
                event_values[1],
                event_values[2],
                event_values[3],
                event_values[4],
            ),
        )

    with pytest.raises(sqlite3.IntegrityError, match="append-only"), transaction(database):
        database.execute(
            "UPDATE events SET outcome = 'changed' WHERE event_id = ?",
            ("event_01K2ABCDEFGHJKMNPQRSTVWXY5",),
        )

    with pytest.raises(sqlite3.IntegrityError, match="append-only"), transaction(database):
        database.execute(
            "DELETE FROM events WHERE event_id = ?",
            ("event_01K2ABCDEFGHJKMNPQRSTVWXY5",),
        )


def test_event_type_vocabulary_is_closed(database: sqlite3.Connection) -> None:
    _seed_run(database)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"), transaction(database):
        database.execute(
            """
            INSERT INTO events(
                event_id, trace_id, span_id, sequence, occurred_at, type, actor,
                task_id, task_generation, command_id, run_id, outcome
            ) VALUES (?, ?, 'span_invalid', 1, ?, 'command.invented', 'bridge:local',
                      ?, 1, ?, ?, 'success')
            """,
            (
                "event_01K2ABCDEFGHJKMNPQRSTVWXY5",
                "trace_01K2ABCDEFGHJKMNPQRSTVWXY3",
                NOW,
                "task_01K2ABCDEFGHJKMNPQRSTVWXYZ",
                "cmd_01K2ABCDEFGHJKMNPQRSTVWXY2",
                "run_01K2ABCDEFGHJKMNPQRSTVWXY1",
            ),
        )


def test_fence_epoch_cannot_move_backwards(database: sqlite3.Connection) -> None:
    with transaction(database):
        database.execute(
            """
            INSERT INTO fence(
                fence_id, profile, vault_id, executor_id, epoch,
                acquired_at, heartbeat_at, expires_at
            ) VALUES (1, 'default', 'vault', 'executor-a', 7, ?, ?, ?)
            """,
            (NOW, NOW, NOW),
        )

    with pytest.raises(sqlite3.IntegrityError, match="increase"), transaction(database):
        database.execute("UPDATE fence SET epoch = 6 WHERE fence_id = 1")

    with pytest.raises(sqlite3.IntegrityError, match="new epoch"), transaction(database):
        database.execute("UPDATE fence SET executor_id = 'executor-b' WHERE fence_id = 1")

    with transaction(database):
        database.execute(
            "UPDATE fence SET executor_id = 'executor-b', epoch = 8 WHERE fence_id = 1"
        )
    row = database.execute("SELECT executor_id, epoch FROM fence").fetchone()
    assert tuple(row) == ("executor-b", 8)
