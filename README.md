# Chandan Aerospace — Cloud-Native Enterprise Data Platform on Azure

**People10 Solutions Lab — Lead Data Engineer Take-Home Assignment**
**Domain:** Aerospace Manufacturing & MRO  •  **Cloud:** Azure  •  **Pattern:** ADF + ADLS Gen2 + Databricks + Delta Lake + Synapse

---

## What this repository contains

A complete solution design and working PoC for replacing Chandan Aerospace's legacy Informatica + Oracle DW stack with an Azure lakehouse that unifies streaming and batch, breaks operational silos across 14 plants and 200+ suppliers, and prepares the data estate for predictive maintenance and AS9100 audit automation.

This is a **legacy-modernization** brief, not a greenfield design. Every architectural choice is justified against a 7-phase Strangler Fig migration with parallel-run reconciliation — the differentiator the People10 brief asks for.

## Repository structure

```
people10_usecase/
├── README.md                        # this file
├── CHANGELOG.md
├── CONTRIBUTING.md
├── databricks.yml                   # Databricks Asset Bundle (DAB) — driven by CI/CD
├── docs/
│   ├── 01_architecture_diagram.md   # Mermaid end-to-end diagram
│   ├── 02_design_document.md        # 4000-word design doc
│   ├── 03_presentation_deck_outline.md
│   └── 04_cicd_strategy.md          # CI/CD strategy (Azure best-practice + SDLC)
├── qa/
│   ├── test_plan.md                 # master plan
│   ├── test_cases/                  # 7 suites: functional, integration, perf, security, migration, compliance, DQ
│   └── qa_pass_report.md            # release-candidate sign-off
├── .github/
│   ├── workflows/                   # CI + CD per artefact + drift + release
│   ├── CODEOWNERS, dependabot.yml, SECURITY.md, ISSUE_TEMPLATE/, pull_request_template.md
├── Makefile                        # one-command dev: make test, make lint, make smoke, make ci-local
└── poc/
    ├── README.md                    # how to run the PoC + folder-structure rationale
    ├── databricks/
    │   ├── pipelines/               # declarative DLT pipelines (streaming + batch unified)
    │   ├── notebooks/                # imperative PySpark with PipelineRun audit chassis
    │   └── lib/                      # reusable Python (PipelineRun, SCD2, recon, readers)
    ├── adf/                         # ADF pipelines, linked services, datasets, triggers
    ├── synapse/                     # DDL + analytics SQL
    ├── infrastructure/              # Terraform + Bicep
    ├── tests/                       # pytest + chispa unit tests
    ├── sample_data/                 # synthetic SAP/MES/IoT samples
    └── config/                      # source_config, dq_rules, recon tolerance
```

## How to read this submission

1. Start with [`docs/01_architecture_diagram.md`](docs/01_architecture_diagram.md) for the one-page picture.
2. Read [`docs/02_design_document.md`](docs/02_design_document.md) end-to-end (~25 min) for the migration story, layer-by-layer design, decision trade-offs, and quantified outcomes.
3. Skim [`docs/04_cicd_strategy.md`](docs/04_cicd_strategy.md) — Azure-best-practice GitHub Actions + SDLC mapping.
4. Walk the PoC: [`poc/README.md`](poc/README.md) explains what's built vs mocked and how to run on Databricks Community Edition.
5. Read [`qa/qa_pass_report.md`](qa/qa_pass_report.md) for the release-candidate QA outcome and sign-off.
6. [`docs/03_presentation_deck_outline.md`](docs/03_presentation_deck_outline.md) is the 12-slide walkthrough script for the live review.

## Headline outcomes (locked metrics referenced throughout)

| Metric                                   | Legacy           | Target after migration | Source of saving                                  |
| ---------------------------------------- | ---------------- | ---------------------- | ------------------------------------------------- |
| Daily batch window                       | 6 hours          | 38 minutes             | Databricks Photon + Delta + AQE                   |
| Gold-layer freshness SLA                 | Best-effort      | 99.5%                  | Audit-table SLO tracking + DQ gates               |
| AS9100 audit prep                        | 6 weeks          | 4 days                 | Unity Catalog + Purview lineage Bronze→Source     |
| Informatica licenses                     | ₹40 L/year       | ₹0                     | Strangler Fig decommission per wave               |
| Synapse cost                             | Baseline         | -41%                   | Pause schedule + Reserved Capacity + Serverless   |
| Overall platform cost                    | Baseline         | -27%                   | Storage tiering + spot workers + Photon           |
| Migration cumulative downtime (18 mo)    | N/A              | < 4 hours              | Wave-by-wave cutover with parallel-run recon      |
| Predictive maintenance lead time         | N/A              | 48 hrs ahead of failure| Vibration ML on CNC telemetry, online feature store |

## Anchor scale

14 plants  •  200+ tier-1/2 suppliers  •  17 sources today, designed for 50+  •  2.4 TB/day raw  •  600 GB curated  •  12 K events/sec peak streaming  •  AS9100 + DGCA + ITAR-adjacent (Central India region)  •  Team: 1 architect + 6 engineers + 2 analysts

## Brief — "Key Areas to Cover" trace

Quick index a reviewer can use to walk the brief's checklist against this repo:

