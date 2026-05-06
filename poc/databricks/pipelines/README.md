# `pipelines/` — Declarative DLT pipelines

This directory holds **Lakeflow Declarative Pipelines** (Delta Live Tables). They are deployed as Databricks Asset Bundle resources of `kind: pipeline`, not jobs. The CD workflow `cd-databricks.yml` deploys them via `databricks bundle deploy`.

## When to put code here vs in `../notebooks/`

| Use a DLT pipeline (here) when… | Use an imperative notebook (`../notebooks/`) when… |
| -- | -- |
| You want streaming and batch in *one* DAG, both feeding the same medallion. | You need the explicit `PipelineRun` audit chassis (lock + watermark + audit row) for AS9100 evidence. |
| You want SCD2 via `apply_changes` (replay-safe, idempotent, lineage automatic). | You need full PySpark control beyond what DLT exposes (custom state stores, advanced foreachBatch idempotency, complex SAP-specific transformations). |
| You want inline DQ via `expect_or_fail` / `expect_or_drop` / `expect`. | You're inside an ADF-orchestrated batch where ADF must own the schedule and lifecycle. |
| You want autoscale, retries, observability, and lineage out of the framework. | You need to swap the runtime (e.g., temporarily run on a job cluster vs serverless) without touching pipeline definitions. |

The PoC keeps **both** patterns deliberately. The imperative pattern lives under `../notebooks/` and gives the panel a window into how the team handles the messy edges; the declarative DLT pipelines live here and demonstrate the canonical Databricks unification of streaming and batch.

## Files

| File | What it does |
| -- | -- |
| `unified_medallion_dlt.py` | One pipeline that ingests **streaming** CNC telemetry from Event Hubs **and** **batch** SAP production-order JSON via Auto Loader; flows both through Bronze → Silver (with three DLT severity tiers + SCD2 via `apply_changes`) → Gold (a materialised view that joins the streaming-derived rollup with the batch-derived production order). The unification claim made explicit. |

## How it's deployed

The pipeline is declared as a bundle resource in [`../../../databricks.yml`](../../../databricks.yml) under `resources.pipelines.unified_medallion`. Targets `dev` / `test` / `prod` apply environment-specific catalogs and Event Hubs endpoints:

```bash
databricks bundle deploy --target dev
databricks bundle run unified_medallion --target dev
```
