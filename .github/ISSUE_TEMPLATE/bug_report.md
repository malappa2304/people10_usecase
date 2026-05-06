---
name: Bug report
about: A pipeline ran but produced wrong / missing / duplicate data, or failed unexpectedly
title: '[BUG] '
labels: bug, triage
assignees: ''
---

## What happened

<!-- Plain English — one paragraph. -->

## Where

| Field | Value |
| -- | -- |
| Pipeline (ADF / Databricks) |  |
| Source system |  |
| Bronze / Silver / Gold layer |  |
| Plant code(s) affected |  |
| Run ID (`audit.pipeline_run.run_id`) |  |
| Time window (UTC) |  |

## Expected vs actual

**Expected:**

**Actual:**

## Reproduction

<!-- Steps. Include the SQL query that surfaces the issue. -->

```sql

```

## Impact

- [ ] Production line affected (cite plant + ₹/day if known)
- [ ] AS9100 audit traceability affected
- [ ] Reporting only — no operational impact
- [ ] Migration/reconciliation variance — link to `audit.reconciliation_results` row

## Suggested severity

- [ ] P1 — production halted / data loss
- [ ] P2 — incorrect numbers visible to executives
- [ ] P3 — reporting drift, no operational risk
- [ ] P4 — cosmetic / docs

## Logs and screenshots

<!-- Attach pipeline_run row, ADF activity output, Databricks job log. Redact PII. -->
