# Changelog

All notable changes to Jira Analytics are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Pytest unit-test suite under `tests/` (run with `python3 -m pytest tests/ -q`)
- CI pipeline (`.github/workflows/validate.yml`) with pytest, unit tests, and `databricks bundle validate -t dev` when secrets are present

### Changed

- Lakeview dashboard is now four Tempo-style audience pages (Portfolio, Flow, Sprint, Team) instead of one 33-widget canvas
- Metric views gained Created vs Resolved, WIP, unassigned/overdue, carryover, and windowed inflow/outflow measures for Genie and the dashboard
- New `metric_flow` view (plus `vw_created_resolved_daily`) for weekly created vs resolved and net backlog change
- Silver and gold DLT pipelines now use `pipeline_channel` variable (dev=PREVIEW, prod=CURRENT) instead of hardcoded `channel: PREVIEW`
- Removed hardcoded `development: true` override from silver/gold pipelines; DABs target mode now controls it
- New `prod` target is a fillable template driven by `prod_catalog`, `prod_warehouse_id`, `prod_owner_email`, and `prod_service_principal` variables; prod runs as service principal instead of named user
- `scripts/sync_config.sh` now patches only the `dev` target block in databricks.yml

### Fixed

- Data-quality expectations strengthened: `expect_or_fail` on primary keys of `issue`, `project`, `user`; `issue_field_history`/`issue_multiselect_history` upgraded to `expect_or_drop`; added key checks to dimension/lookup/bridge tables
- `src/silver/comment_apply.py` now logs skipped/missing tables instead of silently swallowing exceptions

## [0.1.0] - 2026-07-24

### Added

- Lakeflow Connect Jira ingestion pipeline (28 bronze tables)
- Silver DLT pipeline (normalized Jira ERD with Lakeflow column mapping)
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
