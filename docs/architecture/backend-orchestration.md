# Backend Orchestration Pipeline

**Version**: 2.1
**Last updated**: 2026-02-26 (ADR-080 unified agent modes, ADR-079 numbering fix)
**Status**: Canonical reference — all background processing documented here

---

## Overview

YARNNN's backend runs 5 Render services sharing a single codebase:

| # | Service | Render ID | Type | Schedule | Role |
|---|---------|-----------|------|----------|------|
| 1 | `yarnnn-api` | `srv-d5sqotcr85hc73dpkqdg` | Web Service | Always-on | API endpoints, OAuth, manual triggers |
| 2 | `yarnnn-worker` | `srv-d4sebn6mcj7s73bu8en0` | Background Worker | Always-on | RQ job queue (work tickets) |
| 3 | `yarnnn-unified-scheduler` | `crn-d604uqili9vc73ankvag` | Cron Job | `*/5 * * * *` | Deliverables, signals, memory, cleanup |
| 4 | `yarnnn-platform-sync` | `crn-d6gdvi94tr6s73b6btm0` | Cron Job | `*/5 * * * *` | Platform sync scheduling |
| 5 | `yarnnn-mcp-server` | `srv-d6f4vg1drdic739nli4g` | Web Service | Always-on | MCP server for Claude.ai/Desktop (ADR-075) |

### Pipeline Flow

```
External APIs ──[F1: Sync]──→ platform_content ──[F2: Signals]──→ deliverables
                                                                       │
                                                              [F3: Execution]
                                                                       │
                                                                       ▼
                                                              deliverable_versions
                                                                       │
                                                              [F3: Delivery]
                                                                       ▼
                                                              Email / Slack
                                        ┌─────────────────────────────────┘
                                        │ (content marked retained)
chat_sessions ──[F4: Memory]──→ user_context ──→ injected into TP + Signals
                                        │
activity_log ◄── ALL features ──────────┘
```

---

## Feature Map

10 background features, each with a unique ID for cross-referencing.

| ID | Feature | Frequency | LLM? | Cost Driver | Service |
|----|---------|-----------|------|-------------|---------|
| F1 | Platform Sync | Tier-gated (2x/4x/hourly) | No | Platform API reads | platform-sync cron |
| F2 | Signal Processing | Hourly (Starter+) | Haiku | ~500 tokens/cycle | unified-scheduler |
| F3 | Deliverable Execution | Every 5 min (due check) | Sonnet | ~2-5k tokens/run | unified-scheduler |
| F4 | Memory Extraction | Daily 00:00 UTC | Sonnet | ~1-2k tokens/user | unified-scheduler |
| F5 | Conversation Analysis | Daily 06:00 UTC | Sonnet | ~1-2k tokens/user | unified-scheduler |
| F6 | Content Cleanup | Hourly | No | DB deletes | unified-scheduler |
| F7 | Weekly Digest | Weekly per user | No | Email send | unified-scheduler |
| F8 | Import Jobs | Every 5 min | No | Platform API reads | unified-scheduler |
| F9 | Embedding Generation | **NOT IMPLEMENTED** | No | OpenAI API (~$0.02/M tokens) | — |
| F10 | Work Ticket Processing | Every 5 min | Sonnet | ~2-5k tokens/ticket | unified-scheduler + worker |

### Feature Dependencies

