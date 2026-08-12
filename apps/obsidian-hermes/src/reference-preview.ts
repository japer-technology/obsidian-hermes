import type { ControlRoomSnapshot, SourceOfTruth } from "./types";

const note = (path: string): SourceOfTruth => ({
  kind: "markdown",
  canonical_note_path: path,
  durable: true,
  specification_hash: null,
});

const pricing = {
  currency: "USD",
  unit: "per_1m_tokens" as const,
  input: 3,
  cached_input: 0.3,
  output: 15,
  status: "stale" as const,
  as_of: "2026-08-12T00:00:00Z",
  source: "ReadOnly/Models/Pricing/illustrative-example.md",
};

export function referencePreviewSnapshot(): ControlRoomSnapshot {
  const hermesModel = {
    model_id: "anthropic:claude-sonnet-example",
    provider: "anthropic",
    name: "claude-sonnet-example",
    display_name: "Claude Sonnet Example",
    depths: ["fast", "balanced", "deep"],
    context_window_tokens: 200000,
    pricing,
  };
  const localModel = {
    model_id: "local:example-model",
    provider: "local",
    name: "example-model",
    display_name: "Local Example Model",
    depths: ["fast", "deep"],
    context_window_tokens: 32768,
    pricing: { ...pricing, input: null, cached_input: null, output: null, status: "unavailable" as const, as_of: null, source: null },
  };
  return {
    schema: "obsidian-hermes.control-room-snapshot/v1",
    api_version: 1,
    generated_at: "2026-08-12T01:30:00Z",
    status: "validation_only",
    state_model: { canonical: "markdown", coordination_overlay: "sqlite", history: "git", dispatch_enabled: false },
    freshness: {
      canonical_markdown_scanned_at: "2026-08-12T01:30:00Z",
      store_overlay_observed_at: "2026-08-12T01:29:58Z",
      git_observed_at: "2026-08-12T01:29:55Z",
      projection_status: "current",
    },
    runtimes: [
      { runtime_id: "hermes:default", runtime_type: "hermes", display_name: "Hermes Agent", profile: "default", capabilities: ["supports_tasks", "supports_routines"], health: "validation_only", validation_only: true, models: [hermesModel], details: { dispatch_enabled: false } },
      { runtime_id: "openclaw:default", runtime_type: "openclaw", display_name: "OpenClaw", profile: "default", capabilities: ["supports_tasks", "supports_routines"], health: "unconfigured", validation_only: true, models: [localModel], details: { dispatch_enabled: false } },
    ],
    models: [{ ...hermesModel, runtime_id: "hermes:default" }, { ...localModel, runtime_id: "openclaw:default" }],
    tasks: [{
      task_id: "task_01ARZ3NDEKTSV4RRFFQ69G5FAV", runtime_id: "hermes:default", title: "Prepare the living morning brief",
      desired_state: "ready", observed_state: "queued", priority: 80, operation: "brief.generate", agent_profile: "chief-of-staff",
      model_selection: { provider: "anthropic", model: "claude-sonnet-example", depth: "deep", source: "routine" },
      budget: { max_runtime_minutes: 10, max_input_tokens: 50000, max_output_tokens: 10000 },
      queue: { command_id: "cmd_preview", state: "queued", attempt: 0, max_attempts: 3, not_before: "2026-08-12T01:30:00Z", updated_at: "2026-08-12T01:29:58Z", source: "sqlite-overlay" },
      canonical_note_path: "ReadWrite/02 Tasks/Morning brief.md", source_of_truth: note("ReadWrite/02 Tasks/Morning brief.md"),
      field_sources: { title: "markdown", desired_state: "markdown", queue: "sqlite-overlay" },
    }],
    routines: [{
      routine_id: "morning-brief", runtime_id: "openclaw:default", name: "obsidian/brief/morning", desired_state: "active", observed_state: "scheduled",
      schedule: { expression: "daily at 06:30", timezone: "Australia/Sydney", next_run_at: "2026-08-13T20:30:00Z" },
      model_selection: { provider: "local", model: "example-model", depth: "balanced", source: "routine" }, last_run: null,
      canonical_note_path: "ReadWrite/03 Routines/Morning brief.md", source_of_truth: note("ReadWrite/03 Routines/Morning brief.md"), field_sources: { name: "markdown", schedule: "markdown" },
    }],
    queue: [{ command_id: "cmd_preview", task_id: "task_01ARZ3NDEKTSV4RRFFQ69G5FAV", runtime_id: "hermes:default", state: "queued", priority: 80, not_before: "2026-08-12T01:30:00Z", attempt: 0, max_attempts: 3, updated_at: "2026-08-12T01:29:58Z", canonical_note_path: "ReadWrite/02 Tasks/Morning brief.md", source_of_truth: { kind: "sqlite-overlay", canonical_note_path: "ReadWrite/02 Tasks/Morning brief.md", durable: false, specification_hash: null }, field_sources: { state: "sqlite-overlay", priority: "markdown-validated-overlay" } }],
    runs: [{ run_id: "run_preview", runtime_id: "hermes:default", task_id: "task_01ARZ3NDEKTSV4RRFFQ69G5FAV", command_id: "cmd_preview", trace_id: "trace_preview", state: "running", model: { provider: "anthropic", name: "claude-sonnet-example", source: "routine" }, usage: { input_tokens: 12000, output_tokens: 1800, network_requests: 0 }, cost: { estimated_usd: 0.063, actual_usd: 0.042, status: "estimated" }, created_at: "2026-08-12T01:25:00Z", started_at: "2026-08-12T01:26:00Z", finished_at: null, canonical_note_path: "ReadWrite/04 Runs/2026-08-12 Morning brief.md", source_of_truth: note("ReadWrite/04 Runs/2026-08-12 Morning brief.md"), field_sources: { state: "sqlite-overlay", model: "markdown", usage: "sqlite-overlay" } }],
    approvals: [{ approval_id: "approval_preview", runtime_id: "hermes:default", trace_id: "trace_preview", action_class: "external_write", risk_tier: 3, decision: "pending", subject: { type: "task-plan" }, requested_at: "2026-08-12T01:28:00Z", expires_at: "2026-08-13T01:28:00Z", canonical_note_path: "ReadWrite/05 Approvals/Morning brief external write.md", source_of_truth: note("ReadWrite/05 Approvals/Morning brief external write.md"), field_sources: { decision: "sqlite-overlay", subject: "markdown" } }],
    activity: [{ event_id: "event_preview", runtime_id: "hermes:default", occurred_at: "2026-08-12T01:29:00Z", type: "command.running", outcome: "success", actor: "agent:chief-of-staff", trace_id: "trace_preview", task_id: "task_01ARZ3NDEKTSV4RRFFQ69G5FAV", run_id: "run_preview", commit: "9ac4e8f", summary: "Drafted the briefing and requested approval for publishing.", canonical_note_path: "ReadWrite/07 Activity/2026-08-12.md", source_of_truth: note("ReadWrite/07 Activity/2026-08-12.md"), field_sources: { actor: "markdown", commit: "markdown" } }],
    repository: { available: true, role: "historical_shared_memory", head: "9ac4e8f4bb6d8ff31b48bf986447bed3377afb42", ref: "refs/heads/main", dirty: false, ahead: null, behind: null, upstream_status: "unavailable", last_commit: { sha: "9ac4e8f4bb6d8ff31b48bf986447bed3377afb42", summary: "Record morning brief", author: "Hermes Agent", committed_at: "2026-08-12T01:29:15Z" }, observed_at: "2026-08-12T01:29:55Z" },
    warnings: [],
    truncated: false,
  };
}
