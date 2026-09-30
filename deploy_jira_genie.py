# Databricks notebook source
# MAGIC %md
# MAGIC # Deploy Jira Genie (from a Databricks Git folder)
# MAGIC
# MAGIC Run this notebook to deploy the whole accelerator **without leaving the Databricks UI** —
# MAGIC no local machine, no CLI install on your laptop.
# MAGIC
# MAGIC ### How to use it
# MAGIC 1. Add this repo as a **Git folder**: sidebar -> **Workspace** -> your folder ->
# MAGIC    **Create -> Git folder** -> `https://github.com/DB-RKL/jira-genie.git`.
# MAGIC 2. Make sure the [prerequisites](docs/prerequisites.md) are in place: a Unity Catalog
# MAGIC    catalog you can create schemas in, a SQL warehouse, and a **Lakeflow Connect Jira
# MAGIC    connection** (OAuth U2M — must be created interactively, see below).
# MAGIC 3. Attach this notebook to a cluster (classic or serverless), fill in the widgets at
# MAGIC    the top, then **Run all**.
# MAGIC
# MAGIC The notebook writes `config/pipeline.yaml` from the widget values, then runs the same
# MAGIC `sync_config.sh` -> `deploy.sh` -> setup-job steps the CLI workflow uses — authenticated
# MAGIC automatically as you (the notebook's identity).
# MAGIC
# MAGIC > **Jira connection is manual.** The Lakeflow Connect Jira connector is OAuth U2M only,
# MAGIC > so the connection itself must be created interactively in **Catalog Explorer ->
# MAGIC > Connections** before you deploy. Enter its exact name in the `jira_connection` widget.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Configure
# MAGIC Set these widgets (they appear at the top of the notebook), then run the cell.

# COMMAND ----------

dbutils.widgets.text("catalog", "", "1. UC catalog (must already exist)")
dbutils.widgets.text("warehouse_id", "", "2. SQL warehouse ID")
dbutils.widgets.text("jira_connection", "", "3. Lakeflow Connect Jira connection name")
dbutils.widgets.dropdown(
    "deployment_profile",
    "full",
    ["full", "with_dashboard", "with_genie", "with_metrics", "pipeline_only"],
    "4. What to deploy",
)
dbutils.widgets.dropdown(
    "run_ingestion", "yes", ["yes", "no"],
    "5. Run Jira ingestion? (needed once to populate bronze)",
)
dbutils.widgets.text("bronze_schema", "jira_bronze", "Bronze schema")
dbutils.widgets.text("silver_schema", "jira_silver", "Silver schema")
dbutils.widgets.text("gold_schema", "jira_gold", "Gold schema")
dbutils.widgets.text("metrics_schema", "jira_metrics", "Metrics schema")
dbutils.widgets.text("dashboard_name", "Jira Genie", "Dashboard display name")
dbutils.widgets.text("genie_space_name", "Jira Genie", "Genie space title")
dbutils.widgets.text("repo_root", "", "Repo root (blank = auto-detect)")

# This notebook deploys the `dev` target (runs as you, no service principal). It prefixes
# schemas with dev_<user>_ — ideal for demos and evaluation. For a production deployment
# (plain schema names, run as a service principal), use the CLI path in docs/deployment-guide.md.
TARGET = "dev"

cfg = {k: dbutils.widgets.get(k).strip() for k in [
    "catalog", "warehouse_id", "jira_connection", "deployment_profile", "run_ingestion",
    "bronze_schema", "silver_schema", "gold_schema", "metrics_schema",
    "dashboard_name", "genie_space_name", "repo_root",
]}
PROFILE_HAS_GENIE = cfg["deployment_profile"] in ("full", "with_genie")

# jira_connection is required because sync_config.sh mandates it and the ingestion pipeline
# references it. If you have no connection yet (bronze already exists, or you want transforms
# only), deploy from the CLI with ./scripts/deploy.sh --skip-ingestion instead.
required = ["catalog", "warehouse_id", "jira_connection"]
missing = [k for k in required if not cfg[k]]
assert not missing, f"Fill in these widgets first: {missing}"

owner_email = spark.sql("SELECT current_user()").collect()[0][0]
print("Deploying as:", owner_email)
for layer in ["bronze", "silver", "gold", "metrics"]:
    print(f"  {layer:8} -> {cfg['catalog']}.{cfg[layer + '_schema']}")
print("  profile ->", cfg["deployment_profile"], "| target ->", TARGET)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Set up auth, locate the repo, and find the Databricks CLI
# MAGIC Uses the notebook's own credentials (no PAT to paste). Installs the CLI if the cluster
# MAGIC does not already have the bundle-capable Databricks CLI on `PATH`.

