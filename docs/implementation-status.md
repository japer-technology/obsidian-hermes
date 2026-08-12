# V2 implementation status

This document describes the implementation boundary of version `0.1.0a0`. The
normative target remains the [v2.0 runtime specification](specification/v2.0.md).
Where code, examples, or this status page conflict with the specification, the
specification governs.

## Available now

The scaffold provides deterministic building blocks that are safe to exercise
without starting a model or worker:

| Area | Current capability |
| --- | --- |
| Resource contracts | Eleven strict Draft 2020-12 schemas, offline reference resolution, complete valid fixtures, and focused invalid fixtures |
| Markdown resources | UTF-8 leading-frontmatter parser rejecting duplicate keys, aliases, anchors, explicit tags, non-string keys, and extra YAML documents |
| Identity and hashes | Typed Crockford ULIDs, content-derived source IDs, compact sorted JSON, explicit v2 resource hash selections, and complete-plan hashing |
| Operational store | File-backed SQLite in WAL/FULL mode, foreign keys, explicit transactions, ordered reversible migration, fencing, immutable receipts/events, and uniqueness constraints |
| Bridge | Static access-boundary checks and periodic validation-only full rescans; no writes or dispatch |
| Control-room API | Bounded, read-only loopback `/api/v1/health` and `/api/v1/snapshot` DTOs; optional bearer auth; Markdown-first composition with SQLite overlay labels |
| Obsidian UX | Buildable Control Room plugin with vault/offline mode, explicit reference preview, capture/proposal Markdown, runtime/model/depth/cost presentation, and Git-memory provenance |
| Migration | Closed, non-mutating classification of v1 operations |
| Deployment | Three-zone reference vault, fail-closed example configuration, independent Docker mounts, and a hardened service-unit starting point |

The JSON schemas intentionally close underspecified wire vocabularies narrowly.
Those choices and the associated hash assumptions are recorded alongside the
packaged schemas.

## Execution remains blocked

The scaffold must not be described as Phase One “alive.” The following ports
have no trusted production implementation yet:

- supported Hermes home/profile/gateway/cron/model and effective-container
  discovery;
- native routine reconciliation and approval-gated removal/change;
- authenticated approval/control attestation and key custody;
- transactionally claimed, fenced, expiring dispatch envelopes;
- platform-specific no-follow opens, mount-boundary and hard-link enforcement;
- destination allowlist or constrained-proxy network enforcement;
- ingest result manifests, raw-byte promotion, projections, and terminal
  receipt verification;
- queue recovery, daily brief generation, paired backup/restore, and v1
  migration application.

The plugin's control gestures currently create Markdown proposals only. The
loopback API is intentionally read-only, and the default Git provenance port
reports unavailable rather than executing Git commands. A connected runtime,
live commit provenance reader, and authenticated mutating control endpoints
remain future work.

The validation-only bridge raises a safety block if execution is enabled in
configuration. The bundled gates report `wakeAgent: false`, so an empty or
unimplemented queue never invokes a model.

## Acceptance coverage

Schema/canonicalisation, store invariants, parser attacks, lexical paths,
source identity, state transitions, and v1 operation mapping have portable
tests. The remaining v2.0 section 15 scenarios are tracked in
[`tests/acceptance/README.md`](../tests/acceptance/README.md) and must be run
against isolated real runtime fixtures. A green portable test suite is not a
v2 conformance claim.
