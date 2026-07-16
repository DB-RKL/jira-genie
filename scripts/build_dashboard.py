"""Generate the Lakeview dashboard JSON for Jira analytics.

Run:  python scripts/build_dashboard.py
Output: dashboards/jira_analytics.lvdash.json
"""

import json
import os
import secrets
from pathlib import Path

CATALOG_SCHEMA = "rubjit_jira.gold"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "dashboards" / "jira_analytics.lvdash.json"

COLOR_PRIMARY = "#1B5E20"
COLOR_OK = "#00A972"
COLOR_WARN = "#FFAB00"
COLOR_BAD = "#FF3621"
PALETTE = ["#1B5E20", "#00A972", "#FFAB00", "#FF3621", "#8BCAE7", "#AB4057", "#919191"]


def hid() -> str:
    return secrets.token_hex(4)


# ---------- datasets ---------------------------------------------------------

datasets = []


def add_dataset(name: str, sql: str, display: str) -> str:
    datasets.append({
        "name": name,
        "displayName": display,
        "queryLines": [sql],
    })
    return name


DS_VELOCITY = add_dataset(
    "ds_velocity",
    f"SELECT * FROM {CATALOG_SCHEMA}.fct_sprint_velocity",
    "Sprint velocity",
)
DS_VELOCITY_RECENT = add_dataset(
    "ds_velocity_recent",
    (
        f"SELECT * FROM {CATALOG_SCHEMA}.fct_sprint_velocity "
        f"WHERE state = 'closed' AND complete_date IS NOT NULL "
        f"ORDER BY complete_date DESC LIMIT 12"
    ),
    "Sprint velocity (last 12 closed)",
)
DS_ISSUE = add_dataset(
    "ds_issue",
    f"SELECT * FROM {CATALOG_SCHEMA}.fct_issue",
    "Issue fact",
)
DS_ISSUE_OPEN = add_dataset(
    "ds_issue_open",
    f"SELECT * FROM {CATALOG_SCHEMA}.fct_issue WHERE NOT is_resolved",
    "Open issues",
)
DS_ISSUE_RESOLVED_180 = add_dataset(
    "ds_issue_resolved_180",
    (
        f"SELECT * FROM {CATALOG_SCHEMA}.fct_issue "
        f"WHERE is_resolved AND resolved_at >= CURRENT_DATE() - INTERVAL 180 DAYS"
    ),
    "Resolved issues (last 180 days)",
)
DS_PROJECT_HEALTH = add_dataset(
    "ds_project_health",
    f"SELECT * FROM {CATALOG_SCHEMA}.agg_project_health",
    "Project health",
)
DS_ASSIGNEE_LOAD = add_dataset(
    "ds_assignee_load",
    f"SELECT * FROM {CATALOG_SCHEMA}.agg_assignee_load",
    "Assignee load",
)
DS_TEAM_PROD = add_dataset(
    "ds_team_prod",
    f"SELECT * FROM {CATALOG_SCHEMA}.agg_team_productivity",
    "Team productivity",
)
DS_TIME_IN_STATUS = add_dataset(
    "ds_time_in_status",
    f"SELECT * FROM {CATALOG_SCHEMA}.agg_time_in_status",
    "Time in status",
)


# ---------- widget builders --------------------------------------------------

def counter(dataset: str, expression: str, title: str, fmt: str = "0,0", value_alias: str = "value"):
    return {
        "name": hid(),
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
                    "format": {"type": "number-plain", "abbreviation": "auto", "decimalPlaces": {"type": "max", "places": 1}},
                }
            },
            "frame": {"showTitle": True, "title": title},
        },
    }


