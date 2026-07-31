"""Generate the Lakeview dashboard JSON for Jira analytics (semantic layer).

Datasets query Unity Catalog metric views with MEASURE(). The checked-in template
at src/dashboard/jira_analytics.lvdash.json uses {dashboard_catalog} and
{dashboard_schema} placeholders; sync_config.sh patches dashboards/jira_analytics.lvdash.json.

Regenerate template:  python scripts/build_assets.py --regenerate-dashboard
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "src" / "dashboard" / "jira_analytics.lvdash.json"

COLOR_PRIMARY = "#1B5E20"
PALETTE = ["#1B5E20", "#00A972", "#FFAB00", "#FF3621", "#8BCAE7", "#AB4057", "#919191"]

_id_counter = 0


def hid(label: str = "") -> str:
    """Deterministic widget/page id (stable across regenerations)."""
    global _id_counter
    _id_counter += 1
    seed = f"jira-analytics:{label}:{_id_counter}"
    return hashlib.sha256(seed.encode()).hexdigest()[:8]


def build_dashboard(
    output_path: Path | None = None,
    metrics_catalog: str | None = None,
    metrics_schema: str | None = None,
) -> Path:
    """Build dashboard JSON with fully qualified metric view references."""
    global _id_counter
    _id_counter = 0
    output_path = output_path or DEFAULT_OUTPUT
    metrics_catalog = metrics_catalog or "catalog"
    metrics_schema = metrics_schema or "metrics"

    def mv(view: str) -> str:
        return view

    datasets: list[dict] = []

    def add_dataset(name: str, sql: str, display: str) -> str:
        datasets.append({"name": name, "displayName": display, "queryLines": [sql]})
        return name

    DS_VELOCITY = add_dataset(
        "ds_velocity",
        (
            "SELECT `Sprint` AS sprint_name, `Sprint State` AS state, "
            "`Project Key` AS project_key, `Start Date` AS start_date, "
            "`Complete Date` AS complete_date, "
            "MEASURE(`Points Planned`) AS points_in_sprint, "
            "MEASURE(`Points Completed`) AS points_completed, "
            "MEASURE(`Avg Completion Ratio`) AS completion_ratio, "
            "MEASURE(`Issues Planned`) AS issues_in_sprint, "
            "MEASURE(`Issues Completed`) AS issues_completed "
            f"FROM {mv('metric_sprint_velocity')} "
            "GROUP BY `Sprint`, `Sprint State`, `Project Key`, `Start Date`, `Complete Date`"
        ),
        "Sprint velocity",
    )
    DS_VELOCITY_RECENT = add_dataset(
        "ds_velocity_recent",
        (
            "SELECT `Sprint` AS sprint_name, `Sprint State` AS state, "
            "`Project Key` AS project_key, `Start Date` AS start_date, "
            "`Complete Date` AS complete_date, "
            "MEASURE(`Points Planned`) AS points_in_sprint, "
            "MEASURE(`Points Completed`) AS points_completed, "
            "MEASURE(`Avg Completion Ratio`) AS completion_ratio, "
            "MEASURE(`Issues Planned`) AS issues_in_sprint, "
            "MEASURE(`Issues Completed`) AS issues_completed "
            f"FROM {mv('metric_sprint_velocity')} "
            "WHERE `Sprint State` = 'closed' AND `Complete Date` IS NOT NULL "
            "GROUP BY `Sprint`, `Sprint State`, `Project Key`, `Start Date`, `Complete Date` "
            "ORDER BY `Complete Date` DESC LIMIT 12"
        ),
        "Sprint velocity (last 12 closed)",
    )
    issue_dims = (
        "`Issue Key` AS issue_key, `Summary` AS summary, `Project Key` AS project_key, "
        "`Assignee` AS assignee_name, `Priority` AS priority, `Age (days)` AS age_days, "
        "`Status Category` AS status_category, `Issue Type` AS issue_type, "
        "`Is Resolved` AS is_resolved, `Cycle Time (days)` AS cycle_time_days, "
        "`Lead Time (days)` AS lead_time_days, `Age Bucket` AS age_bucket"
    )
    DS_ISSUE = add_dataset(
        "ds_issue",
        f"SELECT {issue_dims} FROM {mv('metric_issue')}",
        "Issue fact",
    )
    DS_ISSUE_OPEN = add_dataset(
        "ds_issue_open",
        f"SELECT {issue_dims} FROM {mv('metric_issue')} WHERE NOT `Is Resolved`",
        "Open issues",
    )
    DS_ISSUE_RESOLVED_180 = add_dataset(
        "ds_issue_resolved_180",
        (
            f"SELECT {issue_dims} FROM {mv('metric_issue')} "
            "WHERE `Is Resolved` AND `Resolved Date` >= CURRENT_DATE() - INTERVAL 180 DAYS"
        ),
        "Resolved issues (last 180 days)",
    )
    DS_PROJECT_HEALTH = add_dataset(
        "ds_project_health",
        (
            "SELECT `Project Key` AS project_key, `Project Name` AS project_name, "
            "MEASURE(`Open Issues`) AS open_issues, "
            "MEASURE(`Open Critical`) AS open_critical, "
            "MEASURE(`Stale Open`) AS stale_open, "
            "MEASURE(`Avg Cycle Time (days)`) AS avg_cycle_time_days, "
            "MEASURE(`Resolved Issues (30d)`) AS resolved_last_30d, "
            "MEASURE(`Created Issues (30d)`) AS created_last_30d "
            f"FROM {mv('metric_project_health')} "
            "GROUP BY `Project Key`, `Project Name`"
        ),
        "Project health",
    )
    DS_ASSIGNEE_LOAD = add_dataset(
        "ds_assignee_load",
        (
            "SELECT `Assignee` AS assignee_name, `Project Key` AS project_key, "
            "`Priority` AS priority, MEASURE(`Open Issues`) AS open_issues "
            f"FROM {mv('metric_assignee_load')} "
            "GROUP BY `Assignee`, `Project Key`, `Priority`"
        ),
        "Assignee load",
    )
    DS_TEAM_PROD = add_dataset(
        "ds_team_prod",
        (
            "SELECT `Assignee` AS assignee_name, "
            "MEASURE(`Resolved (30d)`) AS resolved_30d, "
            "MEASURE(`Resolved (90d)`) AS resolved_90d, "
            "MEASURE(`Open Now`) AS open_now, "
            "MEASURE(`Open Critical`) AS open_critical, "
            "MEASURE(`Avg Cycle Time (days)`) AS avg_cycle_time_days, "
            "MEASURE(`Avg Lead Time (days)`) AS avg_lead_time_days "
            f"FROM {mv('metric_team_productivity')} GROUP BY `Assignee`"
        ),
        "Team productivity",
    )
    DS_TIME_IN_STATUS = add_dataset(
        "ds_time_in_status",
        (
            "SELECT `Project Key` AS project_key, `Status` AS status_name, "
            "MEASURE(`P50 Duration (hours)`) AS p50_hours, "
            "MEASURE(`P90 Duration (hours)`) AS p90_hours, "
            "MEASURE(`Observations`) AS observations "
            f"FROM {mv('metric_time_in_status')} GROUP BY `Project Key`, `Status`"
        ),
        "Time in status",
    )

    def counter(dataset: str, expression: str, title: str, value_alias: str = "value"):
        return {
            "name": hid(f"counter:{title}"),
            "queries": [{
                "name": "main",
                "query": {
                    "datasetName": dataset,
                    "fields": [{"name": value_alias, "expression": expression}],
                    "disaggregated": True,
                },
            }],
            "spec": {
                "version": 2,
                "widgetType": "counter",
                "encodings": {
                    "value": {
                        "fieldName": value_alias,
                        "displayName": title,
                        "format": {
                            "type": "number-plain",
                            "abbreviation": "auto",
                            "decimalPlaces": {"type": "max", "places": 1},
                        },
                    }
                },
                "frame": {"showTitle": True, "title": title},
            },
        }

    def bar(dataset, x_field, x_expr, y_field, y_expr, title, **kwargs):
        color_field = kwargs.get("color_field")
        color_expr = kwargs.get("color_expr")
        sort = kwargs.get("sort")
        stacked = kwargs.get("stacked", False)
        fields = [{"name": x_field, "expression": x_expr}, {"name": y_field, "expression": y_expr}]
        encodings = {
            "x": {
                "fieldName": x_field,
                "scale": {"type": "categorical", **({"sort": {"by": sort}} if sort else {})},
                "displayName": kwargs.get("x_display") or x_field,
            },
            "y": {"fieldName": y_field, "scale": {"type": "quantitative"}, "displayName": kwargs.get("y_display") or y_field},
            "label": {"show": True},
        }
        if color_field and color_expr:
            fields.append({"name": color_field, "expression": color_expr})
            encodings["color"] = {"fieldName": color_field, "scale": {"type": "categorical"}, "displayName": color_field}
            if stacked:
                encodings["y"]["scale"]["stack"] = "stack"
        return {
            "name": hid(f"bar:{title}"),
            "queries": [{"name": "main", "query": {"datasetName": dataset, "fields": fields, "disaggregated": False}}],
            "spec": {"version": 3, "widgetType": "bar", "encodings": encodings,
                     "frame": {"showTitle": True, "title": title}, "mark": {"colors": PALETTE}},
        }

    def line(dataset, x_field, x_expr, y_field, y_expr, title, **kwargs):
        return {
            "name": hid(f"line:{title}"),
            "queries": [{"name": "main", "query": {
                "datasetName": dataset,
                "fields": [{"name": x_field, "expression": x_expr}, {"name": y_field, "expression": y_expr}],
                "disaggregated": False,
            }}],
            "spec": {
                "version": 3, "widgetType": "line",
                "encodings": {
                    "x": {"fieldName": x_field, "scale": {"type": "categorical"}, "displayName": kwargs.get("x_display") or x_field},
                    "y": {"fieldName": y_field, "scale": {"type": "quantitative"}, "displayName": kwargs.get("y_display") or y_field},
                },
                "frame": {"showTitle": True, "title": title}, "mark": {"colors": [COLOR_PRIMARY]},
            },
        }

    def histogram(dataset, x_field, x_expr, y_field, y_expr, title, **kwargs):
        return {
            "name": hid(f"histogram:{title}"),
            "queries": [{"name": "main", "query": {
                "datasetName": dataset,
                "fields": [{"name": x_field, "expression": x_expr}, {"name": y_field, "expression": y_expr}],
                "disaggregated": False,
            }}],
            "spec": {
                "version": 3, "widgetType": "histogram",
                "encodings": {
                    "x": {"fieldName": x_field, "scale": {"type": "categorical", "sort": {"by": "natural-order"}},
                          "displayName": kwargs.get("x_display") or x_field},
                    "y": {"fieldName": y_field, "scale": {"type": "quantitative"}, "displayName": "Issues"},
                },
                "frame": {"showTitle": True, "title": title}, "mark": {"colors": [COLOR_PRIMARY]},
            },
        }

    def pie(dataset, angle_field, angle_expr, color_field, color_expr, title):
        return {
            "name": hid(f"pie:{title}"),
            "queries": [{"name": "main", "query": {
                "datasetName": dataset,
                "fields": [{"name": angle_field, "expression": angle_expr}, {"name": color_field, "expression": color_expr}],
                "disaggregated": False,
            }}],
            "spec": {
                "version": 3, "widgetType": "pie",
                "encodings": {
                    "angle": {"fieldName": angle_field, "scale": {"type": "quantitative"}, "displayName": angle_field},
                    "color": {"fieldName": color_field, "scale": {"type": "categorical"}, "displayName": color_field},
                },
                "frame": {"showTitle": True, "title": title},
            },
        }

    def scatter(dataset, x_field, x_expr, y_field, y_expr, color_field, color_expr, title, **kwargs):
        return {
            "name": hid(f"scatter:{title}"),
            "queries": [{"name": "main", "query": {
                "datasetName": dataset,
                "fields": [
                    {"name": x_field, "expression": x_expr},
                    {"name": y_field, "expression": y_expr},
                    {"name": color_field, "expression": color_expr},
                ],
                "disaggregated": True,
            }}],
            "spec": {
                "version": 3, "widgetType": "scatter",
                "encodings": {
                    "x": {"fieldName": x_field, "scale": {"type": "quantitative"}, "displayName": kwargs.get("x_display") or x_field},
                    "y": {"fieldName": y_field, "scale": {"type": "quantitative"}, "displayName": kwargs.get("y_display") or y_field},
                    "color": {"fieldName": color_field, "scale": {"type": "categorical"}, "displayName": color_field},
                },
                "frame": {"showTitle": True, "title": title},
            },
        }

    def heatmap(dataset, x_field, x_expr, y_field, y_expr, color_field, color_expr, title):
        return {
            "name": hid(f"heatmap:{title}"),
            "queries": [{"name": "main", "query": {
                "datasetName": dataset,
                "fields": [
                    {"name": x_field, "expression": x_expr},
                    {"name": y_field, "expression": y_expr},
                    {"name": color_field, "expression": color_expr},
                ],
                "disaggregated": False,
            }}],
            "spec": {
                "version": 3, "widgetType": "heatmap",
                "encodings": {
                    "x": {"fieldName": x_field, "scale": {"type": "categorical"}, "displayName": x_field},
                    "y": {"fieldName": y_field, "scale": {"type": "categorical"}, "displayName": y_field},
                    "color": {"fieldName": color_field, "scale": {"type": "quantitative"}, "displayName": color_field},
                },
                "frame": {"showTitle": True, "title": title},
            },
        }

    def table(dataset, columns, title):
        enc_cols = []
        for c in columns:
            enc = {
                "fieldName": c["name"], "type": c.get("type", "string"),
                "displayAs": c.get("displayAs", "string"), "title": c.get("title", c["name"]),
                "displayName": c.get("title", c["name"]),
            }
            if "numberFormat" in c:
                enc["numberFormat"] = c["numberFormat"]
                enc["alignContent"] = "right"
            enc_cols.append(enc)
        return {
            "name": hid(f"table:{title}"),
            "queries": [{"name": "main", "query": {
                "datasetName": dataset,
                "fields": [{"name": c["name"], "expression": c["expr"]} for c in columns],
                "disaggregated": True,
            }}],
            "spec": {"version": 1, "widgetType": "table", "encodings": {"columns": enc_cols},
                     "frame": {"showTitle": True, "title": title}},
        }

    def filter_widget(widget_type, field_name, display, ds_list):
        return {
            "name": hid(f"filter:{display}"),
            "queries": [
                {"name": f"{ds}_filter_{field_name}", "query": {
                    "datasetName": ds,
                    "fields": [{"name": field_name, "expression": f"`{field_name}`"}],
                    "disaggregated": False,
                }}
                for ds in ds_list
            ],
            "spec": {
                "version": 2, "widgetType": widget_type,
                "encodings": {"fields": [
                    {"fieldName": field_name, "displayName": display, "queryName": f"{ds}_filter_{field_name}"}
                    for ds in ds_list
                ]},
                "frame": {"showTitle": True, "title": display},
            },
        }

    def make_layout(items):
        return [{"widget": w, "position": {"x": x, "y": y, "width": ww, "height": hh}}
                for (w, x, y, ww, hh) in items]

    def offset_items(items, y_offset: int):
        return [(w, x, y + y_offset, ww, hh) for (w, x, y, ww, hh) in items]

    p1_items = [
        (counter(DS_VELOCITY, "COUNT_IF(`state` = 'active')", "Active sprints"), 0, 0, 1, 2),
        (counter(DS_VELOCITY_RECENT, "AVG(completion_ratio)", "Avg completion (last 12)"), 1, 0, 1, 2),
        (counter(DS_VELOCITY, "SUM(CASE WHEN complete_date >= CURRENT_DATE() - INTERVAL 30 DAYS THEN points_completed END)", "Points completed (30d)"), 2, 0, 1, 2),
        (counter(DS_VELOCITY_RECENT, "SUM(points_in_sprint - points_completed)", "Carryover points (last 12)"), 3, 0, 1, 2),
        (bar(DS_VELOCITY_RECENT, "sprint_name", "`sprint_name`", "points", "SUM(`points_in_sprint`)",
             "Points in sprint vs completed", color_field="metric", color_expr="'Planned'"), 0, 2, 3, 4),
        (line(DS_VELOCITY_RECENT, "sprint_name", "`sprint_name`", "ratio", "AVG(`completion_ratio`)", "Completion ratio trend"), 3, 2, 3, 4),
        (table(DS_VELOCITY, [
            {"name": "sprint_name", "expr": "`sprint_name`", "title": "Sprint"},
            {"name": "state", "expr": "`state`", "title": "State"},
            {"name": "start_date", "expr": "`start_date`", "title": "Start", "type": "datetime", "displayAs": "datetime"},
            {"name": "complete_date", "expr": "`complete_date`", "title": "Complete", "type": "datetime", "displayAs": "datetime"},
            {"name": "points_in_sprint", "expr": "`points_in_sprint`", "title": "Planned pts", "type": "float", "displayAs": "number", "numberFormat": "0,0.0"},
            {"name": "points_completed", "expr": "`points_completed`", "title": "Done pts", "type": "float", "displayAs": "number", "numberFormat": "0,0.0"},
            {"name": "completion_ratio", "expr": "`completion_ratio`", "title": "Completion %", "type": "float", "displayAs": "number", "numberFormat": "0.0%"},
            {"name": "issues_in_sprint", "expr": "`issues_in_sprint`", "title": "Issues", "type": "integer", "displayAs": "number", "numberFormat": "0"},
            {"name": "issues_completed", "expr": "`issues_completed`", "title": "Done", "type": "integer", "displayAs": "number", "numberFormat": "0"},
        ], "Sprint outcomes"), 0, 6, 6, 6),
    ]

    p2_items = [
        (counter(DS_ISSUE_RESOLVED_180, "PERCENTILE_APPROX(cycle_time_days, 0.5)", "Median cycle (days)"), 0, 0, 1, 2),
        (counter(DS_ISSUE_RESOLVED_180, "PERCENTILE_APPROX(lead_time_days, 0.5)", "Median lead (days)"), 1, 0, 1, 2),
        (counter(DS_ISSUE_OPEN, "COUNT_IF(age_days > 30)", "Open >30d"), 2, 0, 1, 2),
        (counter(DS_ISSUE_OPEN, "COUNT_IF(age_days > 30 AND priority IN ('Highest','Critical','Blocker'))", "Stale critical"), 3, 0, 1, 2),
        (histogram(DS_ISSUE_RESOLVED_180, "cycle_bucket",
                   "CASE WHEN cycle_time_days < 1 THEN '< 1d'"
                   " WHEN cycle_time_days < 3 THEN '1-3d'"
                   " WHEN cycle_time_days < 7 THEN '3-7d'"
                   " WHEN cycle_time_days < 14 THEN '7-14d'"
                   " WHEN cycle_time_days < 30 THEN '14-30d'"
                   " WHEN cycle_time_days < 60 THEN '30-60d'"
                   " WHEN cycle_time_days < 90 THEN '60-90d'"
                   " ELSE '90d+' END",
                   "count", "COUNT(*)", "Cycle time distribution (last 180d resolved)", x_display="Cycle bucket"), 0, 2, 3, 4),
        (bar(DS_ISSUE_OPEN, "age_bucket", "`age_bucket`", "count", "COUNT(*)", "Open issues by age bucket", sort="natural-order"), 3, 2, 3, 4),
        (table(DS_TIME_IN_STATUS, [
            {"name": "project_key", "expr": "`project_key`", "title": "Project"},
            {"name": "status_name", "expr": "`status_name`", "title": "Status"},
            {"name": "p50_hours", "expr": "`p50_hours`", "title": "P50 (h)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
            {"name": "p90_hours", "expr": "`p90_hours`", "title": "P90 (h)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
            {"name": "observations", "expr": "`observations`", "title": "Observations", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
        ], "Time in status (p50/p90 hours)"), 0, 6, 3, 6),
        (table(DS_ISSUE_OPEN, [
            {"name": "issue_key", "expr": "`issue_key`", "title": "Key"},
            {"name": "project_key", "expr": "`project_key`", "title": "Project"},
            {"name": "summary", "expr": "`summary`", "title": "Summary"},
            {"name": "assignee_name", "expr": "`assignee_name`", "title": "Assignee"},
            {"name": "priority", "expr": "`priority`", "title": "Priority"},
            {"name": "age_days", "expr": "`age_days`", "title": "Age (days)", "type": "integer", "displayAs": "number", "numberFormat": "0"},
        ], "Top 20 oldest open issues"), 3, 6, 3, 6),
    ]

    p3_items = [
        (counter(DS_PROJECT_HEALTH, "SUM(open_issues)", "Total open"), 0, 0, 1, 2),
        (counter(DS_PROJECT_HEALTH, "COUNT_IF(stale_open > 0)", "Projects w/ stale"), 1, 0, 1, 2),
        (counter(DS_PROJECT_HEALTH, "AVG(avg_cycle_time_days)", "Portfolio avg cycle (d)"), 2, 0, 1, 2),
        (counter(DS_PROJECT_HEALTH, "SUM(resolved_last_30d)", "Resolved (30d)"), 3, 0, 1, 2),
        (heatmap(DS_ISSUE, "project_key", "`project_key`", "status_category", "`status_category`", "count", "COUNT(*)", "Project x status category"), 0, 2, 4, 4),
        (pie(DS_ISSUE, "count", "COUNT(*)", "issue_type", "`issue_type`", "Issue type mix"), 4, 2, 2, 4),
        (bar(DS_ISSUE_OPEN, "project_key", "`project_key`", "count", "COUNT(*)", "Open issues by priority (top projects)",
             color_field="priority", color_expr="`priority`", sort="y-reversed", stacked=True), 0, 6, 6, 4),
        (table(DS_PROJECT_HEALTH, [
            {"name": "project_key", "expr": "`project_key`", "title": "Project"},
            {"name": "project_name", "expr": "`project_name`", "title": "Name"},
            {"name": "open_issues", "expr": "`open_issues`", "title": "Open", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "open_critical", "expr": "`open_critical`", "title": "Open critical", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "stale_open", "expr": "`stale_open`", "title": "Stale (>30d)", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "avg_cycle_time_days", "expr": "`avg_cycle_time_days`", "title": "Avg cycle (d)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
            {"name": "resolved_last_30d", "expr": "`resolved_last_30d`", "title": "Resolved 30d", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "created_last_30d", "expr": "`created_last_30d`", "title": "Created 30d", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
        ], "Project scorecard"), 0, 10, 6, 6),
    ]

    p4_items = [
        (counter(DS_TEAM_PROD, "COUNT_IF(resolved_30d > 0 OR open_now > 0)", "Active contributors (30d)"), 0, 0, 1, 2),
        (counter(DS_TEAM_PROD, "MAX(resolved_30d)", "Top resolver count"), 1, 0, 1, 2),
        (counter(DS_TEAM_PROD, "AVG(avg_cycle_time_days)", "Team avg cycle (d)"), 2, 0, 1, 2),
        (counter(DS_TEAM_PROD, "AVG(open_now)", "Avg open load"), 3, 0, 1, 2),
        (bar(DS_TEAM_PROD, "assignee_name", "`assignee_name`", "resolved_30d", "MAX(`resolved_30d`)", "Top 20 resolvers (30d)", sort="y-reversed"), 0, 2, 3, 4),
        (scatter(DS_TEAM_PROD, "cycle", "`avg_cycle_time_days`", "resolved", "`resolved_90d`", "assignee", "`assignee_name`",
                 "Cycle time vs resolved (90d)", x_display="Avg cycle (days)", y_display="Resolved (90d)"), 3, 2, 3, 4),
        (bar(DS_ASSIGNEE_LOAD, "assignee_name", "`assignee_name`", "open_issues", "SUM(`open_issues`)",
             "Open load by assignee and priority", color_field="priority", color_expr="`priority`", sort="y-reversed", stacked=True), 0, 6, 6, 4),
        (table(DS_TEAM_PROD, [
            {"name": "assignee_name", "expr": "`assignee_name`", "title": "Assignee"},
            {"name": "resolved_30d", "expr": "`resolved_30d`", "title": "Resolved 30d", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "resolved_90d", "expr": "`resolved_90d`", "title": "Resolved 90d", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "open_now", "expr": "`open_now`", "title": "Open now", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "open_critical", "expr": "`open_critical`", "title": "Open critical", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "avg_cycle_time_days", "expr": "`avg_cycle_time_days`", "title": "Avg cycle (d)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
            {"name": "avg_lead_time_days", "expr": "`avg_lead_time_days`", "title": "Avg lead (d)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
        ], "Assignee scorecard"), 0, 10, 6, 6),
    ]

    section_heights = [12, 12, 16, 16]
    sections = [p1_items, p2_items, p3_items, p4_items]
    y_offset = 2  # room for global filters
    all_items = [
        (filter_widget(
            "filter-multi-select",
            "project_key",
            "Project",
            [DS_VELOCITY, DS_VELOCITY_RECENT, DS_ISSUE, DS_ISSUE_OPEN, DS_ISSUE_RESOLVED_180, DS_PROJECT_HEALTH],
        ), 0, 0, 3, 2),
        (filter_widget(
            "filter-multi-select",
            "assignee_name",
            "Assignee",
            [DS_TEAM_PROD, DS_ASSIGNEE_LOAD],
        ), 3, 0, 3, 2),
    ]
    for items, height in zip(sections, section_heights):
        all_items.extend(offset_items(items, y_offset))
        y_offset += height

    pages = [
        {
            "name": hid("page:overview"),
            "displayName": "Jira Analytics",
            "pageType": "PAGE_TYPE_CANVAS",
            "layout": make_layout(all_items),
        },
    ]

    dashboard = {
        "datasets": datasets,
        "pages": pages,
        "uiSettings": {"theme": {"widgetHeaderAlignment": "ALIGNMENT_UNSPECIFIED"}, "applyModeEnabled": False},
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(dashboard, f, indent=2)

    n_widgets = sum(len(p["layout"]) for p in pages)
    print(f"Wrote {output_path} ({os.path.getsize(output_path)} bytes)")
    print(f"Datasets: {len(datasets)}  Pages: {len(pages)}  Widgets: {n_widgets}")
    return output_path


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from read_pipeline_config import layer_config  # noqa: E402

    cfg = layer_config()
    build_dashboard(metrics_catalog=cfg["metrics_catalog"], metrics_schema=cfg["metrics_schema"])
