"""Silver layer: core Jira entities mapped to canonical delivery table names.

Reads from the bronze layer configured in config/pipeline.yaml (pipeline configuration)
and emits normalized canonical tables. Column names are mapped from the
Lakeflow Connect Jira connector (camelCase REST fields) with fallbacks for legacy shapes.
"""

import dlt
from pyspark.sql import functions as F

from layer_config import bronze_fqn, pick


@dlt.table(
    name="issue",
    comment="Canonical issue entity (core fields only; custom/historical fields live in issue_field_history).",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_fail("issue_id_not_null", "id IS NOT NULL")
def issue():
    src = spark.read.table(bronze_fqn("issues"))
    projects = spark.read.table(bronze_fqn("projects"))
    statuses = spark.read.table(bronze_fqn("status"))
    priorities = spark.read.table(bronze_fqn("priority"))
    issue_types = spark.read.table(bronze_fqn("issue_types"))
    resolutions = spark.read.table(bronze_fqn("resolutions"))
    cols = set(src.columns)

    def icol(*names, default=None):
        for name in names:
            if name in cols:
                return F.col(f"i.{name}")
        return F.lit(default)

    return (
        src.alias("i")
        .join(projects.alias("p"), icol("projectKey", "project_key") == F.col("p.key"), "left")
        .join(statuses.alias("s"), icol("status") == F.col("s.name"), "left")
        .join(
            priorities.alias("pr"),
            (icol("priorityId", "priority_id").cast("string") == F.col("pr.id").cast("string"))
            | (icol("priority") == F.col("pr.name")),
            "left",
        )
        .join(issue_types.alias("it"), icol("issueType", "issue_type") == F.col("it.name"), "left")
        .join(resolutions.alias("r"), icol("resolution") == F.col("r.name"), "left")
        .select(
            F.col("i.id").cast("string").alias("id"),
            icol("key", "issue_key").alias("issue_key"),
            F.col("p.id").cast("long").alias("project_id"),
            F.col("it.id").cast("long").alias("issue_type_id"),
            icol("summary").alias("summary"),
            icol("description").alias("description"),
            F.col("pr.id").cast("long").alias("priority_id"),
            F.col("s.id").cast("long").alias("status_id"),
            F.col("r.id").cast("long").alias("resolution_id"),
            icol("reporter", "reporter_account_id", "reporter_id").alias("reporter_id"),
            icol("assignee", "assignee_account_id", "assignee_id").alias("assignee_id"),
            icol("creator", "creator_account_id", "creator_id").alias("creator_id"),
            icol("parent_id").cast("string").alias("parent_id"),
            icol("created", "created_at").cast("timestamp").alias("created_at"),
            icol("updated", "updated_at").cast("timestamp").alias("updated_at"),
            icol("resolutionDate", "resolutiondate", "resolved", "resolved_at").cast("timestamp").alias("resolved_at"),
            icol("due_date").cast("date").alias("due_date"),
            icol("environment").alias("environment"),
            icol("labels").alias("labels"),
            icol("story_points").cast("double").alias("story_points"),
            icol("original_estimate_seconds").cast("long").alias("original_estimate_seconds"),
            icol("remaining_estimate_seconds").cast("long").alias("remaining_estimate_seconds"),
            icol("time_spent_seconds").cast("long").alias("time_spent_seconds"),
            icol("watch_count").cast("int").alias("watch_count"),
            icol("vote_count").cast("int").alias("vote_count"),
        )
    )


@dlt.table(name="issue_comment", comment="Comments on issues.")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def issue_comment():
    src = spark.read.table(bronze_fqn("issue_comments"))
    cols = set(src.columns)

    return src.select(
        F.col("id").cast("string").alias("id"),
        pick(cols, "issue_id", "issueId").cast("string").alias("issue_id"),
        pick(cols, "author_account_id", "author").alias("author_id"),
        pick(cols, "update_author_account_id", "update_author").alias("update_author_id"),
        pick(cols, "body").alias("body"),
        pick(cols, "created", "created_at").cast("timestamp").alias("created_at"),
        pick(cols, "updated", "updated_at").cast("timestamp").alias("updated_at"),
    )


@dlt.table(name="issue_type", comment="Available issue types (Bug, Task, Story, Epic, ...).")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def issue_type():
    src = spark.read.table(bronze_fqn("issue_types"))
    cols = set(src.columns)

    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        pick(cols, "description").alias("description"),
        pick(cols, "icon_url").alias("icon_url"),
        pick(cols, "subtask", "is_subtask").cast("boolean").alias("is_subtask"),
    )


