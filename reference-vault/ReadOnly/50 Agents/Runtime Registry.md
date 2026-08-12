# Runtime Registry

> [!IMPORTANT]
> This is human-owned configuration intent and demo data. Availability, health,
> models, and capabilities must come from authenticated adapter discovery.

| Runtime | Desired state | Binding policy | Discovered state | Notes |
| --- | --- | --- | --- | --- |
| Hermes | disabled | preferred for scheduled work | not discovered | Example adapter target |
| OpenClaw | disabled | eligible for portable tasks | not discovered | Example adapter target, not a dependency |

## Required adapter report

Every runtime adapter must expose a typed identity and version, health,
scheduling semantics, cancellation support, tool capabilities, available model
tuples, usage/cost telemetry, and native job/run identifiers.

Tasks remain portable while `runtime` is unbound. Binding must be explicit or
the result of a named, reviewable policy. Missing capability or discovery data
blocks dispatch rather than triggering a guess.

Secrets, executable paths, bearer tokens, and runtime-reported observations do
not belong in this note.
