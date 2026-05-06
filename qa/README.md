# QA — Test Plan, Test Cases, and Pass Report

This directory holds the QA artefacts for the Chandan Aerospace lakehouse. It maps directly to the design in [`../docs/02_design_document.md`](../docs/02_design_document.md) and the CI/CD posture in [`../docs/04_cicd_strategy.md`](../docs/04_cicd_strategy.md).

## Structure

```
qa/
├── README.md                     this file
├── test_plan.md                  master plan: scope, types, env, RACI, exit criteria
├── test_cases/
│   ├── 01_functional.md          ingestion, transformation, SCD2, DLT
│   ├── 02_integration.md         end-to-end ADF → DBX → Synapse → Power BI
│   ├── 03_performance.md         throughput, latency, concurrency, batch window
│   ├── 04_security.md            AAD, MI, CMK, PE, RLS, secret hygiene
│   ├── 05_migration_reconciliation.md   parallel-run, variance types, tolerance
│   ├── 06_compliance.md          AS9100, DGCA, ITAR
│   └── 07_dq_severity.md         BLOCK / QUARANTINE / WARN behaviour
└── qa_pass_report.md             execution summary, traceability, sign-off
```

## How to read this

1. Start with `test_plan.md` (~10 min) for strategy + entry/exit criteria.
2. Skim `test_cases/01_functional.md` to see the Given/When/Then format we use throughout.
3. Read `qa_pass_report.md` for the executive summary of which tests passed, failed, and the sign-off recommendation.

## Conventions

- **Test ID format:** `TC-<SUITE>-<NNN>` — e.g. `TC-FN-014` for functional case 14.
- **Format:** Given / When / Then per case. One *behaviour* per case, not one assertion.
- **Severity:** Critical / High / Medium / Low — decides regression frequency.
- **Traceability:** every case lists the design-doc section, requirement ID (R-NN), and the source code path it covers.
- **Status in pass report:** Pass / Fail / Blocked / Skipped / Deferred — same vocabulary CI uses.
