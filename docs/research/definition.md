**Obsidian + Hermes Agent**

Definitive use cases, operating models, and reference architecture

Using Obsidian as the human-visible knowledge environment and primary control surface, with Hermes as the execution, retrieval, automation, and learning layer.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>Core thesis</strong></p>
<p>The strongest combined design is not simply “Hermes reads an Obsidian vault.” It is a closed operating loop in which the user thinks, structures, delegates, reviews, and approves work in Obsidian while Hermes performs the underlying actions and writes durable results back into the vault.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**Version 1.0**

11 August 2026

Source synthesis: three supplied Hermes–Obsidian transcripts

# Contents

| **Section**                                  | **Purpose**                                                                                   |
|----------------------------------------------|-----------------------------------------------------------------------------------------------|
| Executive summary                            | The definitive recommendation and the principles that reconcile the three source approaches.  |
| 1\. The combined system                      | Definitions, evidence status, and the division of responsibility between Obsidian and Hermes. |
| 2\. Complete capability catalogue            | All major ways the two systems can be used together.                                          |
| 3\. Interaction and operating modes          | Desktop, mobile, dashboard, headless, autonomous, and Obsidian-first control patterns.        |
| 4\. Reference architecture                   | The layered system design and how source tensions should be resolved.                         |
| 5\. Memory and context engineering           | Core memory, on-demand retrieval, provenance, and controlled compounding.                     |
| 6\. Skills, prompts, and agent configuration | Skill visibility, curation, scoping, telemetry, and self-improvement.                         |
| 7\. Deployment and synchronisation models    | Local, hybrid, VPS, multi-device, and multi-agent options.                                    |
| 8\. Use-case catalogue by domain             | Research, content, software, operations, personal knowledge, and more.                        |
| 9\. Obsidian-first UX and vault design       | Recommended folders, task contracts, run objects, approvals, and commands.                    |
| 10\. Governance, security, and reliability   | Permissions, human authority, secrets, versioning, budgets, and recovery.                     |
| 11\. Implementation roadmap                  | A staged path from simple shared memory to a governed agent operating environment.            |
| 12\. Decision guide and conclusion           | Which operating model to choose and the final design position.                                |
| Appendices                                   | Source map, minimum viable setup, and a representative daily workflow.                        |

All major sections use Word heading styles, so the Navigation pane can be used as an interactive table of contents.

# Executive summary

Obsidian and Hermes can be combined at several levels of maturity. At the simplest level, Obsidian is an external memory store that gives Hermes persistent access to notes, goals, past work, and business context. At the next level, the vault becomes a library of “living files”: Markdown notes, procedures, outputs, and skills that can be inspected by a person and reused by one or more agents. A further level adds mobile access, scheduled jobs, long-running goals, dashboard observability, and a self-improvement loop. The most capable design makes Obsidian the primary human experience for complex work and treats Hermes as a headless execution service beneath it.

The three sources support the same underlying model but emphasise different parts of it. The first focuses on a shared memory vault and mission-control concept. The second demonstrates mobile access, local storage, session and skill learning, channel-specific personalities, traces, and operational dashboards. The third frames Obsidian as the best human interface for viewing and editing the agent’s files, introduces “living files,” explains always-on versus on-demand context, and demonstrates a synced VPS workflow and long-running goal execution.

*Source basis: S1 0:00-10:30; S2 0:00-15:45; S3 0:00-30:17.*

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>Definitive recommendation</strong></p>
<p>Use Obsidian as the durable human-visible system of record for knowledge, tasks, agents, skills, runs, approvals, and outputs. Run Hermes locally or on an always-on host as the execution layer. Load a small core identity and policy context on every run, retrieve only relevant vault material on demand, expose only a curated skill set for each task, and require review for durable memory or skill changes.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## The seven design principles

> 1\. Obsidian is the user-facing environment; Hermes is the worker. Chat remains useful, but durable work should become notes, tasks, runs, decisions, or artifacts rather than disappear into transcripts.
>
> 2\. The vault is a shared source of truth, not a prompt that is injected wholesale. Core memory stays small; project notes and skills are retrieved only when relevant.
>
> 3\. Every useful output should become a living file. Research, plans, decisions, transcripts, procedures, and generated artifacts should be saved into the vault with links and provenance.
>
> 4\. The full skill catalogue may be visible in Obsidian, but only a narrow relevant subset should be active for any agent, channel, project, or run.
>
> 5\. Automatic learning should produce reviewable proposals or diffs. User-authored facts and explicit corrections must outrank inferred memories.
>
> 6\. Execution must be observable and interruptible. Runs need status, trace, cost, outputs, warnings, and approval checkpoints.
>
> 7\. Deployment follows the use case: local-only for maximum privacy and deep work; synced hybrid for most users; VPS or dedicated host for 24/7 access, mobile workflows, and scheduled automation.

## What changes when Obsidian is the primary UX

The primary object changes from a chat session to a durable work item. A project note can declare its goal, context, permitted skills, completion criteria, and required approvals. Hermes can execute one or many sessions against that object, while Obsidian continues to show the task, its runs, its outputs, its decisions, and any proposed learning. This makes the system inspectable, resumable, and much easier to govern.

The resulting system is best understood as a personal or organisational agent operating environment: a human-readable semantic layer in Markdown, backed by an agent runtime that can retrieve, act, schedule, delegate, learn, and write back.

# 1. The combined system

## 1.1 Division of responsibility

| **Layer**                    | **Primary responsibility**                                                               | **What belongs there**                                                                                                   |
|------------------------------|------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| Obsidian                     | Human understanding, intent, editing, navigation, review, and durable knowledge.         | Projects, notes, tasks, decisions, skills, prompts, approvals, outputs, dashboards, and linked context.                  |
| Hermes                       | Planning, retrieval, tool use, orchestration, scheduling, memory review, and execution.  | Sessions, active runs, tool calls, model routing, cron execution, skill invocation, and learning proposals.              |
| Sync / bridge                | Keep authorised devices and the runtime aligned; translate file state into agent events. | Obsidian Sync or another synchronisation mechanism, filesystem watchers, symlinks, queues, locks, and conflict handling. |
| Models, tools, and subagents | Perform specialised reasoning or external actions.                                       | Research tools, coding agents, APIs, browsers, custom skills, and local or hosted models.                                |

## 1.2 Definitions used in this document