# COMMAND ----------

import os
import shutil
import subprocess

ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()

# Locate the repo root (the folder holding databricks.yml). In a Git folder the notebook's
# workspace path maps to /Workspace/<path>, so derive the root from this notebook's location.
detected_root = "/Workspace" + os.path.dirname(ctx.notebookPath().get())
REPO_ROOT = cfg["repo_root"] or detected_root
assert os.path.exists(os.path.join(REPO_ROOT, "databricks.yml")), (
    f"databricks.yml not found under {REPO_ROOT}. Set the 'repo_root' widget to the folder "
    "that contains databricks.yml (e.g. /Workspace/Users/you/jira-genie)."
)
print("Repo root (source):", REPO_ROOT)

# Copy the repo to a local working dir on the driver and run everything from there.
# The sync/deploy scripts write generated artifacts (metric SQL, Genie JSON, patched
# dashboard, sed backups) next to the sources. Doing that directly in the /Workspace mount
# fails — the workspace filesystem enforces special rules on .lvdash.json/.geniespace.json
# files and rejects sidecars like *.lvdash.json.bak. A plain local dir has no such quirks,
# and `bundle deploy` still uploads from here to the workspace normally.
#
# Copy only the build inputs. We deliberately skip notebook objects (this notebook, docs)
# because notebooks in /Workspace cannot be read as plain files (raises Errno 95) — and the
# bundle does not need them.
WORK_ROOT = "/tmp/jira_genie_build"
shutil.rmtree(WORK_ROOT, ignore_errors=True)
os.makedirs(WORK_ROOT, exist_ok=True)
for item in ["databricks.yml", "VERSION", "scripts", "resources", "src", "config"]:
    src = os.path.join(REPO_ROOT, item)
    dst = os.path.join(WORK_ROOT, item)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    elif os.path.exists(src):
        shutil.copy2(src, dst)
assert os.path.exists(os.path.join(WORK_ROOT, "databricks.yml")), "copy failed: databricks.yml missing"
# Restore the executable bit: workspace sync + shutil.copy drop it, but the scripts call
# each other directly (e.g. postdeploy -> push_dashboard.sh), which needs +x (else exit 126).
import stat
scripts_dir = os.path.join(WORK_ROOT, "scripts")
for f in os.listdir(scripts_dir):
    if f.endswith(".sh"):
        p = os.path.join(scripts_dir, f)
        os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
print("Working copy:", WORK_ROOT)

# Ambient auth for the CLI: host + short-lived notebook token.
# PATH: prepend ~/bin (where the installer below puts the CLI on Databricks compute).
# This MUST come before /usr/local/bin: serverless ships a shim there that intercepts
# `databricks` and refuses to run ("only supported from the web terminal"). Prepending ~/bin
# makes the real binary win.
USER_BIN = os.path.expanduser("~/bin")
ENV = {
    **os.environ,
    "DATABRICKS_HOST": ctx.apiUrl().get(),
    "DATABRICKS_TOKEN": ctx.apiToken().get(),
    "DATABRICKS_BUNDLE_TARGET": TARGET,
    "PATH": USER_BIN + ":" + os.environ.get("PATH", ""),
}


