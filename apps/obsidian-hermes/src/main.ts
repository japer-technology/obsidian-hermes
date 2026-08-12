import {
  App,
  ItemView,
  Modal,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  TFile,
  WorkspaceLeaf,
} from "obsidian";
import { ControlRoomApi, normalizeLoopbackBaseUrl } from "./api";
import { referencePreviewSnapshot } from "./reference-preview";
import type { ControlRoomSnapshot, HermesPluginSettings, RuntimeModel } from "./types";
import { readVaultSnapshot, vaultResourceCount } from "./vault";

export const VIEW_TYPE_CONTROL_ROOM = "agent-control-room";

const DEFAULT_SETTINGS: HermesPluginSettings = {
  apiBaseUrl: "http://127.0.0.1:27124",
  bearerToken: "",
  refreshIntervalSeconds: 30,
  previewWhenUnavailable: true,
  captureFolder: "ReadWrite/70 Tasks/Proposals",
  defaultRuntimeId: "unresolved",
  defaultModelId: "",
  defaultDepth: "balanced",
};

function display(value: unknown, fallback = "—"): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function safeFolder(value: string): string {
  const trimmed = value.trim().replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  if (!trimmed || trimmed.split("/").some((part) => !part || part === "." || part === ".." || part.toLowerCase() === ".git" || /[\u0000-\u001f:*?"<>|]/.test(part))) {
    throw new Error("Capture folder must be a relative vault path without dot or Git segments");
  }
  return trimmed;
}

function el(parent: HTMLElement, tag: string, text?: string, cls?: string): HTMLElement {
  const child = parent.createEl(tag as keyof HTMLElementTagNameMap, cls ? { cls } : undefined);
  if (text !== undefined) child.textContent = text;
  return child;
}

export default class AgentControlRoomPlugin extends Plugin {
  declare settings: HermesPluginSettings;
  private refreshTimer?: number;

  async onload(): Promise<void> {
    await this.loadSettings();
    this.registerView(VIEW_TYPE_CONTROL_ROOM, (leaf) => new ControlRoomView(leaf, this));
    this.addRibbonIcon("home", "Open agent control room", () => void this.activateView());
    this.addCommand({ id: "open-control-room", name: "Open agent control room", callback: () => void this.activateView() });
    this.addCommand({ id: "capture-agent-proposal", name: "Capture agent task or proposal", callback: () => new CaptureModal(this.app, this).open() });
    this.addSettingTab(new AgentControlRoomSettingsTab(this.app, this));
    this.app.workspace.onLayoutReady(() => this.startRefreshTimer());
    this.register(() => {
      if (this.refreshTimer !== undefined) window.clearInterval(this.refreshTimer);
    });
  }

  onunload(): void {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_CONTROL_ROOM);
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
    this.startRefreshTimer();
    this.refreshViews();
  }

  private startRefreshTimer(): void {
    if (this.refreshTimer !== undefined) window.clearInterval(this.refreshTimer);
    this.refreshTimer = window.setInterval(
      () => this.refreshViews(),
      this.settings.refreshIntervalSeconds * 1000,
    );
  }

  async activateView(): Promise<void> {
    const existing = this.app.workspace.getLeavesOfType(VIEW_TYPE_CONTROL_ROOM);
    const first = existing[0];
    if (first) {
      await this.app.workspace.revealLeaf(first);
      return;
    }
    const leaf = this.app.workspace.getRightLeaf(false) ?? this.app.workspace.getLeaf(true);
    await leaf.setViewState({ type: VIEW_TYPE_CONTROL_ROOM, active: true });
    await this.app.workspace.revealLeaf(leaf);
  }

  refreshViews(): void {
    for (const leaf of this.app.workspace.getLeavesOfType(VIEW_TYPE_CONTROL_ROOM)) {
      const view = leaf.view;
      if (view instanceof ControlRoomView) void view.refresh();
    }
  }
}

class ControlRoomView extends ItemView {
  private readonly plugin: AgentControlRoomPlugin;
  private snapshot?: ControlRoomSnapshot;
  private mode: "live" | "vault" | "reference-preview" = "vault";
  private message: string | null = null;
  private refreshing = false;

  constructor(leaf: WorkspaceLeaf, plugin: AgentControlRoomPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string { return VIEW_TYPE_CONTROL_ROOM; }
  getDisplayText(): string { return "Agent Control Room"; }
  getIcon(): string { return "home"; }

  async onOpen(): Promise<void> { await this.refresh(); }
  async onClose(): Promise<void> { this.contentEl.empty(); }

  async refresh(): Promise<void> {
    if (this.refreshing) return;
    this.refreshing = true;
    let vault: ControlRoomSnapshot | undefined;
    try {
      vault = readVaultSnapshot(this.plugin.app);
      this.snapshot = vault;
      this.mode = "vault";
      this.message = vaultResourceCount(this.plugin.app) > 0
        ? "Live bridge unavailable; showing canonical vault Markdown."
        : "No bridge snapshot yet; the vault has no Markdown resources to summarize.";
      const base = normalizeLoopbackBaseUrl(this.plugin.settings.apiBaseUrl);
      this.snapshot = await new ControlRoomApi(base, this.plugin.settings.bearerToken).snapshot();
      this.mode = "live";
      this.message = null;
    } catch (error) {
      if (vault && vault.tasks.length === 0 && vault.routines.length === 0 && this.plugin.settings.previewWhenUnavailable) {
        this.snapshot = referencePreviewSnapshot();
        this.mode = "reference-preview";
        this.message = "Reference preview only — no connected bridge or executable runtime.";
      } else if (error instanceof Error && !error.message.includes("fetch")) {
        this.message = `${this.message ?? "Bridge unavailable"} ${error.message}`;
      }
    } finally {
      this.render();
      this.refreshing = false;
    }
  }

  private render(): void {
    const root = this.contentEl;
    root.empty();
    root.addClass("agent-control-room");
    if (!this.snapshot) return;
    const snapshot = this.snapshot;
    const header = el(root, "div", undefined, "acr-header");
    const title = el(header, "div", undefined, "acr-title");
    el(title, "div", "Agent Control Room", "acr-heading");
    el(title, "div", "Markdown memory · Git history · live runtime overlay", "acr-subtitle");
    const actions = el(header, "div", undefined, "acr-actions");
    const capture = actions.createEl("button", { text: "Capture", cls: "mod-cta" });
    capture.addEventListener("click", () => new CaptureModal(this.plugin.app, this.plugin).open());
    const refresh = actions.createEl("button", { text: "Refresh" });
    refresh.addEventListener("click", () => void this.refresh());

    const bannerClass = this.mode === "live" ? "acr-banner live" : "acr-banner preview";
    const banner = el(root, "div", undefined, bannerClass);
    el(banner, "strong", this.mode === "live" ? "LIVE OVERLAY" : this.mode === "vault" ? "VAULT VIEW" : "REFERENCE PREVIEW");
    el(banner, "span", `  ${this.message ?? "Read-only snapshot; changes become Markdown proposals."}`);

    const metrics = el(root, "div", undefined, "acr-metrics");
    metric(metrics, "Attention", String(snapshot.tasks.filter((task) => ["blocked", "approval_required", "failed"].includes(task.observed_state ?? "")).length));
    metric(metrics, "Queued", String(snapshot.queue.length));
    metric(metrics, "Running", String(snapshot.runs.filter((run) => ["running", "reconciling"].includes(run.state)).length));
    metric(metrics, "Routines", String(snapshot.routines.length));
    metric(metrics, "Markdown notes", String(vaultResourceCount(this.plugin.app)));
    metric(metrics, "Git", snapshot.repository.available ? display(snapshot.repository.ref, "connected") : "unavailable");

    const grid = el(root, "div", undefined, "acr-grid");
    this.renderRuntimes(grid, snapshot);
    this.renderQueue(grid, snapshot);
    this.renderModels(grid, snapshot);
    this.renderActivity(grid, snapshot);
  }

  private renderRuntimes(parent: HTMLElement, snapshot: ControlRoomSnapshot): void {
    const section = panel(parent, "Runtimes", "Choose a runtime in a proposal; v1 never dispatches silently.");
    if (!snapshot.runtimes.length) {
      el(section, "p", "No runtime adapter is discovered. ReadOnly/50 Agents/Runtime Registry.md is the desired-state record.", "acr-muted");
      return;
    }
    for (const runtime of snapshot.runtimes) {
      const row = el(section, "div", undefined, "acr-row");
      badge(row, runtime.display_name, runtime.health === "ready" ? "good" : "neutral");
      el(row, "span", `${runtime.runtime_id} · ${runtime.capabilities.join(", ")}`, "acr-row-detail");
    }
  }

  private renderQueue(parent: HTMLElement, snapshot: ControlRoomSnapshot): void {
    const section = panel(parent, "Queue", "Durable task intent comes from Markdown; order and claims are a live overlay.");
    if (!snapshot.tasks.length && !snapshot.queue.length) {
      el(section, "p", "No executable v2 task notes found yet. Capture a proposal to create one.", "acr-muted");
      return;
    }
    for (const task of snapshot.tasks.slice(0, 12)) {
      const row = el(section, "div", undefined, "acr-task");
      const link = row.createEl("a", { text: task.title, cls: "acr-link" });
      link.addEventListener("click", (event) => { event.preventDefault(); void this.openNote(task.canonical_note_path); });
      el(row, "div", `${task.operation} · ${display(task.runtime_id, "unresolved")} · ${display(task.observed_state, "pending")}`, "acr-row-detail");
      badge(row, task.queue?.state ?? task.desired_state, task.queue ? "live" : "neutral");
    }
  }

  private renderModels(parent: HTMLElement, snapshot: ControlRoomSnapshot): void {
    const section = panel(parent, "Models & cost", "Prices are estimates only when a dated Markdown catalogue supports them.");
    if (!snapshot.models.length) {
      el(section, "p", "No model catalogue is discovered. See [[Model and Pricing Catalog]].", "acr-muted");
      return;
    }
    for (const model of snapshot.models.slice(0, 8)) {
      const row = el(section, "div", undefined, "acr-row");
      el(row, "strong", model.display_name);
      el(row, "span", `${model.runtime_id} · ${model.depths.join(" / ")}`, "acr-row-detail");
      const price = model.pricing.input === null || model.pricing.output === null
        ? "price unavailable"
        : `${model.pricing.currency} ${model.pricing.input}/${model.pricing.output} per 1M`;
      badge(row, `${model.pricing.status}: ${price}`, model.pricing.status === "current" ? "good" : "neutral");
      const propose = row.createEl("button", { text: "Propose", cls: "acr-small-button" });
      propose.addEventListener("click", () => new CaptureModal(this.plugin.app, this.plugin, model).open());
    }
  }

  private renderActivity(parent: HTMLElement, snapshot: ControlRoomSnapshot): void {
    const section = panel(parent, "Activity & Git memory", "The last durable note and commit remain useful when the bridge is offline.");
    if (snapshot.repository.available && snapshot.repository.last_commit) {
      const commit = snapshot.repository.last_commit;
      el(section, "div", `${commit.sha.slice(0, 8)} · ${commit.summary}`, "acr-commit");
      el(section, "div", `${commit.author} · ${commit.committed_at}`, "acr-row-detail");
    } else {
      el(section, "p", "Git provenance is not available through this bridge instance.", "acr-muted");
    }
    for (const event of snapshot.activity.slice(0, 6)) {
      const row = el(section, "div", undefined, "acr-activity");
      badge(row, event.outcome, event.outcome === "success" ? "good" : "neutral");
      el(row, "span", `${event.type} · ${display(event.summary, event.actor)} · ${event.occurred_at}`, "acr-row-detail");
      if (event.canonical_note_path) linkNote(row, event.canonical_note_path, () => void this.openNote(event.canonical_note_path!));
    }
  }

  private async openNote(path: string): Promise<void> {
    if (!isSafeNotePath(path)) {
      new Notice("The snapshot contained an unsafe note path.");
      return;
    }
    const file = this.plugin.app.vault.getAbstractFileByPath(path);
    if (file instanceof TFile) await this.plugin.app.workspace.getLeaf(false).openFile(file);
    else new Notice(`Note not found: ${path}`);
  }
}

function isSafeNotePath(path: string): boolean {
  return path.length > 0
    && !/[\u0000-\u001f]/.test(path)
    && !path.startsWith("/")
    && !path.split("/").some((part) => !part || part === "." || part === ".." || part.toLowerCase() === ".git");
}

function metric(parent: HTMLElement, label: string, value: string): void {
  const card = el(parent, "div", undefined, "acr-metric");
  el(card, "div", value, "acr-metric-value");
  el(card, "div", label, "acr-metric-label");
}

function panel(parent: HTMLElement, title: string, subtitle: string): HTMLElement {
  const section = el(parent, "section", undefined, "acr-panel");
  el(section, "h2", title);
  el(section, "p", subtitle, "acr-panel-subtitle");
  return section;
}

function badge(parent: HTMLElement, text: string, kind: "good" | "neutral" | "live"): void {
  el(parent, "span", text, `acr-badge ${kind}`);
}

function linkNote(parent: HTMLElement, path: string, onClick: () => void): void {
  const link = parent.createEl("a", { text: path, cls: "acr-note-link" });
  link.addEventListener("click", (event) => { event.preventDefault(); onClick(); });
}

class CaptureModal extends Modal {
  private readonly plugin: AgentControlRoomPlugin;
  private readonly model?: RuntimeModel;
  private content = "";
  private runtimeId: string;
  private modelId: string;
  private depth: string;

  constructor(app: App, plugin: AgentControlRoomPlugin, model?: RuntimeModel) {
    super(app);
    this.plugin = plugin;
    this.model = model;
    this.runtimeId = plugin.settings.defaultRuntimeId;
    this.modelId = model?.model_id ?? plugin.settings.defaultModelId;
    this.depth = plugin.settings.defaultDepth;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("acr-capture-modal");
    el(contentEl, "h2", "Capture Markdown proposal");
    el(contentEl, "p", "This writes a durable, reviewable note. It does not start an agent or mutate a running task.", "acr-muted");
    const textArea = contentEl.createEl("textarea", { cls: "acr-capture-text" });
    textArea.placeholder = "What should the agent remember, plan, or do?";
    textArea.rows = 8;
    textArea.addEventListener("input", () => { this.content = textArea.value; });
    new Setting(contentEl).setName("Runtime").addText((text) => text.setValue(this.runtimeId).onChange((value) => { this.runtimeId = value.trim(); }));
    new Setting(contentEl).setName("Model profile").addText((text) => text.setValue(this.modelId).onChange((value) => { this.modelId = value.trim(); }));
    new Setting(contentEl).setName("Reasoning depth").addText((text) => text.setValue(this.depth).onChange((value) => { this.depth = value.trim(); }));
    const buttons = el(contentEl, "div", undefined, "acr-modal-buttons");
    const cancel = buttons.createEl("button", { text: "Cancel" });
    cancel.addEventListener("click", () => this.close());
    const save = buttons.createEl("button", { text: "Write proposal", cls: "mod-cta" });
    save.addEventListener("click", () => void this.writeProposal());
  }

  onClose(): void { this.contentEl.empty(); }

  private async writeProposal(): Promise<void> {
    const body = this.content.trim();
    if (!body) { new Notice("Add a capture before writing the proposal."); return; }
    if (body.length > 1_000_000) { new Notice("Capture is larger than the 1 MB proposal limit."); return; }
    let folder: string;
    try { folder = safeFolder(this.plugin.settings.captureFolder); } catch (error) { new Notice(error instanceof Error ? error.message : "Invalid capture folder"); return; }
    try {
      await ensureFolder(this.app, folder);
      const stamp = new Date().toISOString().replace(/[:.]/g, "-");
      let path = `${folder}/${stamp}-agent-proposal.md`;
      let suffix = 2;
      while (this.app.vault.getAbstractFileByPath(path)) {
        path = `${folder}/${stamp}-agent-proposal-${suffix}.md`;
        suffix += 1;
      }
      const markdown = `---\ntype: agent-proposal\nstatus: proposed\ncreated_at: ${new Date().toISOString()}\nruntime_id: ${yamlScalar(this.runtimeId || "unresolved")}\nmodel_id: ${yamlScalar(this.modelId)}\nreasoning_depth: ${yamlScalar(this.depth)}\n---\n\n# Capture\n\n${body}\n\n## Review\n\n- [ ] Validate against the v2 resource contract\n- [ ] Review permissions, budget, and approval requirements\n- [ ] Commit or revise this proposal with Git provenance\n`;
      const file = await this.app.vault.create(path, markdown);
      await this.app.workspace.getLeaf(false).openFile(file);
      new Notice("Markdown proposal written; no runtime action was taken.");
      this.close();
    } catch (error) { new Notice(`Could not write proposal: ${error instanceof Error ? error.message : "unknown error"}`); }
  }
}

function yamlScalar(value: string): string {
  return JSON.stringify(value.replace(/[\r\n]/g, " "));
}

async function ensureFolder(app: App, folder: string): Promise<void> {
  const segments = folder.split("/");
  let current = "";
  for (const segment of segments) {
    current = current ? `${current}/${segment}` : segment;
    if (!app.vault.getAbstractFileByPath(current)) await app.vault.createFolder(current);
  }
}

class AgentControlRoomSettingsTab extends PluginSettingTab {
  private readonly plugin: AgentControlRoomPlugin;

  constructor(app: App, plugin: AgentControlRoomPlugin) { super(app, plugin); this.plugin = plugin; }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Agent Control Room" });
    containerEl.createEl("p", { text: "The bridge is read-only in this scaffold. Secrets remain local plugin settings and are never written to Markdown or Git." });
    new Setting(containerEl).setName("Loopback bridge URL").setDesc("Literal http://127.x.x.x or http://[::1] only.").addText((text) => text.setValue(this.plugin.settings.apiBaseUrl).onChange(async (value) => { try { this.plugin.settings.apiBaseUrl = normalizeLoopbackBaseUrl(value).replace(/\/$/, ""); await this.plugin.saveSettings(); } catch (error) { new Notice(error instanceof Error ? error.message : "Invalid loopback URL"); } }));
    new Setting(containerEl).setName("Bearer token").setDesc("Optional local secret; never put this in a note.").addText((text) => { text.inputEl.type = "password"; text.setValue(this.plugin.settings.bearerToken).onChange(async (value) => { this.plugin.settings.bearerToken = value; await this.plugin.saveSettings(); }); });
    new Setting(containerEl).setName("Refresh interval (seconds)").addText((text) => text.setValue(String(this.plugin.settings.refreshIntervalSeconds)).onChange(async (value) => { const seconds = Number(value); if (Number.isInteger(seconds) && seconds >= 5 && seconds <= 600) { this.plugin.settings.refreshIntervalSeconds = seconds; await this.plugin.saveSettings(); } }));
    new Setting(containerEl).setName("Reference preview when disconnected").addToggle((toggle) => toggle.setValue(this.plugin.settings.previewWhenUnavailable).onChange(async (value) => { this.plugin.settings.previewWhenUnavailable = value; await this.plugin.saveSettings(); }));
    new Setting(containerEl).setName("Proposal folder").setDesc("Relative vault path; proposals are ordinary Markdown.").addText((text) => text.setValue(this.plugin.settings.captureFolder).onChange(async (value) => { try { this.plugin.settings.captureFolder = safeFolder(value); await this.plugin.saveSettings(); } catch { new Notice("Invalid proposal folder"); } }));
  }
}
