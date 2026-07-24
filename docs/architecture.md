# Architecture

## Data Flow

```
databricks.atlassian.net
        │
        ▼
Lakeflow Connect (28 Jira source tables)
        │
        ▼
bronze.*  ──►  silver.* (Fivetran-parity ERD)  ──►  gold.* (marts)
                                                        │
                                                        ▼
                                              metrics.* (8 metric views)
                                                        │
                              ┌─────────────────────────┴─────────────────────────┐
                              ▼                                                   ▼
                   Lakeview dashboard                                  Genie space
```

## Layers

| Layer | Schema var | Contents |
|-------|-----------|----------|
| Bronze | `bronze_schema` | Raw Lakeflow Connect landing (28 tables) |
| Silver | `silver_schema` | Normalized ERD: issue, project, user, status, links, history |
| Gold | `gold_schema` | Facts (`fct_issue`, `fct_sprint_velocity`, …), dimensions, aggregates |
| Metrics | `metrics_schema` | Unity Catalog metric views (SSOT for dashboard + Genie) |

## Bronze Tables (Lakeflow Connect)

28 source tables including `issues_without_deletes`, `issue_field_values`, `projects`, `sprints`, `users`, and lookup tables. The silver layer maps Lakeflow camelCase columns to Fivetran-parity names.

## Silver ERD

Python DLT pipelines in `src/silver/`:

- `core_entities.py` — issue, project, user, status, priority
- `issue_history.py` — field history, worklogs, watchers
- `relationships.py` — links, sprints, epics, components, versions
- `lookups.py` — boards, sprints, groups, permission schemes

See [`docs/diagrams/jira_silver_er.mmd`](diagrams/jira_silver_er.mmd) for the entity-relationship diagram.

## Gold Marts

SQL DLT materialized views in `src/gold/`:

- `fct_issue` — denormalized issue fact with cycle/lead time
- `fct_sprint_velocity` — sprint planning vs completion
- `fct_issue_transitions` — workflow transitions with duration
- `fct_worklog` — logged hours
- `aggregates.sql` — project health, assignee load, team productivity, time in status

See [`docs/diagrams/jira_gold_star_schema.mmd`](diagrams/jira_gold_star_schema.mmd).

## Metric Views

Defined in [`src/metrics/metric_views.sql.tmpl`](../src/metrics/metric_views.sql.tmpl), generated at sync time into `src/metrics/metric_views.sql`. Created by the `build_metrics` task in `jira_analytics_refresh`.

## Bundle Structure

```
config/pipeline.yaml          ← customer edits this
databricks.yml                ← patched by sync_config.sh
resources/common/             ← UC schemas (all profiles)
resources/<profile>/          ← pipelines, jobs, dashboard, Genie
scripts/sync_config.sh        ← config → bundle + artifacts
src/silver/  src/gold/        ← transformation code
src/metrics/                  ← metric view template + generated SQL
dashboards/                   ← generated Lakeview JSON
```

## Orchestration

`jira_analytics_refresh` job runs four tasks sequentially:

1. `ingest_bronze` — Lakeflow Connect pipeline
2. `build_silver` — Silver DLT pipeline
3. `build_gold` — Gold DLT pipeline
4. `build_metrics` — SQL task executing generated metric views
