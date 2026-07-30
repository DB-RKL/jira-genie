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

## Sync Workflow

After editing `pipeline.yaml`, always run sync before deploy. For dev targets, pass your CLI profile:

```bash
./scripts/sync_config.sh -t dev -p <your-profile>
```

This script:

1. Validates required fields
2. Updates `databricks.yml` with your values and selected deployment profile
3. Resolves dev-mode schema prefixes via `bundle summary` (dev targets)
4. Patches `dashboards/jira_analytics.lvdash.json` from the checked-in template
5. Generates `src/metrics/metric_views.sql` and Genie space JSON

Then validate and deploy:

```bash
databricks bundle validate -t dev -p <your-profile>
databricks bundle deploy -t dev -p <your-profile>
```

## Interactive Configuration

Import [`notebooks/00_configure_layers.py`](../notebooks/00_configure_layers.py) into your workspace to validate catalog permissions and print a `pipeline.yaml` block to copy.

## Development Mode Schema Prefixes

When deploying with `-t dev` (development mode), Databricks Asset Bundles prefix schema names (e.g. `dev_user_jira_bronze`). The sync script resolves these prefixes via `bundle summary` so generated metric SQL and Genie identifiers match the deployed schemas.
