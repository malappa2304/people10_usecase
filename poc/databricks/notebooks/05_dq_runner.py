# Databricks notebook source
# MAGIC %md
# MAGIC # 05 — Custom DQ Runner (config-driven, three severity tiers)
# MAGIC
# MAGIC DLT `EXPECT` covers the inline DQ for DLT pipelines, but our PySpark
# MAGIC notebooks (Bronze→Silver) need the same severity model. This runner
# MAGIC reads rules from `config.dq_rules` (Azure SQL, mirrored to Delta as
# MAGIC `audit.dq_rules`) and applies them with the BLOCK / QUARANTINE / WARN
# MAGIC contract.

# COMMAND ----------

from dataclasses import dataclass

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


@dataclass
class DqRule:
    rule_id: str
    table: str
    column: str | None     # NULL for cross-column / row-level rules
    expression: str        # SQL boolean expression — TRUE means PASS
    severity: str          # BLOCK | QUARANTINE | WARN
    description: str


def load_rules(table_filter: str) -> list[DqRule]:
    rows = (
        spark.table("audit.dq_rules")
        .where(F.col("is_enabled") == True)  # noqa: E712
        .where(F.col("table_name") == table_filter)
        .collect()
    )
    return [
        DqRule(
            rule_id=r["rule_id"],
            table=r["table_name"],
            column=r["column_name"],
            expression=r["expression"],
            severity=r["severity"],
            description=r["description"],
        )
        for r in rows
    ]


def run_rules(df: DataFrame, table_name: str, run_id: str) -> DataFrame:
    """Apply all rules for `table_name`. Returns the *passing* DataFrame.
    Side effects:
        * BLOCK violations → raise (caller's PipelineRun will mark FAILED).
        * QUARANTINE violations → write to `audit.dq_quarantine` and drop.
        * WARN violations → emit a count metric to `audit.dq_metrics`.
    """
    rules = load_rules(table_name)

    for rule in rules:
        violations = df.where(f"NOT ({rule.expression})")
        v_count = violations.count()

        if v_count == 0:
            _emit_metric(table_name, rule, 0, run_id)
            continue

        if rule.severity == "BLOCK":
            sample = violations.limit(5).toJSON().collect()
            raise AssertionError(
                f"DQ BLOCK [{rule.rule_id}] {rule.description}: "
                f"{v_count} rows failed. Sample: {sample}"
            )

        if rule.severity == "QUARANTINE":
            (violations
             .withColumn("dq_rule_id", F.lit(rule.rule_id))
             .withColumn("dq_run_id", F.lit(run_id))
             .withColumn("dq_quarantined_at", F.current_timestamp())
             .write.format("delta").mode("append")
             .saveAsTable("audit.dq_quarantine"))
            df = df.where(f"({rule.expression})")
            _emit_metric(table_name, rule, v_count, run_id)
            continue

        if rule.severity == "WARN":
            _emit_metric(table_name, rule, v_count, run_id)
            continue

        raise ValueError(f"Unknown severity: {rule.severity}")

    return df


def _emit_metric(table_name: str, rule: DqRule, v_count: int, run_id: str) -> None:
    spark.sql(
        f"""
        INSERT INTO audit.dq_metrics
        VALUES (
            '{run_id}', '{rule.rule_id}', '{table_name}',
            '{rule.severity}', {v_count}, current_timestamp()
        )
        """
    )


# ----------------------- Example wiring (PoC) ----------------------------------
# In production this is invoked from inside a PipelineRun block; here we keep
# a one-shot illustration so the notebook can be opened and read end-to-end.

if __name__ == "__main__":
    df = spark.table("silver.production_order")
    cleaned = run_rules(df, "silver.production_order", run_id="poc-run-1")
    print(f"Passing rows: {cleaned.count()}")
