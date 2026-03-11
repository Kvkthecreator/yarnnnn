# Workspace Architecture — Development Landscape

YARNNN | March 2026 | Living compass document

---

## Purpose

This document maps the architecture evolution for agent-scoped context, unified input processing, and agent autonomy. It exists so that any contributor can understand what's decided, what's parked, and how the pieces connect.

**Canonical references:**
- [Agent Model Comparison](../architecture/agent-model-comparison.md) — YARNNN's position and conviction (why this model, not others)
- [Naming Conventions](../architecture/naming-conventions.md) — full naming strategy (dev → frontend → GTM)
- [workspace-architecture-analysis-2026-03-02.md](workspace-architecture-analysis-2026-03-02.md) — detailed analysis archive (v1–v5, OpenClaw comparison, ghost entity discovery)

---

## YARNNN's Model (Summary)

YARNNN is a **agent-centric model**: a network of purpose-built specialists that sleep between executions but get smarter each time they wake up. Task-based foundation with agent-like extensions. See [Agent Model Comparison](../architecture/agent-model-comparison.md) for the full rationale.

---

## Naming Convention

Full naming strategy: [Naming Conventions](../architecture/naming-conventions.md).

Quick reference for this document:

| Concept | YARNNN name | Market equivalent |
|---------|------------|-------------------|
| Per-agent behavioral directives | `agent_instructions` | OpenClaw AGENTS.md, Cowork skills |
| Per-agent accumulated knowledge | `agent_memory` | OpenClaw MEMORY.md, daily logs |
| Global user knowledge | `user_memory` | OpenClaw USER.md + SOUL.md |
| Raw platform input | `platform_content` | Source files, filesystem |
| Assembled prompt input | Working memory | Context assembly |
| Agent capabilities | Primitives | Tools (intentionally distinct) |

**Relationship:** `platform_content` (raw) → agent reads during execution → `agent_memory` (derived understanding) → informs next execution. `agent_instructions` (user-authored) tells the agent HOW to interpret the raw material for this specific work.

---

## Implementation Sequence

```
Step 1: Storage                        Step 2: Unified Input Processing
(ADR-087)                              (ADR-088)

┌──────────────────────────┐           ┌──────────────────────────┐
│ agent_instructions │           │ process_agent_     │
│ (TEXT — user-authored)   │           │ input()                  │
│                          │           │                          │
│ agent_memory       │◀──────────│ All input paths converge │
│ (JSONB — system-written) │  writes   │ to one decision point:   │
│                          │  to       │ generate / update memory │
│ mode, session routing    │           │ / log only               │
└──────────────────────────┘           └──────────────────────────┘
                                                    │
                                                    │ enables
                                                    ▼
                                       ┌──────────────────────────┐
                                       │ Step 3: Agent Autonomy   │
                                       │ (ADR-089)                │
                                       │                          │
                                       │ Heartbeats, context-     │
                                       │ aware triggers, lighter  │
                                       │ actions than full gen    │
                                       └──────────────────────────┘
```

### Dependencies

- **Step 2 depends on Step 1.** Input routing needs somewhere to write (agent_memory).
- **Step 3 depends on Step 2.** Autonomous actions need a unified decision point to route through.
- **Step 1 is independent.** Can implement and validate immediately.

### Why this order

Step 1 validates: does scoped context improve output quality? If no, Steps 2-3 are unnecessary.
Step 2 addresses: the scattered input paths (signal processing, event triggers, scheduled generation, webhooks — all separate) are the real architectural debt. Unifying them isn't about concurrency protection — it's about having one model for "the agent should pay attention to this agent."
Step 3 enables: the agent maintaining its own context between explicit triggers. Heartbeat = periodic self-review. Context-aware triggers = reacting to new platform content without full generation.

---

## Step 1: Agent Scoped Context (ADR-087)

**Status:** Proposed → implement now.

**Schema:** 4 new columns, 0 new tables.

| Table | Column | Type | Purpose |
|-------|--------|------|---------|
| agents | `agent_instructions` | TEXT | User-authored behavioral directives |
| agents | `agent_memory` | JSONB | System-accumulated knowledge |
| agents | `mode` | TEXT | 'recurring' \| 'goal' |
| chat_sessions | `agent_id` | UUID FK | Routing key for memory accumulation |

**Phases:**

| Phase | What | Validates |
|-------|------|-----------|
| 1 | Schema + read paths (working memory, headless prompt) | Does scoped context improve TP + headless quality? |
| 2 | Write paths + input unification (process_feedback → memory, nightly cron, unified input router) | Does memory accumulate usefully? Do input paths converge cleanly? |
| 3 | Frontend (instructions editor, memory viewer, goal mode, workspace chat) | Does the UX work? |
| 4 | Memory extraction scoping (route agent-specific facts to agent_memory) | Does automated extraction produce useful scoped memory? |

**Incremental path:**

| Step | Trigger | Migration |
|------|---------|-----------|
| This ADR | Now | `agent_instructions` TEXT + `agent_memory` JSONB |
| D2: typed files | JSONB unwieldy | Split memory sections into `workspace_files` rows |
| D3: workspace entity | N:1 workspace:agent needed | Activate `projects` ghost table or create `workspaces` |

---

## Step 2: Unified Input Processing (ADR-088)

**Status:** Proposed — implement as part of ADR-087 Phase 2.