| **Term**          | **Definition**                                                                                                                                                                                    |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Living file       | A human-readable file that an authorised agent can retrieve and use as context, memory, a procedure, a skill, a prompt component, or an output. The source uses Markdown as the principal format. |
| Shared brain      | A common vault that multiple agents can read from and write to. It is a shared source, not a requirement to load the entire vault into every context window.                                      |
| Core memory       | The small always-loaded set of identity, preferences, corrections, policies, and routing guidance. One source refers to a SOUL file; another shows user.md and memory.md.                         |
| On-demand context | Notes, skills, project files, and past outputs selected only when relevant to the current task.                                                                                                   |
| Skill             | A reusable procedure or capability description that instructs Hermes how to perform a class of work or delegate it to another agent or tool.                                                      |
| Run               | One execution instance against a durable task or goal, including plan, status, trace, costs, outputs, warnings, and approvals.                                                                    |
| Control plane     | The place where the user declares intent, chooses scope, observes progress, grants authority, and changes system behaviour. This document recommends Obsidian for that role.                      |

## 1.3 Evidence status

| **Label**        | **Meaning**                                                                                              |
|------------------|----------------------------------------------------------------------------------------------------------|
| **Demonstrated** | The supplied source describes or visibly walks through the capability.                                   |
| **Described**    | The source claims the capability but does not provide enough detail to assess implementation quality.    |
| **Synthesised**  | The conclusion follows by combining multiple source ideas.                                               |
| **Recommended**  | A design extension proposed in this document to make the system safer, more predictable, or more usable. |
| **Optional**     | A useful extension that is not necessary for the minimum viable setup.                                   |

# 2. Complete capability catalogue

The following catalogue separates the many distinct ways Obsidian and Hermes can be used. Several capabilities overlap, but each represents a different user value or operating pattern.

## 2.1 Knowledge, memory, and context

| **Capability**              | **What it enables**                                                                                                          | **Status**       | **Evidence**               |
|-----------------------------|------------------------------------------------------------------------------------------------------------------------------|------------------|----------------------------|
| Persistent personal memory  | Hermes reads durable facts, preferences, goals, and corrections instead of starting from a blank session.                    | **Demonstrated** | S1 0:00-2:36; S2 1:08-3:59 |
| Project and business memory | The vault stores clients, projects, plans, team information, prior attempts, and historical decisions.                       | **Demonstrated** | S1 2:44-4:38               |
| Historical recall           | Hermes can answer questions such as what was done last month by retrieving relevant notes and outputs.                       | **Demonstrated** | S1 0:46-1:32               |
| Shared cross-agent context  | Hermes, Claude-style coding agents, and other tools can use one Markdown knowledge source.                                   | **Described**    | S1 6:29-9:31; S3 3:15-3:32 |
| Semantic knowledge graph    | Obsidian links, backlinks, folders, and graph views make agent knowledge visible to the user.                                | **Demonstrated** | S3 0:32-1:13; 4:26-4:44    |
| Output compounding          | Generated research, plans, procedures, and artifacts remain available for future work instead of being lost in chat history. | **Synthesised**  | S1 4:04-4:38; S3 4:44-5:14 |
| Vault curation              | Hermes can organise notes, improve structure, add links, and maintain the second brain.                                      | **Described**    | S1 7:34-8:15; S3 3:32-4:02 |
| Capture inbox               | Ideas, brain dumps, links, and requests can be sent from a phone and stored in the vault for later processing.               | **Demonstrated** | S2 5:18-6:21               |

## 2.2 Human control, editing, and observability

| **Capability**                 | **What it enables**                                                                                                         | **Status**       | **Evidence**                                               |
|--------------------------------|-----------------------------------------------------------------------------------------------------------------------------|------------------|------------------------------------------------------------|
| Visible agent files            | The user can inspect memory, sessions, skills, outputs, and folder structure rather than treating the agent as a black box. | **Demonstrated** | S2 7:04-7:33; S3 0:32-1:19                                 |
| Direct skill editing           | A skill Markdown file can be opened, understood, and changed in Obsidian; the runtime can use the revised file.             | **Demonstrated** | S3 26:16-27:45                                             |
| Prompt and personality editing | Identity, memory rules, routing, wiki-link conventions, tone, and channel purpose can be configured in readable files.      | **Demonstrated** | S2 13:35-15:23                                             |
| Run traces and interruption    | The user can see which capability Hermes invoked, stop or interrupt execution, and redirect the work.                       | **Demonstrated** | S2 12:27-13:10                                             |
| Dashboard operations           | Sessions, gateway status, scheduled jobs, traces, message search, model usage, and skill usage can be inspected.            | **Demonstrated** | S2 10:12-11:38                                             |
| Obsidian mission control       | Projects, tasks, outputs, memory, and agent state are brought into one visual operating environment.                        | **Synthesised**  | S1 7:34-9:31; S3 0:32-1:19                                 |
| Approval notes                 | A user changes a durable note from pending to approved to authorise a consequential action.                                 | **Recommended**  | Extension of source observability and human-control themes |
| Task and run objects           | Complex work is controlled through durable Markdown objects rather than transient chat sessions.                            | **Recommended**  | Extension of living files + mission-control model          |

## 2.3 Access and interaction

| **Capability**           | **What it enables**                                                                                                          | **Status**       | **Evidence**                     |
|--------------------------|------------------------------------------------------------------------------------------------------------------------------|------------------|----------------------------------|
| Hermes CLI               | Direct terminal conversation and command execution, similar to a coding-agent harness.                                       | **Demonstrated** | S2 0:25-0:45; 15:25-15:45        |
| Discord or Telegram      | Remote access to vault-aware Hermes from a phone, including research, capture, project status, and skill execution.          | **Demonstrated** | S2 0:33-1:02; 5:18-6:21          |
| Per-channel contexts     | Different channels can represent content, coding, vault operations, or areas of life with isolated skills and personalities. | **Demonstrated** | S2 13:13-14:24; 15:37-15:45      |
| Obsidian side by side    | The user reviews plans and edits context in Obsidian while pairing with Hermes or a coding agent for deep work.              | **Demonstrated** | S2 6:21-7:01                     |
| Multi-device vault       | The same notes, skills, and outputs can appear on desktop, phone, and an authorised server.                                  | **Demonstrated** | S3 1:36-2:04; 18:40-26:03        |
| Always-on service        | Hermes can run on a VPS or dedicated host for 24/7 access, scheduled work, and long-running goals.                           | **Demonstrated** | S3 6:14-8:53; 16:18-18:40        |
| Obsidian-native commands | Commands such as Run task, Approve action, Stop run, or Ask about note can be exposed through an Obsidian plugin.            | **Recommended**  | Extension of Obsidian-primary UX |

## 2.4 Execution, automation, and orchestration

