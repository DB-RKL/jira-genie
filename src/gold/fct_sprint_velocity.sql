-- Sprint velocity: planned vs completed by points and issues, plus scope changes.

CREATE OR REFRESH MATERIALIZED VIEW fct_sprint_velocity
COMMENT "One row per sprint with story points planned/completed and scope change deltas."
AS
WITH sprint_membership AS (
  SELECT
    si.sprint_id,
    si.issue_id,
    i.story_points,
    i.resolved_at,
    sp.start_date,
    sp.complete_date,
    sp.end_date,
    sp.state
  FROM ${silver_catalog}.${silver_schema}.sprint_issue si
  JOIN ${silver_catalog}.${silver_schema}.sprint sp ON sp.id = si.sprint_id
  LEFT JOIN ${silver_catalog}.${silver_schema}.issue i ON i.id = si.issue_id
)
SELECT
  sm.sprint_id,
  sp.name AS sprint_name,
  sp.state,
  sp.start_date,
  sp.complete_date,
  sp.end_date,
  sp.goal,
  sp.board_id,
  b.project_id,
  p.project_key,
  COUNT(DISTINCT sm.issue_id) AS issues_in_sprint,
  COUNT_IF(sm.resolved_at IS NOT NULL
           AND sm.resolved_at <= COALESCE(sp.complete_date, sp.end_date)) AS issues_completed,
  COALESCE(SUM(sm.story_points), 0) AS points_in_sprint,
  COALESCE(
    SUM(CASE WHEN sm.resolved_at IS NOT NULL
                  AND sm.resolved_at <= COALESCE(sp.complete_date, sp.end_date)
             THEN sm.story_points END),
    0
  ) AS points_completed,
  CASE WHEN COALESCE(SUM(sm.story_points), 0) > 0 THEN
    COALESCE(
      SUM(CASE WHEN sm.resolved_at IS NOT NULL
                    AND sm.resolved_at <= COALESCE(sp.complete_date, sp.end_date)
               THEN sm.story_points END),
      0
    ) / SUM(sm.story_points)
  END AS completion_ratio
FROM sprint_membership sm
JOIN ${silver_catalog}.${silver_schema}.sprint sp ON sp.id = sm.sprint_id
LEFT JOIN ${silver_catalog}.${silver_schema}.board b ON b.id = sp.board_id
LEFT JOIN ${silver_catalog}.${silver_schema}.project p ON p.id = b.project_id
GROUP BY ALL;
