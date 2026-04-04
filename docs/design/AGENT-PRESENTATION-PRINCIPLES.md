# Agent Presentation Principles

**Date:** 2026-04-04 (v2 — agents as primary surface)
**Status:** Active
**Supersedes:** v1 (2026-03-13, agent as reference surface)
**Related:**
- [Surface Architecture](SURFACE-ARCHITECTURE.md) v3 — agents page is HOME
- [Surface-Action Mapping](SURFACE-ACTION-MAPPING.md) — directive vs configuration surfaces
- [ADR-140](../adr/ADR-140-agent-workforce-model.md) — workforce model (3 classes, pre-scaffolded roster)
- [ADR-138](../adr/ADR-138-agents-as-work-units.md) — agents as work units (tasks are WHAT, agents are WHO)

---

## Core Insight (Updated)

The backend has three agent classes: domain-steward, synthesizer, platform-bot. The frontend must answer: **how does a user supervise their team?**

Users think:
- "What does my competitive intelligence agent know?" — **domain-first**
- "What did my exec summary agent produce this week?" — **output-first**
- "Is my Slack bot up to date?" — **platform-first**

The answer depends on the agent class. Domain stewards are defined by their accumulated knowledge. Synthesizers are defined by their deliverables. Bots are defined by their platform connection. The agents page dispatches to the right view for each class.

---

## Principle 1: Agent Class Determines View

**The agent's class determines what the user sees when selecting it.** Not a uniform card or detail page — each class gets the view that matches its output shape.

| Agent Class | Primary View | What Defines It |
|---|---|---|
| **Domain steward** | Directory explorer (context domain tree) | Accumulated knowledge in their owned domain |
| **Synthesizer** | Deliverable viewer (latest output + history) | Reports and cross-domain compositions |
| **Platform bot** | Temporal observations (daily logs) | Platform connection + observation stream |

This replaces the v1 approach of a uniform agent identity page. The agent's AGENT.md and memory files are still accessible but secondary — the primary view is the agent's *work product*.

---

## Principle 2: Agents Are Stable, Tasks Come and Go

**The left panel roster is stable — 8 agents, always visible.** Tasks appear as expandable children under each agent.

This is the key UX difference from the task-centric model:
- Tasks page: flat list of 5-15 transient items, no grouping
- Agents page: stable roster of 8 entities, each with 0-3 task responsibilities

Users build a relationship with their agents over time. "My competitive intelligence agent" is a persistent mental anchor. "track-competitors" is a task slug they'll forget.

### Roster layout

Three sections matching agent classes:

```
DOMAIN STEWARDS
● Competitive Intelligence (2 tasks)
● Market Research (1 task)
● Business Development (0 tasks)
● Operations (1 task)
● Marketing & Creative (0 tasks)

SYNTHESIZERS
● Executive Reporting (2 tasks)

PLATFORM BOTS
● Slack Bot (1 task)
● Notion Bot (0 tasks)
```

Agents without tasks are visible but muted (gray dot). This communicates "ready to work" rather than hiding them.

---

## Principle 3: Tasks Are Responsibilities, Not Primary Objects

**Tasks appear as children of their assigned agent — they are what the agent is "responsible for."**

```
● Competitive Intelligence
  ├ Track Competitors (weekly, active)
  └ Competitive Brief (weekly, active)
```

Clicking a task under an agent drills into that task's detail (output, deliverable spec, run history). But the navigational frame is always "I'm looking at this agent's work," not "I'm looking at an isolated task."

### Task metadata in agent context

When showing tasks as agent responsibilities, display:
- Task title (human-readable)
- Schedule ("weekly", "daily", "monthly")
- Status (active/paused/completed) via color
- Last run ("2d ago") for freshness signal

### Task drill-down

Clicking a task switches the center panel to task detail view:
- Output viewer (rendered HTML/markdown)
- Run history
- Deliverable spec
- Back-breadcrumb to agent's primary view

This reuses existing `OutputView`, `RunHistoryView`, `DeliverableView` components.

---

## Principle 4: Domain Stewards Show Knowledge, Not Cards

**For domain stewards (5 of 8 agents), the primary view IS their context domain directory.**

The competitive intelligence agent's view is the `/workspace/context/competitors/` tree — entity folders, tracker files, synthesis files. This is the agent's accumulated knowledge made visible.

Why this works better than a card/summary view:
- Users can see exactly what the agent knows
- Entity-level drill-down (click `anthropic/profile.md` → read the profile)
- Staleness is visible (_tracker.md shows last-updated dates)
- The domain IS the agent's identity — not a separate concept

### Domain-agent mapping

