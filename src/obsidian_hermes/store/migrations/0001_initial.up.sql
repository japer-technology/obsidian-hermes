CREATE TABLE IF NOT EXISTS migrations (
    version INTEGER PRIMARY KEY CHECK (version > 0),
    name TEXT NOT NULL,
    app_version TEXT NOT NULL,
    checksum TEXT NOT NULL,
    down_checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
) STRICT;

CREATE TABLE resources (
    record_id INTEGER PRIMARY KEY,
    schema_name TEXT NOT NULL CHECK (
        schema_name IN (
            'hermes.task/v2',
            'hermes.routine/v2',
            'hermes.control/v2',
            'hermes.agent/v2',
            'hermes.skill/v2'
        )
    ),
    schema_version INTEGER NOT NULL CHECK (schema_version = 2),
    resource_id TEXT NOT NULL CHECK (length(resource_id) > 0),
    revision INTEGER NOT NULL CHECK (revision > 0),
    generation INTEGER NOT NULL CHECK (generation >= 0),
    vault_path TEXT NOT NULL CHECK (length(vault_path) > 0),
    specification_hash TEXT NOT NULL
        CHECK (
            length(specification_hash) = 71
            AND substr(specification_hash, 1, 7) = 'sha256:'
        ),
    content_hash TEXT
        CHECK (
            content_hash IS NULL
            OR (
                length(content_hash) = 71
                AND substr(content_hash, 1, 7) = 'sha256:'
            )
        ),
    desired_state TEXT,
    observed_state TEXT NOT NULL,
    is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE (schema_name, resource_id, generation)
) STRICT;

CREATE UNIQUE INDEX resources_generation_hash
    ON resources(schema_name, resource_id, generation, specification_hash);

CREATE UNIQUE INDEX resources_one_current_generation
    ON resources(schema_name, resource_id)
    WHERE is_current = 1;

CREATE UNIQUE INDEX resources_one_current_path
    ON resources(vault_path)
    WHERE is_current = 1;

CREATE TRIGGER resources_specification_is_immutable
BEFORE UPDATE OF
    schema_name,
    schema_version,
    resource_id,
    revision,
    generation,
    specification_hash,
    content_hash,
    desired_state,
    first_seen_at
ON resources
BEGIN
    SELECT RAISE(ABORT, 'resource specification generation is immutable');
END;

