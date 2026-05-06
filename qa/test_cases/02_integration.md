# Integration Test Cases

End-to-end behaviour across ADF → Databricks → Synapse → Power BI. Run nightly on `develop` and on every UAT promotion.

---

## TC-IT-001 · ADF master orchestrator — happy path
**Severity:** Critical · **Covers:** `poc/adf/pipelines/master_orchestrator_pipeline.json`

- **Given** `source_config` has 3 active sources (1 db_cdc, 1 sftp_file, 1 api_rest); fixture data is staged
- **When** `pl_master_orchestrator` runs with `runDate=2026-05-06`
- **Then** the parent succeeds; ForEach completes with 3/3 children succeeded; `DBX_BronzeToSilver` and `DBX_SCD2_DimMaterial` ran in order; Synapse load completed; Power BI dataset refresh API returns 200.

## TC-IT-002 · ADF master — partial failure does not block downstream
**Severity:** High · **Covers:** Switch + ForEach behaviour

- **Given** the same 3 sources, but the api_rest source returns HTTP 503
- **When** the parent runs
- **Then** the failing source has 3 retries (per pipeline policy) before failing; the other 2 children succeed; `DBX_BronzeToSilver` runs against the succeeded sources only; `Notify_OnFailure` Web activity fires once with the failed source name.

## TC-IT-003 · ADF master — orchestrator parallelism honours `batchCount=8`
**Severity:** Medium · **Covers:** ForEach `batchCount`

- **Given** 16 active sources
- **When** the parent runs
- **Then** at any single moment ≤ 8 child pipelines are in `InProgress` state.

## TC-IT-004 · SAP CDC — incremental delta only
**Severity:** Critical · **Covers:** `pl_sap_cdc` + `subscriberProcess`

- **Given** SAP has emitted 1,000 rows; subscriber `CHANDAN_production_order` has consumed up to row 800
- **When** `pl_sap_cdc` runs
- **Then** Bronze has exactly 200 new rows; the subscriber position advances to 1,000.

## TC-IT-005 · Supplier file — event-driven trigger fires within 60s of blob create
**Severity:** High · **Covers:** `trg_event_supplier_file`

- **Given** trigger is in `Started` state
- **When** a `.csv` is uploaded to `/landing/blobs/supplier/...`
- **Then** `pl_supplier_file` is invoked within 60 seconds; pipeline run id appears in ADF activity log.

## TC-IT-006 · Synapse load — PolyBase via staging
**Severity:** Critical · **Covers:** `pl_synapse_load`

- **Given** Gold Delta `gold.fact_supplier_otd` has 100K rows
- **When** `pl_synapse_load` runs with `load_mode='TRUNCATE_AND_LOAD'`
- **Then** Synapse `dbo.fact_supplier_otd` has 100K rows; load completed in < 5 min using PolyBase staging at `staging/synapse_load`; reject count = 0.

## TC-IT-007 · Streaming → batch unification on the same Silver
**Severity:** Critical · **Covers:** design §1, §6.2 unification claim

- **Given** Silver `silver.cnc_telemetry_1min` is being written by the streaming job; nightly batch job reads from the same table
- **When** the nightly batch joins `silver.cnc_telemetry_1min` with `silver.production_order` on `plant_code` + time window
- **Then** the join completes without lock contention; row counts match `event_count` aggregation; no streaming-batch isolation issues.

## TC-IT-008 · Tiered SLA — three consumers off one Event Hubs source
**Severity:** High · **Covers:** design §6.1 tiered SLA pattern

- **Given** Event Hubs topic `cnc-telemetry` has 3 active consumers: 30-sec OEE job, 5-min ML scoring job, hourly AS9100 audit job
- **When** all three are running for 1 hour
- **Then** each consumer's Silver / Gold output advances at its own cadence; consumers do not block each other; partition lag per consumer stays below SLA threshold.

## TC-IT-009 · Power BI dataset refresh after Synapse load
**Severity:** High · **Covers:** ADF `Exec_SynapseLoad` → Power BI

- **Given** `pl_synapse_load` completed at 02:38 UTC
- **When** the post-load Web activity calls Power BI dataset refresh API
- **Then** API returns 200; Power BI service shows refresh status `Completed` within 10 minutes; tile latency on the executive report is < 1 sec.

## TC-IT-010 · End-to-end audit lineage — Power BI tile back to Bronze row
**Severity:** Critical · **Covers:** AS9100 audit traceability claim

- **Given** a Power BI tile shows `Supplier OTD = 87%` for `SUP-TATA-AERO` on 2026-05-06
- **When** an auditor traces the tile through Purview
- **Then** Purview shows the lineage: Power BI → `curated.v_supplier_otd_current` → `dbo.fact_supplier_otd` (Synapse) → `gold.fact_supplier_otd` (Delta) → `silver.supplier_dispatch` → Bronze SAP CDC payload → SAP source object. Every hop has a row count.

## TC-IT-011 · Cross-source join — production order × supplier dispatch × CNC
**Severity:** High · **Covers:** silos-broken claim

- **Given** Gold has fact_production_order, fact_supplier_otd, and fact_machine_telemetry for the same plant + time window
- **When** the analyst joins all three on `plant_code + time window` to get "for this production order, did the supplier deliver on time AND was the machine healthy?"
- **Then** the join runs in < 30 seconds in Synapse Serverless and produces the expected combined view.

## TC-IT-012 · Failure path — Web activity Logic App triggers Teams notification
**Severity:** Medium · **Covers:** `Notify_OnFailure`

- **Given** `DBX_BronzeToSilver` has been deliberately broken
- **When** the master orchestrator runs
- **Then** the failure dependency fires; the Web activity returns 200; a message appears in the data-platform Teams channel within 60 sec containing pipeline name, run id, and severity P2.