def bar(dataset: str, x_field: str, x_expr: str, y_field: str, y_expr: str,
        title: str, color_field: str | None = None, color_expr: str | None = None,
        x_display: str | None = None, y_display: str | None = None,
        sort: str | None = None, stacked: bool = False):
    fields = [
        {"name": x_field, "expression": x_expr},
        {"name": y_field, "expression": y_expr},
    ]
    encodings = {
        "x": {
            "fieldName": x_field,
            "scale": {"type": "categorical", **({"sort": {"by": sort}} if sort else {})},
            "displayName": x_display or x_field,
        },
        "y": {
            "fieldName": y_field,
            "scale": {"type": "quantitative"},
            "displayName": y_display or y_field,
        },
        "label": {"show": True},
    }
    if color_field and color_expr:
        fields.append({"name": color_field, "expression": color_expr})
        encodings["color"] = {
            "fieldName": color_field,
            "scale": {"type": "categorical"},
            "displayName": color_field,
        }
        if stacked:
            encodings["y"]["scale"]["stack"] = "stack"
    return {
        "name": hid(),
        "queries": [{
            "name": "main",
            "query": {
                "datasetName": dataset,
                "fields": fields,
                "disaggregated": False,
            },
        }],
        "spec": {
            "version": 3,
            "widgetType": "bar",
            "encodings": encodings,
            "frame": {"showTitle": True, "title": title},
            "mark": {"colors": PALETTE},
        },
    }


def line(dataset: str, x_field: str, x_expr: str, y_field: str, y_expr: str,
         title: str, x_temporal: bool = False, x_display: str | None = None,
         y_display: str | None = None):
    return {
        "name": hid(),
        "queries": [{
            "name": "main",
            "query": {
                "datasetName": dataset,
                "fields": [
                    {"name": x_field, "expression": x_expr},
                    {"name": y_field, "expression": y_expr},
                ],
                "disaggregated": False,
            },
        }],
        "spec": {
            "version": 3,
            "widgetType": "line",
            "encodings": {
                "x": {
                    "fieldName": x_field,
                    "scale": {"type": "temporal" if x_temporal else "categorical"},
                    "displayName": x_display or x_field,
                },
                "y": {
                    "fieldName": y_field,
                    "scale": {"type": "quantitative"},
                    "displayName": y_display or y_field,
                },
            },
            "frame": {"showTitle": True, "title": title},
            "mark": {"colors": [COLOR_PRIMARY]},
        },
    }


def histogram(dataset: str, x_field: str, x_expr: str, y_field: str, y_expr: str,
              title: str, x_display: str | None = None):
    return {
        "name": hid(),
        "queries": [{
            "name": "main",
            "query": {
                "datasetName": dataset,
                "fields": [
                    {"name": x_field, "expression": x_expr},
                    {"name": y_field, "expression": y_expr},
                ],
                "disaggregated": False,
            },
        }],
        "spec": {
            "version": 3,
            "widgetType": "histogram",
            "encodings": {
                "x": {
                    "fieldName": x_field,
                    "scale": {"type": "categorical", "sort": {"by": "natural-order"}},
                    "displayName": x_display or x_field,
                },
                "y": {
                    "fieldName": y_field,
                    "scale": {"type": "quantitative"},
                    "displayName": "Issues",
                },
            },
            "frame": {"showTitle": True, "title": title},
            "mark": {"colors": [COLOR_PRIMARY]},
        },
    }


def pie(dataset: str, angle_field: str, angle_expr: str, color_field: str, color_expr: str, title: str):
    return {
        "name": hid(),
        "queries": [{
            "name": "main",
            "query": {
                "datasetName": dataset,
                "fields": [
                    {"name": angle_field, "expression": angle_expr},
                    {"name": color_field, "expression": color_expr},
                ],
                "disaggregated": False,
            },
        }],
        "spec": {
            "version": 3,
            "widgetType": "pie",
            "encodings": {
                "angle": {"fieldName": angle_field, "scale": {"type": "quantitative"}, "displayName": angle_field},
                "color": {"fieldName": color_field, "scale": {"type": "categorical"}, "displayName": color_field},
            },
            "frame": {"showTitle": True, "title": title},
        },
    }


