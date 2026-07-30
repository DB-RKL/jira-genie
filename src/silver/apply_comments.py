"""Apply Unity Catalog comments to bronze and silver tables after DLT materialization."""

import dlt
from pyspark.sql import functions as F

from bronze_comments import BRONZE_TABLE_COMMENTS
from comment_apply import apply_table_comments
from layer_config import bronze_catalog_schema, silver_catalog_schema
from silver_comments import SILVER_TABLE_COMMENTS


@dlt.table(
    name="_uc_comments_applied",
    comment="Internal bookkeeping table recording UC comment application.",
    table_properties={"quality": "silver", "pipelines.internal.table": "true"},
)
def uc_comments_applied():
    bronze_catalog, bronze_schema = bronze_catalog_schema()
    silver_catalog, silver_schema = silver_catalog_schema()

    bronze_count = apply_table_comments(
        spark, bronze_catalog, bronze_schema, BRONZE_TABLE_COMMENTS
    )
    silver_count = apply_table_comments(
        spark, silver_catalog, silver_schema, SILVER_TABLE_COMMENTS
    )

    return spark.createDataFrame(
        [(bronze_count, silver_count)],
        "bronze_comments_applied long, silver_comments_applied long",
    ).select(
        F.col("bronze_comments_applied"),
        F.col("silver_comments_applied"),
        F.current_timestamp().alias("applied_at"),
    )
