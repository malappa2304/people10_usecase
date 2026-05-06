# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Bronze → Silver: SAP Production Order
# MAGIC
# MAGIC **Source:** SAP S/4HANA via SAP CDC connector, landed as JSON in Bronze.
# MAGIC **Target:** `silver.production_order` (Delta, partitioned by `posting_date`).
# MAGIC
# MAGIC What this notebook does:
# MAGIC 1. Reads the synthetic Bronze JSON with an *explicit* schema (no inference).
# MAGIC 2. Flattens nested SAP structure (header + items + plant + customer).
# MAGIC 3. Normalises plant-local timestamps to UTC. (War story: a 5h30m mismatch
# MAGIC    between IST and UTC payloads from two SAP instances cost us two days of
# MAGIC    bad material-ledger reconciliation. We do not infer time zones any more.)
# MAGIC 4. Computes a SHA-256 row hash for change detection (used by SCD2 + recon).
# MAGIC 5. Writes to Silver Delta via `MERGE`.
# MAGIC 6. All wrapped in `PipelineRun` for audit + watermark + lock.

# COMMAND ----------

import sys
sys.path.append("/Workspace/Repos/people10_usecase/poc/databricks")  # MOCK: real path varies

from datetime import timezone
from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType, TimestampType, ArrayType,
)

from lib.pipeline_run import PipelineRun
from lib.scd_helpers import add_row_hash

# COMMAND ----------

# MAGIC %md
# MAGIC ### Explicit schema
# MAGIC We keep this in code (not inferred) because SAP IDoc payloads silently change
# MAGIC types when a customer adds a Z-field. Schema-on-read with an explicit contract
# MAGIC fails loud, which is what we want.

# COMMAND ----------

SAP_SCHEMA = StructType([
    StructField("production_order_id", StringType(), nullable=False),
    StructField("plant_code", StringType(), nullable=False),
    StructField("plant_timezone", StringType(), nullable=False),  # e.g. "Asia/Kolkata"
    StructField("material_id", StringType(), nullable=False),
    StructField("quantity", DoubleType()),
    StructField("uom", StringType()),
    StructField("posting_date_local", StringType()),               # SAP gives string
    StructField("created_by", StringType()),
    StructField("status", StringType()),
    StructField("customer", StructType([
        StructField("customer_id", StringType()),
        StructField("customer_name", StringType()),
        StructField("region", StringType()),
    ])),
    StructField("items", ArrayType(StructType([
        StructField("item_no", IntegerType()),
        StructField("component_id", StringType()),
        StructField("required_qty", DoubleType()),
    ]))),
])

BRONZE_PATH = "abfss://bronze@chandanlake.dfs.core.windows.net/sap/production_order/"
SILVER_TABLE = "silver.production_order"

# COMMAND ----------

with PipelineRun(
    name="bronze_to_silver_production_order",
    source_system="SAP_S4HANA",
    entity="production_order",
) as run:
    last_wm = run.watermark()  # ISO-8601 timestamp string or None on first run

    bronze = (
        spark.read.format("json")
        .schema(SAP_SCHEMA)
        .load(BRONZE_PATH)
    )

    # Watermark filter — incremental by ingest_date partition; full-history on first run.
    if last_wm is not None:
        bronze = bronze.where(F.col("posting_date_local") > F.lit(last_wm))

    # ---- flatten + UTC normalise -------------------------------------------------
    flat = (
        bronze
        .withColumn(
            "posting_ts_local",
            F.to_timestamp("posting_date_local", "yyyy-MM-dd HH:mm:ss"),
        )
        # The from_utc_timestamp / to_utc_timestamp APIs treat a naive timestamp as
        # being in the named TZ. Plant-local → UTC is `to_utc_timestamp(local, tz)`.
        .withColumn(
            "posting_ts_utc",
            F.to_utc_timestamp(F.col("posting_ts_local"), F.col("plant_timezone")),
        )
        .withColumn("customer_id", F.col("customer.customer_id"))
        .withColumn("customer_name", F.col("customer.customer_name"))
        .withColumn("customer_region", F.col("customer.region"))
        .withColumn("item_count", F.size("items"))
        .drop("customer", "items", "posting_date_local", "posting_ts_local")
    )

    # ---- row hash for change detection ------------------------------------------
    hash_cols = [
        "production_order_id", "plant_code", "material_id", "quantity", "uom",
        "posting_ts_utc", "status", "customer_id", "item_count",
    ]
    hashed = add_row_hash(flat, hash_cols).withColumn(
        "ingested_at", F.current_timestamp()
    )

    # ---- merge into Silver ------------------------------------------------------
    if not spark.catalog.tableExists(SILVER_TABLE):
        # First-time bootstrap. In production this is a Phase-2 setup task,
        # not a runtime check — we leave it here for the PoC.
        hashed.write.format("delta").partitionBy("plant_code") \
            .saveAsTable(SILVER_TABLE)
    else:
        target = DeltaTable.forName(spark, SILVER_TABLE)
        target.alias("t").merge(
            hashed.alias("s"),
            "t.production_order_id = s.production_order_id",
        ).whenMatchedUpdateAll(
            condition="t.row_hash <> s.row_hash"
        ).whenNotMatchedInsertAll().execute()

    # ---- audit metrics + watermark -----------------------------------------------
    rows_in = hashed.count()
    new_wm = hashed.agg(F.max("posting_ts_utc")).first()[0]

    run.metric("rows_in", rows_in)
    run.metric("new_watermark", str(new_wm))
    run.advance_watermark(new_wm)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Why MERGE not INSERT
# MAGIC SAP can re-emit the same `production_order_id` after a master-data
# MAGIC correction. INSERT would create duplicates that downstream Gold has to
# MAGIC dedup; MERGE on the natural key with `condition=row_hash <> row_hash`
# MAGIC pushes idempotency into the storage layer, which is the right place.
