"""Silver layer: lookup / configuration tables (boards, sprints, groups, schemes)."""

import dlt
from pyspark.sql import functions as F

BRONZE = "rubjit_jira.bronze"


@dlt.table(name="board", comment="Agile boards.")
def board():
    src = spark.read.table(f"{BRONZE}.boards")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        col("name").alias("name"),
        col("type").alias("board_type"),
        col("project_id").cast("long").alias("project_id"),
        col("filter_id").cast("long").alias("filter_id"),
        col("location_type").alias("location_type"),
    )


@dlt.table(name="project_board", comment="Project <-> board mapping.")
def project_board():
    src = spark.read.table(f"{BRONZE}.project_board")
    return src.select(
        F.col("project_id").cast("long").alias("project_id"),
        F.col("board_id").cast("long").alias("board_id"),
    )


@dlt.table(name="sprint", comment="Sprints.")
def sprint():
    src = spark.read.table(f"{BRONZE}.sprints")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        col("board_id").cast("long").alias("board_id"),
        col("name").alias("name"),
        col("state").alias("state"),
        col("start_date").cast("timestamp").alias("start_date"),
        col("end_date").cast("timestamp").alias("end_date"),
        col("complete_date").cast("timestamp").alias("complete_date"),
        col("goal").alias("goal"),
    )


@dlt.table(name="user_group", comment="Bridge user <-> group.")
def user_group():
    src = spark.read.table(f"{BRONZE}.user_group")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        col("account_id").alias("account_id"),
        col("group_id").alias("group_id"),
        col("group_name").alias("group_name"),
    )


@dlt.table(name="group", comment="Deduped group lookup derived from user_group.")
def group():
    src = spark.read.table(f"{BRONZE}.user_group")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return (
        src.select(
            col("group_id").alias("id"),
            col("group_name").alias("name"),
        )
        .where(F.col("id").isNotNull())
        .distinct()
    )


@dlt.table(name="application_role", comment="Application roles in Jira.")
def application_role():
    src = spark.read.table(f"{BRONZE}.application_roles")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("key").alias("application_role_key"),
        col("name").alias("name"),
        col("description").alias("description"),
        col("user_count").cast("int").alias("user_count"),
        col("group_count").cast("int").alias("group_count"),
    )


@dlt.table(name="permission_scheme", comment="Permission schemes.")
def permission_scheme():
    src = spark.read.table(f"{BRONZE}.permission_schemes")
    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        F.col("description").alias("description"),
    )


@dlt.table(name="security_scheme", comment="Security schemes.")
def security_scheme():
    src = spark.read.table(f"{BRONZE}.security_schemes")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        F.col("description").alias("description"),
        col("default_security_level_id").cast("long").alias("default_security_level_id"),
    )


@dlt.table(name="security_level", comment="Security levels within schemes.")
def security_level():
    src = spark.read.table(f"{BRONZE}.security_level")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        F.col("description").alias("description"),
        col("security_scheme_id").cast("long").alias("security_scheme_id"),
    )


@dlt.table(name="project_permission", comment="Project-level permission grants.")
def project_permission():
    src = spark.read.table(f"{BRONZE}.project_permissions")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        col("project_id").cast("long").alias("project_id"),
        col("permission").alias("permission"),
        col("holder_type").alias("holder_type"),
        col("holder_value").alias("holder_value"),
    )
