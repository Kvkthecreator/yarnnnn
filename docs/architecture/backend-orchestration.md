# Backend Orchestration — Canonical Reference

**Version**: 5.0
**Last updated**: 2026-03-30 (ADR-138/141: task-based execution, ADR-131: Gmail/Calendar removed, ADR-118: output gateway)
**Status**: Canonical — single authoritative reference for all background processing.

---

## Overview

YARNNN runs 5 Render services sharing a single codebase:

| # | Service | Render ID | Type | Schedule | Role |
|---|---------|-----------|------|----------|------|
| 1 | `yarnnn-api` | `srv-d5sqotcr85hc73dpkqdg` | Web Service | Always-on | API endpoints, OAuth, TP chat, manual triggers |
| 2 | `yarnnn-unified-scheduler` | `crn-d604uqili9vc73ankvag` | Cron Job | `*/5 * * * *` | Task execution, composer, memory, cleanup |
| 3 | `yarnnn-platform-sync` | `crn-d6gdvi94tr6s73b6btm0` | Cron Job | `*/5 * * * *` | Platform sync scheduling |
| 4 | `yarnnn-mcp-server` | `srv-d6f4vg1drdic739nli4g` | Web Service | Always-on | MCP server for Claude.ai/Desktop (ADR-075) |
| 5 | `yarnnn-render` | `srv-d6sirjffte5s73f90pfg` | Web Service (Docker) | Always-on | Output gateway — PDF, PPTX, charts, HTML (ADR-118) |

All execution is inline — no background worker, no Redis. On-demand operations use FastAPI BackgroundTasks.

### Data Flow

```
External APIs ──[Sync]──→ platform_content ──→ workspace knowledge
                                                       │
                                              [Task Pipeline]
                                                       │
                                                       ▼
                                              workspace outputs → agent_runs
                                                       │
                                              [Delivery]
                                                       ▼
                                              Email (+ optional render)

chat_sessions ──[Memory Extraction]──→ user_memory ──→ injected into TP

activity_log ◄── ALL features (observability)
```

---

## Complete LLM Consumer Inventory

**Every path that calls the Anthropic API.** This is the cost surface.

### Sonnet Consumers (`claude-sonnet-4-20250514`)

| Consumer | File | Trigger | Gating | Est. Input Tokens |
|----------|------|---------|--------|------------------|
| TP chat (streaming + tools) | `agents/thinking_partner.py` | User message | `check_monthly_message_limit()` | 10K-20K |
| ChatAgent (meeting room) | `agents/chat_agent.py` | User @-mention | `check_monthly_message_limit()` | 10K-20K |
| Task execution (single-step) | `services/task_pipeline.py` | Scheduler cron | `check_credits()` | 9K-20K |
| Task execution (multi-step) | `services/task_pipeline.py` | Scheduler cron | `check_credits()` | 9K-20K × N steps |
| Agent execution (manual/MCP) | `services/agent_execution.py` | User action / MCP | `check_credits()` (caller) | 9K-20K |
| Context inference | `services/context_inference.py` | TP `UpdateSharedContext` | Chat message limit | ~3K-5K |
| Web search | `services/primitives/web_search.py` | TP/headless tool use | Caller's tool round limit | ~2K-4K |
| Context import | `agents/integration/context_import.py` | Import jobs cron | None (bounded by job count) | ~3K-6K |

### Haiku Consumers (`claude-haiku-4-5-20251001`)

| Consumer | File | Trigger | Gating | Est. Input Tokens |
|----------|------|---------|--------|------------------|
| Composer assessment | `services/composer.py` | Scheduler cron heartbeat | State-change gate + `check_credits()` | ~1K-2K |
| Memory extraction | `services/memory.py` | Nightly cron (midnight) | Min 3 user messages/session | ~1K + conversation |
| Session summary | `services/session_continuity.py` | Nightly cron (midnight) | Min 3 user messages/session | ~1K + conversation |
| Project session summary | `services/session_continuity.py` | Nightly cron (midnight) | Min 3 user messages/session | ~1K + conversation |
| Session compaction | `routes/chat.py` | Token overflow mid-chat | `COMPACTION_THRESHOLD` | Conversation history |

### Zero-LLM Consumers (DB/API only)

| Consumer | File | Trigger | Cost |
|----------|------|---------|------|
| Platform sync | `workers/platform_worker.py` | Sync cron | Platform API calls only |
| Content cleanup | `services/platform_content.py` | Hourly cron | DB deletes |
| Workspace cleanup | `services/workspace.py` | Hourly cron | DB deletes |
| Import jobs | `jobs/import_jobs.py` | Every 5 min | DB + platform API |
| Scheduler heartbeat | `jobs/unified_scheduler.py` | Every 5 min | DB queries + activity writes |

