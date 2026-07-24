# Jira Analytics

This repo can be directly deployed in any Databricks workspace that ingests Jira data using [Lakeflow Connect](https://docs.databricks.com/en/connect/index.html). It:

1. Creates standard pipelines to transform bronze → silver (Fivetran-parity ERD) → gold analytical marts
2. Creates Unity Catalog metric views defining governed Jira delivery KPIs
3. Deploys an AI/BI dashboard for sprint velocity, cycle time, portfolio health, and team productivity
4. Provisions a curated Genie space for conversational analytics over the same metric views

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/DB-RKL/jira-analytics.git && cd jira-analytics
cp config/pipeline.example.yaml config/pipeline.yaml
# Edit config/pipeline.yaml with your catalog, warehouse, connection, and email

# 2. Sync and deploy
./scripts/sync_config.sh
databricks bundle deploy -t dev

# 3. Run the refresh job (ingest → silver → gold → metric views)
databricks bundle run jira_analytics_refresh -t dev
```

Open **AI/BI → Dashboards** for the Lakeview dashboard and **Genie** for natural-language Q&A.

## Documentation

| Page | Description |
|------|-------------|
| [docs/index.md](docs/index.md) | Overview, architecture, and design principles |
| [docs/prerequisites.md](docs/prerequisites.md) | Workspace requirements and tooling |
| [docs/configuration.md](docs/configuration.md) | `pipeline.yaml` field reference |
| [docs/deployment-profiles.md](docs/deployment-profiles.md) | Five deployment profile options |
| [docs/deployment-guide.md](docs/deployment-guide.md) | Step-by-step deployment |
| [docs/post-deployment.md](docs/post-deployment.md) | Running jobs, scheduling, troubleshooting |
| [docs/architecture.md](docs/architecture.md) | Data flow and table inventory |
| [docs/extending.md](docs/extending.md) | Adding metric views and dashboard widgets |

## License

Apache License 2.0 — see [LICENSE](LICENSE).