| **Capability**          | **What it enables**                                                                                                           | **Status**       | **Evidence**                                             |
|-------------------------|-------------------------------------------------------------------------------------------------------------------------------|------------------|----------------------------------------------------------|
| Research automation     | Search, collect, compare, summarise, and save source material into the vault.                                                 | **Demonstrated** | S2 5:34-6:21; S3 28:34-30:17                             |
| Media ingestion         | Find videos, fetch transcripts, and store each source as a Markdown file for later analysis.                                  | **Demonstrated** | S2 1:30-1:55; S3 28:34-30:17                             |
| Long-running goal mode  | A verifiable outcome can remain active until its completion criteria are met.                                                 | **Demonstrated** | S3 28:29-30:17                                           |
| Scheduled routines      | Hermes can create and execute cron jobs such as a morning routine or recurring research task.                                 | **Demonstrated** | S2 10:20-11:33                                           |
| Coding-agent delegation | Hermes can route specialised implementation work to another coding agent through a skill.                                     | **Described**    | S2 8:12-8:18; 16:37-16:56                                |
| Model switching         | The harness can use different models and agents without changing the vault knowledge layer.                                   | **Described**    | S2 0:39-0:45; 8:37-9:08                                  |
| Multi-agent handoff     | One agent writes a note or artifact that another agent reads on a later run.                                                  | **Described**    | S1 8:40-9:31                                             |
| Project orchestration   | A project can be decomposed into research, planning, implementation, review, and remediation runs that share durable context. | **Recommended**  | Extension of tasks, runs, shared context, and delegation |

## 2.5 Learning and self-improvement

| **Capability**           | **What it enables**                                                                                       | **Status**       | **Evidence**                                               |
|--------------------------|-----------------------------------------------------------------------------------------------------------|------------------|------------------------------------------------------------|
| User-profile learning    | A review agent extracts stable preferences, desires, corrections, and personal facts into durable memory. | **Demonstrated** | S2 1:08-3:59                                               |
| Session learning         | Stale or expiring sessions are reviewed for memories that should survive the session.                     | **Demonstrated** | S2 2:28-3:15                                               |
| Skill learning           | Repeated or successful workflows can be converted into reusable skill files.                              | **Demonstrated** | S2 1:15-2:04; 3:59-5:12                                    |
| Retrospective proposals  | The agent can show a proposed memory or skill change and the diff it intends to apply.                    | **Demonstrated** | S2 4:03-4:50                                               |
| Telemetry-driven pruning | Skill-use analytics can identify valuable, unused, overlapping, or outdated skills.                       | **Synthesised**  | S2 10:48-12:24                                             |
| Approval-gated learning  | Memory and skill changes are proposed, reviewed, edited, and then committed.                              | **Recommended**  | Safer synthesis of self-improvement + human-control themes |

# 3. Interaction and operating modes

## 3.1 Desktop deep-work mode: Obsidian plus Hermes CLI

In this mode, Obsidian is open beside the Hermes terminal. The user reads project notes, edits plans, links evidence, and reviews outputs while Hermes performs retrieval and execution. This is the best fit for ambiguous, high-value work that benefits from continuous human judgement. The second source explicitly distinguishes mobile capture and research from deep work, where Obsidian is kept side by side with a coding agent so the human remains in the loop.

- Best for architecture, writing, software design, strategic analysis, and work requiring iterative critique.

- Strength: high visibility and immediate correction.

- Limitation: the user must be present and the workstation must be available.

*Source basis: S2 6:21-7:01.*

## 3.2 Mobile gateway mode: Discord or Telegram

Hermes becomes a remote conversational interface to the vault. The user can capture an idea, ask about a project, run a research skill, create an inbox note, or request a background task from a phone. Separate channels can isolate contexts such as content, software, personal administration, or vault maintenance.

- Best for capture, status checks, quick research, voice-driven requests, and starting work away from the computer.

- Strength: low-friction access to the same skills and knowledge from anywhere.

- Limitation: messaging is less suitable for reviewing complex plans, diffs, or large artifacts.

*Source basis: S2 0:00-1:02; 5:18-6:21; 13:13-14:24.*

## 3.3 Dashboard operations mode

The Hermes dashboard remains valuable even in an Obsidian-first system because it exposes runtime-native information: service health, sessions, traces, cron jobs, message history, model usage, token consumption, and top-used skills. Obsidian should not attempt to replace low-level runtime diagnostics. Instead, it should link to or summarise them when a user needs operational detail.

*Source basis: S2 10:12-11:38.*

## 3.4 Living-file workbench mode

Here the main objective is to ensure that agent-accessible work accumulates in Markdown. Notes, standard operating procedures, prompts, skills, transcripts, research, decisions, and generated outputs are all stored as reusable files. The user can inspect them in Obsidian; Hermes can retrieve them when a task requires them; other agents can use the same files without adopting Hermes-specific storage.

The “living file” framing is useful, but it should not be read as a claim that non-agent-accessible files have no value. Its operational meaning is narrower: a file provides more agent leverage when it is accessible, structured, current, and connected to a retrieval path.

*Source basis: S3 2:04-5:25.*

## 3.5 Always-on host or VPS mode

Hermes and a headless copy of the vault run on an always-on machine. Desktop and mobile Obsidian clients synchronise with it. This supports scheduled work, background research, remote messaging, and long-running goals. The third source demonstrates this pattern with a server, a headless synchronisation client, and rapid round-trip creation of notes between the server and desktop.

- Best for 24/7 access, cron jobs, autonomous research, and workflows initiated from a phone.

- Strength: continuity when the user’s laptop is closed.

- Limitation: higher security, reliability, and synchronisation responsibilities.

*Source basis: S3 6:14-8:53; 16:18-26:03.*

## 3.6 Autonomous goal mode

A clear end state is given to Hermes and the agent continues working until the result satisfies measurable criteria or needs permission. The source example requests a fixed number of relevant videos, their transcripts, and separate Markdown files in the vault. The critical design feature is not autonomy by itself; it is a verifiable definition of done.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>Use autonomy only where completion can be checked</strong></p>
<p>Good goals specify quantity, quality, scope, destination, constraints, and permission boundaries. “Research this topic” is weak. “Collect 50 qualifying sources, deduplicate them, save each transcript, and produce a cited synthesis” is materially safer and easier to verify.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

*Source basis: S3 28:29-30:17.*

## 3.7 Multi-agent shared-brain mode

Multiple agents use the same vault as a durable coordination surface. Hermes can write a result, a coding agent can continue the implementation, and a later review agent can inspect both the original task and the generated artifact. The vault provides interoperability because the core files are Markdown. However, each agent should retrieve only the context and capabilities relevant to its role.

*Source basis: S1 6:29-9:31; S3 3:15-3:32.*

## 3.8 Obsidian-first control-plane mode

