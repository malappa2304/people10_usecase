"""
Parallel-run reconciliation framework.

What this does
--------------
For every pipeline currently in dual-run (legacy Informatica → Oracle DW AND
new Delta Gold), this job does a daily FULL OUTER JOIN of the two outputs on
the natural key, computes a SHA-256 hash over a canonical projection of the
value columns on each side, and classifies any mismatch into one of three
variance types:

    MISSING_IN_NEW     — row exists in legacy, not in Delta Gold
    MISSING_IN_LEGACY  — row exists in Delta Gold, not in legacy
    VALUE_MISMATCH     — same key, different hash

Output is one Delta table (`audit.reconciliation_results`) that the cutover
dashboard reads. Per-pipeline tolerance is passed in via `ReconConfig`
(in production, that config would be loaded from a YAML file or table — for
this PoC the config is constructed directly in code). A pipeline is
**cutover-ready** when variance % is below tolerance for ≥ 7 consecutive days.

Why three variance types and not just "mismatch"
------------------------------------------------
The three categories drive different remediation paths. MISSING_IN_NEW is
usually a join-condition bug in our Silver→Gold transformation; MISSING_IN_LEGACY
is usually Informatica filtering out a row we've correctly retained;
VALUE_MISMATCH is usually a transformation difference (timezone, rounding,
SAP plant-local vs UTC). The data owner reviews each category separately.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


@dataclass
class ReconConfig:
    pipeline_name: str
    legacy_table: str       # e.g. oracle_dw.f_supplier_otd
    new_table: str          # e.g. gold.fact_supplier_otd
    business_keys: list[str]
    value_cols: list[str]
    variance_tolerance_pct: float = 0.5  # default, overridden by config


def _hash_values(df: DataFrame, value_cols: list[str], out_col: str = "value_hash") -> DataFrame:
    cols_sorted = sorted(value_cols)
    expr = F.concat_ws(
        "||",
        *[F.coalesce(F.col(c).cast("string"), F.lit("\x00")) for c in cols_sorted],
    )
    return df.withColumn(out_col, F.sha2(expr, 256))


def reconcile(spark: SparkSession, cfg: ReconConfig, run_date: str) -> DataFrame:
    """Run one reconciliation, return a DataFrame ready to append to results."""
    legacy = _hash_values(spark.table(cfg.legacy_table), cfg.value_cols).select(
        *cfg.business_keys, F.col("value_hash").alias("legacy_hash")
    )
    new = _hash_values(spark.table(cfg.new_table), cfg.value_cols).select(
        *cfg.business_keys, F.col("value_hash").alias("new_hash")
    )

    joined = legacy.join(new, cfg.business_keys, "full_outer")

    classified = joined.withColumn(
        "variance_type",
        F.when(F.col("legacy_hash").isNotNull() & F.col("new_hash").isNull(), "MISSING_IN_NEW")
         .when(F.col("legacy_hash").isNull() & F.col("new_hash").isNotNull(), "MISSING_IN_LEGACY")
         .when(F.col("legacy_hash") != F.col("new_hash"), "VALUE_MISMATCH")
         .otherwise(None),
    ).where(F.col("variance_type").isNotNull())

    total_rows = joined.count()
    variances = classified.count()
    variance_pct = (variances * 100.0 / total_rows) if total_rows > 0 else 0.0

    # The result row the dashboard consumes — one row per (pipeline, day).
    summary = spark.createDataFrame(
        [(
            cfg.pipeline_name,
            run_date,
            total_rows,
            variances,
            variance_pct,
            cfg.variance_tolerance_pct,
            variance_pct <= cfg.variance_tolerance_pct,
        )],
        schema="pipeline_name string, run_date string, total_rows long, "
               "variance_rows long, variance_pct double, tolerance_pct double, "
               "within_tolerance boolean",
    )

    # Sample variances for triage — capped so we don't blow up the result table.
    sampled = classified.limit(500).withColumn("pipeline_name", F.lit(cfg.pipeline_name)) \
                                   .withColumn("run_date", F.lit(run_date))

    sampled.write.format("delta").mode("append") \
        .saveAsTable("audit.reconciliation_variance_samples")

    return summary


def cutover_ready(
    spark: SparkSession, pipeline_name: str, consecutive_green_days: int = 7
) -> bool:
    """Return True iff variance has been within tolerance for N consecutive days."""
    history = (
        spark.table("audit.reconciliation_results")
        .where(F.col("pipeline_name") == pipeline_name)
        .orderBy(F.col("run_date").desc())
        .limit(consecutive_green_days)
        .collect()
    )
    if len(history) < consecutive_green_days:
        return False
    return all(row["within_tolerance"] for row in history)
