#!/usr/bin/env bash
# Bundle post-deploy hook: wire Lakeview dashboard widgets after bundle deploy.
#
# bundle deploy via file_path leaves widgets as empty shells (queries: [] / encodings: {}).
# This script runs push_dashboard.sh when the bundle includes jira_genie_dashboard.
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
# Write summary JSON to a temp file and pass its PATH to python. The summary is large; passing
# it via an env var or argv overflows the exec arg/env limit ("Argument list too long").
SUMMARY_FILE="$(mktemp)"
trap 'rm -f "$SUMMARY_FILE"' EXIT
databricks bundle summary "${SUMMARY_ARGS[@]}" > "$SUMMARY_FILE" 2>/dev/null || {
  echo "postdeploy: bundle summary failed — skip dashboard push (run push_dashboard.sh manually)" >&2
  exit 0
}

HAS_DASH="$(SUMMARY_FILE="$SUMMARY_FILE" python3 - <<'PY'
import json, os
with open(os.environ["SUMMARY_FILE"]) as fh:
    d = json.load(fh)
dash = d.get("resources", {}).get("dashboards", {}).get("jira_genie_dashboard")
print("1" if dash and dash.get("id") else "0")
PY
)"

if [[ "$HAS_DASH" != "1" ]]; then
  echo "postdeploy: no jira_genie_dashboard in bundle — skipping dashboard widget wiring"
  exit 0
fi

echo "postdeploy: wiring dashboard widgets and publishing..."
bash "$REPO_ROOT/scripts/push_dashboard.sh" "${ARGS[@]}"
