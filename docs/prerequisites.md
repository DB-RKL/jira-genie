# Prerequisites

## Workspace Requirements

- Databricks workspace with **Unity Catalog** enabled
- An existing Unity Catalog **catalog** with `CREATE SCHEMA` permission on bronze, silver, gold, and metrics schemas
- A **SQL warehouse** (Pro or Serverless) for dashboard, Genie, and metric-view jobs
- **Lakeflow Connect** Jira connector configured with OAuth U2M authentication

## Tooling

| Tool | Version | Purpose |
|------|---------|---------|
| [Databricks CLI](https://docs.databricks.com/dev-tools/cli/) | ≥ 1.3.0 | Bundle deploy, Genie space resource, `engine: direct` |
| Python | 3.9+ | Asset generation scripts (stdlib only) |
| Git | any | Clone this repository |

Authenticate the CLI against your workspace:

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

## Jira Connection

1. In Catalog Explorer, go to **Connections** and create a Jira connection (OAuth U2M).
2. Note the connection name — it must match `jira_connection_name` in `config/pipeline.yaml`.
3. Run an initial Lakeflow Connect ingestion to populate bronze tables before the silver pipeline runs.

## Permissions

| Action | Required on |
|--------|-------------|
| `CREATE SCHEMA` | Target catalog |
| `USE CATALOG` / `USE SCHEMA` | Target catalog and schemas |
| `CREATE TABLE` / `CREATE MATERIALIZED VIEW` | Silver, gold, metrics schemas |
| Run pipelines and jobs | Workspace compute policies |

## Known Limitations

- Preview-channel Lakeflow Connect Jira connector
- OAuth U2M only (no service-principal Connect auth)
- `CREATE CATALOG` requires metastore admin on some workspaces — use an existing catalog instead
