# Backend Orchestration Pipeline

**Version**: 4.0
**Last updated**: 2026-03-06 (ADR-090: work_tickets removed, ADR-092: signal processing dissolved)
**Status**: Hardened — canonical reference for all background processing. Cross-validated against code.

---

## Overview

YARNNN's backend runs 4 Render services sharing a single codebase (ADR-083: worker + Redis removed):

| # | Service | Render ID | Type | Schedule | Role |
|---|---------|-----------|------|----------|------|
| 1 | `yarnnn-api` | `srv-d5sqotcr85hc73dpkqdg` | Web Service | Always-on | API endpoints, OAuth, manual triggers |
| 2 | `yarnnn-unified-scheduler` | `crn-d604uqili9vc73ankvag` | Cron Job | `*/5 * * * *` | Agents, memory, cleanup |
| 3 | `yarnnn-platform-sync` | `crn-d6gdvi94tr6s73b6btm0` | Cron Job | `*/5 * * * *` | Platform sync scheduling |
| 4 | `yarnnn-mcp-server` | `srv-d6f4vg1drdic739nli4g` | Web Service | Always-on | MCP server for Claude.ai/Desktop (ADR-075) |

All execution is inline — no background worker, no Redis. On-demand operations use FastAPI BackgroundTasks or direct calls.

### Pipeline Flow

```
External APIs ──[F1: Sync]──→ platform_content ──→ agents
                                                        │
                                               [F3: Execution]
                                                        │
                                                        ▼
                                               agent_runs
                                                        │
                                               [F3: Delivery]
                                                        ▼
                                               Email / Slack
                                 ┌──────────────────────┘
                                 │ (content marked retained)
chat_sessions ──[F4: Memory]──→ user_memory ──→ injected into TP
                                 │
activity_log ◄── ALL features ──┘
```

---

## Feature Map

Background features, each with a unique ID for cross-referencing. F2 (Signal Processing), F5 (Conversation Analysis), and F10 (Work Tickets) have been removed.

| ID | Feature | Frequency | LLM? | Cost Driver | Service |
|----|---------|-----------|------|-------------|---------|
| F1 | Platform Sync | Tier-gated (2x/4x/hourly) | No | Platform API reads | platform-sync cron |
| ~~F2~~ | ~~Signal Processing~~ | ~~Removed (ADR-092)~~ | — | — | — |
| F3 | Agent Execution | Every 5 min (due check) | Sonnet | ~2-5k tokens/run | unified-scheduler |
| F4 | Memory Extraction | Daily 00:00 UTC | Sonnet | ~1-2k tokens/user | unified-scheduler |
| ~~F5~~ | ~~Conversation Analysis~~ | ~~Removed~~ | — | — | — |
| F6 | Content Cleanup | Hourly | No | DB deletes | unified-scheduler |
| F7 | Weekly Digest | Weekly per user | No | Email send | unified-scheduler |
| F8 | Import Jobs | Every 5 min | No | Platform API reads | unified-scheduler |
| F9 | Embedding Generation | **NOT IMPLEMENTED** | No | OpenAI API (~$0.02/M tokens) | — |
| ~~F10~~ | ~~Work Ticket Processing~~ | ~~Removed (ADR-090)~~ | — | — | — |

### Feature Dependencies

```
F1 (Sync) ──writes──→ platform_content ──read by──→ F3 (Execution)
                                                      │
F4 (Memory) ──writes──→ user_memory ──read by──→ F3
F6 (Cleanup) ──deletes──→ platform_content (expired, non-retained)
F9 (Embeddings) ──would write──→ platform_content.content_embedding
```

---

## F1: Platform Sync

**Files**: `api/workers/platform_worker.py`, `api/jobs/platform_sync_scheduler.py`
**Entry points**: Platform sync cron (scheduled), `POST /integrations/{provider}/sync` (manual)
**ADRs**: ADR-053 (tier gating), ADR-056 (per-source), ADR-073 (cursors), ADR-077 (pagination), ADR-079 (auto-selection)

**This is the ONLY feature that calls external platform APIs.** Everything else reads `platform_content`.

