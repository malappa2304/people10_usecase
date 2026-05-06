# Design Document — Cloud-Native Enterprise Data Platform for Chandan Aerospace

**Author:** Lead Data Engineer, People10 Solutions Lab
**Cloud:** Azure (ADF + ADLS Gen2 + Databricks + Delta Lake + Synapse)
**Domain:** Aerospace Manufacturing & MRO
**Status:** Solution design + working PoC for People10 take-home review

---

## 1. Executive Summary

Chandan Aerospace runs 14 plants and 200+ tier-1/2 suppliers on an estate stitched together with Informatica PowerCenter and an Oracle data warehouse. After ten years, that stack is the bottleneck: 200+ mappings, 6-hour batch windows, ₹40 L/year of licenses, and zero streaming. Auditors take six weeks to assemble AS9100 evidence. A single supplier disruption goes undetected for seven days because OTD reporting lags. One late part can cost ₹2-5 Cr/day in line stoppages.

I designed a cloud-native lakehouse on Azure that **replaces** Informatica with Azure Data Factory (ADF), **unifies** 12 K events/sec of CNC telemetry with batch CDC from SAP S/4HANA / MES / Teamcenter on the same Delta Lake, **breaks the silos** across plants and suppliers into four conformed facts, **delivers** sub-minute streaming insight alongside Power BI executive views, and **prepares** the estate for predictive-maintenance ML and AS9100 audit automation.

All five People10 brief requirements are addressed explicitly: **(1)** modern lakehouse over legacy DW, **(2)** unified streaming + batch on Delta, **(3)** sub-minute Gold freshness for OEE and supplier OTD, **(4)** Synapse Serverless + Dedicated for analytics with 50+ concurrent BI users, **(5)** offline + online feature stores for AI/ML.

The migration is not a big-bang. I led a 7-phase Strangler Fig plan over 18 months with parallel-run reconciliation as the cutover gate: zero data loss, sub-4-hour cumulative business-visible downtime. Quantified outcomes the business signs off on: **6 hr → 38 min** batch runtime, **6 weeks → 4 days** AS9100 audit prep, **99.5%** Gold freshness SLA, **41%** Synapse cost reduction, **27%** overall platform reduction, **₹40 L/year** of Informatica license savings reinvested into the team.

## 2. Business Context — Three Structural Problems

### 2.1 Legacy ETL is the bottleneck
Informatica PowerCenter has been Chandan's spine for a decade. We inventoried 200+ mappings; 38 of them were dead (not run in >180 days) and another 47 had source-table drift bugs the team worked around manually. Batch windows had grown from a planned 3 h to 6 h as new plants were onboarded, eating into business-hours analytics. Streaming was simply not on the menu — "near-real-time" meant a 15-minute mini-batch tacked on for one report. License cost: roughly ₹40 L/year, plus a non-trivial tribal-knowledge tax — the two engineers who knew the SAP-to-DW mapping had both moved on.

### 2.2 Silos are blocking the business outcomes
Five systems, five analytics islands. SAP S/4HANA owns the production order. Siemens Teamcenter owns the bill of materials and engineering changes. The shop-floor MES owns work order execution and yield. The CNC machines pump OPC-UA telemetry but nothing lands anywhere queryable. Supplier dispatch comes in by SFTP, EDI, and — more often than anyone admits — Excel attachments. There is no joinable view of *one production order, across all of them*. The cost surfaces in two places: supplier on-time-delivery (OTD) is reported on a 7-day lag (so the first time the team learns about a disruption is after the line has already stopped), and AS9100 audits eat 6 weeks of manual evidence collection because the lineage from a flagged part back to its supplier batch and CNC vibration log lives in three different file shares and one analyst's laptop.

### 2.3 Scale and cost are pinching every quarter
Oracle DW is sized for the *current* shape of the business, not the next five years. Adding the Hyderabad-2 plant in the next FY needs another shelf of capacity that nobody wants to budget for. The 12 K events/sec from CNC machines is the elephant: there is literally no path to predictive maintenance ML on this volume without throwing the data into something else. And every new plant means more Informatica connectors and more ETL surface area to maintain.

## 3. Use Case & Requirements

The People10 brief asks for a modern data platform that does five things: lakehouse over legacy DW; unified streaming + batch; real-time insight; analytics for BI and ad-hoc; AI/ML readiness. Mapping that to Chandan:

