# Agent Presentation Principles

**Date:** 2026-04-05 (v3 — three-tab center panel, knowledge-first); 2026-04-08 note added for ADR-163 + ADR-164
**Status:** Partially superseded — ADR-163 collapsed the Agents page to roster + identity (no tabs); see SURFACE-ARCHITECTURE.md v8 for current surface model
**Supersedes:** v2 (2026-04-04, task-cards-as-bridge vertical stack)
**Related:**
- [Surface Architecture](SURFACE-ARCHITECTURE.md) v8 — current model (ADR-163: Chat | Work | Agents | Context, Agents page is roster + identity only)
- [ADR-176](../adr/ADR-176-work-first-agent-model.md) — universal specialist roster (9 agents: 6 specialists + 3 bots, supersedes ADR-140)
- [ADR-138](../adr/ADR-138-agents-as-work-units.md) — agents as work units (tasks are WHAT, agents are WHO)
- [ADR-164](../adr/ADR-164-back-office-tasks-tp-as-agent.md) — TP as the 10th agent (meta-cognitive class), back office tasks owned by TP

> **2026-04-13 update:** After ADR-176, the workforce is 9 agents across 3 classes: specialist × 6 (Researcher, Analyst, Writer, Tracker, Designer, TP) + platform-bot × 3. The ICP-specific domain-steward names (Competitive Intelligence, Market Research, etc.) are replaced by universal specialist roles. After ADR-163, the Agents page is no longer the home and no longer uses a three-tab layout. Work observation moved to `/work`, context browsing to `/context`. The Agents page shrank to a single-view roster + identity + health card. This document's "three-tab center panel" principle is historical — the current Agents page has no tabs. The knowledge-first principle (Principle 1 below) remains directionally valid for the per-agent identity card, but the detail views it described now live on `/work` and `/context` surfaces.

---

## Core Insight

Users don't come to the agents page to see task cards. They come to see **what their agents know** and **what they've produced**. The agent IS its accumulated knowledge — domain files, entity profiles, synthesis outputs. Tasks are just the mechanism that keeps the knowledge fresh.

The three-tab center panel (Agent / Setup / Settings) reflects three user intents with decreasing frequency:

1. **Agent tab** (default, daily) — "What does this agent know?" → knowledge browser
2. **Setup tab** (occasional) — "How is this configured?" → task config, schedule, delivery
3. **Settings tab** (rare) — "Who is this agent?" → identity, history, feedback

---

## Principle 1: Knowledge Is the Hero

**The Agent tab shows the agent's accumulated knowledge — not task cards, not status dashboards.** Domain files fill 90% of the space. Task metadata collapses to a single status line.

A user opening "Researcher" sees:
- A 2-line description of what this agent does
- A single status line: `● Active · Updated 2h ago · Weekly · competitors/ → signals/`
- Then immediately: the domain file browser filling the rest of the panel

The status line is clickable — it links to the Setup tab for operational details.

---

## Principle 2: Agent Class Determines the Hero Content

The Agent tab's hero area varies by class, but the three-tab structure is identical for all agents.

| Agent Class | Agent Tab Hero | What Defines It |
|---|---|---|
| **Specialist** (Researcher, Analyst, Writer, Tracker, Designer) | Task assignments + recent outputs + capability summary | What work they're doing and how they contribute |
| **Specialist** (Thinking Partner) | Orchestration health + back office task status | System coherence and workforce coordination |
| **Platform bot** | Observations directory (`/workspace/context/{platform}/`) + connection status | Platform connection + observation stream |

This replaces the v2 approach of vertical stacking (header → task cards → domain files). The tab model gives knowledge the full panel height instead of competing with task cards for vertical space.

---

## Principle 3: Tasks Are Infrastructure, Not the Primary Surface

**Tasks appear on the Setup tab, not the Agent tab.** The Agent tab shows only a collapsed status line derived from the agent's tasks.

Status line derivation:
- **Status dot**: green (has active tasks), gray (no tasks / all paused)
- **Freshness**: "Updated 2h ago" — from most recent `last_run_at` across tasks
- **Cadence**: "Weekly" — from most frequent task schedule
- **Context flow**: "competitors/ → signals/" — reads/writes from tasks, abbreviated

If the agent has no tasks, the status line shows: `○ No active tasks`

Users who want to see task objectives, schedules, delivery channels, or trigger runs go to the **Setup tab**. This is intentional separation: observation (Agent tab) vs. configuration (Setup tab).