### Scheduling

The `platform_sync_scheduler.py` cron runs every 5 minutes and checks:
1. Which users have connected platforms (status `connected` or `active`)
2. Whether the user's tier-based schedule says "sync now" (`should_sync_now()`)
3. Whether enough time has passed since last sync (`_needs_sync()` with min intervals)

Sync is invoked **inline** — `sync_platform()` runs synchronously within the cron process. On-demand user sync uses FastAPI BackgroundTasks (ADR-083).

| Tier | Frequency | Min Interval | Schedule |
|------|-----------|-------------|----------|
| Free | 2x/day | 6 hours | 8am + 6pm user timezone |
| Starter | 4x/day | 4 hours | Every 6 hours |
| Pro | Hourly | 45 minutes | Top of each hour |

### Per-Platform Details

| Platform | Client | Initial Cap | Incremental Cap | Rate Limit | Key Feature |
|----------|--------|-------------|----------------|------------|-------------|
| Slack | `SlackAPIClient` | 1000 msgs/ch | 500 msgs/ch | Retry on 429 | Thread expansion (max 20/ch), user resolution, system msg filtering |
| Gmail | `GoogleAPIClient` | 200 msgs/label | Date-filtered | Semaphore(10) | Concurrent message fetch, base64 payload decode |
| Notion | `NotionAPIClient` | 500 blocks/page | Skip if unchanged | **350ms/call** | Recursive blocks (depth 3), database query (100 rows × 3 pages) |
| Calendar | `GoogleAPIClient` | -7d to +14d | syncToken | None | All calendars (unlimited tier) |

### Storage

Each item → `_store_platform_content()`:
- `retained=False` (ephemeral by default)
- TTL: Slack 14d, Gmail 30d, Notion 90d, Calendar 2d
- Content-hash dedup (SHA-256, upsert on `content_hash`)
- Per-resource errors written to `sync_registry.last_error` on failure, cleared on success

### Performance (wall clock estimates)

| Tier | Sources | First Sync | Incremental |
|------|---------|-----------|------------|
| Free | 5+5+10+cals | ~40-50 sec | ~20 sec |
| Starter | 15+10+25+cals | ~70-80 sec (pages) | ~50 sec |
| Starter (with Notion DBs) | same | **10+ min** | ~2-3 min |
| Pro | 50+30+50+cals | ~3 min (pages) | ~90 sec |

**Bottleneck**: Notion databases — 350ms rate limit × up to 300 rows per database.

### Tables

| Reads | Writes |
|-------|--------|
| `platform_connections` (landscape, selected_sources) | `platform_content` (upsert) |
| `sync_registry` (cursors) | `sync_registry` (cursor + timestamp + error) |
| | `activity_log` (platform_synced) |

---

## ~~F2: Signal Processing~~ — Removed (ADR-092)

Signal processing was dissolved in ADR-092. Its responsibilities were absorbed into:
- **Coordinator agents** (mode=coordinator) — manage child agent lifecycles
- **Trigger dispatch** (`api/services/trigger_dispatch.py`, ADR-088) — unified trigger routing

Files deleted: `signal_extraction.py`, `signal_processing.py`, routes, scheduler phases, `signal_history` table.

---

## F3: Agent Execution

**Files**: `api/services/agent_execution.py`, `api/services/agent_pipeline.py`
**Entry points**: Unified scheduler (every 5 min), `POST /agents/{id}/run`
**ADRs**: ADR-042 (simplified), ADR-049 (freshness), ADR-066 (delivery-first), ADR-072 (retention), ADR-080 (headless mode), ADR-082 (8 active types)
**LLM**: `claude-sonnet-4-20250514` (agent in headless mode)
**Tier gate**: Active agent count limited (Free: 2, Starter: 5, Pro: unlimited)

### Flow

1. Freshness check — skip if no new content since `last_run_at` (ADR-049)
2. Create `agent_runs` (generating)
3. Select strategy by `type_classification.binding`:

| Strategy | Content Source |
|----------|--------------|
| `platform_bound` | Single platform's `platform_content` |
| `cross_platform` | All platforms |
| `research` | Optional platform grounding + research directive (ADR-081) |
| `hybrid` | Platform content + research directive (ADR-081) |

