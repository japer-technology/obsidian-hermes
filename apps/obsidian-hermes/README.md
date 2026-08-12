# Agent Control Room plugin

This is the Obsidian surface for the Markdown-first control room. It is
runtime-neutral: Hermes, OpenClaw, and future adapters appear as discovered
descriptors rather than hard-coded execution dependencies.

The plugin has three clearly separated data modes:

- **Live overlay** - a bounded, read-only snapshot from the literal loopback
  bridge (`/api/v1/snapshot`).
- **Vault view** - durable v2 task and routine notes read directly through
  Obsidian's vault and metadata APIs when the bridge is unavailable.
- **Reference preview** - opt-in illustrative Hermes/OpenClaw data, always
  labelled as preview and never treated as connected state.

Capture and model/depth choices write ordinary Markdown proposals under the
configured folder. They never call a runtime or mutate SQLite. The optional
bearer token is stored only in Obsidian's local plugin settings; it must never
be copied into Markdown or Git.

## Development

```console
npm install
npm run check
npm run build
```

The release artifacts are `manifest.json`, `main.js`, and `styles.css`. Install
those files into a test vault's `.obsidian/plugins/agent-control-room/` folder;
do not develop against a production vault.
