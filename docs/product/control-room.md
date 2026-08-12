# Obsidian Control Room

Obsidian Hermes is an Obsidian-native control plane for personal agents. The
vault is the product surface; Hermes, OpenClaw, and future runtimes are engines
behind typed adapters. A user should be able to capture work, understand what
agents are doing, change cost and quality choices, approve consequences, and
review the durable result without leaving Obsidian.

This product direction complements the [v2 runtime specification](../specification/v2.0.md).
The runtime specification defines safety and execution contracts. This document
defines the experience those contracts should enable. The
[Markdown and Git architecture](../architecture/markdown-and-git.md) defines
the normative state-ownership and reconstruction rules.

## Product promise

Open the vault and know, at a glance:

- what needs attention;
- what is queued, running, scheduled, blocked, or complete;
- which runtime and model will do the work;
- what it is likely to cost and what it actually cost;
- what changed, who or which agent changed it, and why;
- what can be safely adjusted, paused, approved, retried, or cancelled.

The default experience uses ordinary Markdown, links, properties, callouts, and
embeds. Custom views add live interaction; they do not make the vault unreadable
or unusable without the plugin.

## The three memories

The UX presents one coherent workspace while preserving three different jobs:

| Memory | Role in the product |
| --- | --- |
| Markdown | Semantic and declarative memory: what is true, wanted, configured, approved, or meaningfully recorded |
| Git | Episodic shared memory: what changed, who or which agent changed it, why, and how it can be reviewed or recovered |
| SQLite | Short-lived working memory: claims, leases, idempotency, checkpoints, live run state, and the transactional event outbox |

Markdown is the canonical application state, interoperability protocol, and
human UI substrate. Git is not merely a backup: commits, branches, diffs, and
reviews are how humans and agents share provenance and resolve competing
changes. SQLite exists only where files and Git cannot safely arbitrate
concurrency. It must be disposable and reconstructable from Markdown, Git,
runtime discovery, and immutable receipts; meaningful operational outcomes are
mirrored back to deterministic Markdown.

Claims, leases, heartbeats, and rapidly changing queue positions never belong
in Git. Agent-authored bulk or consequential vault changes should be made on a
branch or equivalent proposal, with actor, trace ID, intent, and evidence in the
commit metadata or linked proposal note.

## Primary surfaces

### Control Room

The home view is an operational brief, not a file browser. It shows attention
items, active work, next routines, recent outcomes, runtime health, and spend
against budgets. Every card links to an ordinary note or a live filtered view.

### Capture

A global command accepts natural language, pasted links, selected text, or the
current note. It previews the resulting task, routine, memory, or proposal
before writing Markdown. YAML is available for advanced users but is never the
price of entry.

### Queue

One queue spans every configured runtime. Tasks remain portable until they are
explicitly bound by policy or by the user. Reordering, pausing, cancelling, and
changing a queued task creates a traceable intent revision. A running task is
never silently mutated: it must be paused, cancelled, or replanned.

### Routines

Cron and interval work appears as a living schedule with next run, last result,
health, runtime binding, model policy, budget, and missed-run state. Editing a
routine changes durable Markdown intent; the bridge validates and reconciles it.
Consequential routine changes continue to require approval.

### Runs

A run view combines a live event timeline with durable context: task, plan,
runtime, resolved model, reasoning depth, tools, token usage, estimated cost,
actual cost, outputs, receipt, and recovery actions. Streaming UI is transient;
the final run and receipt projections are deterministic Markdown.

### Models and Costs

Models are presented as deployment-discovered capabilities, not hard-coded
marketing names. A task or routine may select an approved profile describing
runtime, provider, model, reasoning depth, context envelope, and budgets.
Price data records its source, currency, retrieval time, and uncertainty.

Before execution the UI shows an estimate and budget headroom. During a run it
shows measured usage when the runtime provides it. Afterward it records actual
or explicitly marked estimated cost. A stale or missing price never masquerades
as a quote.

### Approvals

Approvals are inbox items attached to the exact plan or routine hash. The view
shows the proposed effect, evidence, risk tier, budget impact, expiry, and the
change since any previous approval. Approve and reject actions call the local
control API; editing a projection does not grant authority.

### Activity

The activity stream answers “what happened?” across humans, agents, Git, and
runtimes. Events correlate actor, runtime, task, run, trace ID, commit, cost,
and resulting notes. Filters can narrow the stream without replacing its
durable Markdown and Git provenance.

## Local Vault API

The Obsidian plugin talks to a loopback-only service owned by the deterministic
bridge. The service exposes a stable, runtime-neutral vocabulary:

- query resources, queue summaries, runs, routines, approvals, costs, and
  runtime health;
- subscribe to ordered events and projection changes;
- submit validated task or routine intent revisions;
- request pause, resume, cancel, retry, replan, reorder, or approval actions;
- preview model choices, capabilities, and cost envelopes before committing.

Read operations may combine Markdown projections with live operational state.
Commands return an accepted intent or control-request identity; they do not
promise that an agent performed the action. The plugin never edits
bridge-owned projections or SQLite directly. Authentication, origin checks,
anti-replay controls, schema validation, and fail-closed runtime discovery are
required before control endpoints are enabled.

## Runtime adapters

Each agent engine is registered through a typed adapter. Hermes and OpenClaw
are examples, not hard dependencies. An adapter reports its identity, version,
health, scheduling and cancellation semantics, available models, supported
tools, cost telemetry, and capability limitations.

The bridge translates portable tasks into runtime-specific dispatch envelopes
only after validation and policy resolution. Unsupported capabilities are
visible before dispatch. Native job and run identifiers remain recorded, while
the vault retains stable task, routine, approval, and trace identities across
runtimes.

## Interaction invariants

- Every meaningful screen has a useful Markdown fallback.
- Live status is visibly distinguished from the last durable projection.
- Estimated, measured, and unknown costs are visually and semantically distinct.
- A model, runtime, or reasoning-depth change is attributable and reversible.
- No dashboard gesture bypasses validation, policy, or approval requirements.
- Runtime failure cannot make durable intent, outcomes, or provenance disappear.
- The operational database can be rebuilt without inventing completed work.

## First vertical slice

The first delightful end-to-end experience is intentionally narrow:

1. Capture a plain-language task in Obsidian and preview its Markdown intent.
2. Choose an available runtime/model profile and see a bounded cost estimate.
3. Watch it move through the unified queue into a live run timeline.
4. Resolve an approval in context when required.
5. Open the output, receipt, activity entry, and attributed Git change.
6. Restart the bridge and reconstruct the same durable story.

Until this slice exists, the reference vault is an experience specification and
demo, while the current bridge remains validation-only.
