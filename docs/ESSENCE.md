# YARNNN Essence

**Purpose**: Foundation document — what YARNNN is, what it believes, how it works.
**Status**: Active
**Date**: 2026-01-28
**Updated**: 2026-03-04 (v7.0 — reflects ADR-080, ADR-087, ADR-090, ADR-092)

---

## Core Thesis

YARNNN is an **autonomous AI agent platform** — powered by accumulated context from your real work platforms.

It connects to the tools where your work lives (Slack, Gmail, Notion, Calendar), accumulates understanding of your work world over time, and uses that context to act autonomously: producing deliverables, operating as a thinking partner that already knows your world, and dispatching work before you ask for it.

**The value proposition in one sentence:**
> AI that works autonomously on your behalf — and gets smarter the longer you use it, because it accumulates context from your actual work.

**What makes this structurally different from every other AI tool:**
- **Autonomous output**: Produces work (reports, digests, briefs) on schedule without prompting
- **Persistent context**: Syncs continuously with Slack, Gmail, Notion, Calendar
- **Accumulated intelligence**: Every sync cycle, every edit, every interaction deepens the system's understanding — per deliverable, not per conversation
- **Compounding moat**: 90 days of accumulated context per specialist is irreplaceable — the system becomes more valuable with tenure

**The insight**: Most AI tools are stateless — they forget everything between sessions. The few that persist data don't act on it autonomously. YARNNN does both: accumulates context AND uses it to work independently. The accumulated context is what makes the autonomy meaningful rather than generic.

---

## The Supervision Model

YARNNN embodies a fundamental shift in how users relate to AI-assisted work:

**From**: User as operator (does the work, AI assists)
**To**: User as supervisor (AI does the work, user oversees)

| Dimension | First-Class Entity | User Relationship |
|-----------|-------------------|-------------------|
| **Data/Workflow** | Deliverables | Objects to supervise |
| **UI/Interaction** | TP (Thinking Partner) | Method of supervision |

Every screen is a supervision surface. TP is always present and interactive — not requiring navigation. Deliverables are always visible — not hidden behind menus.

---

## The Three Pillars

YARNNN's autonomous capability rests on three pillars, each architecturally distinct:

### 1. Thinking Partner (TP) — The Intelligent Interface

A context-aware AI agent with real-time access to accumulated platform context. Not a chatbot — an agent with primitive-based tool use (Search, FetchPlatformContent, CrossPlatformQuery), scoped to the user's work world before the first message arrives.

TP operates in two modes:
- **Chat mode** — Streaming, interactive, full primitive set (15 tool rounds). Used in conversation.
- **Headless mode** — Non-streaming, background, curated read-only primitives (3 tool rounds). Used for autonomous deliverable generation.

Same agent. Same intelligence. Same primitive access. Different execution context.

### 2. Deliverables — Autonomous Output

Scheduled, autonomous work artifacts — each one a purpose-built specialist. Each deliverable has:
- Its own `deliverable_instructions` — user-authored behavioral directive (how it should behave, what it prioritizes)
- Its own `deliverable_memory` — system-accumulated knowledge (what it has learned from every execution)
- Its own sources, schedule, output history, and execution mode

Deliverables are the primary expression of autonomy in YARNNN. They run on schedule, produce versioned immutable output, sleep between executions (zero resource cost), and get smarter with each run — because memory accumulates per specialist, not per conversation.

**The five execution modes** (how a deliverable decides when to act):

| Mode | Character | Execution logic |
|------|-----------|-----------------|
| `recurring` | Clockwork | Fixed schedule, always runs on time |
| `goal` | Project | Fixed schedule, stops when objective is complete |
| `reactive` | On-call | Watches source; accumulates observations; generates at threshold |
| `proactive` | Living specialist | Periodic self-review; generates when it judges conditions warrant |
| `coordinator` | Meta-specialist | Proactive + can create new deliverables and advance schedules for others |

Mode shapes *when* a deliverable acts. Instructions and memory shape *how* it acts.

