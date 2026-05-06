# Migration & Reconciliation Test Cases

Verifies the Strangler Fig parallel-run reconciliation framework — the cutover gate that decides when each pipeline is safe to retire from Informatica + Oracle DW.

---

## TC-MG-001 · Variance type — MISSING_IN_NEW correctly classified
**Severity:** Critical · **Covers:** `poc/databricks/lib/reconciliation.py`

- **Given** legacy Oracle DW has `PO-100001`; new Delta Gold does not
- **When** `reconcile()` runs with that pipeline's config
- **Then** the variance row has `variance_type = 'MISSING_IN_NEW'`; `audit.reconciliation_results.variance_rows` includes this row.

## TC-MG-002 · Variance type — MISSING_IN_LEGACY correctly classified
**Severity:** Critical · **Covers:** `reconciliation.py`

- **Given** new Delta Gold has `PO-200001`; legacy Oracle DW does not
- **When** recon runs
- **Then** the variance row has `variance_type = 'MISSING_IN_LEGACY'`.

## TC-MG-003 · Variance type — VALUE_MISMATCH correctly classified
**Severity:** Critical · **Covers:** `reconciliation.py`

- **Given** both sides have `PO-100002` but `delivery_qty = 20` (legacy) vs `25` (new)
- **When** recon runs
- **Then** `variance_type = 'VALUE_MISMATCH'`; the SHA-256 hashes for the two sides differ.

## TC-MG-004 · Within-tolerance flag — true when variance % ≤ tolerance
**Severity:** High · **Covers:** `ReconConfig.variance_tolerance_pct`

- **Given** a pipeline with tolerance 0.5%; total = 1,000 rows; variance = 4 rows
- **When** recon runs
- **Then** `within_tolerance = true` (variance_pct = 0.4%).

## TC-MG-005 · Within-tolerance flag — false when variance % > tolerance
**Severity:** Critical · **Covers:** `reconciliation.py` summary computation

- **Given** the same pipeline; variance = 8 rows
- **When** recon runs
- **Then** `within_tolerance = false` (variance_pct = 0.8% > 0.5%).

## TC-MG-006 · `cutover_ready` — green only after 7 consecutive days
**Severity:** Critical · **Covers:** `cutover_ready()` helper

- **Given** `audit.reconciliation_results` shows 6 consecutive days within tolerance, then 1 day outside, then 6 consecutive days within
- **When** `cutover_ready(spark, pipeline_name, 7)` is called
- **Then** it returns `False` because the 7-day window is not yet contiguous.

## TC-MG-007 · `cutover_ready` — green at the 7th consecutive day
**Severity:** Critical · **Covers:** `cutover_ready()`

- **Given** 7 consecutive days within tolerance
- **When** `cutover_ready(spark, pipeline_name, 7)` is called
- **Then** returns `True`.

## TC-MG-008 · Dimension cutover requires 14 consecutive days (not 7)
**Severity:** High · **Covers:** `reconciliation_tolerance.yaml` per-pipeline `consecutive_green_days_required`

- **Given** `scd2_dim_material` has `consecutive_green_days_required: 14`
- **When** the dashboard checks readiness with only 7 days green
- **Then** it correctly reports "not yet ready" — must wait the full 14.

## TC-MG-009 · Variance samples are capped at 500 rows
**Severity:** Medium · **Covers:** `audit.reconciliation_variance_samples` limit

- **Given** a pipeline with 50,000 variance rows
- **When** recon runs
- **Then** `audit.reconciliation_variance_samples` receives ≤ 500 rows (capped to keep the table size bounded for triage).

## TC-MG-010 · Recon hash-stability across runs
**Severity:** Critical · **Covers:** `_hash_values` determinism

- **Given** the same row in legacy and new
- **When** recon is run on day 1 and day 5
- **Then** both runs produce the same SHA-256; "value match" is stable across days; no spurious variance from hash drift.

## TC-MG-011 · Recon does not block production
**Severity:** High · **Covers:** isolation between recon and main pipeline

- **Given** recon job running on legacy `oracle_dw.f_supplier_otd`
- **When** the main daily orchestrator runs Gold build
- **Then** neither blocks the other; recon reads the snapshot at the time of its own start; main writes proceed normally.

## TC-MG-012 · Pre-prod gate — CD workflow refuses prod deploy when recon red
**Severity:** Critical · **Covers:** `cd-infra.yml` migration-wave gate (described in §6 of CI/CD strategy)

- **Given** a wave-3 pipeline where `within_tolerance = false` for the last 3 days
- **When** the prod deploy is requested
- **Then** the workflow fails-closed before the apply step; the failure message names the pipeline and links to the dashboard.

## TC-MG-013 · 60-day rerun window for backdated SAP corrections
**Severity:** High · **Covers:** `dq_rule sd_003`

- **Given** SAP emits a backdated correction for a delivery 45 days in the past
- **When** the next recon includes the corrected row
- **Then** recon picks up the change; variance reclassifies; the cutover-readiness counter does NOT reset (legacy already had this same correction logic).

## TC-MG-014 · Cutover dry-run — endpoints flip without breaking
**Severity:** High · **Covers:** wave cutover playbook

- **Given** TEST environment with both legacy and new running
- **When** the cutover script flips Power BI dataset connection from legacy to new
- **Then** Power BI tiles continue to render; numbers match (within tolerance) the prior day's view; rollback flips the connection back in < 5 min.

## TC-MG-015 · Decommission — Informatica workflow stays suspended for 30 days
**Severity:** Medium · **Covers:** decommission policy in design §5

- **Given** wave 3 has cut over successfully on 2026-04-01
- **When** time advances to 2026-04-30
- **Then** Informatica workflows for wave 3 are still in `suspended` state; binary archive job has run; on day 31 the license seat is released.
