# PoC — Chandan Aerospace Lakehouse

This directory holds a **runnable** proof-of-concept for the design described in `../docs/02_design_document.md`. It is deliberately scoped down from the full production estate so that a reviewer can clone, run, and read the result in well under an hour. Anything that has been simplified for the take-home is called out below — I'd rather show what runs than claim what's hypothetical.

## Layout

```
poc/
├── databricks/
│   ├── notebooks/              # 5 notebooks: B→S, SCD2, DLT, Streaming, DQ
│   └── lib/                    # PipelineRun, SCD helpers, reader factory, recon
├── adf/                        # ADF master orchestrator + child pipelines + LS/datasets/triggers
├── synapse/                    # DDL for fact/dim + 4 analytics queries + curated views
├── infrastructure/             # Terraform (foundation) + Bicep (ADF)
├── tests/                      # pytest + chispa unit tests
├── sample_data/                # synthetic SAP / supplier / CNC inputs
└── config/                     # source_config, dq_rules, reconciliation tolerance
```

## How to run locally (Databricks Community Edition)

This is the fastest way to walk the notebook code end-to-end without spinning up cloud infrastructure.

1. **Create a Community Edition workspace** at https://community.cloud.databricks.com (free, 15 GB cluster).
2. **Import the repo**: `Repos` → `Add Repo` → paste the GitHub URL of this codebase. The notebooks reference `/Workspace/Repos/people10_usecase/poc/databricks/lib`; if you import to a different path, edit the `sys.path.append` lines in each notebook.
3. **Upload sample data** to `dbfs:/FileStore/people10/`:
   * `sample_data/sap_production_orders.json`
   * `sample_data/supplier_dispatch.csv`
   * `sample_data/cnc_telemetry_events.json`
4. **Adjust the Bronze paths** in `01_bronze_to_silver_production_order.py` and `04_streaming_cnc_telemetry.py` from `abfss://...` to `dbfs:/FileStore/people10/...` for the local run.
5. **Bootstrap audit tables** (one-time):
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
6. **Run the notebooks in order**: 01 → 02 → 03 → 04. The DQ runner (05) is invoked from inside 01 in production; here you can run it standalone after 01 to see the BLOCK / QUARANTINE / WARN flow.

## Azure provisioning (production path)

For the cloud-side deployment, the chassis is in `infrastructure/`:

1. **Backend bootstrap** — create a storage account + container for Terraform state in your subscription. Skipping the steps for brevity since they vary per organisation.
2. **Foundation (Terraform)**:
   ```bash
   cd infrastructure/terraform
   terraform init -backend-config=backend.${ENV}.hcl
   terraform plan -var environment=${ENV} -out=tf.plan
   terraform apply tf.plan
   ```
   This stands up: Resource Group, Key Vault (CMK), VNet + subnets + NSGs, ADLS Gen2 with hierarchical namespace and CMK and lifecycle policies, Databricks workspace + Unity Catalog metastore + instance pools, Synapse workspace + Dedicated pool, Log Analytics + Action Groups, Private Endpoints for ADLS and Key Vault.
3. **ADF (Bicep)**:
   ```bash
   az deployment group create \
     --resource-group rg-chandan-${ENV} \
     --template-file infrastructure/bicep/adf_pipeline.bicep \
     --parameters environment=${ENV} ...
   ```
4. **ADF artefacts** — linked services, datasets, pipelines, triggers under `adf/` are deployed via `az datafactory` CLI from a CI step. (The JSON files round-trip with the ADF Studio UI for ongoing authoring.)
5. **Control plane seed** — apply `config/source_config_seed.sql` and `config/dq_rules_seed.sql` against the Azure SQL control DB.

## Assumptions

