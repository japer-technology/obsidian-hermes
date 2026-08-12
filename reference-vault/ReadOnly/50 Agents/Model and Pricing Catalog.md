# Model and Pricing Catalog

> [!WARNING]
> No model or price is approved in this reference vault. Prices must be
> discovered or imported with source, currency, timestamp, and billing unit.

## Profiles

| Profile | Intent | Reasoning depth | Task budget | Resolution |
| --- | --- | --- | --- | --- |
| Economy | Classification and routine maintenance | low | $0.10 illustrative cap | unresolved |
| Balanced | Everyday research and drafting | medium | $1.00 illustrative cap | unresolved |
| Deep | Deliberate planning or difficult analysis | high | $5.00 illustrative cap | unresolved |

Caps above demonstrate the UI and are not provider prices or deployment
approval. A resolved profile binds an approved runtime/provider/model tuple and
records the policy revision used.

## Price-data contract

For every billable dimension, retain provider, model, input/output/cache/tool
unit, currency, effective time, retrieval time, source, and confidence. The UI
must label costs as **estimate**, **measured**, or **unknown**. Stale catalogue
data cannot be presented as a current quote.

Changing a queued task's profile creates a durable task revision. Running work
must be paused, cancelled, or replanned; it is never silently repinned.

## Illustrative catalogue row

> [!CAUTION]
> Demonstration data only: stale, unverified, not approved, and not a quote.

| Runtime | Provider | Model | Input / 1M | Cached input / 1M | Output / 1M | Currency | Status |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| demo | example | example-model | 3.00 | 0.30 | 15.00 | USD | illustrative only |
