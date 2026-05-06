# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — SCD2: dim_material
# MAGIC
# MAGIC Hash-based SCD2 onto `gold.dim_material`. Source is the latest Silver
# MAGIC snapshot of material master joined from SAP MARA + Teamcenter PLM.
# MAGIC History matters for AS9100 — the auditor needs to know which revision of a
# MAGIC material spec was used on a given production order date.

# COMMAND ----------

import sys
sys.path.append("/Workspace/Repos/people10_usecase/poc/databricks")

from pyspark.sql import functions as F

from lib.pipeline_run import PipelineRun
from lib.scd_helpers import add_row_hash, merge_scd2

# COMMAND ----------

DIM_TABLE = "gold.dim_material"
HASH_COLS = [
    "material_id", "material_description", "material_group",
    "uom", "spec_revision", "criticality_class",
    "is_aerospace_grade", "supplier_default_id",
]
BUSINESS_KEYS = ["material_id"]

# COMMAND ----------

with PipelineRun(
    name="scd2_dim_material",
    source_system="SAP_S4HANA+TEAMCENTER",
    entity="dim_material",
) as run:
    src = (
        spark.table("silver.material_master")
        .select(
            "material_id",
            "material_description",
            "material_group",
            "uom",
            "spec_revision",
            "criticality_class",
            "is_aerospace_grade",
            "supplier_default_id",
        )
    )
    src_hashed = add_row_hash(src, HASH_COLS)

    if not spark.catalog.tableExists(DIM_TABLE):
        # First load — every row is "current".
        bootstrap = (
            src_hashed
            .withColumn("effective_from", F.current_timestamp())
            .withColumn("effective_to", F.lit(None).cast("timestamp"))
            .withColumn("is_current", F.lit(True))
        )
        bootstrap.write.format("delta").saveAsTable(DIM_TABLE)
    else:
        merge_scd2(
            spark,
            target_table=DIM_TABLE,
            source_df=src_hashed,
            business_keys=BUSINESS_KEYS,
        )

    # Cheap audit metrics; expensive ones (cardinality, distinct supplier_default_id)
    # we leave for the nightly DQ runner so the SCD path stays fast.
    run.metric("source_rows", src.count())
