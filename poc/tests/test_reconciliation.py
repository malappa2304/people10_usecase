"""
Tests for the parallel-run reconciliation framework.

We construct two small in-memory tables that represent legacy and new outputs,
register them as temp views, and verify the three variance types are correctly
classified.
"""

from __future__ import annotations

import pytest
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from databricks.lib.reconciliation import ReconConfig, reconcile


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("test-reconciliation")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.2.0")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def _make_views(spark: SparkSession) -> None:
    legacy = [
        ("PO-001", "M-001", 10.0, "ON_TIME"),    # match
        ("PO-002", "M-002", 20.0, "LATE"),        # value mismatch (20 vs 25)
        ("PO-003", "M-003", 30.0, "ON_TIME"),    # missing in new
    ]
    new = [
        ("PO-001", "M-001", 10.0, "ON_TIME"),    # match
        ("PO-002", "M-002", 25.0, "LATE"),        # value mismatch
        ("PO-004", "M-004", 40.0, "ON_TIME"),    # missing in legacy
    ]
    schema = "purchase_order_id string, material_id string, qty double, status string"
    spark.createDataFrame(legacy, schema).createOrReplaceTempView("legacy_otd")
    spark.createDataFrame(new,    schema).createOrReplaceTempView("new_otd")
    spark.sql("CREATE DATABASE IF NOT EXISTS audit")
    spark.sql(
        "CREATE TABLE IF NOT EXISTS audit.reconciliation_variance_samples "
        "(purchase_order_id string, material_id string, legacy_hash string, new_hash string, "
        " variance_type string, pipeline_name string, run_date string)"
    )


def test_three_variance_types_are_classified(spark: SparkSession):
    _make_views(spark)
    cfg = ReconConfig(
        pipeline_name="test_otd",
        legacy_table="legacy_otd",
        new_table="new_otd",
        business_keys=["purchase_order_id"],
        value_cols=["material_id", "qty", "status"],
        variance_tolerance_pct=1.0,
    )
    summary = reconcile(spark, cfg, run_date="2026-05-06")
    row = summary.first()

    assert row["pipeline_name"] == "test_otd"
    assert row["total_rows"]    == 4   # PO-001 match + PO-002 mismatch + PO-003 + PO-004
    assert row["variance_rows"] == 3
    assert row["variance_pct"]  == 75.0
    assert row["within_tolerance"] is False


def test_within_tolerance_true_when_zero_variance(spark: SparkSession):
    rows = [("PO-001", "M-001", 10.0, "ON_TIME")]
    schema = "purchase_order_id string, material_id string, qty double, status string"
    spark.createDataFrame(rows, schema).createOrReplaceTempView("legacy_match")
    spark.createDataFrame(rows, schema).createOrReplaceTempView("new_match")
    spark.sql("CREATE DATABASE IF NOT EXISTS audit")
    spark.sql(
        "CREATE TABLE IF NOT EXISTS audit.reconciliation_variance_samples "
        "(purchase_order_id string, material_id string, legacy_hash string, new_hash string, "
        " variance_type string, pipeline_name string, run_date string)"
    )

    cfg = ReconConfig(
        pipeline_name="test_match",
        legacy_table="legacy_match",
        new_table="new_match",
        business_keys=["purchase_order_id"],
        value_cols=["material_id", "qty", "status"],
        variance_tolerance_pct=0.5,
    )
    row = reconcile(spark, cfg, run_date="2026-05-06").first()
    assert row["variance_rows"] == 0
    assert row["within_tolerance"] is True
