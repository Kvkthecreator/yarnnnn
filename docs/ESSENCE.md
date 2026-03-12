# YARNNN Essence

**Purpose**: Foundation document — what YARNNN is, what it believes, how it works.
**Status**: Active
**Date**: 2026-01-28
**Updated**: 2026-03-12 (v9.0 — Agent Framework: Scope × Skill × Trigger taxonomy, ADR-109)

---

## Core Thesis

YARNNN is an **autonomous agent platform for recurring knowledge work** — persistent AI specialists with accumulated knowledge do recurring work better than any session-based alternative.

It connects to the tools where your work lives (Slack, Gmail, Notion, Calendar), accumulates knowledge of your work world over time, and deploys persistent agents that act autonomously: producing recurring output, operating as an orchestrator that already knows your world, and dispatching work before you ask for it.

**The value proposition in one sentence:**
> Persistent agents with accumulated knowledge do your recurring work — and get smarter the longer you use them.

**What makes this structurally different from every other AI tool:**
- **Persistent agents**: Each agent has its own identity, directives, memory, workspace, and execution history — sleeping specialists, not session threads
- **Perception pipeline**: Syncs continuously with Slack, Gmail, Notion, Calendar, feeding a shared knowledge base
- **Knowledge accumulation**: Every sync cycle, every edit, every execution deepens each agent's understanding — per specialist, not per conversation
- **Compounding moat**: 90 days of accumulated knowledge per specialist is irreplaceable — the system becomes more valuable with tenure

**The insight**: Most AI tools are stateless — they forget everything between sessions. The few that persist data don't act on it autonomously. YARNNN does both: accumulates knowledge AND deploys persistent agents that use it to work independently. The accumulated knowledge is what makes the autonomy meaningful rather than generic.

---

## The Supervision Model

YARNNN embodies a fundamental shift in how users relate to AI-assisted work:

**From**: User as operator (does the work, AI assists)
**To**: User as supervisor (AI does the work, user oversees)

| Dimension | First-Class Entity | User Relationship |
|-----------|-------------------|-------------------|
| **Data/Workflow** | Agents | Objects to supervise |
| **UI/Interaction** | TP (Thinking Partner) | Method of supervision |

Every screen is a supervision surface. TP is always present and interactive — not requiring navigation. Agents are always visible — not hidden behind menus.

---

## The Three Pillars

YARNNN's autonomous capability rests on three pillars, each architecturally distinct:

### 1. The Orchestrator — The Intelligent Interface

A context-aware AI agent with real-time access to accumulated knowledge. Not a chatbot — an agent with capability-based tool use (Search, FetchPlatformContent, CrossPlatformQuery), scoped to the user's work world before the first message arrives.

The orchestrator operates in two modes:
- **Chat mode** — Streaming, interactive, full capability set (15 tool rounds). Used in conversation.
- **Headless mode** — Non-streaming, background, curated read-only capabilities (3 tool rounds). Used for autonomous agent execution.

Same agent. Same intelligence. Same capability access. Different execution context.

### 2. Persistent Agents — Autonomous Specialists

Each agent is a persistent, sleeping specialist — not a template or a config. Each agent has:
- Its own **directives** — user-authored behavioral programming (how it should behave, what it prioritizes)
- Its own **workspace** — a virtual filesystem with inspectable memory, evolving domain understanding (thesis), and learned preferences
- Its own sources, schedule, output history, and execution mode

Agents are the primary expression of autonomy in YARNNN. They run on schedule, produce versioned immutable output, sleep between executions (zero resource cost), and get smarter with each run — because knowledge accumulates per specialist, not per conversation.

**The five execution modes** (how an agent decides when to act):

| Mode | Character | Execution logic |
|------|-----------|-----------------|
| `recurring` | Clockwork | Fixed schedule, always runs on time |
| `goal` | Project | Fixed schedule, stops when objective is complete |
| `reactive` | On-call | Watches source; accumulates observations; generates at threshold |
| `proactive` | Living specialist | Periodic self-review; generates when it judges conditions warrant |
| `coordinator` | Meta-specialist | Proactive + can create new agents and advance schedules for others |

