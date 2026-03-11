# Architecture: Agents

**Status:** Canonical
**Date:** 2026-02-26 (updated 2026-03-10 for ADR-049 evolution: context provenance)
**Related:**
- [ADR-018: Recurring Agents](../adr/ADR-018-recurring-agents.md)
- [ADR-044: Agent Type Reconceptualization](../adr/ADR-044-agent-type-reconceptualization.md)
- [ADR-045: Agent Orchestration Redesign](../adr/ADR-045-agent-orchestration-redesign.md)
- [ADR-060: Background Conversation Analyst](../adr/ADR-060-background-conversation-analyst.md)
- [ADR-066: Delivery-First Redesign](../adr/ADR-066-agent-detail-redesign.md)
- [ADR-068: Signal-Emergent Agents](../adr/ADR-068-signal-emergent-agents.md)
- [ADR-080: Unified Agent Modes](../adr/ADR-080-unified-agent-modes.md) — agent operates in headless mode for generation
- [ADR-082: Agent Type Consolidation](../adr/ADR-082-agent-type-consolidation.md) — 27→8 active types
- [ADR-092: Agent Intelligence & Mode Taxonomy](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — full mode taxonomy, coordinator type, signal processing dissolution
- [ADR-101: Agent Intelligence Model](../adr/ADR-101-agent-intelligence-model.md) — four-layer knowledge model (Skills / Directives / Memory / Feedback)
- [ADR-102: yarnnn Content Platform](../adr/ADR-102-yarnnn-content-platform.md) — agent outputs as searchable platform_content
- [ADR-104: Agent Instructions as Unified Targeting](../adr/ADR-104-agent-instructions-unified-targeting.md) — instructions as single targeting layer, dead scope/filters deleted
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — workspace filesystem, AGENT.md, topic-scoped memory (Phase 2 COMPLETE: workspace as singular source of truth)
- [ADR-107: Knowledge Filesystem Architecture](../adr/ADR-107-knowledge-filesystem-architecture.md) — `/knowledge/` filesystem for agent-produced knowledge (Proposed)
- [Agent Execution Model](agent-execution-model.md)
- [Four-Layer Model](four-layer-model.md) — Agents are Layer 4 (Work)

---

## What Agents Are

A **agent** is a standing configuration for AI-generated output — and the accumulated intelligence that makes that output improve over time. It defines:
- **What to read** — sources (Slack channels, Gmail labels, Notion pages, Calendar)
- **How to behave** — agent type, mode, instructions (`agent_instructions`)
- **What it has learned** — accumulated operational knowledge (`agent_memory`)
- **Where to send** — destination (Slack channel/DM, Gmail draft, Notion page, download)
- **When to run** — schedule, event trigger, or autonomous review cadence

When a agent executes, it produces a **agent version** — an immutable record of the generated content, the sources used, and the delivery status.

**Conceptual framing (ADR-092)**: A agent is a lightweight specialist agent. Each has its own instructions, its own accumulated memory, its own execution mode. Twenty agents are twenty specialized agents — with zero resource cost when sleeping. The `mode` field determines the character of execution: clockwork schedule, project lifecycle, event-driven accumulation, autonomous domain review, or meta-coordination of other agents. See [ADR-092](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) and [Agent Modes](../features/agent-modes.md).

---

## Schema

### `agents` Table — Standing Configurations

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `user_id` | uuid | Owner |
| `title` | text | Human-readable name ("Monday Slack Digest") |
| `description` | text | Optional user notes |
| `agent_type` | text | Type identifier (see Type System below) |
| `type_config` | jsonb | Type-specific settings |
| `type_classification` | jsonb | ADR-044: `{binding, primary_platform, temporal_pattern, freshness_requirement_hours}` |
| `mode` | text | ADR-092: `recurring` (default) \| `goal` \| `reactive` \| `proactive` \| `coordinator` |
| `agent_instructions` | text | **DEPRECATED (ADR-106 Phase 2):** Migrated to workspace `AGENT.md`. DB column no longer read or written. Retained for lazy migration via `ensure_seeded()`. |
| `agent_memory` | jsonb | **DEPRECATED (ADR-106 Phase 2):** Migrated to workspace `memory/*.md`. DB column no longer read or written. Retained for lazy migration via `ensure_seeded()`. |
| `origin` | text | ADR-068/092: `user_configured`, `analyst_suggested`, or `coordinator_created` |
| `trigger_type` | text | `schedule`, `event`, or `manual` |
| `proactive_next_review_at` | timestamptz | ADR-092: Next review time for `proactive` and `coordinator` mode agents |
| `schedule` | jsonb | Schedule config: `{frequency, day, time, timezone, cron}` |
| `trigger_config` | jsonb | ADR-031: Event trigger config (platform, event_types, cooldown) |
| `sources` | jsonb | `[{platform, resource_id, resource_name, scope_config}]` |
| `destination` | jsonb | `{platform, target, format, options}` |
| `destinations` | jsonb | ADR-031: Array of destination configs (multi-destination support) |
| `status` | text | `active`, `paused`, or `archived` |
| `next_run_at` | timestamptz | Calculated from schedule; NULL for manual trigger |
| `last_run_at` | timestamptz | Last successful execution timestamp |
| `last_triggered_at` | timestamptz | Last event trigger timestamp |
| `created_at` | timestamptz | Creation timestamp |
| `updated_at` | timestamptz | Last modification timestamp |

### `agent_runs` Table — Immutable Output Records

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `agent_id` | uuid | Foreign key to `agents` |
| `version_number` | int | Sequential version number (1, 2, 3...) |
| `status` | text | `delivered`, `failed`, or `suggested` (ADR-060) |
| `draft_content` | text | LLM-generated content (markdown) |
| `final_content` | text | User-edited content (if modified before delivery) |
| `source_snapshots` | jsonb | ADR-049: Platform state + per-source `items_used` at generation time |
| `metadata` | jsonb | Execution metadata: `{input_tokens, output_tokens, model, platform_content_ids, items_fetched, sources_used, strategy}` |
| `analyst_metadata` | jsonb | ADR-060: Confidence, detected pattern, source sessions |
| `delivery_metadata` | jsonb | Delivery details (message ID, URL, delivery timestamp) |
| `created_at` | timestamptz | Generation timestamp |
| `delivered_at` | timestamptz | Delivery timestamp (NULL if failed) |

---

## Agent Origins (ADR-068, updated ADR-092)

Every agent has an `origin` field recording how it came to exist:

| Origin | Created By | Signal Source | Lifecycle |
|---|---|---|---|
| `user_configured` | User (via UI) or TP (on explicit request) | User intent | Configured first, then scheduled |
| `analyst_suggested` | Conversation Analyst (ADR-060) | TP session content (`session_messages`) | Suggested, user enables or dismisses |
| `coordinator_created` | Coordinator agent (ADR-092) | Coordinator's domain review | One-time, user reviews and optionally promotes |

**`user_configured`** — Default. The user or TP explicitly created this agent. It runs on the configured schedule or manually.

**`analyst_suggested`** (ADR-060) — The Conversation Analyst detected a recurring pattern in TP sessions. The system creates a suggested agent. The user reviews it in the UI and either enables it, edits and enables, or dismisses it. Once enabled, behaves identically to `user_configured`.

**`coordinator_created`** (ADR-092) — A coordinator agent (see Modes below) observed a signal within its configured domain and determined it warrants proactive work. The coordinator creates a one-time agent (`trigger_type=manual`) and executes it. The user reviews the output and can:
- Approve and deliver (one-time, done)
- Dismiss (archive)
- Promote to recurring (via `POST /agents/{id}/promote-to-recurring`) — `trigger_type` updates to `schedule`, `origin` stays `coordinator_created` as provenance

The `origin` field is **immutable provenance** — it records how the agent was born, not what it currently is.

> **Note on `signal_emergent`:** This value existed under ADR-068 (Signal-Emergent Agents, now superseded). Existing rows retain their value. New agents created by coordinators use `coordinator_created`. The behavior is identical — provenance vocabulary updated.

---

## Agent Modes (ADR-092)

The `mode` field defines the agent's **execution character** — how it decides when to act, what triggers it, and how its `agent_memory` accumulates. See [ADR-092](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) for full behavioral contracts and implementation phases. See [Agent Modes feature doc](../features/agent-modes.md) for user-facing framing.

| Mode | Character | Trigger | Generates when | Memory accumulates |
|------|-----------|---------|----------------|--------------------|
| `recurring` | Clockwork | Schedule (`next_run_at`) | Every scheduled run | Learned preferences, format patterns |
| `goal` | Project | Schedule (`next_run_at`) | Each run until goal complete | Goal progress, milestone tracking |
| `reactive` | On-call | Event trigger (`event_triggers.py`) | Observation threshold crossed | Agent-authored event observations |
| `proactive` | Living specialist | Slow periodic review (`proactive_next_review_at`) | Agent decides: `generate / observe / sleep` | Self-authored domain review log |
| `coordinator` | Meta-specialist | Slow periodic review (`proactive_next_review_at`) | Agent decides; also creates/advances child agents | Review log + created_agents deduplication |

**`recurring`** — The default. Fixed-cadence work products. Weekly digests, daily briefs, monthly reports.

**`goal`** — Runs until a stated objective is met. The agent writes a goal completion assessment to `agent_memory.goal` after each generation. When `status="complete"`, scheduler skips future runs. User can reopen.

**`reactive`** — Event-driven. Accumulates agent-authored observations from event triggers via `dispatch_trigger()` medium path. When `len(observations) >= threshold` (configurable, default 5), escalates to full generation and clears observations. No `next_run_at` — invisible to schedule query.

**`proactive`** — Self-initiating. Runs on a slow periodic review cadence. Headless agent reads its sources and `agent_memory`, then returns `generate`, `observe`, or `sleep`. Most review cycles result in `observe` or `sleep` — cost-efficient. The agent stays informed without being always-on.

**`coordinator`** — Meta-specialist. Same review cadence as `proactive`, but headless agent has access to two additional write primitives: `CreateAgent` (creates a child with `origin=coordinator_created`) and `AdvanceAgentSchedule` (advances another agent's `next_run_at` to now). `agent_memory.created_agents` serves as the deduplication log, replacing the former `signal_history` table.

> **Key principle:** None of these modes change how L3 is populated. Platform sync and `platform_content` operate the same way regardless of agent mode. Mode governs how L4 responds to what L3 has accumulated — not how L3 is written.

---

## Type System (ADR-044, consolidated by ADR-082)

### Active Agent Types

8 active types across 4 bindings, each anchored to a distinct moment in the user's work rhythm:

| Type | Binding | Rhythm | Purpose |
|------|---------|--------|---------|
| `slack_channel_digest` | platform_bound | daily | What happened in Slack while you were away |
| `gmail_inbox_brief` | platform_bound | daily | Prioritized inbox summary |
| `notion_page_summary` | platform_bound | daily | What changed in your docs |
| `weekly_calendar_preview` | platform_bound | weekly | Your week ahead |
| `meeting_prep` | platform_bound | reactive | Context brief for a specific upcoming meeting |
| `status_report` | cross_platform | weekly | Cross-platform synthesis — what happened this week |
| `research_brief` | research | on-demand | Web research on a topic, optionally grounded in platform data |
| `custom` | hybrid | on-demand | User-defined format with full context access |

**Deprecated types** (19 types remain in DB constraint for backwards compatibility but are not selectable in the UI):
`slack_standup`, `inbox_summary`, `reply_draft`, `follow_up_tracker`, `thread_summary`, `meeting_summary`, `one_on_one_prep`, `stakeholder_update`, `board_update`, `weekly_status`, `project_brief`, `cross_platform_digest`, `activity_summary`, `daily_strategy_reflection`, `deep_research`, `intelligence_brief`, `client_proposal`, `performance_self_assessment`, `newsletter_section`, `changelog`

See [ADR-082](../adr/ADR-082-agent-type-consolidation.md) for the consolidation rationale and what each deprecated type was absorbed into.

### Type Classification (ADR-044)

Each agent type has a `type_classification` object that determines execution behavior:

```json
{
  "binding": "platform_bound" | "cross_platform" | "research" | "hybrid",
  "primary_platform": "slack" | "gmail" | "notion" | "calendar" | null,
  "temporal_pattern": "scheduled" | "reactive" | "on_demand",
  "freshness_requirement_hours": 1 | 4 | 24
}
```

**`binding`** — Determines execution strategy (see Execution Model below)
- `platform_bound` → Single platform's `platform_content`
- `cross_platform` → All platforms' `platform_content`
- `research` → Web research via headless agent WebSearch primitive (ADR-081)
- `hybrid` → Web research + platform content

> **Note (ADR-080/081)**: All strategies gather context from `platform_content`. The agent in headless mode can supplement with primitive calls (Search, Read, List, WebSearch, GetSystemState). Research/hybrid bindings pass a research directive to the headless agent. Strategy distinction is for context gathering scope.

**`primary_platform`** — For platform-bound types, which platform to query

**`temporal_pattern`** — When the agent is valuable
- `scheduled`: Fixed cadence (daily, weekly) — most types
- `reactive`: Triggered by upcoming event (meeting_prep)
- `on_demand`: User-initiated (research_brief, custom)

**`freshness_requirement_hours`** — How stale can source data be?
- 1h: Real-time critical (meeting_prep, platform-bound daily types)
- 4h: Same-day (status_report, notion_page_summary, weekly_calendar_preview)
- 24h: On-demand (research_brief)

### Canonical Terminology (ADR-082)

| Term | Definition | Replaces |
|------|-----------|----------|
| **Binding** | How context is gathered | "Platform-Native" (ADR-031), "Platform-First" (ADR-035), "Wave" (ADR-035) |
| **Tier** | Code maturity: `stable`, `deprecated` | "Beta", "Experimental", "Wave 1/2/3" |
| **Rhythm** | When the agent is valuable: daily, weekly, reactive, on-demand | "Temporal pattern" (ADR-044) |
| **Origin** | How the agent was created | Unchanged (ADR-068) |

---

## Execution Model

**Architecture (ADR-042 + ADR-045 + ADR-080)**: The orchestration pipeline manages lifecycle (triggers, freshness, strategy, delivery, retention). Content generation is handled by the agent in **headless mode** — the same agent that powers TP chat, running with a curated subset of read-only primitives and a structured output prompt.

When a agent is due to run (scheduled, event-triggered, or manual), `execute_agent_generation()` in `agent_execution.py`:

1. Checks source freshness — skips if no new content since `last_run_at` (ADR-049)
2. Creates `agent_runs` row (status=generating) + `work_tickets` row
3. Selects execution strategy by `type_classification.binding` (ADR-045):

| Strategy | Binding | Content Source |
|----------|---------|---------------|
| `PlatformBoundStrategy` | `platform_bound` | Single platform's `platform_content` |
| `CrossPlatformStrategy` | `cross_platform` | All platforms' `platform_content` |
| `ResearchStrategy` | `research` | Optional platform grounding + research directive for headless agent (ADR-081) |
| `HybridStrategy` | `hybrid` | Platform content + research directive for headless agent (ADR-081) |

4. Strategy calls `get_content_summary_for_generation()` — chronological content dump with signal markers (`[UNANSWERED]`, `[STALLED]`, `[URGENT]`, `[DECISION]`), capped at 20 items/source, 500 chars/item
5. User memories appended from `user_memory` (fact/instruction/preference keys)
6. Learned preferences fetched from past version edit history (ADR-101: `get_past_versions_context()`)
7. `build_type_prompt()` assembles type-specific prompt from template + config + gathered context + `agent_instructions` (ADR-104: dual injection — instructions appear in both system prompt and user message)
8. **Agent (headless mode)** generates the draft via `chat_completion_with_tools()` — system prompt includes directives, memory, and learned preferences (ADR-101); read-only primitives (Search, Read, List, WebSearch, GetSystemState), binding-aware round limits (ADR-081). Research/hybrid types receive a research directive and use WebSearch for web investigation.
9. `mark_content_retained()` on consumed `platform_content` records (ADR-072)
10. `DeliveryService.deliver_version()` — email immediately (ADR-066, no approval gate)
11. `store_platform_content(platform="yarnnn")` — agent output written as searchable content (ADR-102)
12. `activity_log` event written (non-fatal)

### Content source

All content comes from `platform_content` (the unified content layer, ADR-073):
- Retained content (significant, never expires) — accumulated intelligence
- Recent ephemeral content (TTL-bounded) — fresh platform state
- yarnnn-generated content (`platform="yarnnn"`) — agent outputs from other agents (ADR-102)
- Strategy-gathered content provides the baseline; headless mode primitives provide supplementary investigation

`platform_content` is the single source, populated by platform sync (ephemeral) and marked retained by agent execution and signal processing.

### Three storage domains (ADR-107, proposed)

The architecture distinguishes three storage domains, each with its own lifecycle and access model:

| Domain | Backing Store | Scope | Lifecycle | Purpose |
|--------|--------------|-------|-----------|---------|
| **External Context** | `platform_content` table | Per-user, shared | TTL-managed (14-90d) | Raw platform data from Slack, Gmail, Notion, Calendar |
| **Agent Intelligence** | `workspace_files` under `/agents/{slug}/` | Per-agent, private | Persistent | Agent identity, memory, working state (ADR-106) |
| **Accumulated Knowledge** | `workspace_files` under `/knowledge/` | Per-user, shared | Persistent, version-aware | Agent-produced knowledge artifacts (ADR-107, proposed) |

ADR-107 proposes moving agent-produced outputs from `platform_content` (`platform="yarnnn"`) to structured files under `/knowledge/` — with content-class directories (digests/, research/, analyses/, briefs/, insights/), versioning, and provenance metadata. Outputs enter `/knowledge/` at delivery time, not generation time. See [ADR-107](../adr/ADR-107-knowledge-filesystem-architecture.md) and [Workspace Conventions](workspace-conventions.md).

### Agent in headless mode (ADR-080)

The content generation step uses the unified agent in headless mode — the same primitives TP uses in chat mode, but constrained:

| Constraint | Value | Rationale |
|---|---|---|
| Primitives | Read-only subset (Search, Read, List, WebSearch, GetSystemState) | No write operations in background jobs |
| Max tool rounds | Binding-aware: platform_bound=2, cross_platform=3, research=6, hybrid=6 (ADR-081) | Research needs room for web search + follow-up |
| Streaming | Off | No user watching |
| Session state | None | Stateless background execution |
| System prompt | Type-specific structured output + optional research directive (ADR-081) | Not TP's conversational prompt |

The agent receives gathered context from the strategy in its prompt. Primitives supplement — they don't replace — the strategy-based context gathering. Most platform-bound and cross-platform agents use 0-1 tool rounds; the gathered context is sufficient. Research/hybrid agents typically use 3-5 rounds for web search investigation (ADR-081).

---

## Lifecycle

### User-Configured Agent Lifecycle

```
User creates agent (UI or TP explicit request)
   ↓
agents row inserted (origin=user_configured, status=active, schedule set)
   ↓
unified_scheduler.py calculates next_run_at
   ↓
Scheduler reaches next_run_at → agent executes
   ↓
agent_version created (status=delivered)
   ↓
Content delivered to destination (Slack, Gmail, Notion, etc.)
   ↓
activity_log event written
   ↓
Scheduler calculates new next_run_at (for recurring agents)
```

### Analyst-Suggested Agent Lifecycle (ADR-060)

```
Conversation Analyst runs (daily cron, mines session_messages)
   ↓
Detects recurring pattern (confidence ≥ 0.60)
   ↓
agents row created (origin=analyst_suggested, status=paused)
agent_version created (status=suggested)
   ↓
User sees suggestion in UI (/agents page, "Suggested" section)
   ↓
User action:
  - Enable → status=active, next_run_at calculated
  - Edit + Enable → updated, then active
  - Dismiss → agent archived, version deleted
   ↓
If enabled: behaves identically to user_configured (scheduled execution)
```

### Coordinator-Created Agent Lifecycle (ADR-092)

Replaces the Signal-Emergent lifecycle (ADR-068, superseded). The intelligence that previously lived in L3 signal processing now lives in a coordinator agent — a user-configured specialist whose job is to watch a domain and create or trigger agents when warranted.

```
REVIEW PASS (Coordinator agent, slow periodic cadence)
────────────────────────────────────────────────────────────
Scheduler: proactive_next_review_at <= NOW()
   ↓
Agent (headless mode, review prompt):
  Reads platform_content via primitives (Search, CrossPlatformQuery, RefreshPlatformContent)
  Reads agent_memory.created_agents (deduplication log)
  Reasons over domain: "Does anything in my configured scope warrant action?"
   ↓
Agent returns one of:
  - advance_schedule(agent_id): Advance an existing agent to run now
  - create_child(type, title, sources): Create a new agent (origin=coordinator_created)
  - observe(note): Append note to agent_memory.review_log — no output
  - sleep(until): Set proactive_next_review_at to specified time — quiet period

ARTIFACT CREATION (when create_child returned)
───────────────────────────────────────────────
→ Check agent_memory.created_agents for dedup (per event_ref)
→ If not duplicate:
   → agents row created (origin=coordinator_created, trigger_type=manual)
   → Records in agent_memory.created_agents
   → Immediately executes
   → agent_version created (status=delivered)
   → Content delivered to user's configured destination

User reviews delivered output:
  - Approves → stays in history
  - Dismisses → agent archived
  - Promotes to recurring → POST /agents/{id}/promote-to-recurring
      → trigger_type=schedule, schedule set, next_run_at calculated
      → origin stays coordinator_created (immutable provenance)
```

**Key principle (ADR-092):** The coordinator is a agent — same schema, same execution model, same audit trail. Its intelligence is scoped to its `agent_instructions`. Multiple coordinators are multiple independent specialists, each accountable for their own domain.

---

## Governance Model (ADR-066)

**Current state (ADR-066)**: All agents deliver immediately. There is no staging or approval gate.

**The `governance` and `governance_ceiling` fields are DEPRECATED** (marked in Pydantic models with `deprecated=True`). They remain in the schema and API for backwards compatibility but are **ignored by all execution logic**.

When a agent executes:
- A version is created
- Content is generated
- Delivery is attempted
- Version `status` becomes `delivered` or `failed` (no `staged` state)

**Historical context**: The original governance model (ADR-028) had three levels:
- `manual` — staged for user review before delivery
- `semi_auto` — automated with notification
- `full_auto` — fully automated, no user interaction

ADR-066 removed this complexity. All agents are now effectively `full_auto` (delivery-first). Users can pause or archive agents, but there is no pre-delivery approval step.

**Deprecation path**: The `governance` field remains in the database schema and API responses for backwards compatibility. It is marked `deprecated=True` in Pydantic models (as of 2026-02-19). Plan: Remove entirely in Phase 3 cleanup (Option A per CLAUDE.md discipline: "Delete legacy code when replacing with new implementation").

**Rationale**: All agent outputs land in the user's own platforms (Slack DM, Gmail drafts, Notion pages). The user is the audience. Pre-approval adds friction without value — the user can always delete the delivered output if it's incorrect.

**Open question**: Signal-emergent agents may warrant a review-before-send gate (as originally stated in ADR-068), since they're proactive and unexpected. This is deferred to Phase 3. Current behavior: signal-emergent agents deliver immediately, same as all others.

---

## Trigger Types

| `trigger_type` | Behavior | `next_run_at` | Use Case |
|---|---|---|---|
| `schedule` | Runs on fixed schedule | Calculated from `schedule` config | `recurring` and `goal` modes |
| `event` | Runs when platform event occurs | NULL | `reactive` mode — accumulates observations via dispatch |
| `manual` | User or system triggers explicitly | NULL | One-time agents, coordinator-created (before promotion) |

**Scheduled agents**: `unified_scheduler.py` queries `agents WHERE next_run_at <= NOW()` every 5 minutes. After execution, `next_run_at` is recalculated from `schedule.frequency`.

**Event-triggered agents**: Platform webhook handler receives event, checks for agents with matching `trigger_config`, dispatches via `dispatch_trigger()` (ADR-088). For `reactive` mode, medium dispatch accumulates observations until threshold triggers generation.

**Proactive/coordinator agents**: `unified_scheduler.py` queries `agents WHERE proactive_next_review_at <= NOW()` (separate query). Invokes a review pass in headless mode. Agent returns `generate / observe / create_child / sleep` — orchestration acts accordingly.

**Manual agents**: Execute via `POST /api/agents/{id}/run` endpoint or when created by coordinator agents (immediate execution, no schedule).

---

## Deduplication & Cost Gates

### Signal Processing Cost Gate (ADR-068)

Signal processing only runs for users with active platform connections. This prevents unnecessary LLM calls for users who haven't connected any platforms.

```sql
SELECT DISTINCT user_id FROM platform_connections
WHERE status = 'active';
```

### Deduplication Rules (ADR-068)

Signal processing applies two deduplication checks:

1. **Confidence threshold**: Only create actions with `confidence ≥ 0.60`
2. **Type deduplication**: Don't create a signal-emergent agent if a user-configured agent of the same type is already scheduled to run within 24 hours
3. **Per-cycle limit**: Only one action per `agent_type` per signal processing cycle

Example: If a `meeting_prep` agent already exists and is scheduled to run today, signal processing will not create another `meeting_prep` agent for a different event. This prevents spam.

**Open question** (ADR-068): Per-signal deduplication windows — if a signal-emergent agent was created for a contact drift 2 days ago, how long before the same contact drift signal is eligible again? This is deferred to Phase 4.

---

## Source & Destination Model

### Sources

Each agent has a `sources` array:

```json
[
  {
    "platform": "slack",
    "resource_id": "C01234567",
    "resource_name": "#engineering"
  }
]
```

**Source scope**: Content is fetched from `platform_content` filtered by `(platform, resource_id)` per source, ordered by `source_timestamp DESC`, limited per source. All fetches use chronological recency.

**Targeting** (ADR-104): What the agent should *focus on* within its sources is controlled by `agent_instructions` — the single unified targeting layer. Instructions flow into both the headless system prompt (behavioral constraints) and the type prompt user message (priority lens). There are no per-source scope modes, filters, or structured targeting fields — all user intent flows through instructions.

### Destinations

Destination config (ADR-028):

```json
{
  "platform": "slack",
  "target": "D01234567",  // DM ID or channel ID
  "format": "markdown",    // markdown | html | plain
  "options": {
    "thread_reply": false,
    "unfurl_links": true
  }
}
```

**Multi-destination support** (ADR-031 Phase 6): `destinations` array allows sending the same agent to multiple targets (e.g., Slack DM + Notion page). Not yet implemented in UI, but schema supports it.

---

## Agent Intelligence Model (ADR-101)

Every agent carries four layers of knowledge:

| Layer | What it is | Storage |
|---|---|---|
| **Skills** | Type-specific format, structure, tool budget | `type_config` JSONB + type prompt templates (unchanged) |
| **Directives** | User's behavioral constraints and targeting — tone, priorities, audience, focus | `/agents/{slug}/AGENT.md` (workspace file — ADR-106 Phase 2) |
| **Memory** | What happened — observations, review decisions, goals | `/agents/{slug}/memory/*.md` (workspace files — ADR-106 Phase 2, topic-scoped) |
| **Feedback** | How well it's doing — edit patterns from user corrections | `agent_runs` metrics → `/agents/{slug}/memory/preferences.md` (future) |

> **ADR-106 Phase 2 COMPLETE:** Workspace files are the **singular source of truth** for agent intelligence. DB columns (`agent_instructions`, `agent_memory`) are no longer read or written. `AGENT.md` mirrors Claude Code's `CLAUDE.md`. `memory/` is topic-scoped (like `.claude/memory/`). `thesis.md` is YARNNN-unique — agents build self-evolving domain understanding. `ensure_seeded()` performs one-time lazy migration from DB columns on first workspace access. See [Workspace Conventions](workspace-conventions.md).

Feedback is computed by `feedback_engine.py` when users approve versions with edits, and aggregated by `get_past_versions_context()` into "learned preferences" injected into the headless system prompt. The status filter includes both `approved` and `delivered` versions (delivery-first model, ADR-066).

See [ADR-101](../adr/ADR-101-agent-intelligence-model.md) for the full model and prompt composition order.

---

## Relationship to Other Systems

| System | Relationship |
|---|---|
| **Agent (Chat Mode / TP)** | Chat mode can create `user_configured` agents on explicit user request. Content generation uses the same agent in headless mode — same primitives, different constraints (ADR-080). |
| **Backend Orchestrator** | `unified_scheduler.py` triggers due agents. `agent_execution.py` runs the strategy pipeline. Signal processing creates/triggers agents on a separate schedule. |
| **Memory (Layer 1)** | User memories (facts, instructions, preferences) are appended to the generation context but are not currently used to filter or prioritize content upstream. |
| **Activity (Layer 2)** | Each agent execution writes an `activity_log` event. Activity log is read for signal processing deduplication. |
| **Context (Layer 3)** | Agents read Context via `platform_content` (unified layer, ADR-072). TP primitives provide access. |
| **Conversation Analyst** | Creates `analyst_suggested` agents by mining TP sessions. Runs daily, produces suggestions. |
| **Coordinator Agents** | Creates `coordinator_created` agents by reviewing their configured domain. Runs on `proactive_next_review_at` cadence. (ADR-092 — replaces signal processing) |

---

## Implementation Status

**ADR-068 Signal-Emergent Agents: Phase 3+4 Complete (2026-02-20)**

Phase 3 delivered:
- Migration 071: `signal_history` table for per-signal deduplication tracking
- Migration 072: Extended `user_notification_preferences` with signal type toggles (meeting_prep, silence_alert, contact_drift)
- Migration 073: Dropped `governance` and `governance_ceiling` columns (ADR-066 cleanup)
- Per-signal deduplication logic in `signal_processing.py` with configurable windows (24h/7d/14d)
- Pydantic model cleanup — removed all governance field references

Phase 4 delivered:
- Split signal processing cron: Calendar signals (hourly), other signals (daily 7 AM)
- Gmail silence signal extraction via live Gmail API (thread history analysis)
- `signals_filter` parameter in `extract_signal_summary()` for selective signal extraction

**Status (2026-02-20):** Signal-emergent agents fully operational with hardened two-phase model.

**What works:**
- ✅ Two-phase execution (orchestration → selective artifact creation)
- ✅ Hybrid action model (trigger_existing + create_signal_emergent)
- ✅ Meeting prep agents (hourly check, 48h lookahead, calendar signals)
- ✅ Gmail silence extraction (daily check, 5+ day threshold)
- ✅ Per-signal deduplication via signal_history table
- ✅ User preferences via user_notification_preferences
- ✅ Split cron frequency (hourly/daily based on signal urgency)

**What's pending:**
- ⚠️ `silence_alert` agent type needs prompt template (extraction works, generation doesn't)
- ⚠️ `contact_drift` signal extraction not yet implemented
- ⚠️ LLM prompt updated to prioritize trigger_existing, but needs real-world testing

---

## Execution Metadata & Audit Trail

Every agent execution captures metadata across multiple storage layers, enabling both debugging and future UI surfacing:

### What's Captured

| Data | Storage Location | Populated? |
|------|-----------------|------------|
| Generated content | `agent_runs.draft_content` / `final_content` | Yes |
| Strategy used | `activity_log.metadata.strategy` | Yes |
| Token usage (input/output/model) | `agent_runs.metadata` + `activity_log.metadata` | Yes (ADR-101) |
| Source snapshots (immutable) + `items_used` | `agent_runs.source_snapshots` | Yes (items_used added for provenance) |
| Platform content IDs consumed | `agent_runs.metadata.platform_content_ids` | Yes (forward link: version→content) |
| Items fetched, sources used, strategy | `agent_runs.metadata` | Yes |
| Execution stages (started/completed/failed) | `work_execution_log` | Yes |
| Content length, sources list | `work_execution_log.metadata` | Yes |
| Delivery status/error | `agent_runs.delivery_status` / `delivery_error` | Yes |
| Delivery timestamp | `agent_runs.delivered_at` | Yes |
| Analyst confidence (suggested only) | `agent_runs.analyst_metadata` | Yes (ADR-060) |
| Platform content IDs retained (backward) | `platform_content.retained_reason` / `retained_ref` | Yes (backward link: content→version) |
| `source_fetch_summary` | `agent_runs` column | **Not populated** (schema exists) |
| `context_snapshot_id` | `agent_runs` column | **Superseded** by `metadata.platform_content_ids` |
| `pipeline_run_id` | `agent_runs` column | **Not used** (ADR-042) |

### Querying Execution History

```sql
-- Execution log for a specific version's work ticket
SELECT stage, message, metadata, timestamp
FROM work_execution_log
WHERE ticket_id = (SELECT pipeline_run_id FROM agent_runs WHERE id = '<version_id>')
ORDER BY timestamp;

-- Activity log with strategy info
SELECT metadata->>'strategy', metadata->>'final_status', created_at
FROM activity_log
WHERE event_type = 'agent_run'
  AND metadata->>'agent_id' = '<agent_id>'
ORDER BY created_at DESC;

-- Source snapshots for audit trail
SELECT source_snapshots FROM agent_runs WHERE id = '<version_id>';
```

### Frontend Surfacing (ADR-066)

The `/agents/[id]` detail page now surfaces per-version execution metadata:
- **Content**: Rendered markdown (ReactMarkdown + Tailwind typography) as the hero element
- **Per-version**: Delivery status badge, timestamp, version number, word count, token count (ADR-101), source snapshot pills
- **Delivery history**: Click version rows to switch the content area (replaces accordion)
- **Failed versions**: Error banner with `delivery_error` message and Retry button

**Not yet surfaced** (data exists in DB):
- Strategy used (`work_execution_log` / `activity_log`)
- Quality trend across versions
- Execution trace (expandable `work_execution_log` stages)

See [docs/features/email-notifications.md](../features/email-notifications.md) for the related in-app delivery channel consideration.

---

## Delivery Routing

### Current State (2026-02-24): Resend-First Email Delivery

Agent content is delivered via **Resend API** (server-side, no user OAuth required). This is the default `"email"` platform handler.

| Component | Service | Purpose |
|-----------|---------|---------|
| **Content delivery** | Resend API (`ResendExporter`) | Full agent content, HTML-formatted. Works for all users. |
| **Gmail drafts/sends** | Gmail API (`GmailExporter`) | Premium: create drafts or send as user's own address (requires Google OAuth). |
| **Status notifications** | Resend API (`send_email`) | Skipped when content was already delivered via email (same inbox). |

**Why Resend over Gmail API for default delivery:**
- Works for **all users** regardless of platform connections (no OAuth required)
- Server-side API key (no token refresh issues, no `invalid_grant` errors)
- Consistent sender: `noreply@yarnnn.com`
- Pricing: Free tier 3,000 emails/month; Pro $20/mo for 50k

**Notification email consolidation:** When the agent's destination is `platform: "email"` or `platform: "gmail"`, the content email IS the notification — the separate "Your agent is ready" notification email is skipped. Failure notifications still send regardless.

### Exporter Registry Pattern

Delivery is abstracted via the exporter registry (`api/integrations/exporters/registry.py`):

```
deliver_version() → ExporterRegistry.get_exporter(platform) → ResendExporter (platform="email", default)
                                                              → GmailExporter (platform="gmail", OAuth)
                                                              → SlackExporter
                                                              → NotionExporter
                                                              → (future: AppExporter)
```

The `ResendExporter` uses `generate_gmail_html()` for HTML formatting (same variant-aware templates as GmailExporter), then delivers via `send_email()` from `jobs/email.py`.

### Future: In-App Delivery Channel

See [docs/features/email-notifications.md — Future Consideration](../features/email-notifications.md) for documented architectural path to in-app delivery. The `destinations` array (ADR-031) supports multi-destination delivery, enabling email + in-app simultaneously.

---

## Open Questions & Future Work

1. **Event triggers** (ADR-031 Phase 4) — Platform webhook integration for real-time agent triggering (Slack mention, Gmail arrival, etc.)
2. **Contact drift signals** — Third signal type from ADR-068 (alert when key contacts haven't been contacted in N days)
3. **Multi-destination UI** — Frontend for configuring `destinations` array (currently only backend-supported)
4. **Quality-based feedback loop** — Automatic source adjustment when `quality_trend = "declining"` for N consecutive versions
5. **Signal promotion UI** — Frontend for "Promote to Recurring" button on signal-emergent agents
6. **In-app delivery channel** — `AppExporter` for richer content presentation + execution metadata surfacing (see Delivery Routing above)
7. **Populate `source_fetch_summary`** — Schema exists but execution code doesn't fill it; useful for debugging and UI

---

## Summary

Agents are YARNNN's output layer — structured, versioned, specialist agents that improve with use. They are:
- **Configured** by users (or TP on explicit request) or **created** by coordinator agents (ADR-092)
- **Mode-driven** (ADR-092) — `recurring`, `goal`, `reactive`, `proactive`, `coordinator` — each with distinct execution character
- **Intelligent** — each carries `agent_instructions` (behavioral directives) and `agent_memory` (accumulated operational knowledge) via ADR-087
- **Executed** by the backend orchestration pipeline — strategy gathers context, agent (headless mode) generates with primitive access (ADR-080)
- **Delivered** to platform destinations (email via Resend, Slack, Notion) without approval gates (ADR-066)
- **Versioned** immutably — each execution produces a permanent record
- **Type-classified** (ADR-044) to determine execution strategy
- **Origin-tagged** to record provenance: `user_configured`, `analyst_suggested`, `coordinator_created`

The agent model is the bridge between YARNNN's knowledge systems (Memory, Activity, Context) and the user's operational world. Every agent is simultaneously a configuration (what to produce), a specialist (how to produce it well), and a knowledge base (what it has learned about this work).

**Architecture note**: Content generation uses the unified agent in headless mode (ADR-080). Coordinator and proactive agents add a review pass before generation. Signal processing as a separate L3 subsystem is dissolved (ADR-092). See [Agent Execution Model](agent-execution-model.md) and [ADR-092](../adr/ADR-092-agent-intelligence-mode-taxonomy.md).
