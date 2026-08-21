-- Denormalized issue fact: one row per issue with all dim joins and derived metrics.

CREATE OR REFRESH MATERIALIZED VIEW fct_issue
COMMENT "Denormalized issue fact with cycle time, lead time, and current sprint."
AS
WITH first_in_progress AS (
  -- First time an issue moved into an 'In Progress' (indeterminate) status, used for cycle time.
  SELECT
    h.issue_id,
    MIN(h.updated_at) AS started_at
  FROM ${silver_catalog}.${silver_schema}.issue_field_history h
  JOIN ${silver_catalog}.${silver_schema}.status s ON CAST(h.value AS STRING) = CAST(s.id AS STRING)
  JOIN ${silver_catalog}.${silver_schema}.status_category sc ON sc.id = s.status_category_id
  WHERE h.field_id = '${status_field_id}'
    AND sc.category_key = '${in_progress_category_key}'
  GROUP BY h.issue_id
),
current_sprint AS (
  SELECT issue_id, MAX(sprint_id) AS current_sprint_id
  FROM ${silver_catalog}.${silver_schema}.sprint_issue si
  JOIN ${silver_catalog}.${silver_schema}.sprint sp ON sp.id = si.sprint_id
  WHERE sp.state IN ('active', 'closed')
  GROUP BY issue_id
)
SELECT
  i.id AS issue_id,
  i.issue_key,
  i.summary,
  i.project_id,
  p.project_key,
  p.name AS project_name,
  i.issue_type_id,
  it.name AS issue_type,
  i.status_id,
  ds.status_name,
  ds.category_key AS status_category_key,
  ds.category_name AS status_category,
  i.priority_id,
  pr.name AS priority,
  i.resolution_id,
  rs.name AS resolution,
  i.assignee_id,
  ua.display_name AS assignee_name,
  i.reporter_id,
  ur.display_name AS reporter_name,
  i.creator_id,
  i.parent_id,
  ei.epic_id,
  cs.current_sprint_id,
  ds_sprint.sprint_name AS current_sprint_name,
  i.created_at,
  i.updated_at,
  i.resolved_at,
  i.due_date,
  i.story_points,
  i.original_estimate_seconds,
  i.remaining_estimate_seconds,
  i.time_spent_seconds,
  i.watch_count,
  i.vote_count,
  i.labels,
  fip.started_at AS first_in_progress_at,
  CASE WHEN i.resolved_at IS NOT NULL THEN TRUE ELSE FALSE END AS is_resolved,
  CASE
    WHEN i.resolved_at IS NOT NULL AND fip.started_at IS NOT NULL
      THEN DATEDIFF(DAY, fip.started_at, i.resolved_at)
  END AS cycle_time_days,
  CASE WHEN i.resolved_at IS NOT NULL
    THEN DATEDIFF(DAY, i.created_at, i.resolved_at)
  END AS lead_time_days,
  CASE WHEN i.resolved_at IS NULL
    THEN DATEDIFF(DAY, i.created_at, CURRENT_TIMESTAMP())
  END AS age_days,
  CASE WHEN i.resolved_at IS NULL THEN
    CASE
      WHEN DATEDIFF(DAY, i.created_at, CURRENT_TIMESTAMP()) < 7 THEN '0-7d'
      WHEN DATEDIFF(DAY, i.created_at, CURRENT_TIMESTAMP()) < 14 THEN '7-14d'
      WHEN DATEDIFF(DAY, i.created_at, CURRENT_TIMESTAMP()) < 30 THEN '14-30d'
      WHEN DATEDIFF(DAY, i.created_at, CURRENT_TIMESTAMP()) < 90 THEN '30-90d'
      ELSE '90d+'
    END
  END AS age_bucket
FROM ${silver_catalog}.${silver_schema}.issue i
LEFT JOIN ${silver_catalog}.${silver_schema}.project p ON p.id = i.project_id
LEFT JOIN ${silver_catalog}.${silver_schema}.issue_type it ON it.id = i.issue_type_id
LEFT JOIN LIVE.dim_status ds ON ds.status_id = i.status_id
LEFT JOIN ${silver_catalog}.${silver_schema}.priority pr ON pr.id = i.priority_id
LEFT JOIN ${silver_catalog}.${silver_schema}.resolution rs ON rs.id = i.resolution_id
LEFT JOIN ${silver_catalog}.${silver_schema}.`user` ua ON ua.account_id = i.assignee_id
LEFT JOIN ${silver_catalog}.${silver_schema}.`user` ur ON ur.account_id = i.reporter_id
LEFT JOIN ${silver_catalog}.${silver_schema}.epic_issue ei ON ei.issue_id = i.id
LEFT JOIN current_sprint cs ON cs.issue_id = i.id
LEFT JOIN LIVE.dim_sprint ds_sprint ON ds_sprint.sprint_id = cs.current_sprint_id
LEFT JOIN first_in_progress fip ON fip.issue_id = i.id;