### 3. Context Accumulation — The Moat

Continuous platform sync feeds a unified content layer (`platform_content`) with retention-based accumulation. Content that proves significant — referenced by a deliverable run, a TP session, or a pattern match — is retained indefinitely. Content that isn't expires after TTL (Slack 14d, Gmail 30d, Notion 90d, Calendar 2d).

This is not "store everything" — it's "accumulate what proved significant." The accumulated corpus grows with every meaningful execution, creating a moat that compounds with tenure.

**The four-layer model** (Memory → Activity → Context → Work):
- **Memory** (`user_memory`): What YARNNN knows about the user — stable, explicit, user-owned. Extracted nightly from TP conversations.
- **Activity** (`activity_log`): What the system has done — append-only provenance log.
- **Context** (`platform_content`): The accumulated content layer — synced, retained, searchable.
- **Work** (`deliverables`, `deliverable_versions`): The output layer — versioned, immutable, supervised.

**The relationship between pillars:**
- Context accumulation enables meaningful autonomy (without context, autonomous output is generic)
- Deliverables are the primary expression of autonomy (push-based, scheduled, improving)
- TP is how the user supervises and steers the autonomous system
- Each pillar reinforces the others: more deliverable runs → more learning → better context → smarter TP → better deliverables

---

## Domain Model

The product revolves around five core entities. (Previous domain model with Workspace / Project / Block / Block_Relation / Work_Ticket / Work_Output / Agent_Session is retired — see ADR-090.)

| Entity | Purpose | Key fields |
|--------|---------|------------|
| **deliverables** | The autonomous specialist | id, user_id, title, deliverable_type, mode, status, sources, schedule, trigger_config, deliverable_instructions, deliverable_memory, origin |
| **deliverable_versions** | Immutable output record | id, deliverable_id, content, version_number, metadata (source_snapshots, trigger_context, generation_cost) |
| **platform_content** | Accumulated context layer | id, user_id, platform, resource_id, item_id, content, retained, retained_reason, expires_at |
| **user_memory** | Stable user knowledge | id, user_id, key, value, source, confidence |
| **activity_log** | System provenance | id, user_id, event_type, metadata, created_at |

Supporting entities:
- `platform_connections` — OAuth credentials + sync preferences + selected sources
- `chat_sessions` + `session_messages` — TP conversation history (with optional `deliverable_id` FK for scoped sessions)
- `filesystem_documents` + `filesystem_chunks` — Uploaded documents (searchable)

**Retired entities** (ADR-090): `work_tickets`, `work_outputs` — do not reference in new code.

---

## Agent Architecture

### One Agent, Two Modes (ADR-080)

YARNNN has one agent — TP — that operates in two execution contexts:

```
Chat Mode (interactive)              Headless Mode (background)
─────────────────────────            ──────────────────────────
Entry: /api/chat                     Entry: generate_draft_inline()
Streaming: yes                       Streaming: no
Tool rounds: 15                      Tool rounds: 3
Primitives: full set                 Primitives: read-only subset
User: conversational                 User: supervisor reviewing output
```

The boundary is preserved: backend orchestration (scheduler, strategy, delivery, retention) stays outside the agent. The agent is invoked at the generation step and returns text.

### The Deliverable as Lightweight Agent (ADR-092, agent-model-comparison.md)

Each deliverable is not a template or a config — it is a purpose-built specialist agent:

| Component | Deliverable field | Agent equivalent |
|-----------|------------------|-----------------|
| Identity | title + deliverable_type | Agent name + role |
| Instructions | `deliverable_instructions` | System prompt behavioral directive |
| Memory | `deliverable_memory` | Accumulated execution knowledge |
| Sources | `sources` JSONB | Context scope |
| Schedule | `schedule` + `trigger_config` | Execution trigger |
| Output history | `deliverable_versions` | Immutable response log |
| Capabilities | Mode-gated primitives | Available tools |

