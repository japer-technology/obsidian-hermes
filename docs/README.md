# Documentation

This directory separates the project's canonical design from exploratory and
historical material.

## Canonical documents

- [Project overview](overview.md) explains the product model, major workflows,
  security boundaries, and roadmap.
- [Runtime specification v1.0](specification/v1.0.md) defines the current
  detailed design baseline for schemas, state transitions, workers, and
  operational controls.

Canonical does not mean implemented. The repository remains in the design
phase, and the root [README](../README.md) is the source of truth for current
delivery status.

## Exploratory documents

- [Design brainstorm](design/brainstorm.md) considers product direction,
  trade-offs, and sequencing. It is not a specification.

## Research archive

- [DeepSeek review](research/deepseek-review.md)
- [OpenAI 5.5 review](research/openai-5.5-review.md)

Research documents are retained for provenance and context. They may contain
unverified recommendations or source-tool citation markers and do not override
canonical project documents.

## Updating documentation

Keep the root README concise. Put durable product explanations in the overview,
versioned requirements in the specification, unsettled ideas under `design/`,
and external analysis under `research/`.

When a proposal becomes accepted design, update the appropriate canonical
document and record any compatibility or migration impact in the pull request.
