"""Silver layer: lookup / configuration tables (boards, sprints, groups, schemes)."""

import dlt
from pyspark.sql import functions as F

from layer_config import bronze_fqn, pick

@dlt.table(name="board", comment="Agile boards.")
def board():
    src = spark.read.table(bronze_fqn("boards"))
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        pick(cols, "name").alias("name"),
        pick(cols, "type", "board_type").alias("board_type"),
        pick(cols, "project_id", "projectId").cast("long").alias("project_id"),
        pick(cols, "filter_id", "filterId").cast("long").alias("filter_id"),
        pick(cols, "location_type", "location").alias("location_type"),
    )


@dlt.table(name="project_board", comment="Project <-> board mapping.")
def project_board():
    src = spark.read.table(bronze_fqn("project_board"))
    cols = set(src.columns)

    return src.select(
        pick(cols, "project_id", "projectId").cast("long").alias("project_id"),
        pick(cols, "board_id", "boardId").cast("long").alias("board_id"),
    )


@dlt.table(name="sprint", comment="Sprints.")
def sprint():
    src = spark.read.table(bronze_fqn("sprints"))
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        pick(cols, "board_id", "boardId").cast("long").alias("board_id"),
        pick(cols, "name").alias("name"),
        pick(cols, "state").alias("state"),
        pick(cols, "start_date", "startDate").cast("timestamp").alias("start_date"),
        pick(cols, "end_date", "endDate").cast("timestamp").alias("end_date"),
        pick(cols, "complete_date", "completeDate").cast("timestamp").alias("complete_date"),
        pick(cols, "goal").alias("goal"),
    )


@dlt.table(name="user_group", comment="Bridge user <-> group.")
def user_group():
    src = spark.read.table(bronze_fqn("user_group"))
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
    src = spark.read.table(bronze_fqn("user_group"))
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
    src = spark.read.table(bronze_fqn("application_roles"))
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
    src = spark.read.table(bronze_fqn("permission_schemes"))
    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        F.col("description").alias("description"),
    )


@dlt.table(name="security_scheme", comment="Security schemes.")
def security_scheme():
    src = spark.read.table(bronze_fqn("security_schemes"))
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
    src = spark.read.table(bronze_fqn("security_level"))
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
    src = spark.read.table(bronze_fqn("project_permissions"))
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        col("project_id").cast("long").alias("project_id"),
        col("permission").alias("permission"),
        col("holder_type").alias("holder_type"),
        col("holder_value").alias("holder_value"),
    )
