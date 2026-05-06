# Security Policy

## Reporting a vulnerability

**Do not open a public issue for security vulnerabilities.**

Email `security@chandan.example.com` (PGP key fingerprint
`FFEE 1234 5678 9ABC DEF0  FFEE 1234 5678 9ABC DEF0`) with:

- A description of the vulnerability
- Affected components (Terraform module, Databricks notebook, ADF pipeline name)
- Reproduction steps where applicable
- Your assessment of severity (CVSS v3.1 score if you have one)

We acknowledge receipt within 24 hours and aim to provide a remediation
timeline within 72 hours. Per AS9100 supplier-cybersecurity requirements,
critical issues affecting Boeing/Airbus-bound parts data are escalated to
the customer security team within 48 hours of confirmation.

## Supported versions

| Branch | Status     | Security fixes |
| ------ | ---------- | -------------- |
| `main` | Production | Yes            |
| `uat`  | Pre-prod   | Yes            |
| `develop` | Active dev | Yes         |
| `release/v1.x` (last 2 minor) | Maintenance | Critical only |
| Older release branches | EOL    | None           |

## Out of scope

- Findings on the synthetic sample data in `poc/sample_data/` — this is fake.
- Findings that require physical access to a Chandan plant.
- Denial-of-service via PoC notebooks running on Databricks Community Edition.

## Hardening posture

- All Azure resources behind Private Endpoints; no public IPs on data plane.
- CMK from Key Vault for ADLS, Synapse, Databricks.
- OIDC federation for CI/CD; zero static secrets in repo or org secrets.
- gitleaks + Dependabot + CodeQL run on every PR.
- AS9100 audit lineage Bronze → Source via Purview.
- ITAR-adjacent components data-residency pinned to Central India by Azure Policy.
