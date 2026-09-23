"""Generate the Lakeview dashboard JSON for Jira analytics (semantic layer).

Datasets query Unity Catalog metric views with MEASURE(). The checked-in template
at src/dashboard/jira_genie.lvdash.json uses {dashboard_catalog} and
{dashboard_schema} placeholders; sync_config.sh patches dashboards/jira_genie.lvdash.json.

Regenerate template:  python scripts/build_assets.py --regenerate-dashboard
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "src" / "dashboard" / "jira_genie.lvdash.json"

COLOR_PRIMARY = "#1B5E20"
PALETTE = ["#1B5E20", "#00A972", "#FFAB00", "#FF3621", "#8BCAE7", "#AB4057", "#919191"]

_id_counter = 0


def hid(label: str = "") -> str:
    """Deterministic widget/page id (stable across regenerations)."""
    global _id_counter
    _id_counter += 1
    seed = f"jira-genie:{label}:{_id_counter}"
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
        return f"`{metrics_catalog}`.`{metrics_schema}`.{view}"

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
            "MEASURE(`Issues Completed`) AS issues_completed, "
            "CASE WHEN `Sprint State` = 'active' THEN 1 ELSE 0 END AS is_active, "
            "CASE WHEN `Complete Date` >= CURRENT_DATE() - INTERVAL 30 DAYS "
            "THEN MEASURE(`Points Completed`) ELSE 0 END AS points_completed_30d "
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
            "MEASURE(`Issues Completed`) AS issues_completed, "
            "MEASURE(`Points Planned`) - MEASURE(`Points Completed`) AS carryover_points "
            f"FROM {mv('metric_sprint_velocity')} "
            "WHERE `Sprint State` = 'closed' AND `Complete Date` IS NOT NULL "
            "GROUP BY `Sprint`, `Sprint State`, `Project Key`, `Start Date`, `Complete Date` "
            "ORDER BY `Complete Date` DESC LIMIT 12"
        ),
        "Sprint velocity (last 12 closed)",
    )
    DS_VELOCITY_SERIES = add_dataset(
        "ds_velocity_series",
        (
            "SELECT `Sprint` AS sprint_name, `Project Key` AS project_key, "
            "`Complete Date` AS complete_date, "
            "'Planned' AS series, MEASURE(`Points Planned`) AS points "
            f"FROM {mv('metric_sprint_velocity')} "
            "WHERE `Sprint State` = 'closed' AND `Complete Date` IS NOT NULL "
            "GROUP BY `Sprint`, `Project Key`, `Complete Date` "
            "UNION ALL "
            "SELECT `Sprint` AS sprint_name, `Project Key` AS project_key, "
            "`Complete Date` AS complete_date, "
            "'Completed' AS series, MEASURE(`Points Completed`) AS points "
            f"FROM {mv('metric_sprint_velocity')} "
            "WHERE `Sprint State` = 'closed' AND `Complete Date` IS NOT NULL "
            "GROUP BY `Sprint`, `Project Key`, `Complete Date`"
        ),
        "Sprint planned vs completed series",
    )
    issue_dims = (
        "`Issue Key` AS issue_key, `Summary` AS summary, `Project Key` AS project_key, "
        "`Assignee` AS assignee_name, `Priority` AS priority, `Age (days)` AS age_days, "
        "`Status Category` AS status_category, `Issue Type` AS issue_type, "
        "`Is Resolved` AS is_resolved, `Cycle Time (days)` AS cycle_time_days, "
        "`Lead Time (days)` AS lead_time_days, `Age Bucket` AS age_bucket"
    )
    cycle_bucket_sql = (
        "CASE WHEN `Cycle Time (days)` < 1 THEN '< 1d'"
        " WHEN `Cycle Time (days)` < 3 THEN '1-3d'"
        " WHEN `Cycle Time (days)` < 7 THEN '3-7d'"
        " WHEN `Cycle Time (days)` < 14 THEN '7-14d'"
        " WHEN `Cycle Time (days)` < 30 THEN '14-30d'"
        " WHEN `Cycle Time (days)` < 60 THEN '30-60d'"
        " WHEN `Cycle Time (days)` < 90 THEN '60-90d'"
        " ELSE '90d+' END AS cycle_bucket"
    )
    DS_ISSUE = add_dataset(
        "ds_issue",
        f"SELECT {issue_dims} FROM {mv('metric_issue')}",
        "Issue fact",
    )
    DS_ISSUE_OPEN = add_dataset(
        "ds_issue_open",
        (
            f"SELECT {issue_dims}, "
            "CASE WHEN `Age (days)` > 30 THEN 1 ELSE 0 END AS is_stale_open, "
            "CASE WHEN `Age (days)` > 30 AND `Priority` IN ('Highest','Critical','Blocker') "
            "THEN 1 ELSE 0 END AS is_stale_critical, "
            "CASE WHEN `Is Unassigned` THEN 1 ELSE 0 END AS is_unassigned, "
            "CASE WHEN `Is Overdue` THEN 1 ELSE 0 END AS is_overdue, "
            "CASE WHEN `Is WIP` THEN 1 ELSE 0 END AS is_wip "
            f"FROM {mv('metric_issue')} WHERE NOT `Is Resolved`"
        ),
        "Open issues",
    )
    DS_ISSUE_KPI = add_dataset(
        "ds_issue_kpi",
        (
            "SELECT `Project Key` AS project_key, "
            "MEASURE(`Open Issues`) AS open_issues, "
            "MEASURE(`Open Critical`) AS open_critical, "
            "MEASURE(`WIP Issues`) AS wip_issues, "
            "MEASURE(`Unassigned Open`) AS unassigned_open, "
            "MEASURE(`Overdue Open`) AS overdue_open, "
            "MEASURE(`Created (30d)`) AS created_30d, "
            "MEASURE(`Resolved (30d)`) AS resolved_30d, "
            "MEASURE(`Created (30d)`) - MEASURE(`Resolved (30d)`) AS net_backlog_30d "
            f"FROM {mv('metric_issue')} GROUP BY `Project Key`"
        ),
        "Issue KPIs by project",
    )
    DS_ISSUE_RESOLVED_180 = add_dataset(
        "ds_issue_resolved_180",
        (
            f"SELECT {issue_dims}, {cycle_bucket_sql} FROM {mv('metric_issue')} "
            "WHERE `Is Resolved` AND `Resolved Date` >= CURRENT_DATE() - INTERVAL 180 DAYS"
        ),
        "Resolved issues (last 180 days)",
    )
    DS_ISSUE_MEDIANS = add_dataset(
        "ds_issue_medians",
        (
            "SELECT `Project Key` AS project_key, "
            "approx_percentile(`Cycle Time (days)`, 0.5) AS median_cycle, "
            "approx_percentile(`Lead Time (days)`, 0.5) AS median_lead "
            f"FROM {mv('metric_issue')} "
            "WHERE `Is Resolved` AND `Resolved Date` >= CURRENT_DATE() - INTERVAL 180 DAYS "
            "GROUP BY `Project Key`"
        ),
        "Resolved medians by project",
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
            "MEASURE(`Created Issues (30d)`) AS created_last_30d, "
            "MEASURE(`Net Backlog Change (30d)`) AS net_backlog_30d, "
            "MEASURE(`Flow Ratio (30d)`) AS flow_ratio_30d, "
            "CASE WHEN MEASURE(`Stale Open`) > 0 THEN 1 ELSE 0 END AS has_stale "
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
            "MEASURE(`Avg Lead Time (days)`) AS avg_lead_time_days, "
            "CASE WHEN MEASURE(`Resolved (30d)`) > 0 OR MEASURE(`Open Now`) > 0 "
            "THEN 1 ELSE 0 END AS is_active_contributor "
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
    DS_FLOW_WEEKLY = add_dataset(
        "ds_flow_weekly",
        (
            "SELECT `Flow Week` AS flow_week, `Project Key` AS project_key, "
            "MEASURE(`Created Issues`) AS created_issues, "
            "MEASURE(`Resolved Issues`) AS resolved_issues, "
            "MEASURE(`Net Backlog Change`) AS net_change "
            f"FROM {mv('metric_flow')} "
            "WHERE `Flow Date` >= CURRENT_DATE() - INTERVAL 84 DAYS "
            "GROUP BY `Flow Week`, `Project Key`"
        ),
        "Created vs resolved (weekly)",
    )
    DS_FLOW_SERIES = add_dataset(
        "ds_flow_series",
        (
            "SELECT `Flow Week` AS flow_week, `Project Key` AS project_key, "
            "'Created' AS series, MEASURE(`Created Issues`) AS issues "
            f"FROM {mv('metric_flow')} "
            "WHERE `Flow Date` >= CURRENT_DATE() - INTERVAL 84 DAYS "
            "GROUP BY `Flow Week`, `Project Key` "
            "UNION ALL "
            "SELECT `Flow Week` AS flow_week, `Project Key` AS project_key, "
            "'Resolved' AS series, MEASURE(`Resolved Issues`) AS issues "
            f"FROM {mv('metric_flow')} "
            "WHERE `Flow Date` >= CURRENT_DATE() - INTERVAL 84 DAYS "
            "GROUP BY `Flow Week`, `Project Key`"
        ),
        "Created vs resolved series",
    )
    DS_WORKLOG = add_dataset(
        "ds_worklog",
        (
            "SELECT `Project Key` AS project_key, `Author` AS author_name, "
            "MEASURE(`Hours (30d)`) AS hours_30d, "
            "MEASURE(`Total Hours`) AS total_hours "
            f"FROM {mv('metric_worklog')} GROUP BY `Project Key`, `Author`"
        ),
        "Worklog hours",
    )

    def agg_field(fn: str, col: str) -> dict:
        # Lakeview widget fields only allow SUM/AVG/COUNT/MAX/MIN + `col`.
        # Field name must be lowercase fn(col) and match encodings.fieldName.
        name = f"{fn.lower()}({col})"
        return {"name": name, "expression": f"{fn}(`{col}`)"}

    def counter(dataset: str, fn: str, col: str, title: str):
        field = agg_field(fn, col)
        return {
            "name": hid(f"counter:{title}"),
            "queries": [{
                "name": "main_query",
                "query": {
                    "datasetName": dataset,
                    "fields": [field],
                    "disaggregated": False,
                },
            }],
            "spec": {
                "version": 2,
                "widgetType": "counter",
                "encodings": {
                    "value": {
                        "fieldName": field["name"],
                        "displayName": title,
                        "format": {
                            "type": "number",
                            "abbreviation": "compact",
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
            "queries": [{"name": "main_query", "query": {"datasetName": dataset, "fields": fields, "disaggregated": False}}],
            "spec": {"version": 3, "widgetType": "bar", "encodings": encodings,
                     "frame": {"showTitle": True, "title": title}, "mark": {"colors": PALETTE}},
        }

    def line(dataset, x_field, x_expr, y_field, y_expr, title, **kwargs):
        return {
            "name": hid(f"line:{title}"),
            "queries": [{"name": "main_query", "query": {
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
            "queries": [{"name": "main_query", "query": {
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

    def scatter(dataset, x_field, x_expr, y_field, y_expr, color_field, color_expr, title, **kwargs):
        return {
            "name": hid(f"scatter:{title}"),
            "queries": [{"name": "main_query", "query": {
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
            "queries": [{"name": "main_query", "query": {
                "datasetName": dataset,
                "fields": [{"name": c["name"], "expression": c["expr"]} for c in columns],
                "disaggregated": True,
            }}],
            "spec": {"version": 2, "widgetType": "table", "encodings": {"columns": enc_cols},
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
        # Authoring coords are 6-wide; GRID_V1 is 12 columns. Scale x/width so
        # the canvas fills the published dashboard instead of the left half.
        return [{"widget": w, "position": {"x": x * 2, "y": y, "width": ww * 2, "height": hh}}
                for (w, x, y, ww, hh) in items]

    def page(name: str, display: str, items: list) -> dict:
        return {
            "name": hid(f"page:{name}"),
            "displayName": display,
            "pageType": "PAGE_TYPE_CANVAS",
            "layoutVersion": "GRID_V1",
            "layout": make_layout(items),
        }

    # Tempo: one audience / one story per page, ~6 gadgets, bar over pie, one list max.
    portfolio = [
        (filter_widget(
            "filter-multi-select", "project_key", "Project",
            [DS_ISSUE, DS_ISSUE_OPEN, DS_ISSUE_KPI, DS_PROJECT_HEALTH, DS_FLOW_SERIES, DS_FLOW_WEEKLY],
        ), 0, 0, 6, 2),
        (counter(DS_ISSUE_KPI, "SUM", "open_issues", "Open issues"), 0, 2, 1, 2),
        (counter(DS_ISSUE_KPI, "SUM", "created_30d", "Created (30d)"), 1, 2, 1, 2),
        (counter(DS_ISSUE_KPI, "SUM", "resolved_30d", "Resolved (30d)"), 2, 2, 1, 2),
        (counter(DS_ISSUE_KPI, "SUM", "net_backlog_30d", "Net backlog (30d)"), 3, 2, 1, 2),
        (counter(DS_ISSUE_KPI, "SUM", "open_critical", "Open critical"), 4, 2, 1, 2),
        (counter(DS_PROJECT_HEALTH, "AVG", "flow_ratio_30d", "Flow ratio (30d)"), 5, 2, 1, 2),
        (bar(DS_FLOW_SERIES, "flow_week", "`flow_week`", "issues", "SUM(`issues`)",
             "Created vs resolved (last 12 weeks)",
             color_field="series", color_expr="`series`",
             x_display="Week", y_display="Issues"), 0, 4, 4, 5),
        (bar(DS_ISSUE_OPEN, "project_key", "`project_key`", "count", "COUNT(*)",
             "Open issues by project", sort="y-reversed",
             x_display="Project", y_display="Open issues"), 4, 4, 2, 5),
        (table(DS_PROJECT_HEALTH, [
            {"name": "project_key", "expr": "`project_key`", "title": "Project"},
            {"name": "project_name", "expr": "`project_name`", "title": "Name"},
            {"name": "open_issues", "expr": "`open_issues`", "title": "Open", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "open_critical", "expr": "`open_critical`", "title": "Open critical", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "stale_open", "expr": "`stale_open`", "title": "Stale (>30d)", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "created_last_30d", "expr": "`created_last_30d`", "title": "Created 30d", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "resolved_last_30d", "expr": "`resolved_last_30d`", "title": "Resolved 30d", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "net_backlog_30d", "expr": "`net_backlog_30d`", "title": "Net backlog", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "flow_ratio_30d", "expr": "`flow_ratio_30d`", "title": "Flow ratio", "type": "float", "displayAs": "number", "numberFormat": "0.00"},
            {"name": "avg_cycle_time_days", "expr": "`avg_cycle_time_days`", "title": "Avg cycle (d)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
        ], "Project scorecard"), 0, 9, 6, 6),
    ]

    flow = [
        (filter_widget(
            "filter-multi-select", "project_key", "Project",
            [DS_ISSUE_OPEN, DS_ISSUE_RESOLVED_180, DS_ISSUE_MEDIANS, DS_TIME_IN_STATUS, DS_ISSUE_KPI],
        ), 0, 0, 6, 2),
        (counter(DS_ISSUE_MEDIANS, "AVG", "median_cycle", "Median cycle (days)"), 0, 2, 1, 2),
        (counter(DS_ISSUE_MEDIANS, "AVG", "median_lead", "Median lead (days)"), 1, 2, 1, 2),
        (counter(DS_ISSUE_OPEN, "SUM", "is_stale_open", "Open >30d"), 2, 2, 1, 2),
        (counter(DS_ISSUE_OPEN, "SUM", "is_stale_critical", "Stale critical"), 3, 2, 1, 2),
        (counter(DS_ISSUE_KPI, "SUM", "wip_issues", "WIP"), 4, 2, 1, 2),
        (counter(DS_ISSUE_KPI, "SUM", "overdue_open", "Overdue open"), 5, 2, 1, 2),
        (histogram(DS_ISSUE_RESOLVED_180, "cycle_bucket", "`cycle_bucket`",
                   "count(*)", "COUNT(*)", "Cycle time distribution (last 180d resolved)",
                   x_display="Cycle bucket"), 0, 4, 3, 5),
        (bar(DS_ISSUE_OPEN, "age_bucket", "`age_bucket`", "count", "COUNT(*)",
             "Open issues by age", sort="natural-order",
             x_display="Age bucket", y_display="Open issues"), 3, 4, 3, 5),
        (table(DS_TIME_IN_STATUS, [
            {"name": "project_key", "expr": "`project_key`", "title": "Project"},
            {"name": "status_name", "expr": "`status_name`", "title": "Status"},
            {"name": "p50_hours", "expr": "`p50_hours`", "title": "P50 (h)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
            {"name": "p90_hours", "expr": "`p90_hours`", "title": "P90 (h)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
            {"name": "observations", "expr": "`observations`", "title": "Observations", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
        ], "Where work stalls (time in status)"), 0, 9, 6, 6),
    ]

    sprint = [
        (filter_widget(
            "filter-multi-select", "project_key", "Project",
            [DS_VELOCITY, DS_VELOCITY_RECENT, DS_VELOCITY_SERIES],
        ), 0, 0, 6, 2),
        (counter(DS_VELOCITY, "SUM", "is_active", "Active sprints"), 0, 2, 1, 2),
        (counter(DS_VELOCITY_RECENT, "AVG", "completion_ratio", "Avg completion (last 12)"), 1, 2, 2, 2),
        (counter(DS_VELOCITY, "SUM", "points_completed_30d", "Points completed (30d)"), 3, 2, 1, 2),
        (counter(DS_VELOCITY_RECENT, "SUM", "carryover_points", "Carryover points (last 12)"), 4, 2, 2, 2),
        (bar(DS_VELOCITY_SERIES, "sprint_name", "`sprint_name`", "points", "SUM(`points`)",
             "Planned vs completed points",
             color_field="series", color_expr="`series`",
             x_display="Sprint", y_display="Points"), 0, 4, 3, 5),
        (line(DS_VELOCITY_RECENT, "sprint_name", "`sprint_name`", "ratio", "AVG(`completion_ratio`)",
              "Completion ratio trend", x_display="Sprint", y_display="Completion"), 3, 4, 3, 5),
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
        ], "Sprint outcomes"), 0, 9, 6, 6),
    ]

    team = [
        (filter_widget(
            "filter-multi-select", "assignee_name", "Assignee",
            [DS_TEAM_PROD, DS_ASSIGNEE_LOAD],
        ), 0, 0, 3, 2),
        (filter_widget(
            "filter-multi-select", "project_key", "Project",
            [DS_ASSIGNEE_LOAD, DS_WORKLOG, DS_ISSUE_KPI],
        ), 3, 0, 3, 2),
        (counter(DS_TEAM_PROD, "SUM", "is_active_contributor", "Active contributors"), 0, 2, 1, 2),
        (counter(DS_TEAM_PROD, "AVG", "open_now", "Avg open load"), 1, 2, 1, 2),
        (counter(DS_ISSUE_KPI, "SUM", "unassigned_open", "Unassigned open"), 2, 2, 1, 2),
        (counter(DS_TEAM_PROD, "AVG", "avg_cycle_time_days", "Team avg cycle (d)"), 3, 2, 1, 2),
        (counter(DS_WORKLOG, "SUM", "hours_30d", "Hours logged (30d)"), 4, 2, 2, 2),
        (bar(DS_ASSIGNEE_LOAD, "assignee_name", "`assignee_name`", "open_issues", "SUM(`open_issues`)",
             "Open load by assignee and priority",
             color_field="priority", color_expr="`priority`", sort="y-reversed", stacked=True,
             x_display="Assignee", y_display="Open issues"), 0, 4, 3, 5),
        (scatter(DS_TEAM_PROD, "cycle", "`avg_cycle_time_days`", "resolved", "`resolved_90d`",
                 "assignee", "`assignee_name`",
                 "Cycle time vs resolved (90d)",
                 x_display="Avg cycle (days)", y_display="Resolved (90d)"), 3, 4, 3, 5),
        (table(DS_TEAM_PROD, [
            {"name": "assignee_name", "expr": "`assignee_name`", "title": "Assignee"},
            {"name": "resolved_30d", "expr": "`resolved_30d`", "title": "Resolved 30d", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "resolved_90d", "expr": "`resolved_90d`", "title": "Resolved 90d", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "open_now", "expr": "`open_now`", "title": "Open now", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "open_critical", "expr": "`open_critical`", "title": "Open critical", "type": "integer", "displayAs": "number", "numberFormat": "0,0"},
            {"name": "avg_cycle_time_days", "expr": "`avg_cycle_time_days`", "title": "Avg cycle (d)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
            {"name": "avg_lead_time_days", "expr": "`avg_lead_time_days`", "title": "Avg lead (d)", "type": "float", "displayAs": "number", "numberFormat": "0.0"},
        ], "Assignee scorecard"), 0, 9, 6, 6),
    ]

    def header(md: str, label: str) -> dict:
        # Markdown/text widget: no queries or spec, just serialized markdown.
        return {"name": hid(f"header:{label}"), "textbox_spec": md}

    def shift(items: list, dy: int) -> list:
        return [(w, x, y + dy, ww, hh) for (w, x, y, ww, hh) in items]

    def section_height(items: list) -> int:
        return max(y + hh for (_, _, y, _, hh) in items)

    # Single page: each section gets a markdown header, then its widgets, stacked.
    sections = [
        ("portfolio", "Portfolio health",
         "Backlog size, inflow vs outflow, and a per-project scorecard.", portfolio),
        ("flow", "Flow & cycle time",
         "How fast work moves, cycle-time distribution, and where it stalls.", flow),
        ("sprint", "Sprint delivery",
         "Planned vs completed points, completion trend, and sprint outcomes.", sprint),
        ("team", "Team & workload",
         "Per-assignee load, throughput, and cycle time.", team),
    ]

    HEADER_H, GAP = 2, 1
    combined: list = []
    cursor = 0
    for label, title, subtitle, items in sections:
        combined.append((header(f"## {title}\n\n{subtitle}", label), 0, cursor, 6, HEADER_H))
        cursor += HEADER_H
        combined += shift(items, cursor)
        cursor += section_height(items) + GAP

    pages = [page("overview", "Jira Genie", combined)]

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
