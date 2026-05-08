# Design Document — Cloud-Native Data Platform on Azure

**People10 Technologies.**
A modern lakehouse on Azure that unifies streaming and batch, supports analytics, and prepares data for AI/ML — mapped against the seven *Key Areas to Cover* from the brief.

---

## 1. Executive summary

The brief asks for an end-to-end data platform that replaces siloed legacy ETL with something that scales, runs both streaming and batch on the same engine, and lets the data be used for analytics *and* AI/ML without a second pipeline. I chose **Azure** because the brief allowed any cloud and Azure has the most mature single-vendor story for this stack: ADLS Gen2 for storage, Databricks for compute, Delta Lake as the open table format, Synapse as the serving layer, Event Hubs for streaming ingestion.

The architecture is a **medallion lakehouse** (Bronze → Silver → Gold) on Delta Lake. Streaming and batch sources both land in the *same* Bronze tables. From there, one set of Silver and Gold tables serves three consumers: real-time dashboards, ad-hoc + executive analytics, and the offline + online feature stores for ML.

I picked manufacturing as the use case (ERP + supplier files for batch, machine telemetry for streaming) because it produces realistic data flows — but the architecture is general. Locked-metric numbers like throughput and concurrency are illustrative targets, not measured production results.

## 2. Architecture overview

The diagram is in [`01_architecture_diagram.md`](01_architecture_diagram.md). In words:

- Streaming sources land via **Azure Event Hubs (Kafka API)**.
- Batch sources land via **Auto Loader** on file drops in ADLS Bronze. In production an orchestrator (Azure Data Factory, with SHIR for on-prem connectivity, or a Databricks Workflow) would copy upstream files into Bronze; in this PoC the DLT pipeline reads directly from ADLS so the unification claim is in one place.
- All sources write into ADLS Gen2 **Bronze** containers.
- **Databricks** (PySpark + Lakeflow Declarative Pipelines / DLT) curates Bronze → Silver → Gold.
- **Silver and Gold are Delta Lake** under Unity Catalog.
- **Synapse Serverless** reads Gold Delta directly for ad-hoc SQL.
- **Synapse Dedicated** is fed via PolyBase for executive Power BI dashboards.
- **Cosmos DB** materialises the online feature store from Gold for sub-100 ms ML inference.

Cross-cutting layers (governance, security, observability) are described in §7-8, not drawn in the diagram, to keep the picture readable.

## 3. Batch & streaming ingestion

### 3.1 Pattern — same medallion, two arrows in

The unification I care about is at the *table* layer: streaming events and batch files end up writing to the same Bronze table family. Downstream code reads "Bronze" without caring which arrow it came from. The DLT pipeline in `poc/databricks/pipelines/unified_medallion_dlt.py` shows this concretely:

- `bronze_cnc_telemetry` — Kafka source via `spark.readStream.format("kafka")`
- `bronze_sap_production_order` — file source via `spark.readStream.format("cloudFiles")` (Auto Loader)

Both use the same `@dlt.table` decorator. Auto Loader's incremental file processing is just a streaming source over file events.

### 3.2 Choices

- **Event Hubs Kafka API over Confluent.** Managed by Azure, integrates natively with AAD, no additional vendor. Confluent is better at huge scale (>100K eps) for its Schema Registry and ksqlDB, but for this PoC the trade-off doesn't pay off.
- **ADF as orchestrator over Airflow.** ADF has a first-class SAP CDC connector and Self-Hosted Integration Runtime for on-prem sources, both useful for legacy migration scenarios. Airflow we'd self-host.
- **Auto Loader over manual `spark.read.json`.** Schema evolution + incremental file detection are first-class. The `cloudFiles.schemaEvolutionMode = "addNewColumns"` mode handles real-world supplier-side schema drift without breaking the pipeline.

## 4. Data processing & transformation

The PoC uses **two patterns**. Each one suits different work.

