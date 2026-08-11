# Deek Seek Suggestions

A genuine operating system for turning an Obsidian vault into a structured, self‑executing knowledge engine on top of Hermes cron. The separation of control plane, operational loops, and synthesis loops, the rigorous lease protocols, and the security boundaries are all good.

Below are enhancements that would further harden, scale, and smooth the experience, grouped by area.

---

### 1. Bridge & Control‑Plane Hardening

**1.1 Active filesystem watchers, not just polling**  
The spec leans on 5‑second polling and filesystem events for the bridge. A dedicated watcher (e.g., `inotify`/`kqueue` via a small binary or Obsidian plugin) would give sub‑second reaction to control‑queue drops, routine edits, or gateway restarts — while still falling back to polling for reliability.

**1.2 Bridge liveness daemon and gateway supervision**  
The bridge should become a long‑running service that not only reconciles routines but also monitors the gateway process. If the gateway stops, the bridge can:
- Set `Agent Status.md` to `offline`
- Attempt a controlled restart via the OS service manager  
- Emit an alert (see §7)  
A separate watchdog cron job *cannot* detect a dead gateway — this must live outside cron.

**1.3 Multi‑machine vault sync conflict resolution**  
If multiple Hermes instances run on different synced copies of the same vault (e.g., via Obsidian Sync or Git), two gateways could both be “active”. Add a **fencing token** (e.g., a machine‑specific lock file or a lease in the vault root that the bridge maintains) so only one instance’s cron loops can execute. The bridge would refuse to start if another instance holds the lock. This prevents duplicate work and partial‑write races across machines.

**1.4 Graceful routine migration and versioning**  
Introduce a `schema_version` field in the routine definition and a migration script. When the bridge detects a routine written for an older schema, it can either refuse it or run a deterministic upgrade before reconciliation. This prevents breakage when the spec evolves.

**1.5 Native Cron Registry as generated documentation**  
`99 System/Hermes Cron Registry.md` could be a Dataview‑queriable table, automatically updated by the bridge. Each row: routine ID, native job ID, schedule, last run, status, model, script hash. This gives a single‑pane view of all cron jobs without having to drop to the CLI.

---

### 2. Command & Workflow Refinements

**2.1 Dry‑run capability for commands**  
Add a `mode: dry-run` to command frontmatter. A worker that claims it would:
- Validate, plan, and produce a detailed preview of actions (files to create/modify, pages to update)
- Write that plan to `06 Outputs/Plans/`  
- Set the command to `awaiting_approval` with the plan hash, without touching the vault.  
This lets a human review the exact consequences before execution.

**2.2 Snooze / delayed retry**  
For transient failures, instead of a fixed exponential backoff, allow a command to be set to `retry_scheduled` with a `not_before` timestamp that the router respects. The watch‑dog can also detect commands stuck in retry loops and escalate.

**2.3 Idempotency‑key chaining for sequential steps**  
The approved action worker already writes per‑step receipts. Add a `parent_idempotency_key` field to allow chaining of dependent external steps (e.g., “publish report” only after “validate data”). The worker would skip later steps if the parent receipt is not completed, avoiding partial external effects.

**2.4 Automated command generation helpers**  
Provide Obsidian‑side templating (Templater, QuickAdd macros) that build valid `hermes.command/v1` frontmatter with the correct schema, date, and dedupe key. This reduces manual YAML errors and encourages capture.

**2.5 Archive‑after‑cooldown for completed commands**  
The spec says not to move commands while active. After they reach `completed`, `cancelled`, or `failed`, a cleanup routine (or the bridge) can move them to `01 Commands/Archive/YYYY-MM/` after a cooldown (e.g., 24 hours). This keeps the Active folder scannable by gate scripts without affecting links.

---

### 3. Security & Trust Boundary Additions

**3.1 Signed approval tokens**  
For high‑risk tiers (3–4), the approval could be a detached signature (e.g., GPG) over the canonical plan hash, stored in the approval note. The worker verifies the signature against a trusted key before executing. This allows approvals across machines without relying solely on file permissions.

