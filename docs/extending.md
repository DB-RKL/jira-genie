# Extending Jira Genie

## Adding a Metric View

1. Add the view definition to [`src/metrics/metric_views.sql.tmpl`](../src/metrics/metric_views.sql.tmpl)
2. Register it in `METRIC_VIEWS` and `COLUMN_CONFIGS` in [`scripts/build_assets.py`](../scripts/build_assets.py)
3. Add field/measure comments in [`src/metrics/metric_view_comments.py`](../src/metrics/metric_view_comments.py)
4. Add sample questions / example SQL in `build_assets.py` for Genie
5. Run `./scripts/sync_config.sh` and redeploy

```sql
-- Example: new view in metric_views.sql.tmpl
CREATE OR REPLACE VIEW {{METRICS_CATALOG}}.{{METRICS_SCHEMA}}.metric_custom
WITH METRICS
AS SELECT ...
```

## Adding Dashboard Widgets

The checked-in dashboard template lives at [`src/dashboard/jira_genie.lvdash.json`](../src/dashboard/jira_genie.lvdash.json) with **unqualified** metric view names (e.g. `FROM metric_issue`). `sync_config.sh` copies it to `dashboards/jira_genie.lvdash.json`; catalog and schema are injected at deploy time via `dataset_catalog` / `dataset_schema` in the bundle dashboard resource.

1. Edit [`scripts/build_dashboard.py`](../scripts/build_dashboard.py) — add datasets and widgets
2. Regenerate the template: `python scripts/build_assets.py --regenerate-dashboard`
3. Run `./scripts/sync_config.sh` to patch `dashboards/jira_genie.lvdash.json` for deploy
4. Redeploy with `databricks bundle deploy -t dev -p <profile>`

## Adding Silver Tables

1. Create a new Python module in `src/silver/` with `@dlt.table` definitions
2. Register the file in `resources/*/silver_pipeline.yml` under `libraries`
3. If reading bronze, use `bronze_fqn()` from `layer_config.py` for configurable paths
4. Redeploy with `databricks bundle deploy -t dev`

## Adding Gold Marts

1. Add a SQL file in `src/gold/`
2. Register it in `resources/*/gold_pipeline.yml` under `libraries`
3. Use `${silver_catalog}.${silver_schema}` placeholders for silver references
4. Add table/column comments in [`src/gold/gold_comments.py`](../src/gold/gold_comments.py)
5. Optionally expose via a new metric view for dashboard/Genie consumption

## Customizing Genie Instructions

Edit `GENIE_INSTRUCTIONS`, `SAMPLE_QUESTIONS`, and `EXAMPLE_SQLS` in [`scripts/build_assets.py`](../scripts/build_assets.py), then run sync.

## Deployment Profile for Extensions

During development, use `pipeline_only` to iterate on pipelines without redeploying dashboard/Genie. Switch to `full` when ready to publish consumption assets.
