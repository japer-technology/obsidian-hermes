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
  return root as unknown as ControlRoomSnapshot;
}

/** Only literal HTTP loopback is accepted: no DNS, TLS exception, or remote host. */
export function normalizeLoopbackBaseUrl(input: string): string {
  const trimmed = input.trim().replace(/\/+$/, "");
  if (!/^http:\/\/(?:127(?:\.\d{1,3}){3}|\[::1\])(?::\d{1,5})?(?:\/[^?#]*)?$/.test(trimmed)) {
    throw new Error("Bridge URL must use literal HTTP loopback (127/8 or [::1])");
  }
  const parsed = new URL(trimmed);
  if (parsed.username || parsed.password || parsed.search || parsed.hash) throw new Error("Bridge URL cannot contain credentials, query, or fragment");
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
    return decodeSnapshot(response.json);
  }
}