* **One region** (Central India) for the take-home. Production has paired-region for non-ITAR; ITAR-adjacent stays in-region with daily ZRS-backed snapshot.
* **No real SAP / MES / Teamcenter connectivity** — connectors and SHIR config are described in the linked services and Bicep but not stood up.
* **Synthetic sample data** is a few rows per source — enough to exercise schema, hashing, and SCD logic. The streaming notebook reads a 10-event JSON file via Auto Loader for local tests; in production it reads Event Hubs at 12K events/sec.
* **Unity Catalog** is referenced in code (catalog/schema/table 3-part naming) but not exhaustively bootstrapped — that is a Phase-2 ops step.
* **Cosmos DB online feature store** is described in the design doc but not provisioned in Terraform here.

## What's mocked vs production-ready

| Component                        | Status              | Notes |
| -------------------------------- | ------------------- | ----- |
| `pipeline_run.py` audit chassis  | Production-ready    | Same code as production with audit/lock/watermark; CE just needs the audit tables created. |
| `scd_helpers.merge_scd2`         | Production-ready    | Two-pass MERGE inside one Delta optimistic-concurrency window. |
| `reconciliation.py`              | Production-ready    | Hash-based FULL OUTER JOIN, three variance types, tolerance-driven cutover gate. |
| Bronze→Silver SAP notebook       | Production-ready    | Explicit schema, UTC normalisation, hash, MERGE on natural key. |
| DLT supplier OTD                 | Production-ready    | Three EXPECT tiers; runs as a DLT pipeline in workspace. |
| Streaming CNC telemetry          | Production-pattern  | Code is production-shape (RocksDB, watermark, foreachBatch + MERGE); for local dev, swap Event Hubs for `cloudFiles` on the sample JSON. |
| `dq_runner.py`                   | Production-ready    | Config-driven from `audit.dq_rules`; severity tiers wired to quarantine + metric tables. |
| ADF master orchestrator          | Production-shape    | Real metadata-driven structure; deploy via `az datafactory pipeline create`. |
| Terraform foundation             | Production-shape    | Skeleton with the right shape — CMK, PE, UC, NSGs — needs ENV-specific tfvars before apply. |
| Bicep ADF                        | Production-shape    | Owns the factory resource + diag settings; pipelines are JSON-deployed. |
| Synapse DDL                      | Production-ready    | HASH/REPLICATE distributions, columnstore, partition functions. |
| Synapse analytics queries        | Production-ready    | Covers the 4 stakeholder queries described in the brief. |
| Cosmos DB online feature store   | Documented only     | Provisioning omitted; design + access pattern in §6.5 of design doc. |
| Purview governance scans         | Documented only     | 6-hourly lineage scans configured in production; not wired here. |
| Defender for Cloud, Action Groups| Skeleton + alerts   | Action groups + one Synapse DWU alert; full alert library not enumerated. |

## Migration playbook — quick reference

The full plan is in §5 of the design doc. The on-call cheat sheet:

1. **Cutover gate:** `audit.reconciliation_results` → `within_tolerance = true` for **≥ 7 consecutive days** for the pipeline (or `≥ 14` for dimensions).
2. **Rollback:** ADF triggers for the cutover wave revert via Bicep redeploy of the previous template version. Reporting endpoints flip back via Power BI dataset connection swap. Total rollback budget: 30 min.
3. **Decommission:** Informatica workflow stays *suspended* (not deleted) for 30 days post-cutover. Folder + binary archive to glacier-tier blob. License is then released at the next renewal anniversary.

## Tests

```bash
cd poc
pip install pytest chispa pyspark==3.5.* delta-spark==3.2.0
pytest tests/ -v
```

The tests cover:
* `test_scd2_logic.py` — hash stability under column reorder, hash sensitivity to value changes, NULL vs empty-string distinction.
* `test_pipeline_run.py` — start/end audit rows, watermark commit only on success, exception re-raises.
* `test_reconciliation.py` — three variance types correctly classified, tolerance gate when zero variance.

## Contact

Questions on any layer (especially the migration / reconciliation framework — that's where I expect the deepest reviewer questions): I'm happy to walk it live in the review.