---

## Principle 4: Agents Are Stable, Tasks Come and Go

**The left panel roster is permanent — 9 agents, always visible, no filters.** Users build a relationship with their agents over time. "My researcher" and "my analyst" are persistent mental anchors — universal roles that make sense regardless of what work the user is doing.

### Roster layout

Two sections with user-friendly labels (ADR-176 universal specialists):

```
YOUR TEAM
● Researcher
  specialist · 2 tasks
● Analyst
  specialist · 1 task
● Writer
  specialist · 2 tasks
● Tracker
  specialist · 1 task
● Designer
  specialist · 0 tasks
● Thinking Partner
  meta-cognitive · 2 tasks

INTEGRATIONS
● Slack Bot
  slack/ · 1 task
● Notion Bot
  notion/ · 0 tasks
● GitHub Bot
  github/ · 0 tasks
```

No filter pills (All/Active/Dormant removed). The roster is fixed — agents can't be deleted (ADR-176 hospital principle). Showing all 9 always communicates "ready to work" for dormant agents.

---

## Principle 5: Task Names Are Freeform

**A task name is the user's description of the work. It never includes frequency, agent name, or internal type classification.**

- Good: "Track Competitors", "Q2 Board Deck", "Monitor HN for AI launches"
- Bad: "Weekly Competitor Report" (frequency is config, not identity)
- Bad: "Competitive Intelligence - Track" (redundant with agent name)
- Bad: "context-track-competitors" (internal classification)

The task type registry provides default `display_name` values, but users and TP can name tasks anything. Schedule, mode, and type_key are separate fields.

---

## Principle 6: TP-Mediated Actions, Not CRUD Forms

**Configuration changes go through TP, not inline edit forms.** The Setup tab shows current config as read-only cards with action buttons that either:

1. Call APIs directly for simple actions: Run Now (`api.tasks.run()`), Pause (`api.tasks.update()`)
2. Open TP chat for complex changes: "Edit via TP →" pre-composes a chat prompt

This is consistent with the product model: the agent platform talks to you. Forms are for settings pages; the working surface uses conversation.

---

## Principle 7: Cognitive State Is Inline, Not Separate

Agent developmental state (quality score, feedback trends, learned preferences) appears on the Settings tab — visible when the user intentionally looks for it, but not cluttering the daily-use Agent tab.

For domain stewards: domain health is implicit in the file browser (entity count, file dates).
For synthesizers: quality is implicit in the output history (delivered/failed, edit distance).
For all agents: the Settings tab's History section shows quality_score, trend, and recent runs.

---

## Principle 8: One Surface for Agent Content

**Domain files render on the agents page, not as a redirect to the Context page.** The agents page is a master-detail surface — selecting an agent shows their content inline. This avoids the redirect loop (agents → context → back to agents) that breaks user flow.

The Context page exists for **cross-cutting browsing** — viewing domains across agents, managing uploads, editing workspace settings. It's the Finder view of the whole workspace. The agents page is the agent-scoped view of the same files.

Both surfaces read from the same data (workspace_files via `GET /api/workspace/tree`). No duplication.

---

## Anti-Patterns

| Anti-pattern | Why it fails | Correct approach |
|---|---|---|
| Task cards as hero | Users came to see knowledge, not task metadata | Tasks collapse to status line (Agent tab) or Setup tab |
| Vertical stack (header → tasks → files) | Files compete with task cards for vertical space | Tabs give knowledge full panel height |
| Redirecting to Context page for file browsing | Breaks flow, loses agent context | Master-detail inline on agents page |
| Frequency in task names | Schedule is config, not identity | Freeform names, schedule as separate field |
| Filter pills on fixed roster | Can't delete agents, filtering hides them pointlessly | Show all 9 always |
| CRUD forms for task config | Product model is conversational | TP-mediated actions |
| Uniform agent detail page | Different classes have different primary artifacts | Class-aware hero dispatch |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-13 | v1 — Source-first mental model, progressive disclosure, platform icons, agent as reference surface. |
| 2026-04-04 | v2 — Agent-centric reframe. Agents as primary working surface. Class-aware dispatch. Tasks as children. Task-cards-as-bridge vertical stack. |
| 2026-04-05 | v3 — Three-tab center panel (Agent / Setup / Settings). Knowledge is the hero. Task metadata collapses to status line. Task naming convention (freeform, no frequency). Roster labels (Your Team / Cross-Team / Integrations, no filter pills). TP-mediated actions. |
