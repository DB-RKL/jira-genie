# Changelog

All notable changes to Jira Genie are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `deploy_jira_genie.py` bootstrap notebook: deploy end-to-end from a Databricks Git folder in the UI (ambient auth, installs the CLI if needed, runs sync -> deploy -> refresh) — no local machine required
- Pytest unit-test suite under `tests/` (run with `python3 -m pytest tests/ -q`)
- CI pipeline (`.github/workflows/validate.yml`) with pytest, unit tests, and `databricks bundle validate -t dev` when secrets are present

### Changed

- README and deployment guide now lead with the Databricks-UI (Git folder) deploy path, with the local CLI path as an alternative
- Lakeview dashboard is a single page with four labeled sections (Portfolio, Flow, Sprint, Team), each introduced by a markdown header
- Metric views gained Created vs Resolved, WIP, unassigned/overdue, carryover, and windowed inflow/outflow measures for Genie and the dashboard
- New `metric_flow` view (plus `vw_created_resolved_daily`) for weekly created vs resolved and net backlog change
- Silver and gold DLT pipelines now use `pipeline_channel` variable (dev=PREVIEW, prod=CURRENT) instead of hardcoded `channel: PREVIEW`
- Removed hardcoded `development: true` override from silver/gold pipelines; DABs target mode now controls it
- New `prod` target is a fillable template driven by `prod_catalog`, `prod_warehouse_id`, `prod_owner_email`, and `prod_service_principal` variables; prod runs as service principal instead of named user
- `scripts/sync_config.sh` now patches only the `dev` target block in databricks.yml

### Fixed

- `scripts/sync_config.sh`: generate the metric SQL, Genie JSON, **and dashboard** artifacts *before* the `bundle summary` prefix-resolution step. On a fresh checkout the summary previously failed with "failed to read serialized ... from file_path ...", aborting sync
- `scripts/deploy.sh`: defer the Genie space (for `full` / `with_genie`) and deploy it via the new `--only-genie` flag after the setup job builds the metric views. A first `bundle deploy` used to fail because Genie-space creation validates that the referenced metric views already exist
- `scripts/deploy.sh`, `sync_config.sh`, `postdeploy.sh`, `push_dashboard.sh`, `verify_dashboard.sh`: pass large `bundle validate`/`summary` JSON to Python via a temp file instead of an env var/argv, which overflowed the exec arg/env limit (`Argument list too long`, exit 126) on serverless. In `sync_config.sh` this had silently dropped the dev schema-prefix resolution, generating metric SQL / Genie JSON against the wrong (unprefixed) schema
- `scripts/deploy.sh`: `--only-genie` now deploys with `--force`, since the postdeploy hook's dashboard-widget wiring is seen by the bundle as a remote modification that otherwise aborts the deploy
- `deploy_jira_genie.py`: no longer pre-creates the layer schemas (the bundle owns them); pre-creating them made `bundle deploy` fail with `SCHEMA_ALREADY_EXISTS`
- `deploy_jira_genie.py`: run from a local working copy (prepending `~/bin` to PATH so the real CLI wins over the serverless web-terminal shim; copying build inputs to `/tmp` to avoid workspace-filesystem quirks like rejected `*.lvdash.json.bak` sidecars; restoring the executable bit on scripts)
- `docs/prerequisites.md`: document that the Jira connection user must be a Jira administrator (ingestion pulls admin-scoped objects; a non-admin user fails the whole pipeline)
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
- Orchestrated refresh job (`jira_genie_setup`)
- Customer documentation in `docs/`

### Design Notes

- Metric views use `MEASURE()` for governed KPIs — dashboard and Genie never re-implement aggregations
- Dev-mode schema prefix resolution via `bundle summary` during sync
- Lakeflow Connect lands Jira `issues` as `issues_without_deletes`; silver layer maps automatically

### Known Limitations

- Preview-channel Lakeflow Connect Jira connector
- OAuth U2M only for Jira connection
- Bronze ingestion may report failure on lookup-table retries even when data is present
