#!/usr/bin/env bash
# Sync config/pipeline.yaml values into databricks.yml and generated artifacts.
# Run this after editing pipeline.yaml — before 'databricks bundle deploy'.
#
# Usage: ./scripts/sync_config.sh [-t dev]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$REPO_ROOT/config/pipeline.yaml"
EXAMPLE="$REPO_ROOT/config/pipeline.example.yaml"
BUNDLE="$REPO_ROOT/databricks.yml"
TARGET="dev"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t|--target) TARGET="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: ./scripts/sync_config.sh [-t dev|prod]"
      exit 0
      ;;
    *) shift ;;
  esac
done

if [[ ! -f "$CONFIG" ]]; then
  if [[ -f "$EXAMPLE" ]]; then
    echo "No config/pipeline.yaml found — copying from pipeline.example.yaml"
    cp "$EXAMPLE" "$CONFIG"
    echo "Edit config/pipeline.yaml with your catalog, warehouse, and connection, then re-run."
    exit 1
  fi
  echo "ERROR: Missing $CONFIG (and no example file)" >&2
  exit 1
fi

read_yaml_value() {
  local key="$1"
  grep "^${key}:" "$CONFIG" | head -1 | sed "s/^${key}:[[:space:]]*\"\{0,1\}\([^\"]*\)\"\{0,1\}[[:space:]]*$/\1/"
}

deployment_profile=$(read_yaml_value "deployment_profile")
warehouse_id=$(read_yaml_value "warehouse_id")
owner_email=$(read_yaml_value "owner_email")
catalog=$(read_yaml_value "catalog")
bronze_schema=$(read_yaml_value "bronze_schema")
silver_schema=$(read_yaml_value "silver_schema")
gold_schema=$(read_yaml_value "gold_schema")
metrics_schema=$(read_yaml_value "metrics_schema")
jira_connection_name=$(read_yaml_value "jira_connection_name")
dashboard_name=$(read_yaml_value "dashboard_name")
genie_space_name=$(read_yaml_value "genie_space_name")

missing=()
[[ -z "$deployment_profile" ]] && missing+=("deployment_profile")
[[ -z "$warehouse_id" ]] && missing+=("warehouse_id")
[[ -z "$owner_email" ]] && missing+=("owner_email")
[[ -z "$catalog" ]] && missing+=("catalog")
[[ -z "$bronze_schema" ]] && missing+=("bronze_schema")
[[ -z "$silver_schema" ]] && missing+=("silver_schema")
[[ -z "$gold_schema" ]] && missing+=("gold_schema")
[[ -z "$metrics_schema" ]] && missing+=("metrics_schema")
[[ -z "$jira_connection_name" ]] && missing+=("jira_connection_name")

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: Missing required fields in $CONFIG: ${missing[*]}"
  exit 1
fi

valid_profiles=("full" "with_dashboard" "with_genie" "with_metrics" "pipeline_only")
profile_valid=false
for p in "${valid_profiles[@]}"; do
  if [[ "$deployment_profile" == "$p" ]]; then
    profile_valid=true
    break
  fi
done
if [[ "$profile_valid" == false ]]; then
  echo "ERROR: Invalid deployment_profile '$deployment_profile'. Must be one of: ${valid_profiles[*]}"
  exit 1
fi

echo "Config values from pipeline.yaml:"
echo "  deployment_profile: $deployment_profile"
echo "  catalog:            $catalog"
echo "  bronze_schema:      $bronze_schema"
echo "  silver_schema:      $silver_schema"
echo "  gold_schema:        $gold_schema"
echo "  metrics_schema:     $metrics_schema"
echo "  warehouse_id:       $warehouse_id"
echo "  jira_connection:    $jira_connection_name"
echo ""

# --- 1. Update databricks.yml profile include ---
sed -i.bak "s|.*# Updated by sync_config.sh|  - resources/${deployment_profile}/*.yml # Updated by sync_config.sh|" "$BUNDLE"

# --- 2. Patch target variables (dev and prod blocks) ---
for var in warehouse_id owner_email catalog bronze_schema silver_schema gold_schema metrics_schema jira_connection_name dashboard_name genie_space_name; do
  val="${!var}"
  sed -i.bak "s/^      ${var}:.*/      ${var}: \"${val}\"/" "$BUNDLE"
done
rm -f "$BUNDLE.bak"

echo "Updated databricks.yml (profile: $deployment_profile)"

# --- 3. Resolve dev-mode schema prefixes if bundle is configured ---
GOLD_SCHEMA="$gold_schema"
METRICS_SCHEMA="$metrics_schema"
if summary_json="$(cd "$REPO_ROOT" && databricks bundle summary -t "$TARGET" -o json 2>/dev/null)"; then
  eval "$(SUMMARY_JSON="$summary_json" python3 - <<'PY'
import json, os, shlex
d = json.loads(os.environ["SUMMARY_JSON"])
schemas = d.get("resources", {}).get("schemas", {})
for layer in ("gold", "metrics"):
    name = schemas.get(layer, {}).get("name")
    if name:
        print(f"export {layer.upper()}_SCHEMA={shlex.quote(name)}")
PY
)"
  echo "Resolved schema prefixes from bundle summary (target: $TARGET)"
fi

# --- 4. Generate metric SQL, Genie JSON, dashboard JSON ---
python3 "$REPO_ROOT/scripts/build_assets.py" \
  --catalog "$catalog" \
  --gold-schema "$GOLD_SCHEMA" \
  --metrics-schema "$METRICS_SCHEMA"

echo ""
echo "Done! Deploy with:"
echo "  databricks bundle deploy -t $TARGET"
echo ""
echo "Then run the refresh job:"
echo "  databricks bundle run jira_analytics_refresh -t $TARGET"