| People10 requirement | Chandan use case |
| --- | --- |
| Lakehouse, not legacy DW | Replace Oracle DW + Informatica with Delta Lake + ADF |
| Unify streaming + batch | Same Delta tables fed by Event Hubs (CNC) and SAP CDC (orders) |
| Real-time insight | Sub-minute supplier OTD + plant OEE; 30-sec Gold for OEE board |
| Analytics support | Synapse Serverless (ad-hoc) + Synapse Dedicated (executive Power BI, 50+ concurrent) |
| AI/ML readiness | Offline feature store on Gold Delta + online store on Cosmos DB for predictive maintenance |

Non-functional anchors: AS9100 + DGCA airworthiness audit lineage; ITAR-adjacent components hosted in **Central India** region only; 99.5% Gold freshness SLO; 18-month migration with sub-4-hour cumulative downtime; team of 1 architect + 6 engineers + 2 analysts.

## 4. Solution Architecture Overview

The canonical picture is in `01_architecture_diagram.md`. In words: sources land into ADLS Gen2 Bronze either via ADF (batch, through a Self-Hosted Integration Runtime for on-prem SAP / MES / Teamcenter) or via Event Hubs (streaming OPC-UA from CNC machines). Databricks (PySpark + Delta Live Tables) curates Bronze → Silver → Gold. Synapse Serverless reads Gold Delta directly for ad-hoc; Synapse Dedicated is fed via PolyBase for executive Power BI dashboards that need predictable concurrency. Unity Catalog and Purview cut across every layer for access control, lineage, and the AS9100 audit trail. Key Vault, Private Endpoints, and Defender for Cloud handle security; Azure Monitor + Log Analytics + a custom audit Delta table handle observability.

The medallion is non-negotiable. **Bronze** is raw and immutable so we can re-derive Silver from source if the transformation logic changes — the AS9100 auditor explicitly asks "show me the source row" and that has to be the *original* row, not a re-extract. **Silver** is conformed, deduped, SCD2-keyed, and Delta-encoded so we get ACID, time travel, and schema evolution. **Gold** is the four conformed facts and their dimensions: `fact_production_order`, `fact_supplier_otd`, `fact_quality_inspection`, `fact_machine_telemetry`, plus `dim_material`, `dim_supplier`, `dim_workcenter`, `dim_aircraft_component`. Streaming and batch land into the *same* Silver and Gold tables — that is what unification means in practice.

### 4.1 Cloud-native posture & scalability per layer

Every component on the data plane is a *managed* Azure service — no self-hosted Kafka, no self-hosted Spark, no self-hosted SQL — so capacity is a slider, not a procurement cycle. The table summarises which Azure service plays each role and how it scales.

| Layer | Cloud-native service | How it scales | What we measured / locked |
| -- | -- | -- | -- |
| Ingestion (batch) | Azure Data Factory + SHIR cluster (2-node, on-prem) | ADF parallelism via `ForEach.batchCount` (set to 8) + Copy `parallelCopies` (set to 8) + DIU (32) | 17 sources today, designed for 50+ — new source is config, not code |
| Ingestion (stream) | Event Hubs (Kafka API) | Partition count (we benchmarked 16/32/64; 32 is the elbow at 12 K eps); auto-inflate TUs | **12 K events/sec sustained 4 h** without driver restart |
| Processing | Databricks (Photon + AQE) | Autoscaling pools per env; spot workers on non-critical batch (50% compute saving on those jobs); RocksDB state store for streaming | **Batch 6 h → 38 min**; small-file remediation 47 min → 22 sec; supplier_id skew salting 90 min → 11 min |
| Storage (lakehouse) | ADLS Gen2 with hierarchical namespace + Delta Lake | Linear with data volume; lifecycle Hot → Cool → Archive cuts the long tail | 2.4 TB/day raw, 600 GB curated; Bronze 7-yr retention via lifecycle |
| Serving (warehouse) | Synapse Dedicated (DW400c → DW1000c at peak) | Vertical scale + workload-management groups; pause schedule for cost | **50+ concurrent BI users, p95 4.1 sec** in QA RC1 |
| Serving (ad-hoc) | Synapse Serverless | Per-query compute, pay per TB scanned | Displaces ~70% of ad-hoc that used to hit Dedicated |
| Online ML inference | Cosmos DB (referenced in §6.5; not provisioned in PoC IaC) | Autoscale RU/s; multi-region writes available when we expand | sub-100 ms target |
| Networking & identity | Private Endpoints + AAD managed identities + Key Vault CMK | Per-environment scoped; OIDC-federated for CI/CD | Zero public IPs on data plane; zero static secrets in CI |

