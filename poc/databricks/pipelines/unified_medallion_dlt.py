# Databricks notebook source
# MAGIC %md
# MAGIC # Unified Medallion — DLT Pipeline (streaming + batch in one)
# MAGIC
# MAGIC **Single Lakeflow Declarative Pipeline** (a.k.a. Delta Live Tables) that
# MAGIC ingests **both** streaming (CNC telemetry from Event Hubs) and batch
# MAGIC (SAP production-order JSON files via Auto Loader) into the **same
# MAGIC medallion**, with a Gold layer that joins the two. This is the
# MAGIC canonical Databricks pattern for the brief's "unify streaming and
# MAGIC batch data" requirement.
# MAGIC
# MAGIC ## Why DLT is the right tool for this flow
# MAGIC * Streaming and batch sources both use the same `@dlt.table` decorator —
# MAGIC   the framework treats files-arriving and events-arriving as a single
# MAGIC   computation model.
# MAGIC * Auto Loader (`cloudFiles`) turns batch file ingestion into a streaming
# MAGIC   source, so incremental file processing is free.
# MAGIC * `apply_changes` gives us SCD2 directly from CDC events without
# MAGIC   hand-rolling a hash-compare merge.
# MAGIC * `expect_or_fail` / `expect_or_drop` / `expect` are the same three
# MAGIC   severity tiers we already model in the custom DQ runner — but inline
# MAGIC   in the pipeline DAG with built-in metrics.
# MAGIC * Lineage, autoscaling, retries, and the event log fall out of the
# MAGIC   framework — no extra plumbing.
# MAGIC
# MAGIC ## When to NOT use DLT (and use the imperative notebooks instead)
# MAGIC * When you need the explicit `PipelineRun` audit chassis (lock + watermark
# MAGIC   + structured audit row) for AS9100 evidence — the imperative pattern
# MAGIC   gives the auditor a row-by-row run history we control precisely.
# MAGIC * When SAP-specific transformations need full PySpark control (timezone
# MAGIC   normalisation across multiple SAP instances was the war story).
# MAGIC * When Spark Structured Streaming features DLT doesn't surface yet
# MAGIC   (custom state stores, advanced foreachBatch idempotency).
# MAGIC
# MAGIC The PoC keeps both patterns deliberately — it shows the
# MAGIC right-tool-for-the-job instinct that production data teams need.

# COMMAND ----------

import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Schemas (explicit contracts — same as the imperative notebooks use)

# COMMAND ----------

OPC_PAYLOAD_SCHEMA = StructType(
    [
        StructField("plant_code", StringType(), nullable=False),
        StructField("machine_id", StringType(), nullable=False),
        StructField("event_ts", TimestampType(), nullable=False),
        StructField("vibration_g", DoubleType()),
        StructField("temperature_c", DoubleType()),
        StructField("spindle_rpm", DoubleType()),
        StructField("feed_rate_mm_min", DoubleType()),
        StructField("tool_id", StringType()),
    ]
)

SAP_SCHEMA = StructType(
    [
        StructField("production_order_id", StringType(), nullable=False),
        StructField("plant_code", StringType(), nullable=False),
        StructField("plant_timezone", StringType(), nullable=False),
        StructField("material_id", StringType(), nullable=False),
        StructField("quantity", DoubleType()),
        StructField("uom", StringType()),
        StructField("posting_date_local", StringType()),
        StructField("created_by", StringType()),
        StructField("status", StringType()),
    ]
)

# Pipeline-level config keys (set in the DLT pipeline definition / databricks.yml)
EH_BOOTSTRAP = spark.conf.get("eh_bootstrap")  # Event Hubs Kafka endpoint
EH_TOPIC = spark.conf.get("eh_topic", "cnc-telemetry")
SAP_BRONZE_PATH = spark.conf.get("sap_bronze_path")  # ADLS path
SCHEMAS_PATH = spark.conf.get("schemas_path")  # Auto Loader schema location

# COMMAND ----------

# MAGIC %md
# MAGIC ## BRONZE — streaming source (Event Hubs / Kafka API)

# COMMAND ----------


