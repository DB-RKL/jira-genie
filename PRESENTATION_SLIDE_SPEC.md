# Jira Analytics — Customer Presentation Slide Spec

12-slide deck · ~20 minutes · Customer-facing

Use this file as the source of truth for the Cursor Canvas deck and Google Slides export.

---

## Slide 1 — Title

**Layout:** `title`

**Title:** Turn Jira into Governed Analytics on Databricks

**Subtitle:** Automated delivery insights — from raw tickets to trusted KPIs in one afternoon

**Speaker notes (30 sec):**
Open with the tension: every engineering org runs on Jira, but leadership still exports CSVs to answer basic delivery questions. This accelerator changes that — it ingests Jira automatically, models trusted KPIs, and gives every stakeholder self-service access through dashboards and natural-language Q&A.

---

## Slide 2 — The Problem

**Layout:** `power_statement`

**Headline:** Your delivery data is in Jira. Your decisions are still in spreadsheets.

**Body bullets:**
- Leadership asks "Are we on track?" — and teams spend hours exporting, filtering, and reconciling numbers
- Every squad has a different Jira filter; steering committees debate whose metrics are right
- Bottlenecks surface in retros, not in real time — stale issues and sprint slippage go unnoticed until it's too late

**Speaker notes (60 sec):**
Name three pains your audience recognizes: manual reporting tax, conflicting KPIs across teams, and late risk detection. The cost isn't the data — Jira has it all. The cost is the friction between Jira and decision-making.

---

## Slide 3 — Who Feels This Pain

**Layout:** `content_3col_cards` (use 4 cards — 2x2 or extend layout)

**Title:** Every delivery stakeholder needs the same truth

| Persona | Pain | What they need |
|---------|------|----------------|
| Engineering Manager | Weekly delivery reviews built from scratch | Sprint health, carryover, aging blockers |
| PMO / Program Lead | Cross-project risk visibility | Portfolio KPIs, stale work, critical backlog |
| Team Lead | Retros based on anecdotes | Planned vs completed, velocity trends |
| Executive | One-page snapshot, not Jira fluency | Open issues, cycle time, throughput |

**Speaker notes (60 sec):**
Walk through each persona quickly. The point: they all need the same governed metrics, consumed differently. EM wants sprint detail; exec wants a portfolio snapshot; PMO wants cross-project comparison.

---

## Slide 4 — What You Get

**Layout:** `content_3col_cards`

**Title:** Four outcomes, one platform

1. **Portfolio health** — Open critical issues, stale work, throughput across projects
2. **Sprint predictability** — Planned vs completed points, velocity trends, carryover
3. **Bottleneck detection** — Time-in-status, transition delays, aging issues
4. **Team productivity** — Assignee load, resolution counts, worklog trends

**Speaker notes (45 sec):**
These aren't abstract analytics goals — each maps to a dashboard page and gold data mart you'll see in the next slides. One pipeline, four decision surfaces.

---

## Slide 5 — Portfolio Health

**Layout:** `content_basic`

**Title:** Portfolio health at a glance

**Headline stat:** One view across every project

**Bullets:**
- Open issues, open critical, and stale (>30 day) work per project
- Average cycle time and lead time by project
- Created vs resolved in the last 30 days — spot throughput imbalance early
- **Powered by:** `agg_project_health` → **Project Portfolio Health** dashboard page

**Speaker notes (60 sec):**
PMO and program leads live here. Instead of pulling five Jira filters before a steering meeting, they open one page: total open, projects with stale work, portfolio avg cycle time, resolved in 30 days. Drill into any project row for detail.

---

## Slide 6 — Sprint Predictability

**Layout:** `content_basic`

**Title:** Sprint predictability

**Headline stat:** Planned vs completed — every sprint, automatically

**Bullets:**
- Story points and issues: planned, completed, added mid-sprint
- Completion ratio and carryover for the last 12 closed sprints
- Active sprint snapshot with scope-change tracking
- **Powered by:** `fct_sprint_velocity` → **Sprint Velocity & Burndown** dashboard page

**Speaker notes (60 sec):**
Engineering managers use this for weekly reviews and retros. When carryover trends up across sprints, it's visible before sprint close — not as a surprise in the retro. Compare planned vs completed points quarter over quarter.

