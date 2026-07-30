"""Per-field and per-measure COMMENT text for Unity Catalog metric views."""

METRIC_VIEW_COLUMN_COMMENTS: dict[str, dict[str, dict[str, str]]] = {
    "metric_issue": {
        "fields": {
            "Issue Key": "Human-readable issue key (e.g. PROJ-123).",
            "Summary": "Issue summary / title.",
            "Project Key": "Project key for filtering and grouping.",
            "Project Name": "Project display name.",
            "Project Lead": "Project lead display name.",
            "Project Category": "Project category name.",
            "Issue Type": "Issue type (Story, Bug, Epic, …).",
            "Status": "Current workflow status.",
            "Status Category": "To Do, In Progress, or Done.",
            "Priority": "Issue priority.",
            "Assignee": "Current assignee display name.",
            "Current Sprint": "Active sprint name when applicable.",
            "Age Bucket": "Open-issue age bucket.",
            "Is Resolved": "Whether the issue is resolved.",
            "Created Date": "Issue creation date.",
            "Resolved Date": "Issue resolution date.",
        },
        "measures": {
            "Issue Count": "Total number of issues.",
            "Open Issues": "Count of unresolved issues.",
            "Resolved Issues": "Count of resolved issues.",
            "Open Critical": "Open issues with critical/highest priority.",
            "Stale Open": "Open issues older than 30 days.",
            "Median Cycle Time (days)": "Median days from in-progress to resolved.",
            "Total Story Points": "Sum of story points.",
        },
    },
    "metric_sprint_velocity": {
        "fields": {
            "Sprint": "Sprint name.",
            "Sprint State": "Sprint state (future, active, closed).",
            "Project Key": "Project key.",
            "Start Date": "Sprint start date.",
            "Complete Date": "Sprint completion date.",
        },
        "measures": {
            "Points Planned": "Story points committed to the sprint.",
            "Points Completed": "Story points completed in the sprint.",
            "Avg Completion Ratio": "Average ratio of completed to planned points.",
            "Issues Planned": "Issues in the sprint.",
            "Issues Completed": "Issues completed in the sprint.",
        },
    },
    "metric_issue_transitions": {
        "fields": {
            "Project Key": "Project key.",
            "From Status": "Previous workflow status.",
            "To Status": "New workflow status.",
        },
        "measures": {
            "Transition Count": "Number of status transitions.",
            "P90 Duration (hours)": "90th percentile hours in the previous status.",
            "Median Duration (hours)": "Median hours in the previous status.",
        },
    },
    "metric_worklog": {
        "fields": {
            "Project Key": "Project key.",
            "Author": "Worklog author display name.",
            "Work Date": "Date work was logged.",
        },
        "measures": {
            "Total Hours": "Total logged hours.",
            "Contributors": "Distinct contributors.",
        },
    },
    "metric_project_health": {
        "fields": {
            "Project Key": "Project key.",
            "Project Name": "Project display name.",
            "Project Lead": "Project lead display name.",
        },
        "measures": {
            "Open Issues": "Open issues in the project.",
            "Open Critical": "Open critical-priority issues.",
            "Stale Open": "Open issues older than 30 days.",
            "Resolved Issues (30d)": "Issues resolved in the last 30 days.",
        },
    },
    "metric_assignee_load": {
        "fields": {
            "Assignee": "Assignee display name.",
            "Project Key": "Project key.",
            "Priority": "Issue priority.",
            "Age Bucket": "Age bucket for open issues.",
        },
        "measures": {
            "Open Issues": "Open issues for the assignee.",
            "Open Story Points": "Sum of open story points.",
        },
    },
    "metric_team_productivity": {
        "fields": {
            "Assignee": "Team member display name.",
        },
        "measures": {
            "Resolved (30d)": "Issues resolved in the last 30 days.",
            "Open Now": "Currently open issues.",
            "Avg Cycle Time (days)": "Average cycle time in days.",
        },
    },
    "metric_time_in_status": {
        "fields": {
            "Project Key": "Project key.",
            "Status": "Workflow status name.",
            "Status Category": "Status category (To Do / In Progress / Done).",
        },
        "measures": {
            "P50 Duration (hours)": "Median hours spent in the status.",
            "P90 Duration (hours)": "90th percentile hours in the status.",
            "Observations": "Number of transition observations.",
        },
    },
}
