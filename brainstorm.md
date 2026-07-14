# Brainstorm: How Obsidian Hermes Comes Together

This document is a thinking space, not a specification. `README.md` and
`specification-1.0.md` already describe *what* the system is and *how* it runs.
This file asks a different question:

> Can Obsidian Hermes be more than documentation of installations, plus Hermes
> and Obsidian glued together with some scripts and a usage plan?

Short answer: **yes.** The installation guide and scripts are the delivery
mechanism, not the product. The product is a *local, transparent operating
environment for a personal agent* — a durable second brain that also acts. This
brainstorm explores what that could mean and how the pieces cohere.

---

## 1. What we actually have today

Stripped to essentials, the current repository defines three moving parts:

* **Obsidian** — the human surface (commands, approvals, dashboards, knowledge).
* **Hermes cron** — the execution engine that runs bounded, fresh-session work.
* **A control bridge + gate scripts** — deterministic, non-LLM glue that decides
  *when* to wake the agent and reconciles routine definitions with real cron jobs.

Everything flows through Markdown as the control plane. That single decision —
Markdown as the interface between intent and action — is the thing that makes
this more than the sum of an install guide and a few cron entries.

## 2. The core idea worth committing to

The unifying concept is a **file-native OODA loop** (Observe, Orient, Decide,
Act) that a human can read, edit, and audit at any moment:

```
Observe   Inbox capture, source ingestion, monitoring
Orient    Maintained wiki: entities, concepts, summaries
Decide    Doctrine, plans, approvals
Act       Approved actions, outputs, receipts
Learn     Outcome review feeding back into doctrine
```

If we make that loop feel *alive and trustworthy*, the installation steps become
incidental. The differentiator is not "we scheduled some scripts"; it is
"knowledge and action share one auditable substrate that outlives any model
session."

## 3. Where it becomes more than documentation

Concrete directions that turn the spec into a living system:

### 3.1 A reference vault, not just prose
Ship an actual `Hermes-Vault/` starter (templates, `AGENTS.md`, `SCHEMA.md`,
example commands, a populated `Home.md`). A user should be able to open it in
Obsidian and *see* the loop before installing anything. Documentation tells;
a seed vault shows.

### 3.2 The control bridge as the real deliverable
The bridge is the piece nobody else has. It is the deterministic reconciler
between "desired routines described in Markdown" and "native Hermes cron jobs."
Building it well — with health reporting, spec hashing, and drift detection —
is what makes the system self-describing and self-healing rather than a pile of
`hermes cron create` commands someone ran once.

### 3.3 Gate scripts as a reusable library
`obsidian-command-gate.py`, `obsidian-inbox-gate.py`, etc. are described but not
provided. Turning them into a small, tested, model-free toolkit (that answers
`{"wakeAgent": true/false}` cheaply) is high-leverage: it is what keeps empty
queues from burning tokens, and it is independently useful to anyone pairing
Obsidian with any agent runtime.

### 3.4 A dashboard that reads like a cockpit
`Home.md` and `Agent Status.md` can become a genuine operational console —
current command, queued work, approvals waiting, blocked items, last backup,
unresolved contradictions. With Dataview/Bases queries this is dynamic, not
hand-maintained. This is where the system stops feeling like scripts and starts
feeling like a product.

### 3.5 Knowledge that compounds
The wiki-ripple + doctrine-synthesis + outcome-review loops are the ambitious
part. Over months they should turn raw captures into evidence-backed
recommendations and then measure whether those recommendations worked. That
feedback edge is what separates a note-taking setup from a system that learns.

## 4. Layers of ambition

A useful way to frame scope is by how far up the value ladder we commit:

| Layer | Description | Feels like |
| ----- | ----------- | ---------- |
| L0 | Install guide + manual scripts | A README |
| L1 | Seed vault + working gate scripts | A starter kit |
| L2 | Control bridge with reconciliation & health | A runtime |
| L3 | Live dashboards + full ingest/knowledge loops | A second brain |
| L4 | Doctrine + outcome feedback + automation discovery | A learning system |

The repository currently sits between L0 and L1. The interesting, defensible
product lives at L2–L4. The path between them is incremental and each layer is
independently useful, which de-risks the build.

## 5. Usage stories that justify the whole thing

Documentation lists features; stories prove value. A few worth designing toward:

* **Drop-and-forget research.** Paste a URL into the inbox. Later, a linked
  summary, extracted entities, and updated concept notes appear — with the
  original preserved and a receipt attached. No chat session required.
* **The morning briefing.** At 06:30 a dashboard summarises new knowledge, open
  approvals, project risks, and yesterday's outcomes. The day starts oriented.
* **Approve-then-act.** Hermes drafts a plan for an external action, hashes it,
  and waits. You approve the exact plan. It executes once, idempotently, and
  files a receipt. Any plan drift re-requires approval.
* **The Friday retrospective.** Outcome review compares past decisions against
  what actually happened and nudges doctrine accordingly.

If these stories feel effortless and trustworthy, the system has become more
than its install steps.

## 6. Risks and honest tensions

* **Complexity vs. local-first simplicity.** Every loop added is more surface to
  understand. The Markdown-first, human-readable guarantee is the antidote —
  guard it fiercely.
* **Agent trust and prompt injection.** Imported content is untrusted data.
  The trust boundary between `raw/` and instructions is load-bearing; it must be
  demonstrated, not just asserted.
* **Runtime coupling.** The design leans on native Hermes cron behaviour
  (fresh sessions, sequential workdir execution, no recursive self-scheduling).
  The control-bridge abstraction is what keeps us from being brittle if that
  runtime shifts.
* **Maintenance drift.** A knowledge system that silently rots is worse than
  none. Wiki-lint, backup verification, and dead-letter handling are not
  optional polish — they are what make the system safe to depend on.

## 7. A suggested next-step sequence

Not a commitment, just the shortest path from "docs" to "living system":

1. **Seed vault (L1).** Commit a runnable starter vault with templates and one
   worked example command already in a terminal state.
2. **Gate scripts (L1).** Provide real, tested, model-free gate scripts.
3. **Minimal loop end-to-end (L2).** Inbox → command → ingest → knowledge →
   output → receipt → dashboard, on a single machine.
4. **Control bridge (L2).** Reconcile routine notes to cron jobs with health and
   drift reporting.
5. **Live dashboard (L3).** Replace static status with dynamic queries.
6. **Synthesis + feedback (L4).** Doctrine, outcome review, automation discovery.

Each step is shippable and demonstrable on its own.

## 8. The one-line thesis

**Obsidian Hermes is not an install guide with scripts attached; it is a
Markdown-native operating environment where a personal agent observes, orients,
decides, and acts — and where a human can read and correct every step.** The
documentation, scripts, and usage plan are how we deliver that idea, not the
idea itself.

---

*This is a brainstorm and is intentionally exploratory. Anything here that
survives scrutiny should graduate into `README.md`, `specification-1.0.md`, or a
concrete issue; anything that does not can simply be deleted.*
