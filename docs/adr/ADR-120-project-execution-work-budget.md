# ADR-120: Project Execution & Work Budget

> **Status**: Proposed
> **Date**: 2026-03-18
> **Authors**: KVK, Claude
> **Extends**: ADR-119 (Workspace Filesystem), ADR-111 (Agent Composer), ADR-118 (Skills)
> **Implements**: FOUNDATIONS.md v3 (PM as domain-cognitive agent, work-is-bounded principle)
> **Related**: ADR-117 (Feedback Substrate — intentions), ADR-116 (Inter-Agent Knowledge), ADR-100 (Monetization)

---

## Context

ADR-119 Phase 2 built the folder structure for projects — `/projects/{slug}/`, PROJECT.md, contribution subfolders, assembly folders. ADR-118 built the skill library — 8 skills that produce binary deliverables. But project folders are dead without an execution engine.

**The problem**: A project with 3 contributing agents and an assembly spec is a static coordination contract. Nothing drives the work forward. No mechanism detects "Analyst contributed fresh data → Writer should draft → all contributions ready → assemble into PPTX." Without this engine, projects require manual orchestration — the user must tell TP when to trigger each step. This violates Axiom 6 (autonomy is the product direction).

**The employee analogy**: You've hired employees and given them a project brief. But there's no project manager running standups, no way for one employee to signal "I'm done, the next person can start," no mechanism for "all pieces are in, assemble the deliverable." The employees sit at their desks with instructions but no workflow connecting them.

**The bloat concern**: TP (the Thinking Partner) is already conversational + compositional + supervisory + orchestrative. Adding project-level heuristics (contribution freshness, assembly timing, per-project budgets) would make TP a monolith. Project execution is a separable domain of expertise.

**The budget concern**: Today's constraints (2/10 agents, 50/∞ messages, 10/100 renders) don't capture total autonomous compute. A project with 4 agents running daily + weekly assembly = 35 autonomous actions/week. Without a governor, Pro users could hit 900+ autonomous runs/month. The system needs a mechanism that bounds total autonomous work.

## Decision

### 1. Project Manager as Domain-Cognitive Agent

A PM is a regular agent whose domain is **project coordination**. It is not a third layer of intelligence — it sits alongside other agents in the two-layer model (FOUNDATIONS.md Axiom 1).

```
TP (meta-cognitive, singular)
  ├── PM Agent "q2-review-pm" (domain: Q2 review project coordination)
  ├── Analyst Agent "revenue-analyst" (domain: revenue data)
  ├── Writer Agent "exec-writer" (domain: executive narrative)
  └── Digest Agent "slack-recap" (domain: slack activity, standalone)
```

**What makes PM special** (domain-specific, not structurally special):
- Its workspace IS the project folder (`/projects/{slug}/`)
- It has orchestration primitives: `CheckContributorFreshness`, `TriggerAssembly`, `RequestContributorAdvance`
- It runs a project heartbeat (check project health) rather than a production cycle (generate output)
- It communicates upward to TP (status reports, escalation) and tracks contributors' outputs

