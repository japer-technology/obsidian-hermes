export const SNAPSHOT_SCHEMA = "obsidian-hermes.control-room-snapshot/v1" as const;
export const SNAPSHOT_API_VERSION = 1 as const;

export type SnapshotStatus = "validation_only" | "ready" | "degraded";
export type RuntimeHealth = "ready" | "degraded" | "offline" | "unconfigured" | "validation_only";
export type ProjectionStatus = "current" | "partial" | "stale" | "not_required";
export type FieldSource = "markdown" | "sqlite-overlay" | "resolved-overlay" | "markdown-validated-overlay";
export type SurfaceMode = "live" | "vault" | "reference-preview";

export interface SourceOfTruth {
  kind: "markdown" | "sqlite-overlay";
  canonical_note_path: string | null;
  durable: boolean;
  specification_hash: string | null;
}

export interface Pricing {
  currency: string;
  unit: "per_1m_tokens";
  input: number | null;
  cached_input: number | null;
  output: number | null;
  status: "current" | "stale" | "unavailable";
  as_of: string | null;
  source: string | null;
}

export interface RuntimeModel {
  runtime_id?: string;
  model_id: string;
  provider: string;
  name: string;
  display_name: string;
  depths: string[];
  context_window_tokens: number | null;
  pricing: Pricing;
}

export interface RuntimeSummary {
  runtime_id: string;
  runtime_type: string;
  display_name: string;
  profile: string;
  capabilities: string[];
  health: RuntimeHealth;
  validation_only: boolean;
  models: RuntimeModel[];
  details: Record<string, unknown>;
}

export interface ModelSelection {
  provider: string | null;
  model: string | null;
  depth: string | null;
  source: string;
}

export interface TaskSummary {
  task_id: string;
  runtime_id: string;
  title: string;
  desired_state: string;
  observed_state: string | null;
  priority: number;
  operation: string;
  agent_profile: string;
  model_selection: ModelSelection;
  budget: Record<string, unknown>;
  queue: {
    command_id: string;
    state: string;
    attempt: number;
    max_attempts: number;
    not_before: string;
    updated_at: string;
    source: "sqlite-overlay";
  } | null;
  canonical_note_path: string;
  source_of_truth: SourceOfTruth;
  field_sources: Record<string, FieldSource>;
}

export interface RoutineSummary {
  routine_id: string;
  runtime_id: string;
  name: string;
  desired_state: string;
  observed_state: string | null;
  schedule: { expression: string; timezone: string; next_run_at: string | null };
  model_selection: ModelSelection;
  last_run: Record<string, unknown> | null;
  canonical_note_path: string;
  source_of_truth: SourceOfTruth;
  field_sources: Record<string, FieldSource>;
}

export interface QueueItem {
  command_id: string;
  task_id: string;
  runtime_id: string;
  state: string;
  priority: number;
  not_before: string;
  attempt: number;
  max_attempts: number;
  updated_at: string;
  canonical_note_path: string | null;
  source_of_truth: SourceOfTruth;
  field_sources: Record<string, FieldSource>;
}

export interface RunSummary {
  run_id: string;
  runtime_id: string;
  task_id: string;
  command_id: string;
  trace_id: string;
  state: string;
  model: { provider: string; name: string; source: string; [key: string]: unknown };
  usage: { input_tokens: number; output_tokens: number; network_requests: number };
  cost: { estimated_usd: number | null; actual_usd: number | null; status: "estimated" | "final" | "unavailable" };
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  canonical_note_path: string | null;
  source_of_truth: SourceOfTruth;
  field_sources: Record<string, FieldSource>;
}

export interface ApprovalSummary {
  approval_id: string;
  runtime_id: string;
  trace_id: string;
  action_class: string;
  risk_tier: number;
  decision: string;
  subject: Record<string, unknown>;
  requested_at: string;
  expires_at: string;
  canonical_note_path: string | null;
  source_of_truth: SourceOfTruth;
  field_sources: Record<string, FieldSource>;
}

export interface ActivityEvent {
  event_id: string;
  runtime_id: string;
  occurred_at: string;
  type: string;
  outcome: string;
  actor: string;
  trace_id: string;
  task_id: string | null;
  run_id: string | null;
  commit: string | null;
  summary: string | null;
  canonical_note_path: string | null;
  source_of_truth: SourceOfTruth;
  field_sources: Record<string, FieldSource>;
}

export interface RepositoryMemory {
  available: boolean;
  role: "historical_shared_memory";
  head: string | null;
  ref: string | null;
  dirty: boolean | null;
  ahead: number | null;
  behind: number | null;
  upstream_status: "known" | "unavailable";
  last_commit: { sha: string; summary: string; author: string; committed_at: string } | null;
  observed_at: string | null;
}

export interface ControlRoomSnapshot {
  schema: typeof SNAPSHOT_SCHEMA;
  api_version: typeof SNAPSHOT_API_VERSION;
  generated_at: string;
  status: SnapshotStatus;
  state_model: {
    canonical: "markdown";
    coordination_overlay: "sqlite";
    history: "git";
    dispatch_enabled: false;
  };
  freshness: {
    canonical_markdown_scanned_at: string;
    store_overlay_observed_at: string | null;
    git_observed_at: string | null;
    projection_status: ProjectionStatus;
  };
  runtimes: RuntimeSummary[];
  models: Array<RuntimeModel & { runtime_id: string }>;
  tasks: TaskSummary[];
  routines: RoutineSummary[];
  queue: QueueItem[];
  runs: RunSummary[];
  approvals: ApprovalSummary[];
  activity: ActivityEvent[];
  repository: RepositoryMemory;
  warnings: Array<{ code: string; message: string; path: string | null }>;
  truncated: boolean;
}

export interface SnapshotPresentation {
  snapshot: ControlRoomSnapshot;
  mode: SurfaceMode;
  bridgeReachable: boolean;
  message: string | null;
}

export interface HermesPluginSettings {
  apiBaseUrl: string;
  bearerToken: string;
  refreshIntervalSeconds: number;
  previewWhenUnavailable: boolean;
  captureFolder: string;
  defaultRuntimeId: string;
  defaultModelId: string;
  defaultDepth: string;
}