def scatter(dataset: str, x_field: str, x_expr: str, y_field: str, y_expr: str,
            color_field: str, color_expr: str, title: str,
            x_display: str | None = None, y_display: str | None = None):
    return {
        "name": hid(),
        "queries": [{
            "name": "main",
            "query": {
                "datasetName": dataset,
                "fields": [
                    {"name": x_field, "expression": x_expr},
                    {"name": y_field, "expression": y_expr},
                    {"name": color_field, "expression": color_expr},
                ],
                "disaggregated": True,
            },
        }],
        "spec": {
            "version": 3,
            "widgetType": "scatter",
            "encodings": {
                "x": {"fieldName": x_field, "scale": {"type": "quantitative"}, "displayName": x_display or x_field},
                "y": {"fieldName": y_field, "scale": {"type": "quantitative"}, "displayName": y_display or y_field},
                "color": {"fieldName": color_field, "scale": {"type": "categorical"}, "displayName": color_field},
            },
            "frame": {"showTitle": True, "title": title},
        },
    }


def heatmap(dataset: str, x_field: str, x_expr: str, y_field: str, y_expr: str,
            color_field: str, color_expr: str, title: str):
    return {
        "name": hid(),
        "queries": [{
            "name": "main",
            "query": {
                "datasetName": dataset,
                "fields": [
                    {"name": x_field, "expression": x_expr},
                    {"name": y_field, "expression": y_expr},
                    {"name": color_field, "expression": color_expr},
                ],
                "disaggregated": False,
            },
        }],
        "spec": {
            "version": 3,
            "widgetType": "heatmap",
            "encodings": {
                "x": {"fieldName": x_field, "scale": {"type": "categorical"}, "displayName": x_field},
                "y": {"fieldName": y_field, "scale": {"type": "categorical"}, "displayName": y_field},
                "color": {"fieldName": color_field, "scale": {"type": "quantitative"}, "displayName": color_field},
            },
            "frame": {"showTitle": True, "title": title},
        },
    }


def table(dataset: str, columns: list[dict], title: str, where: str | None = None,
          order_by: str | None = None, limit: int | None = None):
    sql_fields = [{"name": c["name"], "expression": c["expr"]} for c in columns]
    enc_cols = []
    for c in columns:
        enc = {
            "fieldName": c["name"],
            "type": c.get("type", "string"),
            "displayAs": c.get("displayAs", "string"),
            "title": c.get("title", c["name"]),
            "displayName": c.get("title", c["name"]),
        }
        if "numberFormat" in c:
            enc["numberFormat"] = c["numberFormat"]
            enc["alignContent"] = "right"
        enc_cols.append(enc)
    return {
        "name": hid(),
        "queries": [{
            "name": "main",
            "query": {
                "datasetName": dataset,
                "fields": sql_fields,
                "disaggregated": True,
            },
        }],
        "spec": {
            "version": 1,
            "widgetType": "table",
            "encodings": {"columns": enc_cols},
            "frame": {"showTitle": True, "title": title},
        },
    }


def filter_widget(widget_type: str, field_name: str, display: str, datasets: list[str]):
    queries = [
        {"name": f"{ds}_filter_{field_name}", "query": {
            "datasetName": ds,
            "fields": [{"name": field_name, "expression": f"`{field_name}`"}],
            "disaggregated": False,
        }}
        for ds in datasets
    ]
    encodings_fields = [
        {"fieldName": field_name, "displayName": display, "queryName": f"{ds}_filter_{field_name}"}
        for ds in datasets
    ]
    return {
        "name": hid(),
        "queries": queries,
        "spec": {
            "version": 2,
            "widgetType": widget_type,
            "encodings": {"fields": encodings_fields},
            "frame": {"showTitle": True, "title": display},
        },
    }


# ---------- page assembly ----------------------------------------------------

def make_layout(items):
    """items: list of (widget, x, y, w, h) tuples"""
    return [
        {"widget": w, "position": {"x": x, "y": y, "width": ww, "height": hh}}
        for (w, x, y, ww, hh) in items
    ]


