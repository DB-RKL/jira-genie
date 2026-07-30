#!/usr/bin/env python3
"""Generate all parameterized bundle artifacts from templates.

Outputs:
  - src/metrics/metric_views.sql       (from metric_views.sql.tmpl)
  - src/genie/jira_analytics.geniespace.json
  - src/dashboard/jira_analytics.lvdash.json  (--regenerate-dashboard only)

Usage:
  python scripts/build_assets.py
  python scripts/build_assets.py --catalog my_catalog --gold-schema gold --metrics-schema metrics
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_dashboard import build_dashboard  # noqa: E402

METRIC_VIEWS = [
    "metric_issue",
    "metric_sprint_velocity",
    "metric_issue_transitions",
    "metric_worklog",
    "metric_project_health",
    "metric_assignee_load",
    "metric_team_productivity",
    "metric_time_in_status",
]

COLUMN_CONFIGS: dict[str, list[str]] = {
    "metric_issue": [
        "Issue Key", "Summary", "Project Key", "Project Name", "Project Lead", "Project Category",
        "Issue Type", "Status", "Status Category", "Priority", "Assignee", "Assignee Email",
        "Current Sprint", "Sprint State", "Age Bucket", "Age (days)", "Is Resolved",
        "Created Date", "Resolved Date",
    ],
    "metric_sprint_velocity": [
        "Sprint", "Sprint State", "Project Key", "Project Name", "Project Lead",
        "Sprint Board", "Start Date", "Complete Date",
    ],
    "metric_issue_transitions": [
        "Project Key", "Project Name", "From Status", "To Status",
        "To Status Category", "To Category",
    ],
    "metric_worklog": [
        "Project Key", "Project Name", "Project Lead", "Author", "Author Email", "Work Date",
    ],
    "metric_project_health": [
        "Project Key", "Project Name", "Project Lead", "Project Category",
    ],
    "metric_assignee_load": [
        "Assignee", "Assignee Email", "Project Key", "Project Name", "Priority", "Age Bucket",
    ],
    "metric_team_productivity": ["Assignee", "Assignee Email"],
    "metric_time_in_status": [
        "Project Key", "Project Name", "Status", "Status Category",
    ],
}

# Semantic catalog for Genie instructions — keep in sync with metric_views.sql.tmpl.
METRIC_VIEW_SEMANTICS: dict[str, dict] = {
    "metric_issue": {
        "purpose": "Issue backlog, throughput, cycle/lead time, and aging.",
        "grain": "One row per Jira issue.",
        "joins": [
            "fct_issue → dim_project (project_id): Project Lead, Project Category, Project Type",
            "fct_issue → dim_user as assignee_dim (assignee_id): Assignee Email",
            "fct_issue → dim_user as reporter_dim (reporter_id): Reporter Email",
            "fct_issue → dim_status (status_id): Status Category Order",
            "fct_issue → dim_sprint (current_sprint_id): Sprint State, Sprint Board",
        ],
        "fields": [
            "Issue Key", "Summary", "Project Key", "Project Name", "Project Lead", "Project Category",
            "Issue Type", "Status", "Status Category", "Priority", "Assignee", "Assignee Email",
            "Current Sprint", "Sprint State", "Age Bucket", "Age (days)", "Is Resolved",
            "Created Date", "Resolved Date", "Created Month", "Resolved Month",
        ],
        "measures": [
            "Issue Count", "Open Issues", "Resolved Issues", "Open Critical", "Stale Open",
            "Avg Cycle Time (days)", "Median Cycle Time (days)", "Avg Lead Time (days)",
            "Total Story Points", "Avg Age (days)",
        ],
        "when_to_use": "Backlog health, cycle/lead time, aging, issue-level drill-down.",
    },
    "metric_sprint_velocity": {
        "purpose": "Sprint planning vs delivery and completion ratio.",
        "grain": "One row per sprint per project.",
        "joins": [
            "fct_sprint_velocity → dim_project (project_id): Project Name, Project Lead",
            "fct_sprint_velocity → dim_sprint (sprint_id): Sprint Board",
        ],
        "fields": [
            "Sprint", "Sprint State", "Project Key", "Project Name", "Project Lead",
            "Sprint Board", "Start Date", "Complete Date", "Complete Month",
        ],
        "measures": [
            "Sprint Count", "Points Planned", "Points Completed", "Avg Completion Ratio",
            "Issues Planned", "Issues Completed",
        ],
        "when_to_use": "Velocity, sprint commitment, carryover, completion trends.",
    },
    "metric_issue_transitions": {
        "purpose": "Workflow transitions and time spent in each status.",
        "grain": "One row per issue status transition.",
        "joins": [
            "fct_issue_transitions → dim_project (project_id): Project Key, Project Name",
            "fct_issue_transitions → dim_status as to_status_dim (to_status_id): To Status Category",
        ],
        "fields": [
            "Project Key", "Project Name", "From Status", "To Status",
            "To Status Category", "To Category",
        ],
        "measures": [
            "Transition Count", "Avg Duration (hours)", "Median Duration (hours)",
            "P90 Duration (hours)",
        ],
        "when_to_use": "Time-in-status, workflow bottlenecks, In Review / In Progress dwell time.",
    },
    "metric_worklog": {
        "purpose": "Logged effort hours by contributor and project.",
        "grain": "One row per worklog entry.",
        "joins": [
            "fct_worklog → dim_project (project_id): Project Lead",
            "fct_worklog → dim_user as author_dim (author_id): Author Email",
        ],
        "fields": [
            "Project Key", "Project Name", "Project Lead", "Author", "Author Email",
            "Work Date", "Work Month",
        ],
        "measures": ["Total Hours", "Worklog Entries", "Contributors"],
        "when_to_use": "Effort, capacity, contributor activity.",
    },
    "metric_project_health": {
        "purpose": "Portfolio-level KPIs per project.",
        "grain": "One row per project (pre-aggregated).",
        "joins": [
            "agg_project_health → dim_project (project_id): Project Lead, Project Category",
        ],
        "fields": ["Project Key", "Project Name", "Project Lead", "Project Category"],
        "measures": [
            "Total Issues", "Open Issues", "Resolved Issues", "Open Critical", "Stale Open",
            "Avg Cycle Time (days)", "Avg Lead Time (days)",
            "Resolved Issues (30d)", "Created Issues (30d)",
        ],
        "when_to_use": "Executive portfolio view, project comparison, stale/critical backlog.",
    },
    "metric_assignee_load": {
        "purpose": "Current open workload by assignee, priority, and age.",
        "grain": "One row per assignee × project × priority × age bucket.",
        "joins": [
            "agg_assignee_load → dim_user as assignee_dim (assignee_id): Assignee Email",
            "agg_assignee_load → dim_project (project_id): Project Name",
        ],
        "fields": [
            "Assignee", "Assignee Email", "Project Key", "Project Name", "Priority", "Age Bucket",
        ],
        "measures": ["Open Issues", "Open Story Points", "Avg Age (days)"],
        "when_to_use": "Who is overloaded, open load by priority, aging assignee backlog.",
    },
    "metric_team_productivity": {
        "purpose": "Resolver throughput and cycle time by assignee.",
        "grain": "One row per assignee (pre-aggregated).",
        "joins": [
            "agg_team_productivity → dim_user as assignee_dim (assignee_id): Assignee Email",
        ],
        "fields": ["Assignee", "Assignee Email"],
        "measures": [
            "Resolved (30d)", "Resolved (90d)", "Open Now", "Open Critical",
            "Avg Cycle Time (days)", "Avg Lead Time (days)", "Active Contributors",
        ],
        "when_to_use": "Top resolvers, team throughput, individual cycle time.",
    },
    "metric_time_in_status": {
        "purpose": "Pre-aggregated p50/p90 time-in-status by project and status.",
        "grain": "One row per project × status.",
        "joins": [
            "agg_time_in_status → dim_project (project_id): Project Name",
            "agg_time_in_status → dim_status (status_name): Status Category",
        ],
        "fields": ["Project Key", "Project Name", "Status", "Status Category"],
        "measures": [
            "Observations", "P50 Duration (hours)", "P90 Duration (hours)", "Avg Duration (hours)",
        ],
        "when_to_use": "Status bottleneck heatmaps, compare p50 vs p90 dwell time.",
    },
}


def _render_genie_instructions() -> str:
    lines = [
        "You answer questions about Jira delivery analytics using governed Unity Catalog metric views.",
        "",
        "Rules",
        "- Query ONLY the metric views listed below (never gold fct_* or dim_* tables directly).",
        "- Wrap every KPI in MEASURE(`Measure Name`) — do not recompute COUNT/SUM/AVG manually.",
        "- Filter on fields with WHERE; group with GROUP BY on field display names (backtick-quoted).",
        "- Joined dimension attributes (e.g. Project Lead) are already on the metric view — no extra JOINs in SQL.",
        "",
        "Glossary",
        "- Issue / ticket — work item identified by Issue Key (e.g. SSP-123).",
        "- Status category — To Do (new), In Progress (indeterminate), Done (done).",
        "- Open — Is Resolved = false.",
        "- Cycle time — days from first In Progress to resolution (Median Cycle Time (days)).",
        "- Lead time — days from creation to resolution (Avg Lead Time (days)).",
        "- Velocity — Points Completed on metric_sprint_velocity for closed sprints.",
        "- Critical — priority in Blocker, Critical, or Highest (Open Critical).",
        "- Time in status — P50/P90 Duration (hours) on metric_issue_transitions or metric_time_in_status.",
        "",
        "Relationships (star schema — all many-to-one from fact/aggregate source)",
        "- dim_project enriches project context (lead, category, type) on issue, sprint, worklog, and health views.",
        "- dim_user enriches assignee/author/reporter email on issue, worklog, load, and productivity views.",
        "- dim_status enriches status category on issue and transition views.",
        "- dim_sprint enriches sprint board/state on issue and sprint velocity views.",
        "",
        "Metric view catalog",
    ]
    for view, meta in METRIC_VIEW_SEMANTICS.items():
        lines.append(f"")
        lines.append(f"## {view}")
        lines.append(f"Purpose: {meta['purpose']}")
        lines.append(f"Grain: {meta['grain']}")
        lines.append(f"Use when: {meta['when_to_use']}")
        lines.append("Joins:")
        for join in meta["joins"]:
            lines.append(f"  - {join}")
        lines.append("Fields (dimensions):")
        lines.append("  " + ", ".join(meta["fields"]))
        lines.append("Measures (always use MEASURE()):")
        lines.append("  " + ", ".join(f"MEASURE(`{m}`)" for m in meta["measures"]))
    lines.extend([
        "",
        "Cross-view guidance",
        "- Portfolio / project comparison → metric_project_health",
        "- Sprint velocity / completion → metric_sprint_velocity",
        "- Individual issue drill-down → metric_issue",
        "- Workflow / bottlenecks → metric_issue_transitions or metric_time_in_status",
        "- Who is busy → metric_assignee_load",
        "- Who delivers → metric_team_productivity",
        "- Logged hours → metric_worklog",
        "",
        "Example patterns",
        "  SELECT `Project Key`, MEASURE(`Open Issues`), MEASURE(`Open Critical`)",
        "  FROM metric_project_health GROUP BY 1 ORDER BY 2 DESC",
        "",
        "  SELECT `Project Lead`, MEASURE(`Points Completed`)",
        "  FROM metric_sprint_velocity WHERE `Sprint State` = 'closed' GROUP BY 1",
        "",
        "  SELECT `Assignee Email`, MEASURE(`Open Issues`), MEASURE(`Open Story Points`)",
        "  FROM metric_assignee_load GROUP BY 1 ORDER BY 2 DESC LIMIT 10",
    ])
    return "\n".join(lines)


GENIE_INSTRUCTIONS = _render_genie_instructions()

SAMPLE_QUESTIONS = [
    "What was the velocity for the last 5 closed sprints?",
    "Which 10 assignees resolved the most issues in the last 30 days?",
    "How is median cycle time trending month over month for project DATA?",
    "Which projects have the most open critical issues?",
    "Show me the oldest open bugs and who they are assigned to",
    "What is the average time in In Review status across all projects?",
    "Compare planned vs completed story points for closed sprints this quarter",
    "Which sprints had the worst completion ratio?",
    "Top 10 contributors by total worklog hours last 90 days",
    "What is the distribution of open issues by age bucket?",
]

EXAMPLE_SQLS = [
    {
        "question": ["Which projects have the most open critical issues?"],
        "sql": [
            "SELECT `Project Key`, MEASURE(`Open Critical`) AS open_critical\n",
            "FROM metric_project_health\n",
            "GROUP BY `Project Key`\n",
            "ORDER BY open_critical DESC\n",
            "LIMIT 10",
        ],
    },
    {
        "question": ["What was the velocity for the last 5 closed sprints?"],
        "sql": [
            "SELECT `Sprint`, MEASURE(`Points Completed`) AS velocity\n",
            "FROM metric_sprint_velocity\n",
            "WHERE `Sprint State` = 'closed'\n",
            "GROUP BY `Sprint`, `Complete Date`\n",
            "ORDER BY `Complete Date` DESC\n",
            "LIMIT 5",
        ],
    },
    {
        "question": ["Top 10 contributors by worklog hours"],
        "sql": [
            "SELECT `Author`, MEASURE(`Total Hours`) AS hours\n",
            "FROM metric_worklog\n",
            "GROUP BY `Author`\n",
            "ORDER BY hours DESC\n",
            "LIMIT 10",
        ],
    },
    {
        "question": ["Median cycle time by project"],
        "sql": [
            "SELECT `Project Key`, MEASURE(`Median Cycle Time (days)`) AS median_cycle\n",
            "FROM metric_issue\n",
            "WHERE `Is Resolved`\n",
            "GROUP BY `Project Key`\n",
            "ORDER BY median_cycle DESC",
        ],
    },
    {
        "question": ["P90 time in In Review status by project"],
        "sql": [
            "SELECT `Project Key`, MEASURE(`P90 Duration (hours)`) AS p90_hours\n",
            "FROM metric_issue_transitions\n",
            "WHERE `To Status` = 'In Review'\n",
            "GROUP BY `Project Key`\n",
            "ORDER BY p90_hours DESC",
        ],
    },
    {
        "question": ["Velocity by project lead for closed sprints"],
        "sql": [
            "SELECT `Project Lead`, `Project Key`, MEASURE(`Points Completed`) AS velocity\n",
            "FROM metric_sprint_velocity\n",
            "WHERE `Sprint State` = 'closed'\n",
            "GROUP BY `Project Lead`, `Project Key`\n",
            "ORDER BY velocity DESC",
        ],
    },
    {
        "question": ["Open story points by assignee email"],
        "sql": [
            "SELECT `Assignee Email`, MEASURE(`Open Story Points`) AS points, MEASURE(`Open Issues`) AS issues\n",
            "FROM metric_assignee_load\n",
            "GROUP BY `Assignee Email`\n",
            "ORDER BY points DESC\n",
            "LIMIT 10",
        ],
    },
    {
        "question": ["Which projects have the slowest p90 time in In Progress?"],
        "sql": [
            "SELECT `Project Name`, `Status`, MEASURE(`P90 Duration (hours)`) AS p90_hours\n",
            "FROM metric_time_in_status\n",
            "WHERE `Status` = 'In Progress'\n",
            "GROUP BY `Project Name`, `Status`\n",
            "ORDER BY p90_hours DESC",
        ],
    },
]


def _stable_id(seed: str) -> str:
    n = abs(hash(seed)) % (10**32)
    return f"{n:032x}"


def _escape_sql_comment(text: str) -> str:
    return text.replace("'", "''")


def _metric_view_column_clause(fields: dict[str, str], measures: dict[str, str]) -> str:
    lines: list[str] = []
    for name, comment in fields.items():
        lines.append(f"  `{name}` COMMENT '{_escape_sql_comment(comment)}'")
    for name, comment in measures.items():
        lines.append(f"  `{name}` COMMENT '{_escape_sql_comment(comment)}'")
    if not lines:
        return ""
    return "(\n" + ",\n".join(lines) + "\n)"


def _inject_metric_column_comments(sql_text: str) -> str:
    sys.path.insert(0, str(ROOT / "src" / "metrics"))
    from metric_view_comments import METRIC_VIEW_COLUMN_COMMENTS  # noqa: E402

    for view_name, spec in METRIC_VIEW_COLUMN_COMMENTS.items():
        clause = _metric_view_column_clause(
            spec.get("fields", {}),
            spec.get("measures", {}),
        )
        if not clause:
            continue
        pattern = rf"(CREATE OR REPLACE VIEW [^\n]+\.{view_name})\nWITH METRICS"
        sql_text = re.sub(
            pattern,
            rf"\1\n{clause}\nWITH METRICS",
            sql_text,
            count=1,
        )
    return sql_text


def render_metric_views(
    catalog: str,
    gold_schema: str,
    metrics_schema: str,
    metrics_catalog: str | None = None,
    gold_catalog: str | None = None,
) -> Path:
    metrics_catalog = metrics_catalog or catalog
    gold_catalog = gold_catalog or catalog
    tmpl_path = ROOT / "src/metrics/metric_views.sql.tmpl"
    out_path = ROOT / "src/metrics/metric_views.sql"
    text = tmpl_path.read_text()
    text = (
        text.replace("{{CATALOG}}", catalog)
        .replace("{{GOLD_CATALOG}}", gold_catalog)
        .replace("{{GOLD_SCHEMA}}", gold_schema)
        .replace("{{METRICS_CATALOG}}", metrics_catalog)
        .replace("{{METRICS_SCHEMA}}", metrics_schema)
    )
    out_path.write_text(text)
    print(f"Wrote {out_path}")
    return out_path


def render_genie_space(catalog: str, metrics_schema: str, metrics_catalog: str | None = None) -> Path:
    metrics_catalog = metrics_catalog or catalog
    out_path = ROOT / "src/genie/jira_analytics.geniespace.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tables = []
    for view in sorted(METRIC_VIEWS):
        identifier = f"{metrics_catalog}.{metrics_schema}.{view}"
        tables.append({
            "identifier": identifier,
            "column_configs": [
                {"column_name": c}
                for c in sorted(COLUMN_CONFIGS[view])
            ],
        })

    sample_questions = sorted(
        [{"id": _stable_id(f"q:{q}"), "question": [q]} for q in SAMPLE_QUESTIONS],
        key=lambda item: item["id"],
    )
    example_sqls = sorted(
        [{"id": _stable_id(f"sql:{i}"), **ex} for i, ex in enumerate(EXAMPLE_SQLS)],
        key=lambda item: item["id"],
    )

    space = {
        "version": 2,
        "config": {
            "sample_questions": sample_questions,
        },
        "data_sources": {"tables": tables},
        "instructions": {
            "text_instructions": [{
                "id": _stable_id("instructions:main"),
                "content": [GENIE_INSTRUCTIONS],
            }],
            "example_question_sqls": example_sqls,
        },
    }

    with open(out_path, "w") as f:
        json.dump(space, f, indent=2)
    print(f"Wrote {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate parameterized bundle artifacts")
    parser.add_argument("--catalog", default=None)
    parser.add_argument("--gold-catalog", default=None)
    parser.add_argument("--gold-schema", default=None)
    parser.add_argument("--metrics-catalog", default=None)
    parser.add_argument("--metrics-schema", default=None)
    parser.add_argument(
        "--regenerate-dashboard",
        action="store_true",
        help="Regenerate src/dashboard template (maintainers only)",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    from read_pipeline_config import layer_config  # noqa: E402

    cfg = layer_config()
    catalog = args.catalog or cfg["catalog"]
    gold_catalog = args.gold_catalog or cfg["gold_catalog"]
    gold_schema = args.gold_schema or cfg["gold_schema"]
    metrics_catalog = args.metrics_catalog or cfg["metrics_catalog"]
    metrics_schema = args.metrics_schema or cfg["metrics_schema"]

    render_metric_views(
        catalog,
        gold_schema,
        metrics_schema,
        metrics_catalog,
        gold_catalog,
    )
    render_genie_space(catalog, metrics_schema, metrics_catalog)
    if args.regenerate_dashboard:
        build_dashboard(
            ROOT / "src" / "dashboard" / "jira_analytics.lvdash.json",
            metrics_catalog="{dashboard_catalog}",
            metrics_schema="{dashboard_schema}",
        )
    print("Done.")


if __name__ == "__main__":
    main()
