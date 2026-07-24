# Extending Jira Analytics

## Adding a Metric View

1. Add the view definition to [`src/metrics/metric_views.sql.tmpl`](../src/metrics/metric_views.sql.tmpl)
2. Register it in `METRIC_VIEWS` and `COLUMN_CONFIGS` in [`scripts/build_assets.py`](../scripts/build_assets.py)
3. Add sample questions / example SQL in the same file for Genie
4. Run `./scripts/sync_config.sh` and redeploy

```sql
-- Example: new view in metric_views.sql.tmpl
CREATE OR REPLACE VIEW {{METRICS_CATALOG}}.{{METRICS_SCHEMA}}.metric_custom
WITH METRICS
AS SELECT ...
```

## Adding Dashboard Widgets

Edit [`scripts/build_dashboard.py`](../scripts/build_dashboard.py):

1. Add a dataset with a `MEASURE()` query against your metric view
2. Add a widget helper call (counter, bar, table, etc.)
3. Place it in the `all_items` layout list
4. Run `./scripts/sync_config.sh` to regenerate the dashboard JSON

## Adding Silver Tables

1. Create a new Python module in `src/silver/` with `@dlt.table` definitions
2. Register the file in `resources/*/silver_pipeline.yml` under `libraries`
3. If reading bronze, use `bronze_fqn()` from `layer_config.py` for configurable paths
4. Redeploy with `databricks bundle deploy -t dev`

## Adding Gold Marts

1. Add a SQL file in `src/gold/`
2. Register it in `resources/*/gold_pipeline.yml` under `libraries`
3. Use `${silver_catalog}.${silver_schema}` placeholders for silver references
4. Optionally expose via a new metric view for dashboard/Genie consumption

## Customizing Genie Instructions

Edit `GENIE_INSTRUCTIONS`, `SAMPLE_QUESTIONS`, and `EXAMPLE_SQLS` in [`scripts/build_assets.py`](../scripts/build_assets.py), then run sync.

## Deployment Profile for Extensions

During development, use `pipeline_only` to iterate on pipelines without redeploying dashboard/Genie. Switch to `full` when ready to publish consumption assets.