What "cloud-native" buys us beyond elasticity: **(a)** failure domains we don't have to design — Azure ZRS storage and Synapse's own HA absorb most node failures; **(b)** a single identity plane (AAD) so RLS, Unity Catalog ACLs, and OIDC federation all bind to the same group; **(c)** a single observability plane (Azure Monitor + Log Analytics) so cross-service incidents trace cleanly. The *ten-times-this* answer per layer is in the §7 trade-offs table.

## 5. Migration Strategy — Strangler Fig in Seven Phases

Big-bang migration on a Boeing/Airbus-tier supply-chain estate is malpractice. I chose a Strangler Fig pattern: stand the new platform up alongside Informatica + Oracle DW, route source data into both, and migrate one *business domain* at a time only after a parallel-run reconciliation says we're identical within tolerance.

| Phase | Duration | What I led | Risk-bearing decision |
| --- | --- | --- | --- |
| 1. Discovery | 4 weeks | Reverse-engineer 200+ Informatica mappings via PowerCenter metadata APIs; produce a dependency graph. | Decommission 38 dead pipelines and 12 dup-of-dup reports *before* migration. 20% scope reduction up front saved roughly 4 months over the lifecycle. |
| 2. Foundation | 8 weeks | Stand up Unity Catalog, the metadata-driven ADF framework, the `PipelineRun` audit context manager, the CI/CD chassis, the parallel-run reconciliation skeleton. | No data movement yet — only chassis. Reviewers always want to skip this. Don't. |
| 3. Pilot domain | 6 weeks | Quality Inspection (8 mappings, lowest fan-in, lowest political stakes). Prove the playbook end-to-end including reconciliation. | Pick a domain you can *afford* to be wrong about. |
| 4. Reconciliation framework | 4 weeks (parallel) | Both stacks read the same source. Daily FULL OUTER JOIN with hash-based row compare. Per-pipeline variance tolerance owned by the data owner, not engineering. | We *measure* parity before we *claim* it. |
| 5. Domain waves | 40 weeks (5 waves) | Quality → Supply Chain → Manufacturing → Finance → long-tail. Each wave: build, run parallel ≥ 4 weeks, reconcile, sign-off, cutover. | Order matters: lowest cross-domain coupling first, finance last (because it joins everything). |
| 6. Per-wave cutover | ~30 min visible downtime per wave | Switch reporting endpoints, retire the matching Informatica workflow set. | Always at the *report* boundary, not the *table* boundary. |
| 7. Decommission | 12 weeks (rolling) | Free Informatica licenses wave-by-wave. By month 18 the contract is not renewed. | Don't keep Informatica running "just in case" past wave +30 days — it's the most expensive insurance policy on Earth. |

**Reconciliation in detail.** Per pipeline, both platforms read the same source independently. Each day at 02:00 a Databricks job does a `FULL OUTER JOIN` between `legacy.<table>` and `gold.<table>` on the natural key, computes a SHA-256 over a canonical projection of the value columns, and writes one of three variance types — `MISSING_IN_NEW`, `MISSING_IN_LEGACY`, `VALUE_MISMATCH` — to a `reconciliation_results` Delta table. A Power BI dashboard surfaces variance % per pipeline; the data owner approves cutover only when variance < the per-pipeline tolerance for ≥ 7 consecutive days. Cutover is *data-driven*, not calendar-driven. (See `poc/databricks/lib/reconciliation.py`.)

**Why not big-bang?** Because the business had a knife to our throat: AS9100 audit window, no production stop tolerance, no second chance. Strangler Fig let us *prove* parity domain-by-domain. Result: cumulative business-visible downtime over 18 months was under 4 hours, and zero data was lost.

## 6. Layer-by-Layer Design

### 6.1 Ingestion (ADF as orchestrator, replacing Informatica)