4. Agent (headless mode, ADR-080/081) generates via `chat_completion_with_tools()` — read-only primitives (Search, Read, List, WebSearch, GetSystemState), binding-aware tool rounds (2-6)
5. `mark_content_retained()` on consumed content (ADR-072)
6. Record `source_snapshots` (ADR-049)
7. `DeliveryService.deliver_version()` — email immediately (ADR-066, no approval gate)

### Tables

| Reads | Writes |
|-------|--------|
| `agents`, `platform_content` | `agent_runs` |
| `sync_registry` (freshness) | `platform_content` (retained=true) |
| `agent_runs` (versioning) | `source_snapshots`, `activity_log` |

---

## F4: Memory Extraction

**File**: `api/services/memory.py`
**Entry point**: Unified scheduler at 00:00 UTC
**ADRs**: ADR-064 (implicit memory), ADR-067 (session continuity)
**LLM**: `claude-sonnet-4-20250514`

Memory is fully implicit — TP has no explicit memory tools.

### Three Write Paths

| Path | Input | Output | LLM? |
|------|-------|--------|------|
| Conversation extraction | Yesterday's `chat_sessions` (≥3 user msgs) | `user_memory` entries | Yes (Sonnet) |
| Session summaries | Sessions with ≥5 user messages | `chat_sessions.summary` | Yes (Sonnet) |
| Activity patterns | 30 days of `activity_log` | `user_memory` (confidence 0.6) | No (rule-based) |

Source priority for `user_memory`: `user_stated > conversation > feedback > pattern`

### Tables

| Reads | Writes |
|-------|--------|
| `chat_sessions`, `session_messages` | `user_memory` |
| `activity_log`, `user_memory` | `chat_sessions` (summary) |
| | `activity_log` (memory_written) |

---

## ~~F5: Conversation Analysis~~ — Removed

`api/services/conversation_analysis.py` was deleted. Agent suggestions are now handled through TP conversation (user-driven) and coordinator agents (automated).

---

## F6: Content Cleanup

**File**: `api/services/platform_content.py`
**Entry point**: Unified scheduler (hourly)
**ADR**: ADR-072 (retention model)

Deletes expired non-retained content: `DELETE FROM platform_content WHERE retained=false AND expires_at < now`

Writes `content_cleanup` events to `activity_log` per user.

---

## F7: Import Jobs

**File**: `api/jobs/import_jobs.py`
**Entry point**: Unified scheduler (every 5 min)

1. Recover stale processing jobs (stuck >10 min)
2. Process pending `integration_import_jobs` (limit 10)
3. Used for on-demand source imports from context page

---

## F8: Embedding Generation (NOT IMPLEMENTED)

**Infrastructure exists but is not wired into the pipeline.**

| Component | Status | File |
|-----------|--------|------|
| `content_embedding vector(1536)` column on `platform_content` | Exists (migration 077) | — |
| `embeddings.py` — OpenAI `text-embedding-3-small` | Exists, functional | `api/services/embeddings.py` |
| `get_embeddings_batch()` — batch API call | Exists, functional | `api/services/embeddings.py` |
| `search_platform_content()` SQL function | Supports vector + text search | migration 077 |
| TP Search primitive | Calls `search_platform_content()` | `api/services/primitives/search.py` |
| **Background embedding generation** | **Missing** | — |

**Gap**: Platform content is stored without embeddings at sync time. The `search_platform_content()` SQL function supports vector similarity search, but since `content_embedding` is never populated, semantic search always falls back to text matching.

**To implement**: Add a post-sync phase that generates embeddings for `platform_content` rows where `content_embedding IS NULL`. Batch via `get_embeddings_batch()` to minimize API calls. Could run:
- Inline after sync (adds latency to sync)
- As a separate hourly phase in unified scheduler (decoupled, preferred)
- On-demand when TP Search is invoked (lazy, but adds latency to chat)

**Cost estimate**: OpenAI `text-embedding-3-small` = ~$0.02 per 1M tokens. 300 items × ~500 tokens avg = 150k tokens = ~$0.003 per full sync. Negligible.

