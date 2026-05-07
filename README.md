The People10 Solutions Lab — three days of work to design and prototype a modern lakehouse on Azure that unifies streaming and batch, supports analytics, and gets data ready for AI/ML.

The brief is generic ("a modern data platform"), so I picked manufacturing as the use case because it gave me realistic streaming + batch flows to demonstrate. The architecture choices, trade-offs, and trade-off rationale are all mine to defend.
---

## How I spent the 3 days

A quick honest log so a reviewer can see where the time actually went. Not a project plan — just what I worked on.

- **Day 1 (~6 hrs).** Read the brief twice. Settled on Azure within the first hour because the brief allowed any cloud and I know it best. Sketched the medallion architecture and drafted the design doc skeleton. Most of the time went into reasoning out the medallion + Delta Lake choice and the trade-off table. Picked manufacturing as the use case so streaming + batch flows would be concrete.
- **Day 2 (~7 hrs).** Built the runnable pieces. The DLT pipeline took the longest — getting `apply_changes` and the streaming + batch unification right in one DAG was the part that needed the most care. Wrote the imperative notebooks with the `PipelineRun` audit chassis. Got bitten by SAP timezone normalisation; explicit `to_utc_timestamp(col, tz)` per row fixed it. Wrote the unit tests at the end of the day.
- **Day 3 (~5 hrs).** Polish. Mermaid architecture diagram, Synapse DDL + analytics queries, CI workflow with the right shape, the TODO. Then a thorough QA pass that surfaced a YAML syntax bug and a handful of stale cross-references after I'd trimmed earlier drafts.

Roughly **18 hours of focused work over 3 days**. Big chunks not done are listed in [`TODO.md`](TODO.md).

## How to read this

1. **[`docs/01_architecture_diagram.md`](docs/01_architecture_diagram.md)** — one diagram, 1 minute.
2. **[`docs/02_design_document.md`](docs/02_design_document.md)** — design covering the brief's 7 key areas, ~10 minutes.
3. **[`poc/databricks/pipelines/unified_medallion_dlt.py`](poc/databricks/pipelines/unified_medallion_dlt.py)** — the central demo, ~5 minutes. One DLT pipeline ingests **streaming** (Event Hubs) **and** **batch** (Auto Loader) into the same medallion. This is the unification claim made literal.
4. **[`TODO.md`](TODO.md)** — what I'd do next if I had more time, and what I'm uncertain about.

## WHat is the ask, and where it's covered

| Key Areas to Cover | Where in this repo |
| -- | -- |
| Batch & streaming ingestion | Design doc §3 · DLT pipeline `unified_medallion_dlt.py` · Streaming notebook `04_streaming_cnc_telemetry.py` |
| Data processing & transformation | Design doc §4 · 3 notebooks under `poc/databricks/notebooks/` · Reusable lib in `poc/databricks/lib/` |
| Storage architecture | Design doc §5 · Terraform `main.tf` · Synapse DDL under `poc/synapse/ddl/` |
| Cloud-native services & scalability | Design doc §6 |
| Data quality, governance & security | Design doc §7 · DLT expectations inline in the pipeline |
| CI/CD, monitoring & cost optimization | Design doc §8 · `.github/workflows/ci.yml` · `Makefile` |
| Trade-offs & future evolution | Design doc §9 + §10 |

## Repo layout

```
people10_usecase/
├── README.md                   # this file (single source of truth)
├── TODO.md                     # what's next + things I'm uncertain about
├── Makefile                    # make test / lint / smoke / ci-local
├── databricks.yml              # Databricks Asset Bundle
├── .env.example                # local dev env-var template
├── docs/
│   ├── 01_architecture_diagram.md
│   ├── 02_design_document.md
│   └── 03_presentation_deck_outline.md
├── poc/
│   ├── databricks/
│   │   ├── pipelines/          # DLT — unified streaming + batch
│   │   │   └── unified_medallion_dlt.py
│   │   ├── notebooks/          # imperative PySpark with PipelineRun audit chassis
│   │   │   ├── 01_bronze_to_silver_production_order.py
│   │   │   ├── 02_scd2_dim_material.py
│   │   │   └── 04_streaming_cnc_telemetry.py
│   │   └── lib/                # reusable: PipelineRun, SCD2, recon, readers
│   ├── synapse/
│   │   ├── ddl/                # fact_production_order, fact_supplier_otd
│   │   └── analytics/          # supplier_otd_trend, top_suppliers_by_plant
│   ├── infrastructure/terraform/   # one self-contained main.tf
│   ├── tests/                  # pytest + chispa unit tests
│   ├── sample_data/            # synthetic JSON / CSV
│   └── config/                 # source_config seed
└── .github/workflows/ci.yml    # PR validation
```

## Running it locally

### Unit tests + lint

```bash
make test         # pytest + chispa with coverage gate (≥ 80% on poc/databricks/lib)
make lint         # ruff check + format-check + mypy --strict + sqlfluff
make ci-local     # everything CI runs, locally
```

Or without `make`:

```bash
pip install "pyspark==3.5.*" "delta-spark==3.2.*" "pytest==8.*" "pytest-cov==5.*" "chispa==0.10.*"
PYTHONPATH=poc pytest poc/tests/ -v --cov=poc/databricks/lib --cov-fail-under=80
```

### Notebooks on Databricks Community Edition

The fastest way to walk the notebook code end-to-end without standing up cloud infra.

1. Create a free Community Edition workspace at https://community.cloud.databricks.com.
2. Import this repo as a *Repo* in the workspace.
3. Upload the three sample-data files to `dbfs:/FileStore/people10/`:
   - `poc/sample_data/sap_production_orders.json`
   - `poc/sample_data/supplier_dispatch.csv`
   - `poc/sample_data/cnc_telemetry_events.json`
4. In `01_bronze_to_silver_production_order.py` and `04_streaming_cnc_telemetry.py`, change the Bronze path from `abfss://…` to `dbfs:/FileStore/people10/…`.
5. Bootstrap the audit tables (one-time):

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

6. Run the notebooks in order: `01` → `02` → `04`. Optionally deploy the DLT pipeline via `databricks bundle deploy --target dev` after pointing `databricks.yml` at your CE workspace.

## What runs vs what doesn't

The line between "I built it" and "I designed it" matters, so I'm being explicit.

**Runs end-to-end:** the three notebooks under `poc/databricks/notebooks/` against the sample data on Databricks Community Edition; the unified DLT pipeline once the bundle is deployed; the `pytest` suite with ≥ 80% coverage on the production library; CI on every PR.

**Designed but not provisioned:** the Synapse Dedicated pool (DDL is ready, no pool in the take-home env to apply against), the Cosmos DB online feature store (pattern in design doc §6, IaC not written), Microsoft Purview lineage scans (referenced, not wired), the rest of the Terraform networking + Synapse + monitoring modules (the foundation is in `main.tf` — each missing module would be ~50 lines).

[`TODO.md`](TODO.md) is the honest "what's next" — read it alongside this README. I'd rather flag a gap than smooth over it.

## Things I'd like to talk about in the review

The most interesting question, in my opinion, is **why I kept *both* a DLT pipeline and imperative PySpark notebooks** when DLT can do most of what the notebooks do. The answer is in design doc §4. I'd genuinely like a second opinion on whether to retire the imperative notebooks in production, or keep both as a deliberate dual-pattern.