@dlt.table(
    name="bronze_cnc_telemetry",
    comment="OPC-UA telemetry events streaming from CNC machines via Event Hubs (Kafka API). 12K events/sec peak.",
    table_properties={
        "quality": "bronze",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
    },
)
def bronze_cnc_telemetry():
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", EH_BOOTSTRAP)
        .option("subscribe", EH_TOPIC)
        .option("kafka.security.protocol", "SASL_SSL")
        .option("startingOffsets", "latest")
        .option("maxOffsetsPerTrigger", 100_000)  # bound the micro-batch
        .load()
        .selectExpr(
            "CAST(value AS STRING) AS payload",
            "timestamp AS kafka_ingest_ts",
        )
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## BRONZE — batch source (SAP files via Auto Loader)
# MAGIC
# MAGIC Auto Loader is what makes "batch" land in DLT as a streaming source.
# MAGIC `cloudFiles.schemaEvolutionMode = "addNewColumns"` handles supplier-side
# MAGIC schema drift without breaking the pipeline.

# COMMAND ----------


@dlt.table(
    name="bronze_sap_production_order",
    comment="SAP S/4HANA production-order JSON files arriving in ADLS Bronze. Auto Loader for incremental ingestion.",
    table_properties={"quality": "bronze"},
)
def bronze_sap_production_order():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .option("cloudFiles.schemaLocation", f"{SCHEMAS_PATH}/sap_po")
        .schema(SAP_SCHEMA)
        .load(SAP_BRONZE_PATH)
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## SILVER — streaming, with watermark and three DLT severity tiers

# COMMAND ----------