---

## ~~F10: Work Ticket Processing~~ — Removed (ADR-090)

Work ticket processing was removed in ADR-090 Phase 1. Agent execution (F3) is the only execution path.
Files deleted: `work_execution.py`, `agents/factory.py`, `agents/agent.py`, `routes/work.py`, `routes/agents.py`.

---

## Unified Scheduler — Phase Map

**File**: `api/jobs/unified_scheduler.py`
**Render cron**: `*/5 * * * *`, `cd api && python -m jobs.unified_scheduler`

| Phase | Frequency | Gate | Feature |
|-------|-----------|------|---------|
| Agents | Every 5 min | `next_pulse_at <= now` | F3 |
| Import Jobs | Every 5 min | Pending jobs exist | F8 |
| Content Cleanup | Hourly (`minute < 5`) | Always | F6 |
| Weekly Digests | Hourly (`minute < 5`) | Day + hour + tz match | F7 |
| Memory Extraction | Daily (`hour == 0, minute < 5`) | Always | F4 |
| Activity Patterns | Daily (`hour == 0, minute < 5`) | Always | F4 |
| Heartbeat | Every 5 min | Always | Observability |

> **ADR-126 Note**: The scheduler is now a **pulse dispatcher**. Each agent gets its turn to pulse (`next_pulse_at <= now`), and the agent's pulse decides whether to generate, observe, wait, or escalate. The scheduler acts on the decision — it no longer owns the generate decision itself. See `api/services/agent_pulse.py` and [SCHEDULER-EVOLUTION.md](../design/SCHEDULER-EVOLUTION.md).

---

## Observability

### activity_log — Central Nervous System

| Event Type | Writer | Feature |
|-----------|--------|---------|
| `platform_synced` | `platform_worker.py` | F1 |
| `agent_run` | `agent_execution.py` | F3 |
| `agent_approved` / `rejected` | `routes/agents.py` | User action |
| `agent_scheduled` | `unified_scheduler.py` | F3 |
| `agent_bootstrapped` | `onboarding_bootstrap.py` | ADR-110 |
| `memory_written` | `memory.py` | F4 |
| `session_summary_written` | `memory.py` | F4 |
| `content_cleanup` | `unified_scheduler.py` | F6 |
| `integration_connected` / `disconnected` | `routes/integrations.py` | OAuth |
| `chat_session` | `chat.py` | User action |
| `scheduler_heartbeat` | `unified_scheduler.py` | Observability |

### Consumers

| Consumer | File | What it reads | Purpose |
|----------|------|--------------|---------|
| Working memory | `working_memory.py` | Last 10 events (7-day) | TP system prompt injection |
| System status | `routes/system.py` | Job status per type | Background activity page |
| Pattern detection | `memory.py` | 30-day events | Behavioral analysis |
| TP primitive | `primitives/system_state.py` | Current state | `GetSystemState` tool |

### System Status Endpoint

`GET /api/system/status` — pure read, writes nothing.
Reads: `workspaces` (tier), `platform_connections`, `sync_registry` (incl. `last_error`, `last_error_at`), `platform_content` (counts), `activity_log` (job status).

---

## LLM Usage

| Model | Feature | Purpose | Cost/Call |
|-------|---------|---------|-----------|
| `claude-sonnet-4-20250514` | F3 Agent Execution | Agent headless mode (ADR-080/081) — draft generation + binding-aware tool rounds (2-6). Research types use WebSearch primitive (nested Sonnet call). | ~2-12k tokens |
| `claude-sonnet-4-20250514` | F4 Memory Extraction | Fact extraction | ~1-2k tokens |
| `claude-sonnet-4-20250514` | F4 Session Summaries | Cross-session continuity | ~1k tokens |
| `text-embedding-3-small` | F9 Embeddings (not impl.) | Semantic search | ~$0.003/sync |

---

## Database Tables

