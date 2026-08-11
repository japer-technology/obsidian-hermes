# Hermes v2 executable schemas

This directory contains the strict Draft 2020-12 validation layer for the
eleven resource kinds required by the v2.0 specification.  Each resource
schema has a fixed `schema` discriminator, `schema_version: 2`, and rejects
unknown fields.  `common.schema.json` contains only shared definitions and is
not itself a resource kind.

The schemas deliberately implement the closed Phase One vocabulary.  An
extension must add a registered value and its tests before the validator will
accept it.  The following choices close places where v2.0 describes behaviour
without spelling out an exhaustive wire vocabulary:

- run states are the command lifecycle states from `claimed` onward, excluding
  only pre-run `queued` and `validated`;
- approval decisions are `pending`, `approved`, and `rejected`, and attestation
  methods are `local-bridge` and `signature`;
- authoritative agent and skill resources have `status: approved`; proposal
  lifecycle state is outside the executable resource directories;
- routine execution modes are the three Phase One modes named by the spec:
  `script-only`, `script-gated-agent`, and `agent`;
- Phase One task input is an HTTPS or HTTP URL, task outputs are
  `source-summary` or `daily-brief`, and the only task-level pre-approval class
  is `bulk_vault_write`;
- raw source type is currently `article`, with `prompt_injection` as the one
  registered diagnostic security flag;
- receipt statuses cover successful, deduplicated, and terminal command
  outcomes; event types and bounded event metadata are an explicit Phase One
  registry in the event schema;
- a terminal receipt may have `run_id: null` when authenticated cancellation,
  blocking, or supersession happens before any worker attempt; step and dedupe
  receipts always belong to a run;
- run outputs and receipt outputs are vault-path strings, while checkpoint and
  error projections are nullable bounded strings, because v2.0 gives no nested
  wire shape for them;
- task cancel/retry, routine run-once, and system controls take an empty
  `parameters` object; only task snooze admits `not_before`; derived control
  observation states are `pending`, `applied`, `rejected`, `expired`, and
  `failed`;
- gateway and bridge component state adds the example's `online` to the
  applicable dashboard failure states, while sandbox checks use
  `passed`/`failed`/`unknown` and the Phase One network default is always
  `denied`;
- priorities use the conventional inclusive range 0 through 100.
- Phase One routine schedules are limited to bounded `every Nm`/`every Nh`
  intervals and a daily five-field `minute hour * * *` trigger; other cron
  shapes remain blocked until their runtime semantics are specified.
- concrete resource paths never contain glob syntax; permission maxima accept
  only an exact path or a terminal `/**` subtree glob.

These are intentionally narrow assumptions.  Widening one is a schema change,
not a permissive fallback.

## Validation layers

JSON Schema validates structure and local values.  A conforming bridge also
needs deterministic checks that JSON Schema cannot establish on one decoded
document:

1. the Markdown reader must require UTF-8 and exactly one leading frontmatter
   document, and reject duplicate keys, aliases, custom tags, non-string map
   keys, and additional YAML documents;
2. timestamps need an RFC 3339 parser and routine timezones need the installed
   IANA database;
3. paths must be resolved under configured zone roots with no-follow opens,
   symlink/hard-link/mount checks, and case/Unicode collision detection;
4. revisions, trace sequence numbers, references, permission intersections,
   state transitions, expiry ordering, and attestation signatures require
   operational state or deployment policy;
5. `source_id` must equal `src_sha256_` plus the digest of the exact promoted
   source bytes, and receipt/idempotency uniqueness belongs in SQLite.

## Hash contracts

The schemas validate hash values but do not silently invent the missing plan
artifact schema.  Until that contract is added, only these resource selections
are safe to implement:

- task specification: all frontmatter except `observed`;
- routine specification: all frontmatter except `observed`,
  `approval.approval_id`, and `approval.approved_spec_hash` (excluding the last
  two avoids a self-referential hash; `approval.required_for_change` remains);
- agent and skill specifications: all frontmatter;
- control specification: all frontmatter except `attestation` and `observed`;
- approval attestation payload: approval ID, decision, complete subject,
  expiry, and approver, exactly as named by v2.0.

Run, raw-source metadata, receipts, status, and events are bridge projections
or operational records and have no resource specification hash in v2.0.  Raw
source content hashes cover the exact staged bytes, not a re-serialized YAML
mapping or normalized Markdown body.

Canonicalization code must preserve array order, sort mapping keys, emit
whitespace-free UTF-8 JSON, normalize an included Markdown body to LF plus one
final newline, and format the digest as lowercase `sha256:<hex>`.  The v2.0
text does not yet settle JSON number formatting or Unicode escaping, so hash
fixtures should avoid floats and non-ASCII scalars until that is specified.

The complete direct JSON instances under `tests/fixtures/v2/valid/` exercise
the executable schemas. Complete task and approval Markdown fixtures also
cross the strict frontmatter layer. Parser-adversarial Markdown files and
focused schema failures live under `tests/fixtures/v2/invalid/`.