---

## Unified Scheduler — Phase Map

**File**: `api/jobs/unified_scheduler.py`
**Render cron**: `*/5 * * * *` — `cd api && python -m jobs.unified_scheduler`

Each tick executes these phases in order:

| Phase | Frequency | Gate | LLM? | Cost per tick |
|-------|-----------|------|------|---------------|
| 1. User discovery | Every tick | — | No | 2 DB queries (shared, reused) |
| 2. Task execution | Every tick | `next_run_at <= now` on tasks table | Sonnet (when tasks due) | 0 when idle; ~$0.05-0.08/task |
| 3. Content cleanup | Hourly (`minute < 5`) | — | No | 1 DB delete |
| 4. Workspace cleanup | Hourly (`minute < 5`) | — | No | 2 DB deletes |
| 5. Import jobs | Every tick | Pending jobs exist | No (may trigger context_import Sonnet) | 2 DB queries |
| 6. Composer heartbeat | Every tick (Pro) / midnight (Free) | State-change gate | Haiku (only when warranted) | ~$0.003/LLM call |
| 7. Memory extraction | Midnight only | — | Haiku | ~$0.002/session |
| 8. Session summaries | Midnight only | — | Haiku | ~$0.001/session |
| 9. Scheduler heartbeat event | Hourly (`minute < 5`) | — | No | N activity_log writes |

### Cost Protection Mechanisms

| Mechanism | What it prevents | Where |
|-----------|-----------------|-------|
| **State-change gate** (composer) | Repeat Haiku calls when nothing changed | `run_heartbeat()` in `composer.py` |
| **Credit enforcement** | Unbounded task execution | `check_credits()` in `task_pipeline.py` |
| **Message limits** | Unbounded chat (Free tier) | `check_monthly_message_limit()` in `chat.py` |
| **Execution lock** | Duplicate task runs | Optimistic `next_run_at` bump in `task_pipeline.py` |
| **Hourly activity writes** | Activity log bloat | `is_hourly_tick` gate in scheduler |
| **Prompt caching** | Repeated token charges for stable prompts | `anthropic-beta: prompt-caching-2024-07-31` header on all calls |

---

## Platform Sync Scheduler

**File**: `api/jobs/platform_sync_scheduler.py`
**Render cron**: `*/5 * * * *` — `cd api && python -m jobs.platform_sync_scheduler`

**Zero LLM cost.** Pure DB queries + platform API calls.

### Per-Tick Flow

1. Query `platform_connections` for connected users
2. Per user: check tier-based sync schedule (`should_sync_now()`)
3. Per eligible platform: dispatch to `platform_worker.py`

### Platforms

| Platform | Client | TTL | Key Feature |
|----------|--------|-----|-------------|
| Slack | `SlackAPIClient` | 14d | Thread expansion, user resolution |
| Notion | `NotionAPIClient` | 90d | Recursive blocks (depth 3), database query |
| GitHub | `GitHubAPIClient` | 14d | Issues + PRs, token refresh on 401 |

Gmail and Calendar removed (ADR-131).

### Sync Frequency

| Tier | Frequency | Schedule |
|------|-----------|----------|
| Free | Daily | 8am + 6pm user timezone |
| Pro | Hourly | Top of each hour |

---

## Observability

### activity_log Events

| Event Type | Writer | Frequency | Purpose |
|-----------|--------|-----------|---------|
| `platform_synced` | `platform_worker.py` | Per sync | Sync tracking |
| `task_executed` | `task_pipeline.py` | Per task run | Execution audit |
| `agent_bootstrapped` | `composer.py` | On agent creation | Composer actions |
| `memory_written` | `memory.py` | Nightly | Memory extraction |
| `session_summary_written` | `memory.py` | Nightly | Session continuity |
| `content_cleanup` | `unified_scheduler.py` | Hourly (when items cleaned) | Cleanup tracking |
| `composer_heartbeat` | `unified_scheduler.py` | When actionable OR hourly | Composer health |
| `scheduler_heartbeat` | `unified_scheduler.py` | Hourly | Scheduler health |
| `chat_session` | `chat.py` | Per session start | Chat tracking |

### Consumers

| Consumer | File | What it reads |
|----------|------|--------------|
| Working memory | `working_memory.py` | Last 10 events (7-day window) → TP system prompt |
| System status page | `routes/system.py` | Latest event per type → job health |
| TP `GetSystemState` | `primitives/system_state.py` | Latest scheduler_heartbeat + sync state |
| Composer state gate | `composer.py` | Recent `composer_heartbeat` where `should_act=true` |

---

## Database Tables — Backend View