**3.2 Prompt‑injection detection in raw content**  
Before ingestion, the ingest worker could run a lightweight deterministic scan (regex for “ignore previous instructions”, suspicious shell commands) and record a `security_flag` in the raw source frontmatter. This does not block ingestion but makes injection attempts auditable.

**3.3 Network confinement labels**  
Instead of `network: read` in permissions, introduce a label system (e.g., `network: ["api.github.com", "newsapi.org"]`) so that even read‑only network access is whitelisted per command. The gate script can enforce this before waking the agent.

---

### 4. Observability & User Experience

**4.1 Dedicated Obsidian plugin for the bridge**  
The external bridge could be packaged as an Obsidian plugin. It would:
- Display live gateway/cron status in the ribbon and a side‑pane  
- Provide UI buttons to approve, cancel, or snooze commands  
- Trigger routine reconciliation on save  
- Show a Dataview‑based dashboard on `Home.md` with one‑click filters  
This eliminates the need for a separate terminal process and brings all control into Obsidian itself.

**4.2 Approval notifications via external channels**  
Use Hermes’s built‑in delivery (or the original `japer-technology/obsidian-hermes` plugin) to push alerts when:  
- A command enters `awaiting_approval`  
- The gateway goes offline  
- A dead‑letter count increases  
This makes the system proactive rather than requiring the user to check the dashboard.

**4.3 Detailed run logs in the vault**  
Beyond receipts, each cron session could optionally append a structured log entry to `99 System/Logs/<routine_name>.md`, including:
- Timestamps of each step  
- Files touched  
- Tool usage  
- Token estimates (if available)  
This aids debugging and cost monitoring without leaving the vault.

**4.4 Scheduled “noop” watchdog for gateway heartbeats**  
The queue watchdog can’t detect gateway death. Add a separate external heartbeat monitor (a tiny systemd timer or launchd job) that pings the gateway API every minute and updates `Agent Status.md`. The bridge can then react to the dead state.

---

### 5. Expansion & Advanced Patterns

**5.1 Context‑pipelining for tight loops**  
The spec rightly limits `context_from`. However, for a tightly coupled “ingest → wiki ripple” chain where the ingest worker produces a change manifest and the ripple worker should immediately act on it, `context_from` would avoid re‑reading the entire vault. Use it with a lifecycle: the chain job deletes its own `context_from` reference after completion, falling back to vault‑read if missing.

**5.2 Armory‑driven routine updates**  
When the armory loop identifies an automation candidate (e.g., “every time we see a PDF, extract text automatically”), it can create a draft routine note in `10 Routines/Active/`. The bridge would see it as `desired_state: draft` and ignore it until a human sets it to `active` (or an approval workflow confirms). This closes the loop from observation to new capability without requiring CLI intervention.

**5.3 Cross‑vault federation**  
If a user runs multiple vaults (work, personal, research), the bridge could be extended with a `remote_vault` target. A command in vault A could request knowledge from vault B via a controlled API, with cross‑vault approvals. This keeps each vault’s integrity while enabling shared intelligence.

**5.4 Built‑in backup verification hook into Obsidian**  
The backup verifier script could optionally run an Obsidian plugin command (via URI scheme) that triggers a vault integrity check (e.g., `obsidian://check-and-report`) and capture the results in the snapshot.

**5.5 Handling of Obsidian Sync conflicts**  
Add a detection step: if the watchdog finds `.sync-conflict-*` files, it escalates to `blocked` any command that might touch the conflicting paths, and creates a human‑readable alert.

---

These suggestions respect the core architecture while adding resilience, usability, and future‑proofing. The spec is already at the “buildable” stage; the above would help it survive real‑world chaos and operator fatigue. If you’d like me to dive deeper into any single piece — say, the bridge daemon design or the Obsidian plugin API surface — just ask.