### 4.1 Pattern A — Declarative pipelines (DLT)

**File:** `poc/databricks/pipelines/unified_medallion_dlt.py`.

One pipeline does the whole flow:

- Ingests **streaming** (Event Hubs) and **batch** (Auto Loader) into Bronze.
- Applies inline data-quality checks at three severity tiers:
  - `expect_or_fail` — halt the pipeline.
  - `expect_or_drop` — quarantine the row, keep going.
  - `expect` — emit a metric, no other effect.
- Maintains the SCD2 dimension via `apply_changes`.
- Produces a Gold materialised view that joins the streaming rollup with the batch dimension.

Why DLT here: lineage, autoscaling, retries, and the event log all come from the framework. Less plumbing to write and maintain.

### 4.2 Pattern B — Imperative notebooks (PySpark)

**Files:** `poc/databricks/notebooks/01_*.py`, `02_*.py`, `04_*.py`.

Each notebook is wrapped in a `PipelineRun` audit chassis. That gives me three things on every run:

- A pipeline lock (no double-runs from ADF retries).
- A watermark for incremental ingestion.
- A structured row in `audit.pipeline_run` — what an auditor reads when something goes wrong.

I use this pattern where DLT can't comfortably express the work. The clearest example is the SAP timezone case in `01_bronze_to_silver_production_order.py`:

- SAP sends `posting_date` as a naive timestamp string (no timezone).
- A separate `plant_timezone` column says which zone to interpret it in.
- The code calls `to_utc_timestamp(col, tz)` per row.

Column-driven, source-specific transforms like this are awkward in DLT but natural in plain PySpark.

### 4.3 Which one to use

> **Decision rule.** If the work can be expressed as `@dlt.table` + `expect`s + `apply_changes`, put it in `pipelines/`. Otherwise put it in `notebooks/` with the `PipelineRun` chassis.

For this take-home I deliberately kept both, to show the judgment call. In production I'd probably consolidate to DLT once the team is comfortable with it — that's an open question called out in `TODO.md`.

### 4.4 SCD2 — two implementations

