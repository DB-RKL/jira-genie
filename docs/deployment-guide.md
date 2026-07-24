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
databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

## Step 4: Sync configuration

```bash
./scripts/sync_config.sh
```

This validates your config, patches `databricks.yml`, and generates metric SQL, Genie JSON, and dashboard JSON.

## Step 5: Deploy

```bash
databricks bundle deploy -t dev
```

For production:

```bash
databricks bundle deploy -t prod
```

## Step 6: Run the refresh job

```bash
databricks bundle run jira_analytics_refresh -t dev
```

This runs: Lakeflow Connect ingestion → silver DLT → gold DLT → metric views SQL task.

For metric views only (after gold exists):

```bash
databricks bundle run jira_build_metrics -t dev
```

## Step 7: Verify

1. **Catalog Explorer** — check schemas `jira_bronze`, `jira_silver`, `jira_gold`, `jira_metrics` (or dev-prefixed names)
2. **SQL** — `SELECT MEASURE(\`Open Issues\`) FROM <catalog>.<metrics_schema>.metric_project_health`
3. **AI/BI → Dashboards** — open your dashboard
4. **Genie** — open the Jira Analytics space

See [post-deployment.md](post-deployment.md) for scheduling and troubleshooting.