CREATE TABLE commands (
    command_id TEXT PRIMARY KEY CHECK (length(command_id) > 0),
    task_schema TEXT NOT NULL DEFAULT 'hermes.task/v2'
        CHECK (task_schema = 'hermes.task/v2'),
    task_id TEXT NOT NULL,
    task_generation INTEGER NOT NULL CHECK (task_generation > 0),
    operation TEXT NOT NULL CHECK (operation IN ('source.ingest', 'brief.generate')),
    mode TEXT NOT NULL CHECK (mode IN ('execute', 'dry-run')),
    state TEXT NOT NULL CHECK (
        state IN (
            'queued',
            'validated',
            'claimed',
            'running',
            'awaiting_approval',
            'retry_scheduled',
            'verifying',
            'completed',
            'blocked',
            'failed',
            'cancelled',
            'dead_letter',
            'superseded'
        )
    ),
    priority INTEGER NOT NULL CHECK (priority BETWEEN 0 AND 100),
    trace_id TEXT NOT NULL UNIQUE,
    specification_hash TEXT NOT NULL
        CHECK (
            length(specification_hash) = 71
            AND substr(specification_hash, 1, 7) = 'sha256:'
        ),
    dedupe_hash TEXT NOT NULL
        CHECK (
            length(dedupe_hash) = 71
            AND substr(dedupe_hash, 1, 7) = 'sha256:'
        ),
    command_payload TEXT NOT NULL CHECK (
        json_valid(command_payload) AND json_type(command_payload) = 'object'
    ),
    not_before TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 0 CHECK (attempt >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 0),
    failure_class TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (task_id, task_generation),
    UNIQUE (command_id, trace_id),
    UNIQUE (command_id, task_id, task_generation, trace_id),
    CHECK (attempt <= max_attempts),
    FOREIGN KEY (task_schema, task_id, task_generation)
        REFERENCES resources(schema_name, resource_id, generation)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (task_schema, task_id, task_generation, specification_hash)
        REFERENCES resources(schema_name, resource_id, generation, specification_hash)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TRIGGER commands_specification_is_immutable
BEFORE UPDATE OF
    command_id,
    task_schema,
    task_id,
    task_generation,
    operation,
    mode,
    priority,
    trace_id,
    specification_hash,
    dedupe_hash,
    command_payload,
    created_at
ON commands
BEGIN
    SELECT RAISE(ABORT, 'command specification is immutable');
END;

CREATE TABLE runs (
    run_id TEXT PRIMARY KEY CHECK (length(run_id) > 0),
    command_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    task_generation INTEGER NOT NULL CHECK (task_generation > 0),
    trace_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    state TEXT NOT NULL CHECK (
        state IN (
            'claimed',
            'running',
            'awaiting_approval',
            'retry_scheduled',
            'verifying',
            'completed',
            'blocked',
            'failed',
            'cancelled',
            'dead_letter',
            'superseded'
        )
    ),
    agent_profile TEXT NOT NULL,
    model_provider TEXT NOT NULL CHECK (length(model_provider) > 0),
    model_name TEXT NOT NULL CHECK (length(model_name) > 0),
    model_source TEXT NOT NULL CHECK (model_source IN ('routine', 'agent_profile')),
    context_manifest TEXT NOT NULL DEFAULT '[]' CHECK (
        json_valid(context_manifest) AND json_type(context_manifest) = 'array'
    ),
    skills_used TEXT NOT NULL DEFAULT '[]' CHECK (
        json_valid(skills_used) AND json_type(skills_used) = 'array'
    ),
    outputs TEXT NOT NULL DEFAULT '[]' CHECK (
        json_valid(outputs) AND json_type(outputs) = 'array'
    ),
    approval_ids TEXT NOT NULL DEFAULT '[]' CHECK (
        json_valid(approval_ids) AND json_type(approval_ids) = 'array'
    ),
    input_tokens INTEGER NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
    output_tokens INTEGER NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
    network_requests INTEGER NOT NULL DEFAULT 0 CHECK (network_requests >= 0),
    last_checkpoint TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    UNIQUE (command_id, attempt_number),
    UNIQUE (run_id, command_id),
    UNIQUE (run_id, command_id, trace_id),
    UNIQUE (run_id, task_id, task_generation, trace_id),
    FOREIGN KEY (command_id, task_id, task_generation, trace_id)
        REFERENCES commands(command_id, task_id, task_generation, trace_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE TABLE fence (
    fence_id INTEGER PRIMARY KEY CHECK (fence_id = 1),
    profile TEXT NOT NULL,
    vault_id TEXT NOT NULL,
    executor_id TEXT NOT NULL,
    epoch INTEGER NOT NULL UNIQUE CHECK (epoch > 0),
    acquired_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    UNIQUE (profile, vault_id)
) STRICT;

CREATE TRIGGER fence_epoch_is_monotonic
BEFORE UPDATE OF epoch ON fence
WHEN NEW.epoch <= OLD.epoch
BEGIN
    SELECT RAISE(ABORT, 'fence epoch must increase');
END;

CREATE TRIGGER fence_owner_change_requires_new_epoch
BEFORE UPDATE OF profile, vault_id, executor_id ON fence
WHEN NEW.epoch <= OLD.epoch
BEGIN
    SELECT RAISE(ABORT, 'fence owner change requires a new epoch');
END;

CREATE TABLE leases (
    command_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    owner TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    fence_epoch INTEGER NOT NULL CHECK (fence_epoch > 0),
    FOREIGN KEY (command_id) REFERENCES commands(command_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (run_id, command_id) REFERENCES runs(run_id, command_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (fence_epoch) REFERENCES fence(epoch)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE INDEX leases_by_expiry ON leases(expires_at);

CREATE TABLE approvals (
    approval_id TEXT PRIMARY KEY CHECK (length(approval_id) > 0),
    revision INTEGER NOT NULL CHECK (revision > 0),
    trace_id TEXT NOT NULL,
    action_class TEXT NOT NULL CHECK (
        action_class IN ('bulk_vault_write', 'external_write', 'routine_change')
    ),
    risk_tier INTEGER NOT NULL CHECK (risk_tier BETWEEN 0 AND 4),
    subject_type TEXT NOT NULL CHECK (subject_type IN ('task-plan', 'routine-spec')),
    subject_json TEXT NOT NULL CHECK (
        json_valid(subject_json) AND json_type(subject_json) = 'object'
    ),
    subject_hash TEXT NOT NULL
        CHECK (
            length(subject_hash) = 71
            AND substr(subject_hash, 1, 7) = 'sha256:'
        ),
    decision TEXT NOT NULL CHECK (decision IN ('pending', 'approved', 'rejected')),
    requested_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    attestation_method TEXT,
    attestation_key_id TEXT,
    attestation_signature TEXT,
    task_schema TEXT
        CHECK (task_schema IS NULL OR task_schema = 'hermes.task/v2'),
    task_id TEXT,
    task_generation INTEGER,
    run_id TEXT,
    routine_id TEXT,
    routine_revision INTEGER,
    FOREIGN KEY (task_schema, task_id, task_generation)
        REFERENCES resources(schema_name, resource_id, generation)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (run_id, task_id, task_generation, trace_id)
        REFERENCES runs(run_id, task_id, task_generation, trace_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CHECK (
        (action_class = 'bulk_vault_write'
            AND risk_tier = 2
            AND subject_type = 'task-plan')
        OR
        (action_class = 'external_write'
            AND risk_tier = 3
            AND subject_type = 'task-plan')
        OR
        (action_class = 'routine_change'
            AND risk_tier = 4
            AND subject_type = 'routine-spec')
    ),
    CHECK (
        (decision = 'pending'
            AND decided_by IS NULL
            AND decided_at IS NULL
            AND attestation_method IS NULL
            AND attestation_key_id IS NULL
            AND attestation_signature IS NULL)
        OR
        (decision IN ('approved', 'rejected')
            AND length(decided_by) > 0
            AND decided_at IS NOT NULL
            AND attestation_method IN ('local-bridge', 'signature')
            AND length(attestation_key_id) > 0
            AND length(attestation_signature) > 0
            AND (action_class <> 'routine_change' OR attestation_method = 'signature'))
    ),
    CHECK (
        (subject_type = 'task-plan'
            AND task_schema = 'hermes.task/v2'
            AND task_id IS NOT NULL
            AND task_generation IS NOT NULL
            AND run_id IS NOT NULL
            AND routine_id IS NULL
            AND routine_revision IS NULL
            AND json_extract(subject_json, '$.type') IS subject_type
            AND json_extract(subject_json, '$.task_id') IS task_id
            AND json_extract(subject_json, '$.run_id') IS run_id
            AND json_extract(subject_json, '$.task_generation') IS task_generation
            AND json_extract(subject_json, '$.hash_kind') IS 'plan'
            AND json_extract(subject_json, '$.hash') IS subject_hash)
        OR
        (subject_type = 'routine-spec'
            AND task_schema IS NULL
            AND task_id IS NULL
            AND task_generation IS NULL
            AND run_id IS NULL
            AND routine_id IS NOT NULL
            AND routine_revision IS NOT NULL
            AND json_extract(subject_json, '$.type') IS subject_type
            AND json_extract(subject_json, '$.routine_id') IS routine_id
            AND json_extract(subject_json, '$.revision') IS routine_revision
            AND json_extract(subject_json, '$.hash_kind') IS 'specification'
            AND json_extract(subject_json, '$.hash') IS subject_hash)
    )
) STRICT;

CREATE INDEX approvals_by_expiry ON approvals(decision, expires_at);

CREATE TRIGGER approvals_subject_is_immutable
BEFORE UPDATE OF
    approval_id,
    revision,
    trace_id,
    action_class,
    risk_tier,
    subject_type,
    subject_json,
    subject_hash,
    requested_at,
    expires_at,
    task_schema,
    task_id,
    task_generation,
    run_id,
    routine_id,
    routine_revision
ON approvals
BEGIN
    SELECT RAISE(ABORT, 'approval subject is immutable');
END;

CREATE TRIGGER approvals_decision_is_one_way
BEFORE UPDATE OF
    decision,
    decided_by,
    decided_at,
    attestation_method,
    attestation_key_id,
    attestation_signature
ON approvals
WHEN OLD.decision <> 'pending' OR NEW.decision NOT IN ('approved', 'rejected')
BEGIN
    SELECT RAISE(ABORT, 'approval decision is one-way');
END;

CREATE TRIGGER approvals_are_immutable_on_delete
BEFORE DELETE ON approvals
BEGIN
    SELECT RAISE(ABORT, 'approvals are immutable');
END;

CREATE TABLE receipts (
    receipt_id TEXT PRIMARY KEY CHECK (length(receipt_id) > 0),
    trace_id TEXT NOT NULL,
    command_id TEXT NOT NULL,
    run_id TEXT,
    step_id TEXT NOT NULL,
    receipt_kind TEXT NOT NULL CHECK (receipt_kind IN ('step', 'terminal', 'dedupe')),
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (
        status IN (
            'completed',
            'deduplicated',
            'failed',
            'blocked',
            'cancelled',
            'dead_letter',
            'superseded'
        )
    ),
    completed_at TEXT NOT NULL,
    outputs TEXT NOT NULL DEFAULT '[]' CHECK (
        json_valid(outputs) AND json_type(outputs) = 'array'
    ),
    content_hash TEXT
        CHECK (
            content_hash IS NULL
            OR (
                length(content_hash) = 71
                AND substr(content_hash, 1, 7) = 'sha256:'
            )
        ),
    external_reference TEXT,
    metadata TEXT NOT NULL DEFAULT '{}' CHECK (
        json_valid(metadata) AND json_type(metadata) = 'object'
    ),
    UNIQUE (command_id, step_id),
    CHECK (receipt_kind = 'terminal' OR run_id IS NOT NULL),
    CHECK (
        receipt_kind <> 'terminal'
        OR status IN (
            'completed',
            'deduplicated',
            'blocked',
            'failed',
            'cancelled',
            'dead_letter',
            'superseded'
        )
    ),
    FOREIGN KEY (command_id) REFERENCES commands(command_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (command_id, trace_id) REFERENCES commands(command_id, trace_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (run_id, command_id, trace_id)
        REFERENCES runs(run_id, command_id, trace_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE UNIQUE INDEX receipts_one_terminal_per_command
    ON receipts(command_id)
    WHERE receipt_kind = 'terminal';

CREATE TRIGGER receipts_are_immutable_on_update
BEFORE UPDATE ON receipts
BEGIN
    SELECT RAISE(ABORT, 'receipts are immutable');
END;

CREATE TRIGGER receipts_are_immutable_on_delete
BEFORE DELETE ON receipts
BEGIN
    SELECT RAISE(ABORT, 'receipts are immutable');
END;

CREATE TRIGGER commands_require_terminal_receipt
BEFORE UPDATE OF state ON commands
WHEN
    NEW.state IN ('completed', 'blocked', 'failed', 'cancelled', 'dead_letter', 'superseded')
    AND OLD.state NOT IN ('completed', 'blocked', 'failed', 'cancelled', 'dead_letter', 'superseded')
    AND NOT EXISTS (
        SELECT 1
        FROM receipts
        WHERE receipts.command_id = NEW.command_id
          AND receipts.receipt_kind = 'terminal'
          AND (
              receipts.status = NEW.state
              OR (NEW.state = 'completed' AND receipts.status = 'deduplicated')
          )
    )
BEGIN
    SELECT RAISE(ABORT, 'terminal commands require a terminal receipt');
END;

CREATE TRIGGER commands_cannot_start_terminal
BEFORE INSERT ON commands
WHEN NEW.state IN ('completed', 'blocked', 'failed', 'cancelled', 'dead_letter', 'superseded')
BEGIN
    SELECT RAISE(ABORT, 'new commands cannot start in a terminal state');
END;

CREATE TRIGGER commands_terminal_state_is_immutable
BEFORE UPDATE OF state ON commands
WHEN
    OLD.state IN ('completed', 'blocked', 'failed', 'cancelled', 'dead_letter', 'superseded')
    AND NEW.state <> OLD.state
BEGIN
    SELECT RAISE(ABORT, 'terminal command state is immutable');
END;

CREATE TABLE events (
    event_id TEXT PRIMARY KEY CHECK (length(event_id) > 0),
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    parent_span_id TEXT,
    sequence INTEGER NOT NULL CHECK (sequence >= 0),
    occurred_at TEXT NOT NULL,
    type TEXT NOT NULL CHECK (
        type IN (
            'bridge.startup',
            'bridge.ready',
            'bridge.blocked',
            'bridge.drift_detected',
            'gateway.online',
            'gateway.offline',
            'resource.validated',
            'resource.invalid',
            'command.queued',
            'command.validated',
            'command.claimed',
            'command.running',
            'command.awaiting_approval',
            'command.retry_scheduled',
            'command.verifying',
            'command.completed',
            'command.blocked',
            'command.failed',
            'command.cancelled',
            'command.dead_letter',
            'command.superseded',
            'control.applied',
            'control.rejected',
            'routine.reconciled',
            'routine.drift_detected',
            'approval.attested',
            'approval.rejected',
            'sandbox.mounts_verified',
            'security.denied'
        )
    ),
    actor TEXT NOT NULL,
    task_schema TEXT NOT NULL DEFAULT 'hermes.task/v2'
        CHECK (task_schema = 'hermes.task/v2'),
    task_id TEXT,
    task_generation INTEGER,
    command_id TEXT,
    run_id TEXT,
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure', 'denied', 'noop')),
    data TEXT NOT NULL DEFAULT '{}' CHECK (
        json_valid(data) AND json_type(data) = 'object'
    ),
    UNIQUE (trace_id, sequence),
    CHECK (
        (task_id IS NULL AND task_generation IS NULL)
        OR (task_id IS NOT NULL AND task_generation IS NOT NULL)
    ),
    CHECK (run_id IS NULL OR command_id IS NOT NULL),
    FOREIGN KEY (task_schema, task_id, task_generation)
        REFERENCES resources(schema_name, resource_id, generation)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (command_id) REFERENCES commands(command_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (command_id, trace_id) REFERENCES commands(command_id, trace_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    FOREIGN KEY (run_id, command_id, trace_id)
        REFERENCES runs(run_id, command_id, trace_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE INDEX events_by_occurred_at ON events(occurred_at);
CREATE INDEX events_by_command ON events(command_id, sequence);

CREATE TRIGGER events_sequence_is_monotonic
BEFORE INSERT ON events
WHEN
    EXISTS (SELECT 1 FROM events WHERE trace_id = NEW.trace_id)
    AND NEW.sequence <= (
        SELECT max(sequence) FROM events WHERE trace_id = NEW.trace_id
    )
BEGIN
    SELECT RAISE(ABORT, 'event sequence must increase within a trace');
END;

CREATE TRIGGER events_are_append_only_on_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are append-only');
END;

CREATE TRIGGER events_are_append_only_on_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are append-only');
END;

CREATE TABLE outbox (
    outbox_id INTEGER PRIMARY KEY,
    event_id TEXT NOT NULL,
    destination TEXT NOT NULL,
    payload TEXT NOT NULL CHECK (
        json_valid(payload) AND json_type(payload) = 'object'
    ),
    available_at TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    delivered_at TEXT,
    last_error TEXT,
    UNIQUE (event_id, destination),
    FOREIGN KEY (event_id) REFERENCES events(event_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT
) STRICT;

CREATE INDEX outbox_pending
    ON outbox(available_at)
    WHERE delivered_at IS NULL;
