# Post-Deployment

## Running Jobs

| Job | Command | Purpose |
|-----|---------|---------|
| Full refresh | `databricks bundle run jira_analytics_refresh -t dev` | Ingest → silver → gold → metrics (profile-dependent) |
| Metrics only | `databricks bundle run jira_build_metrics -t dev` | Rebuild metric views over existing gold |

The refresh job schedule is paused by default. Enable it in the Databricks Jobs UI or edit `resources/*/orchestration.yml`.

## Testing

Run the local pytest suite to validate transformation logic and configuration:

```bash
python3 -m pytest tests/ -q
```

The test suite covers:
- Transformation functions (comments apply, config sync)
- Pipeline configuration structure

CI automatically runs the full suite on each push to `main` and pull request, plus `databricks bundle validate -t dev` (gated on `DATABRICKS_HOST` and `DATABRICKS_TOKEN` secrets being set). On forks without these secrets, validation is skipped but Python tests still run.

## Using the Dashboard

Navigate to **AI/BI → Dashboards** and open your configured dashboard name. The dashboard is four audience pages (Portfolio, Flow, Sprint, Team), each with its own story and filters. All widgets query Unity Catalog metric views via `MEASURE()`.

## Using Genie

Open **Genie** and select the Jira Analytics space. Sample questions and example SQL are pre-loaded. Genie queries the same nine metric views as the dashboard.

Re-deploying the bundle with the same `genie_space_name` updates the existing Genie space in place (Databricks Asset Bundles manages the resource by bundle key `jira_analytics_genie`). You do not need a separate create-or-update script.

## Metric Views

| View | Key measures |
|------|-------------|
| `metric_issue` | Open Issues, WIP, Unassigned/Overdue, Created/Resolved (30d), Median Cycle Time |
| `metric_flow` | Created Issues, Resolved Issues, Net Backlog Change (by day/week) |
| `metric_sprint_velocity` | Points Completed, Carryover Points, Avg Completion Ratio |
| `metric_issue_transitions` | P90 Duration (hours) |
| `metric_worklog` | Total Hours, Hours (30d), Contributors |
| `metric_project_health` | Open Issues, Stale Open, Net Backlog Change (30d), Flow Ratio (30d) |
| `metric_assignee_load` | Open Issues, Stale Open by assignee |
| `metric_team_productivity` | Resolved (30d), Avg Cycle Time |
| `metric_time_in_status` | P50/P90 Duration per status |

```sql
SELECT `Project Key`, MEASURE(`Open Issues`), MEASURE(`Open Critical`)
FROM my_catalog.jira_metrics.metric_project_health
GROUP BY `Project Key`
ORDER BY 2 DESC;
```

## Troubleshooting

### Bronze ingestion fails with "table already managed by another pipeline"

An older ingestion pipeline may own tables in the target bronze schema. Either drop the old pipeline or use fresh schema names in `pipeline.yaml`.

### Deploy fails: "Connection type 'HTTP' is not supported for ingestion pipelines"

`jira_connection_name` points at a connection that is not a Lakeflow Connect **JIRA** connection. MCP/REST connections have `connection_type: HTTP` and cannot back an ingestion pipeline.

Check what you have:

```bash
databricks connections list -p <your-profile> -o json \
  | python3 -c "import json,sys; [print(c['name'], c['connection_type']) for c in json.load(sys.stdin)]"
```

Fix by pointing `jira_connection_name` at a JIRA-type connection, or create one in **Catalog Explorer → External Data → Connections**.

#### Deploying without ingestion (bronze already exists)

If bronze tables are already populated — for example another pipeline ingests them, or you are working in a demo workspace with no Jira connection — deploy everything except the ingestion pipeline:

```bash
./scripts/deploy.sh -t dev -p <your-profile> --skip-ingestion
```

This builds the `--select` list from `bundle summary`, excluding two resources:

| Excluded | Why |
|----------|-----|
| `pipelines.jira_ingestion_pipeline` | Needs a JIRA-type Lakeflow Connect connection |
| `jobs.jira_analytics_refresh` | Its `ingest_bronze` task depends on that pipeline |

Because the refresh job is skipped, rebuild the layers directly:

```bash
databricks bundle run jira_build_metrics -t dev -p <your-profile>
```

Run the silver and gold pipelines from the Pipelines UI, or re-add ingestion once a JIRA connection exists.

The equivalent raw CLI command, if you prefer not to use the script:

```bash
databricks bundle deploy -t dev -p <your-profile> --force --select schemas.bronze,schemas.silver,schemas.gold,schemas.metrics,pipelines.jira_silver_pipeline,pipelines.jira_gold_pipeline,jobs.jira_build_metrics,dashboards.jira_analytics_dashboard,genie_spaces.jira_analytics_genie
```

