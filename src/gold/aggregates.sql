-- Aggregate marts used directly by dashboards and the app.

CREATE OR REFRESH MATERIALIZED VIEW agg_assignee_load
COMMENT "Current load per assignee: open issues split by priority and age bucket."
AS
SELECT
  f.assignee_id,
  f.assignee_name,
  f.project_id,
  f.project_key,
  f.priority,
  f.age_bucket,
  COUNT(*) AS open_issues,
  AVG(f.age_days) AS avg_age_days,
  SUM(COALESCE(f.story_points, 0)) AS open_story_points
FROM LIVE.fct_issue f
WHERE NOT f.is_resolved
  AND f.assignee_id IS NOT NULL
GROUP BY ALL;


CREATE OR REFRESH MATERIALIZED VIEW agg_project_health
COMMENT "Per-project KPIs used on the portfolio page."
AS
SELECT
  f.project_id,
  f.project_key,
  f.project_name,
  COUNT(*) AS total_issues,
  COUNT_IF(NOT f.is_resolved) AS open_issues,
  COUNT_IF(f.is_resolved) AS resolved_issues,
  COUNT_IF(NOT f.is_resolved AND f.priority IN ('Highest', 'Critical', 'Blocker')) AS open_critical,
  COUNT_IF(NOT f.is_resolved AND f.age_days > 30) AS stale_open,
  AVG(CASE WHEN f.is_resolved THEN f.cycle_time_days END) AS avg_cycle_time_days,
  AVG(CASE WHEN f.is_resolved THEN f.lead_time_days END) AS avg_lead_time_days,
  COUNT_IF(f.resolved_at >= CURRENT_DATE() - INTERVAL 30 DAYS) AS resolved_last_30d,
  COUNT_IF(f.created_at >= CURRENT_DATE() - INTERVAL 30 DAYS) AS created_last_30d
FROM LIVE.fct_issue f
GROUP BY ALL;


CREATE OR REFRESH MATERIALIZED VIEW agg_team_productivity
COMMENT "Per-assignee productivity over the last 90 days."
AS
SELECT
  f.assignee_id,
  f.assignee_name,
  COUNT_IF(f.is_resolved AND f.resolved_at >= CURRENT_DATE() - INTERVAL 30 DAYS) AS resolved_30d,
  COUNT_IF(f.is_resolved AND f.resolved_at >= CURRENT_DATE() - INTERVAL 90 DAYS) AS resolved_90d,
  COUNT_IF(NOT f.is_resolved) AS open_now,
  AVG(CASE WHEN f.is_resolved THEN f.cycle_time_days END) AS avg_cycle_time_days,
  AVG(CASE WHEN f.is_resolved THEN f.lead_time_days END) AS avg_lead_time_days,
  COUNT_IF(NOT f.is_resolved AND f.priority IN ('Highest', 'Critical', 'Blocker')) AS open_critical
FROM LIVE.fct_issue f
WHERE f.assignee_id IS NOT NULL
GROUP BY ALL;


CREATE OR REFRESH MATERIALIZED VIEW agg_time_in_status
COMMENT "Time-in-status distribution per (project, status), used for box-plot/p50/p90."
AS
SELECT
  t.project_id,
  p.project_key,
  t.to_status AS status_name,
  t.to_category_key AS status_category_key,
  COUNT(*) AS observations,
  PERCENTILE_APPROX(t.duration_hours, 0.5) AS p50_hours,
  PERCENTILE_APPROX(t.duration_hours, 0.9) AS p90_hours,
  AVG(t.duration_hours) AS avg_hours
FROM LIVE.fct_issue_transitions t
LEFT JOIN rubjit_jira.silver.project p ON p.id = t.project_id
WHERE t.duration_hours IS NOT NULL
GROUP BY ALL;
