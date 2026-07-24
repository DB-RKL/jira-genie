# Post-Deployment

## Running Jobs

| Job | Command | Purpose |
|-----|---------|---------|
| Full refresh | `databricks bundle run jira_analytics_refresh -t dev` | Ingest → silver → gold → metrics |
| Metrics only | `databricks bundle run jira_build_metrics -t dev` | Rebuild metric views over existing gold |

The refresh job schedule is paused by default. Enable it in the Databricks Jobs UI or edit `resources/*/orchestration.yml`.

## Using the Dashboard

Navigate to **AI/BI → Dashboards** and open your configured dashboard name. The dashboard queries Unity Catalog metric views via `MEASURE()` — filters at the top apply across all widgets.

## Using Genie

Open **Genie** and select the Jira Analytics space. Sample questions and example SQL are pre-loaded. Genie queries the same eight metric views as the dashboard.

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

1. Confirm metric views exist: `SHOW TABLES IN <catalog>.<metrics_schema>`
2. Re-run `jira_analytics_refresh` or `jira_build_metrics`
3. Re-deploy consumption layer after metrics exist

## Regenerating Artifacts

After changing catalog, schemas, or dashboard layout:

```bash
./scripts/sync_config.sh
databricks bundle deploy -t dev
```
