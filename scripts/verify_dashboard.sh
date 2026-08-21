#!/usr/bin/env bash
# Diagnose why a Lakeview dashboard shows no data.
#
# Checks: patched JSON placeholders, widget wiring (local + remote), metric view SQL,
# and a sample KPI query against the warehouse.
#
# Usage: ./scripts/verify_dashboard.sh [-t dev|prod] [-p <profile>]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DASHBOARD_JSON="$REPO_ROOT/dashboards/jira_analytics.lvdash.json"
TARGET="dev"
CLI_PROFILE="${DATABRICKS_CONFIG_PROFILE:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target) TARGET="$2"; shift 2 ;;
    -p|--profile) CLI_PROFILE="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: ./scripts/verify_dashboard.sh [-t dev|prod] [-p <profile>]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

DB_ARGS=()
[[ -n "$CLI_PROFILE" ]] && DB_ARGS+=(-p "$CLI_PROFILE")

fail() { echo "FAIL: $*" >&2; exit 1; }
warn() { echo "WARN: $*" >&2; }
ok() { echo "OK:   $*"; }

[[ -f "$DASHBOARD_JSON" ]] || fail "Missing $DASHBOARD_JSON — run ./scripts/sync_config.sh first."

if grep -q '{dashboard_catalog}\|{dashboard_schema}' "$DASHBOARD_JSON"; then
  fail "Dashboard JSON still has placeholders — re-run ./scripts/sync_config.sh -t $TARGET ${CLI_PROFILE:+-p $CLI_PROFILE}"
fi
ok "Local dashboard JSON is patched (no placeholders)"

LOCAL_STATS="$(python3 - <<'PY' "$DASHBOARD_JSON"
import json, pathlib, sys
d = json.loads(pathlib.Path(sys.argv[1]).read_text())
layout = [item for p in d["pages"] for item in p["layout"]]
empty = [
    item["widget"]["spec"]["frame"]["title"]
    for item in layout
    if not item["widget"].get("queries") or not item["widget"]["spec"].get("encodings")
]
ds = next(x for x in d["datasets"] if x["name"] == "ds_project_health")
sql = ds["queryLines"][0]
# extract FQN before metric view name
fqn = sql.split("FROM", 1)[1].strip().rsplit(".", 1)[0]
print(len(layout), len(empty), fqn)
PY
)"
read -r LOCAL_WIDGETS LOCAL_EMPTY METRICS_FQN <<<"$LOCAL_STATS"
ok "Local JSON: $LOCAL_WIDGETS widgets, $LOCAL_EMPTY without queries/encodings"
if [[ "$LOCAL_EMPTY" -gt 0 ]]; then
  fail "Local dashboard template has unwired widgets — regenerate with build_assets.py"
fi
echo "      Metrics target: $METRICS_FQN"

BUNDLE_ARGS=(-t "$TARGET" -o json "${DB_ARGS[@]}")
SUMMARY="$(databricks bundle summary "${BUNDLE_ARGS[@]}" 2>/dev/null)" || fail "bundle summary failed — authenticate and deploy first"

DASHBOARD_ID="$(python3 -c "
import json,sys
d=json.loads(sys.argv[1])
print(d.get('resources',{}).get('dashboards',{}).get('jira_analytics_dashboard',{}).get('id',''))
" "$SUMMARY")"
WAREHOUSE_ID="$(python3 -c "
import json,sys
d=json.loads(sys.argv[1])
print(d.get('resources',{}).get('dashboards',{}).get('jira_analytics_dashboard',{}).get('warehouse_id',''))
" "$SUMMARY")"
[[ -n "$DASHBOARD_ID" ]] || fail "Dashboard not deployed in this workspace/target"

REMOTE_JSON="$(mktemp)"
databricks lakeview get "$DASHBOARD_ID" "${DB_ARGS[@]}" -o json > "$REMOTE_JSON"
WORKSPACE_EXPORT="$(mktemp)"
DASH_PATH="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('path',''))" "$REMOTE_JSON")"
if [[ -n "$DASH_PATH" ]]; then
  databricks workspace export "$DASH_PATH" "${DB_ARGS[@]}" --file "$WORKSPACE_EXPORT" 2>/dev/null || true
