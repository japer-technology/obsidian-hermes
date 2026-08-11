from obsidian_hermes.migration import (
    MigrationDisposition,
    RoutineDisposition,
    classify_operation,
    classify_routine,
)


def test_v1_operation_mapping_is_closed_and_non_executable() -> None:
    assert classify_operation("source.ingest") is MigrationDisposition.DRAFT_TASK
    assert classify_operation("brief.generate") is MigrationDisposition.DRAFT_TASK
    assert classify_operation("action.execute") is MigrationDisposition.BLOCKED_ACTION
    assert classify_operation("wiki.ripple") is MigrationDisposition.DEFERRED_PROPOSAL
    assert classify_operation("invented.operation") is MigrationDisposition.QUARANTINE


def test_v1_routines_are_only_proposals_and_remain_disabled() -> None:
    assert classify_routine("control-reconciler") is RoutineDisposition.BRIDGE_CONFIGURATION
    assert classify_routine("command-router") is RoutineDisposition.ROUTER_CONFIGURATION
    assert classify_routine("ingest-worker") is RoutineDisposition.DISABLED_PHASE_ONE
    assert classify_routine("wiki-ripple") is RoutineDisposition.DISABLED_DEFERRED
