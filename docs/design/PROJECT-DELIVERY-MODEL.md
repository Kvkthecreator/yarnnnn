# Project Delivery Model — Agents Produce, Projects Deliver

> **Status**: Decision captured, implementation pending
> **Date**: 2026-03-20
> **Authors**: KVK, Claude
> **Scope**: How outputs flow from agent production to user delivery
> **Related**: ADR-120 (project execution), ADR-122 (project registry), ADR-118 (skills/output gateway), FOUNDATIONS.md (Axiom 1, 6)

---

## Decision

**Agents produce. Projects deliver.**

All delivery configuration and execution moves from individual agents to the project level. Agents are workers that produce outputs into the project workspace. The PM coordinates when and how those outputs reach the user.

This supersedes the current "All Direct" delivery model (agent-framework.md) where every agent delivers independently (N+1 deliveries).

---

## Current State (being replaced)

- Each agent has its own `destination` field (email target, format)
- `delivery.py` delivers per-agent after each run
- PM assembles and delivers separately
- User receives N agent emails + 1 assembly email per cycle
- Platform digest agents (no PM) deliver directly

## Target State

- Agents write output to their workspace (`/agents/{slug}/outputs/{date}/`)
- Agent output is copied to project contributions (`/projects/{slug}/contributions/{agent_slug}/`)
- PM decides when to deliver based on contribution freshness and project cadence
- Delivery configuration lives on PROJECT.md (objective.format, delivery section)
- Single delivery per project per cycle (assembly for multi-agent, passthrough for single-agent)

---

## Design Principles

### 1. Project is the delivery unit

The user thinks in projects, not agents. "My Slack Recap" is a project. They don't care that internally a Slack Agent produced the content and a PM coordinated delivery. They care about receiving their recap.

### 2. PM for all projects — no exceptions

Every project gets a PM agent at scaffold time, including single-agent platform digests. PM is project infrastructure, not a user-facing worker. PM agents are excluded from tier agent limits.

**Why no exceptions**: Lifecycle considerations (when to add PM, Composer subjectivity about project maturity) create more complexity than universal PM. The PM for a single-agent project is lightweight — it coordinates delivery and will naturally take on more responsibility as the project gains contributors.

### 3. Single-agent projects are a special case, not a different architecture

A single-agent project (e.g., Slack Recap with one digest agent) is structurally identical to a multi-agent project. The PM's assembly step is a passthrough — one contribution in, one output out. But the architecture is the same:

```
Agent produces → contribution folder → PM assesses → PM delivers
```

This means when the project gains a second contributor (duty promotion, Composer addition), the delivery pipeline doesn't change. PM just has more inputs to coordinate.

### 4. Delivery cadence is a project setting

Two distinct scheduling concepts:

- **Agent schedule**: When does each worker run? (daily at 9am, every 6h)
- **Project delivery cadence**: When does the user receive output? (every Monday, daily, on-demand)

These are decoupled. A project might have 3 agents running daily but deliver a weekly assembled report. The PM respects the project delivery cadence as a constraint.

---

## Scheduling Model (ADR-126 Aligned)

Three distinct scheduling concerns, separated by ADR-126:

| Concern | Owner | Where it lives | What it means |
|---------|-------|---------------|--------------|
| **Pulse cadence** | Agent (scales with seniority) | `agents.next_pulse_at` | How often the agent senses its domain |
| **Generation decision** | Agent (via pulse) | Pulse Tier 1/2 | Whether the agent produces output this cycle |
| **Project delivery cadence** | PM + Project charter | `PROJECT.md ## Delivery` | When the user receives assembled output |

These are decoupled. An agent might pulse every 5 minutes (senior, always sensing), generate twice a week (when domain warrants it), while the project delivers weekly (PM assembles on Friday).

| Concept | Owner | Where it lives |
|---------|-------|---------------|
| Agent pulse rhythm | Agent maturity + mode | `agents.next_pulse_at` (replaces `next_run_at`) |
| Default pulse rhythm | Derived from `agents.schedule` | Training wheels for new agents |
| Project delivery cadence | Project charter | `PROJECT.md ## Delivery` |
| Assembly timing | PM coordination pulse | `memory/work_plan.md` |
| Delivery execution | PM + delivery service | PM triggers `deliver_from_output_folder()` |

---

## Impact on Existing Code

### Agent creation (`scaffold_project`)
- Member agents created with `destination=None` — no direct delivery
- ✅ Already implemented in registry v1.3

### Delivery service (`delivery.py`)
- Currently called per-agent-run in `agent_execution.py`
- Needs refactoring: agent runs write to workspace only, PM triggers delivery
- **Migration path**: Dual-write during transition (deliver per-agent AND to workspace), then cut over

### PM heartbeat
- Currently checks contribution freshness → triggers assembly
- Needs extension: also triggers delivery based on project cadence
- Single-agent projects: PM passthrough (contribution = output, deliver immediately)
- **ADR-128**: PM now reads contributor self-assessment histories (rolling, 5 recent) alongside freshness. Assembly gating considers both output recency AND contributor self-reported confidence. PM writes `project_assessment.md` each pulse — contributors read this to understand project constraints.

### Frontend
- Agent detail pages: remove delivery configuration
- Project settings: add delivery cadence configuration (daily/weekly/on-demand)
- Dashboard: show project delivery status, not per-agent delivery

---

## Open Questions (for further discourse)

1. **Standalone agents outside projects**: Do they still exist? If projects are the primary unit, is there a case for an agent that isn't part of any project? If not, all agents are project members by definition.

2. **User override on individual delivery**: Some users might want individual agent outputs in addition to the project assembly. Is this a per-project setting ("also send individual agent outputs") or per-agent opt-in?

3. **Delivery format per project**: The objective already includes `format` (email, pdf, etc.). Should delivery support multiple formats per project? (e.g., email summary + PDF attachment + Slack notification)

4. **Context tab design**: How should project context be surfaced? Raw filesystem vs. semantic grouping (sources, agent knowledge, PM intelligence). Parked for separate design discourse.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-20 | v1 — Decision captured: agents produce, projects deliver. PM for all projects. |
| 2026-03-21 | v1.1 — ADR-128: PM heartbeat now reads contributor self-assessments + writes project_assessment.md. Assembly gating considers contributor cognitive state. |
