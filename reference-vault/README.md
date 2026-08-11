# Obsidian Hermes v2 reference vault

This directory tracks the recommended v2 vault shape so it can be copied and
opened as a `Hermes-Vault`. It is a structural scaffold, not a runnable or
production-secure deployment.

The three top-level zones describe the worker's effective access classes:

- `ReadWrite/` holds inbox items, maintained knowledge, outputs, proposals, and
  per-run staging.
- `ReadOnly/` holds human or bridge-owned intent, policy, evidence, runs, and
  audit projections. Git permissions do not make it read-only; the container
  mount must enforce that boundary.
- `Private/` represents host-only content. Never mount this directory into a
  worker. Mount a separate, empty, non-symlink mask at the worker's `Private`
  path instead.

Files named `.gitkeep` only preserve empty directories. Replace placeholders
with schema-valid resources after reviewing the v2 specification, then keep
execution paused until validation and filesystem-boundary tests pass.

