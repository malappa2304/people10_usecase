# Functional Test Cases

Source code path is shown for each case. Severity drives regression frequency: **Critical** runs every PR, **High** runs nightly, **Medium** runs on `develop` push, **Low** runs weekly.

---

## TC-FN-001 · Bronze→Silver SAP — explicit schema is enforced
**Severity:** Critical · **Covers:** `poc/databricks/notebooks/01_bronze_to_silver_production_order.py`

- **Given** a Bronze JSON file with an unexpected new column `z_field`
- **When** notebook 01 runs against `SAP_SCHEMA`
- **Then** the unexpected column is dropped (not silently inferred), the run completes, and a WARN-tier metric `unexpected_columns_count = 1` is emitted to `audit.dq_metrics`.

## TC-FN-002 · Bronze→Silver SAP — SAP plant-local timestamp normalises to UTC
**Severity:** Critical · **Covers:** notebook 01, lines transforming `posting_date_local`

- **Given** a Bronze row with `posting_date_local = '2026-05-05 14:00:00'` and `plant_timezone = 'Asia/Kolkata'`
- **When** notebook 01 runs
- **Then** Silver row has `posting_ts_utc = 2026-05-05T08:30:00Z` (IST −5h30m).

## TC-FN-003 · Bronze→Silver SAP — DST transition (US plant, future state)
**Severity:** Medium · **Covers:** notebook 01

- **Given** a Bronze row with `posting_date_local = '2026-03-08 02:30:00'`, `plant_timezone = 'America/Chicago'` (during US spring-forward)
- **When** notebook 01 runs
- **Then** the row is either correctly normalised to UTC or quarantined (DST gap is ambiguous); it must NEVER produce a wrong UTC value silently.

## TC-FN-004 · Bronze→Silver SAP — duplicate `production_order_id` is MERGED, not duplicated
**Severity:** Critical · **Covers:** notebook 01

- **Given** Silver already has `PO-100001` with `quantity = 12`; Bronze emits `PO-100001` with `quantity = 14`
- **When** notebook 01 runs
- **Then** Silver still has exactly one row for `PO-100001`, with `quantity = 14` and a different `row_hash`.

## TC-FN-005 · Bronze→Silver SAP — identical re-emit is a no-op
**Severity:** High · **Covers:** notebook 01 MERGE condition

- **Given** Silver has `PO-100001` with hash `h1`; Bronze emits the same row again
- **When** notebook 01 runs
- **Then** the MERGE skips the update (`condition: t.row_hash <> s.row_hash`); no Silver row is rewritten; `metrics.rows_written = 0`.

## TC-FN-006 · Watermark advances only on success
**Severity:** Critical · **Covers:** `poc/databricks/lib/pipeline_run.py`

- **Given** the prior watermark is `2026-05-05T00:00:00Z`
- **When** notebook 01 runs and an exception is raised mid-flight
- **Then** the audit row is `FAILED`; `audit.pipeline_watermark.watermark_value` is **unchanged** at `2026-05-05T00:00:00Z`.

## TC-FN-007 · Watermark advances on success
**Severity:** Critical · **Covers:** `pipeline_run.py`

- **Given** the prior watermark is `2026-05-05T00:00:00Z`
- **When** notebook 01 successfully ingests rows up to `2026-05-06T08:00:00Z`
- **Then** `audit.pipeline_watermark.watermark_value = 2026-05-06T08:00:00Z` after run completes.

## TC-FN-008 · Pipeline lock prevents double-run
**Severity:** High · **Covers:** `pipeline_run._acquire_lock`

- **Given** `audit.pipeline_lock` already has a row for `bronze_to_silver_production_order`
- **When** a second instance of the notebook starts
- **Then** the second instance raises `RuntimeError: Pipeline '...' is already running` and exits without writing Silver.

## TC-FN-009 · SCD2 — first load creates current rows
**Severity:** Critical · **Covers:** notebook 02 + `scd_helpers.merge_scd2`

- **Given** `gold.dim_material` does not exist; Silver has 5 distinct materials
- **When** notebook 02 runs
- **Then** `gold.dim_material` has exactly 5 rows, all with `is_current = true`, `effective_to IS NULL`, and `effective_from = run_ts`.

## TC-FN-010 · SCD2 — attribute change expires old, inserts new
**Severity:** Critical · **Covers:** `merge_scd2`

- **Given** `dim_material` has `M-AERO-FRAME-A320` with `spec_revision = 'R5'`, `is_current = true`
- **When** Silver emits the same `material_id` with `spec_revision = 'R6'`
- **Then** there are exactly 2 rows for `M-AERO-FRAME-A320`: the R5 row with `is_current = false` and a populated `effective_to`, and the R6 row with `is_current = true` and `effective_to IS NULL`.

## TC-FN-011 · SCD2 — unchanged row produces no version
**Severity:** High · **Covers:** `merge_scd2`

- **Given** `dim_material` has `M-001` current; Silver emits the identical row
- **When** notebook 02 runs
- **Then** row count for `M-001` is unchanged (still 1); no new effective period is opened.

## TC-FN-012 · SCD2 — hash is column-order-stable
**Severity:** High · **Covers:** `add_row_hash`

- **Given** the same set of values
- **When** `add_row_hash` is called with two different column orderings
- **Then** both calls produce the same hash. (See `tests/test_scd2_logic.py::test_hash_is_stable_under_column_reorder`.)

## TC-FN-013 · SCD2 — NULL distinct from empty string
**Severity:** Medium · **Covers:** `add_row_hash` sentinel handling

- **Given** two rows identical except one has `desc = NULL` and the other `desc = ''`
- **When** hashes are computed
- **Then** the two hashes differ. (See `tests/test_scd2_logic.py::test_null_values_are_hashed_distinctly`.)