| Table | Written by (backend) | Read by (backend) |
|-------|---------------------|------------------|
| `platform_content` | Platform sync, content cleanup | Task pipeline (context gathering), TP Search |
| `sync_registry` | Platform sync | Sync scheduler (freshness), system state |
| `platform_connections` | OAuth | Scheduler (user discovery), sync scheduler |
| `agents` | Composer, API routes | Task pipeline, scheduler |
| `tasks` | API routes, TP primitives | Scheduler (`next_run_at` query) |
| `agent_runs` | Task pipeline | Frontend, delivery |
| `workspace_files` | Task pipeline, platform sync | Task pipeline (context), TP workspace tools |
| `user_memory` | Memory extraction, user edits | Working memory → TP prompt |
| `work_credits` | Task pipeline, render | Credit enforcement |
| `activity_log` | All features | Working memory, system status, composer |
| `chat_sessions` | Chat endpoints, session summaries | Memory extraction, session continuity |
| `session_messages` | Chat endpoints | Memory extraction |

---

## Render Service Environment

**Critical shared env vars** — when changing, check ALL services:

| Env Var | API | Scheduler | Sync | MCP | Render |
|---------|-----|-----------|------|-----|--------|
| `SUPABASE_URL` | yes | yes | yes | yes | yes |
| `SUPABASE_SERVICE_KEY` | yes | yes | yes | yes | yes |
| `INTEGRATION_ENCRYPTION_KEY` | yes | yes | yes | — | — |
| `SLACK_CLIENT_ID/SECRET` | yes | — | yes | — | — |
| `NOTION_CLIENT_ID/SECRET` | yes | yes | yes | — | — |
| `GITHUB_CLIENT_ID/SECRET` | yes | — | — | — | — |
| `ANTHROPIC_API_KEY` | yes | yes | — | — | — |
| `RESEND_API_KEY` | yes | yes | — | — | — |
| `RENDER_SERVICE_URL` | yes | yes | — | — | — |
| `RENDER_SERVICE_SECRET` | yes | yes | — | — | yes |
| `MCP_BEARER_TOKEN` | — | — | — | yes | — |
| `MCP_USER_ID` | — | — | — | yes | — |

---

## Design Principles

1. **Single fetch path**: Platform sync is the ONLY feature calling external platform APIs. Everything else reads `platform_content` or `workspace_files`.
2. **Content retention** (ADR-072): Synced content starts ephemeral with TTL. Task pipeline marks consumed content as retained. Cleanup deletes expired non-retained content.
3. **Implicit memory** (ADR-064): No explicit memory tools for TP. Nightly cron extracts facts.
4. **Delivery-first** (ADR-066): No approval gate. Task pipeline delivers immediately after generation.
5. **Mechanical scheduling** (ADR-141): Zero LLM cost for scheduling. Pure SQL: `next_run_at <= now()`.
6. **State-change gate** (composer): Haiku LLM called only when workspace state has actually changed since last assessment. Prevents spin loops.
7. **Prompt caching everywhere**: All Anthropic API calls include `anthropic-beta: prompt-caching-2024-07-31` header. System prompts and tool definitions are cached (~90% savings on stable components).
8. **Credit-bounded execution**: Autonomous work (task runs, renders) consumes work credits. Budget checked before pipeline entry.
9. **Hourly activity writes**: Heartbeat events written hourly (not every 5-min tick) to prevent activity_log bloat.

---

## Known Gaps

### GAP-1: Embedding Generation

Infrastructure exists (`content_embedding` column, `embeddings.py`, `search_platform_content()` RPC) but pipeline is not wired. Semantic search falls back to text matching. Low priority — text matching works adequately for current content volumes.

### GAP-2: Memory Extraction Not Firing

Zero `memory_extracted` events since 2026-03-20. Needs investigation — either no qualifying sessions (≥3 user messages) or a code path issue.

### GAP-3: Batch API for Scheduled Tasks

Anthropic Batch API offers 50% off for non-real-time calls. All scheduled task runs qualify. Deferred until user scale justifies implementation (~50+ Pro users). See [TOKEN-ECONOMICS-ANALYSIS.md](../monetization/TOKEN-ECONOMICS-ANALYSIS.md).

---

## See Also

- [agent-execution-model.md](./agent-execution-model.md) — deep-dive on the 3-layer execution model
- [SERVICE-MODEL.md](./SERVICE-MODEL.md) — end-to-end system description
- [../monetization/TOKEN-ECONOMICS-ANALYSIS.md](../monetization/TOKEN-ECONOMICS-ANALYSIS.md) — per-consumer cost analysis
- [../integrations/RENDER-SERVICES.md](../integrations/RENDER-SERVICES.md) — infrastructure operations
