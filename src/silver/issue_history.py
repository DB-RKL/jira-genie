"""Silver layer: issue field history (changelog) tables.

Fivetran splits historical issue field values into `issue_field_history` (scalar fields)
and `issue_multiselect_history` (array-valued fields). Lakeflow Connect lands all values
together in `issue_field_values`; we split here based on field type.

The full schema of `issue_field_values` likely has columns:
- issue_id, field_id, field_value, updated_at, is_current

For multi-select fields the same (issue_id, field_id) key appears multiple times.
"""

import dlt
from pyspark.sql import functions as F

BRONZE = "rubjit_jira.bronze"


@dlt.table(
    name="field",
    comment="Field metadata: name, type, custom flag.",
)
def field():
    src = spark.read.table(f"{BRONZE}.issue_fields")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").alias("id"),
        col("name").alias("name"),
        col("description").alias("description"),
        col("custom").cast("boolean").alias("is_custom"),
        col("schema_type").alias("schema_type"),
        col("schema_items").alias("schema_items"),
    )


@dlt.table(
    name="issue_field_history",
    comment="Scalar field values per issue, with change history. One row per (issue_id, field_id, updated_at).",
)
@dlt.expect("not_null_issue", "issue_id IS NOT NULL")
@dlt.expect("not_null_field", "field_id IS NOT NULL")
def issue_field_history():
    fv = spark.read.table(f"{BRONZE}.issue_field_values")
    fields = spark.read.table(f"{BRONZE}.issue_fields")
    cols = set(fv.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    # Determine array-valued fields by schema_type ('array' in Jira schema).
    array_fields = (
        fields.select(F.col("id").alias("field_id"), F.col("schema_type"))
        .where(F.col("schema_type") == "array")
        .select("field_id")
    )

    return (
        fv.alias("v")
        .join(array_fields.alias("a"), F.col("v.field_id") == F.col("a.field_id"), "left_anti")
        .select(
            F.col("v.issue_id").cast("string").alias("issue_id"),
            F.col("v.field_id").alias("field_id"),
            col("field_value").alias("value"),
            col("updated_at").cast("timestamp").alias("updated_at"),
            col("is_current").cast("boolean").alias("is_current"),
        )
    )


@dlt.table(
    name="issue_multiselect_history",
    comment="Array-valued field values per issue. Multiple rows per (issue_id, field_id, updated_at).",
)
@dlt.expect("not_null_issue", "issue_id IS NOT NULL")
@dlt.expect("not_null_field", "field_id IS NOT NULL")
def issue_multiselect_history():
    fv = spark.read.table(f"{BRONZE}.issue_field_values")
    fields = spark.read.table(f"{BRONZE}.issue_fields")
    cols = set(fv.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    array_fields = (
        fields.select(F.col("id").alias("field_id"), F.col("schema_type"))
        .where(F.col("schema_type") == "array")
        .select("field_id")
    )

    return (
        fv.alias("v")
        .join(array_fields.alias("a"), F.col("v.field_id") == F.col("a.field_id"), "inner")
        .select(
            F.col("v.issue_id").cast("string").alias("issue_id"),
            F.col("v.field_id").alias("field_id"),
            col("field_value").alias("value"),
            col("updated_at").cast("timestamp").alias("updated_at"),
            col("is_current").cast("boolean").alias("is_current"),
        )
    )


@dlt.table(name="issue_worklog", comment="Worklog entries per issue.")
def issue_worklog():
    src = spark.read.table(f"{BRONZE}.issue_worklogs")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("string").alias("id"),
        col("issue_id").cast("string").alias("issue_id"),
        col("author_account_id").alias("author_id"),
        col("time_spent_seconds").cast("long").alias("time_spent_seconds"),
        col("started").cast("timestamp").alias("started_at"),
        col("created").cast("timestamp").alias("created_at"),
        col("updated").cast("timestamp").alias("updated_at"),
        col("comment").alias("comment"),
    )


@dlt.table(name="issue_watcher", comment="Watchers per issue.")
def issue_watcher():
    src = spark.read.table(f"{BRONZE}.issue_watchers")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        col("issue_id").cast("string").alias("issue_id"),
        col("watcher_account_id").alias("watcher_id"),
    )