Mode shapes *when* an agent acts. Directives and memory shape *how* it acts.

### 3. Knowledge Accumulation — The Moat

A perception pipeline (continuous platform sync) feeds a shared knowledge base with retention-based accumulation. Content that proves significant — referenced by an agent run, an orchestrator session, or a pattern match — is retained indefinitely. Content that isn't expires after TTL (Slack 14d, Gmail 30d, Notion 90d, Calendar 2d).

This is not "store everything" — it's "accumulate what proved significant." The knowledge base grows with every meaningful execution, creating a moat that compounds with tenure.

**The four-layer model** (Memory → Activity → Knowledge → Work):
- **Memory** (`user_memory` → migrating to workspace files): What YARNNN knows about the user — stable, explicit, user-owned. Extracted nightly from orchestrator conversations.
- **Activity** (`activity_log`): What the system has done — append-only provenance log.
- **Knowledge** (`platform_content` + workspace files): The accumulated knowledge layer — synced, retained, searchable. Agent workspaces provide inspectable, per-agent intelligence.
- **Work** (`agents`, `agent_runs`): The output layer — versioned, immutable, supervised.

**The relationship between pillars:**
- Knowledge accumulation enables meaningful autonomy (without knowledge, autonomous output is generic)
- Agents are the primary expression of autonomy (push-based, scheduled, improving)
- The orchestrator is how the user supervises and steers the autonomous system
- Each pillar reinforces the others: more agent runs → more learning → deeper knowledge → smarter orchestrator → better agents

---

## Domain Model

The product revolves around five core entities. (Previous domain model with Workspace / Project / Block / Block_Relation / Work_Ticket / Work_Output / Agent_Session is retired — see ADR-090.)

| Entity | Purpose | Key fields |
|--------|---------|------------|
| **agents** | The persistent specialist | id, user_id, title, scope, skill, mode, status, sources, schedule, trigger_config, origin |
| **agent_runs** | Immutable output record | id, agent_id, content, version_number, metadata (source_snapshots, trigger_context, generation_cost) |
| **workspace_files** | Agent workspaces + knowledge base | id, user_id, path, content, summary, embedding, tags — virtual filesystem (ADR-106) |
| **platform_content** | Accumulated knowledge layer | id, user_id, platform, resource_id, item_id, content, retained, retained_reason, expires_at |
| **user_memory** | Stable user knowledge (migrating to workspace) | id, user_id, key, value, source, confidence |
| **activity_log** | System provenance | id, user_id, event_type, metadata, created_at |

Supporting entities:
- `platform_connections` — OAuth credentials + sync preferences + selected sources
- `chat_sessions` + `session_messages` — Orchestrator conversation history (with optional `agent_id` FK for scoped sessions)
- `filesystem_documents` + `filesystem_chunks` — Uploaded documents (searchable)

**Retired entities** (ADR-090): `work_tickets`, `work_outputs` — do not reference in new code.

---

## Agent Architecture

### One Agent, Two Modes (ADR-080)

YARNNN has one agent — the orchestrator (internally "TP") — that operates in two execution contexts:

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

### The Agent as Persistent Specialist (ADR-092, ADR-103, ADR-106, ADR-109)

**Agent taxonomy** (ADR-109): Every agent is defined by two orthogonal axes — **Scope** (what it knows: platform, cross_platform, knowledge, research, autonomous) and **Skill** (what it does: digest, prepare, monitor, research, synthesize, orchestrate, act) — plus a **Trigger** (when it runs: recurring, goal, reactive, proactive, coordinator). See [Agent Framework](architecture/agent-framework.md) for the canonical reference.

Each agent is not a template or a config — it is a persistent, sleeping specialist:

| Component | Implementation | Purpose |
|-----------|---------------|---------|
| Identity | title + scope + skill | Agent name, context strategy, and work behavior |
| Directives | `agent_instructions` → `AGENT.md` workspace file | User-authored behavioral programming |
| Workspace | `workspace_files` (virtual filesystem) | Inspectable memory, thesis, working notes, references |
| Memory | `/agents/{slug}/memory/*.md` | Topic-scoped accumulated knowledge (replaces JSONB blob) |
| Sources | `sources` JSONB | Knowledge base scope |
| Schedule | `schedule` + `trigger_config` | Execution trigger |
| Output history | `agent_runs` + `/agents/{slug}/runs/` | Immutable response log |
| Capabilities | Mode-gated primitives | Available tools (+ workspace primitives for reasoning agents) |

This is why the agent is the unit of both *work* and *intelligence*. The mode shapes its execution character. The directives shape its behavior. The workspace makes it better over time — and makes its intelligence inspectable.

### Capability Registry (Mode-Gated)

Capabilities (internally "primitives") are the agent's tools. They are mode-gated — some available in both chat and headless, some chat-only, some headless-only:

| Capability | Chat | Headless | Notes |
|------------|------|----------|-------|
| Search | ✓ | ✓ | Semantic search over knowledge base |
| FetchPlatformContent | ✓ | ✓ | Fetch specific resource content |
| CrossPlatformQuery | ✓ | ✓ | Cross-platform synthesis |
| RefreshPlatformContent | ✓ | ✓ | Trigger live platform fetch |
| ReadWorkspace | ✗ | ✓ | Read from agent's workspace (ADR-106) |
| WriteWorkspace | ✗ | ✓ | Write to agent's workspace (ADR-106) |
| SearchWorkspace | ✗ | ✓ | Search within workspace (ADR-106) |
| QueryKnowledge | ✗ | ✓ | Search the shared knowledge base (ADR-106) |
| CreateAgent | ✓ | headless only (coordinator) | Coordinator write capability |
| AdvanceAgentSchedule | ✓ | headless only (coordinator) | Coordinator write capability |
| SendSlackMessage | ✓ | ✗ | Chat-only (user must confirm) |
| EditMemory | ✓ | ✗ | Chat-only (explicit user action) |

### Agent Scoped Context (ADR-087)

When an orchestrator chat session is attached to a specific agent (via `agent_id` FK on `chat_sessions`), the runtime context injected into the system prompt includes that agent's directives and workspace state. This enables the user to converse with a specialist that knows its own domain — not just the user's general profile. Instructions are edited through chat (ADR-105) — the orchestrator acknowledges, refines, and persists directive changes conversationally.

---

## Execution Architecture

### Scheduler → Dispatcher → Agent

```
Unified Scheduler (Render cron, every 5 min)
  │
  ├── recurring/goal agents:  next_run_at <= now
  │     └── _dispatch_high() → generate_draft_inline()
  │
  ├── reactive agents:        event arrives
  │     └── _dispatch_medium_reactive()
  │           ├── below threshold → write observation to agent_memory
  │           └── at threshold → _dispatch_high() → generate_draft_inline()
  │
  └── proactive/coordinator:        proactive_next_review_at <= now
        └── run_proactive_review() or run_coordinator_review()
              ├── action=observe → log to review_log, advance next_review_at
              ├── action=sleep   → advance next_review_at by specified interval
              └── action=generate → _dispatch_high() → generate_draft_inline()
                        (coordinator also: CreateAgent, AdvanceAgentSchedule)
```

### Generation Pipeline

When generation is triggered (`_dispatch_high`), the pipeline runs:
1. Strategy selection (agent type + sources → prompt strategy)
2. Source assembly (fetch relevant platform_content)
3. Headless agent execution (TP headless mode, max 3 tool rounds)
4. Version creation (immutable `agent_runs` record)
5. Retention marking (referenced platform_content marked retained)
6. Delivery (email notification if preferences set)
7. Activity logging

---

## Infrastructure

Four Render services (ADR-083 — worker + Redis removed):