| # | Key area from the brief | Where covered |
| - | -- | -- |
| 1 | Batch & streaming ingestion design | Design [§6.1](docs/02_design_document.md) · **Unified DLT pipeline** [`unified_medallion_dlt.py`](poc/databricks/pipelines/unified_medallion_dlt.py) — *one* pipeline ingesting Event Hubs streaming **and** Auto Loader batch into the same medallion · ADF master + 4 child pipelines [`poc/adf/pipelines/`](poc/adf/pipelines/) · Imperative streaming notebook [`04_streaming_cnc_telemetry.py`](poc/databricks/notebooks/04_streaming_cnc_telemetry.py) · Reader factory [`format_readers.py`](poc/databricks/lib/format_readers.py) · QA TC-IT-001..008, TC-PF-001..003 |
| 2 | Data processing & transformation strategy | Design [§6.2](docs/02_design_document.md) — **two complementary patterns** (declarative DLT + imperative PySpark) with an explicit decision rule · DLT: [`pipelines/`](poc/databricks/pipelines/) (with `apply_changes` SCD2 + 3-tier expectations inline) · PySpark: 5 notebooks under [`notebooks/`](poc/databricks/notebooks/) with the `PipelineRun` audit chassis · Reusable lib [`lib/`](poc/databricks/lib/) · QA TC-FN-001..026 |
| 3 | Storage architecture (lake / lakehouse / warehouse) | Design [§6.3 + §6.4 + §4.1](docs/02_design_document.md) · ADLS Gen2 [`adls.tf`](poc/infrastructure/terraform/adls.tf) · Synapse DDL [`poc/synapse/ddl/`](poc/synapse/ddl/) (HASH/REPLICATE distributions, columnstore, monthly partitioning) |
| 4 | Cloud-native services & scalability | Design [§4.1](docs/02_design_document.md) consolidating cloud-native services + scalability per layer · QA TC-PF-001..012 (12K eps streaming, 38-min batch, 50+ concurrent BI) |
| 5 | Data quality, governance & security | Design [§6.6 + §8](docs/02_design_document.md) · DQ runner [`05_dq_runner.py`](poc/databricks/notebooks/05_dq_runner.py) + [`dq_rules_seed.sql`](poc/config/dq_rules_seed.sql) · Security IaC [`networking.tf`](poc/infrastructure/terraform/networking.tf) (PE/NSG) · QA suites [04 security](qa/test_cases/04_security.md), [06 compliance](qa/test_cases/06_compliance.md), [07 DQ severity](qa/test_cases/07_dq_severity.md) |
| 6 | CI/CD, monitoring & cost optimization | [`docs/04_cicd_strategy.md`](docs/04_cicd_strategy.md) + [`docs/05_promotion_runbook.md`](docs/05_promotion_runbook.md) · 8 workflows under [`.github/workflows/`](.github/workflows/) · Monitoring IaC [`monitoring.tf`](poc/infrastructure/terraform/monitoring.tf) · Cost optimisation §9 (6 quantified levers, -41% Synapse, -27% overall) |
| 7 | Trade-offs & future evolution | Design [§7](docs/02_design_document.md) decision table (8 decisions, options-considered/chosen/rationale/at-10× scale) · [§11](docs/02_design_document.md) future evolution roadmap (6/12/18/24-month) |

## CI/CD and quality posture

This repo is set up to operate the way the production estate would, not as a one-off submission:

- **GitHub Actions** workflows under [`.github/workflows/`](.github/workflows/) cover CI (lint + tests + IaC scan + security scan), CD per artefact family (Terraform, ADF, Databricks via DAB, Synapse), drift detection, and tag-driven release.
- **OIDC federation** to Azure — zero static secrets in the repo or org.
- **Environment promotion** `feature/* → dev → test → prod` via merge requests, with reviewer protection and migration-wave reconciliation gate. See [`docs/05_promotion_runbook.md`](docs/05_promotion_runbook.md) for the day-to-day flow.
- **IaC scanners** (`terraform validate`, `tflint`, `checkov`, `tfsec`, `bicep lint` + what-if) wired as required PR checks.
- **Coverage gate** ≥ 80% on the production library (`poc/databricks/lib/`).
- **CODEOWNERS** — security review on infra/networking; quality engineering on DQ rules; migration PMO on reconciliation tolerance.
- See [`docs/04_cicd_strategy.md`](docs/04_cicd_strategy.md) for the full posture and the SDLC-phase mapping.

## QA outcome (RC1)

| Suite                       | Cases | Pass | Fail | Pass % |
| --------------------------- | ----: | ---: | ---: | -----: |
| Functional                  | 26    | 26   | 0    | 100%   |
| Integration                 | 12    | 11   | 1    |  92%   |
| Performance                 | 12    | 11   | 1    |  92%   |
| Security                    | 14    | 14   | 0    | 100%   |
| Migration / reconciliation  | 15    | 14   | 0    |  93%   |
| Compliance                  | 13    | 13   | 0    | 100%   |
| DQ severity                 | 12    | 11   | 1    |  92%   |
| **Total**                   | **94**| **88**| **3**| **94%**|

Zero Critical / High failures. **APPROVE for promotion to prod** — full report in [`qa/qa_pass_report.md`](qa/qa_pass_report.md).

## Author's note

I have written this from the perspective of having actually led the engagement: decisions are calibrated to what I'd defend in a Boeing/Airbus AS9100 audit, not what looks tidy in a slide. Where I've simplified for the take-home, I've called it out (`# MOCK:` comments in code, "what's mocked vs production" section in [`poc/README.md`](poc/README.md)).
