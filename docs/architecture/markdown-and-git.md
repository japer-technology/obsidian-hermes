# Markdown and Git are the memory model

> [!IMPORTANT]
> This is a target-architecture decision. The v2 execution specification still
> governs safety, validation, approvals, and runtime behaviour. This document
> governs where product state belongs and how the Obsidian experience presents
> it.

Obsidian Hermes is a Markdown application with a live runtime overlay. It is
not a database application that happens to export notes.

The vault is the shared, inspectable workspace for people and agents. Git gives
that workspace durable history and collaboration semantics. A local database
may coordinate concurrent work, but it must not become a second, hidden source
of truth.

## Three kinds of memory

| Memory | Technology | What belongs there | Lifetime |
| --- | --- | --- | --- |
| Semantic and declarative memory | Markdown in the vault | Intent, tasks, routines, runtime and model profiles, budgets, approvals, knowledge, outputs, receipts, and human explanation | Durable |
| Episodic and collaborative memory | Git | Diffs, authorship, agent provenance, review, alternatives, accepted changes, rollback points, and the history of how the vault evolved | Durable |
| Working memory | Local bridge and, where needed, SQLite | Claims, leases, fencing tokens, idempotency reservations, heartbeats, transient checkpoints, and delivery outbox state | Disposable |

The distinction is visible in the UI. A field derived from a note, a Git
commit, or a live runtime observation must be labelled as such. Freshness must
never be implied.

## Markdown is the application state

Prefer an ordinary `.md` file whenever the information remains meaningful as a
document. In particular:

- a task is a note, not merely a row;
- a routine and its schedule are a note;
- runtime, model, reasoning-depth, and pricing profiles are notes;
- approvals and receipts are notes linked to the relevant task and run;
- activity summaries and cost ledgers have Markdown projections;
- dashboards are views over notes, Git provenance, and live observations.

Use standard Markdown constructs before inventing syntax: headings, lists,
task lists, tables, links, block quotes, callouts, and fenced code blocks. YAML
frontmatter is reserved for the small typed surface that automation must query
or validate. The body carries goals, context, reasoning, evidence, and results
in prose that remains useful in any Markdown editor.

Executable resources continue to use the strict v2 frontmatter contracts. A
plugin may offer a friendlier editor, but it writes the same portable document
that a person or another agent runtime can read.

## Git is shared memory

Git is more than backup:

- a diff records what an agent or person learned or changed;
- a commit is an accepted episode in the vault's history;
- a branch is a proposed or alternative future;
- review is the approval surface for ordinary knowledge and configuration
  changes;
- merge conflict resolution is explicit reconciliation of competing beliefs;
- revert and restore provide recovery without erasing the historical record;
- commit, path, task, run, and trace identifiers connect execution to evidence.

Material automated changes should be attributable. Deployments may adopt
commit trailers such as:

```text
Actor-Runtime: openclaw-local
Actor-Profile: researcher
Task-ID: task_...
Run-ID: run_...
Trace-ID: trace_...
```

These trailers are provenance, not authority. A Git author, branch name, or
commit signature does not replace the v2 approval and attestation rules. The
vault must not contain credentials, provider tokens, or unredacted private
runtime logs.

Git writes are also not an implicit bridge power. An adapter may report
read-only provenance by default. Committing, branching, pushing, merging, or
rewriting history requires an explicit operator policy and the same bounded,
auditable action path as any other consequential write.

## SQLite is a rebuildable coordination overlay

SQLite is appropriate when ordinary files cannot safely arbitrate concurrent
workers. Its narrow responsibilities are:

- atomic command claims and expiring leases;
- fencing and generation checks;
- idempotency reservations;
- transient checkpoints and delivery outbox state;
- a rebuildable index used for bounded live queries.

It is not the sole home of a task, routine, approval, output, receipt, pricing
decision, or completed-run history. If a durable value must temporarily exist
in SQL for correctness, the design must name its canonical Markdown note and
its deterministic materialisation or reconciliation rule.

The current pre-alpha store is a safety scaffold and is broader than this
target ownership boundary. New product features must not deepen that coupling.

## Reconstruction invariant

Given the vault at a known Git commit, the system must be able to rebuild every
disposable index and return to a safe, non-running state without inventing
intent.

Deleting the operational database may lose an in-flight lease or transient
checkpoint. It must not lose:

- what the user asked for;
- which runtime and model policy were selected;
- budgets and pricing inputs;
- approvals or their subjects;
- completed outputs and receipts;
- the explanation and provenance of material changes.

Recovery never assumes that an interrupted action completed. It reconciles
Markdown receipts and runtime observations, then requires retry or review when
the outcome is ambiguous.

## Runtime-neutral notes

Hermes, OpenClaw, and future agent systems are runtime adapters, not separate
vaults or task formats. A durable note selects a logical runtime profile and
declares required capabilities. The bridge resolves that profile to an
installed adapter and reports observed runtime identity separately.

Runtime-specific identifiers and raw responses belong in a bounded adapter
section or linked evidence note. They must not leak into the common task model
when a portable concept exists.

Changing runtime, model, reasoning depth, or budget creates a visible revision
or proposal. It never silently changes the meaning of work that is already
running.

## Obsidian UX contract

The control room merges three sources without flattening them:

```text
canonical Markdown + Git provenance + optional live overlay -> Obsidian views
```

It must:

- deep-link every durable card to its source note;
- show live, projected, stale, offline, and preview states distinctly;
- show the runtime, model/depth policy, estimated cost, and available budget;
- remain useful when the bridge is offline;
- create standard Markdown for captures and proposed changes;
- avoid a hidden plugin database;
- present live controls as proposals until the validated bridge accepts them.

Reference or demonstration data must always be marked as preview data. It must
never be visually indistinguishable from a connected runtime.

## Ownership test for new fields

Before adding a database column or API-only value, ask:

1. Would a person want to read, link, diff, review, or edit this later?
2. Would another agent need it after the bridge state is lost?
3. Does it explain intent, authority, evidence, cost, or outcome?

If any answer is yes, it belongs in Markdown and Git. SQL may cache or
coordinate it, but it cannot own it alone.
