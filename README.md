# Jira Analytics

This repo can be directly deployed in any Databricks workspace that ingests Jira data using [Lakeflow Connect](https://docs.databricks.com/en/connect/index.html). It:

1. Creates standard pipelines to transform bronze → silver (normalized Jira ERD) → gold analytical marts
2. Creates Unity Catalog metric views defining governed Jira delivery KPIs
3. Deploys an AI/BI dashboard (Portfolio, Flow, Sprint, Team) for created vs resolved, cycle time, velocity, and workload
4. Provisions a curated Genie space for conversational analytics over the same metric views

## Data Model

Medallion pipeline from raw Jira ingestion through governed metric views:

![Jira Analytics data model](docs/diagrams/jira_data_model_overview.png)

| Layer | Schema | Key objects |
|-------|--------|-------------|
| Bronze | `bronze_schema` | 28 Lakeflow Connect source tables |
| Silver | `silver_schema` | Normalized ERD: `issue`, `project`, `user`, `sprint_issue`, history |
| Gold | `gold_schema` | Facts, dimensions, aggregates (`fct_issue`, `fct_sprint_velocity`, …) |
| Metrics | `metrics_schema` | 9 Unity Catalog metric views (dashboard + Genie SSOT) |

Detailed ER diagrams: [Silver ERD](docs/diagrams/jira_silver_er.png) · [Gold star schema](docs/diagrams/jira_gold_star_schema.png) · [Source (Mermaid)](docs/diagrams/)

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/DB-RKL/jira-analytics.git && cd jira-analytics
cp config/pipeline.example.yaml config/pipeline.yaml
# Edit config/pipeline.yaml with your catalog, warehouse, connection, and email

# 2. Sync, validate, and deploy (use -p for dev so schema prefixes resolve correctly)
./scripts/sync_config.sh -t dev -p <your-profile>
databricks bundle validate -t dev -p <your-profile>
./scripts/deploy.sh -t dev -p <your-profile>   # bundle deploy + auto dashboard widget wiring

# 3. Run the refresh job (ingest → silver → gold → metric views)
databricks bundle run jira_analytics_refresh -t dev -p <your-profile>
```

Open **AI/BI → Dashboards** for the Lakeview dashboard and **Genie** for natural-language Q&A.

## Before you deploy

Read these expectations up front so the first run matches what you see in docs and demos.

| Topic | What to expect |
|-------|----------------|
| **Lakeflow Connect Jira** | Preview connector; OAuth U2M only. You need a working Jira connection and at least one successful bronze ingestion before silver runs. |
| **Local CLI required** | Run `./scripts/sync_config.sh` on your machine before every `bundle validate` / `deploy`. It patches `databricks.yml`, generates metric SQL and Genie JSON, and prepares the dashboard from the checked-in template. |
| **Dev schema prefixes** | In `dev` mode, schemas are prefixed with `dev_<user>_` (e.g. `dev_jane_jira_silver`). Always pass `-p <profile>` to `sync_config.sh` so prefixes resolve from your bundle summary. |
| **Sprint analytics** | Sprint velocity widgets need sprint membership on issues (`issues.sprint_ids` from Connect). Without it, sprint charts may be empty even when other KPIs look fine. |
| **Dashboard publish** | Use `./scripts/deploy.sh` (recommended) or `databricks bundle deploy` — both run a **postdeploy hook** that wires widgets via `push_dashboard.sh` when your profile includes the dashboard. |
| **Profiles** | `pipeline_only` runs ingest → silver → gold only. Add metrics, dashboard, or Genie via [deployment profiles](docs/deployment-profiles.md). |

Full checklist: [prerequisites](docs/prerequisites.md) · [deployment guide](docs/deployment-guide.md) · [post-deployment](docs/post-deployment.md).

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
| [docs/data-model.md](docs/data-model.md) | Layered data model diagrams (PNG + Mermaid source) |
| [docs/extending.md](docs/extending.md) | Adding metric views and dashboard widgets |

## License

Apache License 2.0 — see [LICENSE](LICENSE).
