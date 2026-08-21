#!/usr/bin/env bash
# Push the patched dashboard JSON to Lakeview via the update API.
#
# Normally you do not run this manually — it runs automatically after every
# `databricks bundle deploy` via scripts/postdeploy.sh (experimental.scripts.postdeploy).
# Use this script directly only to re-publish without a full deploy.
#
# Usage: ./scripts/push_dashboard.sh [-t dev|prod] [-p <profile>] [--no-publish]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DASHBOARD_JSON="$REPO_ROOT/dashboards/jira_analytics.lvdash.json"
TARGET="dev"
CLI_PROFILE="${DATABRICKS_CONFIG_PROFILE:-}"
PUBLISH=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target) TARGET="$2"; shift 2 ;;
    -p|--profile) CLI_PROFILE="$2"; shift 2 ;;
    --no-publish) PUBLISH=false; shift ;;
    -h|--help)
      echo "Usage: ./scripts/push_dashboard.sh [-t dev|prod] [-p <profile>] [--no-publish]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ ! -f "$DASHBOARD_JSON" ]]; then
  echo "ERROR: Missing $DASHBOARD_JSON — run ./scripts/sync_config.sh first." >&2
  exit 1
fi

BUNDLE_ARGS=(-t "$TARGET" -o json)
[[ -n "$CLI_PROFILE" ]] && BUNDLE_ARGS+=(-p "$CLI_PROFILE")

SUMMARY="$(databricks bundle summary "${BUNDLE_ARGS[@]}" 2>/dev/null)" || {
  echo "ERROR: databricks bundle summary failed. Run sync_config.sh and ensure the bundle is deployed." >&2
  exit 1
}

DASHBOARD_META="$(python3 - <<'PY' "$SUMMARY"
import json, sys
summary = json.loads(sys.argv[1])
dash = summary.get("resources", {}).get("dashboards", {}).get("jira_analytics_dashboard")
if not dash or not dash.get("id"):
    raise SystemExit(1)
print(json.dumps({
    "id": dash["id"],
    "display_name": dash.get("display_name", ""),
    "warehouse_id": dash.get("warehouse_id", ""),
}))
PY
)" || {
  echo "ERROR: Dashboard resource jira_analytics_dashboard not found in bundle summary." >&2
  echo "Deploy the bundle with a profile that includes the dashboard (with_dashboard or full)." >&2
  exit 1
}

DASHBOARD_ID="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['id'])" "$DASHBOARD_META")"
WAREHOUSE_ID="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['warehouse_id'])" "$DASHBOARD_META")"
CONFIG="$REPO_ROOT/config/pipeline.yaml"
if [[ -f "$CONFIG" ]]; then
  DISPLAY_NAME="$(grep '^dashboard_name:' "$CONFIG" | head -1 | sed 's/^dashboard_name:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/')"
fi
if [[ -z "${DISPLAY_NAME:-}" ]]; then
  DISPLAY_NAME="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['display_name'])" "$DASHBOARD_META")"
fi

if [[ -z "$DASHBOARD_ID" ]]; then
  echo "ERROR: Dashboard resource jira_analytics_dashboard not found in bundle summary." >&2
  echo "Deploy the bundle with a profile that includes the dashboard (with_dashboard or full)." >&2
  exit 1
fi

echo "Updating dashboard: $DISPLAY_NAME ($DASHBOARD_ID)"

python3 - <<'PY' "$DASHBOARD_JSON" "$DISPLAY_NAME" "$WAREHOUSE_ID" > /tmp/dashboard_update.json
import json, pathlib, sys
path, display_name, warehouse_id = sys.argv[1:4]
content = pathlib.Path(path).read_text()
json.loads(content)  # validate
payload = {
    "display_name": display_name,
    "warehouse_id": warehouse_id,
    "serialized_dashboard": content,
}
json.dump(payload, sys.stdout)
PY

UPDATE_ARGS=(lakeview update "$DASHBOARD_ID" --json @/tmp/dashboard_update.json)
[[ -n "$CLI_PROFILE" ]] && UPDATE_ARGS+=(-p "$CLI_PROFILE")
databricks "${UPDATE_ARGS[@]}"

if [[ "$PUBLISH" == true ]]; then
  echo "Publishing dashboard..."
  PUBLISH_ARGS=(lakeview publish "$DASHBOARD_ID" --json "{\"embed_credentials\":true,\"warehouse_id\":\"$WAREHOUSE_ID\"}")
  [[ -n "$CLI_PROFILE" ]] && PUBLISH_ARGS+=(-p "$CLI_PROFILE")
  databricks "${PUBLISH_ARGS[@]}"
fi

VERIFY_ARGS=(-t "$TARGET")
[[ -n "$CLI_PROFILE" ]] && VERIFY_ARGS+=(-p "$CLI_PROFILE")
"$REPO_ROOT/scripts/verify_dashboard.sh" "${VERIFY_ARGS[@]}" || true

echo "Done. Dashboard widgets are wired from $DASHBOARD_JSON"
