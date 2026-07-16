#!/usr/bin/env bash
# Create the Jira Analytics Genie Space.
#
# Genie spaces are not yet first-class in DAB, so we provision via REST API.
# Run AFTER the gold pipeline has produced its tables.
#
# Usage:
#   PROFILE=fe-vm-graphrag ./scripts/create_genie_space.sh
#
# Prints the space ID on success. Save it into ~/jira-analytics-board/app.yaml
# as GENIE_SPACE_ID so the "Ask Jira" page in the app can call it.

set -euo pipefail

PROFILE="${PROFILE:-fe-vm-graphrag}"
HOST="$(databricks auth env --profile "$PROFILE" 2>/dev/null | awk -F= '/DATABRICKS_HOST/{print $2}' | tr -d '"' || true)"
HOST="${HOST:-https://fevm-serverless-stable-wx20co.cloud.databricks.com}"
TOKEN="$(databricks auth token --host "$HOST" --profile "$PROFILE" 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])')"
WAREHOUSE_ID="${WAREHOUSE_ID:-ced20c73f16a2915}"
CATALOG="${CATALOG:-rubjit_jira}"

INSTRUCTIONS=$(cat <<'EOT'
You answer questions about Jira data ingested via Databricks Lakeflow Connect.

Glossary
- "Issue" / "ticket" — a Jira work item. Identified by issue_key (e.g. DATA-123).
- "Status category" buckets: "new" (To Do), "indeterminate" (In Progress), "done" (Done/Resolved).
- "Resolved" — issues with a non-null resolved_at; equivalent to status_category_key = 'done'.
- "Open" — issues with status_category_key in ('new', 'indeterminate').
- "Cycle time" — days between first In Progress entry and resolution (column cycle_time_days in fct_issue).
- "Lead time" — days between creation and resolution (column lead_time_days in fct_issue).
- "Story points" — column story_points in fct_issue (NULL when not set).
- "Sprint state": active, closed, future. Only closed sprints have meaningful velocity.
- "Velocity" — points_completed in fct_sprint_velocity for closed sprints.
- "Critical" issues — priority in ('Blocker', 'Critical', 'Highest').

Default to the gold marts (fct_issue, fct_sprint_velocity, agg_*). Only query silver when a user
asks for fields not in gold.
EOT
)

# Tables to expose to the Genie space.
TABLES=(
  "$CATALOG.gold.fct_issue"
  "$CATALOG.gold.fct_issue_transitions"
  "$CATALOG.gold.fct_sprint_velocity"
  "$CATALOG.gold.fct_worklog"
  "$CATALOG.gold.dim_user"
  "$CATALOG.gold.dim_project"
  "$CATALOG.gold.dim_status"
  "$CATALOG.gold.dim_sprint"
  "$CATALOG.gold.agg_assignee_load"
  "$CATALOG.gold.agg_project_health"
  "$CATALOG.gold.agg_team_productivity"
  "$CATALOG.gold.agg_time_in_status"
  "$CATALOG.silver.issue"
  "$CATALOG.silver.sprint"
  "$CATALOG.silver.project"
)

TABLES_JSON=$(printf '%s\n' "${TABLES[@]}" | python3 -c '
import json, sys
tables = [t.strip() for t in sys.stdin if t.strip()]
print(json.dumps([{"name": t} for t in tables]))
')

EXAMPLE_QUESTIONS=$(cat <<'EOT'
[
  "What was the velocity (points_completed) for the last 5 closed sprints?",
  "Which 10 assignees resolved the most issues in the last 30 days?",
  "How is cycle time trending month over month for project DATA?",
  "Which projects have the most open critical issues?",
  "Show me the oldest open bugs and who they're assigned to",
  "What's the average time in 'In Review' status across all projects?",
  "Compare planned vs completed story points for closed sprints this quarter",
  "Which sprints had the worst completion ratio?",
  "Top 10 contributors by total worklog hours last 90 days",
  "Distribution of resolution types across all closed issues"
]
EOT
)

PAYLOAD=$(python3 -c '
import json, os, sys
print(json.dumps({
  "title": "Jira Analytics",
  "description": "Natural-language Q&A over the Jira analytics gold/silver tables.",
  "warehouse_id": os.environ["WAREHOUSE_ID"],
  "tables": json.loads(os.environ["TABLES_JSON"]),
  "instructions": os.environ["INSTRUCTIONS"],
  "example_questions": json.loads(os.environ["EXAMPLE_QUESTIONS"]),
}))
' WAREHOUSE_ID="$WAREHOUSE_ID" TABLES_JSON="$TABLES_JSON" INSTRUCTIONS="$INSTRUCTIONS" EXAMPLE_QUESTIONS="$EXAMPLE_QUESTIONS")

RESPONSE=$(curl -fsS -X POST "$HOST/api/2.0/genie/spaces" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

SPACE_ID=$(echo "$RESPONSE" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("space_id") or json.load(open("/dev/stdin")).get("id",""))' 2>/dev/null || true)
if [ -z "$SPACE_ID" ]; then
  SPACE_ID=$(echo "$RESPONSE" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("space_id") or d.get("id",""))')
fi

echo "Created Genie Space: $SPACE_ID"
echo "Full response:"
echo "$RESPONSE" | python3 -m json.tool

echo ""
echo "Next: add to ~/jira-analytics-board/app.yaml:"
echo "  - name: GENIE_SPACE_ID"
echo "    value: \"$SPACE_ID\""
