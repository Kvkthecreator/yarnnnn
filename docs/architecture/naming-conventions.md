# YARNNN Naming Conventions

**Status:** Canonical
**Date:** 2026-03-06 (updated from 2026-03-03)
**Related:**
- [Agent Model Comparison](agent-model-comparison.md) — why YARNNN has its own model
- [ADR-087: Agent Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — naming convention table

---

## Purpose

YARNNN operates in a rapidly evolving AI landscape where terminology shifts frequently. This document establishes naming conventions that:

1. Are consistent from database column to API response to frontend UI to marketing copy
2. Are intuitive enough that a new contributor, user, or investor can understand the system without a glossary
3. Don't require translation between internal and external vocabulary
4. Are stable enough to survive the next wave of industry terminology shifts

The goal: **one name per concept, used everywhere.**

---

## The Core Vocabulary

### Tier 1 — Concepts a user encounters

These names appear in the UI, in onboarding, in marketing, and in the codebase. They must be immediately understandable.

| Concept | YARNNN name | Used in | NOT called |
|---------|------------|---------|------------|
| A recurring or one-time AI work product | **Agent** | DB, API, UI, docs, marketing | task, workflow, agent, automation, job |
| A specific generated output | **Version** | DB (`agent_runs`), UI, API | draft, output, result, artifact, build |
| The AI agent in conversation | **Agent** (internally TP) | UI, marketing, docs | assistant, chatbot, copilot, thinking partner |
| Connected external platform | **Platform** | DB (`platform_connections`), UI, settings | integration, connector, app, service |
| Synced content from platforms | **Context** | UI (Context page), marketing | data, content, signals, feed |
| What YARNNN knows about the user | **Memory** | UI (Memory page), marketing | profile, preferences, knowledge, context |

**Why "Agent":** It communicates that YARNNN produces tangible output — not just conversation. A agent is a standing commitment: "I will produce this for you, on this schedule, from these sources." No other term in the AI landscape carries this specificity. "Task" implies one-time. "Workflow" implies multi-step process. "Agent" implies autonomous entity. "Agent" implies recurring, specialized, improving output.

**Why "Agent":** The product has evolved from conversational assistant to autonomous execution. "Agent" is now the accurate description: it creates agents, manages work, executes on schedule, and learns from feedback. The prior name "Thinking Partner" undersold the execution capability. Internally still abbreviated as "TP" in code (no rename needed — the codebase uses TP as a system identifier, not a user-facing label).

### Tier 2 — Concepts a developer encounters

These names appear in code, API documentation, and architecture docs. They should be clear to a developer reading the codebase for the first time.

| Concept | YARNNN name | DB/code location | Market equivalent |
|---------|------------|-------------------|-------------------|
| Per-agent behavioral directives | **`AGENT.md`** | Workspace: `/agents/{slug}/AGENT.md` (migrating from `agents.agent_instructions` TEXT) | CLAUDE.md, OpenClaw AGENTS.md |
| Per-agent accumulated knowledge | **`memory/`** | Workspace: `/agents/{slug}/memory/*.md` (migrating from `agents.agent_memory` JSONB) | `.claude/memory/`, OpenClaw MEMORY.md |
| Per-agent domain understanding | **`thesis.md`** | Workspace: `/agents/{slug}/thesis.md` | (YARNNN-unique — no equivalent) |
| Global user knowledge | **`user_memory`** | `user_memory` table (renamed from `user_context` in ADR-087 migration) | OpenClaw USER.md + SOUL.md |
| Raw platform input | **`platform_content`** | `platform_content` table | Source files, filesystem |
| Agent workspace | **Workspace** | `workspace_files` table, path-based access via `AgentWorkspace` class | `.claude/` directory, AgentFS |
| Assembled prompt input per turn | **Working memory** | `build_working_memory()` output | Context assembly, bootstrap context |
| Agent capabilities | **Primitives** | `api/services/primitives/` | Tools (intentionally distinct — see below) |
| Background content generation | **Headless mode** | `mode="headless"` in agent execution | Background jobs, cron tasks |
| The decision point for incoming signals | **Input router** | `process_agent_input()` (ADR-088) | Gateway (OpenClaw), dispatcher |
| Serial execution protection | **Advisory locks** | Postgres advisory locks per agent | Lane Queue (OpenClaw), task queue |

**Why "Primitives" not "Tools":** YARNNN's primitives are a curated, mode-gated set — not an extensible plugin system. "Tools" implies users can add their own (MCP model). "Primitives" implies a foundational set that the system provides. This is an intentional product choice: YARNNN's value comes from how the agent uses its built-in capabilities with accumulated context, not from tool extensibility.

### Tier 3 — Concepts in architecture docs only

These appear only in ADRs and architecture documentation. They help contributors understand the system but don't surface to users.

| Concept | YARNNN name | Reference |
|---------|------------|-----------|
| The pipeline managing agent lifecycle | **Orchestration** | ADR-080, agent-execution-model.md |
| What decides how to gather context for a agent type | **Execution strategy** | ADR-045, backend-orchestration.md |
| Hourly scan for significant platform activity | **Signal processing** | ADR-068 |
| Content that has been referenced and is kept indefinitely | **Retained content** | ADR-072 |
| The four data layers | **Memory / Activity / Context / Work** | ADR-063 |
| Graduated response to incoming signals | **Signal strength** (high/medium/low) | ADR-088 |

---

## Naming Relationships

How the names connect across layers:

```
User sees:                  Developer sees:              Stores:
─────────                   ──────────────               ─────────
Agent          →      agent              →   agents (table)
  └─ Instructions    →      AGENT.md           →   workspace_files (path-based)
  └─ Memory          →      memory/*.md        →   workspace_files (path-based)
  └─ Thesis          →      thesis.md          →   workspace_files (path-based)
  └─ Sources         →      sources            →   agents.sources (JSONB)
  └─ Schedule        →      schedule           →   agents.schedule (JSONB)
  └─ Versions        →      agent_runs         →   agent_runs (table)
  └─ Workspace       →      AgentWorkspace     →   workspace_files (virtual filesystem)

Context (page)       →      platform_content         →   platform_content (table)
Memory (page)        →      user_memory              →   user_memory (table)
Agent                →      TP / chat mode           →   chat_sessions + session_messages
```

> **Note (ADR-106):** Agent intelligence is migrating from DB columns (`agent_instructions`, `agent_memory`) to workspace files (`AGENT.md`, `memory/*.md`). During Phase 1, both exist. Phase 2 will make workspace files the source of truth. See [Workspace Conventions](workspace-conventions.md).

---

## Naming Debt

Existing names that don't follow these conventions. Each has a migration plan.

| Current name | Should become | Scope of change | When |
|-------------|---------------|-----------------|------|
| `user_context` (table) | `user_memory` | DB rename + all backend references + frontend API calls | **ADR-087 migration window** (bundled as separate commit before Phase 1 columns) |
| `template_structure` + `type_config` + `recipient_context` (agent columns) | Partially consolidated (2026-03-09): `recipient_context` and `template_structure.format_notes` surfaced in Instructions panel alongside `agent_instructions`. `type_config` remains in Settings (type-specific execution parameters). | Backend fields unchanged; frontend Instructions panel now owns `recipient_context` + `template_structure` | Done (UI consolidation). Full schema merge deferred — fields stay separate, UI unifies them. |
| `filesystem_items` references in code | Should all be `platform_content` | Grep + replace (table already renamed per ADR-072) | Immediate cleanup |
| `surface_context` (frontend → backend) | `chat_context` or rename to match `agent_id` routing | Frontend API call + backend handler | ADR-087 Phase 1 (when we wire `agent_id`) |
| `agents.agent_instructions` (column) | `AGENT.md` workspace file | Workspace file becomes source of truth; column kept for read fallback | ADR-106 Phase 2 |
| `agents.agent_memory` (JSONB column) | `memory/*.md` workspace files | Topic-scoped workspace files replace opaque JSONB | ADR-106 Phase 2 |

---

## Frontend ↔ GTM Alignment

The naming should carry through from code to product to market. Here's how each Tier 1 concept maps:

### Agent

| Layer | How it appears |
|-------|---------------|
| **DB** | `agents` table |
| **API** | `GET /api/agents`, `POST /api/agents` |
| **Frontend** | "Work" in nav, agent cards, creation via Agent chat |
| **Marketing** | "YARNNN agents get smarter with every run." |
| **Onboarding** | "Set up your first agent — a recurring AI work product that improves over time." |

**The pitch:** Agents aren't tasks you check off. They're standing commitments that compound in quality. Every time your Monday digest runs, it knows more about what matters to you. That's because each agent carries its own memory.

### Agent

| Layer | How it appears |
|-------|---------------|
| **DB** | `chat_sessions`, `session_messages` |
| **API** | `POST /api/chat` |
| **Frontend** | Chat interface, "Agent" in nav (with Sparkles icon) |
| **Marketing** | "Your agent understands your work across every platform." |
| **Onboarding** | "Chat with your agent — it knows your Slack, email, calendar, and docs." |

### Memory

| Layer | How it appears |
|-------|---------------|
| **DB** | `user_memory`, `agents.agent_memory` |
| **API** | `GET /api/memory/context` |
| **Frontend** | Memory page (global), Memory section in agent detail (per-agent) |
| **Marketing** | "YARNNN remembers what matters. Global memory for you, specialized memory for each agent." |

### Instructions

| Layer | How it appears |
|-------|---------------|
| **DB** | `agents.agent_instructions` |
| **API** | Part of agent CRUD |
| **Frontend** | "Instructions" textarea in agent settings (Phase 3) |
| **Marketing** | "Tell each agent how to think — your instructions shape its behavior." |
| **Onboarding** | "Add instructions like 'use formal tone' or 'focus on trends, not raw data.'" |

---

## Naming Convention Rules

For future development:

1. **One name, everywhere.** If the UI calls it "Memory," the API returns `memory`, the code uses `memory`, and the docs say "memory." No translation layers.

2. **User-facing names are plain English.** No jargon in Tier 1. "Agent" is the one domain-specific term, and it's worth the learning curve because it communicates the product's core value.

3. **Developer-facing names are descriptive.** `agent_instructions` not `config`. `agent_memory` not `context`. `platform_content` not `data`. The name should tell you what it is without looking up a glossary.

4. **Avoid overloaded terms.** "Context" is the most dangerous word in AI. In YARNNN: "Context" = the raw platform content page. "Memory" = accumulated knowledge. "Working memory" = assembled prompt input. "Instructions" = behavioral directives. Never use "context" to mean memory, instructions, or prompt input in code or docs.

5. **Rename when the model changes, not for trends.** The shift from "Thinking Partner" to "Agent" reflects a real product evolution — YARNNN now executes autonomously, not just collaborates. "Agent" stays because no better term captures recurring AI work products. Rename when the product model changes, not when marketing buzzwords shift.

6. **Primitives stay primitives.** This is the one intentionally non-market term. It signals that YARNNN's agent capabilities are built-in and curated, not a plug-in marketplace.

---

## The Communication Framework

When explaining YARNNN to someone who knows the AI landscape:

> **"YARNNN delivers specialized AI work products that get smarter with every run."**
>
> Unlike chat assistants that start from scratch each session, every YARNNN agent carries its own memory — what it has learned from past runs, user feedback, and platform activity. Unlike always-on agents that burn compute continuously, YARNNN's agents sleep between runs and wake up fully informed.
>
> Think of it as a team of specialists, each improving at their specific job: your Monday digest gets better at digests, your meeting prep gets better at meeting prep, your competitor tracker gets better at tracking competitors.

When explaining to someone non-technical:

> **"YARNNN reads your Slack, email, and docs, then produces the work products you need — automatically, on your schedule."**
>
> Each agent is like hiring a specialist who reads everything relevant and produces a polished output. The more it runs, the better it gets, because it remembers what you liked and what you changed.

---

## References

- [Agent Model Comparison](agent-model-comparison.md) — why YARNNN has its own model
- [ADR-087: Agent Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — naming convention origin
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — chat mode / headless mode naming
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — workspace path conventions
- [Workspace Conventions](workspace-conventions.md) — canonical workspace path reference
- [Development Landscape](../analysis/workspace-architecture-landscape.md) — implementation sequence
