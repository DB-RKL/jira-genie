-- Status transition fact: one row per (issue, status change) with entered/exited and duration.

CREATE OR REFRESH MATERIALIZED VIEW fct_issue_transitions
COMMENT "Status transition fact derived from issue_field_history (field_id = 'status')."
AS
WITH status_changes AS (
  SELECT
    h.issue_id,
    CAST(h.value AS STRING) AS status_id_raw,
    h.updated_at AS entered_at,
    LEAD(h.updated_at) OVER (PARTITION BY h.issue_id ORDER BY h.updated_at) AS exited_at,
    LAG(CAST(h.value AS STRING)) OVER (PARTITION BY h.issue_id ORDER BY h.updated_at) AS prev_status_id_raw
  FROM ${silver_catalog}.${silver_schema}.issue_field_history h
  WHERE h.field_id = '${status_field_id}'
)
SELECT
  sc.issue_id,
  ip.project_id,
  ip.issue_key,
  sc.prev_status_id_raw AS from_status_id,
  s_from.name AS from_status,
  sc.status_id_raw AS to_status_id,
  s_to.name AS to_status,
  cat_to.category_key AS to_category_key,
  sc.entered_at,
  sc.exited_at,
  CASE WHEN sc.exited_at IS NOT NULL
    THEN (UNIX_TIMESTAMP(sc.exited_at) - UNIX_TIMESTAMP(sc.entered_at)) / 3600.0
  END AS duration_hours
FROM status_changes sc
LEFT JOIN ${silver_catalog}.${silver_schema}.issue ip ON ip.id = sc.issue_id
LEFT JOIN ${silver_catalog}.${silver_schema}.status s_from
  ON TRY_CAST(sc.prev_status_id_raw AS BIGINT) = s_from.id
LEFT JOIN ${silver_catalog}.${silver_schema}.status s_to
  ON TRY_CAST(sc.status_id_raw AS BIGINT) = s_to.id
LEFT JOIN ${silver_catalog}.${silver_schema}.status_category cat_to
  ON cat_to.id = s_to.status_category_id;
