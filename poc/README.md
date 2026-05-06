# PoC — how to read and run it

The runnable subset of the design. Three Databricks notebooks, one DLT pipeline, a Synapse DDL pair plus two analytics queries, a Terraform skeleton, pytest tests, and synthetic sample data.

The point isn't to be exhaustive — it's to show that the design in `../docs/02_design_document.md` actually runs, with the awkward bits (SAP timezone normalisation, hash-based SCD2, idempotent streaming MERGE) handled in a way I'd defend in production.

---

## Layout

```
poc/
├── databricks/
│   ├── pipelines/              # DLT — unified streaming + batch (the central demo)
│   │   ├── unified_medallion_dlt.py
│   │   └── README.md
│   ├── notebooks/              # imperative PySpark with PipelineRun audit chassis
│   │   ├── 01_bronze_to_silver_production_order.py
│   │   ├── 02_scd2_dim_material.py
│   │   └── 04_streaming_cnc_telemetry.py
│   └── lib/                    # PipelineRun, SCD helpers, reader factory, recon
├── synapse/
│   ├── ddl/                    # fact_production_order, fact_supplier_otd
│   └── analytics/              # supplier_otd_trend, top_suppliers_by_plant
├── infrastructure/terraform/   # one self-contained main.tf
├── tests/                      # pytest + chispa
├── sample_data/                # synthetic JSON / CSV for local runs
└── config/                     # source_config seed
```

## Run locally on Databricks Community Edition

The fastest way to walk the notebook code end-to-end without standing up cloud infra.

1. **Create a free Community Edition workspace** at https://community.cloud.databricks.com.
2. **Import this repo** as a Repo in the workspace.
3. **Upload sample data** to `dbfs:/FileStore/people10/`:
   - `sample_data/sap_production_orders.json`
   - `sample_data/supplier_dispatch.csv`
   - `sample_data/cnc_telemetry_events.json`
4. **Update the Bronze paths** in `01_bronze_to_silver_production_order.py` and `04_streaming_cnc_telemetry.py` from `abfss://...` to `dbfs:/FileStore/people10/...`.
5. **Bootstrap the audit tables** (one-time):
   ```sql
   CREATE DATABASE IF NOT EXISTS audit;
   CREATE TABLE IF NOT EXISTS audit.pipeline_run
       (run_id STRING, pipeline_name STRING, source_system STRING, entity STRING,
        status STRING, started_at TIMESTAMP, ended_at TIMESTAMP,
        metrics_json STRING, error_text STRING, host STRING) USING DELTA;
   CREATE TABLE IF NOT EXISTS audit.pipeline_lock
       (pipeline_name STRING, run_id STRING, host STRING, acquired_at TIMESTAMP) USING DELTA;
   CREATE TABLE IF NOT EXISTS audit.pipeline_watermark
       (source_system STRING, entity STRING, watermark_value STRING, updated_at TIMESTAMP) USING DELTA;
   ```
6. **Run the notebooks**: `01` → `02` → `04`. Optionally deploy and run the DLT pipeline via `databricks bundle deploy --target dev` after pointing `databricks.yml` at your CE workspace.

## Run unit tests locally

```bash
make test
```

Or directly:

```bash
pip install pyspark==3.5.* delta-spark==3.2.* pytest==8.* pytest-cov==5.* chispa==0.10.*
PYTHONPATH=poc pytest poc/tests/ -v --cov=poc/databricks/lib --cov-fail-under=80
```

## What runs vs what doesn't

**Runs locally on Community Edition with the sample data:**
- Notebooks 01, 02, 04 in `notebooks/`
- All unit tests under `tests/`

**Runs in a Databricks workspace with the bundle deployed:**
- DLT pipeline `pipelines/unified_medallion_dlt.py` (needs Event Hubs + ADLS endpoints set in `databricks.yml`)
- The smoke job and daily-orchestrator job declared in `databricks.yml`

**Designed but not runnable in the take-home environment:**
- Synapse DDL — the SQL is written; there's no Synapse pool to apply it against
- Terraform `main.tf` — the plan is valid; the apply needs a real Azure subscription with the right RBAC
- Cosmos DB online feature store — referenced in design, no IaC

The honest "what's next" is in `../TODO.md`.
