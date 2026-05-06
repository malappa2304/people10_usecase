"""
Multi-format reader factory.

A single function that returns a configured DataFrameReader for the formats
we actually see at Chandan: SAP IDoc XML/JSON, MES SQL Server (JDBC),
Teamcenter REST (pre-staged JSON), supplier CSV/Excel, OPC-UA Avro.

Auto Loader is the default for files (`cloudFiles`); we lean on schema
evolution + schema hints to handle supplier-side schema drift gracefully.
"""

from __future__ import annotations

from typing import Optional

from pyspark.sql import DataFrame, SparkSession


def read_sap_json(
    spark: SparkSession,
    path: str,
    schema: Optional[str] = None,
    schema_location: Optional[str] = None,
) -> DataFrame:
    """SAP S/4HANA payloads we get as JSON via the SAP CDC connector.

    We pin schema explicitly when we have it (avoids the silent type-narrowing
    issue we hit on `posting_date` between IST/UTC payloads), but fall back to
    Auto Loader's schema inference + schema-location for new tables.
    """
    reader = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    )
    if schema is not None:
        reader = reader.schema(schema)
    elif schema_location is not None:
        reader = reader.option("cloudFiles.schemaLocation", schema_location)
    return reader.load(path)


def read_supplier_csv(
    spark: SparkSession,
    path: str,
    schema: str,
    schema_location: str,
) -> DataFrame:
    """Supplier dispatch CSVs — schema-on-read, rescue on drift.

    `_rescued_data` captures any column the supplier added without telling us;
    those rows go into a quarantine table, not Silver.
    """
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.schemaLocation", schema_location)
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .option("header", "true")
        .schema(schema)
        .load(path)
    )


def read_mes_jdbc(
    spark: SparkSession,
    jdbc_url: str,
    table: str,
    secret_scope: str,
    user_key: str,
    password_key: str,
    watermark_col: str,
    watermark_value: Optional[str],
) -> DataFrame:
    """Incremental pull from on-prem MES (SQL Server) via SHIR.

    Note: in production this is invoked via ADF Copy + landed as Parquet to
    Bronze; we expose a JDBC reader here for completeness and for tests.
    """
    user = dbutils.secrets.get(secret_scope, user_key)  # type: ignore[name-defined]
    password = dbutils.secrets.get(secret_scope, password_key)  # type: ignore[name-defined]
    where = f"{watermark_col} > '{watermark_value}'" if watermark_value else "1=1"
    return (
        spark.read.format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", f"(SELECT * FROM {table} WHERE {where}) AS sub")
        .option("user", user)
        .option("password", password)
        .option("fetchsize", "10000")
        .load()
    )


def read_eventhubs_kafka(
    spark: SparkSession,
    bootstrap_servers: str,
    topic: str,
    starting_offsets: str = "latest",
    max_offsets_per_trigger: int = 100_000,
) -> DataFrame:
    """OPC-UA telemetry via Event Hubs Kafka API.

    `max_offsets_per_trigger` keeps the micro-batch bounded so the foreachBatch
    MERGE stays predictable under load — without it, a backlog after a cluster
    bounce can ingest tens of millions of events into one trigger and OOM.
    """
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", topic)
        .option("startingOffsets", starting_offsets)
        .option("maxOffsetsPerTrigger", max_offsets_per_trigger)
        .option("kafka.security.protocol", "SASL_SSL")
        .option("kafka.sasl.mechanism", "PLAIN")
        .load()
    )