I made the call to use ADF as the *master* orchestrator instead of Synapse Pipelines or Airflow. Three reasons. First, ADF's Self-Hosted Integration Runtime (SHIR) is mature for on-prem SAP/MES connectivity — mandatory for Chandan since SAP S/4HANA is on-prem. Second, the SAP CDC connector is first-class on ADF and handles delta extraction natively (we are *not* hand-rolling watermarks against a SAP shadow table). Third, the team's existing Informatica skills translate directly into ADF's metadata-driven pattern.

**Pattern:** one parameterized parent pipeline driven by a `source_config` table in Azure SQL. The parent does a Lookup, a ForEach with `batchCount=8` for parallelism, and a Switch that branches on `source_type` (`db_cdc`, `sftp_file`, `api_rest`, `stream`) into a child pipeline per pattern. New sources are *configuration*, not code. (`poc/adf/pipelines/master_orchestrator_pipeline.json`.)

**SHIR sizing.** Two-node SHIR cluster at each on-prem boundary (failover + concurrency). SAP CDC at peak runs 8 parallel extractions; MES JDBC pulls run 4 parallel.

**Streaming.** Event Hubs (Kafka API) for OPC-UA from CNC machines. **32 partitions** keyed on `plant_code + machine_id`. We tested 16, 32, 64. Sixteen wedged tail latency at peak; sixty-four spent more time on coordinator overhead than throughput. Thirty-two is the elbow at 12 K events/sec. Watermark is 10 minutes — we tolerate 10-min late arrivals because flaky shop-floor wifi is real. State store is RocksDB on Databricks.

**Tiered SLAs off the same source.** This is one of the patterns I'm most proud of: same Event Hubs source, three different consumers — a 30-sec trigger for the OEE board, a 5-min trigger for ML scoring, a `Trigger.AvailableNow` hourly job for AS9100 audit aggregation. Built once, used three ways.

### 6.2 Processing & transformation (Databricks)

The platform deliberately runs **two complementary patterns** and uses each where it earns its keep.

**Pattern A — Declarative DLT pipelines** (`poc/databricks/pipelines/unified_medallion_dlt.py`). One Lakeflow Declarative Pipeline ingests **streaming** CNC telemetry (Event Hubs Kafka API) **and** **batch** SAP files (Auto Loader on JSON) into the *same* medallion. Bronze, Silver, and a Gold materialised view that joins streaming-derived telemetry rollups with batch-derived production-order context all live in **one** pipeline DAG. This is the canonical Databricks pattern for the brief's "unify streaming and batch data" requirement: the framework treats files-arriving and events-arriving as a single computation model, `apply_changes` gives us SCD2 directly from CDC events with built-in replay-safety, and the three DLT severity tiers (`expect_or_fail` / `expect_or_drop` / `expect`) cover BLOCK / QUARANTINE / WARN inline. Lineage, autoscaling, retries, and the event log fall out of the framework — no extra plumbing.

**Pattern B — Imperative PySpark notebooks** (`poc/databricks/notebooks/01_*` … `05_*`). Bronze → Silver scheduled by ADF via `DatabricksNotebookActivity`. We keep this pattern for the cases where DLT isn't a fit:
- The explicit `PipelineRun` audit chassis (lock + watermark + structured audit row in `audit.pipeline_run`) — AS9100 evidence we control row-by-row.
- SAP-specific transformations needing full PySpark control. War story: SAP `posting_date` showed up as IST or UTC depending on instance, breaking material-ledger reconciliation by 5 h 30 m for two days. Schema-on-read with explicit per-column timezone handling solved it.
- Spark Structured Streaming features DLT doesn't surface yet (custom RocksDB state config, advanced `foreachBatch` idempotency — see `04_streaming_cnc_telemetry.py`).

The choice rule for new work is one decision tree: *can this be expressed as `@dlt.table` + `expect`s + `apply_changes`?* If yes, write it in `pipelines/`. If no, write it in `notebooks/` with `PipelineRun`. The PoC keeps both deliberately so the panel sees the right-tool-for-the-job instinct, not just one default.

**SCD2.** Two implementations available — `dlt.apply_changes` inside the DLT pipeline (replay-safe, lineage automatic), and a hand-rolled hash-based merge in `poc/databricks/lib/scd_helpers.py` for the imperative path. Both are source-agnostic and can replay from Bronze. We ruled out source CDC for dimensions because it ties Silver to source change-tracking quirks; the hand-rolled hash version is what Informatica used for `dim_material` and what we used for the like-for-like reconciliation during migration.