Drop `genie_spaces.jira_analytics_genie` or `dashboards.jira_analytics_dashboard` if your `deployment_profile` does not include them. List the exact keys for your profile with:

```bash
databricks bundle summary -t dev -p <your-profile> -o json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{k}.{n}') for k,v in d['resources'].items() for n in v]"
```

### Silver pipeline fails on column names

Lakeflow Connect uses camelCase REST field names (`issueId`, `projectKey`). The silver layer maps these automatically. If your connector version differs, check `src/silver/*.py`.

### Dev-mode schema prefix mismatch

When using `-t dev`, schemas are prefixed (e.g. `dev_user_jira_gold`). Always run `./scripts/sync_config.sh` before deploy so generated metric SQL matches deployed schema names.

### Genie deploy fails on "must be sorted"

Re-run `./scripts/sync_config.sh` — the build script sorts tables, columns, and example SQLs as required by the Genie API.

### Dashboard shows no data

The dashboard has **two bindings** that must both be correct:

| Binding | What it connects | How it breaks |
|---------|------------------|---------------|
| **Datasets → UC** | Each dataset SQL points at `catalog.schema.metric_*` | Wrong dev schema prefix in patched JSON (re-run `sync_config.sh -p <profile>`) |
| **Widgets → datasets** | Each widget has `queries` + `encodings` | Fixed automatically by the bundle **postdeploy hook** (`scripts/postdeploy.sh` → `push_dashboard.sh`). If widgets are still empty shells, run `./scripts/push_dashboard.sh` manually. |

**Diagnose:**

```bash
./scripts/verify_dashboard.sh -t dev -p <your-profile>
```

**Fix (run in order):**

```bash
./scripts/sync_config.sh -t dev -p <your-profile>
./scripts/deploy.sh -t dev -p <your-profile>
databricks bundle run jira_analytics_refresh -t dev -p <your-profile>
```

`deploy.sh` runs `bundle deploy` and the postdeploy hook wires all widgets via the Lakeview API.

The dashboard reads Unity Catalog **metric views**, not gold tables directly.

1. **Run the refresh job** so gold tables and metric views are populated:
   ```bash
   databricks bundle run jira_analytics_refresh -t dev -p <your-profile>
   ```

2. **Confirm metric views return data:**
   ```sql
   SELECT MEASURE(`Open Issues`) FROM <catalog>.<metrics_schema>.metric_issue;
   SELECT MEASURE(`Points Completed`) FROM <catalog>.<metrics_schema>.metric_sprint_velocity;
   ```

3. **Check dev schema prefixes:** run `./scripts/sync_config.sh -t dev -p <your-profile>` before deploy so generated SQL uses `dev_<user>_jira_*` schemas.

4. **Sprint widgets empty but other widgets work:** sprint velocity depends on `sprint_issue` data derived from Jira issue sprint fields. Confirm your Jira instance populates sprint membership in the Connect `issues` table.

5. **Draft vs published dashboard:** `bundle deploy` updates the draft. Open the dashboard in AI/BI and publish if viewers still see an older version.

### `bundle deploy` fails: dashboard modified remotely

Expected after `push_dashboard.sh` or the postdeploy hook runs — the Lakeview API updates the dashboard outside bundle's last-deployed snapshot.

**Fix:** deploy with `--force` (local `dashboards/jira_analytics.lvdash.json` is source of truth; postdeploy re-wires widgets):

```bash
./scripts/deploy.sh -t dev -p <your-profile>
# or:
databricks bundle deploy -t dev -p <your-profile> --force
```

Only use `databricks bundle generate dashboard --resource jira_analytics_dashboard --force` if you intentionally edited widgets in the UI and want to pull those changes into the repo.

### Dashboard widgets are empty shells (titles only, no data)

If widgets show titles but the inspector reports `queries: []` and `encodings: {}` (only filters may work), the postdeploy hook may not have run (e.g. profile without dashboard, or deploy without the hook). Re-wire with:

```bash
./scripts/sync_config.sh -t dev -p <your-profile>
./scripts/deploy.sh -t dev -p <your-profile>
```

Or push only:

```bash
./scripts/push_dashboard.sh -t dev -p <your-profile>
```

The postdeploy hook / `push_dashboard.sh` calls `lakeview update` with the patched `dashboards/jira_analytics.lvdash.json` and publishes.

## Regenerating Artifacts

After changing catalog, schemas, or dashboard layout:

```bash
./scripts/sync_config.sh -t dev -p <your-profile>
./scripts/deploy.sh -t dev -p <your-profile>
```
