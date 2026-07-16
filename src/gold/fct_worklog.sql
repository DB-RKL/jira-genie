CREATE OR REFRESH MATERIALIZED VIEW fct_worklog
COMMENT "Worklog fact denormalized with project and assignee."
AS
SELECT
  w.id AS worklog_id,
  w.issue_id,
  i.issue_key,
  i.project_id,
  p.project_key,
  p.name AS project_name,
  w.author_id,
  u.display_name AS author_name,
  w.time_spent_seconds,
  w.time_spent_seconds / 3600.0 AS time_spent_hours,
  w.started_at,
  w.created_at,
  w.updated_at,
  CAST(w.started_at AS DATE) AS work_date
FROM rubjit_jira.silver.issue_worklog w
LEFT JOIN rubjit_jira.silver.issue i ON i.id = w.issue_id
LEFT JOIN rubjit_jira.silver.project p ON p.id = i.project_id
LEFT JOIN rubjit_jira.silver.`user` u ON u.account_id = w.author_id;