fi
PUBLISHED_JSON="$(mktemp)"
databricks api get "/api/2.0/lakeview/dashboards/${DASHBOARD_ID}/published" "${DB_ARGS[@]}" -o json > "$PUBLISHED_JSON" 2>/dev/null || echo '{}' > "$PUBLISHED_JSON"

REMOTE_STATS="$(python3 - <<'PY' "$REMOTE_JSON" "$WORKSPACE_EXPORT"
import json, pathlib, sys
remote = json.load(open(sys.argv[1]))
sd = json.loads(remote["serialized_dashboard"])
layout = [item for p in sd["pages"] for item in p.get("layout", [])]
empty = sum(
    1 for item in layout
    if not item["widget"].get("queries") or not item["widget"]["spec"].get("encodings")
)
ws_empty = None
ws_path = sys.argv[2]
if pathlib.Path(ws_path).exists() and pathlib.Path(ws_path).stat().st_size > 0:
    ws = json.load(open(ws_path))
    ws_layout = [item for p in ws["pages"] for item in p.get("layout", [])]
    ws_empty = sum(
        1 for item in ws_layout
        if not item["widget"].get("queries") or not item["widget"]["spec"].get("encodings")
    )
print(json.dumps({
    "display_name": remote.get("display_name", ""),
    "widgets": len(layout),
    "empty": empty,
    "workspace_empty": ws_empty,
}))
PY
)"
REMOTE_NAME="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['display_name'])" "$REMOTE_STATS")"
REMOTE_WIDGETS="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['widgets'])" "$REMOTE_STATS")"
REMOTE_EMPTY="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['empty'])" "$REMOTE_STATS")"
WORKSPACE_EMPTY="$(python3 -c "import json,sys; v=json.loads(sys.argv[1]).get('workspace_empty'); print(v if v is not None else -1)" "$REMOTE_STATS")"
echo "Remote dashboard: $REMOTE_NAME ($DASHBOARD_ID)"
if [[ "$REMOTE_EMPTY" -gt 0 ]]; then
  fail "$REMOTE_EMPTY/$REMOTE_WIDGETS remote widgets are empty shells — run ./scripts/push_dashboard.sh -t $TARGET ${CLI_PROFILE:+-p $CLI_PROFILE}"
fi
if [[ "$WORKSPACE_EMPTY" -ge 0 && "$WORKSPACE_EMPTY" -gt 0 ]]; then
  fail "$WORKSPACE_EMPTY/$REMOTE_WIDGETS workspace file widgets are empty shells (bundle deploy stripped bindings) — run ./scripts/push_dashboard.sh -t $TARGET ${CLI_PROFILE:+-p $CLI_PROFILE}"
fi
ok "Remote dashboard: all $REMOTE_WIDGETS widgets wired"

WAREHOUSE_STATE="$(databricks api get "/api/2.0/sql/warehouses/${WAREHOUSE_ID}" "${DB_ARGS[@]}" -o json 2>/dev/null | python3 -c "import json,sys; w=json.load(sys.stdin); print(w.get('state','UNKNOWN'))" || echo "UNKNOWN")"
echo "      Warehouse $WAREHOUSE_ID state: $WAREHOUSE_STATE"

