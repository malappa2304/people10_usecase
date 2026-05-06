# Data Quality Severity Test Cases

Verifies the BLOCK / QUARANTINE / WARN contract under both DLT (`expect_or_fail` / `expect_or_drop` / `expect`) and the custom `dq_runner.py`.

---

## TC-DQ-001 · DLT BLOCK — `expect_or_fail` halts pipeline and pages on-call
**Severity:** Critical · **Covers:** notebook 03 `expect_or_fail("non_null_supplier_id")`

- **Given** the DLT pipeline configured with rule `non_null_supplier_id` BLOCK; input has a NULL `supplier_id`
- **When** the pipeline runs
- **Then** the pipeline transitions to `FAILED`; `gold_fact_supplier_otd` is not advanced; alert reaches `ag-chandan-prod-p1p2` action group; on-call PagerDuty incident raised.

## TC-DQ-002 · DLT QUARANTINE — `expect_or_drop` keeps pipeline running, drops violators
**Severity:** Critical · **Covers:** notebook 03 `expect_or_drop("delivery_qty_non_negative")`

- **Given** 1,000 input rows; 4 with `delivery_qty < 0`
- **When** DLT runs
- **Then** target table has 996 rows; the 4 violators land in DLT's quarantine view; pipeline status = SUCCESS.

## TC-DQ-003 · DLT WARN — `expect` passes through and emits metric
**Severity:** High · **Covers:** notebook 03 `expect("supplier_known_in_dim")`

- **Given** 1,000 rows; 12 with unknown `supplier_id`
- **When** DLT runs
- **Then** all 1,000 rows land in target; DLT event log shows 12 warnings against the rule; pipeline status = SUCCESS.

## TC-DQ-004 · Custom DQ runner — BLOCK on non-DLT pipeline
**Severity:** Critical · **Covers:** `dq_runner.run_rules` for rule severity BLOCK

- **Given** a non-DLT PySpark notebook calls `run_rules(df, "silver.production_order", run_id)`; `dq_rules.po_001` is BLOCK; some rows violate
- **When** the runner executes
- **Then** an `AssertionError` is raised with the rule_id and a sample of violating rows; the wrapping `PipelineRun` marks `FAILED`; watermark not advanced.

## TC-DQ-005 · Custom DQ runner — QUARANTINE writes to `audit.dq_quarantine`
**Severity:** Critical · **Covers:** `dq_runner` QUARANTINE branch

- **Given** rule `po_002` is QUARANTINE; 7 of 100 rows violate
- **When** `run_rules` runs
- **Then** the returned DataFrame has 93 rows; `audit.dq_quarantine` has 7 rows tagged with `dq_rule_id='po_002'` and the run_id; downstream notebook receives only the clean DataFrame.

## TC-DQ-006 · Custom DQ runner — WARN emits metric without dropping
**Severity:** High · **Covers:** `dq_runner` WARN branch

- **Given** rule `po_004` is WARN; 12 of 100 rows violate
- **When** `run_rules` runs
- **Then** all 100 rows are returned; `audit.dq_metrics` has a row `severity='WARN', rule_id='po_004', count=12`.

## TC-DQ-007 · DQ runner — disabled rule is skipped
**Severity:** Medium · **Covers:** `is_enabled` flag

- **Given** rule `cnc_002` has `is_enabled = 0`
- **When** `load_rules('silver.cnc_telemetry_1min')` runs
- **Then** rule `cnc_002` is not in the returned list; even if input data violates it, the pipeline succeeds.

## TC-DQ-008 · DQ runner — unknown severity raises configuration error
**Severity:** Medium · **Covers:** `run_rules` defensive branch

- **Given** a rule with severity `'BLOCKER'` (typo)
- **When** `run_rules` evaluates it
- **Then** a `ValueError("Unknown severity: BLOCKER")` is raised; no rows pass through; the misconfiguration is fail-loud.

## TC-DQ-009 · 3-sigma row-count anomaly detector
**Severity:** High · **Covers:** anomaly detection job (described in design §8)

- **Given** 30-day rolling row count for `gold.fact_supplier_otd` has σ = 5,000 around mean 200,000
- **When** today's count is 180,000 (4σ below mean)
- **Then** an alert fires to the data-platform Teams channel; `audit.dq_metrics` records the anomaly; pipeline does not block (anomaly is informational, not gating).

## TC-DQ-010 · Cross-table reconciliation — SAP order line count vs MES work order count
**Severity:** Critical · **Covers:** nightly cross-table recon (design §8)

- **Given** SAP emits 12,500 order lines; MES has 12,500 corresponding work orders
- **When** the cross-table recon runs
- **Then** `audit.dq_metrics` records `match=true`; if drift > 0.5%, an alert fires.

## TC-DQ-011 · DQ rules audit — every Silver/Gold table has at least one BLOCK rule
**Severity:** High · **Covers:** `dq_rules_seed.sql` coverage

- **Given** the list of all Silver and Gold tables
- **When** `audit.dq_rules` is queried with `severity = 'BLOCK'` grouped by `table_name`
- **Then** every table appears in the result; no production table ships without a primary-key NOT-NULL BLOCK rule.

## TC-DQ-012 · Quarantine table size — capped to 30-day rolling window
**Severity:** Medium · **Covers:** quarantine retention policy

- **Given** `audit.dq_quarantine` has been collecting for 30 days
- **When** the daily compaction job runs
- **Then** rows older than 30 days are deleted (dq team has had the chance to triage); table size remains bounded; row count > 30 days = 0.
