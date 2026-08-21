# Databricks notebook source
# MAGIC %md
# MAGIC # Configure Jira Analytics
# MAGIC
# MAGIC Use this notebook to pick where each layer lives in Unity Catalog before deploying.
# MAGIC
# MAGIC 1. Set the widgets below.
# MAGIC 2. Run validation cells.
# MAGIC 3. Copy the generated YAML into **`config/pipeline.yaml`**, then run `./scripts/sync_config.sh`.

# COMMAND ----------

dbutils.widgets.text("catalog", "my_company_catalog", "UC catalog (must exist)")
dbutils.widgets.text("bronze_schema", "jira_bronze", "Bronze schema")
dbutils.widgets.text("silver_schema", "jira_silver", "Silver schema")
dbutils.widgets.text("gold_schema", "jira_gold", "Gold schema")
dbutils.widgets.text("metrics_schema", "jira_metrics", "Metrics schema")
dbutils.widgets.text("jira_connection", "my-jira-connection", "Lakeflow Connect Jira connection")
dbutils.widgets.text("warehouse_id", "", "SQL warehouse ID")
dbutils.widgets.dropdown("deployment_profile", "full", ["full", "with_dashboard", "with_genie", "with_metrics", "pipeline_only"], "Deployment profile")

catalog = dbutils.widgets.get("catalog").strip()
bronze_schema = dbutils.widgets.get("bronze_schema").strip()
silver_schema = dbutils.widgets.get("silver_schema").strip()
gold_schema = dbutils.widgets.get("gold_schema").strip()
metrics_schema = dbutils.widgets.get("metrics_schema").strip()
jira_connection = dbutils.widgets.get("jira_connection").strip()
warehouse_id = dbutils.widgets.get("warehouse_id").strip()
deployment_profile = dbutils.widgets.get("deployment_profile").strip()

print("Layer map:")
for layer, schema in [("bronze", bronze_schema), ("silver", silver_schema), ("gold", gold_schema), ("metrics", metrics_schema)]:
    print(f"  {layer:8} → {catalog}.{schema}")

# COMMAND ----------

spark.sql(f"DESCRIBE CATALOG EXTENDED `{catalog}`").display()

# COMMAND ----------

for schema in [bronze_schema, silver_schema, gold_schema, metrics_schema]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")
    print(f"OK  {catalog}.{schema}")

# COMMAND ----------

owner = spark.sql("SELECT current_user()").collect()[0][0]

yaml_block = f"""# Copy to config/pipeline.yaml
deployment_profile: "{deployment_profile}"
warehouse_id: "{warehouse_id}"
owner_email: "{owner}"

catalog: "{catalog}"
bronze_schema: "{bronze_schema}"
silver_schema: "{silver_schema}"
gold_schema: "{gold_schema}"
metrics_schema: "{metrics_schema}"

jira_connection_name: "{jira_connection}"

dashboard_name: "Jira Analytics"
genie_space_name: "Jira Analytics"
"""

print(yaml_block)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deploy (run locally after saving pipeline.yaml)
# MAGIC
# MAGIC ```bash
# MAGIC ./scripts/sync_config.sh
# MAGIC databricks bundle deploy -t dev
# MAGIC databricks bundle run jira_analytics_setup -t dev
# MAGIC ```
