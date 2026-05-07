"""
Unit tests for hash-based SCD2 logic.

Uses chispa for DataFrame equality and a local Spark session via pytest-spark.
Run: `pytest poc/tests/test_scd2_logic.py -v`
"""

from __future__ import annotations

import pytest
from databricks.lib.scd_helpers import add_row_hash
from pyspark.sql import SparkSession


@pytest.fixture(scope="module")
def spark() -> SparkSession:
    return (
        SparkSession.builder.appName("test-scd2")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.jars.packages", "io.delta:delta-spark_2.12:3.2.0")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )


def test_hash_is_stable_under_column_reorder(spark: SparkSession):
    """add_row_hash sorts hash_cols, so column order in the call must not matter."""
    df = spark.createDataFrame([("M-001", "AERO-FRAME", "KG")], ["material_id", "desc", "uom"])

    h_a = add_row_hash(df, ["material_id", "desc", "uom"])
    h_b = add_row_hash(df, ["uom", "material_id", "desc"])

    assert h_a.collect()[0]["row_hash"] == h_b.collect()[0]["row_hash"]


def test_hash_changes_on_value_change(spark: SparkSession):
    df1 = spark.createDataFrame([("M-001", "AERO-FRAME", "KG")], ["material_id", "desc", "uom"])
    df2 = spark.createDataFrame([("M-001", "AERO-FRAME-V2", "KG")], ["material_id", "desc", "uom"])

    h1 = add_row_hash(df1, ["material_id", "desc", "uom"]).collect()[0]["row_hash"]
    h2 = add_row_hash(df2, ["material_id", "desc", "uom"]).collect()[0]["row_hash"]

    assert h1 != h2


def test_null_values_are_hashed_distinctly_from_empty_string(spark: SparkSession):
    """We hash NULL as a sentinel \\x00 — must not collide with empty string."""
    df_null = spark.createDataFrame([("M-001", None, "KG")], "material_id string, desc string, uom string")
    df_empty = spark.createDataFrame([("M-001", "", "KG")], "material_id string, desc string, uom string")

    h_null = add_row_hash(df_null, ["material_id", "desc", "uom"]).collect()[0]["row_hash"]
    h_empty = add_row_hash(df_empty, ["material_id", "desc", "uom"]).collect()[0]["row_hash"]

    assert h_null != h_empty


def test_hash_column_added_with_default_name(spark: SparkSession):
    df = spark.createDataFrame([("M-001",)], ["material_id"])
    out = add_row_hash(df, ["material_id"])
    assert "row_hash" in out.columns
    assert out.schema["row_hash"].dataType.typeName() == "string"
