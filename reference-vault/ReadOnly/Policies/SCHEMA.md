# Vault schema policy

This placeholder points to the installed, versioned v2 executable schemas;
prose and examples are not validators or conformance fixtures.

Resource notes must use one leading safe-YAML frontmatter document, declare
their full `schema`, set `schema_version: 2`, carry stable identifiers and
revisions where required, and reject unknown fields or operations. The bridge
must validate resources and canonical hashes before reconciliation, approval,
claiming, or model invocation.