This is the recommended advanced model for complex Hermes work. The user creates or edits a task note in Obsidian, chooses an agent profile, defines linked context, limits skills, sets completion criteria, and marks the task ready. A bridge detects the state change, starts Hermes, and writes progress, warnings, approvals, and outputs back into linked run notes. The user can pause, cancel, or approve from Obsidian without needing to remain in a terminal session.

*Source basis: Recommended synthesis of S1 mission control, S2 traces and scoping, and S3 Obsidian editing and living files.*

# 4. Reference architecture

<img src="Obsidian_Hermes_Definitive_Guide_assets/media/image1.png" title="Figure 1. Recommended reference architecture for an Obsidian-primary Hermes system." style="width:6.75in;height:3.4562in" alt="Figure 1. Recommended reference architecture for an Obsidian-primary Hermes system." />

*Figure 1. Recommended reference architecture for an Obsidian-primary Hermes system.*

## 4.1 Layered design

> 1\. Human interface layer: Obsidian desktop and mobile are the primary surfaces for durable work. Discord or Telegram provide low-friction remote access. The CLI and dashboard remain expert and operational interfaces.
>
> 2\. Semantic state layer: the Markdown vault stores projects, tasks, context, memory, skills, prompts, outputs, decisions, and links. It is the portable human-readable knowledge substrate.
>
> 3\. Bridge and operational layer: synchronisation, file watching, symlinks, queues, locks, event sequencing, and approval handling convert vault state into reliable execution.
>
> 4\. Hermes runtime layer: Hermes selects context, plans, invokes skills, delegates to subagents, schedules work, records traces, and proposes memory or skill updates.
>
> 5\. Execution layer: models, browsers, APIs, coding agents, and custom tools perform the work.
>
> 6\. Write-back layer: results, citations, decisions, logs, and proposed learning are projected into the vault as linked living files.

## 4.2 Resolving the apparent tensions in the sources

| **Source tension**                                                                                      | **Definitive resolution**                                                                                                                                               |
|---------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| “One shared brain” versus “do not load the whole vault.”                                                | Use one shared source of truth, but perform scoped retrieval. Shared storage does not imply indiscriminate context injection.                                           |
| A vault may expose 185-200 skills, but large skill sets confuse routing.                                | Keep the full skill registry visible and searchable in Obsidian. Activate only a small, role-specific subset for each agent, channel, project, or run.                  |
| Hermes can automatically update memory and skills, while Obsidian is meant to keep the human in charge. | Automatic review is valuable; automatic durable mutation should be governed. Produce a proposal and diff, then accept, edit, or reject it.                              |
| One source presents local files and symlinks; another presents a VPS as the best setup.                 | Both are valid deployment modes. Local is preferable for privacy and deep work. VPS is preferable for 24/7 access and automation. Hybrid is the general recommendation. |
| Chat is central to Hermes, but Obsidian is proposed as the primary UX.                                  | Use chat for exploration and capture. Convert durable intent and outcomes into project, task, run, decision, memory, or skill objects in Obsidian.                      |

## 4.3 Operational state should not rely on Markdown alone

Markdown is excellent for semantic state and human review, but it is not a transactional database. Concurrent runs, process identifiers, event ordering, retries, locks, and partial failures require a small operational store such as SQLite or an append-only event log. The vault should remain the user-visible projection and durable semantic record; the runtime store should protect execution correctness.

*Source basis: Recommended engineering extension; the sources demonstrate files, sessions, traces, and dashboard state but do not specify a transactional control protocol.*

# 5. Memory and context engineering

## 5.1 Two-speed context: always-on core and on-demand vault

The third source gives the most useful context model: a small always-loaded memory contains essential identity and preferences, while notes and skills are loaded only when relevant. This reconciles personalisation with context-window efficiency. The system should never read the entire vault into every run.

| **Context tier**                  | **Typical contents**                                                                         | **Loading rule**                                                          |
|-----------------------------------|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| Tier 1: core policy               | Identity, answer style, hard constraints, safety rules, routing rules, critical corrections. | Always loaded; deliberately small.                                        |
| Tier 2: human-authored truth      | Explicit goals, project briefs, decisions, preferences, people, and organisational policies. | Loaded by project link, agent profile, or explicit reference.             |
| Tier 3: approved Hermes memory    | Stable learned preferences, summaries, and recurring facts accepted by the user.             | Retrieved when relevant; lower authority than explicit human corrections. |
| Tier 4: project knowledge         | Notes, research, plans, source material, SOPs, and previous outputs.                         | Scoped search within declared context roots.                              |
| Tier 5: sessions and traces       | Prior conversations, tool calls, run logs, and intermediate state.                           | Search only when continuity or debugging requires it.                     |
| Tier 6: ephemeral working context | Current plan, scratch data, temporary calculations, and tool responses.                      | Run-local; discarded or summarised at completion.                         |

*Source basis: S3 5:14-6:14; S2 14:35-15:23.*

## 5.2 Authority and provenance

The vault should distinguish who asserted a fact and how confident the system should be. A useful precedence order is: explicit user correction; approved policy or project decision; human-authored note; approved Hermes memory; derived summary; unreviewed inference. Every durable memory should carry provenance, date, source run, and review status.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>Memory rule</strong></p>
<p>The best memory is not the largest memory. It is the smallest current set of high-value facts that prevents repetition, improves decisions, and can be traced back to an authoritative source.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 5.3 Retrieval sequence

> 1\. Start with the current note, task, or message and its explicit links.
>
> 2\. Load the selected agent profile and the project’s declared context roots.
>
> 3\. Retrieve exact entities, recent decisions, and relevant outputs before broad semantic search.
>
> 4\. Apply a token budget and stop adding context when marginal relevance falls below the threshold.
>
> 5\. Preserve citations or links to every source file used.
>
> 6\. Write a compact context manifest into the run note so the user can see what Hermes relied on.

## 5.4 Controlled learning loop

<img src="Obsidian_Hermes_Definitive_Guide_assets/media/image2.png" title="Figure 2. The recommended compounding loop adds a human review gate before durable memory or skill changes." style="width:6.75in;height:2.7064in" alt="Figure 2. The recommended compounding loop adds a human review gate before durable memory or skill changes." />

*Figure 2. The recommended compounding loop adds a human review gate before durable memory or skill changes.*

The second source describes three learning triggers: periodic conversation review, skill review after repeated interaction, and review of stale sessions. It also shows a retrospective workflow that presents a proposed change and a diff. The definitive design keeps those triggers but changes the default write path from silent mutation to reviewable proposal for any high-impact memory or skill change.

*Source basis: S2 2:06-4:50.*

## 5.5 Memory hygiene

- Corrections must supersede older conflicting memories rather than coexist ambiguously.

- Time-sensitive facts need expiry or review dates.

- Project-specific facts should not leak into unrelated project contexts.

