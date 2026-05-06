# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — Streaming: CNC Telemetry (12K events/sec peak)
# MAGIC
# MAGIC Reads OPC-UA events off Event Hubs (Kafka API), 32 partitions keyed on
# MAGIC `plant_code+machine_id`. Watermark 10 min, RocksDB state store. Stateful
# MAGIC 1-min rollup of vibration/temperature/spindle-rpm. Writes Silver via
# MAGIC `foreachBatch` + idempotent MERGE.
# MAGIC
# MAGIC The same Bronze stream is consumed three times at three SLAs:
# MAGIC * 30-sec triggers → OEE board (this notebook is the 30-sec consumer)
# MAGIC * 5-min triggers → ML scoring job (separate notebook, same source)
# MAGIC * `Trigger.AvailableNow` hourly → AS9100 audit aggregation (separate job)
# MAGIC
# MAGIC War story: small-file problem on IoT Bronze made a downstream query take
# MAGIC 47 min. `OPTIMIZE bronze.cnc_telemetry ZORDER BY (machine_id, event_ts)`
# MAGIC nightly took it to 22 sec.

# COMMAND ----------

import sys
sys.path.append("/Workspace/Repos/people10_usecase/poc/databricks")

from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, TimestampType,
)

from lib.format_readers import read_eventhubs_kafka

# COMMAND ----------

# ---- Config ------------------------------------------------------------------

EH_BOOTSTRAP = "chandan-eventhubs.servicebus.windows.net:9093"  # MOCK
TOPIC = "cnc-telemetry"

CHECKPOINT = "abfss://checkpoints@chandanlake.dfs.core.windows.net/streaming/cnc_telemetry/"
SILVER_TABLE = "silver.cnc_telemetry_1min"

# Trigger interval — 30s for the OEE consumer. The same source code is
# parameterised in production; we hard-code here for readability.
TRIGGER_INTERVAL = "30 seconds"

# RocksDB on Databricks — required at this scale; default HDFS state store
# OOMs at >5K events/sec.
spark.conf.set(
    "spark.sql.streaming.stateStore.providerClass",
    "com.databricks.sql.streaming.state.RocksDBStateStoreProvider",
)

# COMMAND ----------

OPC_PAYLOAD_SCHEMA = StructType([
    StructField("plant_code", StringType(), nullable=False),
    StructField("machine_id", StringType(), nullable=False),
    StructField("event_ts", TimestampType(), nullable=False),
    StructField("vibration_g", DoubleType()),
    StructField("temperature_c", DoubleType()),
    StructField("spindle_rpm", DoubleType()),
    StructField("feed_rate_mm_min", DoubleType()),
    StructField("tool_id", StringType()),
])

# COMMAND ----------

# ---- Read from Event Hubs ----------------------------------------------------
raw = read_eventhubs_kafka(
    spark,
    bootstrap_servers=EH_BOOTSTRAP,
    topic=TOPIC,
    starting_offsets="latest",
    max_offsets_per_trigger=100_000,
)

parsed = (
    raw
    .selectExpr("CAST(value AS STRING) AS payload", "timestamp AS kafka_ts")
    .withColumn("event", F.from_json("payload", OPC_PAYLOAD_SCHEMA))
    .select("event.*", "kafka_ts")
    .where(F.col("plant_code").isNotNull() & F.col("machine_id").isNotNull())
    .withWatermark("event_ts", "10 minutes")
)

# ---- 1-minute stateful rollup -----------------------------------------------
agg = (
    parsed
    .groupBy(
        F.window("event_ts", "1 minute").alias("w"),
        F.col("plant_code"),
        F.col("machine_id"),
    )
    .agg(
        F.avg("vibration_g").alias("vibration_g_avg"),
        F.max("vibration_g").alias("vibration_g_p100"),
        F.expr("percentile_approx(vibration_g, 0.95)").alias("vibration_g_p95"),
        F.avg("temperature_c").alias("temperature_c_avg"),
        F.avg("spindle_rpm").alias("spindle_rpm_avg"),
        F.count("*").alias("event_count"),
    )
    .select(
        F.col("plant_code"),
        F.col("machine_id"),
        F.col("w.start").alias("window_start_utc"),
        F.col("w.end").alias("window_end_utc"),
        "vibration_g_avg", "vibration_g_p100", "vibration_g_p95",
        "temperature_c_avg", "spindle_rpm_avg", "event_count",
        F.current_timestamp().alias("ingested_at"),
    )
)

# COMMAND ----------

def upsert_to_silver(microbatch_df, batch_id: int) -> None:
    """Idempotent MERGE — same (plant_code, machine_id, window_start_utc)
    will update with the freshest aggregate. Idempotency matters here because
    Structured Streaming can re-deliver a micro-batch on driver restart."""
    if microbatch_df.rdd.isEmpty():
        return

    if not spark.catalog.tableExists(SILVER_TABLE):
        microbatch_df.write.format("delta") \
            .partitionBy("plant_code") \
            .saveAsTable(SILVER_TABLE)
        return

    target = DeltaTable.forName(spark, SILVER_TABLE)
    target.alias("t").merge(
        microbatch_df.alias("s"),
        "t.plant_code = s.plant_code AND t.machine_id = s.machine_id "
        "AND t.window_start_utc = s.window_start_utc",
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()


query = (
    agg.writeStream
    .foreachBatch(upsert_to_silver)
    .option("checkpointLocation", CHECKPOINT)
    .trigger(processingTime=TRIGGER_INTERVAL)
    .queryName("cnc_telemetry_1min_oee")
    .start()
)

# query.awaitTermination()  # uncommented in production; left commented for PoC.
