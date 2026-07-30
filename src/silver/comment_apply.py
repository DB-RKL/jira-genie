"""Apply Unity Catalog table and column comments from metadata definitions."""


def _escape_comment(text: str) -> str:
    return text.replace("'", "''")


def _table_exists(spark, fqn: str) -> bool:
    try:
        spark.table(fqn)
        return True
    except Exception:
        return False


def _existing_columns(spark, fqn: str) -> set[str]:
    return {field.name for field in spark.table(fqn).schema.fields}


def apply_table_comments(
    spark,
    catalog: str,
    schema: str,
    metadata: dict[str, dict[str, object]],
) -> int:
    """Apply table and column comments. Skips missing tables and columns."""
    applied = 0
    for table, spec in metadata.items():
        fqn = f"`{catalog}`.`{schema}`.`{table}`"
        if not _table_exists(spark, f"{catalog}.{schema}.{table}"):
            continue

        table_comment = spec.get("comment")
        if table_comment:
            spark.sql(
                f"COMMENT ON TABLE {fqn} IS '{_escape_comment(str(table_comment))}'"
            )
            applied += 1

        column_comments = spec.get("columns", {})
        if not isinstance(column_comments, dict):
            continue

        existing = _existing_columns(spark, f"{catalog}.{schema}.{table}")
        for column, comment in column_comments.items():
            if column not in existing:
                continue
            spark.sql(
                f"COMMENT ON COLUMN {fqn}.`{column}` IS '{_escape_comment(str(comment))}'"
            )
            applied += 1

    return applied


def generate_comment_sql(
    catalog: str,
    schema: str,
    metadata: dict[str, dict[str, object]],
) -> list[str]:
    """Build COMMENT ON TABLE/COLUMN statements (no existence checks)."""
    statements: list[str] = []
    for table, spec in metadata.items():
        fqn = f"`{catalog}`.`{schema}`.`{table}`"
        table_comment = spec.get("comment")
        if table_comment:
            statements.append(
                f"COMMENT ON TABLE {fqn} IS '{_escape_comment(str(table_comment))}';"
            )
        column_comments = spec.get("columns", {})
        if not isinstance(column_comments, dict):
            continue
        for column, comment in column_comments.items():
            statements.append(
                f"COMMENT ON COLUMN {fqn}.`{column}` IS '{_escape_comment(str(comment))}';"
            )
    return statements
