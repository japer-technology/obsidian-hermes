DROP INDEX IF EXISTS outbox_pending;
DROP TABLE IF EXISTS outbox;

DROP TRIGGER IF EXISTS events_are_append_only_on_delete;
DROP TRIGGER IF EXISTS events_are_append_only_on_update;
DROP TRIGGER IF EXISTS events_sequence_is_monotonic;
DROP INDEX IF EXISTS events_by_command;
DROP INDEX IF EXISTS events_by_occurred_at;
DROP TABLE IF EXISTS events;

DROP TRIGGER IF EXISTS commands_require_terminal_receipt;
DROP TRIGGER IF EXISTS commands_cannot_start_terminal;
DROP TRIGGER IF EXISTS receipts_are_immutable_on_delete;
DROP TRIGGER IF EXISTS receipts_are_immutable_on_update;
DROP INDEX IF EXISTS receipts_one_terminal_per_command;
DROP TABLE IF EXISTS receipts;

DROP TRIGGER IF EXISTS approvals_are_immutable_on_delete;
DROP TRIGGER IF EXISTS approvals_decision_is_one_way;
DROP TRIGGER IF EXISTS approvals_subject_is_immutable;
DROP INDEX IF EXISTS approvals_by_expiry;
DROP TABLE IF EXISTS approvals;

DROP INDEX IF EXISTS leases_by_expiry;
DROP TABLE IF EXISTS leases;

DROP TRIGGER IF EXISTS fence_owner_change_requires_new_epoch;
DROP TRIGGER IF EXISTS fence_epoch_is_monotonic;
DROP TABLE IF EXISTS fence;

DROP TABLE IF EXISTS runs;

DROP TRIGGER IF EXISTS commands_specification_is_immutable;
DROP TABLE IF EXISTS commands;

DROP INDEX IF EXISTS resources_one_current_path;
DROP INDEX IF EXISTS resources_one_current_generation;
DROP TABLE IF EXISTS resources;
