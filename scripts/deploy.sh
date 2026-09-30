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
ONLY_GENIE=false
WITH_GENIE=false
PASSTHROUGH=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target) TARGET="$2"; shift 2 ;;
    -p|--profile) CLI_PROFILE="$2"; shift 2 ;;
    --skip-sync) SKIP_SYNC=true; shift ;;
    --skip-ingestion) SKIP_INGESTION=true; shift ;;
    --only-genie) ONLY_GENIE=true; shift ;;
    --with-genie) WITH_GENIE=true; shift ;;
    --) shift; PASSTHROUGH=("$@"); break ;;
    -h|--help)
      echo "Usage: ./scripts/deploy.sh [-t dev|prod] [-p <profile>] [--skip-sync] [--skip-ingestion]"
      echo "                           [--only-genie] [--with-genie] [-- <bundle deploy args>]"
      echo ""
      echo "Runs sync_config.sh, then databricks bundle deploy."
      echo "Dashboard widget wiring runs automatically via postdeploy hook when applicable."
      echo ""
      echo "  --skip-ingestion  Deploy all resources except the Lakeflow Connect ingestion"
      echo "                    pipeline. Use when bronze already exists or there is no"
      echo "                    JIRA-type connection."
      echo "  --only-genie      Deploy ONLY the Genie space. Use after the setup job has built"
      echo "                    the metric views (Genie creation validates the tables exist)."
      echo "  --with-genie      Include the Genie space in this deploy. By default the Genie"
      echo "                    space is deferred (see --only-genie) because it fails until the"
      echo "                    metric views exist."
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

DEPLOY_PROFILE=""
if [[ -f "$REPO_ROOT/config/pipeline.yaml" ]]; then
  DEPLOY_PROFILE="$(grep '^deployment_profile:' "$REPO_ROOT/config/pipeline.yaml" | head -1 | sed 's/^deployment_profile:[[:space:]]*"\{0,1\}\([^"]*\)"\{0,1\}[[:space:]]*$/\1/')"
fi
PROFILE_HAS_GENIE=false
[[ "$DEPLOY_PROFILE" == "full" || "$DEPLOY_PROFILE" == "with_genie" ]] && PROFILE_HAS_GENIE=true

GENIE_RESOURCE="genie_spaces.jira_genie_space"

# --only-genie: deploy just the Genie space (after the setup job has built metric views) and stop.
# --force: the postdeploy hook wires the dashboard widgets via the Lakeview API, which the
# bundle sees as a remote modification; without --force the deploy aborts ("modified remotely").
if [[ "$ONLY_GENIE" == true ]]; then
  echo "==> Deploying only the Genie space ($GENIE_RESOURCE)..."
  databricks bundle deploy "${DEPLOY_ARGS[@]}" --select "$GENIE_RESOURCE" --force
  echo "Genie space deployed."
  exit 0
fi

DEPLOY_EXTRA=()
if [[ "$DEPLOY_PROFILE" == "full" || "$DEPLOY_PROFILE" == "with_dashboard" ]]; then
  DEPLOY_EXTRA+=(--force)
  echo "==> Dashboard profile ($DEPLOY_PROFILE): using bundle deploy --force"
  echo "    (postdeploy push_dashboard updates the remote dashboard via Lakeview API after each deploy)"
fi

# Decide which resources to exclude from this pass.
#  - ingestion: excluded on --skip-ingestion (no connection / bronze already exists)
#  - Genie space: deferred by default when the profile includes it, because Genie creation
#    validates that every referenced metric view already exists — and those are only built by
#    the setup job, which runs AFTER deploy. Deploy it later with --only-genie (or force it in
#    now with --with-genie once the metric views exist).
DEFER_GENIE=false
if [[ "$PROFILE_HAS_GENIE" == true && "$WITH_GENIE" == false ]]; then
  DEFER_GENIE=true
fi

if [[ "$SKIP_INGESTION" == true || "$DEFER_GENIE" == true ]]; then
  # Use `bundle validate` (config only) rather than `bundle summary` (config + deployed
  # state): summary can list resources that were removed from config but still linger in
  # state, and passing those to --select fails with "no such resource".
  # Write the (large) validate JSON to a temp file and pass its PATH to python. Passing the
  # JSON itself via an env var overflows the exec env-size limit ("Argument list too long").
  CONFIG_FILE="$(mktemp)"
  databricks bundle validate "${DEPLOY_ARGS[@]}" -o json > "$CONFIG_FILE" 2>/dev/null \
    || { echo "ERROR: bundle validate failed — cannot compute --select list" >&2; rm -f "$CONFIG_FILE"; exit 1; }
  SELECT_LIST="$(SKIP_INGESTION="$SKIP_INGESTION" DEFER_GENIE="$DEFER_GENIE" CONFIG_FILE="$CONFIG_FILE" python3 - <<'PY'
import json, os

excluded = set()
if os.environ.get("SKIP_INGESTION") == "true":
    excluded.add("pipelines.jira_ingestion_pipeline")
if os.environ.get("DEFER_GENIE") == "true":
    excluded.add("genie_spaces.jira_genie_space")
with open(os.environ["CONFIG_FILE"]) as fh:
    resources = json.load(fh).get("resources", {})
keys = [f"{kind}.{name}" for kind, items in resources.items() for name in items]
print(",".join(k for k in sorted(keys) if k not in excluded))
PY
)"
  rm -f "$CONFIG_FILE"
  [[ -n "$SELECT_LIST" ]] || { echo "ERROR: no deployable resources found" >&2; exit 1; }
  DEPLOY_EXTRA+=(--select "$SELECT_LIST")
  [[ "$SKIP_INGESTION" == true ]] && echo "==> Skipping ingestion pipeline"
  [[ "$DEFER_GENIE" == true ]] && echo "==> Deferring Genie space (needs metric views first — see below)"
  echo "==> Deploying: ${SELECT_LIST//,/, }"
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

if [[ "$DEFER_GENIE" == true ]]; then
  echo ""
  echo "NOTE: the Genie space was deferred. It can only be created after the metric views exist."
  echo "  1) Ensure bronze is populated (Lakeflow Connect ingestion has run at least once)"
  echo "  2) Build silver -> gold -> metric views:"
  echo "       databricks bundle run jira_genie_setup ${SYNC_ARGS[*]}"
  echo "  3) Deploy the Genie space:"
  echo "       ./scripts/deploy.sh ${SYNC_ARGS[*]} --skip-sync --only-genie"
fi