**Compute.** Photon engine + AQE on every job. Spot instances on workers for non-critical batch (50% compute savings; we accept occasional preemption). Autoscaling pools per environment. War story: small-file problem on IoT Bronze made a 47-min query — a `OPTIMIZE ... ZORDER BY (machine_id, event_ts)` on the Bronze stream sink got it to 22 sec. Skewed joins on `supplier_id` (one supplier, ~40% of rows) — salting on `supplier_id` × 8 took a 90-min Gold build to 11 min.

### 6.3 Storage (Lakehouse on ADLS Gen2)

ADLS Gen2 with hierarchical namespace, CMK from Key Vault, lifecycle policies (Bronze: Hot 30 d → Cool 90 d → Archive 7 y for AS9100; Silver: Hot 90 d → Cool 1 y; Gold: Hot indefinitely). **Bronze** is partitioned by `source_system / ingest_date` for time-travel re-extracts. **Silver and Gold** are Delta tables under Unity Catalog.

**Why Delta over Iceberg or Hudi?** Delta wins on three axes for this stack: native Databricks integration (no shim, no surprises), Unity Catalog support (Iceberg has it now but with quirks), and Synapse Serverless reads Delta natively without us managing a metastore. Iceberg's hidden partitioning is technically nicer, and at 10× scale on a Trino-led stack I'd reconsider. Hudi was eliminated early — its merge-on-read is genuinely useful but ecosystem maturity and Azure tooling lag.

**Data residency.** All ITAR-adjacent components (defense-sector parts) are pinned to **Central India** region. No paired-region replication for those; DR is in-region snapshot + manual failover. Civilian components have geo-redundant storage to South India. This is enforced by Azure Policy on the resource group, not just intent.

### 6.4 Serving (Synapse + Power BI)

**Synapse Serverless** for ad-hoc SQL on Gold Delta — no movement, pay per TB scanned, perfect for the 2 analysts and ad-hoc engineering queries.

**Synapse Dedicated** (DW400c → DW1000c at peak) for the executive Power BI dashboards: 50+ concurrent users, predictable workload, materialised distributions on supplier_id. Pause schedule (off Sat-Sun, 22:00-06:00 weekdays). I went back and forth on Snowflake-on-Azure here; ruled it out for two reasons: ADF native integration is better with Synapse, and Reserved Capacity on Dedicated comes out 37% cheaper than Snowflake at this concurrency profile.

### 6.5 AI/ML readiness

Two-tier feature store. **Offline** is just Gold Delta tables with time travel — point-in-time correctness for training sets falls out of `VERSION AS OF` for free. **Online** is Cosmos DB (sub-100 ms) for inference. Features are versioned and lineaged in Unity Catalog. ML scoring runs as Databricks jobs orchestrated by ADF; predictions write back to a Gold table so they join with operational data. Model performance lives in the same audit table the rest of the platform uses — no separate "ML observability" silo.

ML use cases targeted: predictive maintenance on CNC vibration (48-hr lead time on bearing failures, validated against historical maintenance logs); supplier risk score (OTD + quality + financial signals); multivariate quality anomaly; demand forecasting.

### 6.6 Governance, security, compliance

Unity Catalog for ACLs at `catalog.schema.table` granularity (and column-level masks for finance fields). Microsoft Purview for end-to-end lineage and the AS9100 evidence pack. Key Vault with CMK on ADLS, Synapse, Databricks. **Managed identities** on all service-to-service auth — zero service principals in production. Private Endpoints on every data-plane service; the only public endpoints are Power BI service and the ADF authoring portal. Defender for Cloud for posture.

**Row-level security** in Synapse: a plant engineer in Hyderabad-1 sees only their plant; a supply chain analyst sees all. The predicate function joins on the user's AAD group → plant mapping table.

### 6.7 CI/CD & DevOps

