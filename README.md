# Obsidian Hermes

> [!WARNING]
> Obsidian Hermes is pre-alpha. The deterministic schema/store kernel and a
> validation-only bridge are scaffolded, but worker dispatch is intentionally
> disabled and Phase One is not yet conformant or safe for real execution.

Obsidian Hermes is a local-first operating environment that uses an Obsidian
vault as the command centre, durable memory, workflow interface, and audit log
for Hermes Agent.

The design keeps commands, approvals, evidence, project state, outputs, and
execution receipts in readable Markdown. Hermes performs bounded work through
scheduled workers, while a deterministic control bridge reconciles desired
routine definitions with the runtime.

## Architecture

```text
User
  ↓
Obsidian vault (tasks, approvals, context, results)
  ↓
Deterministic control bridge
  ↓
Hermes cron workers
  ↓
Outputs, receipts, and updated knowledge
```

## Design principles

- **Local first:** ordinary Markdown remains useful without a model provider.
- **Human controlled:** consequential actions require explicit approval.
- **Auditable:** material actions link intent, evidence, output, and receipt.
- **Evidence backed:** imported sources remain separate from maintained
  knowledge.
- **Recoverable:** workers use bounded batches, leases, retries, and dead-letter
  handling.
- **Least privilege:** untrusted content cannot grant authority to an agent.

## Documentation

| Document | Status | Purpose |
| --- | --- | --- |
| [Project overview](docs/overview.md) | Canonical | Concepts, workflows, and intended capabilities |
| [Runtime specification v2.0](docs/specification/v2.0.md) | Canonical | Current schemas, control-plane contracts, and safety requirements |
| [Runtime specification v1.0](docs/specification/v1.0.md) | Superseded | Historical cron-first baseline and v2 migration source |
| [Design brainstorm](docs/design/brainstorm.md) | Exploratory | Product direction, risks, and possible delivery sequence |
| [Research notes](docs/research/) | Non-normative | External reviews retained as design input |

See the [documentation index](docs/) for document ownership and status.

## Implemented scaffold

The repository now establishes Python 3.12 as the reference implementation
toolchain and includes:

- strict executable schemas and complete fixtures for all eleven v2 resources;
- safe Markdown frontmatter parsing, typed identifiers, canonical hashes, and
  a closed command-state policy;
- an explicit SQLite migration for resources, commands, runs, leases,
  approvals, receipts, events, outbox, fencing, and migration history;
- a validation-only bridge and CLI that cannot dispatch workers;
- the three-zone reference vault, deployment examples, and CI checks.

The Hermes discovery adapter, authenticated approvals and dispatch, hardened
file opens, effective Docker mount inspection, network enforcement, workers,
projections, backup/restore, and lifecycle recovery remain implementation work.
See [implementation status](docs/implementation-status.md) for the exact
boundary.

## Development

Create a Python 3.12 environment and install the editable package:

```console
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff format --check .
python -m ruff check .
python -m mypy
```

Useful validation-only commands are:

```console
obsidian-hermes validate schemas
obsidian-hermes validate resource tests/fixtures/v2/valid/hermes.task-v2.json
obsidian-hermes validate vault --config config/hermes.example.toml
obsidian-hermes bridge run --config /etc/obsidian-hermes/hermes.toml --once
```

The example configuration contains deployment paths and must be copied and
reviewed; it is not expected to run directly from a source checkout.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/obsidian_hermes/` | Deterministic bridge kernel and packaged contracts |
| `tests/` | Unit, schema-conformance, security, and future acceptance coverage |
| `reference-vault/` | Non-production three-zone Obsidian vault scaffold |
| `config/` | Fail-closed reference bridge configuration |
| `deploy/` | Docker/Hermes and service-manager examples |
| `docs/` | Canonical specifications, implementation status, and research |

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change. Design
changes should identify affected schemas, permissions, failure modes, migration
needs, and recovery tests.

For help, see [SUPPORT.md](SUPPORT.md). Please report vulnerabilities according
to [SECURITY.md](SECURITY.md), not through a public issue.

## License

Obsidian Hermes is available under the [MIT License](LICENSE).
