import type { App, CachedMetadata, TFile } from "obsidian";
import type {
  ControlRoomSnapshot,
  ModelSelection,
  RoutineSummary,
  SourceOfTruth,
  TaskSummary,
} from "./types";

const SNAPSHOT_SCHEMA = "obsidian-hermes.control-room-snapshot/v1" as const;

function text(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function nullableText(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function number(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function object(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function source(path: string, hash: string | null = null): SourceOfTruth {
  return { kind: "markdown", canonical_note_path: path, durable: true, specification_hash: hash };
}

function modelSelection(frontmatter: Record<string, unknown>): ModelSelection {
  const model = object(frontmatter.model_selection);
  return {
    provider: nullableText(model.provider),
    model: nullableText(model.model),
    depth: nullableText(model.depth),
    source: text(model.source, "markdown"),
  };
}

function nested(frontmatter: Record<string, unknown>, key: string): Record<string, unknown> {
  return object(frontmatter[key]);
}

function isCanonicalResourcePath(path: string): boolean {
  const parts = path.split("/");
  return (parts[0] === "ReadOnly" || parts[0] === "ReadWrite")
    && !parts.some((part) => part.toLowerCase() === "private");
}

function task(file: TFile, frontmatter: Record<string, unknown>): TaskSummary {
  const observed = nested(frontmatter, "observed");
  const budget = nested(frontmatter, "budgets");
  const runtimeId = text(frontmatter.runtime_id, "unresolved");
  const hash = typeof frontmatter.specification_hash === "string" ? frontmatter.specification_hash : null;
  return {
    task_id: text(frontmatter.id, file.path),
    runtime_id: runtimeId,
    title: text(frontmatter.title, file.basename),
    desired_state: text(frontmatter.desired_state, "draft"),
    observed_state: nullableText(observed.state),
    priority: number(frontmatter.priority),
    operation: text(frontmatter.operation, "unknown"),
    agent_profile: text(frontmatter.agent_profile, "unbound"),
    model_selection: modelSelection(frontmatter),
    budget,
    queue: null,
    canonical_note_path: file.path,
    source_of_truth: source(file.path, hash),
    field_sources: {
      title: "markdown",
      desired_state: "markdown",
      observed_state: "markdown",
      priority: "markdown",
      operation: "markdown",
      model_selection: "markdown",
      budget: "markdown",
    },
  };
}

function routine(file: TFile, frontmatter: Record<string, unknown>): RoutineSummary {
  const observed = nested(frontmatter, "observed");
  const schedule = nested(frontmatter, "schedule");
  const execution = nested(frontmatter, "execution");
  const runtimeId = text(frontmatter.runtime_id, "unresolved");
  return {
    routine_id: text(frontmatter.id, file.path),
    runtime_id: runtimeId,
    name: text(frontmatter.name, file.basename),
    desired_state: text(frontmatter.desired_state, "draft"),
    observed_state: text(observed.state, null as unknown as string),
    schedule: {
      expression: text(schedule.expression, "unscheduled"),
      timezone: text(schedule.timezone, "Etc/UTC"),
      next_run_at: null,
    },
    model_selection: {
      provider: nullableText(execution.provider),
      model: nullableText(execution.model),
      depth: nullableText(execution.depth),
      source: "markdown",
    },
    last_run: null,
    canonical_note_path: file.path,
    source_of_truth: source(file.path),
    field_sources: { name: "markdown", desired_state: "markdown", schedule: "markdown", model_selection: "markdown" },
  };
}

function emptySnapshot(now: string): ControlRoomSnapshot {
  return {
    schema: SNAPSHOT_SCHEMA,
    api_version: 1,
    generated_at: now,
    status: "validation_only",
    state_model: { canonical: "markdown", coordination_overlay: "sqlite", history: "git", dispatch_enabled: false },
    freshness: {
      canonical_markdown_scanned_at: now,
      store_overlay_observed_at: null,
      git_observed_at: null,
      projection_status: "not_required",
    },
    runtimes: [],
    models: [],
    tasks: [],
    routines: [],
    queue: [],
    runs: [],
    approvals: [],
    activity: [],
    repository: {
      available: false,
      role: "historical_shared_memory",
      head: null,
      ref: null,
      dirty: null,
      ahead: null,
      behind: null,
      upstream_status: "unavailable",
      last_commit: null,
      observed_at: null,
    },
    warnings: [],
    truncated: false,
  };
}

/** Read durable v2 resources directly from Obsidian's metadata cache. */
export function readVaultSnapshot(app: App): ControlRoomSnapshot {
  const now = new Date().toISOString();
  const snapshot = emptySnapshot(now);
  const tasks: TaskSummary[] = [];
  const routines: RoutineSummary[] = [];

  for (const file of app.vault.getMarkdownFiles()) {
    if (!isCanonicalResourcePath(file.path)) continue;
    const cache: CachedMetadata | null = app.metadataCache.getFileCache(file);
    const frontmatter = cache?.frontmatter;
    if (!frontmatter || typeof frontmatter.schema !== "string") continue;
    if (frontmatter.schema === "hermes.task/v2") tasks.push(task(file, frontmatter));
    if (frontmatter.schema === "hermes.routine/v2") routines.push(routine(file, frontmatter));
  }

  tasks.sort((left, right) => right.priority - left.priority || left.task_id.localeCompare(right.task_id));
  routines.sort((left, right) => left.name.localeCompare(right.name));
  snapshot.tasks = tasks;
  snapshot.routines = routines;
  snapshot.freshness.projection_status = "current";
  return snapshot;
}

export function vaultResourceCount(app: App): number {
  return app.vault.getMarkdownFiles().length;
}
