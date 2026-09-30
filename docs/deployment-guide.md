# Deployment Guide

There are two ways to deploy Jira Genie:

- **Option A — Databricks UI (Git folder):** run everything from the workspace, no local machine. Best for customers and demos.
- **Option B — Local CLI:** the scripted workflow below (Steps 1–8), best for CI/CD and repeatable automation.

## Option A: Deploy from the Databricks UI

1. **Add the repo as a Git folder.** Sidebar -> **Workspace** -> choose a folder -> **Create -> Git folder** -> `https://github.com/DB-RKL/jira-genie.git`.
2. **Create the Jira connection** (Catalog Explorer -> Connections, OAuth U2M) — this is always interactive; note its exact name.
3. **Open `deploy_jira_genie.py`** at the repo root, attach it to a cluster.
4. **Fill in the widgets** (catalog, warehouse ID, Jira connection name, deployment profile, target) and **Run all**.

The notebook authenticates as the running user, writes `config/pipeline.yaml`, installs the Databricks CLI if needed (requires egress to github.com), and runs the same sync -> deploy -> refresh steps described below. If the cluster cannot reach github.com to fetch the CLI, use Option B instead.

## Option B: Deploy from a local CLI

## Step 1: Clone the repository

```bash
git clone https://github.com/DB-RKL/jira-genie.git
cd jira-genie
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

This validates your config, patches the **dev** target in `databricks.yml`, generates metric SQL and Genie JSON, and patches the dashboard from `src/dashboard/jira_genie.lvdash.json`. The **prod** target is left as a template — see "Deploying to production" below.

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

For the `full` and `with_genie` profiles, `deploy.sh` **defers the Genie space** and deploys
everything else (schemas, pipelines, job, dashboard). This is deliberate: creating a Genie space
validates that every metric view it references already exists, but those are only built by the
setup job in Step 7. You deploy the Genie space in Step 7b, once the metric views exist.

Or deploy directly — add `--force` when your profile includes the dashboard (postdeploy modifies the remote dashboard via Lakeview API). Note that a direct `bundle deploy` of a genie profile will fail until the metric views exist, so exclude the Genie space on the first pass:

```bash
databricks bundle deploy -t dev -p <your-profile> --force \
  --select schemas.bronze,schemas.silver,schemas.gold,schemas.metrics,pipelines.jira_ingestion_pipeline,pipelines.jira_silver_pipeline,pipelines.jira_gold_pipeline,jobs.jira_genie_setup,dashboards.jira_genie_dashboard
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

## Step 7: Ingest, then run the refresh job

First make sure bronze is populated — the silver pipeline reads from it. Run the Lakeflow Connect ingestion pipeline once (it also has its own schedule):

```bash
databricks bundle run jira_ingestion_pipeline -t dev -p <your-profile>
```

Then run the refresh job:

```bash
databricks bundle run jira_genie_setup -t dev -p <your-profile>
```

This runs: silver DLT → gold DLT → metric views (when your deployment profile includes metrics).

## Step 7b: Deploy the Genie space

Only needed for the `full` and `with_genie` profiles (skipped by `deploy.sh` in Step 6). Now that the metric views exist, create the Genie space:

```bash
./scripts/deploy.sh -t dev -p <your-profile> --skip-sync --only-genie
```

## Step 8: Verify

1. **Catalog Explorer** — check schemas `jira_bronze`, `jira_silver`, `jira_gold`, `jira_metrics` (or dev-prefixed names)
2. **SQL** — `SELECT MEASURE(\`Open Issues\`) FROM <catalog>.<metrics_schema>.metric_project_health`
3. **AI/BI → Dashboards** — open your dashboard
4. **Genie** — open the Jira Genie space

See [post-deployment.md](post-deployment.md) for scheduling and troubleshooting.