---

## Slide 7 — Bottleneck Detection

**Layout:** `content_basic`

**Title:** Bottleneck detection

**Headline stat:** Find where work stalls — before it becomes a miss

**Bullets:**
- Median and p90 time-in-status per project and status
- Full status transition history with duration in hours
- Aging open issues bucketed by age (0–7d, 7–14d, 14–30d, 30–90d, 90d+)
- **Powered by:** `agg_time_in_status`, `fct_issue_transitions` → **Cycle Time & Aging** dashboard page

**Speaker notes (60 sec):**
This is where process improvement gets evidence. "In Review takes too long" becomes a number — p50 and p90 hours per status. Pair with the oldest-open-issues table to assign follow-ups before exec reviews.

---

## Slide 8 — Team Productivity

**Layout:** `content_basic`

**Title:** Team productivity and load

**Headline stat:** Who is carrying the work — and who is closing it

**Bullets:**
- Open workload per assignee: issues, story points, priority, age bucket
- Resolution counts (30d / 90d) and average cycle time per person
- Worklog hours by contributor over rolling windows
- **Powered by:** `agg_assignee_load`, `agg_team_productivity`, `fct_worklog` → **Team Productivity** dashboard page

**Speaker notes (60 sec):**
Team leads use this to balance load and recognize contributors. Spot assignees with high open critical counts or disproportionate aging work. Worklog data adds a time-spent dimension beyond issue counts.

---

## Slide 9 — How It Works

**Layout:** `content_basic`

**Title:** How it works — medallion architecture on Databricks

**Flow:**
```
Jira Cloud
    → Lakeflow Connect (28 source tables)
    → Bronze (raw landing)
    → Silver DLT / Python (Fivetran-parity ERD)
    → Gold DLT / SQL (analytical marts)
    → Lakeview dashboard + Genie Q&A
```

**Bullets:**
- **Ingest:** Lakeflow Connect pulls issues, sprints, worklogs, projects, users, and status history
- **Transform:** Silver normalizes to a clean, reusable schema; gold builds KPI-ready marts
- **Consume:** Four-page dashboard + Genie natural-language Q&A on the same governed tables
- **Orchestrate:** One job chains bronze → silver → gold on demand or on schedule

**Speaker notes (90 sec):**
Keep this non-technical for business audiences; go deeper for platform teams. Key message: no custom connectors to maintain, no separate BI stack, everything governed in Unity Catalog. One job refresh gives deterministic end-to-end updates.

---

## Slide 10 — What Ships

**Layout:** `content_basic`

**Title:** What ships in the accelerator

| Component | What you get |
|-----------|-------------|
| Ingestion | 28 Jira source tables via Lakeflow Connect |
| Silver layer | Fivetran-parity normalized schema (issues, sprints, history, lookups) |
| Gold layer | 4 fact tables, 4 dimension tables, 4 aggregate marts |
| Dashboard | 4 pages, 35 widgets — Sprint, Cycle Time, Portfolio, Team |
| Genie space | Curated tables + glossary for natural-language Q&A |
| Orchestration | Single refresh job: ingest → silver → gold |

**Footnote (speaker notes only):** Pilot-ready today; production rollout adds parameterization, service principal auth, scheduling, and UC grants.

**Speaker notes (60 sec):**
This is an accelerator, not a blank canvas. Customers deploy the bundle, run one job, and get a working analytics platform. Mention briefly that production hardening (service principals, scheduling, multi-env) is a follow-on — don't oversell as turnkey enterprise prod.

---

## Slide 11 — Business Outcomes

**Layout:** `content_3col` (4 stats — use 2x2 grid in canvas)

**Title:** Expected business impact

| Metric | Target |
|--------|--------|
| Manual reporting effort | 20–40% reduction |
| Cycle-time diagnosis speed | 15–30% faster |
| Sprint predictability | 10–20% improvement (commit vs complete) |
| Source of truth | 1 governed metric layer for all stakeholders |

**Speaker notes (45 sec):**
Frame these as typical targets customers track, not guaranteed SLAs. The mechanism: eliminate CSV exports, surface bottlenecks before retros, and give every stakeholder the same numbers in dashboard and Genie.