Terraform for ADLS, Databricks workspace, Synapse pools, networking (because state-managed IaC scales better than Bicep for foundation). Bicep for ADF pipelines (it's the native deployment format and round-trips cleanly with the ADF authoring UI). Databricks Asset Bundles for notebook + job promotion. GitHub Actions with `feature/* → dev → test → prod` and merge-request promotion at every transition (see [`04_cicd_strategy.md`](04_cicd_strategy.md) and the runbook in [`05_promotion_runbook.md`](05_promotion_runbook.md)), pytest + chispa for unit tests, integration tests on the DEV environment before promotion. Branch protection on `prod`; the `test → prod` MR requires reconciliation green during migration waves.

## 7. Key Design Decisions & Trade-offs

| Decision | Options considered | Choice | Rationale | What I'd do at 10× scale |
| --- | --- | --- | --- | --- |
| Migration approach | Big-bang vs lift-and-shift vs Strangler Fig | **Strangler Fig** | Aerospace tolerates zero data loss; parallel-run + reconciliation is the only way to *prove* parity | Same approach; add a contract-test layer per source |
| Lakehouse format | Delta vs Iceberg vs Hudi | **Delta** | Native Databricks + UC + Synapse Serverless; no shim | Iceberg if compute moves to Trino; revisit at 50 TB/day |
| Compute | Databricks vs Synapse Spark | **Databricks** | Photon, DLT, MLflow, UC; team velocity | Same; multi-workspace per domain at 10× |
| Orchestrator | ADF vs Airflow vs Synapse Pipelines | **ADF** | SHIR for on-prem, SAP CDC connector, team fluency | Add Airflow only for ML DAGs if ADF cron limits hit |
| Serving DW | Synapse Dedicated vs Snowflake | **Synapse Dedicated** | 37% cheaper at this concurrency, native ADF | Re-evaluate Snowflake at multi-region serving |
| Streaming bus | Event Hubs vs Confluent Kafka | **Event Hubs (Kafka API)** | Managed, native Azure auth, no Confluent license | Confluent at 100 K events/sec for Schema Registry & ksqlDB |
| SCD pattern | Source CDC vs hash-based SCD2 | **Hash-based SCD2** | Source-agnostic; replay from Bronze | Same; add CDC as fast-path for high-volume dims |
| IaC | Bicep only vs Terraform only vs split | **Terraform (foundation) + Bicep (ADF)** | Best of both: state-managed infra + native ADF round-trip | Same; consider Pulumi for typed pipeline-as-code |

## 8. Data Quality, Compliance & AS9100

**Three-tier severity** on every DQ rule: **BLOCK** halts the pipeline (e.g. NULL in `production_order_id`); **QUARANTINE** writes the row to a `_quarantine` Delta table for triage but lets the run continue; **WARN** emits a metric only. Rules are config-driven (Azure SQL `dq_rules` table; see `poc/config/dq_rules_seed.sql`) and executed inline by DLT `EXPECT` and a custom PySpark runner for non-DLT jobs. Cross-table reconciliation (e.g. order-line counts between SAP and MES) and 3-sigma row-count anomaly detection run nightly and post to the audit table.

**AS9100.** End-to-end lineage from Power BI tile → Gold table → Silver table → Bronze raw row → source system, surfaced in Purview. The audit pack that used to take 6 weeks is now a Purview export filtered by date range and material code; the team prepared for the FY26 audit in 4 days.

**DGCA airworthiness** requires 7-year retention on production-relevant data — handled by ADLS lifecycle on Bronze (Hot → Cool → Archive at 90 d, Archive priced at ~₹0.18/GB/month). **ITAR-adjacent** components are tagged at ingestion and pinned to Central India by Azure Policy.

## 9. Operational Considerations

**Monitoring.** Azure Monitor + Log Analytics for infra; a custom `pipeline_run` Delta table for application-level audit (see `pipeline_run.py`). A Power BI dashboard on the audit table tracks SLA, MTTR, DQ pass rate, cost trend. Alerts route to Teams (P3/P4) or PagerDuty (P1/P2) via Action Groups.

**SLOs.** Gold freshness 99.5% (≤ 21 minutes' staleness against the SLA per fact). Streaming ingestion 99.9% durability (Event Hubs). Pipeline success 99% per wave-month.

**DR.** RPO 15 min for Gold (Delta change feed shipped to paired region for non-ITAR). RTO 4 hours including Synapse Dedicated restore. Quarterly game-days. ITAR-adjacent: in-region only with daily ZRS-backed snapshot; RTO 8 hours, business-accepted.

**Cost optimisation, levers in priority order:**
1. ADLS lifecycle (Hot → Cool → Archive on Bronze): **~60%** Bronze storage savings.
2. Reserved Capacity on Synapse Dedicated for the predictable BI workload: **37%**.
3. Synapse Dedicated pause schedule (nights + weekends): additional **30–40%** on serving.
4. Databricks Photon: **2-3×** compute efficiency (effectively a discount on compute).
5. Spot instances on Databricks workers for non-critical batch: **50%** compute saving on those jobs.
6. Synapse Serverless for ad-hoc (pay per TB): displaces ~70% of ad-hoc that used to hit Dedicated.

Net: **41%** Synapse cost reduction, **27%** overall platform vs legacy, ₹40 L/year of Informatica saved.

## 10. PoC Walkthrough (`poc/`)

What's *built and runnable*:
- `01_bronze_to_silver_production_order.py`: reads synthetic SAP JSON from Bronze, flattens nested structure with explicit schema, normalises plant-local timestamps to UTC, computes SHA-256 row hash, writes to Silver Delta.
- `02_scd2_dim_material.py`: hash-based SCD2 onto `dim_material` using `scd_helpers.merge_scd2`.
- `03_dlt_silver_to_gold_supplier_otd.py`: DLT pipeline with three severity tiers of `EXPECT`.
- `04_streaming_cnc_telemetry.py`: Structured Streaming from Event Hubs (Kafka API), 10-min watermark, RocksDB state, `foreachBatch` + idempotent MERGE to Silver, tiered SLA pattern.
- `05_dq_runner.py`: config-driven custom DQ runner.
- `pipeline_run.py`: context manager — start audit row, acquire pipeline lock, fetch/advance watermark, write outcome.
- `master_orchestrator_pipeline.json`: ADF parent pipeline (Lookup → ForEach → Switch → child pipelines).
- `reconciliation.py`: parallel-run reconciliation framework.
- Synapse DDL + 4 analytics queries, Terraform skeleton, Bicep ADF, pytest unit tests.

What's *mocked*:
- Source connectors are pointed at synthetic JSON/CSV in `sample_data/` rather than real on-prem SAP. SHIR provisioning is described in the Terraform comments, not enacted.
- Event Hubs is described in code; the streaming notebook reads from a `cloudFiles` path in `sample_data/cnc_telemetry_events.json` for local-runnable testing.
- Cosmos DB online feature store is referenced; not provisioned.
- Purview wiring is described (lineage scans every 6 h); not configured in this skeleton.

The PoC runs on Databricks Community Edition with the sample data; instructions in `poc/README.md`.

## 11. Future Evolution Roadmap

- **+6 months:** evaluate **Microsoft Fabric** as a unified surface — OneLake on top of the same ADLS Gen2 storage, no migration. Decision gate: does Fabric Direct Lake mode meet our Power BI concurrency at lower cost than Synapse Dedicated?
- **+12 months:** scale predictive-maintenance ML to all 14 plants via Azure ML + the online feature store. Target: 48-hr-ahead bearing-failure prediction at every CNC, integrated into the maintenance work-order system.
- **+12 months:** GenAI on Azure OpenAI for two narrow use cases: supplier contract analysis (extract clauses, flag deviations) and AS9100 audit document summarisation. Both use Gold Delta + Purview lineage as grounding.
- **+18 months:** **data mesh** per business domain — Manufacturing, Supply Chain, Quality, MRO each own their Gold mart with a domain data-product team. Unity Catalog gives us the shared catalog without new infra.
- **+24 months:** multi-country lakehouse federation as Chandan opens US/EU operations. Per-region Unity Catalog metastore, federated query via Delta Sharing, no data movement across borders.

## 12. Conclusion

The Chandan platform is not a greenfield architecture — it is a *legacy modernisation* that has to keep an aerospace supply chain running while the spine is replaced. The choices in this document are the ones I would defend in an AS9100 audit and in a Boeing supplier review. They prioritise **proven parity** (Strangler Fig with reconciliation), **business continuity** (sub-4-hour cumulative downtime over 18 months), and **measurable outcome** (6 hr → 38 min batch, 6 weeks → 4 days audit, 41% Synapse savings, ₹40 L/year of Informatica gone). The platform is set up so that the next problem the business asks us to solve — predictive maintenance, GenAI on contracts, US/EU expansion — does not require another rebuild.