| Table | Layer | Written by | Read by |
|-------|-------|-----------|---------|
| `platform_content` | Context | F1 Sync, F3 (retained flag), F6 (cleanup) | F3 Execution, TP Search |
| `sync_registry` | Context | F1 Sync | F3 Freshness, System status |
| `platform_connections` | Context | F1 Sync, OAuth | F1, System status |
| `agents` | Work | User, Coordinator | F3 Execution |
| `agent_runs` | Work | F3 Execution | User review |
| `user_memory` | Memory | F4 Memory, User edits | TP, Working memory |
| `activity_log` | Activity | ALL features | Working memory, F4, System status |
| `chat_sessions` | Activity | Chat endpoints, F4 (summary) | F4 |
| `session_messages` | Activity | Chat endpoints | F4 |

---

## Manual Trigger Paths

| Endpoint | Feature | Notes |
|----------|---------|-------|
| `POST /integrations/{provider}/sync` | F1 | Runs via FastAPI BackgroundTasks |
| `POST /agents/{id}/run` | F3 | Direct execution |
| `POST /admin/backfill-sources/{user_id}` | F1 (ADR-079) | Admin-only, backfill smart defaults |

---

## Render Service Environment

**Critical shared env vars** (must be on API + Sync Cron + Unified Scheduler):

| Env Var | API | Sync Cron | Unified Sched | MCP Server |
|---------|-----|-----------|---------------|------------|
| `SUPABASE_URL` | yes | yes | yes | yes |
| `SUPABASE_SERVICE_KEY` | yes | yes | yes | yes |
| `INTEGRATION_ENCRYPTION_KEY` | yes | yes | yes | — |
| `GOOGLE_CLIENT_ID/SECRET` | yes | yes | yes | — |
| `SLACK_CLIENT_ID/SECRET` | yes | yes | yes | — |
| `NOTION_CLIENT_ID/SECRET` | yes | yes | yes | — |
| `ANTHROPIC_API_KEY` | yes | — | yes | — |
| `RESEND_API_KEY` | yes | — | yes | — |
| `MCP_BEARER_TOKEN` | — | — | — | yes |

---

## Design Principles

1. **Single fetch path** (ADR-073): F1 is the ONLY feature calling external APIs. Everything else reads `platform_content`.
2. **Content retention** (ADR-072): All synced content starts ephemeral with TTL. F3 marks consumed content as retained. F6 cleans expired non-retained content hourly.
3. **Implicit memory** (ADR-064): No explicit memory tools for TP. F4 extracts nightly.
4. **Delivery-first** (ADR-066): No approval gate. F3 delivers immediately after generation.
5. **activity_log as nervous system**: Every feature writes events. Multiple consumers read for different purposes.
6. **Tier-gated LLM spend**: Token budget checked per chat message (not per background job). Agent count gated by tier.
7. **Unified agent, separate orchestration** (ADR-080): F3 invokes the agent in headless mode for content generation. Orchestration (scheduling, strategy, delivery, retention) stays in the pipeline. One agent, two modes — shared primitives, no drift.

---

## Known Gaps & Optimization Opportunities

### GAP-1: Embedding Generation (F9)

Infrastructure exists but pipeline is not wired. See F9 section above.

### GAP-2: Notion Database Sync Performance

Notion's 3 req/sec rate limit (350ms/call) × up to 300 rows per database creates a bottleneck. A Starter user with 5 database sources could take 10+ minutes on first sync. Options:
- Cap database row sync (e.g., 50 rows for Free/Starter, unlimited for Pro)
- Tier-gate database source selection
- Prioritize recently-edited rows only

### GAP-3: No Inter-Platform Parallelization in Sync

Platforms sync sequentially within a user. Running Slack + Gmail + Notion + Calendar in parallel (asyncio.gather) would reduce wall clock by ~1.5-2x. Low risk since each platform uses independent API credentials.

### ~~GAP-4: Conversation Analysis Overlap with Signal Processing~~ — Resolved (ADR-092)

Signal processing (F2) and conversation analysis (F5) were both removed (ADR-092). Coordinator agents now handle proactive work creation.

### ~~GAP-5: Work Ticket Dual Path~~ — **Resolved** (ADR-083)

Removed RQ worker and Redis. All work tickets now execute inline (single path).