---

## Slide 12 — Get Started

**Layout:** `content_basic` + `closing`

**Title:** Get started today

**Steps:**
1. **Connect** — Create Lakeflow Connect Jira connection in Catalog Explorer (OAuth)
2. **Deploy** — `databricks bundle deploy` with your catalog and warehouse
3. **Refresh** — `databricks bundle run jira_analytics_refresh`
4. **Explore** — Open the Lakeview dashboard; ask your first Genie question

**CTA:** Your delivery data is already in Jira. Put it to work.

**Example Genie questions to demo:**
- "Which projects have the most open critical issues?"
- "What was the velocity for the last 5 closed sprints?"
- "Show me the oldest open bugs and who they're assigned to"

**Speaker notes (60 sec):**
Close with the pilot path — under an hour to first insights. Offer to run a live demo: deploy, refresh, open dashboard, ask Genie. Leave audience with the CTA and offer Q&A.

---

## Google Slides `create-from-spec` JSON

```json
[
  {"layout": "title", "title": "Turn Jira into Governed Analytics on Databricks", "body": "Automated delivery insights — from raw tickets to trusted KPIs in one afternoon"},
  {"layout": "power_statement", "title": "Your delivery data is in Jira. Your decisions are still in spreadsheets."},
  {"layout": "content_basic", "title": "Every delivery stakeholder needs the same truth", "body": "Engineering Manager — sprint health, carryover, aging blockers\nPMO / Program Lead — portfolio KPIs, stale work, critical backlog\nTeam Lead — planned vs completed, velocity trends\nExecutive — open issues, cycle time, throughput"},
  {"layout": "content_basic", "title": "Four outcomes, one platform", "body": "Portfolio health — open critical, stale work, throughput\nSprint predictability — planned vs completed, velocity, carryover\nBottleneck detection — time-in-status, transition delays\nTeam productivity — assignee load, resolution counts, worklog"},
  {"layout": "content_basic", "title": "Portfolio health at a glance", "body": "Open issues, critical backlog, and stale work per project\nAvg cycle time and lead time by project\nCreated vs resolved in last 30 days\nDashboard: Project Portfolio Health"},
  {"layout": "content_basic", "title": "Sprint predictability", "body": "Planned vs completed points and issues every sprint\nCompletion ratio and carryover for last 12 closed sprints\nActive sprint snapshot with scope-change tracking\nDashboard: Sprint Velocity & Burndown"},
  {"layout": "content_basic", "title": "Bottleneck detection", "body": "Median and p90 time-in-status per project\nFull status transition history with duration\nAging open issues by age bucket\nDashboard: Cycle Time & Aging"},
  {"layout": "content_basic", "title": "Team productivity and load", "body": "Open workload per assignee by priority and age\nResolution counts and avg cycle time per person\nWorklog hours by contributor\nDashboard: Team Productivity"},
  {"layout": "content_basic", "title": "How it works", "body": "Jira Cloud → Lakeflow Connect → Bronze (28 tables)\n→ Silver DLT (Fivetran-parity ERD)\n→ Gold DLT (analytical marts)\n→ Lakeview dashboard + Genie Q&A\nOne job orchestrates end-to-end refresh"},
  {"layout": "content_basic", "title": "What ships in the accelerator", "body": "28 Jira source tables via Lakeflow Connect\nFivetran-parity silver + 12 gold marts\n4-page Lakeview dashboard (35 widgets)\nGenie space with curated glossary\nSingle orchestrated refresh job"},
  {"layout": "content_basic", "title": "Expected business impact", "body": "20–40% reduction in manual Jira reporting\n15–30% faster cycle-time diagnosis\n10–20% improvement in sprint predictability\nOne governed source of truth for all stakeholders"},
  {"layout": "content_basic", "title": "Get started today", "body": "1. Connect — Lakeflow Connect Jira in Catalog Explorer\n2. Deploy — databricks bundle deploy\n3. Refresh — databricks bundle run jira_analytics_refresh\n4. Explore — dashboard + first Genie question"},
  {"layout": "closing"}
]
```
