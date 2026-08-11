# Security

Obsidian Hermes is currently a design specification, not an executable
release. Its intended system can ingest untrusted content and coordinate
actions, so security-sensitive design flaws are still important.

## Supported versions

There are no runnable releases or supported deployment versions yet. This
policy applies to the current documentation and to examples added during the
design phase.

## Reporting a vulnerability

Report vulnerabilities privately through a
[GitHub Security Advisory](https://github.com/japer-technology/obsidian-hermes/security/advisories/new).

Do not open a public issue for a vulnerability. Include:

- the affected document, component, or proposed workflow;
- the impact and realistic attack path;
- the trust boundary or permission involved;
- reproduction details or a minimal proof of concept, if safe;
- suggested mitigations, if known.

Remove credentials, private vault content, personal data, and unrelated logs
before submitting a report. Maintainers will coordinate validation,
remediation, and disclosure with the reporter.

## Security scope

Examples of in-scope concerns include:

- approval, authorisation, or permission bypasses;
- prompt injection crossing from imported content into trusted instructions;
- path traversal or writes outside the configured vault;
- duplicate or uncertain external effects;
- unsafe lease, retry, or multi-machine coordination;
- secret exposure in Markdown, logs, outputs, or receipts;
- control-bridge privilege escalation or schedule tampering.

General hardening ideas without a concrete vulnerability may be filed through
the design proposal template.
