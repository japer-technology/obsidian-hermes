import { requestUrl } from "obsidian";
import {
  SNAPSHOT_API_VERSION,
  SNAPSHOT_SCHEMA,
  type ControlRoomSnapshot,
} from "./types";

export class SnapshotContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SnapshotContractError";
  }
}

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new SnapshotContractError(`${path} must be an object`);
  }
  return value as Record<string, unknown>;
}

function string(value: unknown, path: string): string {
  if (typeof value !== "string") throw new SnapshotContractError(`${path} must be a string`);
  return value;
}

function array(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new SnapshotContractError(`${path} must be an array`);
  return value;
}

function requiredString(value: unknown, path: string): void {
  string(value, path);
}

function nullableString(value: unknown, path: string): void {
  if (value !== null) requiredString(value, path);
}

function finiteNumber(value: unknown, path: string): void {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new SnapshotContractError(`${path} must be a finite number`);
  }
}

function boolean(value: unknown, path: string): void {
  if (typeof value !== "boolean") throw new SnapshotContractError(`${path} must be a boolean`);
}

function sourceOfTruth(value: unknown, path: string): void {
  const source = record(value, path);
  if (source.kind !== "markdown" && source.kind !== "sqlite-overlay") {
    throw new SnapshotContractError(`${path}.kind is invalid`);
  }
  nullableString(source.canonical_note_path, `${path}.canonical_note_path`);
  boolean(source.durable, `${path}.durable`);
  nullableString(source.specification_hash, `${path}.specification_hash`);
}

function pricing(value: unknown, path: string): void {
  const price = record(value, path);
  requiredString(price.currency, `${path}.currency`);
  if (price.unit !== "per_1m_tokens") throw new SnapshotContractError(`${path}.unit is invalid`);
  for (const key of ["input", "cached_input", "output"]) {
    if (price[key] !== null) finiteNumber(price[key], `${path}.${key}`);
  }
  if (price.status !== "current" && price.status !== "stale" && price.status !== "unavailable") {
    throw new SnapshotContractError(`${path}.status is invalid`);
  }
  nullableString(price.as_of, `${path}.as_of`);
  nullableString(price.source, `${path}.source`);
}

function checkRows(root: Record<string, unknown>, key: string, required: string[]): void {
  array(root[key], key).forEach((item, index) => {
    const row = record(item, `${key}[${index}]`);
    for (const field of required) {
      if (!(field in row)) throw new SnapshotContractError(`${key}[${index}].${field} is required`);
    }
  });
}

