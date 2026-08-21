# Deployment Guide

## Step 1: Clone the repository

```bash
git clone https://github.com/DB-RKL/jira-analytics.git
cd jira-analytics
```

## Step 2: Configure

```bash
cp config/pipeline.example.yaml config/pipeline.yaml
```

Edit `config/pipeline.yaml` with your:

- `catalog` — existing Unity Catalog name
- `warehouse_id` — SQL warehouse ID
- `owner_email` — your workspace user email
- `jira_connection_name` — Lakeflow Connect Jira connection name
- `deployment_profile` — start with `pipeline_only` for first deploy, then `full`

## Step 3: Authenticate

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com -p <your-profile>
```

## Step 4: Sync configuration

Pass your CLI profile so schema prefixes resolve correctly:

```bash
./scripts/sync_config.sh -t dev -p <your-profile>
```

This validates your config, patches the **dev** target in `databricks.yml`, generates metric SQL and Genie JSON, and patches the dashboard from `src/dashboard/jira_analytics.lvdash.json`. The **prod** target is left as a template — see "Deploying to production" below.

## Step 5: Validate the bundle

```bash
databricks bundle validate -t dev -p <your-profile>
```

Fix any reported errors before deploying.

## Step 6: Deploy

Recommended (sync + deploy + automatic dashboard wiring):

```bash
./scripts/deploy.sh -t dev -p <your-profile>
```

Or deploy directly — add `--force` when your profile includes the dashboard (postdeploy modifies the remote dashboard via Lakeview API):

```bash
databricks bundle deploy -t dev -p <your-profile> --force
```

For production:

```bash
./scripts/deploy.sh -t prod -p <your-profile>
```

## Step 6b: Deploying to production

The **prod** target in `databricks.yml` is a template that runs unattended as a service principal. Before deploying, fill in the required production variables — either edit `databricks.yml` directly or pass them at deploy time.

Required variables:

- `prod_catalog` — existing Unity Catalog
- `prod_warehouse_id` — Serverless SQL warehouse ID
- `prod_owner_email` — notification email and dashboard/Genie folder owner
- `prod_service_principal` — service principal application ID

Example deploy command:

```bash
databricks bundle deploy -t prod \
  --var prod_catalog=jira_prod \
  --var prod_warehouse_id=abc123def456 \
  --var prod_owner_email=team@example.com \
  --var prod_service_principal=<service-principal-app-id>
```

**Important:** The Lakeflow Connect Jira connector uses OAuth U2M authentication, which requires interactive setup. Even in production, create the Jira connection interactively (via Catalog Explorer → Connections) — the service principal runs only the transform and refresh jobs, not the OAuth connection setup.

The prod pipelines use `pipeline_channel: CURRENT` (stable channel), while dev uses `PREVIEW` to match the preview-channel Jira connector.

## Step 7: Run the refresh job

```bash
databricks bundle run jira_analytics_setup -t dev -p <your-profile>
```

This runs: silver DLT → gold DLT → metric views (when your deployment profile includes metrics). Ingestion runs separately via the `jira_ingestion_pipeline` with its own schedule.

## Step 8: Verify

1. **Catalog Explorer** — check schemas `jira_bronze`, `jira_silver`, `jira_gold`, `jira_metrics` (or dev-prefixed names)
2. **SQL** — `SELECT MEASURE(\`Open Issues\`) FROM <catalog>.<metrics_schema>.metric_project_health`
3. **AI/BI → Dashboards** — open your dashboard
4. **Genie** — open the Jira Analytics space

See [post-deployment.md](post-deployment.md) for scheduling and troubleshooting.
