# Post-Deployment

## Running Jobs

| Job | Command | Purpose |
|-----|---------|---------|
| Full refresh | `databricks bundle run jira_analytics_refresh -t dev` | Ingest → silver → gold → metrics (profile-dependent) |
| Metrics only | `databricks bundle run jira_build_metrics -t dev` | Rebuild metric views over existing gold |

The refresh job schedule is paused by default. Enable it in the Databricks Jobs UI or edit `resources/*/orchestration.yml`.

## Using the Dashboard

Navigate to **AI/BI → Dashboards** and open your configured dashboard name. The dashboard queries Unity Catalog metric views via `MEASURE()` — filters at the top apply across all widgets.

## Using Genie

Open **Genie** and select the Jira Analytics space. Sample questions and example SQL are pre-loaded. Genie queries the same eight metric views as the dashboard.

Re-deploying the bundle with the same `genie_space_name` updates the existing Genie space in place (Databricks Asset Bundles manages the resource by bundle key `jira_analytics_genie`). You do not need a separate create-or-update script.

## Metric Views

| View | Key measures |
|------|-------------|
| `metric_issue` | Open Issues, Median Cycle Time, Open Critical |
| `metric_sprint_velocity` | Points Completed, Avg Completion Ratio |
| `metric_issue_transitions` | P90 Duration (hours) |
| `metric_worklog` | Total Hours, Contributors |
| `metric_project_health` | Open Issues, Stale Open, Resolved (30d) |
| `metric_assignee_load` | Open Issues by assignee |
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

### Silver pipeline fails on column names

Lakeflow Connect uses camelCase REST field names (`issueId`, `projectKey`). The silver layer maps these automatically. If your connector version differs, check `src/silver/*.py`.

### Dev-mode schema prefix mismatch

When using `-t dev`, schemas are prefixed (e.g. `dev_user_jira_gold`). Always run `./scripts/sync_config.sh` before deploy so generated metric SQL matches deployed schema names.

### Genie deploy fails on "must be sorted"

Re-run `./scripts/sync_config.sh` — the build script sorts tables, columns, and example SQLs as required by the Genie API.

### Dashboard shows no data

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

## Regenerating Artifacts

After changing catalog, schemas, or dashboard layout:

```bash
./scripts/sync_config.sh
databricks bundle deploy -t dev
```
