# Turn Jira into a Governed Analytics Platform on Databricks

*Your delivery data lives in Jira. Your decisions shouldn't live in spreadsheets.*

Engineering organizations run on Jira — sprints, backlogs, blockers, and release plans all pass through it. Yet when leadership asks "Are we on track?", "Where are we stuck?", or "Which teams are improving?", the answer usually involves exporting CSVs, stitching together Jira filters, and debating whose numbers are right.

Teams can change that today. Using Databricks Lakeflow Connect, Delta Live Tables, and AI/BI, you can stand up a **Jira analytics pilot in an afternoon** — automated ingestion, trusted KPIs, a ready-made dashboard, and natural-language Q&A through Genie. This post explains what customers can use right now, how it works, and what to expect on the path from pilot to production.

---

## What you can do today

The Jira Analytics accelerator delivers four outcomes that map directly to how delivery teams actually work:

### 1. Portfolio health at a glance

See open issues, critical backlog, stale work, and throughput across every project — without building a new report each week.

**Powered by:** `agg_project_health` (open issues, open critical, stale open, avg cycle/lead time, created vs resolved in last 30 days) and the **Project Portfolio Health** dashboard page (total open, projects with stale issues, portfolio avg cycle time, resolved in 30 days).

### 2. Sprint predictability

Compare planned vs completed story points, track velocity over closed sprints, and spot carryover before it becomes a pattern.

**Powered by:** `fct_sprint_velocity` (planned vs completed points and issues, completion ratio, scope changes) and the **Sprint Velocity & Burndown** page (active sprints, avg completion, points completed, carryover, sprint-level tables).

### 3. Bottleneck detection

Find where work stalls — median time in each status, aging open issues, and transition delays that slow delivery.

**Powered by:** `agg_time_in_status` (p50/p90 hours per status), `fct_issue_transitions` (status change history with duration), and the **Cycle Time & Aging** page (median cycle/lead time, open >30d, stale critical, time-in-status tables).

### 4. Team productivity and load

Understand who is carrying the most open work, who is resolving issues, and how cycle times vary by assignee.

**Powered by:** `agg_assignee_load`, `agg_team_productivity`, `fct_worklog`, and the **Team Productivity** page (active contributors, top resolvers, avg open load, per-assignee resolution counts).

---

## How it works

The architecture follows a familiar medallion pattern, fully managed on Databricks:

```
Jira Cloud  →  Lakeflow Connect  →  bronze (28 tables)
                                        │
                                        ▼  DLT (Python)
                                   silver (Fivetran-parity ERD)
                                        │
                                        ▼  DLT (SQL)
                                   gold (analytical marts)
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
           Lakeview dashboard    Genie space         Your apps / notebooks
           (4 pages, 35 widgets)  (natural language)
```

**Bronze** — Lakeflow Connect ingests 28 Jira source tables (issues, sprints, worklogs, projects, users, status history, and more) into Unity Catalog.

**Silver** — Delta Live Tables transform raw API data into a normalized, Fivetran-parity schema. Issue history, sprint relationships, and lookup tables are cleaned, typed, and deduplicated.

**Gold** — SQL materialized views build business-ready marts:

| Table | What it answers |
|-------|-----------------|
| `fct_issue` | One row per issue with cycle time, lead time, age buckets, and dimension joins |
| `fct_sprint_velocity` | Planned vs completed by sprint, with completion ratios |
| `fct_issue_transitions` | Every status change with duration in hours |
| `fct_worklog` | Time logged per issue, author, and project |
| `dim_user`, `dim_project`, `dim_status`, `dim_sprint` | Shared dimensions for filtering |
| `agg_project_health` | Per-project KPIs for portfolio views |
| `agg_assignee_load` | Open workload by assignee, priority, and age |
| `agg_team_productivity` | Resolution counts and cycle times by person |
| `agg_time_in_status` | Median and p90 dwell time per status |

**Consumption** — A four-page Lakeview dashboard ships with the bundle. A Genie space (provisioned via script) lets anyone ask questions in plain English over the same governed tables.

A single Databricks job orchestrates the full refresh: ingestion → silver → gold. Run it on demand or on a schedule once you are ready for production.

---

## A day in the life: four personas

### Engineering Manager — weekly delivery review

Monday morning, you open the **Sprint Velocity & Burndown** page. You filter to your team's project and scan completion ratios for the last 12 closed sprints. Carryover points are trending up — a signal to discuss scope discipline in standup, not a surprise at sprint close.

You switch to **Cycle Time & Aging** and check the table of oldest open issues. Two critical bugs have been in "In Review" for over two weeks. You assign follow-ups before the exec review on Thursday.

### PMO — cross-project risk triage

You need a portfolio view, not a single-team snapshot. On **Project Portfolio Health**, you compare open critical issues and stale (>30 day) open work across projects. One program shows rising created-vs-resolved imbalance — you flag it for the program lead.

In Genie, you ask: *"Which projects have the most open critical issues?"* The answer comes from `agg_project_health`, the same table the dashboard uses. No conflicting numbers in the steering committee deck.

### Team Lead — sprint retrospective with evidence

Retros should be data-informed, not anecdotal. You pull up `fct_sprint_velocity` for the sprint that just closed: planned points, completed points, issues added mid-sprint. The team sees exactly where commitment broke down.

You ask Genie: *"Compare planned vs completed story points for closed sprints this quarter."* The conversation shifts from "we always underestimate" to "we added 40% scope after day three in two of four sprints."

### Executive — one-page portfolio snapshot

You do not need Jira fluency. The **Project Portfolio Health** page gives you four numbers: total open issues, projects with stale work, portfolio average cycle time, and issues resolved in the last 30 days. Drill into any project table row for detail, or ask Genie: *"How is cycle time trending month over month?"*

