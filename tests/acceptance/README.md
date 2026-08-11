# V2 acceptance-test ledger

This directory tracks specification section 15 without turning unimplemented
runtime behaviour into passing mocks.

| Specification scenario | Portable coverage | Required next fixture |
| --- | --- | --- |
| 15.1 Schema and canonicalisation | Partial: schemas, fixtures, frontmatter, IDs, hashes | Property tests for every hash contract and semantic reference validation |
| 15.2 Basic lifecycle | Store constraints only | Real bridge + Hermes ingest vertical slice |
| 15.3 Empty queue | Idle gates return `wakeAgent: false` | Assert no session, run, command, or vault mutation through a real scheduler tick |
| 15.4 Dry run and approval | Plan hash only | Authenticated attestation and material-plan invalidation fixture |
| 15.5 Duplicate ingestion | Content-derived source ID only | Raw promotion and dedupe receipt integration |
| 15.6 Crash and lease recovery | Lease/store constraints only | Process termination at every durable checkpoint |
| 15.7 Prompt injection | Parser/path boundaries only | Ingest an adversarial raw source through a constrained worker |
| 15.8 Path and symlink attacks | Portable lexical and symlink tests | Platform no-follow, hard-link, alternate-mount, and Git-history fixture |
| 15.9 Filesystem boundaries | Not portable | Real Docker mount-table and hidden private-token test |
| 15.10 Gateway and bridge failure | Not implemented | External supervisor and bounded-restart fixture |
| 15.11 Fencing and sync conflict | Database fencing plus filename detection | Two-executor and synchronised-vault fixture |
| 15.12 Backup and restore | Not implemented | Paired isolated vault/database restore drill |
| 15.13 V1 migration | Operation classification only | Representative non-mutating planner and rollback fixture |

Tests are added here only when they exercise the real enforcement boundary.
Incomplete scenarios must stay visibly incomplete rather than skipped as if
they represented conformance.
