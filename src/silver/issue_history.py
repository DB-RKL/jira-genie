"""Silver layer: issue field history (changelog) tables.

The delivery analytics model splits historical issue field values into `issue_field_history` (scalar fields)
and `issue_multiselect_history` (array-valued fields). Lakeflow Connect lands current
values in `issue_field_values`; we split here based on field type metadata.
"""

import dlt
from pyspark.sql import functions as F

from layer_config import bronze_fqn, pick


@dlt.table(
    name="field",
    comment="Field metadata: name, type, custom flag.",
)
def field():
    src = spark.read.table(bronze_fqn("issue_fields"))
    cols = set(src.columns)

    return src.select(
        F.col("id").alias("id"),
        pick(cols, "name").alias("name"),
        pick(cols, "description").alias("description"),
        pick(cols, "custom", "is_custom").cast("boolean").alias("is_custom"),
        pick(cols, "schema_type", "type").alias("schema_type"),
        pick(cols, "schema_items").alias("schema_items"),
    )


def _field_values():
    fv = spark.read.table(bronze_fqn("issue_field_values"))
    fields = spark.read.table(bronze_fqn("issue_fields"))
    fv_cols = set(fv.columns)
    field_cols = set(fields.columns)

    array_fields = (
        fields.select(
            pick(field_cols, "id", "key").alias("field_id"),
            pick(field_cols, "schema_type", "type").alias("schema_type"),
        )
        .where(F.col("schema_type") == "array")
        .select("field_id")
    )

    value_col = pick(fv_cols, "field_value", "value")
    updated_col = pick(fv_cols, "updated_at", "ingestion_timestamp", "created", "updated")
    current_col = pick(fv_cols, "is_current", default=True)

    return fv.alias("v"), array_fields.alias("a"), value_col, updated_col, current_col


@dlt.table(
    name="issue_field_history",
    comment="Scalar field values per issue, with change history. One row per (issue_id, field_id, updated_at).",
)
@dlt.expect_or_drop("not_null_issue", "issue_id IS NOT NULL")
@dlt.expect_or_drop("not_null_field", "field_id IS NOT NULL")
def issue_field_history():
    fv, array_fields, value_col, updated_col, current_col = _field_values()

    return (
        fv.join(array_fields, F.col("v.field_id") == F.col("a.field_id"), "left_anti")
        .select(
            F.col("v.issue_id").cast("string").alias("issue_id"),
            F.col("v.field_id").alias("field_id"),
            value_col.alias("value"),
            updated_col.cast("timestamp").alias("updated_at"),
            current_col.cast("boolean").alias("is_current"),
        )
    )


@dlt.table(
    name="issue_multiselect_history",
    comment="Array-valued field values per issue. Multiple rows per (issue_id, field_id, updated_at).",
)
@dlt.expect_or_drop("not_null_issue", "issue_id IS NOT NULL")
@dlt.expect_or_drop("not_null_field", "field_id IS NOT NULL")
def issue_multiselect_history():
    fv, array_fields, value_col, updated_col, current_col = _field_values()

    return (
        fv.join(array_fields, F.col("v.field_id") == F.col("a.field_id"), "inner")
        .select(
            F.col("v.issue_id").cast("string").alias("issue_id"),
            F.col("v.field_id").alias("field_id"),
            value_col.alias("value"),
            updated_col.cast("timestamp").alias("updated_at"),
            current_col.cast("boolean").alias("is_current"),
        )
    )


@dlt.table(name="issue_worklog", comment="Worklog entries per issue.")
def issue_worklog():
    src = spark.read.table(bronze_fqn("issue_worklogs"))
    cols = set(src.columns)

    return src.select(
        F.col("id").cast("string").alias("id"),
        pick(cols, "issue_id", "issueId").cast("string").alias("issue_id"),
        pick(cols, "author_account_id", "author_id", "author").alias("author_id"),
        pick(cols, "time_spent_seconds").cast("long").alias("time_spent_seconds"),
        pick(cols, "started", "started_at").cast("timestamp").alias("started_at"),
        pick(cols, "created", "created_at").cast("timestamp").alias("created_at"),
        pick(cols, "updated", "updated_at").cast("timestamp").alias("updated_at"),
        pick(cols, "comment").alias("comment"),
    )


@dlt.table(name="issue_watcher", comment="Watchers per issue.")
def issue_watcher():
    src = spark.read.table(bronze_fqn("issue_watchers"))
    cols = set(src.columns)

    return src.select(
        pick(cols, "issue_id", "issueId").cast("string").alias("issue_id"),
        pick(cols, "watcher_account_id", "userId", "watcher_id").alias("watcher_id"),
    )