/** Defensive boundary for the explicit, read-only control-room v1 contract. */
export function decodeSnapshot(value: unknown): ControlRoomSnapshot {
  const root = record(value, "snapshot");
  if (root.schema !== SNAPSHOT_SCHEMA) {
    throw new SnapshotContractError(`Unsupported snapshot schema: ${String(root.schema)}`);
  }
  if (root.api_version !== SNAPSHOT_API_VERSION) {
    throw new SnapshotContractError(`Unsupported API version: ${String(root.api_version)}`);
  }
  if (root.status !== "validation_only" && root.status !== "ready" && root.status !== "degraded") {
    throw new SnapshotContractError("status is invalid");
  }
  string(root.generated_at, "generated_at");
  const stateModel = record(root.state_model, "state_model");
  if (stateModel.canonical !== "markdown" || stateModel.coordination_overlay !== "sqlite" || stateModel.history !== "git") {
    throw new SnapshotContractError("The snapshot state model is incompatible with Markdown-first operation");
  }
  if (stateModel.dispatch_enabled !== false) {
    throw new SnapshotContractError("v1 is read-only; dispatch_enabled must be false");
  }
  const freshness = record(root.freshness, "freshness");
  string(freshness.canonical_markdown_scanned_at, "freshness.canonical_markdown_scanned_at");
  nullableString(freshness.store_overlay_observed_at, "freshness.store_overlay_observed_at");
  nullableString(freshness.git_observed_at, "freshness.git_observed_at");
  if (!["current", "partial", "stale", "not_required"].includes(String(freshness.projection_status))) {
    throw new SnapshotContractError("freshness.projection_status is invalid");
  }
  checkRows(root, "runtimes", ["runtime_id", "runtime_type", "display_name", "health", "capabilities", "models"]);
  checkRows(root, "models", ["runtime_id", "model_id", "provider", "name", "display_name", "depths", "pricing"]);
  checkRows(root, "tasks", ["task_id", "runtime_id", "title", "desired_state", "canonical_note_path", "source_of_truth"]);
  checkRows(root, "routines", ["routine_id", "runtime_id", "name", "schedule", "canonical_note_path", "source_of_truth"]);
  checkRows(root, "queue", ["command_id", "task_id", "runtime_id", "state", "source_of_truth"]);
  checkRows(root, "runs", ["run_id", "runtime_id", "state", "usage", "cost", "source_of_truth"]);
  checkRows(root, "approvals", ["approval_id", "runtime_id", "decision", "source_of_truth"]);
  checkRows(root, "activity", ["event_id", "runtime_id", "occurred_at", "type", "actor", "source_of_truth"]);
  record(root.repository, "repository");
  array(root.warnings, "warnings");
  if (typeof root.truncated !== "boolean") throw new SnapshotContractError("truncated must be a boolean");

  const runtimes = array(root.runtimes, "runtimes");
  runtimes.forEach((value, index) => {
    const runtime = record(value, `runtimes[${index}]`);
    requiredString(runtime.runtime_id, `runtimes[${index}].runtime_id`);
    requiredString(runtime.runtime_type, `runtimes[${index}].runtime_type`);
    requiredString(runtime.display_name, `runtimes[${index}].display_name`);
    requiredString(runtime.profile, `runtimes[${index}].profile`);
    array(runtime.capabilities, `runtimes[${index}].capabilities`).forEach((capability, capabilityIndex) => requiredString(capability, `runtimes[${index}].capabilities[${capabilityIndex}]`));
    array(runtime.models, `runtimes[${index}].models`).forEach((model, modelIndex) => checkModel(model, `runtimes[${index}].models[${modelIndex}]`));
    boolean(runtime.validation_only, `runtimes[${index}].validation_only`);
  });
  array(root.models, "models").forEach((value, index) => checkModel(value, `models[${index}]`, true));
  array(root.tasks, "tasks").forEach((value, index) => {
    const task = record(value, `tasks[${index}]`);
    requiredString(task.task_id, `tasks[${index}].task_id`);
    requiredString(task.runtime_id, `tasks[${index}].runtime_id`);
    requiredString(task.title, `tasks[${index}].title`);
    requiredString(task.canonical_note_path, `tasks[${index}].canonical_note_path`);
    sourceOfTruth(task.source_of_truth, `tasks[${index}].source_of_truth`);
  });
  array(root.routines, "routines").forEach((value, index) => {
    const routine = record(value, `routines[${index}]`);
    requiredString(routine.routine_id, `routines[${index}].routine_id`);
    requiredString(routine.runtime_id, `routines[${index}].runtime_id`);
    const schedule = record(routine.schedule, `routines[${index}].schedule`);
    requiredString(schedule.expression, `routines[${index}].schedule.expression`);
    requiredString(schedule.timezone, `routines[${index}].schedule.timezone`);
    requiredString(routine.canonical_note_path, `routines[${index}].canonical_note_path`);
    sourceOfTruth(routine.source_of_truth, `routines[${index}].source_of_truth`);
  });
  array(root.queue, "queue").forEach((value, index) => {
    const item = record(value, `queue[${index}]`);
    requiredString(item.command_id, `queue[${index}].command_id`);
    requiredString(item.task_id, `queue[${index}].task_id`);
    requiredString(item.runtime_id, `queue[${index}].runtime_id`);
    sourceOfTruth(item.source_of_truth, `queue[${index}].source_of_truth`);
  });
  array(root.runs, "runs").forEach((value, index) => {
    const run = record(value, `runs[${index}]`);
    requiredString(run.run_id, `runs[${index}].run_id`);
    requiredString(run.runtime_id, `runs[${index}].runtime_id`);
    const usage = record(run.usage, `runs[${index}].usage`);
    for (const key of ["input_tokens", "output_tokens", "network_requests"]) finiteNumber(usage[key], `runs[${index}].usage.${key}`);
    const cost = record(run.cost, `runs[${index}].cost`);
    for (const key of ["estimated_usd", "actual_usd"]) if (cost[key] !== null) finiteNumber(cost[key], `runs[${index}].cost.${key}`);
    sourceOfTruth(run.source_of_truth, `runs[${index}].source_of_truth`);
  });
  array(root.approvals, "approvals").forEach((value, index) => {
    const approval = record(value, `approvals[${index}]`);
    requiredString(approval.approval_id, `approvals[${index}].approval_id`);
    requiredString(approval.runtime_id, `approvals[${index}].runtime_id`);
    record(approval.subject, `approvals[${index}].subject`);
    sourceOfTruth(approval.source_of_truth, `approvals[${index}].source_of_truth`);
  });
  array(root.activity, "activity").forEach((value, index) => {
    const event = record(value, `activity[${index}]`);
    requiredString(event.event_id, `activity[${index}].event_id`);
    requiredString(event.runtime_id, `activity[${index}].runtime_id`);
    requiredString(event.occurred_at, `activity[${index}].occurred_at`);
    sourceOfTruth(event.source_of_truth, `activity[${index}].source_of_truth`);
  });
  return root as unknown as ControlRoomSnapshot;
}

