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

BRONZE = "rubjit_jira.bronze"


@dlt.table(name="issue_link", comment="Directed links between issues.")
def issue_link():
    src = spark.read.table(f"{BRONZE}.issue_links")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("string").alias("id"),
        col("source_issue_id").cast("string").alias("source_issue_id"),
        col("target_issue_id").cast("string").alias("target_issue_id"),
        col("link_type_id").cast("long").alias("link_type_id"),
    )


@dlt.table(name="issue_link_type", comment="Dedup'd link type lookup (blocks, relates to, etc.)")
def issue_link_type():
    src = spark.read.table(f"{BRONZE}.issue_links")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return (
        src.select(
            col("link_type_id").cast("long").alias("id"),
            col("link_type_name").alias("name"),
            col("inward").alias("inward_description"),
            col("outward").alias("outward_description"),
        )
        .where(F.col("id").isNotNull())
        .distinct()
    )


@dlt.table(
    name="sprint_issue",
    comment="Many-to-many bridge between sprints and issues. Derived from issues.sprint_ids array.",
)
def sprint_issue():
    issues = spark.read.table(f"{BRONZE}.issues")
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
def epic_issue():
    issues = spark.read.table(f"{BRONZE}.issues").alias("c")
    issue_types = spark.read.table(f"{BRONZE}.issue_types").alias("t")
    parents = spark.read.table(f"{BRONZE}.issues").alias("p")

    return (
        issues
        .join(parents, F.col("c.parent_id") == F.col("p.id"), "inner")
        .join(issue_types, F.col("p.issue_type_id") == F.col("t.id"), "inner")
        .where(F.lower(F.col("t.name")) == "epic")
        .select(
            F.col("p.id").cast("string").alias("epic_id"),
            F.col("c.id").cast("string").alias("issue_id"),
        )
        .distinct()
    )


@dlt.table(name="component", comment="Components (deduped from project_components).")
def component():
    src = spark.read.table(f"{BRONZE}.project_components")
    cols = set(src.columns)

    def col(name, default=None):
        return F.col(name) if name in cols else F.lit(default)

    return src.select(
        F.col("id").cast("long").alias("id"),
        col("name").alias("name"),
        col("description").alias("description"),
        col("lead_account_id").alias("lead_id"),
        col("project_id").cast("long").alias("project_id"),
        col("assignee_type").alias("assignee_type"),
    )


@dlt.table(
    name="issue_component",
    comment="Bridge issue <-> component. Derived from issues.components array if present.",
)
def issue_component():
    issues = spark.read.table(f"{BRONZE}.issues")
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
def version():
    src = spark.read.table(f"{BRONZE}.version")
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
    src = spark.read.table(f"{BRONZE}.version")
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
    issues = spark.read.table(f"{BRONZE}.issues")
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
