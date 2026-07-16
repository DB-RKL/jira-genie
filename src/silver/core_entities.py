"""Silver layer: core Jira entities mapped to Fivetran-parity table names.

Reads from `rubjit_jira.bronze.*` (Lakeflow Connect Jira connector output)
and emits canonical Fivetran-style normalized tables. Bronze column names follow
the Jira REST API; if first sync reveals deviations, adjust the SELECT lists below.
"""

import dlt
from pyspark.sql import functions as F

BRONZE = "rubjit_jira.bronze"


@dlt.table(
    name="issue",
    comment="Fivetran-parity issue (core fields only; custom/historical fields live in issue_field_history).",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
@dlt.expect("unique_id", "id IS NOT NULL")
def issue():
    src = spark.read.table(f"{BRONZE}.issues")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("string").alias("id"),
        col("key").alias("issue_key"),
        col("project_id").cast("long").alias("project_id"),
        col("issue_type_id").cast("long").alias("issue_type_id"),
        col("summary").alias("summary"),
        col("description").alias("description"),
        col("priority_id").cast("long").alias("priority_id"),
        col("status_id").cast("long").alias("status_id"),
        col("resolution_id").cast("long").alias("resolution_id"),
        col("reporter_account_id").alias("reporter_id"),
        col("assignee_account_id").alias("assignee_id"),
        col("creator_account_id").alias("creator_id"),
        col("parent_id").cast("string").alias("parent_id"),
        col("created").cast("timestamp").alias("created_at"),
        col("updated").cast("timestamp").alias("updated_at"),
        col("resolved").cast("timestamp").alias("resolved_at"),
        col("due_date").cast("date").alias("due_date"),
        col("environment").alias("environment"),
        col("labels").alias("labels"),
        col("story_points").cast("double").alias("story_points"),
        col("original_estimate_seconds").cast("long").alias("original_estimate_seconds"),
        col("remaining_estimate_seconds").cast("long").alias("remaining_estimate_seconds"),
        col("time_spent_seconds").cast("long").alias("time_spent_seconds"),
        col("watch_count").cast("int").alias("watch_count"),
        col("vote_count").cast("int").alias("vote_count"),
    )


@dlt.table(name="issue_comment", comment="Comments on issues.")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def issue_comment():
    src = spark.read.table(f"{BRONZE}.issue_comments")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("string").alias("id"),
        col("issue_id").cast("string").alias("issue_id"),
        col("author_account_id").alias("author_id"),
        col("update_author_account_id").alias("update_author_id"),
        col("body").alias("body"),
        col("created").cast("timestamp").alias("created_at"),
        col("updated").cast("timestamp").alias("updated_at"),
    )


@dlt.table(name="issue_type", comment="Available issue types (Bug, Task, Story, Epic, ...).")
def issue_type():
    src = spark.read.table(f"{BRONZE}.issue_types")
    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        F.col("description").alias("description"),
        F.col("icon_url").alias("icon_url"),
        F.col("subtask").cast("boolean").alias("is_subtask"),
    )


@dlt.table(name="project", comment="Jira projects.")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def project():
    src = spark.read.table(f"{BRONZE}.projects")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        col("key").alias("project_key"),
        col("name").alias("name"),
        col("description").alias("description"),
        col("project_category_id").cast("long").alias("project_category_id"),
        col("project_type_key").alias("project_type_key"),
        col("lead_account_id").alias("lead_id"),
        col("url").alias("url"),
        col("style").alias("style"),
        col("archived").cast("boolean").alias("is_archived"),
    )


@dlt.table(name="project_category", comment="Project categories.")
def project_category():
    src = spark.read.table(f"{BRONZE}.project_categories")
    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        F.col("description").alias("description"),
    )


@dlt.table(name="project_role", comment="Available project roles.")
def project_role():
    src = spark.read.table(f"{BRONZE}.project_roles")
    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        F.col("description").alias("description"),
    )


@dlt.table(name="project_role_actor", comment="User/group assignments to project roles.")
def project_role_actor():
    src = spark.read.table(f"{BRONZE}.project_role_actor")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        col("project_id").cast("long").alias("project_id"),
        col("role_id").cast("long").alias("role_id"),
        col("actor_id").alias("actor_id"),
        col("actor_type").alias("actor_type"),
        col("actor_name").alias("actor_name"),
    )


@dlt.table(name="user", comment="Jira users.")
@dlt.expect_or_drop("valid_id", "account_id IS NOT NULL")
def user():
    src = spark.read.table(f"{BRONZE}.users")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("account_id").alias("account_id"),
        col("display_name").alias("display_name"),
        col("email_address").alias("email"),
        col("active").cast("boolean").alias("is_active"),
        col("account_type").alias("account_type"),
        col("locale").alias("locale"),
        col("time_zone").alias("time_zone"),
    )


@dlt.table(name="status", comment="Status lookup.")
def status():
    src = spark.read.table(f"{BRONZE}.status")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        col("name").alias("name"),
        col("description").alias("description"),
        col("status_category_id").cast("long").alias("status_category_id"),
        col("icon_url").alias("icon_url"),
    )


@dlt.table(name="status_category", comment="Status category lookup (To Do / In Progress / Done).")
def status_category():
    src = spark.read.table(f"{BRONZE}.status_category")
    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("key").alias("category_key"),
        F.col("name").alias("name"),
        F.col("color_name").alias("color_name"),
    )


@dlt.table(name="priority", comment="Priority lookup.")
def priority():
    src = spark.read.table(f"{BRONZE}.priority")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        col("name").alias("name"),
        col("description").alias("description"),
        col("status_color").alias("color"),
        col("icon_url").alias("icon_url"),
    )


@dlt.table(name="resolution", comment="Resolution lookup.")
def resolution():
    src = spark.read.table(f"{BRONZE}.resolutions")
    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        F.col("description").alias("description"),
    )
