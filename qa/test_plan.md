# Master Test Plan — Chandan Aerospace Lakehouse

| Field | Value |
| -- | -- |
| Document version | 1.0 |
| Date | 2026-05-06 |
| Owner | QA Lead, People10 Solutions Lab |
| Approvers | Data Platform Lead · Security Lead · Migration PMO |
| Linked design | [`../docs/02_design_document.md`](../docs/02_design_document.md) |
| Linked CI/CD | [`../docs/04_cicd_strategy.md`](../docs/04_cicd_strategy.md) |

---

## 1. Purpose and scope

This plan defines the testing strategy for the Cloud-Native Enterprise Data Platform we are building for Chandan Aerospace. It covers all four artefact families — Terraform infra, ADF pipelines, Databricks notebooks, Synapse SQL — plus the migration parallel-run reconciliation, security posture, and AS9100/DGCA/ITAR compliance controls.

### 1.1 In scope

- Functional correctness of Bronze → Silver → Gold transformations across the 17 sources / 4 conformed facts / 4 dimensions.
- End-to-end orchestration through ADF → Databricks → Synapse.
- Streaming ingestion at 12K events/sec peak, three SLA tiers off the same source.
- Hash-based SCD2 across `dim_material`, `dim_supplier`, `dim_workcenter`, `dim_aircraft_component`.
- DQ severity tiers (BLOCK / QUARANTINE / WARN) under DLT and the custom runner.
- Migration parallel-run reconciliation framework — all three variance types and the tolerance gate.
- Security: AAD / managed identity / CMK / Private Endpoints / RLS / secret hygiene.
- Compliance: AS9100 lineage, DGCA 7-year retention, ITAR-adjacent residency.
- CI/CD: PR validation, environment promotion, drift detection, rollback.

### 1.2 Out of scope

- Power BI report-layer visual testing (handled by analytics-team).
- SAP / MES / Teamcenter source-side functional testing (vendor-managed).
- Hardware-level CNC OPC-UA emitter testing (plant maintenance team).
- Full network penetration test (separate engagement, security-team owned).

## 2. Test types and what each is for

| # | Type | Why we run it | Tool / approach | Cadence |
| -- | -- | -- | -- | -- |
| 1 | **Unit** | Logic correctness in isolation | pytest + chispa | Every PR |
| 2 | **Functional / system** | End-to-end behaviour against synthetic data | Notebook runs in dev workspace | Every PR + nightly |
| 3 | **Integration** | ADF → DBX → Synapse handoffs | Databricks Workflows fixture + smoke ADF run | On `dev` push (every MR merge into `dev`) |
| 4 | **Performance** | Throughput / latency / concurrency targets | Synthetic 12K eps load generator + JMeter for Synapse | Pre-cutover and weekly on prod |
| 5 | **Security** | Posture controls behave as designed | Defender for Cloud + manual verification | Every release + quarterly review |
| 6 | **Migration / reconciliation** | Parity between legacy DW and new Gold | `reconciliation.py` + dashboard | Daily during migration waves |
| 7 | **Compliance** | AS9100 / DGCA / ITAR controls | Manual verification + Purview lineage export | Per release + annual audit |
| 8 | **Data quality** | DLT EXPECT + custom runner severity | Inline DLT + `dq_runner.py` | Every pipeline run |
| 9 | **DR / failover** | Game-day exercise | Manual quarterly drill | Quarterly |

## 3. Test environments

| Env | Purpose | Source data | Differences from prod |
| -- | -- | -- | -- |
| **local (CE)** | Developer self-test | Sample fixtures in `poc/sample_data/` | No Unity Catalog; no PEs |
| **dev**  | Auto-deploys on every MR merge into `dev` branch  | Synthetic + obfuscated 1-day prod slice | Smaller cluster sizes; spot workers |
| **test** | Auto-deploys on every MR merge into `test` branch | Production-shape data, masked          | Same shape as prod; lower DWU |
| **prod** | Tag-driven; only after `test → prod` MR merges    | Real data                              | Full sizing |

Promotion path: `feature/* → dev → test → prod`. Every transition is a merge request. Promotion runbook in [`../docs/05_promotion_runbook.md`](../docs/05_promotion_runbook.md).

