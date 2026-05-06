# `pipelines/` — Declarative DLT pipelines

Lakeflow Declarative Pipelines (Delta Live Tables). Deployed as Databricks Asset Bundle resources of `kind: pipeline` via `databricks bundle deploy`.

## When to put code here vs in `../notebooks/`

| Use a DLT pipeline (here) when… | Use an imperative notebook (`../notebooks/`) when… |
| -- | -- |
| Streaming and batch in *one* DAG, both feeding the same medallion | You need the explicit `PipelineRun` audit chassis (lock + watermark + audit row) |
| SCD2 via `apply_changes` is enough (replay-safe, lineage automatic) | You need full PySpark control beyond what DLT exposes |
| Inline DQ via `expect_or_fail` / `expect_or_drop` / `expect` | Source-specific transformations (e.g. SAP timezone normalisation) |

The PoC keeps both patterns deliberately to show pattern-choice judgment. In production I'd consolidate to DLT once the team has internalised the framework.

## Files

- `unified_medallion_dlt.py` — One pipeline that ingests **streaming** (Event Hubs) and **batch** (Auto Loader on SAP files) into the same medallion. Three DLT severity tiers + SCD2 via `apply_changes`. Gold materialised view joins streaming-derived rollups with batch-derived dimensions.

## Deploy

```bash
databricks bundle deploy --target dev
databricks bundle run unified_medallion --target dev
```