```
F1 (Sync) ──writes──→ platform_content ──read by──→ F2 (Signals)
                                                      │
                                           F2 creates → F3 (Execution)
                                                      │
F4 (Memory) ──writes──→ user_context ──read by──→ F2, F3, F5
F5 (Analysis) ──creates──→ deliverables ──read by──→ F3
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

Sync is invoked **inline** (not queued to RQ) — `sync_platform()` runs synchronously within the cron process.

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
| `platform_connections` | `platform_content` (upsert) |
| `sync_registry` (cursors) | `sync_registry` (cursor + error) |
| | `platform_connections` (last_synced_at) |
| | `activity_log` (platform_synced) |

---

## F2: Signal Processing

**Files**: `api/services/signal_extraction.py`, `api/services/signal_processing.py`
**Entry points**: Unified scheduler (hourly), `POST /signal-processing/trigger` (manual, 5-min rate limit)
**ADRs**: ADR-068 (signal phases), ADR-069 (Layer 4 content)
**LLM**: `claude-haiku-4-5-20251001`
**Tier gate**: Starter+ only (Free tier skipped)

### Phase 1: Signal Extraction (Deterministic — No LLM)

`extract_signal_summary()` reads cached `platform_content`:

| Platform | Window | Limit |
|----------|--------|-------|
| Calendar | Non-expired or retained | 50 |
| Gmail | Last 7 days | 30 |
| Slack | Last 2 days | 100 |
| Notion | Non-expired or retained | 20 |

### Phase 2: Signal Reasoning (Single LLM Call)

- Skip if < 3 total content items
- Input: content summaries + `user_context` (memory) + recent `activity_log` + existing deliverables with Layer 4 content
- Output: `SignalAction` objects filtered by confidence ≥ 0.60

### Phase 3: Action Execution

| Action | What happens |
|--------|-------------|
| `create_signal_emergent` | Dedup via `signal_history` → Create deliverable → Immediately execute |
| `trigger_existing` | Set deliverable's `next_run_at` to now |
| `no_action` | Below threshold or deduplicated |

### Tables

| Reads | Writes |
|-------|--------|
| `platform_content`, `platform_connections` | `deliverables` (signal-emergent) |
| `user_context`, `activity_log` | `signal_history` |
| `deliverables` + `deliverable_versions` (Layer 4) | `activity_log` (signal_processed) |
| `signal_history` (dedup) | `deliverable_versions` (via execution) |

---

## F3: Deliverable Execution

**Files**: `api/services/deliverable_execution.py`, `api/services/deliverable_pipeline.py`
**Entry points**: Unified scheduler (every 5 min), Signal Processing (emergent), `POST /deliverables/{id}/run`
**ADRs**: ADR-042 (simplified), ADR-049 (freshness), ADR-066 (delivery-first), ADR-072 (retention), ADR-080 (headless mode)
**LLM**: `claude-sonnet-4-20250514` (agent in headless mode)
**Tier gate**: Active deliverable count limited (Free: 2, Starter: 5, Pro: unlimited)

### Flow

1. Freshness check — skip if no new content since `last_run_at` (ADR-049)
2. Create `deliverable_versions` (generating) + `work_tickets` (running)
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
| `deliverables`, `platform_content` | `deliverable_versions`, `work_tickets` |
| `sync_registry` (freshness) | `work_execution_log` |
| `deliverable_versions` (versioning) | `platform_content` (retained=true) |
| | `source_snapshots`, `activity_log` |

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
| Conversation extraction | Yesterday's `chat_sessions` (≥3 user msgs) | `user_context` entries | Yes (Sonnet) |
| Session summaries | Sessions with ≥5 user messages | `chat_sessions.summary` | Yes (Sonnet) |
| Activity patterns | 30 days of `activity_log` | `user_context` (confidence 0.6) | No (rule-based) |

Source priority for `user_context`: `user_stated > conversation > feedback > pattern`

### Tables

| Reads | Writes |
|-------|--------|
| `chat_sessions`, `session_messages` | `user_context` |
| `activity_log`, `user_context` | `chat_sessions` (summary) |
| | `activity_log` (memory_written) |

---

## F5: Conversation Analysis

**File**: `api/services/conversation_analysis.py`
**Entry point**: Unified scheduler at 06:00 UTC
**ADRs**: ADR-060 (analysis), ADR-061 (two-path architecture)
**LLM**: `claude-sonnet-4-20250514`

Detects patterns in conversation history and creates suggested deliverables.

### Flow

1. Get users with recent activity (last 7 days)
2. Detect user stage — skip onboarding users (ADR-060 Amendment 001)
3. Analyze conversation patterns → `AnalystSuggestion` objects
4. Create suggested deliverables (origin=analyst)
5. Dedup via `signal_history`
6. Send notification emails

### Tables

| Reads | Writes |
|-------|--------|
| `chat_sessions`, `session_messages` | `deliverables` (suggested) |
| `deliverables` (existing) | `deliverable_versions` |
| | `signal_history`, `activity_log` |

---

## F6: Content Cleanup

**File**: `api/services/platform_content.py`
**Entry point**: Unified scheduler (hourly)
**ADR**: ADR-072 (retention model)

Deletes expired non-retained content: `DELETE FROM platform_content WHERE retained=false AND expires_at < now`

Writes `content_cleanup` events to `activity_log` per user.

---

## F7: Weekly Digest

**File**: `api/jobs/digest.py`
**Entry point**: Unified scheduler (hourly check, weekly per user)

1. `get_workspaces_due_for_digest()` — RPC checks day + hour + timezone match
2. Gather: tickets completed, outputs delivered, memories added
3. Send via Resend email
4. Track in `scheduled_messages`

---

## F8: Import Jobs

**File**: `api/jobs/import_jobs.py`
**Entry point**: Unified scheduler (every 5 min)

1. Recover stale processing jobs (stuck >10 min)
2. Process pending `integration_import_jobs` (limit 10)
3. Used for on-demand source imports from context page

---

## F9: Embedding Generation (NOT IMPLEMENTED)

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

## F10: Work Ticket Processing

**Files**: `api/jobs/unified_scheduler.py` (scheduled), `api/workers/platform_worker.py` (background via RQ)
**Entry points**: Unified scheduler (every 5 min), RQ worker (always-on)
**LLM**: `claude-sonnet-4-20250514`

Two execution paths:
1. **Scheduled**: `get_due_work()` → `execute_work_ticket()` (inline in scheduler)
2. **Background**: `execute_work_background()` via RQ queue (worker service)

---

## Unified Scheduler — Phase Map

**File**: `api/jobs/unified_scheduler.py`
**Render cron**: `*/5 * * * *`, `cd api && python -m jobs.unified_scheduler`

| Phase | Frequency | Gate | Feature |
|-------|-----------|------|---------|
| Deliverables | Every 5 min | `next_run_at <= now` | F3 |
| Work Tickets | Every 5 min | `get_due_work()` | F10 |
| Import Jobs | Every 5 min | Pending jobs exist | F8 |
| Signal Processing | Hourly (`minute < 5`) | Starter+ tier | F2 |
| Content Cleanup | Hourly (`minute < 5`) | Always | F6 |
| Weekly Digests | Hourly (`minute < 5`) | Day + hour + tz match | F7 |
| Memory Extraction | Daily (`hour == 0, minute < 5`) | Always | F4 |
| Activity Patterns | Daily (`hour == 0, minute < 5`) | Always | F4 |
| Conversation Analysis | Daily (`hour == 6, minute < 5`) | Always | F5 |
| Heartbeat | Every 5 min | Always | Observability |

---

## Observability

### activity_log — Central Nervous System

| Event Type | Writer | Feature |
|-----------|--------|---------|
| `platform_synced` | `platform_worker.py` | F1 |
| `signal_processed` | `signal_processing.py` | F2 |
| `deliverable_run` | `deliverable_execution.py` | F3 |
| `deliverable_approved` / `rejected` | `routes/deliverables.py` | User action |
| `deliverable_scheduled` | `unified_scheduler.py` | F3 |
| `memory_written` | `memory.py` | F4 |
| `session_summary_written` | `memory.py` | F4 |
| `pattern_detected` | `memory.py` | F4 |
| `conversation_analyzed` | `conversation_analysis.py` | F5 |
| `content_cleanup` | `platform_content.py` | F6 |
| `integration_connected` / `disconnected` | `routes/integrations.py` | OAuth |
| `chat_session` | `chat.py` | User action |
| `scheduler_heartbeat` | `unified_scheduler.py` | Observability |

### Consumers

| Consumer | File | What it reads | Purpose |
|----------|------|--------------|---------|
| Working memory | `working_memory.py` | Last 10 events (7-day) | TP system prompt injection |
| Signal processing | `signal_processing.py` | Recent events | LLM reasoning context |
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
| `claude-haiku-4-5-20251001` | F2 Signal Processing | Signal reasoning | ~500 tokens |
| `claude-sonnet-4-20250514` | F3 Deliverable Execution | Agent headless mode (ADR-080/081) — draft generation + binding-aware tool rounds (2-6). Research types use WebSearch primitive (nested Sonnet call). | ~2-12k tokens |
| `claude-sonnet-4-20250514` | F4 Memory Extraction | Fact extraction | ~1-2k tokens |
| `claude-sonnet-4-20250514` | F4 Session Summaries | Cross-session continuity | ~1k tokens |
| `claude-sonnet-4-20250514` | F5 Conversation Analysis | Suggested deliverables | ~1-2k tokens |
| `text-embedding-3-small` | F9 Embeddings (not impl.) | Semantic search | ~$0.003/sync |

---

## Database Tables

| Table | Layer | Written by | Read by |
|-------|-------|-----------|---------|
| `platform_content` | Context | F1 Sync, F3 (retained flag), F6 (cleanup) | F2 Signals, F3 Execution, TP Search |
| `sync_registry` | Context | F1 Sync | F3 Freshness, System status |
| `platform_connections` | Context | F1 Sync, OAuth | F1, F2, System status |
| `deliverables` | Work | F2 Signals, F5 Analysis, User | F3 Execution, F2 (Layer 4) |
| `deliverable_versions` | Work | F3 Execution | F2 (Layer 4), User review |
| `user_context` | Memory | F4 Memory, User edits | TP, F2 Signals, Working memory |
| `activity_log` | Activity | ALL features | Working memory, F2, F4, System status |
| `signal_history` | Work | F2 Signal Processing | F2 (dedup), F5 (dedup) |
| `work_tickets` | Work | F3, F10 | Scheduler, F7 Digest |
| `chat_sessions` | Activity | Chat endpoints, F4 (summary) | F4, F5 |
| `session_messages` | Activity | Chat endpoints | F4, F5 |

---

## Manual Trigger Paths

| Endpoint | Feature | Notes |
|----------|---------|-------|
| `POST /integrations/{provider}/sync` | F1 | Runs inline (not queued) |
| `POST /signal-processing/trigger` | F2 | 5-min rate limit |
| `POST /deliverables/{id}/run` | F3 | Direct execution |
| `POST /admin/backfill-sources/{user_id}` | F1 (ADR-079) | Admin-only, backfill smart defaults |

---

## Render Service Environment

**Critical shared env vars** (must be on API + Sync Cron + Unified Scheduler + Worker):

| Env Var | API | Sync Cron | Unified Sched | Worker | MCP Server |
|---------|-----|-----------|---------------|--------|------------|
| `SUPABASE_URL` | yes | yes | yes | yes | yes |
| `SUPABASE_SERVICE_KEY` | yes | yes | yes | yes | yes |
| `INTEGRATION_ENCRYPTION_KEY` | yes | yes | yes | yes | — |
| `GOOGLE_CLIENT_ID/SECRET` | yes | yes | yes | yes | — |
| `SLACK_CLIENT_ID/SECRET` | yes | yes | yes | yes | — |
| `NOTION_CLIENT_ID/SECRET` | yes | yes | yes | yes | — |
| `ANTHROPIC_API_KEY` | yes | — | yes | yes | — |
| `OPENAI_API_KEY` | — | — | — | yes | — |
| `RESEND_API_KEY` | yes | — | yes | — | — |
| `MCP_BEARER_TOKEN` | — | — | — | — | yes |

---

## Design Principles

1. **Single fetch path** (ADR-073): F1 is the ONLY feature calling external APIs. Everything else reads `platform_content`.
2. **Content retention** (ADR-072): All synced content starts ephemeral with TTL. F3 marks consumed content as retained. F6 cleans expired non-retained content hourly.
3. **Implicit memory** (ADR-064): No explicit memory tools for TP. F4 extracts nightly.
4. **Delivery-first** (ADR-066): No approval gate. F3 delivers immediately after generation.
5. **activity_log as nervous system**: Every feature writes events. Multiple consumers read for different purposes.
6. **Tier-gated LLM spend**: Token budget checked per chat message (not per background job). Deliverable count and signal processing gated by tier.
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

### GAP-4: Conversation Analysis Overlap with Signal Processing

F5 (Conversation Analysis) and F2 (Signal Processing) both create deliverables from pattern detection. F5 runs daily from chat patterns; F2 runs hourly from platform content. They share `signal_history` for dedup but have independent detection logic. Consider whether F5 should be merged into F2 as a "conversation signals" pass.

### GAP-5: Work Ticket Dual Path

F10 has two execution paths (scheduled inline vs RQ background) which adds complexity. The RQ worker service is always-on but only used for background work tickets, not platform sync. Consider whether the worker service is still needed or if everything can run in the scheduler.