@dlt.table(
    name="silver_cnc_telemetry_1min",
    comment="1-minute machine-level rollup of CNC telemetry, partitioned by plant_code.",
    partition_cols=["plant_code"],
)
# BLOCK — pipeline fails if a row reaches Silver without a machine_id.
@dlt.expect_or_fail("non_null_machine", "plant_code IS NOT NULL AND machine_id IS NOT NULL")
# QUARANTINE — drop rows with implausible aggregate values; pipeline continues.
@dlt.expect_or_drop("vibration_in_range", "vibration_g_avg BETWEEN 0 AND 50")
# WARN — surface the metric only.
@dlt.expect("event_count_positive", "event_count > 0")
def silver_cnc_telemetry_1min():
    parsed = (
        dlt.read_stream("bronze_cnc_telemetry")
        .withColumn("event", F.from_json("payload", OPC_PAYLOAD_SCHEMA))
        .select("event.*", "kafka_ingest_ts")
        .where(F.col("plant_code").isNotNull() & F.col("machine_id").isNotNull())
        .withWatermark("event_ts", "10 minutes")
    )
    return (
        parsed.groupBy(
            F.window("event_ts", "1 minute").alias("w"),
            "plant_code",
            "machine_id",
        )
        .agg(
            F.avg("vibration_g").alias("vibration_g_avg"),
            F.expr("percentile_approx(vibration_g, 0.95)").alias("vibration_g_p95"),
            F.max("vibration_g").alias("vibration_g_max"),
            F.avg("temperature_c").alias("temperature_c_avg"),
            F.avg("spindle_rpm").alias("spindle_rpm_avg"),
            F.count("*").alias("event_count"),
        )
        .select(
            "plant_code",
            "machine_id",
            F.col("w.start").alias("window_start_utc"),
            F.col("w.end").alias("window_end_utc"),
            "vibration_g_avg",
            "vibration_g_p95",
            "vibration_g_max",
            "temperature_c_avg",
            "spindle_rpm_avg",
            "event_count",
            F.current_timestamp().alias("ingested_at"),
        )
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## SILVER — batch source flattened, UTC-normalised, hashed
# MAGIC
# MAGIC Same transformation logic as the imperative notebook 01, expressed
# MAGIC declaratively. Notice the SAP plant-local → UTC normalisation is
# MAGIC explicit — DLT is fine for it; we keep the imperative version for the
# MAGIC cases where we need full PySpark control beyond what DLT exposes.

# COMMAND ----------


@dlt.table(
    name="silver_sap_production_order",
    comment="Flattened SAP production order with plant-local → UTC normalisation and SHA-256 row hash for change detection.",
)
@dlt.expect_or_fail("non_null_pk", "production_order_id IS NOT NULL")
@dlt.expect_or_drop("known_plant", "plant_code RLIKE '^[A-Z]{3}-[0-9]+$'")
@dlt.expect("future_posting_warn", "posting_ts_utc <= current_timestamp() + INTERVAL 7 DAYS")
def silver_sap_production_order():
    return (
        dlt.read_stream("bronze_sap_production_order")
        .withColumn(
            "posting_ts_local",
            F.to_timestamp("posting_date_local", "yyyy-MM-dd HH:mm:ss"),
        )
        .withColumn(
            "posting_ts_utc",
            F.to_utc_timestamp(F.col("posting_ts_local"), F.col("plant_timezone")),
        )
        .withColumn(
            "row_hash",
            F.sha2(
                F.concat_ws(
                    "||",
                    F.coalesce(F.col("production_order_id").cast("string"), F.lit("\x00")),
                    F.coalesce(F.col("plant_code").cast("string"), F.lit("\x00")),
                    F.coalesce(F.col("material_id").cast("string"), F.lit("\x00")),
                    F.coalesce(F.col("quantity").cast("string"), F.lit("\x00")),
                    F.coalesce(F.col("status").cast("string"), F.lit("\x00")),
                ),
                256,
            ),
        )
        .withColumn("ingested_at", F.current_timestamp())
        .drop("posting_date_local", "posting_ts_local")
    )


# COMMAND ----------

# MAGIC %md
# MAGIC ## SILVER — SCD2 dim_material via `apply_changes` (DLT's native CDC pattern)
# MAGIC
# MAGIC When inside a DLT pipeline, prefer `apply_changes` over our hand-rolled
# MAGIC `merge_scd2`. It gives idempotent, replay-safe SCD2 with built-in
# MAGIC ordering by `sequence_by` and produces lineage automatically.

# COMMAND ----------

dlt.create_streaming_table(
    name="silver_dim_material",
    comment="SCD2 material master maintained by DLT apply_changes from silver_sap_production_order events.",
)

dlt.apply_changes(
    target="silver_dim_material",
    source="silver_sap_production_order",
    keys=["material_id"],
    sequence_by=F.col("posting_ts_utc"),  # event ordering for SCD2 history
    stored_as_scd_type=2,
    track_history_column_list=["uom", "status"],  # only track real attribute changes
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## GOLD — joins streaming + batch (the unification claim made explicit)
# MAGIC
# MAGIC `dlt.read()` (without `_stream`) gives us the current snapshot of a
# MAGIC table — a batch view. So this Gold materialised view joins the
# MAGIC streaming-derived telemetry rollup with the batch-derived production
# MAGIC order context as if both were ordinary tables. **Streaming and batch
# MAGIC unified.**

# COMMAND ----------


@dlt.table(
    name="gold_machine_oee_5min",
    comment=(
        "5-minute OEE rollup per (plant, machine), joined with the active "
        "production order. Streaming telemetry + batch SAP — one Gold view."
    ),
)
def gold_machine_oee_5min():
    cnc_5m = (
        dlt.read("silver_cnc_telemetry_1min")
        .groupBy(
            "plant_code",
            "machine_id",
            (F.floor(F.unix_timestamp("window_start_utc") / 300) * 300).alias("bucket_5m_unix"),
        )
        .agg(
            F.avg("vibration_g_avg").alias("vibration_g_5m_avg"),
            F.max("vibration_g_max").alias("vibration_g_5m_max"),
            F.sum("event_count").alias("event_count_5m"),
        )
    )

    active_po = (
        dlt.read("silver_sap_production_order")
        .where(F.col("status").isin("REL", "CNF"))
        .select("plant_code", "production_order_id", "material_id", "posting_ts_utc")
    )

    return (
        cnc_5m.alias("c")
        .join(active_po.alias("p"), on=["plant_code"], how="left")
        .select(
            F.col("c.plant_code"),
            F.col("c.machine_id"),
            F.from_unixtime(F.col("c.bucket_5m_unix")).cast(TimestampType()).alias("window_start_utc"),
            F.from_unixtime(F.col("c.bucket_5m_unix") + 300).cast(TimestampType()).alias("window_end_utc"),
            "c.vibration_g_5m_avg",
            "c.vibration_g_5m_max",
            "c.event_count_5m",
            F.col("p.production_order_id").alias("active_production_order_id"),
            F.col("p.material_id"),
            F.current_timestamp().alias("computed_at"),
        )
    )
