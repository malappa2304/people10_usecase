# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [Unreleased]

## [1.0.0-rc1] — 2026-05-06

### Added — Foundation cut

- **Architecture & design**
  - End-to-end Mermaid architecture diagram (`docs/01_architecture_diagram.md`)
  - 4,000-word design document with 7-phase Strangler Fig migration plan (`docs/02_design_document.md`)
  - 12-slide presentation deck outline (`docs/03_presentation_deck_outline.md`)
  - CI/CD strategy mapped to Azure Well-Architected + SDLC (`docs/04_cicd_strategy.md`)

- **PoC source code**
  - Reusable Databricks library: `PipelineRun` audit chassis, hash-based SCD2 helpers, multi-format reader factory, parallel-run reconciliation
  - 5 Databricks notebooks: Bronze→Silver SAP, SCD2 dim_material, DLT supplier_otd with 3-tier expectations, Structured Streaming CNC, custom DQ runner
  - 5 ADF pipelines (master orchestrator, batch ingestion, SAP CDC, supplier file, Synapse load) + 3 linked services + 4 datasets + 2 triggers
  - 4 Synapse DDL files + 4 analytics queries (supplier OTD trend, top suppliers by plant, production cycle time, quality defect rate)
  - Terraform foundation skeleton (ADLS, Databricks, Synapse, networking, monitoring) + Bicep ADF
  - 3 pytest unit-test modules covering SCD2 hash logic, PipelineRun chassis, reconciliation framework
  - Synthetic sample data + control-plane seed SQL + reconciliation tolerance config

- **CI/CD**
  - GitHub Actions workflows: `ci.yml`, `cd-infra.yml`, `cd-databricks.yml`, `cd-adf.yml`, `cd-synapse.yml`, `drift-detection.yml`, `release.yml`, plus reusable Azure-login workflow
  - Databricks Asset Bundle config (`databricks.yml`) with dev / uat / prod targets
  - OIDC federation to Azure (zero static secrets); environment-scoped credentials
  - Required PR checks: ruff, mypy --strict, yamllint, sqlfluff, pytest with 80% coverage gate, terraform validate + tflint + checkov + tfsec, bicep lint + what-if, ADF JSON schema, gitleaks, dependency-review
  - Repo hygiene: CODEOWNERS, Dependabot, PR template, SECURITY.md, issue templates

- **QA**
  - Master test plan with entry/exit criteria, RACI, risk register
  - 7 test suites — 94 test cases — covering functional, integration, performance, security, migration/reconciliation, compliance (AS9100/DGCA/ITAR), and DQ severity
  - QA pass report for v1.0.0-rc1: 88/94 passed, zero Critical/High failures, **APPROVE for prod**

### Locked metrics validated in this release

- 12.6 K events/sec sustained for 4 h (target: 12 K eps)
- 34-min batch on representative load (target: ≤ 38 min)
- 99.7% Gold-layer freshness over 14-day UAT window (target: 99.5%)
- 50 concurrent BI users with p95 = 4.1 sec (target: ≤ 5 sec)
- AS9100 audit prep dry-run 3.5 days (target: ≤ 4 days)
- Synapse cost projection -42% (target: -41%)

### Known limitations

- Cosmos DB online feature store referenced in design but not provisioned in Terraform yet (planned v1.1)
- Purview scan cadence currently hourly; awaiting Premium licence for 6-hourly target
- Decommission test (TC-MG-015) deferred to v1.2 because it requires 30 days post-cutover

### Migration

This release is **foundation only** — the platform is stood up and the migration framework is operational. No legacy Informatica workflow has been retired yet. Wave 1 (Quality Inspection pilot) is scheduled to begin under v1.1.

---

[Unreleased]: https://github.com/malappa2304/people10_usecase/compare/v1.0.0-rc1...HEAD
[1.0.0-rc1]: https://github.com/malappa2304/people10_usecase/releases/tag/v1.0.0-rc1