@dlt.table(name="project", comment="Jira projects.")
@dlt.expect_or_fail("project_id_not_null", "id IS NOT NULL")
def project():
    src = spark.read.table(bronze_fqn("projects"))
    cols = set(src.columns)

    return src.select(
        F.col("id").cast("long").alias("id"),
        pick(cols, "key", "project_key").alias("project_key"),
        pick(cols, "name").alias("name"),
        pick(cols, "description").alias("description"),
        pick(cols, "project_category_id", "projectCategory").cast("long").alias("project_category_id"),
        pick(cols, "project_type_key", "projectTypeKey").alias("project_type_key"),
        pick(cols, "lead_account_id", "lead").alias("lead_id"),
        pick(cols, "url").alias("url"),
        pick(cols, "style").alias("style"),
        pick(cols, "archived", "is_archived").cast("boolean").alias("is_archived"),
    )


@dlt.table(name="project_category", comment="Project categories.")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def project_category():
    src = spark.read.table(bronze_fqn("project_categories"))
    cols = set(src.columns)

    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        pick(cols, "description").alias("description"),
    )


@dlt.table(name="project_role", comment="Available project roles.")
def project_role():
    src = spark.read.table(bronze_fqn("project_roles"))
    cols = set(src.columns)

    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        pick(cols, "description").alias("description"),
    )


@dlt.table(name="project_role_actor", comment="User/group assignments to project roles.")
def project_role_actor():
    src = spark.read.table(bronze_fqn("project_role_actor"))
    cols = set(src.columns)

    return src.select(
        pick(cols, "project_id", "projectId").cast("long").alias("project_id"),
        pick(cols, "role_id", "roleId").cast("long").alias("role_id"),
        pick(cols, "actor_id", "actorId").alias("actor_id"),
        pick(cols, "actor_type", "actorType").alias("actor_type"),
        pick(cols, "actor_name", "actorName").alias("actor_name"),
    )


@dlt.table(name="user", comment="Jira users.")
@dlt.expect_or_fail("account_id_not_null", "account_id IS NOT NULL")
def user():
    src = spark.read.table(bronze_fqn("users"))
    cols = set(src.columns)

    return src.select(
        pick(cols, "account_id", "id").alias("account_id"),
        pick(cols, "display_name", "displayName").alias("display_name"),
        pick(cols, "email_address", "email", "emailId").alias("email"),
        pick(cols, "active", "is_active").cast("boolean").alias("is_active"),
        pick(cols, "account_type", "accountType").alias("account_type"),
        pick(cols, "locale").alias("locale"),
        pick(cols, "time_zone", "timeZone").alias("time_zone"),
    )


@dlt.table(name="status", comment="Status lookup.")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def status():
    src = spark.read.table(bronze_fqn("status"))
    categories = spark.read.table(bronze_fqn("status_category"))
    cols = set(src.columns)

    def scol(*names, default=None):
        for name in names:
            if name in cols:
                return F.col(f"s.{name}")
        return F.lit(default)

    return (
        src.alias("s")
        .join(
            categories.alias("c"),
            scol("status_category_id", "status_category") == F.col("c.name"),
            "left",
        )
        .select(
            F.col("s.id").cast("long").alias("id"),
            scol("name").alias("name"),
            scol("description").alias("description"),
            F.col("c.id").cast("long").alias("status_category_id"),
            scol("icon_url").alias("icon_url"),
        )
    )


@dlt.table(name="status_category", comment="Status category lookup (To Do / In Progress / Done).")
def status_category():
    src = spark.read.table(bronze_fqn("status_category"))
    cols = set(src.columns)
    name_col = pick(cols, "name")

    # Prefer Jira's canonical statuscategory key (new / indeterminate / done),
    # which is stable across locales; only fall back to mapping the English
    # display name when the source does not expose a key column.
    source_key = pick(cols, "key", "category_key")
    category_key = (
        F.when(source_key.isNotNull(), source_key)
        .when(name_col == "To Do", "new")
        .when(name_col == "In Progress", "indeterminate")
        .when(name_col == "Done", "done")
        .otherwise(F.lower(name_col))
    )

    return src.select(
        F.col("id").cast("long").alias("id"),
        category_key.alias("category_key"),
        name_col.alias("name"),
        pick(cols, "color_name").alias("color_name"),
    )


@dlt.table(name="priority", comment="Priority lookup.")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def priority():
    src = spark.read.table(bronze_fqn("priority"))
    cols = set(src.columns)

    return src.select(
        F.col("id").cast("long").alias("id"),
        pick(cols, "name").alias("name"),
        pick(cols, "description").alias("description"),
        pick(cols, "status_color", "color").alias("color"),
        pick(cols, "icon_url").alias("icon_url"),
    )


@dlt.table(name="resolution", comment="Resolution lookup.")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def resolution():
    src = spark.read.table(bronze_fqn("resolutions"))
    cols = set(src.columns)

    return src.select(
        F.col("id").cast("long").alias("id"),
        F.col("name").alias("name"),
        pick(cols, "description").alias("description"),
    )
