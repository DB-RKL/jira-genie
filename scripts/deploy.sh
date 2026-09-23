#!/usr/bin/env bash
# Recommended deploy entrypoint: sync config, bundle deploy, auto-wire dashboard.
#
# bundle deploy triggers experimental.scripts.postdeploy (push_dashboard.sh) when
# the deployment profile includes jira_genie_dashboard.
#
# Usage: ./scripts/deploy.sh [-t dev|prod] [-p <profile>] [--skip-sync] [--skip-ingestion]
#                            [-- <bundle deploy args>]
#
# --skip-ingestion deploys every resource except the Lakeflow Connect ingestion pipeline.
# Use it when bronze tables already exist or the workspace has no JIRA-type connection; the
# setup job (silver -> gold -> metrics) does not depend on ingestion and still deploys.
#
# Args after -- are passed through to 'databricks bundle deploy', e.g.
#   ./scripts/deploy.sh -t dev -p myprofile -- --select schemas.bronze,pipelines.jira_silver_pipeline

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="dev"
CLI_PROFILE="${DATABRICKS_CONFIG_PROFILE:-}"
SKIP_SYNC=false
SKIP_INGESTION=false
PASSTHROUGH=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target) TARGET="$2"; shift 2 ;;
    -p|--profile) CLI_PROFILE="$2"; shift 2 ;;
    --skip-sync) SKIP_SYNC=true; shift ;;
    --skip-ingestion) SKIP_INGESTION=true; shift ;;
    --) shift; PASSTHROUGH=("$@"); break ;;
    -h|--help)
      echo "Usage: ./scripts/deploy.sh [-t dev|prod] [-p <profile>] [--skip-sync] [--skip-ingestion]"
      echo "                           [-- <bundle deploy args>]"
      echo ""
      echo "Runs sync_config.sh, then databricks bundle deploy."
      echo "Dashboard widget wiring runs automatically via postdeploy hook when applicable."
      echo ""
      echo "  --skip-ingestion  Deploy all resources except the Lakeflow Connect ingestion"
      echo "                    pipeline. Use when bronze already exists or there is no"
      echo "                    JIRA-type connection."
      echo "  --                Forward remaining args to 'databricks bundle deploy'."
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

export DATABRICKS_BUNDLE_TARGET="$TARGET"
[[ -n "$CLI_PROFILE" ]] && export DATABRICKS_CONFIG_PROFILE="$CLI_PROFILE"

SYNC_ARGS=(-t "$TARGET")
DEPLOY_ARGS=(-t "$TARGET")
[[ -n "$CLI_PROFILE" ]] && SYNC_ARGS+=(-p "$CLI_PROFILE") && DEPLOY_ARGS+=(-p "$CLI_PROFILE")

if [[ "$SKIP_SYNC" == false ]]; then
  echo "==> Syncing config and regenerating artifacts..."
  "$REPO_ROOT/scripts/sync_config.sh" "${SYNC_ARGS[@]}"
fi

DEPLOY_EXTRA=()
if [[ -f "$REPO_ROOT/config/pipeline.yaml" ]]; then
  DEPLOY_PROFILE="$(grep '^deployment_profile:' "$REPO_ROOT/config/pipeline.yaml" | head -1 | sed 's/^deployment_profile:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/')"
  if [[ "$DEPLOY_PROFILE" == "full" || "$DEPLOY_PROFILE" == "with_dashboard" ]]; then
    DEPLOY_EXTRA+=(--force)
    echo "==> Dashboard profile ($DEPLOY_PROFILE): using bundle deploy --force"
    echo "    (postdeploy push_dashboard updates the remote dashboard via Lakeview API after each deploy)"
  fi
fi

if [[ "$SKIP_INGESTION" == true ]]; then
  # Use `bundle validate` (config only) rather than `bundle summary` (config + deployed
  # state): summary can list resources that were removed from config but still linger in
  # state, and passing those to --select fails with "no such resource".
  CONFIG_JSON="$(databricks bundle validate "${DEPLOY_ARGS[@]}" -o json 2>/dev/null)" \
    || { echo "ERROR: bundle validate failed — cannot compute --select list" >&2; exit 1; }
  SELECT_LIST="$(CONFIG_JSON="$CONFIG_JSON" python3 - <<'PY'
import json, os

# Only the ingestion pipeline is excluded; the setup job (silver -> gold -> metrics)
# no longer depends on it, so it still deploys and is runnable from the UI.
EXCLUDED = {"pipelines.jira_ingestion_pipeline"}
resources = json.loads(os.environ["CONFIG_JSON"]).get("resources", {})
keys = [f"{kind}.{name}" for kind, items in resources.items() for name in items]
print(",".join(k for k in sorted(keys) if k not in EXCLUDED))
PY
)"
  [[ -n "$SELECT_LIST" ]] || { echo "ERROR: no deployable resources found" >&2; exit 1; }
  DEPLOY_EXTRA+=(--select "$SELECT_LIST")
  echo "==> Skipping ingestion pipeline; deploying:"
  echo "    ${SELECT_LIST//,/, }"
fi

((${#PASSTHROUGH[@]} > 0)) && DEPLOY_EXTRA+=("${PASSTHROUGH[@]}")

echo "==> Deploying bundle (dashboard widgets wired automatically when profile includes dashboard)..."
if ((${#DEPLOY_EXTRA[@]} > 0)); then
  databricks bundle deploy "${DEPLOY_ARGS[@]}" "${DEPLOY_EXTRA[@]}"
else
  databricks bundle deploy "${DEPLOY_ARGS[@]}"
fi

echo ""
echo "Deploy complete. Verify dashboard with:"
echo "  ./scripts/verify_dashboard.sh ${SYNC_ARGS[*]}"
