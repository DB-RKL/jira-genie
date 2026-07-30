"""Apply Unity Catalog comments to gold tables after DLT materialization."""

import dlt
from pyspark.sql import functions as F

from comment_apply import apply_table_comments
from gold_comments import GOLD_TABLE_COMMENTS
from layer_config import gold_catalog_schema


@dlt.table(
    name="_uc_gold_comments_applied",
    comment="Internal bookkeeping table recording gold UC comment application.",
    table_properties={"quality": "gold", "pipelines.internal.table": "true"},
)
def uc_gold_comments_applied():
    gold_catalog, gold_schema = gold_catalog_schema()
    gold_count = apply_table_comments(
        spark, gold_catalog, gold_schema, GOLD_TABLE_COMMENTS
    )
    return spark.createDataFrame(
        [(gold_count,)],
        "gold_comments_applied long",
    ).select(
        F.col("gold_comments_applied"),
        F.current_timestamp().alias("applied_at"),
    )