**What PM does NOT do** (TP's job):
- Create or dissolve agents — PM requests TP via escalation
- Create or dissolve projects — Composer decides this
- Manage agents outside its project — PM only sees its contributors

**PM lifecycle follows Axiom 3** — a PM accumulates project knowledge: which contributors are reliable, what assembly cadence works, how the user structures feedback. A nascent PM follows the assembly spec literally. A mature PM adapts timing, suggests contributor changes, and refines assembly format based on feedback history.

### 2. Composer / PM Separation of Concerns

The Composer decides **whether** a project should exist. The PM decides **how** it executes.

**Composer keeps** (existing + extended):
- Create/dissolve projects (calls `CreateProject` primitive, scaffolds PM agent)
- Create/dissolve agents (existing)
- Detect project opportunities ("these agents' outputs should combine")
- Set project intent and initial contributors
- Monitor project health at system level (reads PM status, not re-derives)

**PM takes over** (new):
- Contribution freshness monitoring (which contributors have new outputs since last assembly?)
- Assembly readiness evaluation (are all required contributions fresh? is budget available?)
- Assembly execution (invoke skills to compose contributions into deliverable)
- Project work budget enforcement (am I within my allocated work units?)
- Escalation to TP when stuck (contributor stale for 7+ days, budget exhausted, assembly failed)

### 3. Project Heartbeat

The heartbeat pattern recurses — same cheap-first design as the system heartbeat, but at project scope.

**System heartbeat (TP/Composer)** — unchanged cadence:
- Agent health (existing)
- Project health (new — thin: read PM status from project folder, not re-derive)
- Coverage gaps (existing)
- Composition opportunities (existing)
- Work budget status (new — total units consumed this period)

**Project heartbeat (PM agent)** — triggered per-project:
- **When**: After any contributor produces output, or on PM's own schedule (configurable cadence)
- **What it checks**:
  1. Contributor freshness: which agents have new outputs since last assembly?
  2. Assembly readiness: do all required contributors have fresh contributions?
  3. Budget check: does this project have work units remaining for an assembly?
  4. Staleness: has a required contributor not produced in N days? → escalate to TP
- **Cost model**: PM heartbeat is pure DB/workspace reads (zero LLM) unless assembly or escalation is warranted. Follows the same cheap-first pattern as Composer.

**Trigger mechanism**: When a contributing agent's run completes and writes to `/projects/{slug}/contributions/{agent-slug}/`, the system fires `maybe_trigger_project_heartbeat(project_slug)` — analogous to `maybe_trigger_heartbeat()` for the system-level Composer. Debounced to prevent thrashing.

### 4. PM Execution Flow

```
1. PM heartbeat fires (contributor produced, or PM schedule)
2. Read PROJECT.md for intent, contributors, assembly spec
3. Check each contributor's latest output date vs. last assembly date
4. If all required contributors fresh AND budget available:
     → Execute assembly:
       a. Read all contributions from /projects/{slug}/contributions/
       b. Compose via LLM (PM's own generation — like any agent run)
       c. Invoke RuntimeDispatch for binary rendering (PPTX, PDF, etc.)
       d. Write to /projects/{slug}/assembly/{date}/ with manifest.json
       e. Deliver via destination in PROJECT.md
       f. Debit work units (1 for assembly + 1 per render)
5. If some contributors stale:
     → RequestContributorAdvance (ask TP to advance the agent's schedule)
     → Or wait, if within acceptable staleness window
6. If budget exhausted:
     → Write status to project folder, escalate to TP
7. Update PM status in /projects/{slug}/status.json
```

### 5. PM Primitives

Available to PM agents during their headless execution:

| Primitive | What | Modes |
|-----------|------|-------|
| `CheckContributorFreshness` | Read contributors' latest output dates, compare to last assembly | headless |
| `TriggerAssembly` | Execute assembly: compose contributions, render, deliver | headless |
| `RequestContributorAdvance` | Ask TP to advance a specific agent's next_run_at | headless |
| `ReadProjectStatus` | Read project health metrics (freshness, budget, assembly history) | chat, headless |
| `UpdateProjectIntent` | Refine PROJECT.md intent, assembly spec, or delivery preferences | headless |

Plus existing primitives: `ReadWorkspace`, `WriteWorkspace`, `SearchWorkspace`, `QueryKnowledge`, `RuntimeDispatch`.

### 6. Work Budget

**The governor**: Autonomous work units bound total system activity per user per billing period.

**What costs work units:**

| Action | Units | Rationale |
|--------|-------|-----------|
| Agent run (headless generation) | 1 | One LLM call + delivery |
| Project assembly | 2 | LLM composition + coordination overhead |
| Skill render (RuntimeDispatch) | 1 | Compute on output gateway |
| PM heartbeat (LLM path) | 1 | When PM needs LLM reasoning, not just DB checks |
| PM heartbeat (cheap path) | 0 | Pure DB/workspace reads — free |
| TP message (chat) | 0 | Covered by existing message limit |

**Tier allocation** (internal governor — pricing model deferred):

| Tier | Work Units / Month | Approx. Capacity |
|------|-------------------|------------------|
| Free | 60 | ~2 agents daily, no projects |
| Pro | 1000 | ~10 agents daily + 2-3 active projects |

**Enforcement points:**
- `unified_scheduler.py`: Before dispatching agent run, check remaining units
- PM heartbeat: Before triggering assembly, check project + global budget
- `RuntimeDispatch`: Before invoking render service, check remaining units
- Graceful degradation: When budget is low, PM reduces assembly frequency; when exhausted, PM pauses and escalates to TP

**Per-project allocation** (optional, user-configurable):
- User can set per-project budget caps via TP conversation or project settings
- PM respects project-level cap even if global budget has remaining units
- Default: no per-project cap (global budget applies)

**Tracking**: New `work_units` table or column on `activity_log` recording units consumed per action, with rollup queries for budget checking.

### 7. Intent Decomposition

The PM's core cognitive task: **translate user intent into executable, bounded work.**

User intent arrives as flat data in PROJECT.md:
```yaml
Intent:
  Deliverable: Q2 Business Review
  Audience: Leadership team
  Format: pptx
  Purpose: Quarterly performance review

Delivery:
  Channel: email
  Target: ceo@example.com
```

PM decomposes this into a work plan:
1. Which agents contribute? (revenue-analyst: data, exec-writer: narrative)
2. Which skills produce output? (spreadsheet for data, presentation for deck)
3. What cadence? (contributors run weekly, assembly biweekly)
4. What budget? (est. 8 units/cycle: 2 agent runs + 1 assembly + 1 render + buffer)
5. What assembly format? (combine analyst data as slides 2-5, writer narrative as executive summary slide 1 + speaker notes)

The work plan lives in the project folder as `work-plan.md` — it's the PM's operational document, analogous to an agent's `thesis.md`. It evolves as the PM learns from feedback.

### 8. Project-Level Intentions

Projects have intentions with the same structure as agent intentions (Axiom 3):

- **Recurring**: "Produce Q2 review deck every 2 weeks" — periodic assembly
- **Goal**: "Produce year-end analysis by December 15" — bounded, completes when delivered
- **Reactive**: "Alert me when revenue drops >10% QoQ" — event-triggered assembly

Each intention carries:
- **Trigger**: schedule, condition, or event
- **Output format**: which skills to invoke (pptx, pdf, chart, etc.)
- **Delivery**: channel and target per intention (same project might email the deck weekly but Slack the alert immediately)
- **Budget allocation**: how many work units this intention can consume per cycle

Multiple intentions per project are valid. A "Q2 Review" project might have:
- Recurring: biweekly deck assembly (pptx → email)
- Reactive: alert on revenue anomaly (chart → slack)
- Goal: produce final Q2 board deck by July 1

The PM manages all active intentions, scheduling and budgeting across them.

## Implementation Phases

### Phase 1: PM Agent & Project Heartbeat
- PM agent creation via Composer (extends `CreateProject` to also create PM agent)
- PM execution strategy (new strategy in `agent_pipeline.py`)
- Project heartbeat trigger (`maybe_trigger_project_heartbeat()`)
- `CheckContributorFreshness` and `ReadProjectStatus` primitives
- PM status file (`/projects/{slug}/status.json`)

### Phase 2: Assembly Execution
- `TriggerAssembly` primitive (compose contributions → LLM → RuntimeDispatch → deliver)
- Assembly manifest in `/projects/{slug}/assembly/{date}/manifest.json`
- Delivery from assembly folder (extends `deliver_from_output_folder()`)
- `RequestContributorAdvance` primitive

### Phase 3: Work Budget Governor
- `work_units` tracking (table or activity_log extension)
- Budget checking in scheduler, PM heartbeat, and RuntimeDispatch
- Tier allocation (Free: 60, Pro: 1000)
- Graceful degradation (PM reduces frequency → pauses → escalates)
- Budget status in system heartbeat data

### Phase 4: Intent Decomposition & Project Intentions
- PM work plan generation (`work-plan.md`)
- Multi-intention support in PROJECT.md
- Per-intention trigger, output format, delivery, budget allocation
- `UpdateProjectIntent` primitive

### Phase 5: Composer v2.0
- Composer prompt updated with project awareness, skill library (8 skills), PM delegation
- System heartbeat extended with project health signals (reads PM status)
- Composition opportunity detection (cross-agent output patterns → suggest project)
- Deferred: pricing model migration (credits vs. subscription)

## Resolved Decisions

1. **PM is an agent, not a new entity type.** Uses the same `agents` table, same workspace abstraction, same lifecycle model. Its `role` is `coordinator` (or new `pm` role). Its workspace root is the project folder.

2. **Two layers, not three.** PM is domain-cognitive (Axiom 1). Its domain is project coordination. TP monitors PMs exactly as it monitors any agent. PM doesn't manage agents — it manages contributions to its project.

3. **Work budget is an internal governor first.** Pricing model migration (credits, pay-per-unit) is deferred until the mechanism is validated in production. Initial implementation uses tier-based allocation with the same Free/Pro tiers.

4. **Heartbeat recurses, not monoliths.** System heartbeat stays lean (reads PM status). Project heartbeat runs independently per PM. Same cheap-first pattern: DB reads → gate → LLM only when warranted.

5. **Assembly is change-driven, not time-driven.** PM assembles when contributions are fresh, not on a fixed cron. The PM's schedule is for health checks; assembly timing is emergent from contributor output patterns.

6. **Agents are the write path.** Users don't directly manipulate project folders. Intent changes go through TP → PM → workspace writes. Feedback on outputs flows through the distillation pipeline. Frontend is read-only on workspace (Derived Principle 3).

## Files (Planned)

| Action | File | What |
|--------|------|------|
| Modify | `api/services/composer.py` | Composer v2.0: project awareness, PM creation, project health in heartbeat |
| Modify | `api/services/workspace.py` | PM workspace conventions, project status file |
| Create | `api/services/primitives/project_execution.py` | PM-specific primitives |
| Modify | `api/services/primitives/registry.py` | Register PM primitives |
| Modify | `api/services/agent_pipeline.py` | PM execution strategy |
| Modify | `api/services/agent_execution.py` | Project heartbeat trigger |
| Modify | `api/jobs/unified_scheduler.py` | Work budget check before dispatch |
| Modify | `api/services/platform_limits.py` | Work unit tracking + budget enforcement |
| Modify | `api/services/delivery.py` | Deliver from assembly folder |
| Create | `supabase/migrations/XXX_work_units.sql` | Work units tracking |
| Modify | `docs/architecture/FOUNDATIONS.md` | v3 updates (done) |

## What This Supersedes

- ADR-114 Phase 4 (Composer Prompt v2.0) → absorbed into Phase 5 of this ADR
- ADR-119 Phase 4 (frontend) → remains separate, downstream of this
- ADR-117 Phase 3 (intentions) → partially addressed here (project-level intentions), agent-level intentions remain in ADR-117

## Relationship to Pricing

The work budget model establishes the **mechanism** for usage-based pricing without committing to a specific pricing model. The tier allocations (60 free / 1000 pro) are internal governors.

Future pricing options enabled by this architecture:
- **Credits**: Users buy work unit packs (100 for $X, 500 for $Y)
- **Tiered subscription with overages**: Pro includes 1000 units, $0.01/unit beyond
- **Project-based pricing**: Per-active-project monthly fee that includes N work units

The pricing model decision is deferred until:
1. Work budget mechanism is implemented and validated
2. Real usage patterns establish unit costs
3. Product/business alignment on pricing strategy
