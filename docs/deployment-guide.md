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

For **dev** deployments, pass your CLI profile so schema prefixes resolve correctly:

```bash
./scripts/sync_config.sh -t dev -p <your-profile>
```

For **prod**, profile is optional:

```bash
./scripts/sync_config.sh -t prod
```

This validates your config, patches `databricks.yml`, generates metric SQL and Genie JSON, and patches the dashboard from `src/dashboard/jira_analytics.lvdash.json`.

## Step 5: Validate the bundle

```bash
databricks bundle validate -t dev -p <your-profile>
```

Fix any reported errors before deploying.

## Step 6: Deploy

```bash
databricks bundle deploy -t dev -p <your-profile>
```

For production:

```bash
databricks bundle deploy -t prod -p <your-profile>
```

## Step 7: Run the refresh job

```bash
databricks bundle run jira_analytics_refresh -t dev -p <your-profile>
```

This runs: Lakeflow Connect ingestion → silver DLT → gold DLT → metric views (when your deployment profile includes metrics).

For metric views only (after gold exists):

```bash
databricks bundle run jira_build_metrics -t dev -p <your-profile>
```

## Step 8: Verify

1. **Catalog Explorer** — check schemas `jira_bronze`, `jira_silver`, `jira_gold`, `jira_metrics` (or dev-prefixed names)
2. **SQL** — `SELECT MEASURE(\`Open Issues\`) FROM <catalog>.<metrics_schema>.metric_project_health`
3. **AI/BI → Dashboards** — open your dashboard
4. **Genie** — open the Jira Analytics space

See [post-deployment.md](post-deployment.md) for scheduling and troubleshooting.
