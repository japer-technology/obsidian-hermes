# Obsidian Hermes

> [!WARNING]
> Obsidian Hermes is in the specification and design phase. This repository
> does not yet contain an installable or runnable implementation.

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
Obsidian vault (commands, approvals, knowledge)
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

## Repository status

The repository currently contains design documentation only. It does **not**
yet ship the reference vault, control bridge, gate scripts, schemas, or tests
described by the specification.

The next useful milestone is a minimal, testable vertical slice:

1. a reference vault;
2. deterministic queue gates;
3. one end-to-end command lifecycle;
4. the control bridge and health reporting.

Implementation-specific source, test, packaging, and CI structure should be
introduced only after the implementation language and runtime contract are
chosen.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change. Design
changes should identify affected schemas, permissions, failure modes, migration
needs, and recovery tests.

For help, see [SUPPORT.md](SUPPORT.md). Please report vulnerabilities according
to [SECURITY.md](SECURITY.md), not through a public issue.

## License

Obsidian Hermes is available under the [MIT License](LICENSE).
