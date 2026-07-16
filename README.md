# Jira Analytics (Databricks)

Lakeflow Connect → Fivetran-parity ERD → analytical marts → AI/BI dashboard + Genie space.

## Architecture

```
databricks.atlassian.net  ──►  Lakeflow Connect Jira pipeline  ──►  rubjit_jira.bronze.*  (28 tables)
                                                                          │
                                                                          ▼  DLT  (src/silver/*.py)
                                                              rubjit_jira.silver.*  (Fivetran-parity)
                                                                          │
                                                                          ▼  DLT  (src/gold/*.sql)
                                                                rubjit_jira.gold.*  (marts)
                                                                          │
                            ┌─────────────────────────────────────────────┼─────────────────────────────────────┐
                            ▼                                             ▼                                     ▼
              Lakeview dashboard (4 pages)                   Genie Space (NL Q&A)             jira-analytics-board app
```

## Prerequisites (one-time)

1. **OAuth U2M connection to Jira** — Lakeflow Connect for Jira only supports OAuth U2M. Create the connection in **Catalog Explorer → Data → External Data → Connections → Create connection → Jira**. Name it **`jira_databricks_atlassian`**. Authorize using your `@databricks.com` Atlassian account.
2. **Catalog** — `rubjit_jira` must exist. If it does not:
   ```sql
   CREATE CATALOG IF NOT EXISTS rubjit_jira;
   ```
3. SQL warehouse: `ced20c73f16a2915` (Serverless Starter on fevm-serverless-stable-wx20co). Override with `--var warehouse_id=<id>`.

## Deploy

```bash
cd ~/jira-analytics
databricks bundle deploy -t fe_vm -p fe-vm-graphrag
```

This deploys:

| Resource | Type | Notes |
|---|---|---|
| `rubjit_jira.bronze` / `silver` / `gold` | schemas | empty until pipelines run |
| `jira_ingestion_pipeline` | Lakeflow Connect managed pipeline | full refresh first time |
| `jira_silver_pipeline` | DLT pipeline (Python) | reads bronze, writes silver |
| `jira_gold_pipeline` | DLT pipeline (SQL) | reads silver, writes gold |
| `jira_analytics_refresh` | Job | orchestrates bronze → silver → gold |
| `jira_analytics_dashboard` | Lakeview dashboard | 4 pages, 35 widgets |

## Run

```bash
# Run end-to-end once
databricks bundle run jira_analytics_refresh -t fe_vm -p fe-vm-graphrag

# Or run a single stage
databricks bundle run jira_ingestion_pipeline -t fe_vm -p fe-vm-graphrag
databricks bundle run jira_silver_pipeline   -t fe_vm -p fe-vm-graphrag
databricks bundle run jira_gold_pipeline     -t fe_vm -p fe-vm-graphrag
```

## Genie space

DAB does not yet have first-class Genie support. Create via REST API:

```bash
PROFILE=fe-vm-graphrag ./scripts/create_genie_space.sh
```

If the API call fails (endpoint name changes are common), create the space via UI:

1. Open **Genie → New space**, name it `Jira Analytics`.
2. Add tables: `rubjit_jira.gold.fct_issue`, `fct_sprint_velocity`, `fct_issue_transitions`, `fct_worklog`, all `agg_*` and `dim_*`, plus `rubjit_jira.silver.{issue, sprint, project}`.
3. Paste the instructions from `scripts/create_genie_space.sh` (variable `INSTRUCTIONS`).
4. Seed the example questions from the same file.
5. Note the space ID from the URL — paste into `~/jira-analytics-board/app.yaml` as `GENIE_SPACE_ID`.

## Regenerating the dashboard JSON

```bash
python3 scripts/build_dashboard.py
databricks bundle deploy -t fe_vm -p fe-vm-graphrag
```

## Gaps vs. Fivetran's Jira ERD

Lakeflow Connect ingests 28 source tables — enough to recreate ~30 of Fivetran's normalized tables. Tables in Fivetran's canonical ERD that we cannot reproduce (not surfaced by the connector):

- `audit_log` — full audit history is not exposed by Lakeflow Connect
- `field_option` — option-list values for custom fields
- `dashboard` / `filter` — Jira dashboards and saved filters
- `workflow` / `workflow_status` — workflow definitions

These are intentionally skipped. Everything else is mapped — see `src/silver/*.py` for the table-by-table translation.

## Verifying the silver schema after first sync

The silver DLT code assumes Jira REST API column names on the bronze tables. If Lakeflow Connect uses different names, the silver views will fail. Run this after first ingestion to spot drift:

```sql
DESCRIBE rubjit_jira.bronze.issues;
-- compare with the SELECT in src/silver/core_entities.py:issue()
```

Each silver function uses a `col(name, default)` helper that returns `lit(default)` when a column is missing, so the worst case is NULL columns rather than a hard failure.
