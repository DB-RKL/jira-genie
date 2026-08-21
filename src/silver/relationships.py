"""Silver layer: relationships and bridge tables.

Includes:
- issue_link + issue_link_type (split from bronze issue_links)
- sprint_issue (derived from bronze issues -> the sprint custom field)
- epic_issue (derived from bronze issues -> parent_id where parent type is Epic)
- issue_component, component (split from bronze project_components)
- issue_version, project_version (derived from bronze version + issues fix_versions)
"""

import dlt
from pyspark.sql import functions as F

from layer_config import bronze_fqn, conf_value, pick

@dlt.table(name="issue_link", comment="Directed links between issues.")
@dlt.expect_or_drop("valid_endpoints", "source_issue_id IS NOT NULL AND target_issue_id IS NOT NULL")
def issue_link():
    src = spark.read.table(bronze_fqn("issue_links"))
    cols = set(src.columns)

    source_id = pick(cols, "source_issue_id", "issue_id")
    target_id = pick(cols, "target_issue_id", "related_issue_id")
    link_type_id = pick(cols, "link_type_id")

    return src.select(
        F.concat_ws("-", source_id, target_id, pick(cols, "relationship", "link_type_name")).alias("id"),
        source_id.cast("string").alias("source_issue_id"),
        target_id.cast("string").alias("target_issue_id"),
        link_type_id.cast("long").alias("link_type_id"),
    )


@dlt.table(name="issue_link_type", comment="Dedup'd link type lookup (blocks, relates to, etc.)")
def issue_link_type():
    src = spark.read.table(bronze_fqn("issue_links"))
    cols = set(src.columns)

    link_type_id = pick(cols, "link_type_id")
    link_type_name = pick(cols, "link_type_name", "relationship")

    return (
        src.select(
            link_type_id.cast("long").alias("id"),
            link_type_name.alias("name"),
            pick(cols, "inward", "inward_description").alias("inward_description"),
            pick(cols, "outward", "outward_description").alias("outward_description"),
        )
        .where(F.col("name").isNotNull())
        .distinct()
    )


@dlt.table(
    name="sprint_issue",
    comment="Many-to-many bridge between sprints and issues. Derived from issues.sprint_ids array.",
)
@dlt.expect_or_drop("valid_keys", "sprint_id IS NOT NULL AND issue_id IS NOT NULL")
def sprint_issue():
    issues = spark.read.table(bronze_fqn("issues"))
    cols = set(issues.columns)
    sprint_col = "sprint_ids" if "sprint_ids" in cols else ("sprints" if "sprints" in cols else None)
    if sprint_col is None:
        return issues.select(
            F.lit(None).cast("long").alias("sprint_id"),
            F.lit(None).cast("string").alias("issue_id"),
        ).where(F.lit(False))

    return (
        issues
        .select(
            F.col("id").cast("string").alias("issue_id"),
            F.col(sprint_col).alias("sprint_ids"),
        )
        .withColumn("sprint_id", F.explode_outer("sprint_ids"))
        .where(F.col("sprint_id").isNotNull())
        .select(F.col("sprint_id").cast("long").alias("sprint_id"), "issue_id")
        .distinct()
    )


@dlt.table(
    name="epic_issue",
    comment="Bridge linking child issues to their epic. Derived from issues.parent_id where parent type = Epic.",
)
@dlt.expect_or_drop("valid_keys", "epic_id IS NOT NULL AND issue_id IS NOT NULL")
def epic_issue():
    issues = spark.read.table(bronze_fqn("issues"))
    cols = set(issues.columns)
    parent_col = next((name for name in ("parent_id", "parentId", "parent") if name in cols), None)
    if parent_col is None:
        return issues.select(
            F.lit(None).cast("string").alias("epic_id"),
            F.lit(None).cast("string").alias("issue_id"),
        ).where(F.lit(False))

    issue_types = spark.read.table(bronze_fqn("issue_types")).alias("t")
    parents = spark.read.table(bronze_fqn("issues")).alias("p")

    # Configurable so instances that renamed/localized the Epic issue type still resolve.
    epic_type_name = conf_value("epic_issue_type_name", "epic").lower()

    return (
        issues.alias("c")
        .join(parents, F.col(f"c.{parent_col}") == F.col("p.id"), "inner")
        .join(issue_types, F.col("p.issue_type_id") == F.col("t.id"), "inner")
        .where(F.lower(F.col("t.name")) == epic_type_name)
        .select(
            F.col("p.id").cast("string").alias("epic_id"),
            F.col("c.id").cast("string").alias("issue_id"),
        )
        .distinct()
    )


@dlt.table(name="component", comment="Components (deduped from project_components).")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def component():
    src = spark.read.table(bronze_fqn("project_components"))
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        pick(cols, "name").alias("name"),
        pick(cols, "description").alias("description"),
        pick(cols, "lead_account_id", "lead").alias("lead_id"),
        pick(cols, "project_id", "projectId").cast("long").alias("project_id"),
        pick(cols, "assignee_type", "assigneeType").alias("assignee_type"),
    )


@dlt.table(
    name="issue_component",
    comment="Bridge issue <-> component. Derived from issues.components array if present.",
)
def issue_component():
    issues = spark.read.table(bronze_fqn("issues"))
    cols = set(issues.columns)
    comp_col = "component_ids" if "component_ids" in cols else ("components" if "components" in cols else None)
    if comp_col is None:
        return issues.select(
            F.lit(None).cast("string").alias("issue_id"),
            F.lit(None).cast("long").alias("component_id"),
        ).where(F.lit(False))

    return (
        issues
        .select(F.col("id").cast("string").alias("issue_id"), F.col(comp_col).alias("components"))
        .withColumn("component_id", F.explode_outer("components"))
        .where(F.col("component_id").isNotNull())
        .select("issue_id", F.col("component_id").cast("long").alias("component_id"))
        .distinct()
    )


@dlt.table(name="version", comment="Versions (deduped from version table).")
@dlt.expect_or_drop("valid_id", "id IS NOT NULL")
def version():
    src = spark.read.table(bronze_fqn("version"))
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        col("name").alias("name"),
        col("description").alias("description"),
        col("archived").cast("boolean").alias("is_archived"),
        col("released").cast("boolean").alias("is_released"),
        col("release_date").cast("date").alias("release_date"),
        col("start_date").cast("date").alias("start_date"),
    )


@dlt.table(name="project_version", comment="Bridge project <-> version.")
def project_version():
    src = spark.read.table(bronze_fqn("version"))
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        col("project_id").cast("long").alias("project_id"),
        F.col("id").cast("long").alias("version_id"),
    ).distinct()


@dlt.table(
    name="issue_version",
    comment="Bridge issue <-> fix version. Derived from issues.fix_version_ids if present.",
)
def issue_version():
    issues = spark.read.table(bronze_fqn("issues"))
    cols = set(issues.columns)
    ver_col = (
        "fix_version_ids" if "fix_version_ids" in cols
        else ("fix_versions" if "fix_versions" in cols else None)
    )
    if ver_col is None:
        return issues.select(
            F.lit(None).cast("string").alias("issue_id"),
            F.lit(None).cast("long").alias("version_id"),
        ).where(F.lit(False))

    return (
        issues
        .select(F.col("id").cast("string").alias("issue_id"), F.col(ver_col).alias("versions"))
        .withColumn("version_id", F.explode_outer("versions"))
        .where(F.col("version_id").isNotNull())
        .select("issue_id", F.col("version_id").cast("long").alias("version_id"))
        .distinct()
    )