| Service | Type | Role |
|---------|------|------|
| yarnnn-api | Web Service | FastAPI — chat, agents, auth, admin |
| yarnnn-unified-scheduler | Cron Job | Agent execution (all modes) |
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
- ✅ Agent execution pipeline — strategy → assembly → generation → version → delivery
- ✅ Five agent modes — recurring, goal, reactive, proactive, coordinator
- ✅ Per-agent instructions + memory (ADR-087)
- ✅ Agent-scoped TP sessions (chat attached to specific agent)
- ✅ Email notifications (Resend — agent_ready, agent_failed)
- ✅ MCP server (ADR-075 — OAuth 2.1 for Claude.ai, bearer token for Claude Desktop)
- ✅ Tier model (Free / Pro $19/mo — source limits, sync frequency, agent counts — ADR-100)
- ✅ Nightly memory extraction from orchestrator conversations
- ✅ Agent workspace architecture — virtual filesystem with inspectable per-agent intelligence (ADR-106)
- ✅ Instructions-to-chat migration — directive editing through conversational orchestrator (ADR-105)
- ✅ Unified targeting — agent_instructions as single targeting layer, dead infrastructure deleted (ADR-104)

### What's not yet built
- ❌ Agent Framework migration — Scope × Skill × Trigger taxonomy replacing 7-type system (ADR-109, docs complete, code migration pending)
- ❌ Notifications preferences UI (infrastructure complete, settings page pending)
- ❌ Session summaries writer (ADR-067 Phase 1 — currently `chat_sessions.summary` always empty)
- ❌ Review-first supervision UX (ADR-021 — primary agent view → review queue → TP inline)

---

## Product Philosophy

### Five architectural principles (from agent-model-comparison.md)

1. **The agent is the unit of work AND intelligence.** Not a template, not a config — a persistent, sleeping specialist with its own workspace, directives, and execution character.

2. **Sleep-wake architecture.** An agent that isn't running costs nothing, hallucinates nothing, and wastes nothing. Graduated response (observe → sleep → generate) is how intelligence should behave.

3. **Knowledge accumulation is moat per agent.** Not per user profile, not per conversation — per specialist. The weekly client report gets better at being a weekly client report. The competitive watch brief gets better at watching competition.

4. **Graduated response preserves the task foundation.** Reactive and proactive modes don't generate on every event — they observe, accumulate, and decide. This keeps output meaningful and cost-efficient.

5. **Orchestration stays outside the agent.** The scheduler decides when to trigger. The pipeline handles source assembly, delivery, and retention. The agent generates output. These concerns don't mix.

6. **Agent intelligence must be inspectable.** Users browse workspace files to understand what an agent knows. Debug by reading, not querying. Transparency builds trust in autonomous systems.

### What we're not building (current)

| Feature | Why not yet |
|---------|-------------|
| Multi-workspace / team collaboration | Single-user is the ICP; team features add governance complexity without current demand |
| Automated delivery (Slack send, email send without review) | Supervision model requires review before external delivery |
| Billing / subscriptions | Pre-PMF |
| Agent marketplace / shareable agents | No community yet |
| Full A2A coordination | Coordinator mode is the first step; full agent-to-agent is the roadmap vision |

---

## Key File Locations

| Concern | Location |
|---------|----------|
| Orchestrator agent + system prompt | `api/agents/thinking_partner.py` |
| Capability registry | `api/services/primitives/registry.py` |
| Coordinator primitives | `api/services/primitives/coordinator.py` |
| Agent execution pipeline | `api/services/agent_execution.py` |
| Unified scheduler (all modes) | `api/jobs/unified_scheduler.py` |
| Proactive review | `api/services/proactive_review.py` |
| Reactive dispatch | `api/services/trigger_dispatch.py` |
| Platform sync worker | `api/workers/platform_worker.py` |
| Platform sync scheduler | `api/jobs/platform_sync_scheduler.py` |
| Runtime context builder | `api/services/working_memory.py` |
| Agent workspace | `api/services/workspace.py` |
| Memory extraction (nightly) | `api/services/memory.py` |
| Agent routes | `api/routes/agents.py` |
| Frontend API client | `web/lib/api/client.ts` |

---

*This document is the current specification. For decision history, see `docs/adr/`. For GTM language and positioning, see `docs/working_docs/strategy/GTM_POSITIONING.md`. For narrative sequencing, see `docs/NARRATIVE.md`. For terminology conventions, see ADR-103.*
