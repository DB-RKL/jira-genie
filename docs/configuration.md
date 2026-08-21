# Configuration

All customer-specific settings live in **`config/pipeline.yaml`**. Copy from the example template:

```bash
cp config/pipeline.example.yaml config/pipeline.yaml
```

## Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `deployment_profile` | Yes | What to deploy: `full`, `with_dashboard`, `with_genie`, `with_metrics`, `pipeline_only` |
| `warehouse_id` | Yes | SQL warehouse ID for dashboard, Genie, and jobs |
| `owner_email` | Yes | Your workspace user email (dashboard/Genie folder: `/Users/<email>`) |
| `catalog` | Yes | Unity Catalog name (must exist) |
| `bronze_schema` | Yes | Bronze landing schema (default: `jira_bronze`) |
| `silver_schema` | Yes | Silver ERD schema (default: `jira_silver`) |
| `gold_schema` | Yes | Gold marts schema (default: `jira_gold`) |
| `metrics_schema` | Yes | Metric views schema (default: `jira_metrics`) |
| `jira_connection_name` | Yes | Lakeflow Connect Jira connection name |
| `dashboard_name` | No | Lakeview dashboard title (default: `Jira Analytics`) |
| `genie_space_name` | No | Genie space title (default: `Jira Analytics`) |
| `pipeline_channel` | No | DLT release channel for silver/gold pipelines (default: `PREVIEW` for dev, `CURRENT` for prod) |
| `prod_catalog` | No | [prod only] Unity Catalog for production deployment (must exist; default empty) |
| `prod_warehouse_id` | No | [prod only] Serverless SQL warehouse ID for production dashboard/Genie/metrics (default empty) |
| `prod_owner_email` | No | [prod only] Notification email and folder path for production resources (default empty) |
| `prod_service_principal` | No | [prod only] Service principal application ID to run production refresh unattended (default empty) |

## Example

```yaml
deployment_profile: "full"
warehouse_id: "abc123def456"
owner_email: "analyst@company.com"

catalog: "my_company_catalog"
bronze_schema: "jira_bronze"
silver_schema: "jira_silver"
gold_schema: "jira_gold"
metrics_schema: "jira_metrics"

jira_connection_name: "my-jira-connection"

dashboard_name: "Jira Analytics"
genie_space_name: "Jira Analytics"
```

## Sync Workflow (Dev Target)

After editing `pipeline.yaml`, always run sync before deploy. For dev targets, pass your CLI profile:

```bash
./scripts/sync_config.sh -t dev -p <your-profile>
```

This script:

1. Validates required fields
2. Updates `databricks.yml` with your values and selected deployment profile
3. Resolves dev-mode schema prefixes via `bundle summary` (dev targets)
4. Copies `dashboards/jira_analytics.lvdash.json` from the checked-in template (unqualified metric view names; catalog/schema set by the bundle dashboard resource)
5. Generates `src/metrics/metric_views.sql` and Genie space JSON

Then validate and deploy:

```bash
databricks bundle validate -t dev -p <your-profile>
databricks bundle deploy -t dev -p <your-profile>
```

## Production Configuration

The `prod` target runs unattended as a service principal. Instead of `pipeline.yaml`, configure it via `prod_*` bundle variables:

```bash
databricks bundle deploy -t prod \
  --var prod_catalog=jira_prod \
  --var prod_warehouse_id=abc123def456 \
  --var prod_owner_email=team@example.com \
  --var prod_service_principal=<sp-app-id> \
  --var jira_connection_name=<prod-jira-connection>
```

The `prod_*` variables ship with obvious `REPLACE_WITH_*` placeholder defaults so `bundle validate -t prod` passes; a deploy fails until you supply real values. `prod` deploys the dashboard with `embed_credentials: false` (viewers query with their own permissions) since it is owned by a service principal.

Or set these in `databricks.yml` under `targets.prod.variables` before deploy. Note that:
- `sync_config.sh` only patches the `dev` target; `prod` is not overwritten
- Lakeflow Connect's Jira connector requires OAuth U2M interactive login, so create the connection manually before the ingestion pipeline runs
- `pipeline_channel` defaults to `CURRENT` for prod (stable releases) vs `PREVIEW` for dev

## Jira-Instance Overrides (Advanced)

A few transformation knobs are set in the pipeline `configuration:` blocks (in `resources/*/silver_pipeline.yml` and `resources/*/gold_pipeline.yml`) with defaults that match a standard Jira Cloud instance. Override them only if your instance differs:

| Config key | Default | Where | Purpose |
|------------|---------|-------|---------|
| `status_field_id` | `status` | gold | The `issue_field_history.field_id` that marks a status change (drives transitions + cycle time). |
| `in_progress_category_key` | `indeterminate` | gold | Jira status-category key for "In Progress"; the point cycle time starts counting. |
| `epic_issue_type_name` | `epic` | silver | Issue-type name (case-insensitive) used to derive the `epic_issue` bridge; change if the Epic type was renamed/localized. |

Status-category keys (`new` / `indeterminate` / `done`) are Jira's canonical API keys and are used directly; the silver layer prefers the source's key column and only falls back to mapping English display names when no key is present.

## Interactive Configuration

Import [`notebooks/00_configure_layers.py`](../notebooks/00_configure_layers.py) into your workspace to validate catalog permissions and print a `pipeline.yaml` block to copy.

## Development Mode Schema Prefixes

When deploying with `-t dev` (development mode), Databricks Asset Bundles prefix schema names (e.g. `dev_user_jira_bronze`). The sync script resolves these prefixes via `bundle summary` so generated metric SQL and Genie identifiers match the deployed schemas.

Resource display names (dashboard, jobs, pipelines) use the names from `pipeline.yaml` without a `[dev <user>]` prefix — the dev target sets `presets.name_prefix: ""` in `databricks.yml`.