function checkModel(value: unknown, path: string, requireRuntime = false): void {
  const model = record(value, path);
  if (requireRuntime) requiredString(model.runtime_id, `${path}.runtime_id`);
  for (const key of ["model_id", "provider", "name", "display_name"]) requiredString(model[key], `${path}.${key}`);
  array(model.depths, `${path}.depths`).forEach((depth, index) => requiredString(depth, `${path}.depths[${index}]`));
  if (model.context_window_tokens !== null) finiteNumber(model.context_window_tokens, `${path}.context_window_tokens`);
  pricing(model.pricing, `${path}.pricing`);
}

/** Only literal HTTP loopback is accepted: no DNS, TLS exception, or remote host. */
export function normalizeLoopbackBaseUrl(input: string): string {
  const trimmed = input.trim().replace(/\/+$/, "");
  if (!/^http:\/\/(?:127(?:\.\d{1,3}){3}|\[::1\])(?::\d{1,5})?$/.test(trimmed)) {
    throw new Error("Bridge URL must use literal HTTP loopback (127/8 or [::1])");
  }
  const parsed = new URL(trimmed);
  if (parsed.username || parsed.password || parsed.search || parsed.hash) throw new Error("Bridge URL cannot contain credentials, query, or fragment");
  if (parsed.pathname !== "/") throw new Error("Bridge URL cannot contain a path prefix");
  if (parsed.hostname !== "[::1]") {
    const octets = parsed.hostname.split(".").map(Number);
    if (octets.length !== 4 || octets[0] !== 127 || octets.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
      throw new Error("Bridge URL must use an address in 127.0.0.0/8");
    }
  }
  return `${trimmed}/`;
}

export class ControlRoomApi {
  constructor(private readonly baseUrl: string, private readonly bearerToken: string) {}

  async snapshot(): Promise<ControlRoomSnapshot> {
    const base = normalizeLoopbackBaseUrl(this.baseUrl);
    const response = await requestUrl({
      url: new URL("api/v1/snapshot", base).toString(),
      method: "GET",
      headers: this.bearerToken ? { Authorization: `Bearer ${this.bearerToken}` } : {},
      throw: false,
    });
    if (response.status < 200 || response.status >= 300) throw new Error(`Bridge returned HTTP ${response.status}`);
    if (typeof response.text === "string" && response.text.length > 8_500_000) {
      throw new Error("Bridge response exceeds the client safety limit");
    }
    return decodeSnapshot(response.json);
  }
}
