-- Gold dimensions. All reference silver via the fully-qualified silver namespace
-- so that the gold pipeline can run independently of the silver pipeline session.

CREATE OR REFRESH MATERIALIZED VIEW dim_user
COMMENT "Conformed user dimension with group memberships flattened to a comma list."
AS
SELECT
  u.account_id,
  u.display_name,
  u.email,
  u.is_active,
  u.account_type,
  u.locale,
  u.time_zone,
  CONCAT_WS(', ', COLLECT_LIST(g.group_name)) AS groups
FROM ${silver_catalog}.${silver_schema}.`user` u
LEFT JOIN ${silver_catalog}.${silver_schema}.user_group g
  ON g.account_id = u.account_id
GROUP BY ALL;


CREATE OR REFRESH MATERIALIZED VIEW dim_project
COMMENT "Project dimension with category, lead name, and current issue counts."
AS
SELECT
  p.id AS project_id,
  p.project_key,
  p.name AS project_name,
  p.description,
  p.project_type_key,
  pc.name AS category_name,
  p.lead_id,
  ul.display_name AS lead_name,
  p.is_archived,
  COUNT(i.id) AS total_issues,
  COUNT_IF(i.resolved_at IS NULL) AS open_issues,
  COUNT_IF(i.resolved_at IS NOT NULL) AS resolved_issues
FROM ${silver_catalog}.${silver_schema}.project p
LEFT JOIN ${silver_catalog}.${silver_schema}.project_category pc ON pc.id = p.project_category_id
LEFT JOIN ${silver_catalog}.${silver_schema}.`user` ul ON ul.account_id = p.lead_id
LEFT JOIN ${silver_catalog}.${silver_schema}.issue i ON i.project_id = p.id
GROUP BY ALL;


CREATE OR REFRESH MATERIALIZED VIEW dim_status
COMMENT "Status with its category (To Do / In Progress / Done) and a derived sort order."
AS
SELECT
  s.id AS status_id,
  s.name AS status_name,
  sc.category_key,
  sc.name AS category_name,
  sc.color_name,
  CASE sc.category_key
    WHEN 'new' THEN 1
    WHEN 'indeterminate' THEN 2
    WHEN 'done' THEN 3
    ELSE 99
  END AS category_order
FROM ${silver_catalog}.${silver_schema}.status s
LEFT JOIN ${silver_catalog}.${silver_schema}.status_category sc ON sc.id = s.status_category_id;


CREATE OR REFRESH MATERIALIZED VIEW dim_sprint
COMMENT "Sprint dimension with board, project (inferred), and effective duration."
AS
SELECT
  sp.id AS sprint_id,
  sp.name AS sprint_name,
  sp.state,
  sp.start_date,
  sp.end_date,
  sp.complete_date,
  sp.goal,
  sp.board_id,
  b.name AS board_name,
  b.project_id,
  DATEDIFF(DAY, sp.start_date, COALESCE(sp.complete_date, sp.end_date)) AS duration_days
FROM ${silver_catalog}.${silver_schema}.sprint sp
LEFT JOIN ${silver_catalog}.${silver_schema}.board b ON b.id = sp.board_id;


CREATE OR REFRESH MATERIALIZED VIEW dim_date
COMMENT "Date dimension covering 2 years before earliest issue creation through 1 year ahead."
AS
WITH bounds AS (
  SELECT
    DATE_SUB(MIN(CAST(created_at AS DATE)), 730) AS start_date,
    DATE_ADD(CURRENT_DATE(), 365) AS end_date
  FROM ${silver_catalog}.${silver_schema}.issue
),
dates AS (
  SELECT EXPLODE(SEQUENCE(start_date, end_date, INTERVAL 1 DAY)) AS date_key
  FROM bounds
)
SELECT
  date_key,
  EXTRACT(YEAR FROM date_key) AS year,
  EXTRACT(QUARTER FROM date_key) AS quarter,
  EXTRACT(MONTH FROM date_key) AS month,
  DATE_FORMAT(date_key, 'MMM') AS month_name,
  EXTRACT(WEEK FROM date_key) AS iso_week,
  EXTRACT(DAY FROM date_key) AS day_of_month,
  EXTRACT(DAYOFWEEK FROM date_key) AS day_of_week,
  DATE_FORMAT(date_key, 'EEE') AS day_name,
  CASE WHEN EXTRACT(DAYOFWEEK FROM date_key) IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekend
FROM dates;