## TC-FN-014 · DLT supplier OTD — NULL `supplier_id` BLOCKS
**Severity:** Critical · **Covers:** notebook 03 `expect_or_fail("non_null_supplier_id")`

- **Given** Silver has a row with `supplier_id IS NULL`
- **When** the DLT pipeline runs
- **Then** the pipeline fails; `gold_fact_supplier_otd` is not updated; an alert fires to the P1/P2 action group.

## TC-FN-015 · DLT supplier OTD — negative `delivery_qty` QUARANTINES
**Severity:** High · **Covers:** notebook 03 `expect_or_drop("delivery_qty_non_negative")`

- **Given** 100 input rows of which 3 have `delivery_qty < 0`
- **When** the DLT pipeline runs
- **Then** `gold_fact_supplier_otd` has 97 rows, the 3 negative rows go to a `_quarantine` table, and the pipeline succeeds.

## TC-FN-016 · DLT supplier OTD — unknown supplier WARNs only
**Severity:** Medium · **Covers:** notebook 03 `expect("supplier_known_in_dim")`

- **Given** Silver has a row with `supplier_id = 'SUP-ZZ-NEW'` not in `dim_supplier`
- **When** DLT runs
- **Then** the row is included in `gold_fact_supplier_otd`; `audit.dq_metrics` records 1 warning under rule `supplier_known_in_dim`; pipeline succeeds.

## TC-FN-017 · OTD status classification — ON_TIME / LATE / PENDING
**Severity:** Critical · **Covers:** notebook 03 `otd_status` CASE

| `expected_delivery_ts_utc` | `actual_delivery_ts_utc` | Expected `otd_status` |
| -- | -- | -- |
| 2026-05-05T08:00 | 2026-05-05T07:55 | ON_TIME |
| 2026-05-05T08:00 | 2026-05-05T08:00 | ON_TIME |
| 2026-05-05T08:00 | 2026-05-05T13:00 | LATE   |
| 2026-05-05T08:00 | NULL              | PENDING |

## TC-FN-018 · `gold_supplier_otd_daily` aggregation excludes PENDING
**Severity:** High · **Covers:** notebook 03 `gold_supplier_otd_daily`

- **Given** 10 source rows: 4 ON_TIME, 3 LATE, 3 PENDING for one (supplier, plant, date)
- **When** the daily aggregate runs
- **Then** the row has `total_orders = 7`, `on_time_orders = 4`, `otd_pct = 57.14`. PENDING rows are excluded.

## TC-FN-019 · Streaming CNC — 1-min rollup correctness
**Severity:** Critical · **Covers:** notebook 04 stateful aggregation

- **Given** 600 events (10/sec for 60s) into one window
- **When** notebook 04 processes them
- **Then** the Silver row for that window has `event_count = 600`, `vibration_g_avg ≈ mean of inputs`, `vibration_g_p100 = max(inputs)`.

## TC-FN-020 · Streaming CNC — late arrivals beyond watermark are dropped
**Severity:** High · **Covers:** notebook 04 watermark

- **Given** an event with `event_ts = current - 11 min` (watermark = 10 min)
- **When** the stream processes it
- **Then** the event is dropped; metric `late_dropped_count` increments; the in-progress 1-min window is unaffected.

## TC-FN-021 · Streaming CNC — idempotent MERGE on driver restart
**Severity:** Critical · **Covers:** notebook 04 `foreachBatch`

- **Given** a micro-batch wrote 100 rows; the driver restarts before checkpoint commit
- **When** the same micro-batch is replayed
- **Then** Silver row count for the affected window is still 100 (not 200) because of `whenMatchedUpdateAll` on the natural key.

## TC-FN-022 · DQ runner — BLOCK rule failure raises and rolls back
**Severity:** Critical · **Covers:** `poc/databricks/notebooks/05_dq_runner.py`

- **Given** rule `po_001` (NOT NULL `production_order_id`) is BLOCK; 5 rows violate
- **When** `run_rules` is invoked from inside `PipelineRun`
- **Then** an `AssertionError` is raised; the wrapping `PipelineRun` marks `FAILED`; watermark is not advanced.

## TC-FN-023 · DQ runner — QUARANTINE rule writes and drops
**Severity:** High · **Covers:** `dq_runner`

- **Given** rule `po_002` is QUARANTINE; 100 input rows, 7 violate
- **When** `run_rules` runs
- **Then** the returned DataFrame has 93 rows; 7 rows land in `audit.dq_quarantine` with `dq_rule_id = 'po_002'` and the run id.

## TC-FN-024 · DQ runner — WARN rule passes silently with metric
**Severity:** Medium · **Covers:** `dq_runner`

- **Given** rule `po_004` is WARN; 100 input rows, 12 violate
- **When** `run_rules` runs
- **Then** all 100 rows are returned; `audit.dq_metrics` has a row with `severity='WARN'`, `count=12`.

## TC-FN-025 · Synapse view — RLS predicate scopes plant engineer
**Severity:** Critical · **Covers:** Synapse RLS function (described in design §6.6)

- **Given** AAD user `eng-hyd1@chandan.local` is in group `plant-engineer-HYD-1`
- **When** they SELECT from `curated.v_supplier_otd_current`
- **Then** they see only rows where `plant_code = 'HYD-1'`; querying `WHERE plant_code = 'BLR-2'` returns 0 rows.

## TC-FN-026 · Synapse stored proc — `usp_refresh_supplier_otd_view` is idempotent
**Severity:** High · **Covers:** `poc/synapse/ddl/views_curated.sql`

- **Given** `mv_supplier_otd_daily` has 5,000 rows
- **When** the stored proc runs twice in a row
- **Then** row count is identical after both runs (TRUNCATE + INSERT pattern).
