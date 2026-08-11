# Contributing

Thanks for helping improve Obsidian Hermes.

## Current scope

The v2 reference scaffold uses Python 3.12, a `src/` package, explicit SQLite
migrations, JSON Schema Draft 2020-12, PyYAML's safe loader with a stricter
frontmatter profile, and pytest. The bridge remains validation-only while its
security-sensitive runtime adapters are built and tested.

Do not widen a closed schema vocabulary, enable dispatch, or fill a
security-sensitive port with a permissive fallback without updating the
normative contract and its recovery/security tests.

## Before proposing a change

1. Read the root [README](README.md) and [documentation index](docs/).
2. Search existing issues for the same problem.
3. Open a design proposal before making a material architecture, schema, or
   trust-boundary change.
4. Report vulnerabilities privately according to [SECURITY.md](SECURITY.md).

## Ground rules

Contributions must preserve the project's core guarantees:

- local-first, human-readable state;
- immutable raw evidence and explicit provenance;
- bounded autonomous execution;
- least-privilege tools and permissions;
- explicit approval for consequential actions;
- idempotent external effects and durable receipts;
- visible, recoverable failures;
- no reliance on conversational memory for scheduled work.

Research notes under `docs/research/` are non-normative. A recommendation must
be validated and incorporated into a canonical document before it becomes part
of the design.

## Design and schema changes

Describe:

- the user or operational problem;
- affected documents, schemas, operations, and state transitions;
- permissions and trust boundaries;
- failure modes and recovery behaviour;
- compatibility and migration requirements;
- how the change can be tested safely.

Unknown operations and invalid states should fail closed. Proposals that add
external, destructive, financial, credential, or security-sensitive effects
must define an approval and idempotency model.

## Pull requests

- Keep each pull request focused on one coherent change.
- Link the issue or proposal that provides context.
- Update every affected cross-reference.
- Distinguish implemented behaviour from planned behaviour.
- Do not commit credentials, private vault content, generated local state, or
  unredacted logs.
- Use an imperative commit subject under 72 characters where practical.

Run the deterministic checks before opening a pull request:

```console
python -m pip install -e ".[dev]"
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m pytest
```

Docker boundary and restore tests require isolated fixtures and remain separate
from the portable unit suite. Never substitute a mocked mount result for the
required effective-mount and private-token tests.

By contributing, you agree that your contribution is licensed under the
[MIT License](LICENSE).