TEST_SQL="SELECT MEASURE(\`Open Issues\`) AS total_open FROM ${METRICS_FQN}.metric_project_health"
WIDGET_SQL="SELECT SUM(open_issues) AS value FROM (SELECT \`Project Key\` AS project_key, \`Project Name\` AS project_name, MEASURE(\`Open Issues\`) AS open_issues, MEASURE(\`Open Critical\`) AS open_critical, MEASURE(\`Stale Open\`) AS stale_open, MEASURE(\`Avg Cycle Time (days)\`) AS avg_cycle_time_days, MEASURE(\`Resolved Issues (30d)\`) AS resolved_last_30d, MEASURE(\`Created Issues (30d)\`) AS created_last_30d FROM ${METRICS_FQN}.metric_project_health GROUP BY \`Project Key\`, \`Project Name\`)"
BAR_SQL="SELECT \`project_key\`, COUNT(*) AS count, \`priority\` FROM (SELECT \`Issue Key\` AS issue_key, \`Summary\` AS summary, \`Project Key\` AS project_key, \`Assignee\` AS assignee_name, \`Priority\` AS priority, \`Age (days)\` AS age_days, \`Status Category\` AS status_category, \`Issue Type\` AS issue_type, \`Is Resolved\` AS is_resolved, \`Cycle Time (days)\` AS cycle_time_days, \`Lead Time (days)\` AS lead_time_days, \`Age Bucket\` AS age_bucket FROM ${METRICS_FQN}.metric_issue WHERE NOT \`Is Resolved\`) GROUP BY \`project_key\`, \`priority\`"
echo "Running: $TEST_SQL"
SQL_RESULT="$(mktemp)"
SQL_PAYLOAD="$(python3 - <<PY
import json
print(json.dumps({
    "warehouse_id": "$WAREHOUSE_ID",
    "statement": """$TEST_SQL""",
    "wait_timeout": "50s",
}))
PY
)"
if databricks api post /api/2.0/sql/statements "${DB_ARGS[@]}" --json "$SQL_PAYLOAD" -o json > "$SQL_RESULT" 2>/dev/null; then
  python3 - <<'PY' "$SQL_RESULT" "$WIDGET_SQL" "$BAR_SQL" "$WAREHOUSE_ID" "${DB_ARGS[*]}"
import json, subprocess, sys

def run_sql(statement, warehouse_id, profile_args):
    import shlex
    args = shlex.split(profile_args)
    payload = json.dumps({"warehouse_id": warehouse_id, "statement": statement, "wait_timeout": "50s"})
    proc = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements", *args, "--json", payload, "-o", "json"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return {"state": "CLI_ERROR", "error": proc.stderr[:300], "data": None}
    r = json.loads(proc.stdout)
    return {
        "state": r.get("status", {}).get("state"),
        "error": r.get("status", {}).get("error"),
        "data": r.get("result", {}).get("data_array"),
    }

sql_result, widget_sql, bar_sql, warehouse_id, profile_args = sys.argv[1:6]
r = json.load(open(sql_result))
state = r.get("status", {}).get("state")
err = r.get("status", {}).get("error", {})
data = r.get("result", {}).get("data_array")
widget = run_sql(widget_sql, warehouse_id, profile_args)
bar = run_sql(bar_sql, warehouse_id, profile_args)
if state != "SUCCEEDED":
    print(f"FAIL: metric query {state}: {err.get('message', err)}")
    sys.exit(1)
if not data or data[0][0] in (None, "", "0"):
    print(f"WARN: metric query succeeded but returned {data!r} — run jira_analytics_refresh")
else:
    print(f"OK:   metric_project_health total_open = {data[0][0]}")
print("OK:   widget Total open SQL =", widget.get("data"))
print("OK:   bar chart SQL rows =", len(bar.get("data") or []))
PY
else
  warn "Could not run SQL (warehouse may be stopped). Start warehouse $WAREHOUSE_ID and retry."
fi

PUBLISHED_STALE="$(PUBLISHED_JSON="$PUBLISHED_JSON" python3 - <<'PY'
import json, os
print(json.load(open(os.environ["PUBLISHED_JSON"])).get("revision_create_time", ""))
PY
)"
DRAFT_UPDATE="$(REMOTE_JSON="$REMOTE_JSON" python3 - <<'PY'
import json, os
print(json.load(open(os.environ["REMOTE_JSON"])).get("update_time", ""))
PY
)"
if [[ -n "$PUBLISHED_STALE" && -n "$DRAFT_UPDATE" && "$DRAFT_UPDATE" > "$PUBLISHED_STALE" ]]; then
  warn "Draft ($DRAFT_UPDATE) is newer than published revision ($PUBLISHED_STALE) — republish required"
fi

rm -f "$REMOTE_JSON" "$SQL_RESULT" "$PUBLISHED_JSON" "$WORKSPACE_EXPORT"
echo ""
echo "If widgets still look empty in the browser:"
echo "  1. Run ./scripts/push_dashboard.sh -t $TARGET ${CLI_PROFILE:+-p $CLI_PROFILE}"
echo "  2. Hard-refresh the published dashboard URL (not draft)"
echo "  3. Run: databricks bundle run jira_analytics_refresh -t $TARGET ${CLI_PROFILE:+-p $CLI_PROFILE}"
