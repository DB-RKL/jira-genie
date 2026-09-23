"""Read pipeline configuration from config/pipeline.yaml for scripts and notebooks."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE_CONFIG = ROOT / "config" / "pipeline.yaml"
PIPELINE_EXAMPLE = ROOT / "config" / "pipeline.example.yaml"


def _parse_flat_yaml(text: str) -> dict[str, str]:
    """Parse simple key: value YAML (no nesting)."""
    cfg: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.match(r"^([a-z_]+):\s*(.+?)\s*$", stripped)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip().strip("'\"")
        cfg[key] = val
    return cfg


def pipeline_config(overrides: dict | None = None) -> dict[str, str]:
    """Return resolved catalog, schemas, and deployment settings."""
    path = PIPELINE_CONFIG if PIPELINE_CONFIG.exists() else PIPELINE_EXAMPLE
    cfg = _parse_flat_yaml(path.read_text()) if path.exists() else {}

    cfg.setdefault("catalog", "")
    cfg.setdefault("bronze_schema", "jira_bronze")
    cfg.setdefault("silver_schema", "jira_silver")
    cfg.setdefault("gold_schema", "jira_gold")
    cfg.setdefault("metrics_schema", "jira_metrics")
    cfg.setdefault("deployment_profile", "full")
    cfg.setdefault("dashboard_name", "Jira Genie")
    cfg.setdefault("genie_space_name", "Jira Genie")

    catalog = cfg.get("catalog", "")
    cfg["bronze_catalog"] = cfg.get("bronze_catalog", catalog)
    cfg["silver_catalog"] = cfg.get("silver_catalog", catalog)
    cfg["gold_catalog"] = cfg.get("gold_catalog", catalog)
    cfg["metrics_catalog"] = cfg.get("metrics_catalog", catalog)

    if overrides:
        cfg.update({k: str(v) for k, v in overrides.items()})
        if "catalog" in overrides:
            for layer in ("bronze", "silver", "gold", "metrics"):
                ck = f"{layer}_catalog"
                if ck not in overrides:
                    cfg[ck] = overrides["catalog"]

    return cfg


# Backward-compatible alias used by build_assets.py
def layer_config(overrides: dict | None = None) -> dict[str, str]:
    return pipeline_config(overrides)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Print pipeline config from config/pipeline.yaml")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    cfg = pipeline_config()
    if args.json:
        print(json.dumps(cfg, indent=2))
    else:
        key_map = {
            "catalog": "CATALOG",
            "bronze_catalog": "BRONZE_CATALOG",
            "bronze_schema": "BRONZE_SCHEMA",
            "silver_catalog": "SILVER_CATALOG",
            "silver_schema": "SILVER_SCHEMA",
            "gold_catalog": "GOLD_CATALOG",
            "gold_schema": "GOLD_SCHEMA",
            "metrics_catalog": "METRICS_CATALOG",
            "metrics_schema": "METRICS_SCHEMA",
            "jira_connection_name": "JIRA_CONNECTION_NAME",
            "warehouse_id": "WAREHOUSE_ID",
            "owner_email": "OWNER_EMAIL",
            "deployment_profile": "DEPLOYMENT_PROFILE",
            "dashboard_name": "DASHBOARD_NAME",
            "genie_space_name": "GENIE_SPACE_NAME",
        }
        for k in key_map:
            if k in cfg:
                print(f"export {key_map[k]}={json.dumps(cfg[k])}")


if __name__ == "__main__":
    main()