---

## Getting started: pilot in 30–60 minutes

You need a Databricks workspace with Unity Catalog, a SQL warehouse, and a Jira Cloud instance.

**1. Create the Jira connection**

In Catalog Explorer, create a Lakeflow Connect connection to Jira (OAuth user-to-machine). Authorize with your Atlassian account.

**2. Create a catalog**

```sql
CREATE CATALOG IF NOT EXISTS jira_analytics;
```

**3. Deploy the asset bundle**

Clone the Jira Analytics repository and deploy with Databricks Asset Bundles, pointing variables at your catalog, warehouse, and connection name:

```bash
databricks bundle deploy -t <your-target> -p <your-profile>
```

This provisions bronze/silver/gold schemas, three pipelines (ingestion, silver DLT, gold DLT), an orchestration job, and the Lakeview dashboard.

**4. Run the first refresh**

```bash
databricks bundle run jira_analytics_refresh -t <your-target> -p <your-profile>
```

The job chains bronze ingestion → silver transformation → gold modeling. First run may take longer while Lakeflow Connect performs a full sync.

**5. Open the dashboard**

Navigate to **AI/BI → Dashboards** and open **Jira Analytics**. Four pages are ready: Sprint Velocity, Cycle Time & Aging, Project Portfolio Health, and Team Productivity.

**6. (Optional) Set up Genie**

Create a Genie space with the gold and silver tables, plus curated instructions so Genie understands Jira terminology (cycle time, velocity, status categories). A provisioning script is included in the repository.

---

## Questions you can ask Genie today

Once the gold pipeline has run, stakeholders can self-serve without writing SQL:

- *"What was the velocity (points_completed) for the last 5 closed sprints?"*
- *"Which 10 assignees resolved the most issues in the last 30 days?"*
- *"How is cycle time trending month over month for project ENG?"*
- *"Which projects have the most open critical issues?"*
- *"Show me the oldest open bugs and who they're assigned to"*
- *"What's the average time in 'In Review' status across all projects?"*
- *"Compare planned vs completed story points for closed sprints this quarter"*
- *"Which sprints had the worst completion ratio?"*
- *"Top 10 contributors by total worklog hours last 90 days"*
- *"Distribution of resolution types across all closed issues"*

Genie queries the same governed gold tables the dashboard uses — one source of truth for every stakeholder.

---

## What to expect (honest limitations)

This accelerator is **available today as a pilot template**, not a fully hardened production service out of the box. Plan accordingly:

| Area | Current state | What it means for you |
|------|--------------|----------------------|
| Connector channel | Lakeflow Connect for Jira is on the preview channel | Expect API and schema evolution; validate after first sync |
| Jira auth | OAuth user-to-machine connection | Works for pilots; production should move to a service principal or dedicated service account |
| Data coverage | 28 of ~30 Fivetran-parity tables | Audit logs, field options, Jira dashboards/filters, and workflow definitions are not available from the connector |
| Schema assumptions | Silver code assumes Jira REST API column names | Run `DESCRIBE` on bronze tables after first ingestion and adjust mappings if needed |
| Genie provisioning | Manual script (not yet a first-class DAB resource) | One-time setup; API endpoints may change |
| Scheduling | Job schedule ships paused | Enable and tune cadence when you move beyond pilot |
| Parameterization | Catalog and owner values need customization per deployment | Replace defaults with your catalog name, service principal, and workspace target |

None of these block a successful pilot. They define the work between "working demo" and "production rollout."

---

## Is it production-ready?

**As shipped: no — it is a strong MVP you can pilot today.**

**What is already solid:**

- Complete end-to-end pipeline (ingest → model → consume)
- 28-table bronze ingestion, Fivetran-parity silver, seven gold marts with four aggregate tables
- Orchestrated refresh job with failure notifications
- Four-page Lakeview dashboard with 35 widgets
- Genie space with curated glossary and example questions
- Basic data quality checks on silver tables (null ID drops, uniqueness expectations)

**What production requires:**

1. **Parameterize** — Replace hardcoded catalog, owner, and workspace values with bundle variables for each environment.
2. **Add a production target** — Separate `prod` bundle target with `mode: production`, service principal `run_as`, and Unity Catalog grants for consumer groups.
3. **Mature the pipelines** — Move off preview channel and development mode once validated in your environment.
4. **Enable operations** — Turn on the refresh schedule, add data freshness monitoring, and wire alerts to your on-call channel.
5. **Validate schema** — Compare bronze column names against silver expectations after first sync; add regression checks.
6. **Document governance** — Define RPO/RTO, connector limitations, and which KPIs are official vs exploratory.

Teams that complete this checklist turn the accelerator into a governed analytics platform their whole organization can trust.

---

## The business value

Organizations running this pilot typically target:

- **20–40% reduction** in manual Jira reporting effort (no more CSV exports and filter gymnastics)
- **15–30% faster** cycle-time diagnosis (bottlenecks visible in `agg_time_in_status` instead of discovered in retros)
- **10–20% improvement** in sprint predictability (planned vs completed tracked in `fct_sprint_velocity` every sprint)
- **One source of truth** for issue flow, throughput, and worklog analytics across dashboard, Genie, and downstream apps

The shift is from "Jira is where we track work" to "Jira is where we **improve** how we work."

---

## Get started

1. **Deploy** the Jira Analytics bundle to your Databricks workspace.
2. **Run** the end-to-end refresh job and confirm gold tables are populated.
3. **Open** the Lakeview dashboard and walk through all four pages with your team.
4. **Ask** your first Genie question and compare the answer to what you already know.
5. **Decide** which KPIs become part of your operating rhythm — weekly reviews, sprint retros, portfolio steering.

Your delivery data is already in Jira. It is time to put it to work.