This is why the deliverable is the unit of both *work* and *intelligence*. The mode shapes its execution character. The instructions shape its behavior. The memory makes it better over time.

### Primitive Registry (Mode-Gated)

Primitives are the agent's tools. They are mode-gated — some available in both chat and headless, some chat-only, some headless-only:

| Primitive | Chat | Headless | Notes |
|-----------|------|----------|-------|
| Search | ✓ | ✓ | Semantic search over platform_content |
| FetchPlatformContent | ✓ | ✓ | Fetch specific resource content |
| CrossPlatformQuery | ✓ | ✓ | Cross-platform synthesis |
| RefreshPlatformContent | ✓ | ✓ | Trigger live platform fetch |
| CreateDeliverable | ✓ | headless only (coordinator) | Coordinator write primitive |
| AdvanceDeliverableSchedule | ✓ | headless only (coordinator) | Coordinator write primitive |
| SendSlackMessage | ✓ | ✗ | Chat-only (user must confirm) |
| EditMemory | ✓ | ✗ | Chat-only (explicit user action) |

### Deliverable Scoped Context (ADR-087)

When a TP chat session is attached to a specific deliverable (via `deliverable_id` FK on `chat_sessions`), the working memory injected into the system prompt includes that deliverable's `deliverable_instructions` and `deliverable_memory`. This enables the user to converse with a specialist that knows its own domain — not just the user's general profile.

---

## Execution Architecture

### Scheduler → Dispatcher → Agent

```
Unified Scheduler (Render cron, every 5 min)
  │
  ├── recurring/goal deliverables:  next_run_at <= now
  │     └── _dispatch_high() → generate_draft_inline()
  │
  ├── reactive deliverables:        event arrives
  │     └── _dispatch_medium_reactive()
  │           ├── below threshold → write observation to deliverable_memory
  │           └── at threshold → _dispatch_high() → generate_draft_inline()
  │
  └── proactive/coordinator:        proactive_next_review_at <= now
        └── run_proactive_review() or run_coordinator_review()
              ├── action=observe → log to review_log, advance next_review_at
              ├── action=sleep   → advance next_review_at by specified interval
              └── action=generate → _dispatch_high() → generate_draft_inline()
                        (coordinator also: CreateDeliverable, AdvanceDeliverableSchedule)
```

### Generation Pipeline

When generation is triggered (`_dispatch_high`), the pipeline runs:
1. Strategy selection (deliverable type + sources → prompt strategy)
2. Source assembly (fetch relevant platform_content)
3. Headless agent execution (TP headless mode, max 3 tool rounds)
4. Version creation (immutable `deliverable_versions` record)
5. Retention marking (referenced platform_content marked retained)
6. Delivery (email notification if preferences set)
7. Activity logging

---

## Infrastructure

Four Render services (ADR-083 — worker + Redis removed):

| Service | Type | Role |
|---------|------|------|
| yarnnn-api | Web Service | FastAPI — chat, deliverables, auth, admin |
| yarnnn-unified-scheduler | Cron Job | Deliverable execution (all modes) |
| yarnnn-platform-sync | Cron Job | Platform content sync (all platforms) |
| yarnnn-mcp-server | Web Service | MCP protocol for Claude.ai / Claude Code |

All execution is inline — no background worker, no Redis, no queue. Platform sync runs in crons; on-demand sync uses FastAPI BackgroundTasks.

**Shared env vars** (must be set on API + both Schedulers):
- `INTEGRATION_ENCRYPTION_KEY` — Fernet key for OAuth token decryption
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
- `NOTION_CLIENT_ID` / `NOTION_CLIENT_SECRET`

**Platform API clients** (ADR-076 — Direct API, no gateway):
- `api/integrations/core/slack_client.py` (SlackAPIClient)
- `api/integrations/core/google_client.py` (GoogleAPIClient — Gmail + Calendar)
- `api/integrations/core/notion_client.py` (NotionAPIClient)

---

## Current State