Production-shape data on TEST is masked per the data-classification matrix: customer names hashed, supplier banking details redacted, employee names tokenised.

## 4. Roles and responsibilities (RACI)

| Activity | QA | DataPlatform | Security | Migration PMO | Stakeholders |
| -- | -- | -- | -- | -- | -- |
| Author functional cases | R | A | I | I | C |
| Author migration cases | C | C | I | R/A | C |
| Author security cases | C | C | R/A | I | I |
| Execute regression | R/A | C | I | I | I |
| Execute migration recon | R | A | I | C | C |
| Sign off prod release | A | A | A | A | I |

## 5. Entry and exit criteria

### 5.1 Entry to TEST (the `dev → test` MR)
- All P1/P2 DEV defects closed
- Coverage ≥ 80% on `poc/databricks/lib/`
- Terraform plan against TEST empty after deploy
- All CI checks green for ≥ 24 h on `dev`

### 5.2 Exit from TEST (the `test → prod` MR)
- 100% pass on Critical and High functional cases
- ≥ 95% pass on Medium; documented workaround for any failures
- Performance: 12K eps streaming sustained for ≥ 4 h with no driver restarts; 38-min batch achieved
- Security: Defender posture ≥ 90 / 100; zero High findings open
- Migration recon: `within_tolerance = true` for ≥ 7 consecutive days for the wave's pipelines (≥ 14 for dimensions)
- Compliance: Purview lineage exportable for any random Gold row to source
- Sign-off recorded in `qa_pass_report.md`

### 5.3 Suspension / resume
Suspend testing if:
- A P1 defect is found that blocks > 30% of test cases
- Test environment is unstable for > 2 hours
- Source-side schema drift breaks > 10 fixtures simultaneously

Resume only when the trigger condition is documented as resolved.

## 6. Test data strategy

- **Synthetic data** in `poc/sample_data/` covers happy-path schema. Each case lists the fixture(s) it uses.
- **Boundary fixtures** under `qa/fixtures/` (created during execution): null-only rows, max-length strings, boundary timestamps (DST transitions, leap-second), unicode names.
- **Masked production slice** in TEST — `dbx_test.qa_fixtures.*` schema. Refreshed weekly from a 1-day prod export with reversible tokenisation.

## 7. Defect lifecycle

`Open` → `Triaged` (severity + owner) → `In progress` → `Fixed in dev branch` → `Verified on DEV env` → `Closed`. Critical defects re-open the relevant test case in the regression set automatically.

Severity vs priority:
- **Critical** — production halted, data loss, audit failure.
- **High** — incorrect numbers in executive reporting; recoverable.
- **Medium** — single-source / single-plant impact; workaround exists.
- **Low** — cosmetic / docs.

## 8. Risk register (test-side)

| # | Risk | Mitigation |
| -- | -- | -- |
| TR-1 | TEST data divergence from prod masks real bugs | Weekly refresh; statistical drift check before each test cycle |
| TR-2 | OPC-UA emulator under-counts vs real CNC | Cross-check against 10-min capture from one real machine per quarter |
| TR-3 | Reconciliation false-positives on legacy timezone bug | Variance tolerance per pipeline; data-owner sign-off |
| TR-4 | Test cluster cost spike during perf runs | Scheduled tear-down + spot workers; budget alert at 70% of monthly cap |
| TR-5 | Late-arriving SAP corrections during recon window | 60-day rerun window built into recon framework |

## 9. Tooling

| Need | Tool | Where |
| -- | -- | -- |
| Unit tests | pytest, chispa | `poc/tests/` |
| Notebook runs | Databricks Workflows | dev workspace |
| Load generation | OPC-UA emitter (custom) + JMeter | dev workspace |
| Recon | `reconciliation.py` | Databricks job |
| Lineage export | Microsoft Purview API | manual + CI on release |
| Defender posture | Defender for Cloud | Azure portal + CI export |
| Defect tracking | GitHub Issues with labels | this repo |

## 10. Reporting

The single source of truth is [`qa_pass_report.md`](qa_pass_report.md). It is regenerated for each release candidate and pasted into the Release notes.