**The problem:** Five input types, five separate code paths, no unified decision model.

| Input type | Current handler | Decision logic |
|------------|----------------|---------------|
| User messages | `POST /chat` → TP loop | Always: full conversation |
| Scheduled generation | `unified_scheduler.py` | Always: full generation |
| Platform events | `event_triggers.py` | Always: full generation (with cooldown) |
| Signal detection | `unified_scheduler.py` (hourly) | Create new agent OR ignore |
| Platform sync | `platform_sync_scheduler.py` | N/A — writes to platform_content |

**The solution:** `process_agent_input()` — a single function that receives an input and decides the action:

| Signal strength | Action | Example |
|----------------|--------|---------|
| High | Full generation | Schedule fires, direct @mention |
| Medium | Update `agent_memory` | New messages in monitored channel |
| Low | Log only | Tangentially related activity |

This collapses the heartbeat, signal processing, and event trigger concerns into one routing model. The Lane Queue (per-agent serialization) is an implementation detail within this function, needed when concurrent writes become real.

---

## Step 3: Agent Autonomy (ADR-089)

**Status:** Proposed (Parked) — un-park after Step 2 validates.

**The expansion:** Currently all triggers produce full generation. With unified input processing + agent memory, lighter actions become possible:

| Autonomous action | Trigger | Writes to |
|-------------------|---------|-----------|
| Platform content observation | New content for agent's sources | `agent_memory.observations` |
| End-of-session context flush | TP session expires in agent scope | `agent_memory.session_summaries` |
| Signal accumulation | Signal detected for existing agent | `agent_memory.observations` |
| Periodic workspace review (heartbeat) | Configurable interval | `agent_memory` (compaction + update) |

**The tension resolved:** Claude Code is task-based (sessions, explicit triggers). OpenClaw is agent-oriented (always-on, continuous awareness). YARNNN's path: task-based foundation (agents, scheduled generation) with agent-oriented extensions (context-aware triggers, heartbeats). Step 1 is task-based. Step 2 adds the routing layer. Step 3 adds the always-aware behavior on top.

---

## Architecture Mapping

| Concept | Claude Code | OpenClaw | YARNNN |
|---------|------------|----------|--------|
| Raw input | Source files | Workspace dir + daily logs | `platform_content` + documents |
| Generated output | — | Agent responses | `agent_runs` |
| Per-project instructions | CLAUDE.md | AGENTS.md + SOUL.md | `agent_instructions` |
| Per-project memory | CLAUDE.md (accumulated) | MEMORY.md + daily logs | `agent_memory` |
| Global user profile | — | USER.md | `user_memory` |
| Execution schedule | CI/CD | HEARTBEAT.md + crons | `schedule` + `trigger_config` |
| Tool configuration | — | TOOLS.md | Primitives registry |
| Input routing | CLI invocation | Gateway | `process_agent_input()` [Step 2] |
| Work serialization | Single process | Lane Queue | Advisory locks / optimistic concurrency [Step 2] |
| Autonomous awareness | — | Memory flush + heartbeats | Context-aware triggers [Step 3] |

---

## Naming Debt (Future Cleanup)

| Current name | Should become | Why | When |
|-------------|---------------|-----|------|
| `user_context` (table) | `user_memory` | It's memory, not assembled context | **ADR-087 migration window** (bundled as separate commit) |
| `template_structure` + `type_config` + `recipient_context` | Consider consolidating under `agent_instructions` | All part of the instructions layer | After ADR-087 Phase 1 validates |
| Signal processing (in `unified_scheduler.py`) + event triggers (`event_triggers.py`) + webhooks | Converge into unified input model | Scattered input paths | ADR-088 / ADR-087 Phase 2 |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-02 | Rejected FK-scoping on user_context (v1) | Relational thinking, not context-document thinking |
| 2026-03-02 | Adopted context document per agent (v2) | Completes ADR-038 filesystem mapping |
| 2026-03-03 | Validated via OpenClaw comparison (v4) | Typed files work; Lane Queue gap identified |
| 2026-03-03 | Split `work_context` → `agent_instructions` + `agent_memory` | Instructions (user-authored, stable) ≠ memory (system-accumulated, growing). Market-aligned naming. |
| 2026-03-03 | Collapsed three tracks into sequential steps | Data model → input unification → agent autonomy. Each step enables the next. |
| 2026-03-03 | Confirmed agent as unit of work | Workspace entity deferred until N:1 becomes real |

---

## What to Read

| If you want to understand... | Read |
|------------------------------|------|
| The schema decision and implementation plan | [ADR-087: Agent Scoped Context](../adr/ADR-087-workspace-scoping-architecture.md) |
| The input unification and serialization plan | [ADR-088: Unified Input Processing](../adr/ADR-088-input-gateway-work-serialization.md) |
| The agent autonomy expansion | [ADR-089: Agent Autonomy & Context-Aware Triggers](../adr/ADR-089-agent-autonomy-context-aware-triggers.md) |
| How we got here (full analysis, 5 versions) | [workspace-architecture-analysis-2026-03-02.md](workspace-architecture-analysis-2026-03-02.md) |
| The filesystem-as-context foundation | [ADR-038](../adr/ADR-038-filesystem-as-context.md) |
| The unified agent modes | [ADR-080](../adr/ADR-080-unified-agent-modes.md) |
