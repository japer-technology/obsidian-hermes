# Contributing

Thanks for helping improve Obsidian Hermes.

## Current scope

The project is in the specification and design phase. The repository does not
yet have an implementation language, package manager, build, or test suite.
Documentation, design corrections, focused examples, and implementation
proposals are welcome.

Do not introduce a language-specific project skeleton or dependency stack
without an accepted design proposal. Those choices should follow the runtime
contract rather than define it accidentally.

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

There are currently no project build or test commands. For documentation
changes, verify Markdown links, issue-form syntax, and whitespace. Add
toolchain-specific validation instructions when an implementation toolchain is
accepted.

By contributing, you agree that your contribution is licensed under the
[MIT License](LICENSE).
