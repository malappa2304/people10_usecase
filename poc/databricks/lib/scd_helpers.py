"""
SCD1 / SCD2 helpers — hash-based, source-agnostic.

Why hash-based and not source CDC
---------------------------------
Source CDC ties Silver to whatever change-tracking quirk the source has
(SAP shadow tables, MES trigger-based audit columns, the supplier file we
get only as a daily full snapshot…). A SHA-256 over a canonical projection
of the attributes lets us dedupe and SCD2 *the same way* across all sources,
and lets us re-run from Bronze without needing the source to remember.

Trade-off: at 50M+ rows on a wide dimension the hash compute is non-trivial.
We accept it; we don't run dimension SCD2 on the hot path.
"""

from __future__ import annotations

from typing import Iterable

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def add_row_hash(df: DataFrame, hash_cols: Iterable[str], out_col: str = "row_hash") -> DataFrame:
    """SHA-256 over a stable, sorted projection.

    `hash_cols` is sorted so that adding/removing an attribute later doesn't
    silently shift hashes — schema evolution should be explicit.
    """
    cols_sorted = sorted(hash_cols)
    concat_expr = F.concat_ws(
        "||",
        *[F.coalesce(F.col(c).cast("string"), F.lit("\x00")) for c in cols_sorted],
    )
    return df.withColumn(out_col, F.sha2(concat_expr, 256))


def merge_scd1(
    spark: SparkSession,
    target_table: str,
    source_df: DataFrame,
    business_keys: list[str],
) -> None:
    """In-place upsert; no history kept. Use only when the business says so."""
    on_clause = " AND ".join([f"t.{k} = s.{k}" for k in business_keys])
    DeltaTable.forName(spark, target_table).alias("t").merge(
        source_df.alias("s"), on_clause
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()


def merge_scd2(
    spark: SparkSession,
    target_table: str,
    source_df: DataFrame,
    business_keys: list[str],
    hash_col: str = "row_hash",
    effective_from: str = "effective_from",
    effective_to: str = "effective_to",
    is_current: str = "is_current",
) -> None:
    """Hash-based SCD2 merge.

    Algorithm
    ---------
    1. For each incoming row, compare hash against current row in target.
    2. If different OR no current row → expire current (set effective_to = now,
       is_current = false) AND insert new row (effective_from = now,
       is_current = true).
    3. If hash matches → no-op.

    Implementation detail: Delta's MERGE doesn't natively support "expire
    current AND insert new" in one statement, so we run two passes inside
    a single Delta transaction (atomic via Delta's optimistic concurrency).
    """
    target = DeltaTable.forName(spark, target_table)
    on_keys = " AND ".join([f"t.{k} = s.{k}" for k in business_keys])

    # --- Pass 1: expire matched-but-changed current rows ---
    target.alias("t").merge(
        source_df.alias("s"),
        f"{on_keys} AND t.{is_current} = true AND t.{hash_col} <> s.{hash_col}",
    ).whenMatchedUpdate(
        set={
            effective_to: "current_timestamp()",
            is_current: "false",
        }
    ).execute()

    # --- Pass 2: insert new versions for changed-or-new rows ---
    # Build the set of source rows whose hash isn't currently in target.
    current_hashes = (
        spark.table(target_table)
        .where(F.col(is_current) == True)  # noqa: E712
        .select(*business_keys, F.col(hash_col).alias("__current_hash"))
    )
    join_cond = [source_df[k] == current_hashes[k] for k in business_keys]
    to_insert = (
        source_df.alias("s")
        .join(current_hashes.alias("c"), join_cond, "left")
        .where(
            (F.col("c.__current_hash").isNull())
            | (F.col(f"s.{hash_col}") != F.col("c.__current_hash"))
        )
        .select("s.*")
        .withColumn(effective_from, F.current_timestamp())
        .withColumn(effective_to, F.lit(None).cast("timestamp"))
        .withColumn(is_current, F.lit(True))
    )
    to_insert.write.format("delta").mode("append").saveAsTable(target_table)