def sh(cmd, cwd=WORK_ROOT, check=True):
    """Run a shell command in the working copy with ambient auth, streaming combined output."""
    print(f"\n$ {cmd}")
    p = subprocess.run(cmd, shell=True, cwd=cwd, env=ENV,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.stdout:
        print(p.stdout)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed (exit {p.returncode}): {cmd}")
    return p


# Ensure a bundle-capable Databricks CLI is available.
def cli_ok():
    r = subprocess.run("databricks version", shell=True, env=ENV,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode == 0 and "bundle" in subprocess.run(
        "databricks bundle -h", shell=True, env=ENV,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True).stdout.lower()


if cli_ok():
    sh("databricks version")
else:
    print("Installing the Databricks CLI (needs internet egress to github.com)...")
    # On Databricks compute the installer detects DATABRICKS_RUNTIME_VERSION and installs to
    # ~/bin (no sudo needed); that dir is already on PATH via ENV above.
    sh("curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh")
    assert cli_ok(), (
        "Databricks CLI still not available. This workspace may block egress to github.com. "
        "Install the CLI on the cluster (or run the local CLI workflow from your laptop — see README)."
    )
    sh("databricks version")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Verify the catalog exists
# MAGIC The catalog must already exist. Do **not** pre-create the layer schemas here — the bundle
# MAGIC owns them, and `bundle deploy` fails with `SCHEMA_ALREADY_EXISTS` if they were created
# MAGIC out-of-band first.

# COMMAND ----------

spark.sql(f"DESCRIBE CATALOG `{cfg['catalog']}`")  # fails fast if the catalog is missing
print(f"OK  catalog {cfg['catalog']} exists. Schemas will be created by the bundle:")
for layer in ["bronze", "silver", "gold", "metrics"]:
    print(f"  {cfg['catalog']}.{cfg[layer + '_schema']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Write `config/pipeline.yaml`
# MAGIC This is the single config file the deploy scripts read. It is written into the local
# MAGIC working copy (`/tmp`), so it never touches the repo in your workspace.

# COMMAND ----------

pipeline_yaml = f"""# Generated by deploy_jira_genie.py from notebook widgets.
deployment_profile: "{cfg['deployment_profile']}"
warehouse_id: "{cfg['warehouse_id']}"
owner_email: "{owner_email}"

catalog: "{cfg['catalog']}"
bronze_schema: "{cfg['bronze_schema']}"
silver_schema: "{cfg['silver_schema']}"
gold_schema: "{cfg['gold_schema']}"
metrics_schema: "{cfg['metrics_schema']}"

jira_connection_name: "{cfg['jira_connection']}"

dashboard_name: "{cfg['dashboard_name']}"
genie_space_name: "{cfg['genie_space_name']}"
"""

config_path = os.path.join(WORK_ROOT, "config", "pipeline.yaml")
os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, "w") as f:
    f.write(pipeline_yaml)
print("Wrote", config_path)
print(pipeline_yaml)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Sync config and generate artifacts
# MAGIC Patches the bundle's target block and generates the metric SQL, Genie JSON, and dashboard
# MAGIC from the checked-in templates.

# COMMAND ----------

sh(f"bash ./scripts/sync_config.sh -t {TARGET}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Validate and deploy the infrastructure
# MAGIC `deploy.sh` runs `bundle deploy` (schemas, pipelines, job, dashboard) and auto-wires the
# MAGIC dashboard widgets. The **Genie space is deferred here on purpose** — Genie creation checks
# MAGIC that every metric view already exists, and those are only built in step 8. It is deployed
# MAGIC in step 9.

# COMMAND ----------

sh(f"databricks bundle validate -t {TARGET}")

# COMMAND ----------

# --skip-sync: step 5 already ran sync_config.sh, so don't repeat it here.
# deploy.sh defers the Genie space automatically for the full / with_genie profiles.
sh(f"bash ./scripts/deploy.sh -t {TARGET} --skip-sync")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Ingest Jira into bronze
# MAGIC Runs the Lakeflow Connect ingestion pipeline once to populate bronze (silver reads from it).
# MAGIC Skip this (set the `run_ingestion` widget to `no`) if bronze is already populated. This can
# MAGIC take several minutes and requires the Jira connection to be authorized.
# MAGIC
# MAGIC > The connecting Jira user must be a **Jira administrator** — ingestion pulls admin-scoped
# MAGIC > objects (security schemes/levels, application/project roles, statuses). A non-admin user
# MAGIC > fails with `JIRA_ADMIN_PERMISSION_MISSING`, which fails the whole pipeline. See
# MAGIC > [docs/prerequisites.md](docs/prerequisites.md).

# COMMAND ----------

if cfg["run_ingestion"] == "yes":
    sh(f"databricks bundle run jira_ingestion_pipeline -t {TARGET}")
else:
    print("Skipped ingestion (run_ingestion=no). Ensure bronze is already populated.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Build silver -> gold -> metric views
# MAGIC Runs the setup job. Metric views must exist before the Genie space can be created (step 9).

# COMMAND ----------

sh(f"databricks bundle run jira_genie_setup -t {TARGET}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Deploy the Genie space
# MAGIC Now that the metric views exist, create the Genie space. (Runs only when your profile
# MAGIC includes Genie: `full` or `with_genie`.)

# COMMAND ----------

if PROFILE_HAS_GENIE:
    sh(f"bash ./scripts/deploy.sh -t {TARGET} --skip-sync --only-genie")
else:
    print(f"Profile '{cfg['deployment_profile']}' has no Genie space — nothing to deploy.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Done — where to look
# MAGIC - **Catalog Explorer**: schemas under your catalog. This deploys the `dev` target, so they
# MAGIC   are prefixed with `dev_<user>_` (e.g. `dev_jane_jira_silver`).
# MAGIC - **AI/BI -> Dashboards**: the "Jira Genie" dashboard.
# MAGIC - **Genie**: the "Jira Genie" space for natural-language Q&A.
# MAGIC
# MAGIC See [docs/post-deployment.md](docs/post-deployment.md) for scheduling, refresh, and troubleshooting.
