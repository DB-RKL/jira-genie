"""Resolve Unity Catalog layer paths from pipeline configuration."""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.column import Column


def _spark() -> SparkSession:
    return SparkSession.getActiveSession() or SparkSession.builder.getOrCreate()


def _conf(key: str, fallback_key: str | None = None, default: str = "") -> str:
    spark = _spark()
    val = spark.conf.get(key, None)
    if val:
        return val
    if fallback_key:
        val = spark.conf.get(fallback_key, None)
        if val:
            return val
    return default


# Lakeflow Connect lands the Jira "issues" source as issues_without_deletes.
_BRONZE_TABLE_ALIASES: dict[str, str] = {
    "issues": "issues_without_deletes",
}


def bronze_fqn(table: str) -> str:
    table = _BRONZE_TABLE_ALIASES.get(table, table)
    cat = _conf("bronze_catalog", "catalog")
    sch = _conf("bronze_schema")
    return f"{cat}.{sch}.{table}"


def silver_fqn(table: str) -> str:
    cat = _conf("silver_catalog", "catalog")
    sch = _conf("silver_schema")
    return f"{cat}.{sch}.{table}"


def bronze_catalog_schema() -> tuple[str, str]:
    return _conf("bronze_catalog", "catalog"), _conf("bronze_schema")


def silver_catalog_schema() -> tuple[str, str]:
    return _conf("silver_catalog", "catalog"), _conf("silver_schema")


def conf_value(key: str, default: str = "") -> str:
    """Read a pipeline configuration value (spark conf), falling back to a default.

    Used for Jira-instance-specific knobs (e.g. the issue-type name that marks an
    epic) so they are not hardcoded in transformation logic.
    """
    return _conf(key, default=default)


def pick(cols: set[str], *names: str, default=None) -> Column:
    """Return the first present column, supporting Lakeflow camelCase and legacy snake_case."""
    for name in names:
        if name in cols:
            return F.col(name)
    return F.lit(default)
