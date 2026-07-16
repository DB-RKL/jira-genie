-- Databricks business semantics layer: Unity Catalog metric views.
--
-- Metric views define governed dimensions + measures on top of the gold marts,
-- so the dashboard, Genie, and any BI/AI tool compute KPIs identically.
-- These are plain UC views (WITH METRICS), NOT DLT materialized views, so they
-- are created by a SQL task on a warehouse after the gold pipeline runs.
--
-- Query a measure with the MEASURE() function, e.g.:
--   SELECT `Project Key`, MEASURE(`Open Issues`), MEASURE(`Median Cycle Time (days)`)
--   FROM rubjit_jira.metrics.metric_issue
--   GROUP BY `Project Key`;

CREATE OR REPLACE VIEW rubjit_jira.metrics.metric_issue
WITH METRICS
LANGUAGE YAML
COMMENT 'Issue delivery semantics: throughput, cycle/lead time, backlog health.'
AS $$
version: 1.1
source: rubjit_jira.gold.fct_issue
filter: issue_id IS NOT NULL
fields:
  - name: Project Key
    expr: project_key
    synonyms: ['project', 'proj']
  - name: Project Name
    expr: project_name
  - name: Issue Type
    expr: issue_type
    synonyms: ['type']
  - name: Status
    expr: status_name
  - name: Status Category
    expr: status_category
    synonyms: ['category', 'To Do In Progress Done']
  - name: Priority
    expr: priority
  - name: Resolution
    expr: resolution
  - name: Assignee
    expr: assignee_name
    synonyms: ['owner', 'engineer']
  - name: Current Sprint
    expr: current_sprint_name
    synonyms: ['sprint']
  - name: Age Bucket
    expr: age_bucket
  - name: Is Resolved
    expr: is_resolved
  - name: Created Month
    expr: DATE_TRUNC('MONTH', created_at)
  - name: Resolved Month
    expr: DATE_TRUNC('MONTH', resolved_at)
  - name: Created Date
    expr: CAST(created_at AS DATE)
measures:
  - name: Issue Count
    expr: COUNT(1)
    synonyms: ['total issues', 'tickets']
  - name: Open Issues
    expr: COUNT_IF(NOT is_resolved)
    synonyms: ['open', 'backlog']
  - name: Resolved Issues
    expr: COUNT_IF(is_resolved)
    synonyms: ['closed', 'done']
  - name: Open Critical
    expr: COUNT_IF(NOT is_resolved AND priority IN ('Highest', 'Critical', 'Blocker'))
    synonyms: ['critical backlog']
  - name: Stale Open
    expr: COUNT_IF(NOT is_resolved AND age_days > 30)
    synonyms: ['aging issues', 'stale']
  - name: Avg Cycle Time (days)
    expr: AVG(cycle_time_days)
  - name: Median Cycle Time (days)
    expr: PERCENTILE_APPROX(cycle_time_days, 0.5)
    synonyms: ['p50 cycle time']
  - name: Avg Lead Time (days)
    expr: AVG(lead_time_days)
  - name: Total Story Points
    expr: SUM(story_points)
  - name: Avg Age (days)
    expr: AVG(age_days)
$$;


CREATE OR REPLACE VIEW rubjit_jira.metrics.metric_sprint_velocity
WITH METRICS
LANGUAGE YAML
COMMENT 'Sprint delivery semantics: planned vs completed points, completion ratio.'
AS $$
version: 1.1
source: rubjit_jira.gold.fct_sprint_velocity
fields:
  - name: Sprint
    expr: sprint_name
  - name: Sprint State
    expr: state
    synonyms: ['active closed future']
  - name: Project Key
    expr: project_key
    synonyms: ['project']
  - name: Complete Month
    expr: DATE_TRUNC('MONTH', complete_date)
measures:
  - name: Sprint Count
    expr: COUNT(DISTINCT sprint_id)
  - name: Points Planned
    expr: SUM(points_in_sprint)
    synonyms: ['committed points']
  - name: Points Completed
    expr: SUM(points_completed)
    synonyms: ['velocity', 'delivered points']
  - name: Avg Completion Ratio
    expr: AVG(completion_ratio)
    synonyms: ['completion rate']
  - name: Issues Planned
    expr: SUM(issues_in_sprint)
  - name: Issues Completed
    expr: SUM(issues_completed)
$$;


CREATE OR REPLACE VIEW rubjit_jira.metrics.metric_issue_transitions
WITH METRICS
LANGUAGE YAML
COMMENT 'Workflow semantics: status transitions and time-in-status.'
AS $$
version: 1.1
source: rubjit_jira.gold.fct_issue_transitions
joins:
  - name: project
    source: rubjit_jira.gold.dim_project
    on: source.project_id = project.project_id
    rely:
      at_most_one_match: true
fields:
  - name: Project Key
    expr: project.project_key
    synonyms: ['project']
  - name: From Status
    expr: from_status
  - name: To Status
    expr: to_status
    synonyms: ['status']
  - name: To Category
    expr: to_category_key
measures:
  - name: Transition Count
    expr: COUNT(1)
  - name: Avg Duration (hours)
    expr: AVG(duration_hours)
    synonyms: ['average time in status']
  - name: Median Duration (hours)
    expr: PERCENTILE_APPROX(duration_hours, 0.5)
    synonyms: ['p50 time in status']
  - name: P90 Duration (hours)
    expr: PERCENTILE_APPROX(duration_hours, 0.9)
    synonyms: ['p90 time in status']
$$;


CREATE OR REPLACE VIEW rubjit_jira.metrics.metric_worklog
WITH METRICS
LANGUAGE YAML
COMMENT 'Effort semantics: logged hours by project and contributor.'
AS $$
version: 1.1
source: rubjit_jira.gold.fct_worklog
fields:
  - name: Project Key
    expr: project_key
    synonyms: ['project']
  - name: Project Name
    expr: project_name
  - name: Author
    expr: author_name
    synonyms: ['contributor', 'engineer']
  - name: Work Date
    expr: work_date
  - name: Work Month
    expr: DATE_TRUNC('MONTH', work_date)
measures:
  - name: Total Hours
    expr: SUM(time_spent_hours)
    synonyms: ['logged hours', 'effort']
  - name: Worklog Entries
    expr: COUNT(1)
  - name: Contributors
    expr: COUNT(DISTINCT author_id)
    synonyms: ['unique contributors']
$$;
