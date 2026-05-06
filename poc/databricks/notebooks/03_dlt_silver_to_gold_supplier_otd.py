# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — DLT: Silver → Gold `fact_supplier_otd`
# MAGIC
# MAGIC Delta Live Tables pipeline. Three severity tiers of `EXPECT`:
# MAGIC
# MAGIC | Tier        | DLT clause                       | Behaviour on violation                |
# MAGIC | ----------- | -------------------------------- | ------------------------------------- |
# MAGIC | BLOCK       | `expect_or_fail`                 | Pipeline fails — page on-call          |
# MAGIC | QUARANTINE  | `expect_or_drop` + quarantine    | Row routed to `_quarantine` table     |
# MAGIC | WARN        | `expect`                         | Row passes; metric emitted to audit   |
# MAGIC
# MAGIC We chose DLT over more PySpark for two reasons: declarative readability
# MAGIC for the team, and free expectations infrastructure that wires straight
# MAGIC into the audit dashboard.

# COMMAND ----------

import dlt
from pyspark.sql import functions as F


# ---- Silver inputs -----------------------------------------------------------

@dlt.view(comment="Latest dispatch events from supplier portals")
def silver_supplier_dispatch():
    return spark.read.table("silver.supplier_dispatch")


@dlt.view(comment="Production order requirements with promised dates")
def silver_production_order_requirements():
    return spark.read.table("silver.production_order_requirements")


# ---- Gold fact ---------------------------------------------------------------

@dlt.table(
    name="gold_fact_supplier_otd",
    comment="One row per (supplier_id, plant_code, expected_date_utc) — supplier on-time-delivery fact",
    table_properties={
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.autoOptimize.autoCompact": "true",
    },
    partition_cols=["expected_date_utc"],
)
# BLOCK — these columns are required for any downstream join. NULL = pipeline fails.
@dlt.expect_or_fail("non_null_supplier_id", "supplier_id IS NOT NULL")
@dlt.expect_or_fail("non_null_plant_code",  "plant_code IS NOT NULL")
@dlt.expect_or_fail("non_null_expected_date_utc", "expected_date_utc IS NOT NULL")
# QUARANTINE — row is suspect but pipeline can continue; row goes to _quarantine.
@dlt.expect_or_drop("delivery_qty_non_negative", "delivery_qty >= 0")
@dlt.expect_or_drop("expected_before_actual", "actual_delivery_ts_utc IS NULL OR actual_delivery_ts_utc >= expected_date_utc - interval 60 days")
# WARN — surfaced as a metric only.
@dlt.expect("supplier_known_in_dim", "supplier_id IN (SELECT supplier_id FROM gold.dim_supplier WHERE is_current = true)")
def gold_fact_supplier_otd():
    dispatch = dlt.read("silver_supplier_dispatch")
    reqs = dlt.read("silver_production_order_requirements")

    return (
        reqs.alias("r")
        .join(dispatch.alias("d"),
              (F.col("r.purchase_order_id") == F.col("d.purchase_order_id"))
              & (F.col("r.material_id") == F.col("d.material_id")),
              "left")
        .select(
            F.col("r.supplier_id"),
            F.col("r.plant_code"),
            F.col("r.material_id"),
            F.col("r.purchase_order_id"),
            F.col("r.expected_delivery_ts_utc").alias("expected_date_utc"),
            F.col("d.actual_delivery_ts_utc"),
            F.coalesce(F.col("d.delivery_qty"), F.lit(0.0)).alias("delivery_qty"),
            F.col("r.required_qty"),
            F.when(
                F.col("d.actual_delivery_ts_utc").isNull(), F.lit("PENDING")
            ).when(
                F.col("d.actual_delivery_ts_utc") <= F.col("r.expected_delivery_ts_utc"),
                F.lit("ON_TIME"),
            ).otherwise(F.lit("LATE")).alias("otd_status"),
            F.coalesce(
                F.unix_timestamp("d.actual_delivery_ts_utc")
                - F.unix_timestamp("r.expected_delivery_ts_utc"),
                F.lit(None),
            ).alias("delay_seconds"),
            F.current_timestamp().alias("ingested_at"),
        )
    )


# ---- Materialised aggregate for Power BI -------------------------------------

@dlt.table(
    name="gold_supplier_otd_daily",
    comment="Daily supplier OTD aggregate — feeds the supplier OTD real-time dashboard",
)
def gold_supplier_otd_daily():
    return (
        dlt.read("gold_fact_supplier_otd")
        .where(F.col("otd_status") != "PENDING")
        .groupBy(
            F.col("plant_code"),
            F.col("supplier_id"),
            F.to_date("expected_date_utc").alias("expected_date"),
        )
        .agg(
            F.count("*").alias("total_orders"),
            F.sum(F.when(F.col("otd_status") == "ON_TIME", 1).otherwise(0)).alias("on_time_orders"),
            F.avg("delay_seconds").alias("avg_delay_seconds"),
        )
        .withColumn(
            "otd_pct",
            F.round(F.col("on_time_orders") * 100.0 / F.col("total_orders"), 2),
        )
    )