Both are source-agnostic (they don't depend on source-side CDC), and both can replay from Bronze.

| Implementation | Where | When to use |
| -- | -- | -- |
| `dlt.apply_changes` | DLT pipeline | Default for new work in DLT — replay-safe, lineage automatic |
| Hash-based merge (`scd_helpers.merge_scd2`) | `poc/databricks/lib/scd_helpers.py` | Inside imperative notebooks. SHA-256 over a sorted projection of attributes; expire-and-insert on hash mismatch |

## 5. Storage architecture

**Lakehouse on ADLS Gen2 with Delta Lake.** Three layers:

- **Bronze** — raw and immutable, partitioned by `source_system / ingest_date`. Partitioned for efficient time-travel re-extracts when a transformation bug needs replay. Lifecycle: Hot 30d → Cool 90d → Archive (long-tail retention for compliance use cases).
- **Silver** — conformed, deduped, SCD2-keyed Delta tables. ACID concurrent writes, time travel for audit replay, schema evolution.
- **Gold** — business facts and dimensions. Read by Synapse Serverless directly; Synapse Dedicated load is via PolyBase staging.

**Why Delta Lake over Iceberg or Hudi:**

- Native Databricks integration, no shim.
- Unity Catalog support is first-class.
- Synapse Serverless reads Delta natively — no external metastore.
- Open format — can move to Iceberg later if a Trino-led stack emerges.

At 10× this scale on a multi-engine stack, I'd reconsider — Iceberg's hidden partitioning is technically nicer. For this PoC and team velocity, Delta is the right call.

## 6. Cloud-native services & scalability

Every component on the data plane is a *managed* service. No self-hosted Kafka, no self-hosted Spark, no self-hosted SQL. Capacity is a config slider.

| Layer | Service | Scale handle | Reason |
| -- | -- | -- | -- |
| Streaming ingest | Event Hubs (Kafka API) | Partition count + Throughput Units | Managed, auto-inflate available |
| Batch ingest | Auto Loader (ADF or Databricks Workflows for orchestration) | `ForEach` parallelism + per-file streaming | SHIR available for on-prem connectivity |
| Compute | Databricks (Photon + AQE) | Autoscaling pools, spot workers for non-critical | Photon ≈ 2-3× efficiency; spot saves ~50% on batch |
| Storage | ADLS Gen2 + Delta | Linear; lifecycle for cost | Hierarchical NS gives directory-level ACLs |
| Serving (warehouse) | Synapse Dedicated | DWU scale-up; pause schedule | Workload management groups for concurrency |
| Serving (ad-hoc) | Synapse Serverless | Per-query, pay-per-TB | Displaces ad-hoc that would otherwise hit Dedicated |
| Online ML | Cosmos DB (referenced) | Autoscale RU/s | Sub-100 ms reads at any scale |

Beyond elasticity, "cloud-native" here also means: a single AAD identity plane (so RLS, UC ACLs, and OIDC federation bind to the same group), and a single observability plane (Azure Monitor + Log Analytics) so cross-service incidents trace cleanly.

## 7. Data quality, governance & security

**Data quality** — three severity tiers used consistently:

- `BLOCK` — pipeline halts. Used for primary-key NULL checks. In DLT this is `expect_or_fail`.
- `QUARANTINE` — row diverted to a quarantine table; pipeline continues. In DLT this is `expect_or_drop`. Useful for "this row is suspicious but we don't want to halt the world".
- `WARN` — metric only. In DLT this is `expect`. Used for known-noisy checks.

The DLT pipeline shows all three in action.

**Governance:**

- **Unity Catalog** for fine-grained access (`catalog.schema.table` ACLs + column-level masks for sensitive fields).
- **Microsoft Purview** for lineage and a business glossary. Lineage scans every 6 hours. Pattern referenced in design; scan configuration not in IaC for this PoC.

**Security:**

- **Azure Key Vault** with customer-managed keys for ADLS encryption.
- **Managed identities** for service-to-service auth — no service principals in the Terraform.
- **Private Endpoints** on every data-plane service in production (skeleton in `main.tf`; full networking module deferred for time).
- **Microsoft Defender for Cloud** for posture management.
- **Row-level security** in Synapse for tenant scoping (e.g. plant engineers see only their plant).

## 8. CI/CD, monitoring & cost

### 8.1 CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml` runs on PR and push to `dev`. What it does today (matches the file):

- Lint Python — `ruff check`, `ruff format --check`, `mypy --strict` on the production library.
- Unit tests — `pytest` + `chispa`, coverage gate ≥ 80% on `poc/databricks/lib/`.
- IaC validation — `terraform fmt` + `terraform validate`.
- Security scan — `gitleaks` on the full diff.

What I'd add for production but didn't build for this take-home:

- CD workflows per environment (Databricks bundle deploy, Synapse DDL apply, Terraform apply).
- OIDC federation to Azure — no static client secrets in repo or org settings.
- Reviewer-protected GitHub Environments for `dev` / `test` / `prod` with branch-protection rules.
- Heavier IaC scanning (`tflint`, `checkov`, `tfsec`) and `actions/dependency-review` on PRs.
- `yamllint` and `sqlfluff` on the YAML and SQL.

The CI workflow is the meaningful artefact for a 3-day PoC; the CD shape is described above instead of all written.

### 8.2 Monitoring

- **Azure Monitor + Log Analytics** for service-level metrics and alerts.
- A custom `audit.pipeline_run` Delta table written by the `PipelineRun` chassis for application-level audit (run_id, status, watermark, metrics_json). This is what drives the SLO dashboards and what an auditor would query for the change record.
- Action Groups route alerts to Teams (low severity) or PagerDuty (high severity).

### 8.3 Cost optimisation

In priority order of impact:

1. **ADLS lifecycle** (Hot → Cool → Archive on Bronze) — significant storage savings on the long tail.
2. **Synapse Dedicated pause schedule** — pause overnight and weekends.
3. **Databricks Photon** — ~2-3× compute efficiency; effectively a discount.
4. **Spot workers** on non-critical batch — ~50% savings on those jobs (we accept occasional preemption).
5. **Synapse Serverless** for ad-hoc — pay per TB scanned, displaces a class of workloads that would otherwise sit on Dedicated.

## 9. Trade-offs

| Decision | Options considered | Choice | Rationale | At 10× this scale |
| -- | -- | -- | -- | -- |
| Lakehouse format | Delta vs Iceberg vs Hudi | **Delta** | Native Databricks + UC + Synapse Serverless reads it directly | Iceberg if compute moves to Trino |
| Compute | Databricks vs Synapse Spark | **Databricks** | Photon, DLT, MLflow, UC; team velocity | Same; multi-workspace per domain |
| Orchestrator | ADF vs Airflow vs Synapse Pipelines | **ADF** | SAP CDC, SHIR for on-prem | Airflow only for ML DAGs if ADF cron limits hit |
| Serving DW | Synapse Dedicated vs Snowflake-on-Azure | **Synapse Dedicated** | Reserved Capacity is cheaper at this concurrency; ADF native | Re-evaluate Snowflake at multi-region serving |
| Streaming bus | Event Hubs vs Confluent Kafka | **Event Hubs** | Managed, AAD-native, no extra vendor | Confluent at >100K eps for Schema Registry |
| Dual processing pattern | DLT only vs imperative only vs both | **Both, deliberately** | Shows pattern-choice judgment | Probably consolidate to DLT in production |

## 10. Future evolution

- **+6 months** — Evaluate Microsoft Fabric / OneLake. Same ADLS storage, no migration. Decision gate is whether Direct Lake mode meets concurrency at lower cost than Synapse Dedicated.
- **+12 months** — Predictive maintenance ML in production via Azure ML + the online feature store. Add a model registry and serving endpoints.
- **+12 months** — GenAI on Azure OpenAI for two narrow uses: contract analysis and audit-document summarisation. Both grounded on Gold Delta + Purview lineage as the source of truth.
- **+18 months** — Domain-led data ownership (data mesh) once the platform is stable. Unity Catalog already supports this without new infra.
- **+24 months** — Multi-region federation if the business expands geographically. Per-region UC metastore + Delta Sharing across regions.

## 11. Honest scope of this PoC

What's **working code** in this repo (read it, run it):

- Architecture diagram (`docs/01_*`).
- This design doc.
- The DLT pipeline (`poc/databricks/pipelines/unified_medallion_dlt.py`).
- Three imperative notebooks (Bronze→Silver SAP, SCD2, streaming CNC).
- Reusable library (`PipelineRun`, `scd_helpers`, `reconciliation`, `format_readers`).
- Terraform skeleton (`main.tf`) — RG, KV, ADLS, Databricks workspace, Log Analytics. Networking + Synapse + Cosmos are deferred.
- Synapse DDL for two facts (production order, supplier OTD) + two analytics queries.
- Pytest unit tests with coverage gate.
- GitHub Actions CI workflow.

What's **described, not provisioned**:

- Cosmos DB online feature store.
- Full networking (VNet, subnets, Private Endpoints).
- Synapse workspace + Dedicated pool — DDL is written; no pool in the take-home env.
- Microsoft Purview scan configuration.
- The CD half of CI/CD (ADF push, Databricks bundle deploy, Synapse DDL apply per env).

What I'd build next (with rough effort) is in `TODO.md`. The most important item there: actually running the streaming notebook against a real Event Hubs at the target throughput, rather than extrapolating from a smaller test.