# ---- Page 1: Sprint velocity & burndown ----
p1_items = [
    (counter(DS_VELOCITY,
             f"COUNT_IF(`state` = 'active')",
             "Active sprints"), 0, 0, 1, 2),
    (counter(DS_VELOCITY_RECENT,
             "AVG(completion_ratio)",
             "Avg completion (last 12)"), 1, 0, 1, 2),
    (counter(DS_VELOCITY,
             "SUM(CASE WHEN complete_date >= CURRENT_DATE() - INTERVAL 30 DAYS THEN points_completed END)",
             "Points completed (30d)"), 2, 0, 1, 2),
    (counter(DS_VELOCITY_RECENT,
             "SUM(points_in_sprint - points_completed)",
             "Carryover points (last 12)"), 3, 0, 1, 2),
    (filter_widget("filter-multi-select", "project_key", "Project",
                   [DS_VELOCITY, DS_VELOCITY_RECENT]), 4, 0, 2, 2),

    (bar(DS_VELOCITY_RECENT,
         "sprint_name", "`sprint_name`",
         "points", "SUM(`points_in_sprint`)",
         "Points in sprint vs completed",
         color_field="metric", color_expr="'Planned'"),
     0, 2, 3, 4),
    (line(DS_VELOCITY_RECENT,
          "sprint_name", "`sprint_name`",
          "ratio", "AVG(`completion_ratio`)",
          "Completion ratio trend"),
     3, 2, 3, 4),

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

# ---- Page 2: Cycle Time & Aging ----
p2_items = [
    (counter(DS_ISSUE_RESOLVED_180,
             "PERCENTILE_APPROX(cycle_time_days, 0.5)",
             "Median cycle (days)"), 0, 0, 1, 2),
    (counter(DS_ISSUE_RESOLVED_180,
             "PERCENTILE_APPROX(lead_time_days, 0.5)",
             "Median lead (days)"), 1, 0, 1, 2),
    (counter(DS_ISSUE_OPEN,
             "COUNT_IF(age_days > 30)",
             "Open >30d"), 2, 0, 1, 2),
    (counter(DS_ISSUE_OPEN,
             "COUNT_IF(age_days > 30 AND priority IN ('Highest','Critical','Blocker'))",
             "Stale critical"), 3, 0, 1, 2),
    (filter_widget("filter-multi-select", "project_key", "Project",
                   [DS_ISSUE, DS_ISSUE_OPEN, DS_ISSUE_RESOLVED_180]), 4, 0, 2, 2),

    (histogram(DS_ISSUE_RESOLVED_180,
               "cycle_bucket",
               "CASE WHEN cycle_time_days < 1 THEN '< 1d'"
               " WHEN cycle_time_days < 3 THEN '1-3d'"
               " WHEN cycle_time_days < 7 THEN '3-7d'"
               " WHEN cycle_time_days < 14 THEN '7-14d'"
               " WHEN cycle_time_days < 30 THEN '14-30d'"
               " WHEN cycle_time_days < 60 THEN '30-60d'"
               " WHEN cycle_time_days < 90 THEN '60-90d'"
               " ELSE '90d+' END",
               "count", "COUNT(*)",
               "Cycle time distribution (last 180d resolved)",
               x_display="Cycle bucket"),
     0, 2, 3, 4),
    (bar(DS_ISSUE_OPEN,
         "age_bucket", "`age_bucket`",
         "count", "COUNT(*)",
         "Open issues by age bucket",
         sort="natural-order"),
     3, 2, 3, 4),

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

# ---- Page 3: Project Portfolio ----
p3_items = [
    (counter(DS_PROJECT_HEALTH, "SUM(open_issues)", "Total open"), 0, 0, 1, 2),
    (counter(DS_PROJECT_HEALTH, "COUNT_IF(stale_open > 0)", "Projects w/ stale"), 1, 0, 1, 2),
    (counter(DS_PROJECT_HEALTH, "AVG(avg_cycle_time_days)", "Portfolio avg cycle (d)"), 2, 0, 1, 2),
    (counter(DS_PROJECT_HEALTH, "SUM(resolved_last_30d)", "Resolved (30d)"), 3, 0, 1, 2),
    (filter_widget("filter-multi-select", "project_key", "Project",
                   [DS_PROJECT_HEALTH, DS_ISSUE_OPEN, DS_ISSUE]), 4, 0, 2, 2),

    (heatmap(DS_ISSUE,
             "project_key", "`project_key`",
             "status_category", "`status_category`",
             "count", "COUNT(*)",
             "Project x status category"), 0, 2, 4, 4),
    (pie(DS_ISSUE,
         "count", "COUNT(*)",
         "issue_type", "`issue_type`",
         "Issue type mix"), 4, 2, 2, 4),

    (bar(DS_ISSUE_OPEN,
         "project_key", "`project_key`",
         "count", "COUNT(*)",
         "Open issues by priority (top projects)",
         color_field="priority", color_expr="`priority`",
         sort="y-reversed", stacked=True),
     0, 6, 6, 4),

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

# ---- Page 4: Team Productivity ----
p4_items = [
    (counter(DS_TEAM_PROD, "COUNT_IF(resolved_30d > 0 OR open_now > 0)", "Active contributors (30d)"), 0, 0, 1, 2),
    (counter(DS_TEAM_PROD, "MAX(resolved_30d)", "Top resolver count"), 1, 0, 1, 2),
    (counter(DS_TEAM_PROD, "AVG(avg_cycle_time_days)", "Team avg cycle (d)"), 2, 0, 1, 2),
    (counter(DS_TEAM_PROD, "AVG(open_now)", "Avg open load"), 3, 0, 1, 2),
    (filter_widget("filter-multi-select", "assignee_name", "Assignee",
                   [DS_TEAM_PROD, DS_ASSIGNEE_LOAD]), 4, 0, 2, 2),

    (bar(DS_TEAM_PROD,
         "assignee_name", "`assignee_name`",
         "resolved_30d", "MAX(`resolved_30d`)",
         "Top 20 resolvers (30d)",
         sort="y-reversed"),
     0, 2, 3, 4),
    (scatter(DS_TEAM_PROD,
             "cycle", "`avg_cycle_time_days`",
             "resolved", "`resolved_90d`",
             "assignee", "`assignee_name`",
             "Cycle time vs resolved (90d)",
             x_display="Avg cycle (days)",
             y_display="Resolved (90d)"),
     3, 2, 3, 4),

    (bar(DS_ASSIGNEE_LOAD,
         "assignee_name", "`assignee_name`",
         "open_issues", "SUM(`open_issues`)",
         "Open load by assignee and priority",
         color_field="priority", color_expr="`priority`",
         sort="y-reversed", stacked=True),
     0, 6, 6, 4),

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


pages = [
    {"name": hid(), "displayName": "Sprint Velocity & Burndown",
     "pageType": "PAGE_TYPE_CANVAS", "layout": make_layout(p1_items)},
    {"name": hid(), "displayName": "Cycle Time & Aging",
     "pageType": "PAGE_TYPE_CANVAS", "layout": make_layout(p2_items)},
    {"name": hid(), "displayName": "Project Portfolio Health",
     "pageType": "PAGE_TYPE_CANVAS", "layout": make_layout(p3_items)},
    {"name": hid(), "displayName": "Team Productivity",
     "pageType": "PAGE_TYPE_CANVAS", "layout": make_layout(p4_items)},
]

dashboard = {
    "datasets": datasets,
    "pages": pages,
    "uiSettings": {
        "theme": {"widgetHeaderAlignment": "ALIGNMENT_UNSPECIFIED"},
        "applyModeEnabled": False,
    },
}


OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w") as f:
    json.dump(dashboard, f, indent=2)

print(f"Wrote {OUTPUT_PATH}  ({os.path.getsize(OUTPUT_PATH)} bytes)")
print(f"Datasets: {len(datasets)}  Pages: {len(pages)}  Widgets: {sum(len(p['layout']) for p in pages)}")