| Agent | Domain | Directory |
|---|---|---|
| Competitive Intelligence | `competitors` | `/workspace/context/competitors/` |
| Market Research | `market` | `/workspace/context/market/` |
| Business Development | `relationships` | `/workspace/context/relationships/` |
| Operations | `projects` | `/workspace/context/projects/` |
| Marketing & Creative | `content_research` | `/workspace/context/content_research/` |

This mapping comes from `AGENT_TEMPLATES` in `api/services/agent_framework.py` and the `steward_agent` field in `api/services/directory_registry.py`.

---

## Principle 5: Synthesizers Show Deliverables

**For the synthesizer agent (Executive Reporting), the primary view is the latest deliverable output.**

The synthesizer doesn't own a domain — it reads across domains and produces reports. Its value is in the composed output, so that's what the user sees first.

Layout: latest output (rendered HTML/iframe) with run history below. Same pattern as the current task page's OutputView — because for synthesizers, the single-output assumption IS correct.

---

## Principle 6: Bots Show Observations + Connection Status

**For platform bots (Slack Bot, Notion Bot), the primary view is their temporal observations directory plus platform connection health.**

Bots are mechanical — they sense a platform and write structured observations. The user cares about:
1. Is the platform connected and healthy?
2. What has the bot observed recently?

The view shows the temporal directory (`/workspace/context/slack/`, `/workspace/context/notion/`) with daily observation files, plus a connection status indicator at the bottom.

---

## Principle 7: Agent-Scoped TP, Not Task-Scoped Only

**TP chat on the agents page is agent-scoped by default, narrowing to task-scoped on drill-down.**

| State | TP Scope | Use Cases |
|---|---|---|
| Agent selected | Agent-scoped | "Run the competitive brief", "What does this agent know about Anthropic?", "Assign a new task" |
| Task selected (drill-down) | Task-scoped | "Focus on pricing this week", "Run this task now", "The competitor section is weak" |

Agent-scoped TP is broader than task-scoped — it can discuss the agent's domain, trigger any of the agent's tasks, or assign new work. Task-scoped TP narrows to a specific task's execution and output.

---

## Principle 8: Cognitive State Is Inline, Not Separate

**Agent developmental state (self-reflection, feedback trends, run confidence) appears inline within the agent view, not on a separate dashboard.**

For domain stewards: domain health indicators in the _tracker.md (entity count, staleness, coverage).
For synthesizers: run trajectory with confidence trend in the run history.
For all agents: memory file sizes and last-updated dates signal developmental depth.

The existing `_tracker.md` file (deterministic, zero LLM cost) already serves as the "cognitive dashboard" for domain stewards — it shows what the agent knows, what's stale, and what's missing.

---

## Anti-Patterns (Updated)

| Anti-pattern | Why it fails | Correct approach |
|---|---|---|
| Uniform agent detail page | Different agent classes have different primary artifacts | Class-aware dispatch (domain/deliverable/observations) |
| Tasks as primary navigation | Tasks are transient, agents are persistent | Agents as roster, tasks as responsibilities |
| Separate agent reference page | Forces navigation away from working context | Agent identity info is inline in the agent view |
| Flat task list ungrouped | No relationship between work and worker visible | Tasks grouped under their assigned agent |
| Domain explorer only on context page | The domain IS the steward's primary view | Domain explorer embedded in steward agent view |

---

## Migration from v1

v1 had the agents page as a secondary reference surface (workforce types explainer + card list linking to `/agents/[id]` identity pages). v2 promotes agents to the primary working surface:

| v1 | v2 |
|---|---|
| `/agents` = explainer + card list | `/agents` = HOME, three-panel working surface |
| `/agents/[id]` = identity reference page | Agent identity inline in center panel |
| `/tasks` = primary working surface | Tasks as children of agents |
| Separate task page for output/config | Task detail via drill-down from agent |

The `/agents/[id]` route can redirect to `/agents?agent={id}` (slug-resolved) for backwards compatibility during migration.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-13 | v1 — Source-first mental model, progressive disclosure, platform icons, source-affinity grouping. Agent as reference surface. |
| 2026-03-16 | v1.1 — Platform icons on dashboard, supervision dashboard, origin badges. |
| 2026-03-21 | v1.2 — Principle 8: cognitive state is operational (ADR-128 Phase 6). |
| 2026-04-04 | v2 — Agent-centric reframe. Agents as primary working surface, not reference. Class-aware dispatch (domain/deliverable/observations). Tasks as responsibilities. Agent-scoped TP. Supersedes source-first grouping (domain-first for stewards, output-first for synthesizers). |
