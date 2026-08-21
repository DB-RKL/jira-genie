#!/usr/bin/env bash
# Bundle post-deploy hook: wire Lakeview dashboard widgets after bundle deploy.
#
# bundle deploy via file_path leaves widgets as empty shells (queries: [] / encodings: {}).
# This script runs push_dashboard.sh when the bundle includes jira_analytics_dashboard.
#
# Invoked automatically from databricks.yml experimental.scripts.postdeploy.
# Also safe to run manually after bundle deploy.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${DATABRICKS_BUNDLE_TARGET:-dev}"
PROFILE="${DATABRICKS_CONFIG_PROFILE:-}"

ARGS=(-t "$TARGET")
[[ -n "$PROFILE" ]] && ARGS+=(-p "$PROFILE")

SUMMARY_ARGS=("${ARGS[@]}" -o json)
summary="$(databricks bundle summary "${SUMMARY_ARGS[@]}" 2>/dev/null)" || {
  echo "postdeploy: bundle summary failed — skip dashboard push (run push_dashboard.sh manually)" >&2
  exit 0
}

HAS_DASH="$(SUMMARY_JSON="$summary" python3 - <<'PY'
import json, os, sys
d = json.loads(os.environ["SUMMARY_JSON"])
dash = d.get("resources", {}).get("dashboards", {}).get("jira_analytics_dashboard")
print("1" if dash and dash.get("id") else "0")
PY
)"

if [[ "$HAS_DASH" != "1" ]]; then
  echo "postdeploy: no jira_analytics_dashboard in bundle — skipping dashboard widget wiring"
  exit 0
fi

echo "postdeploy: wiring dashboard widgets and publishing..."
"$REPO_ROOT/scripts/push_dashboard.sh" "${ARGS[@]}"
