# Documentation

This directory separates the project's canonical design from exploratory and
historical material.

## Canonical documents

- [Obsidian Control Room](product/control-room.md) defines the primary product
  experience: capture, queue, routines, runs, model/cost controls, approvals,
  activity, a local Vault API, and runtime-neutral adapters.
- [Markdown and Git architecture](architecture/markdown-and-git.md) defines the
  state-ownership and reconstruction invariants across Markdown, Git, and
  SQLite.
- [Project overview](overview.md) explains the product model, major workflows,
  security boundaries, and roadmap.
- [Runtime specification v2.0](specification/v2.0.md) defines the current
  detailed design baseline for schemas, state transitions, workers, and
  operational controls.
- [Runtime specification v1.0](specification/v1.0.md) is the superseded
  cron-first baseline retained for migration and design history.
- [Implementation status](implementation-status.md) maps the current pre-alpha
  scaffold to v2.0 and lists the fail-closed runtime gaps.

Canonical does not mean implemented. The repository now contains a pre-alpha,
validation-only runtime scaffold and a Markdown experience preview; the root
[README](../README.md) is the source of truth for current delivery status.

## Exploratory documents

- [Design brainstorm](design/brainstorm.md) considers product direction,
  trade-offs, and sequencing. It is not a specification.

## Research archive

- [DeepSeek review](research/deepseek-review.md)
- [OpenAI 5.5 review](research/openai-5.5-review.md)
- [Definitive use cases and architecture](research/definition.md)
- [Secure Obsidian vault access](research/obsidian-vaults.md)

Research documents are retained for provenance and context. They may contain
unverified recommendations or source-tool citation markers and do not override
canonical project documents.

## Updating documentation

Keep the root README concise. Put durable product explanations in the overview,
versioned requirements in the specification, unsettled ideas under `design/`,
and external analysis under `research/`.

When a proposal becomes accepted design, update the appropriate canonical
document and record any compatibility or migration impact in the pull request.
