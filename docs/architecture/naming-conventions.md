# YARNNN Naming Conventions

**Status:** Canonical
**Date:** 2026-03-03
**Related:**
- [Agent Model Comparison](agent-model-comparison.md) — why YARNNN has its own model
- [ADR-087: Deliverable Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — naming convention table

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
| A recurring or one-time AI work product | **Deliverable** | DB, API, UI, docs, marketing | task, workflow, agent, automation, job |
| A specific generated output | **Version** | DB (`deliverable_versions`), UI, API | draft, output, result, artifact, build |
| The AI assistant in conversation | **Thinking Partner** (TP) | UI, marketing, docs | assistant, chatbot, copilot, agent |
| Connected external platform | **Platform** | DB (`platform_connections`), UI, settings | integration, connector, app, service |
| Synced content from platforms | **Context** | UI (Context page), marketing | data, content, signals, feed |
| What YARNNN knows about the user | **Memory** | UI (Memory page), marketing | profile, preferences, knowledge, context |

**Why "Deliverable":** It communicates that YARNNN produces tangible output — not just conversation. A deliverable is a standing commitment: "I will produce this for you, on this schedule, from these sources." No other term in the AI landscape carries this specificity. "Task" implies one-time. "Workflow" implies multi-step process. "Agent" implies autonomous entity. "Deliverable" implies recurring, specialized, improving output.

**Why "Thinking Partner":** It communicates collaboration, not automation. The TP doesn't just execute — it thinks with you. This differentiates from "assistant" (subservient), "copilot" (secondary), and "agent" (autonomous).

### Tier 2 — Concepts a developer encounters

These names appear in code, API documentation, and architecture docs. They should be clear to a developer reading the codebase for the first time.

| Concept | YARNNN name | DB/code location | Market equivalent |
|---------|------------|-------------------|-------------------|
| Per-deliverable behavioral directives | **`deliverable_instructions`** | `deliverables.deliverable_instructions` (TEXT) | OpenClaw AGENTS.md, Cowork skills, CLAUDE.md rules |
| Per-deliverable accumulated knowledge | **`deliverable_memory`** | `deliverables.deliverable_memory` (JSONB) | OpenClaw MEMORY.md + daily logs |
| Global user knowledge | **`user_memory`** | `user_memory` table (renamed from `user_context` in ADR-087 migration) | OpenClaw USER.md + SOUL.md |
| Raw platform input | **`platform_content`** | `platform_content` table | Source files, filesystem |
| Assembled prompt input per turn | **Working memory** | `build_working_memory()` output | Context assembly, bootstrap context |
| Agent capabilities | **Primitives** | `api/services/primitives/` | Tools (intentionally distinct — see below) |
| Background content generation | **Headless mode** | `mode="headless"` in agent execution | Background jobs, cron tasks |
| The decision point for incoming signals | **Input router** | `process_deliverable_input()` (ADR-088) | Gateway (OpenClaw), dispatcher |
| Serial execution protection | **Advisory locks** | Postgres advisory locks per deliverable | Lane Queue (OpenClaw), task queue |

**Why "Primitives" not "Tools":** YARNNN's primitives are a curated, mode-gated set — not an extensible plugin system. "Tools" implies users can add their own (MCP model). "Primitives" implies a foundational set that the system provides. This is an intentional product choice: YARNNN's value comes from how the agent uses its built-in capabilities with accumulated context, not from tool extensibility.

### Tier 3 — Concepts in architecture docs only

These appear only in ADRs and architecture documentation. They help contributors understand the system but don't surface to users.

| Concept | YARNNN name | Reference |
|---------|------------|-----------|
| The pipeline managing deliverable lifecycle | **Orchestration** | ADR-080, agent-execution-model.md |
| What decides how to gather context for a deliverable type | **Execution strategy** | ADR-045, backend-orchestration.md |
| Hourly scan for significant platform activity | **Signal processing** | ADR-068 |
| Content that has been referenced and is kept indefinitely | **Retained content** | ADR-072 |
| The four data layers | **Memory / Activity / Context / Work** | ADR-063 |
| Graduated response to incoming signals | **Signal strength** (high/medium/low) | ADR-088 |

---

## Naming Relationships

How the names connect across layers:

```
User sees:                  Developer sees:              DB stores:
─────────                   ──────────────               ─────────
Deliverable          →      deliverable              →   deliverables (table)
  └─ Instructions    →      deliverable_instructions →   deliverables.deliverable_instructions
  └─ Memory          →      deliverable_memory       →   deliverables.deliverable_memory
  └─ Sources         →      sources                  →   deliverables.sources (JSONB)
  └─ Schedule        →      schedule + trigger_config →  deliverables.schedule (JSONB)
  └─ Versions        →      deliverable_versions     →   deliverable_versions (table)

Context (page)       →      platform_content         →   platform_content (table)
Memory (page)        →      user_memory              →   user_memory (table)
Thinking Partner     →      TP / chat mode           →   chat_sessions + session_messages
```

---

## Naming Debt

Existing names that don't follow these conventions. Each has a migration plan.

| Current name | Should become | Scope of change | When |
|-------------|---------------|-----------------|------|
| `user_context` (table) | `user_memory` | DB rename + all backend references + frontend API calls | **ADR-087 migration window** (bundled as separate commit before Phase 1 columns) |
| `template_structure` + `type_config` + `recipient_context` (deliverable columns) | Consider consolidating under instructions layer | Backend fields + frontend forms | After ADR-087 Phase 1 validates; these are structural instructions vs. behavioral instructions — may stay separate with clearer naming |
| `filesystem_items` references in code | Should all be `platform_content` | Grep + replace (table already renamed per ADR-072) | Immediate cleanup |
| `surface_context` (frontend → backend) | `chat_context` or rename to match `deliverable_id` routing | Frontend API call + backend handler | ADR-087 Phase 1 (when we wire `deliverable_id`) |

---

## Frontend ↔ GTM Alignment

The naming should carry through from code to product to market. Here's how each Tier 1 concept maps:

### Deliverable

| Layer | How it appears |
|-------|---------------|
| **DB** | `deliverables` table |
| **API** | `GET /api/deliverables`, `POST /api/deliverables` |
| **Frontend** | Deliverables page, deliverable cards, "Create Deliverable" button |
| **Marketing** | "YARNNN deliverables get smarter with every run." |
| **Onboarding** | "Set up your first deliverable — a recurring AI work product that improves over time." |

**The pitch:** Deliverables aren't tasks you check off. They're standing commitments that compound in quality. Every time your Monday digest runs, it knows more about what matters to you. That's because each deliverable carries its own memory.

### Thinking Partner

| Layer | How it appears |
|-------|---------------|
| **DB** | `chat_sessions`, `session_messages` |
| **API** | `POST /api/chat` |
| **Frontend** | Chat interface, "Thinking Partner" in nav |
| **Marketing** | "Your Thinking Partner understands your work across every platform." |
| **Onboarding** | "Chat with your Thinking Partner — it knows your Slack, email, calendar, and docs." |

### Memory

| Layer | How it appears |
|-------|---------------|
| **DB** | `user_memory`, `deliverables.deliverable_memory` |
| **API** | `GET /api/memory/context` |
| **Frontend** | Memory page (global), Memory section in deliverable detail (per-deliverable) |
| **Marketing** | "YARNNN remembers what matters. Global memory for you, specialized memory for each deliverable." |

### Instructions

| Layer | How it appears |
|-------|---------------|
| **DB** | `deliverables.deliverable_instructions` |
| **API** | Part of deliverable CRUD |
| **Frontend** | "Instructions" textarea in deliverable settings (Phase 3) |
| **Marketing** | "Tell each deliverable how to think — your instructions shape its behavior." |
| **Onboarding** | "Add instructions like 'use formal tone' or 'focus on trends, not raw data.'" |

---

## Naming Convention Rules

For future development:

1. **One name, everywhere.** If the UI calls it "Memory," the API returns `memory`, the code uses `memory`, and the docs say "memory." No translation layers.

2. **User-facing names are plain English.** No jargon in Tier 1. "Deliverable" is the one domain-specific term, and it's worth the learning curve because it communicates the product's core value.

3. **Developer-facing names are descriptive.** `deliverable_instructions` not `config`. `deliverable_memory` not `context`. `platform_content` not `data`. The name should tell you what it is without looking up a glossary.

4. **Avoid overloaded terms.** "Context" is the most dangerous word in AI. In YARNNN: "Context" = the raw platform content page. "Memory" = accumulated knowledge. "Working memory" = assembled prompt input. "Instructions" = behavioral directives. Never use "context" to mean memory, instructions, or prompt input in code or docs.

5. **Don't rename to follow trends.** If the market starts calling everything "agents," YARNNN still calls them deliverables. If the market calls everything "skills," YARNNN still calls them instructions. The naming reflects the product model, not the latest convention. Rename only when YARNNN's model itself changes.

6. **Primitives stay primitives.** This is the one intentionally non-market term. It signals that YARNNN's agent capabilities are built-in and curated, not a plug-in marketplace.

---

## The Communication Framework

When explaining YARNNN to someone who knows the AI landscape:

> **"YARNNN delivers specialized AI work products that get smarter with every run."**
>
> Unlike chat assistants that start from scratch each session, every YARNNN deliverable carries its own memory — what it has learned from past runs, user feedback, and platform activity. Unlike always-on agents that burn compute continuously, YARNNN's deliverables sleep between runs and wake up fully informed.
>
> Think of it as a team of specialists, each improving at their specific job: your Monday digest gets better at digests, your meeting prep gets better at meeting prep, your competitor tracker gets better at tracking competitors.

When explaining to someone non-technical:

> **"YARNNN reads your Slack, email, and docs, then produces the work products you need — automatically, on your schedule."**
>
> Each deliverable is like hiring a specialist who reads everything relevant and produces a polished output. The more it runs, the better it gets, because it remembers what you liked and what you changed.

---

## References

- [Agent Model Comparison](agent-model-comparison.md) — why YARNNN has its own model
- [ADR-087: Deliverable Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) — naming convention origin
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — chat mode / headless mode naming
- [Development Landscape](../analysis/workspace-architecture-landscape.md) — implementation sequence