### What's live and working
- ✅ Four-platform sync (Slack, Gmail, Notion, Calendar) — paginated, TTL-based, retention-aware
- ✅ Unified content layer (`platform_content`) with accumulation moat
- ✅ TP agent — chat mode with full primitive set, streaming, scoped to user context
- ✅ Headless agent — non-streaming generation with curated primitives
- ✅ Deliverable execution pipeline — strategy → assembly → generation → version → delivery
- ✅ Five deliverable modes — recurring, goal, reactive, proactive, coordinator
- ✅ Per-deliverable instructions + memory (ADR-087)
- ✅ Deliverable-scoped TP sessions (chat attached to specific deliverable)
- ✅ Email notifications (Resend — deliverable_ready, deliverable_failed)
- ✅ MCP server (ADR-075 — OAuth 2.1 for Claude.ai, bearer token for Claude Desktop)
- ✅ Tier model (Free / Starter / Pro — source limits, sync frequency, deliverable counts)
- ✅ Nightly memory extraction from TP conversations

### What's not yet built
- ❌ Notifications preferences UI (infrastructure complete, settings page pending)
- ❌ Deliverable type taxonomy revision (current 8 types predate mode system — scheduled)
- ❌ `work_tickets` / `work_outputs` table drop (ADR-090 Phase 4 — post-migration period)
- ❌ Session summaries writer (ADR-067 Phase 1 — currently `chat_sessions.summary` always empty)
- ❌ Review-first supervision UX (ADR-021 — primary deliverable view → review queue → TP inline)

---

## Product Philosophy

### Five architectural principles (from agent-model-comparison.md)

1. **Deliverable is the unit of work AND intelligence.** Not a template, not a config — a sleeping specialist with its own memory, instructions, and execution character.

2. **Sleep is a feature.** A deliverable that isn't running costs nothing, hallucinates nothing, and wastes nothing. Graduated response (observe → sleep → generate) is how intelligence should behave.

3. **Accumulation is moat per deliverable.** Not per user profile, not per conversation — per specialist. The weekly client report gets better at being a weekly client report. The competitive watch brief gets better at watching competition.

4. **Graduated response preserves the task foundation.** Reactive and proactive modes don't generate on every event — they observe, accumulate, and decide. This keeps output meaningful and cost-efficient.

5. **Orchestration stays outside the agent.** The scheduler decides when to trigger. The pipeline handles source assembly, delivery, and retention. The agent generates text. These concerns don't mix.

### What we're not building (current)

| Feature | Why not yet |
|---------|-------------|
| Multi-workspace / team collaboration | Single-user is the ICP; team features add governance complexity without current demand |
| Automated delivery (Slack send, email send without review) | Supervision model requires review before external delivery |
| Billing / subscriptions | Pre-PMF |
| Agent marketplace / shareable deliverables | No community yet |
| Full A2A coordination | Coordinator mode is the first step; full agent-to-agent is the roadmap vision |

---

## Key File Locations

| Concern | Location |
|---------|----------|
| TP Agent + system prompt | `api/agents/thinking_partner.py` |
| Primitive registry | `api/services/primitives/registry.py` |
| Coordinator primitives | `api/services/primitives/coordinator.py` |
| Deliverable execution pipeline | `api/services/deliverable_execution.py` |
| Unified scheduler (all modes) | `api/jobs/unified_scheduler.py` |
| Proactive review | `api/services/proactive_review.py` |
| Reactive dispatch | `api/services/trigger_dispatch.py` |
| Platform sync worker | `api/workers/platform_worker.py` |
| Platform sync scheduler | `api/jobs/platform_sync_scheduler.py` |
| Working memory builder | `api/services/working_memory.py` |
| Memory extraction (nightly) | `api/services/memory.py` |
| Deliverable routes | `api/routes/deliverables.py` |
| Frontend API client | `web/lib/api/client.ts` |

---

*This document is the current specification. For decision history, see `docs/adr/`. For GTM language and positioning, see `docs/GTM_POSITIONING.md`. For narrative sequencing, see `docs/NARRATIVE.md`.*
