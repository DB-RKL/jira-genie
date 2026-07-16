# Jira Analytics — Slide Content (12 slides)

Customer-facing · ~20 minutes · Databricks

---

## Slide 1 — Title

**Turn Jira into Governed Analytics on Databricks**

Automated delivery insights — from raw tickets to trusted KPIs in one afternoon

---

## Slide 2 — The Problem

**Your delivery data is in Jira. Your decisions are still in spreadsheets.**

- Leadership asks "Are we on track?" — teams spend hours exporting, filtering, and reconciling numbers
- Every squad has a different Jira filter; steering committees debate whose metrics are right
- Bottlenecks surface in retros, not in real time — stale issues and sprint slippage go unnoticed

---

## Slide 3 — Who Feels This Pain

**Every delivery stakeholder needs the same truth**

| Persona | Pain | What they need |
|---------|------|----------------|
| Engineering Manager | Weekly delivery reviews built from scratch | Sprint health, carryover, aging blockers |
| PMO / Program Lead | Cross-project risk visibility | Portfolio KPIs, stale work, critical backlog |
| Team Lead | Retros based on anecdotes | Planned vs completed, velocity trends |
| Executive | One-page snapshot, not Jira fluency | Open issues, cycle time, throughput |

---

## Slide 4 — What You Get

**Four outcomes, one platform**

1. **Portfolio health** — Open critical issues, stale work, throughput across projects
2. **Sprint predictability** — Planned vs completed points, velocity trends, carryover
3. **Bottleneck detection** — Time-in-status, transition delays, aging issues
4. **Team productivity** — Assignee load, resolution counts, worklog trends

---

## Slide 5 — Portfolio Health

**Portfolio health at a glance**

**Headline:** One view across every project

- Open issues, open critical, and stale (>30 day) work per project
- Average cycle time and lead time by project
- Created vs resolved in the last 30 days — spot throughput imbalance early

*Dashboard: Project Portfolio Health*

---

## Slide 6 — Sprint Predictability

**Sprint predictability**

**Headline:** Planned vs completed — every sprint, automatically

- Story points and issues: planned, completed, added mid-sprint
- Completion ratio and carryover for the last 12 closed sprints
- Active sprint snapshot with scope-change tracking

*Dashboard: Sprint Velocity & Burndown*

---

## Slide 7 — Bottleneck Detection

**Bottleneck detection**

**Headline:** Find where work stalls — before it becomes a miss

- Median and p90 time-in-status per project and status
- Full status transition history with duration in hours
- Aging open issues bucketed by age (0–7d, 7–14d, 14–30d, 30–90d, 90d+)

*Dashboard: Cycle Time & Aging*

---

## Slide 8 — Team Productivity

**Team productivity and load**

**Headline:** Who is carrying the work — and who is closing it

- Open workload per assignee: issues, story points, priority, age bucket
- Resolution counts (30d / 90d) and average cycle time per person
- Worklog hours by contributor over rolling windows

*Dashboard: Team Productivity*

---

## Slide 9 — How It Works

**How it works — medallion architecture on Databricks**

```
Jira Cloud
  → Lakeflow Connect (28 source tables)
  → Bronze (raw landing)
  → Silver DLT (Fivetran-parity ERD)
  → Gold DLT (analytical marts)
  → Lakeview dashboard + Genie Q&A
```

- **Ingest:** Lakeflow Connect pulls issues, sprints, worklogs, projects, users, status history
- **Transform:** Silver normalizes; gold builds KPI-ready marts
- **Consume:** Four-page dashboard + Genie natural-language Q&A on governed tables
- **Orchestrate:** One job chains bronze → silver → gold on demand or on schedule

---

## Slide 10 — What Ships

**What ships in the accelerator**

| Component | What you get |
|-----------|-------------|
| Ingestion | 28 Jira source tables via Lakeflow Connect |
| Silver layer | Fivetran-parity normalized schema |
| Gold layer | 4 facts, 4 dims, 4 aggregate marts |
| Dashboard | 4 pages, 35 widgets |
| Genie space | Curated tables + glossary for NL Q&A |
| Orchestration | Single refresh job: ingest → silver → gold |

*Pilot-ready today; production adds parameterization, service principal auth, and scheduling.*

---

## Slide 11 — Business Outcomes

**Expected business impact**

| Metric | Target |
|--------|--------|
| Manual reporting effort | 20–40% reduction |
| Cycle-time diagnosis speed | 15–30% faster |
| Sprint predictability | 10–20% improvement |
| Source of truth | 1 governed metric layer for all stakeholders |

---

## Slide 12 — Get Started

**Get started today**

1. **Connect** — Create Lakeflow Connect Jira connection in Catalog Explorer
2. **Deploy** — `databricks bundle deploy` with your catalog and warehouse
3. **Refresh** — `databricks bundle run jira_analytics_refresh`
4. **Explore** — Open the Lakeview dashboard; ask your first Genie question

**Your delivery data is already in Jira. Put it to work.**

Example Genie questions:
- "Which projects have the most open critical issues?"
- "What was the velocity for the last 5 closed sprints?"
- "Show me the oldest open bugs and who they're assigned to"