- Sensitive memories should have narrower access scopes than ordinary notes.

- Low-value session summaries should be archived instead of promoted to core memory.

- The user should be able to inspect, edit, reject, or delete any learned memory in Obsidian.

# 6. Skills, prompts, and agent configuration

## 6.1 The skill catalogue and the active skill set are different things

The sources appear to disagree about large skill libraries. One celebrates having roughly 185 visible skills in Obsidian; another reports that a similar number makes the model unpredictable because descriptions overlap and consume context. Both observations can be true. Visibility is useful for discovery and maintenance; broad runtime exposure is harmful. The system should therefore maintain a complete registry but load only a curated active set.

*Source basis: S2 7:33-8:18; 11:45-13:32; S3 0:49-1:19; 26:16-27:45.*

## 6.2 Recommended skill metadata

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>---<br />
type: hermes-skill<br />
id: research-youtube-transcripts<br />
status: approved<br />
owner: user<br />
version: 1.3<br />
purpose: Find qualifying videos, fetch transcripts, and save linked source notes.<br />
triggers:<br />
- video research<br />
- transcript collection<br />
permissions:<br />
network: true<br />
filesystem:<br />
write:<br />
- 30 Knowledge/Research/**<br />
deny:<br />
- 90 System/Secrets/**<br />
inputs:<br />
- topic<br />
- target_count<br />
outputs:<br />
- source_notes<br />
- synthesis_note<br />
agents:<br />
- researcher<br />
projects:<br />
- optional<br />
review_after: 2026-11-01<br />
---</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

The metadata makes skills inspectable, testable, and governable. Descriptions should be mutually discriminative so the router can identify the right skill. Overlapping skills should be merged, narrowed, or given explicit precedence rules.

## 6.3 Scope skills by role, channel, and project

- A vault channel may load file organisation, wiki-linking, note capture, and memory-management skills.

- A content channel may load research, outlining, transcript, editing, and publishing procedures.

- A build channel may load repository, testing, code review, and coding-agent delegation skills.

- A project may further restrict skills to those approved for its data and risk level.

- A run may temporarily add one specialist skill with explicit permission.

*Source basis: S2 13:13-14:24.*

## 6.4 Prompt and personality files

The second source shows that agent identity, personality, memory guidance, routing, channel context, and conventions such as always using wiki links can be represented in editable files. Obsidian is a natural interface for these controls because the user can see the complete prompt assembly and change it without searching through hidden configuration directories.

*Source basis: S2 13:35-15:23.*

## 6.5 Skill lifecycle

> 1\. Observe: Hermes detects a recurring successful workflow or the user requests a reusable procedure.
>
> 2\. Propose: Hermes creates a draft skill note with purpose, triggers, steps, permissions, examples, and evidence from the originating run.
>
> 3\. Review: the user edits the skill and resolves overlap with existing skills.
>
> 4\. Test: run the skill against representative cases and record expected outputs.
>
> 5\. Approve: set status to approved and add it to specific agent or project scopes.
>
> 6\. Measure: use dashboard telemetry to track invocation frequency, failures, cost, and value.
>
> 7\. Maintain or retire: update stale instructions, merge duplicates, or disable unused skills.

# 7. Deployment and synchronisation models

## 7.1 Comparison

| **Model**                 | **Best fit**                                                             | **Advantages**                                                                           | **Primary trade-offs**                                                             |
|---------------------------|--------------------------------------------------------------------------|------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Local-only                | Private deep work on one workstation.                                    | Simple ownership; no server; easy direct filesystem access; strong privacy boundary.     | Unavailable when the machine is off; limited mobile and scheduled operation.       |
| Local + messaging gateway | Remote capture and commands while the home workstation remains online.   | Adds mobile access without a full cloud server.                                          | Depends on workstation uptime and secure remote connectivity.                      |
| Synced hybrid             | Most individual and small-team use.                                      | Desktop and phone UX plus an always-on runtime; shared living files; flexible deep work. | Requires conflict handling, backup, and careful secret separation.                 |
| Always-on VPS             | 24/7 automation, scheduled jobs, background research, and remote access. | Continuous availability; easy headless execution; suitable for long-running goals.       | Largest security and operational burden; should use least privilege and isolation. |
| Multi-agent shared vault  | Workflows spanning research, coding, review, and content agents.         | Portable context and file-based handoff across models and tools.                         | Requires strict retrieval scopes, ownership rules, and write coordination.         |

## 7.2 Synchronisation

The third source presents official Obsidian synchronisation and an open-source file-synchronisation alternative, then demonstrates a headless server client. The important architectural requirement is not the vendor: it is a convergent, encrypted or otherwise appropriately protected sync path with clear conflict behaviour, continuous operation, and backups.

- Do not store API keys, passwords, or private runtime credentials in the synced vault.

- Separate user-authored semantic files from high-churn runtime traces to reduce conflicts.

- Use stable identifiers for tasks and runs so renames do not break relationships.

- Version critical skills, prompts, policies, and memory files with Git or another history mechanism.

- Prefer append-only run logs and separate output files over multiple processes editing the same note.

*Source basis: S3 18:40-26:03.*

## 7.3 Local runtime paths and symlinks

The second source demonstrates symlinking Hermes memory, sessions, and skills into the Obsidian vault so the runtime remains the owner of its native files while the user can inspect them in Obsidian. This is a strong pattern for local deployments. For synced or multi-device deployments, high-churn session directories may be better represented by summaries or selective projections rather than fully synchronised.

*Source basis: S2 7:04-7:33.*

## 7.4 Security correction to the source walkthroughs

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>Do not treat root access as a production default</strong></p>
<p>A source walkthrough installs and manages the agent at server root level for convenience. A durable deployment should use a dedicated non-root account or container, narrowly scoped filesystem permissions, separate secrets, outbound network controls where appropriate, and explicit approval for destructive or externally consequential actions.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 8. Use-case catalogue by domain

| **Domain**                    | **Representative workflow**                                                                                            | **Durable vault output**                                                     | **Best interface**                          |
|-------------------------------|------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|---------------------------------------------|
| Research and intelligence     | Collect sources, compare claims, fetch transcripts, synthesise findings, and preserve citations.                       | Source notes, research brief, evidence map, unresolved questions.            | Mobile request or /go; review in Obsidian.  |
| Content creation              | Capture ideas, research examples, build an outline, draft, edit, and create a reusable content procedure.              | Idea note, source pack, outline, draft, publishing checklist, learned skill. | Mobile capture; desktop deep work.          |
| Software engineering          | Read project context, inspect a repository, create a plan, delegate implementation, run tests, and document decisions. | Task, architecture note, run trace, code-review findings, release notes.     | Obsidian + CLI; specialist coding agent.    |
| Business operations           | Track goals, prepare briefings, monitor projects, draft procedures, and schedule recurring reviews.                    | Operating dashboard, decisions, SOPs, weekly briefing, follow-up tasks.      | Obsidian control plane + scheduled jobs.    |
| Chief-of-staff support        | Turn meetings, inbox items, and priorities into an organised plan and decision queue.                                  | Daily plan, waiting list, approval queue, stakeholder notes.                 | Mobile gateway + Obsidian dashboard.        |
| Personal knowledge management | Capture thoughts, link concepts, summarise reading, surface related notes, and maintain knowledge hygiene.             | Linked notes, topic maps, reading summaries, memory proposals.               | Obsidian primary UX.                        |
| Learning and study            | Build topic notes, quiz from sources, compare explanations, and schedule spaced reviews.                               | Study guide, question bank, misconceptions, progress log.                    | Obsidian + scheduled prompts.               |
| Meetings and decisions        | Ingest notes, extract actions, identify decisions, link supporting evidence, and update projects.                      | Meeting note, decision record, task notes, memory updates.                   | Mobile or desktop capture; Obsidian review. |
| Media and transcript library  | Find relevant media, save transcripts, tag topics, and generate cross-source synthesis.                                | One Markdown source note per item, index, synthesis, citation graph.         | Long-running goal mode.                     |
| Personal operations           | Track routines, calories, habits, travel preparation, or recurring household workflows.                                | Daily logs, dashboards, reminders, reusable procedures.                      | Mobile gateway + cron.                      |
| Legal or policy review        | Compare a document against declared policies, identify issues, and prepare an evidence-linked review.                  | Review memo, clause notes, risk list, approval record.                       | Obsidian deep work with human approval.     |
| Multi-agent collaboration     | Research agent gathers evidence, coding agent implements, review agent critiques, and Hermes coordinates handoffs.     | Shared task graph, handoff notes, artifacts, review findings.                | Shared vault + scoped agent profiles.       |

## 8.1 A representative research workflow

> 1\. The user captures a research question from a phone or creates a task note in Obsidian.
>
> 2\. Hermes reads the linked project brief and activates only the research, transcript, and citation skills.
>
> 3\. A long-running goal collects a fixed number of qualifying sources and saves each as a living file.
>
> 4\. Hermes creates a synthesis note, a source index, and a list of contradictory or low-confidence claims.
>
> 5\. The user reviews the result in Obsidian, corrects scope, and approves any durable memory or skill proposal.
>
> 6\. Future work retrieves the source pack instead of repeating the same research.

## 8.2 A representative software workflow

> 1\. The project note defines architecture, constraints, repository links, and approval boundaries.
>
> 2\. Hermes creates a planning run and retrieves the relevant design notes and prior decisions.
>
> 3\. A coding-agent skill delegates implementation while Hermes tracks status and writes an execution trace.
>
> 4\. Tests and review findings become linked run artifacts rather than terminal-only output.
>
> 5\. The user approves the final change or requests remediation from the task note.
>
> 6\. A retrospective proposes updates to the project memory or a reusable implementation skill.

# 9. Obsidian-first UX and vault design

## 9.1 Recommended vault structure

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>00 Inbox/<br />
01 Dashboard/<br />
10 Projects/<br />
20 Areas/<br />
30 Knowledge/<br />
40 Memory/<br />
Human/<br />
Hermes Approved/<br />
Proposals/<br />
50 Agents/<br />
60 Skills/<br />
70 Tasks/<br />
80 Runs/<br />
90 Automations/<br />
95 Approvals/<br />
98 Archive/<br />
99 System/<br />
Hermes Runtime Links/<br />
Policies/<br />
Templates/</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

The folder structure is intentionally legible rather than clever. Links and metadata should carry most relationships. High-churn runtime data should remain separate from user-authored notes, and only the portions that add human value should be projected into the main vault.

- Use stable IDs in frontmatter so links survive renames and moves.

- Prefer links and metadata over deeply nested folder taxonomies.

- Separate human-authored truth, approved Hermes memory, unreviewed proposals, and runtime traces.

- Write task outputs into project or knowledge folders; keep raw operational state in the system area.

- Archive completed runs without deleting the decisions, evidence, and reusable outputs they produced.

## 9.2 Task contract

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>---<br />
type: hermes-task<br />
id: task-2026-0811-001<br />
status: ready<br />
project: "[[JAPER Secure Compute]]"<br />
agent: architect<br />
priority: high<br />
goal: Assess the authentication architecture and produce a cited design review.<br />
context:<br />
- "[[Authentication Architecture]]"<br />
- "[[Security Requirements]]"<br />
context_roots:<br />
- 10 Projects/JAPER<br />
- 30 Knowledge/Security<br />
skills:<br />
- repository-analysis<br />
- architecture-review<br />
- technical-writing<br />
permissions:<br />
network: false<br />
write:<br />
- 10 Projects/JAPER/Reviews/**<br />
approval:<br />
required_before:<br />
- modify_repository<br />
- send_external_message<br />
completion_criteria:<br />
- Findings cite source files.<br />
- Risks are ranked.<br />
- Recommendations include trade-offs.<br />
output: "[[Authentication Architecture Review]]"<br />
---</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

Changing status from draft to ready can be treated as the run command. The contract gives Hermes a bounded world: a goal, context, permitted skills, authority, completion criteria, and a destination.

### 9.2.1 Task lifecycle states

| **State**          | **Meaning**                                                                        |
|--------------------|------------------------------------------------------------------------------------|
| draft              | The user is still defining the task; Hermes does not execute it.                   |
| ready              | The task is complete enough to queue.                                              |
| queued / running   | Hermes has accepted the task or is actively executing a run.                       |
| blocked            | Execution cannot continue because information, access, or a dependency is missing. |
| approval-required  | A consequential step is waiting for explicit human authority.                      |
| completed          | The completion criteria have been met and outputs are linked.                      |
| failed / cancelled | The run ended without completion; the reason and last checkpoint are recorded.     |

## 9.3 Run object

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>---<br />
type: hermes-run<br />
id: run-2026-0811-113302<br />
task: "[[task-2026-0811-001]]"<br />
status: approval-required<br />
agent: architect<br />
started: 2026-08-11T11:33:02+10:00<br />
model_profile: reasoning<br />
context_manifest:<br />
- "[[Authentication Architecture]]"<br />
- "[[Security Requirements]]"<br />
skills_used:<br />
- repository-analysis<br />
- architecture-review<br />
cost:<br />
tokens: 18420<br />
approval_request: "[[Approve repository patch]]"<br />
outputs:<br />
- "[[Authentication Architecture Review]]"<br />
---<br />
<br />
# Plan<br />
1. Read the project brief and constraints.<br />
2. Inspect authentication entry points.<br />
3. Trace validation and failure paths.<br />
4. Compare implementation to stated requirements.<br />
5. Produce findings and recommendations.<br />
<br />
# Activity<br />
- 11:33 Loaded declared context.<br />
- 11:35 Inspected authentication middleware.<br />
- 11:42 Found an unresolved trust-boundary ambiguity.<br />
<br />
# Warnings<br />
The next step would modify repository files and requires approval.</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 9.4 Approval object

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>---<br />
type: hermes-approval<br />
id: approval-2026-0811-004<br />
run: "[[run-2026-0811-113302]]"<br />
status: pending<br />
action: modify_repository<br />
risk: medium<br />
requested_by: architect<br />
expires: 2026-08-12T17:00:00+10:00<br />
---<br />
<br />
## Proposed action<br />
Apply the reviewed patch to the authentication validation layer.<br />
<br />
## Evidence<br />
- [[Authentication Architecture Review#Finding 3]]<br />
- [[Test Plan - Authentication]]<br />
<br />
## Decision<br />
- [ ] Approve<br />
- [ ] Reject<br />
- [ ] Request changes</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 9.5 Agent profile

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>---<br />
type: hermes-agent<br />
id: architect<br />
purpose: Analyse system design and produce evidence-linked recommendations.<br />
core_context:<br />
- "[[Architecture Principles]]"<br />
- "[[Security Policy]]"<br />
skills:<br />
- repository-analysis<br />
- architecture-review<br />
- diagramming<br />
memory_scope:<br />
- projects<br />
- decisions<br />
- architecture<br />
write_scope:<br />
- 10 Projects/**/Reviews/**<br />
- 80 Runs/**<br />
forbidden:<br />
- deploy<br />
- send_external_message<br />
personality: rigorous, concise, explicit about uncertainty<br />
---</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 9.6 Automation object

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th>---<br />
type: hermes-automation<br />
id: morning-briefing<br />
enabled: true<br />
schedule: "0 7 * * 1-5"<br />
agent: chief-of-staff<br />
context:<br />
- "[[Active Projects]]"<br />
- "[[Waiting]]"<br />
- "[[Calendar Commitments]]"<br />
output_template: "01 Dashboard/Daily/{{date}} Morning Briefing"<br />
permissions:<br />
write:<br />
- 01 Dashboard/Daily/**<br />
---</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 9.7 Proposed Obsidian commands

| **Command**                                | **Effect**                                                                           |
|--------------------------------------------|--------------------------------------------------------------------------------------|
| Hermes: Run current task                   | Validate the current note, mark it queued, and start a run.                          |
| Hermes: Ask about current note             | Open a scoped conversation using the note and its links as context.                  |
| Hermes: Create task from selection         | Turn selected text into a linked task contract.                                      |
| Hermes: Show run trace                     | Open the active run note or runtime trace.                                           |
| Hermes: Pause / stop run                   | Send an interrupt and update the run state.                                          |
| Hermes: Approve action                     | Resolve the linked approval object and resume execution.                             |
| Hermes: Save as memory proposal            | Create a provenance-linked memory proposal instead of directly changing core memory. |
| Hermes: Convert workflow to skill proposal | Generate a draft skill from the selected run and its trace.                          |

## 9.8 Declarative plus conversational UX

The strongest UX combines two modes. Conversation is best for exploration, capture, clarification, and quick commands. Declarative notes are best for goals, constraints, plans, authority, completion criteria, and state. A good system lets a conversation create or update a durable object, and lets a durable object open a scoped conversation. Neither mode should replace the other.

# 10. Governance, security, and reliability

| **Risk**                               | **Control**                                                                                                                 |
|----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| Unbounded vault access                 | Declare context roots and deny sensitive folders by default. Record a context manifest for each run.                        |
| Skill confusion or unintended tool use | Use curated active skill sets, discriminative descriptions, project scopes, and explicit precedence.                        |
| Silent memory corruption               | Separate human truth from inferred memory; require proposals, provenance, and review for durable changes.                   |
| Self-modifying skills                  | Generate diffs, test in a sandbox, require approval, and keep version history.                                              |
| Destructive or external actions        | Use permission classes and approval gates for deletion, deployment, purchases, messages, or external publication.           |
| Secrets in the vault                   | Keep credentials in a secret manager or environment variables outside synchronised Markdown.                                |
| Server compromise                      | Use a dedicated non-root account or container, minimum filesystem permissions, patching, logging, and network restrictions. |
| Sync conflict                          | Avoid concurrent edits to the same note; prefer append-only logs, stable IDs, and a defined conflict-resolution policy.     |
| Runaway cost or autonomy               | Apply time, token, model, API, and task budgets; require reauthorisation when a limit is reached.                           |
| Opaque failure                         | Expose trace, current action, last successful checkpoint, retries, warnings, and a kill switch.                             |
| Vendor or model dependency             | Keep knowledge and procedures in portable Markdown and isolate provider-specific configuration.                             |
| Stale knowledge                        | Add review dates, freshness metadata, and scheduled audits for skills, policies, and critical memories.                     |

## 10.1 Human authority model

The user should retain final authority over durable facts, permissions, consequential actions, and the agent’s operating law. Hermes may recommend, plan, and execute within granted scope. It should not treat access to a vault or skill as blanket authority to use every capability against every file.

## 10.2 Observability requirements

- Current task, run status, agent, and model profile.

- Context files selected and the reason each was included.

- Skills and tools invoked, with inputs and outputs.

- External side effects and pending approvals.

- Token, time, API, and monetary consumption where available.

- Artifacts created or modified.

- Warnings, retries, and failure classification.

- Memory or skill changes proposed at the end of the run.

# 11. Implementation roadmap

| **Stage**                     | **Scope**                                                                                   | **Acceptance test**                                                                      |
|-------------------------------|---------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| 1\. Shared vault              | Point Hermes at a controlled Obsidian vault or expose native Hermes files through symlinks. | Hermes can read a test note and write a result that is visible in Obsidian.              |
| 2\. Context discipline        | Define core memory, project context roots, and human/agent memory separation.               | A run shows only relevant files and does not load the whole vault.                       |
| 3\. Skill curation            | Catalogue all skills in Obsidian; activate small role-specific sets.                        | Ambiguous prompts no longer trigger unrelated skills; active skills are visible per run. |
| 4\. Living outputs            | Require research, decisions, plans, and artifacts to be saved with links and provenance.    | A completed task can be resumed later without redoing the research.                      |
| 5\. Mobile and sync           | Add secure multi-device sync and an optional messaging gateway.                             | A phone request creates a vault note and the desktop sees it without manual copying.     |
| 6\. Runs and observability    | Create task/run objects, trace summaries, stop controls, and dashboard links.               | The user can identify what Hermes is doing and interrupt it.                             |
| 7\. Approvals and permissions | Add action classes, approval notes, budgets, and least-privilege runtime accounts.          | Consequential actions pause until the correct approval is recorded.                      |
| 8\. Controlled learning       | Turn memory and skill updates into proposals with diffs and provenance.                     | The user can accept, edit, or reject every durable learning change.                      |
| 9\. Automation                | Add cron jobs and verifiable long-running goals.                                            | Scheduled and autonomous work produces traceable outputs within defined limits.          |
| 10\. Multi-agent operation    | Add specialist agent profiles and file-based handoffs.                                      | Agents share approved knowledge without sharing every skill or context by default.       |

## 11.1 Minimum recommended first implementation

> 1\. Create a dedicated vault or clearly bounded Hermes workspace within an existing vault.
>
> 2\. Expose user.md, memory.md, approved skills, and selected session summaries in a visible system folder.
>
> 3\. Define one small core memory file and one project context file.
>
> 4\. Choose five to fifteen trusted skills for the first agent profile; disable the rest from runtime routing.
>
> 5\. Require every completed task to write a result note and a concise run summary.
>
> 6\. Add one mobile channel or one scheduled job only after the local workflow is predictable.
>
> 7\. Introduce learning proposals after the user can inspect and correct normal runs.
>
> 8\. Add the Obsidian task/control bridge only when the underlying file and permission contracts are stable.

# 12. Decision guide and conclusion

## 12.1 Which model should be used?

| **Need**                                     | **Recommended model**                                                                                |
|----------------------------------------------|------------------------------------------------------------------------------------------------------|
| Persistent recall and fewer repeated prompts | Local vault memory with small core context and scoped retrieval.                                     |
| Ideas and research from a phone              | Discord or Telegram gateway writing to an Obsidian inbox.                                            |
| Careful strategy, architecture, or writing   | Obsidian side by side with Hermes CLI or a specialist agent.                                         |
| 24/7 scheduled work or long-running research | Synced hybrid or always-on host with strict permissions and budgets.                                 |
| Many skills                                  | Full Obsidian registry plus narrow active sets per agent, channel, project, and run.                 |
| Self-improving workflows                     | Memory and skill review agents that create approval-gated proposals and diffs.                       |
| Multiple models or agents                    | Shared Markdown vault with scoped retrieval and explicit handoff notes.                              |
| Complex, governed Hermes work                | Obsidian-first tasks, runs, approvals, traces, and artifacts backed by a runtime bridge.             |
| Maximum privacy                              | Local-only execution, local models where appropriate, and no synced sensitive folders.               |
| Nontechnical daily use                       | Obsidian primary UX with a small command palette and minimal exposure to terminal or server details. |

## 12.2 Final position

Obsidian is valuable to Hermes in at least five independent roles: memory store, living-file knowledge base, skill and prompt editor, observability surface, and human control plane. Hermes is valuable to Obsidian in at least seven roles: conversational gateway, retrieval engine, vault curator, skill runner, automation service, multi-agent orchestrator, and learning system.

The most important architectural move is to externalise durable knowledge and intent from the agent. When memory, procedures, tasks, and outputs live in a human-readable vault, the agent becomes replaceable and the accumulated system remains inspectable. The second most important move is to keep execution scoped: one shared vault does not mean one giant prompt, and one visible skill catalogue does not mean every skill should be active.

The definitive operating model is therefore: Obsidian for human cognition, durable state, and authority; Hermes for retrieval, planning, action, scheduling, and controlled learning; a narrow bridge for synchronisation and events; and explicit governance around permissions, costs, provenance, and self-modification.

# Appendix A. Source map

| **Source**                  | **Primary contribution to this document**                                                                                                                                                                 |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| S1 - Pasted markdown(7).md  | Persistent memory, the shared-brain concept, shared access across agents, outputs feeding later work, and the mission-control framing.                                                                    |
| S2 - Pasted markdown (2).md | Mobile Discord use, CLI and dashboard operation, local files and symlinks, self-improving memory and skills, per-channel skill/personality scoping, traces, analytics, and coding-agent delegation.       |
| S3 - Pasted markdown(8).md  | Obsidian as the visible human interface, living files, skill editing, multi-device and VPS synchronisation, on-demand context, agent-assisted setup, headless operation, and long-running goal execution. |

Source references in this document use transcript identifiers and approximate video time ranges. Recommendations labelled “Recommended” or “Optional” are architectural extensions derived from the source themes rather than capabilities directly demonstrated in the supplied material.

# Appendix B. Minimum viable setup checklist

- A dedicated or bounded Obsidian vault is available to Hermes.

- The runtime can read and write a test note.

- Core memory is small, explicit, and human-editable.

- Project context is linked or declared rather than discovered from the entire vault.

- Only trusted, relevant skills are active.

- Outputs are written back into named project or knowledge locations.

- Sessions, runs, or traces can be inspected and stopped.

- Secrets are outside the vault.

- Backups and version history exist for critical notes, skills, and prompts.

- Automatic memory or skill changes are reviewable.

- Scheduled or autonomous work has completion criteria, permissions, and budgets.

- The user can recover from sync conflict, failed run, or compromised runtime.

# Appendix C. A representative day in the system

> 1\. During a commute, the user sends a voice note to a research channel. Hermes creates an inbox note with the request and links it to the relevant project.
>
> 2\. At the next scheduled briefing, Hermes surfaces the captured idea, current project status, unresolved approvals, and related past research in an Obsidian dashboard note.
>
> 3\. The user converts the idea into a task, adds completion criteria, restricts the skills, and marks it ready.
>
> 4\. Hermes starts a run on the always-on host, gathers sources, and writes a progress trace and source notes into the vault.
>
> 5\. The run reaches an action requiring additional authority and creates an approval note. The user reviews the evidence in Obsidian and approves a narrower action.
>
> 6\. Hermes completes the research, produces a linked synthesis, and updates the task status.
>
> 7\. For deep work, the user opens Obsidian beside a coding or writing agent, using the source pack and project decisions as the shared context.
>
> 8\. At completion, Hermes proposes one memory update and one reusable skill. The user edits and approves the memory, but rejects the skill as too narrow.
>
> 9\. The final artifacts remain linked to the project, so the next task retrieves them rather than repeating the work.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr class="header">
<th><p><strong>End state</strong></p>
<p>The user can capture, understand, delegate, supervise, approve, and reuse work from one durable environment. Hermes gains rich context and autonomy without becoming opaque or unconstrained.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>
