"""Unity Catalog table and column comment definitions for the silver layer."""

SILVER_TABLE_COMMENTS: dict[str, dict[str, object]] = {
    "issue": {
        "comment": "Canonical issue entity (core fields only; custom/historical fields live in issue_field_history).",
        "columns": {
            "id": "Jira issue id.",
            "issue_key": "Human-readable issue key (e.g. PROJ-123).",
            "project_id": "Foreign key to project.",
            "issue_type_id": "Foreign key to issue_type.",
            "summary": "Issue summary / title.",
            "description": "Issue description body.",
            "priority_id": "Foreign key to priority.",
            "status_id": "Foreign key to status.",
            "resolution_id": "Foreign key to resolution when resolved.",
            "reporter_id": "Reporter user account id.",
            "assignee_id": "Assignee user account id.",
            "creator_id": "Creator user account id.",
            "parent_id": "Parent issue id for sub-tasks and epic children.",
            "created_at": "Issue creation timestamp.",
            "updated_at": "Last update timestamp.",
            "resolved_at": "Resolution timestamp.",
            "due_date": "Due date.",
            "environment": "Environment field.",
            "labels": "Issue labels.",
            "story_points": "Story points estimate.",
            "original_estimate_seconds": "Original time estimate in seconds.",
            "remaining_estimate_seconds": "Remaining estimate in seconds.",
            "time_spent_seconds": "Time spent in seconds.",
            "watch_count": "Number of watchers.",
            "vote_count": "Number of votes.",
        },
    },
    "issue_comment": {
        "comment": "Comments on issues.",
        "columns": {
            "id": "Comment id.",
            "issue_id": "Parent issue id.",
            "author_id": "Comment author account id.",
            "update_author_id": "Author of the last comment edit.",
            "body": "Comment body.",
            "created_at": "Comment creation timestamp.",
            "updated_at": "Comment last-updated timestamp.",
        },
    },
    "issue_type": {
        "comment": "Available issue types (Bug, Task, Story, Epic, …).",
        "columns": {
            "id": "Issue type id.",
            "name": "Issue type name.",
            "description": "Issue type description.",
            "icon_url": "Icon URL.",
            "is_subtask": "Whether this type represents sub-tasks.",
        },
    },
    "project": {
        "comment": "Jira projects.",
        "columns": {
            "id": "Project id.",
            "project_key": "Project key.",
            "name": "Project name.",
            "description": "Project description.",
            "project_category_id": "Foreign key to project_category.",
            "project_type_key": "Project type key.",
            "lead_id": "Project lead account id.",
            "url": "Project URL.",
            "style": "Project style (classic, next-gen).",
            "is_archived": "Whether the project is archived.",
        },
    },
    "project_category": {
        "comment": "Project categories.",
        "columns": {
            "id": "Category id.",
            "name": "Category name.",
            "description": "Category description.",
        },
    },
    "project_role": {
        "comment": "Available project roles.",
        "columns": {
            "id": "Role id.",
            "name": "Role name.",
            "description": "Role description.",
        },
    },
    "project_role_actor": {
        "comment": "User/group assignments to project roles.",
        "columns": {
            "project_id": "Project id.",
            "role_id": "Role id.",
            "actor_id": "Actor id (user or group).",
            "actor_type": "Actor type.",
            "actor_name": "Actor display name.",
        },
    },
    "user": {
        "comment": "Jira users.",
        "columns": {
            "account_id": "Atlassian account id.",
            "display_name": "Display name.",
            "email": "Email address.",
            "is_active": "Whether the user is active.",
            "account_type": "Account type.",
            "locale": "User locale.",
            "time_zone": "User time zone.",
        },
    },
    "status": {
        "comment": "Status lookup.",
        "columns": {
            "id": "Status id.",
            "name": "Status name.",
            "description": "Status description.",
            "status_category_id": "Foreign key to status_category.",
            "icon_url": "Icon URL.",
        },
    },
    "status_category": {
        "comment": "Status category lookup (To Do / In Progress / Done).",
        "columns": {
            "id": "Status category id.",
            "category_key": "Category key (new, indeterminate, done).",
            "name": "Category display name.",
            "color_name": "Display color name.",
        },
    },
    "priority": {
        "comment": "Priority lookup.",
        "columns": {
            "id": "Priority id.",
            "name": "Priority name.",
            "description": "Priority description.",
            "color": "Display color.",
            "icon_url": "Icon URL.",
        },
    },
    "resolution": {
        "comment": "Resolution lookup.",
        "columns": {
            "id": "Resolution id.",
            "name": "Resolution name.",
            "description": "Resolution description.",
        },
    },
    "field": {
        "comment": "Field metadata: name, type, custom flag.",
        "columns": {
            "id": "Field id.",
            "name": "Field display name.",
            "description": "Field description.",
            "is_custom": "Whether the field is custom.",
            "schema_type": "Field schema type (string, array, …).",
            "schema_items": "Array item type when schema_type is array.",
        },
    },
    "issue_field_history": {
        "comment": "Scalar field values per issue, with change history. One row per (issue_id, field_id, updated_at).",
        "columns": {
            "issue_id": "Issue id.",
            "field_id": "Jira field id.",
            "value": "Scalar field value.",
            "updated_at": "Timestamp when this value became current.",
            "is_current": "Whether this row is the current value for the field.",
        },
    },
    "issue_multiselect_history": {
        "comment": "Array-valued field values per issue. Multiple rows per (issue_id, field_id, updated_at).",
        "columns": {
            "issue_id": "Issue id.",
            "field_id": "Jira field id.",
            "value": "Array element value.",
            "updated_at": "Timestamp when this value became current.",
            "is_current": "Whether this row is the current value for the field.",
        },
    },
    "issue_worklog": {
        "comment": "Worklog entries per issue.",
        "columns": {
            "id": "Worklog id.",
            "issue_id": "Issue id.",
            "author_id": "Worklog author account id.",
            "time_spent_seconds": "Time logged in seconds.",
            "started_at": "Worklog start timestamp.",
            "created_at": "Worklog creation timestamp.",
            "updated_at": "Worklog update timestamp.",
            "comment": "Worklog comment text.",
        },
    },
    "issue_watcher": {
        "comment": "Watchers per issue.",
        "columns": {
            "issue_id": "Issue id.",
            "watcher_id": "Watcher account id.",
        },
    },
    "issue_link": {
        "comment": "Directed links between issues.",
        "columns": {
            "id": "Synthetic link id.",
            "source_issue_id": "Source issue id.",
            "target_issue_id": "Target issue id.",
            "link_type_id": "Foreign key to issue_link_type.",
        },
    },
    "issue_link_type": {
        "comment": "Deduped link type lookup (blocks, relates to, etc.).",
        "columns": {
            "id": "Link type id.",
            "name": "Link type name.",
            "inward_description": "Inward link description.",
            "outward_description": "Outward link description.",
        },
    },
    "sprint_issue": {
        "comment": "Many-to-many bridge between sprints and issues. Derived from issues.sprint_ids array.",
        "columns": {
            "sprint_id": "Sprint id.",
            "issue_id": "Issue id.",
        },
    },
    "epic_issue": {
        "comment": "Bridge linking child issues to their epic. Derived from issues.parent_id where parent type = Epic.",
        "columns": {
            "epic_id": "Epic issue id.",
            "issue_id": "Child issue id.",
        },
    },
    "component": {
        "comment": "Components (deduped from project_components).",
        "columns": {
            "id": "Component id.",
            "name": "Component name.",
            "description": "Component description.",
            "lead_id": "Component lead account id.",
            "project_id": "Owning project id.",
            "assignee_type": "Default assignee type for the component.",
        },
    },
    "issue_component": {
        "comment": "Bridge issue <-> component. Derived from issues.components array if present.",
        "columns": {
            "issue_id": "Issue id.",
            "component_id": "Component id.",
        },
    },
    "version": {
        "comment": "Versions (deduped from version table).",
        "columns": {
            "id": "Version id.",
            "name": "Version name.",
            "description": "Version description.",
            "is_archived": "Whether the version is archived.",
            "is_released": "Whether the version is released.",
            "release_date": "Release date.",
            "start_date": "Start date.",
        },
    },
    "project_version": {
        "comment": "Bridge project <-> version.",
        "columns": {
            "project_id": "Project id.",
            "version_id": "Version id.",
        },
    },
    "issue_version": {
        "comment": "Bridge issue <-> fix version. Derived from issues.fix_version_ids if present.",
        "columns": {
            "issue_id": "Issue id.",
            "version_id": "Fix version id.",
        },
    },
    "board": {
        "comment": "Agile boards.",
        "columns": {
            "id": "Board id.",
            "name": "Board name.",
            "board_type": "Board type (scrum, kanban).",
            "project_id": "Primary project id.",
            "filter_id": "Saved filter id backing the board.",
            "location_type": "Board location type.",
        },
    },
    "project_board": {
        "comment": "Project <-> board mapping.",
        "columns": {
            "project_id": "Project id.",
            "board_id": "Board id.",
        },
    },
    "sprint": {
        "comment": "Sprints.",
        "columns": {
            "id": "Sprint id.",
            "board_id": "Board id.",
            "name": "Sprint name.",
            "state": "Sprint state (future, active, closed).",
            "start_date": "Sprint start timestamp.",
            "end_date": "Sprint end timestamp.",
            "complete_date": "Sprint completion timestamp.",
            "goal": "Sprint goal.",
        },
    },
    "user_group": {
        "comment": "Bridge user <-> group.",
        "columns": {
            "account_id": "User account id.",
            "group_id": "Group id.",
            "group_name": "Group name.",
        },
    },
    "group": {
        "comment": "Deduped group lookup derived from user_group.",
        "columns": {
            "id": "Group id.",
            "name": "Group name.",
        },
    },
    "application_role": {
        "comment": "Application roles in Jira.",
        "columns": {
            "application_role_key": "Application role key.",
            "name": "Role name.",
            "description": "Role description.",
            "user_count": "Number of users in the role.",
            "group_count": "Number of groups in the role.",
        },
    },
    "permission_scheme": {
        "comment": "Permission schemes.",
        "columns": {
            "id": "Permission scheme id.",
            "name": "Scheme name.",
            "description": "Scheme description.",
        },
    },
    "security_scheme": {
        "comment": "Security schemes.",
        "columns": {
            "id": "Security scheme id.",
            "name": "Scheme name.",
            "description": "Scheme description.",
            "default_security_level_id": "Default security level id.",
        },
    },
    "security_level": {
        "comment": "Security levels within schemes.",
        "columns": {
            "id": "Security level id.",
            "name": "Security level name.",
            "description": "Security level description.",
            "security_scheme_id": "Parent security scheme id.",
        },
    },
    "project_permission": {
        "comment": "Project-level permission grants.",
        "columns": {
            "project_id": "Project id.",
            "permission": "Permission key.",
            "holder_type": "Grant holder type (user, group, …).",
            "holder_value": "Grant holder identifier.",
        },
    },
}
