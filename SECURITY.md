# Security Policy

## Supported versions

Security fixes are provided for the **0.5.x** release line. Upgrade from older
versions before relying on neuDB with sensitive data.

| Version | Supported |
| --- | --- |
| 0.5.x | Yes |
| Earlier versions | No |

## Reporting a vulnerability

Please **do not open a public issue** for a suspected vulnerability. Use GitHub's
[private vulnerability reporting form](https://github.com/sajadxdp0/neudb/security/advisories/new).

Include, where possible:

- The affected version and installation method (GitHub/source or container).
- The component involved (core storage, CLI, API, or agent).
- Reproduction steps, expected behavior, and actual behavior.
- The security impact and any suggested mitigation.
- Sanitized logs or a minimal proof of concept. Never include real API keys,
  credentials, personal data, or database contents.

Please give maintainers time to investigate before disclosing the issue
publicly. Do not test against systems or data you do not own.

## Response and disclosure

Maintainers aim to acknowledge a report within **5 business days**, provide an
initial assessment within **10 business days**, and keep the reporter informed
while a fix is developed. Coordinated disclosure is targeted within **90 days**
of acknowledgement, or sooner when a fix is available. Credit is given with the
reporter's permission.

The HTTP API is a single-process local service. Protect it with a strong
`NEUDB_API_KEY`, keep its port on loopback, and use a trusted TLS reverse proxy
for any remote access.
