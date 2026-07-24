#!/usr/bin/env python3
"""Generate all parameterized bundle artifacts from templates.

Outputs:
  - src/metrics/metric_views.sql       (from metric_views.sql.tmpl)
  - src/genie/jira_analytics.geniespace.json
  - dashboards/jira_analytics.lvdash.json (via build_dashboard)

Usage:
  python scripts/build_assets.py
  python scripts/build_assets.py --catalog my_catalog --gold-schema gold --metrics-schema metrics
"""

from __future__ import annotations

import argparse
import json
import os
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
        "Issue Key", "Summary", "Project Key", "Issue Type", "Status",
        "Status Category", "Priority", "Assignee", "Age Bucket", "Is Resolved",
    ],
    "metric_sprint_velocity": ["Sprint", "Sprint State", "Project Key", "Start Date", "Complete Date"],
    "metric_issue_transitions": ["Project Key", "From Status", "To Status", "To Category"],
    "metric_worklog": ["Project Key", "Author", "Work Date"],
    "metric_project_health": ["Project Key", "Project Name"],
    "metric_assignee_load": ["Assignee", "Project Key", "Priority", "Age Bucket"],
    "metric_team_productivity": ["Assignee"],
    "metric_time_in_status": ["Project Key", "Status", "Status Category"],
}

GENIE_INSTRUCTIONS = """You answer questions about Jira delivery analytics using governed Unity Catalog metric views.

Always query the metric views in the metrics schema. Use the MEASURE() function for KPIs — never re-implement aggregations manually.

Glossary
- Issue / ticket — a Jira work item (Issue Key, e.g. DATA-123).
- Status category — To Do (new), In Progress (indeterminate), Done (done).
- Open — not resolved (Is Resolved = false).
- Cycle time — days from first In Progress to resolution (Median Cycle Time measure on metric_issue).
- Lead time — days from creation to resolution (Avg Lead Time measure on metric_issue).
- Velocity — Points Completed on metric_sprint_velocity for closed sprints.
- Critical — priority in Blocker, Critical, Highest (Open Critical measure).
- Time in status — P50/P90 Duration (hours) on metric_issue_transitions or metric_time_in_status.

Metric views (single source of truth)
- metric_issue — issue backlog, cycle/lead time, aging
- metric_sprint_velocity — sprint velocity, completion ratio
- metric_issue_transitions — workflow transitions, time-in-status
- metric_worklog — logged hours by contributor
- metric_project_health — portfolio KPIs per project
- metric_assignee_load — open load by assignee and priority
- metric_team_productivity — resolver throughput
- metric_time_in_status — p50/p90 hours per status

Example pattern:
  SELECT `Project Key`, MEASURE(`Open Issues`), MEASURE(`Open Critical`)
  FROM metric_project_health
  GROUP BY `Project Key`
  ORDER BY 2 DESC
"""

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
]


def _stable_id(seed: str) -> str:
    n = abs(hash(seed)) % (10**32)
    return f"{n:032x}"


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
    parser.add_argument("--skip-dashboard", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    from read_pipeline_config import layer_config  # noqa: E402

    cfg = layer_config()
    catalog = args.catalog or cfg["catalog"]
    gold_catalog = args.gold_catalog or cfg["gold_catalog"]
    gold_schema = args.gold_schema or cfg["gold_schema"]
    metrics_catalog = args.metrics_catalog or cfg["metrics_catalog"]
    metrics_schema = args.metrics_schema or cfg["metrics_schema"]

    render_metric_views(catalog, gold_schema, metrics_schema, metrics_catalog, gold_catalog)
    render_genie_space(catalog, metrics_schema, metrics_catalog)
    if not args.skip_dashboard:
        build_dashboard(ROOT / "dashboards" / "jira_analytics.lvdash.json")
    print("Done.")


if __name__ == "__main__":
    main()
