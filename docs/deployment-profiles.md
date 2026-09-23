# Deployment Profiles

Choose a profile in `config/pipeline.yaml` via `deployment_profile`. The sync script switches which resource folder is included in `databricks.yml`.

| Profile | Deploys | When to use |
|---------|---------|-------------|
| `full` | Pipelines + metrics job + dashboard + Genie | First-time setup |
| `with_dashboard` | Pipelines + metrics job + dashboard | Skip Genie |
| `with_genie` | Pipelines + metrics job + Genie | Skip dashboard |
| `with_metrics` | Pipelines + metrics job | Data + semantic layer only |
| `pipeline_only` | Pipelines + refresh job | Data engineering only |

All profiles include `resources/common/schemas.yml` (bronze, silver, gold, metrics schemas).

## DLT Pipeline Channels

The silver and gold DLT pipelines are configured per target:

- **dev**: `pipeline_channel: PREVIEW` — matches the preview-channel Lakeflow Connect Jira source connector
- **prod**: `pipeline_channel: CURRENT` — uses the stable DLT release channel

The Lakeflow Connect ingestion pipeline always uses PREVIEW because the Jira connector is only available in preview.

## Resource Matrix

| Resource | pipeline_only | with_metrics | with_dashboard | with_genie | full |
|----------|:---:|:---:|:---:|:---:|:---:|
| UC schemas | ✓ | ✓ | ✓ | ✓ | ✓ |
| Lakeflow Connect ingestion pipeline | ✓ | ✓ | ✓ | ✓ | ✓ |
| Silver + gold DLT pipelines | ✓ | ✓ | ✓ | ✓ | ✓ |
| `jira_genie_setup` job (silver → gold → metrics task) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Lakeview dashboard | | | ✓ | | ✓ |
| Genie space | | | | ✓ | ✓ |

## Staged Deployment

For first-time setup, you can deploy in stages even with `full` profile by temporarily changing `deployment_profile`:

```bash
# 1. Pipelines only
# Set deployment_profile: "pipeline_only" in pipeline.yaml
./scripts/sync_config.sh -t dev -p <profile>
./scripts/deploy.sh -t dev -p <profile>
databricks bundle run jira_genie_setup -t dev -p <profile>

# 2. Add consumption layer
# Set deployment_profile: "full"
./scripts/sync_config.sh -t dev -p <profile>
./scripts/deploy.sh -t dev -p <profile>
```

Genie and dashboard require metric views to exist before they deploy successfully.
