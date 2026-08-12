# Obsidian Hermes

> [!WARNING]
> Pre-alpha, validation-only scaffold. It cannot safely dispatch an agent or
> claim production runtime conformance. Its current executable focus is safe
> local lifecycle management of the vault-facing capabilities.

Obsidian Hermes is a Markdown-first Obsidian control room for agent work. It
turns a vault into a living workspace for capture, queues, routines, runs,
approvals, model/depth choices, budgets, costs, activity, and durable memory.
Hermes Agent, OpenClaw, and future engines are runtime adapters behind the same
portable task and provenance model.

## The memory model

```text
Markdown = semantic/declarative memory (current intent and meaning)
Git      = episodic/shared memory (history, attribution, review, recovery)
SQLite   = working memory (leases, claims, idempotency, transient overlay)
```

Markdown is the application state and interoperability protocol, not an export
of a hidden database. Git is a shared memory and review surface, not merely a
backup. SQLite is disposable and rebuildable; durable meaning and outcomes are
written back to ordinary Markdown with links to their Git provenance.

## What is scaffolded

- A real Obsidian plugin under [`apps/obsidian-hermes`](apps/obsidian-hermes/)
  with a Control Room view, offline vault mode, clearly labelled reference
  preview, capture/proposal notes, runtime/model/depth cards, cost freshness,
  activity, and Git provenance presentation.
- A bounded, read-only loopback API at `/api/v1/health` and
  `/api/v1/snapshot`, with runtime-neutral DTOs, Hermes/OpenClaw descriptors,
  optional bearer authentication, and explicit Markdown/SQLite/Git provenance.
- Strict v2 Draft 2020-12 schemas, frontmatter security checks, canonical
  hashes, typed identifiers, deterministic transitions, and a reversible SQLite
  coordination migration.
- A reference vault containing ordinary Markdown control-room pages for
  Capture, Queue, Routines, Runs, Models and Costs, Approvals, Activity, the
  Runtime Registry, and Git Memory.

Everything that would mutate a runtime remains disabled. The plugin writes
reviewable Markdown proposals; it does not write SQLite, call a model, commit
Git, or pretend that a preview is live.

## Read next

| Document | Purpose |
| --- | --- |
| [Control Room product contract](docs/product/control-room.md) | Obsidian UX, runtime adapters, pricing, approvals, and first vertical slice |
| [Markdown and Git architecture](docs/architecture/markdown-and-git.md) | Canonical ownership, three memories, Git provenance, and reconstruction invariant |
| [v2.0 specification](docs/specification/v2.0.md) | Normative safety, schemas, transitions, and execution contracts |
| [Implementation status](docs/implementation-status.md) | What is available and what remains deliberately blocked |
| [Reference vault](reference-vault/README.md) | Copyable Markdown-first experience scaffold |

## Development

Python 3.12 is the bridge toolchain. Node 22 is used for the plugin CI job.

```console
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy

cd apps/obsidian-hermes
npm install
npm run check
npm run build
```

The plugin release artifacts are `manifest.json`, `main.js`, and `styles.css`.
Install them only in a disposable test vault. The official Obsidian guidance
also recommends deferring layout work until the workspace is ready and using
the platform request API for network calls; this scaffold follows both rules.

## Repository layout

| Path | Purpose |
| --- | --- |
| `apps/obsidian-hermes/` | Obsidian Control Room plugin |
| `src/obsidian_hermes/` | Deterministic bridge, contracts, schemas, and coordination store |
| `tests/` | Unit, security, schema, API, and conformance fixtures |
| `reference-vault/` | Standard Markdown experience and policy scaffold |
| `config/` and `deploy/` | Fail-closed host configuration and service examples |
| `docs/` | Canonical product architecture, v2 specification, status, and research |

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[SUPPORT.md](SUPPORT.md) before using the scaffold with real data.

## Lifecycle manager

The lifecycle commands manage the bundled Obsidian plugin and seed the
reference-vault notes. They record only the plugin release files in an
installation manifest at `.obsidian-hermes/installation.json`; seeded Markdown
is immediately user-owned and is never overwritten or removed.

The installed package uses its bundled release assets. To run directly from a
checkout, build the plugin first and supply that checkout with `--source-root`.
Then run:

```console
obsidian-hermes lifecycle --vault /path/to/vault install
obsidian-hermes lifecycle --vault /path/to/vault doctor
obsidian-hermes lifecycle --vault /path/to/vault update
obsidian-hermes lifecycle --vault /path/to/vault repair
obsidian-hermes lifecycle --vault /path/to/vault uninstall
```

`install` refuses to replace an unmanaged plugin by default; `--force` adopts
it after making a local backup. `update` and `repair` back up a replaced plugin
file under `.obsidian-hermes/backups/`. `uninstall` removes only unmodified,
manifest-tracked plugin assets and always preserves Markdown. Use
`uninstall --purge-state` only to remove the lifecycle manifest and known
backups after a clean uninstall; unrecognised state files are retained.

## License

MIT. See [LICENSE](LICENSE).
