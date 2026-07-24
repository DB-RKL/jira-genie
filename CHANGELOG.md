# Changelog

All notable changes to Jira Analytics are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-24

### Added

- Lakeflow Connect Jira ingestion pipeline (28 bronze tables)
- Silver DLT pipeline (Fivetran-parity ERD with Lakeflow column mapping)
- Gold DLT pipeline (issue facts, sprint velocity, transitions, worklogs, aggregates)
- Eight Unity Catalog metric views as single source of truth for dashboard and Genie
- Single-page AI/BI Lakeview dashboard (33 widgets)
- Curated Genie space with glossary, sample questions, and example SQL
- Config-driven deployment via `config/pipeline.yaml` and `scripts/sync_config.sh`
- Five deployment profiles: `full`, `with_dashboard`, `with_genie`, `with_metrics`, `pipeline_only`
- Orchestrated refresh job (`jira_analytics_refresh`)
- Customer documentation in `docs/`

### Design Notes

- Metric views use `MEASURE()` for governed KPIs — dashboard and Genie never re-implement aggregations
- Dev-mode schema prefix resolution via `bundle summary` during sync
- Lakeflow Connect lands Jira `issues` as `issues_without_deletes`; silver layer maps automatically

### Known Limitations

- Preview-channel Lakeflow Connect Jira connector
- OAuth U2M only for Jira connection
- Bronze ingestion may report failure on lookup-table retries even when data is present
