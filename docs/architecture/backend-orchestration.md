# Backend Orchestration — Canonical Reference

**Version**: 6.1
**Last updated**: 2026-04-03
**Status**: Canonical — single authoritative reference for active background processing.

---

## Overview

YARNNN runs 4 Render services sharing a single codebase:

| # | Service | Render ID | Type | Schedule | Role |
|---|---------|-----------|------|----------|------|
| 1 | `yarnnn-api` | `srv-d5sqotcr85hc73dpkqdg` | Web Service | Always-on | API endpoints, OAuth, TP chat, manual triggers |
| 2 | `yarnnn-unified-scheduler` | `crn-d604uqili9vc73ankvag` | Cron Job | `*/5 * * * *` | Task execution, lifecycle hygiene, workspace cleanup, scheduler heartbeat |
| 3 | `yarnnn-mcp-server` | `srv-d6f4vg1drdic739nli4g` | Web Service | Always-on | MCP server for Claude.ai/Desktop (ADR-075) |
| 4 | `yarnnn-render` | `srv-d6sirjffte5s73f90pfg` | Web Service (Docker) | Always-on | Output gateway — PDF, PPTX, charts, HTML (ADR-118) |

Platform sync service is gone (ADR-153). Composer and nightly memory/session
jobs are also gone (ADR-156).

All execution is inline — no background worker, no Redis. On-demand operations use FastAPI BackgroundTasks.

### Data Flow

```
Task scheduler ──→ task_pipeline.py ──→ workspace context / task outputs
                                      │
                                      └──→ agent_runs

TP chat ──→ UpdateContext / workspace files ──→ working_memory injection

activity_log ◄── task execution, integrations, scheduler heartbeat
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
### Haiku Consumers (`claude-haiku-4-5-20251001`)

| Consumer | File | Trigger | Gating | Est. Input Tokens |
|----------|------|---------|--------|------------------|
| Session compaction | `routes/chat.py` | Token overflow mid-chat | `COMPACTION_THRESHOLD` | Conversation history |

### Zero-LLM Consumers (DB/API only)

| Consumer | File | Trigger | Cost |
|----------|------|---------|------|
| Workspace cleanup | `services/workspace.py` | Hourly cron | DB deletes |
| Scheduler heartbeat | `jobs/unified_scheduler.py` | Every 5 min | DB queries + activity writes |

---

## Unified Scheduler — Phase Map

**File**: `api/jobs/unified_scheduler.py`
**Render cron**: `*/5 * * * *` — `cd api && python -m jobs.unified_scheduler`

Each tick executes these phases in order:

| Phase | Frequency | Gate | LLM? | Cost per tick |
|-------|-----------|------|------|---------------|
| 1. User discovery | Every tick | — | No | Shared DB queries |
| 2. Task execution | Every tick | `next_run_at <= now` on tasks table | Sonnet (when tasks due) | 0 when idle; task cost only when due |
| 3. Workspace cleanup | Hourly (`minute < 5`) | Ephemeral file TTLs | No | DB deletes |
| 4. Lifecycle hygiene | Every tick | Underperformer rule | No | DB reads/writes |
| 5. Scheduler heartbeat event | Hourly (`minute < 5`) | — | No | activity_log writes |

### Cost Protection Mechanisms

| Mechanism | What it prevents | Where |
|-----------|-----------------|-------|
| **Credit enforcement** | Unbounded task execution | `check_credits()` in `task_pipeline.py` |
| **Message limits** | Unbounded chat (Free tier) | `check_monthly_message_limit()` in `chat.py` |
| **Execution lock** | Duplicate task runs | Optimistic `next_run_at` bump in `task_pipeline.py` |
| **Hourly activity writes** | Activity log bloat | `is_hourly_tick` gate in scheduler |
| **Prompt caching** | Repeated token charges for stable prompts | `anthropic-beta: prompt-caching-2024-07-31` header on all calls |

---

## Observability

### activity_log Events

| Event Type | Writer | Frequency | Purpose |
|-----------|--------|-----------|---------|
| `task_executed` | `task_pipeline.py` | Per task run | Execution audit |
| `content_cleanup` | `unified_scheduler.py` | Hourly (when items cleaned) | Cleanup tracking |
| `scheduler_heartbeat` | `unified_scheduler.py` | Hourly | Scheduler health |
| `chat_session` | `chat.py` | Per session start | Chat tracking |

### Consumers

| Consumer | File | What it reads |
|----------|------|--------------|
| Working memory | `working_memory.py` | Last 10 events (7-day window) → TP system prompt |
| System status page | `routes/system.py` | Latest event per type → job health |
| TP `GetSystemState` | `primitives/system_state.py` | Latest scheduler_heartbeat + sync state |

---

## Database Tables — Backend View

| Table | Written by (backend) | Read by (backend) |
|-------|---------------------|------------------|
| `platform_connections` | OAuth / integrations routes | Scheduler (user discovery), integrations, status surfaces |
| `agents` | API routes, lifecycle hygiene | Task pipeline, scheduler |
| `tasks` | API routes, TP primitives | Scheduler (`next_run_at` query) |
| `agent_runs` | Task pipeline | Frontend, delivery |
| `workspace_files` | Task pipeline, TP context writes | Task pipeline (context), TP workspace tools |
| `user_memory` | User edits / in-session context updates | Working memory → TP prompt |
| `work_credits` | Task pipeline, render | Credit enforcement |
| `activity_log` | Tasks, scheduler, integrations, chat | Working memory, system status |
| `chat_sessions` | Chat endpoints | Session continuity |
| `session_messages` | Chat endpoints | Session compaction / chat runtime |

---

## Render Service Environment

**Critical shared env vars** — when changing, check ALL services:

| Env Var | API | Scheduler | MCP | Render |
|---------|-----|-----------|-----|--------|
| `SUPABASE_URL` | yes | yes | yes | yes |
| `SUPABASE_SERVICE_KEY` | yes | yes | yes | yes |
| `INTEGRATION_ENCRYPTION_KEY` | yes | yes | — | — |
| `SLACK_CLIENT_ID/SECRET` | yes | — | — | — |
| `NOTION_CLIENT_ID/SECRET` | yes | yes | — | — |
| `GITHUB_CLIENT_ID/SECRET` | yes | — | — | — |
| `ANTHROPIC_API_KEY` | yes | yes | — | — |
| `RESEND_API_KEY` | yes | yes | — | — |
| `RENDER_SERVICE_URL` | yes | yes | — | — |
| `RENDER_SERVICE_SECRET` | yes | yes | — | yes |
| `MCP_BEARER_TOKEN` | — | — | yes | — |
| `MCP_USER_ID` | — | — | yes | — |

---

## Design Principles

1. **Task-first data flow** (ADR-153): autonomous work happens through tasks, not a generic platform sync cache.
2. **Single intelligence layer** (ADR-156): strategic judgment lives in TP, not Composer.
3. **In-session memory** (ADR-156): TP writes durable context during conversation; no nightly memory extraction job.
4. **Delivery-first** (ADR-066): No approval gate. Task pipeline delivers immediately after generation.
5. **Mechanical scheduling** (ADR-141): Zero LLM cost for scheduling. Pure SQL: `next_run_at <= now()`.
6. **Prompt caching everywhere**: All Anthropic API calls include `anthropic-beta: prompt-caching-2024-07-31` header. System prompts and tool definitions are cached (~90% savings on stable components).
7. **Credit-bounded execution**: Autonomous work (task runs, renders) consumes work credits. Budget checked before pipeline entry.
8. **Hourly activity writes**: Heartbeat events written hourly (not every 5-min tick) to prevent activity_log bloat.

---

## Known Gaps

### GAP-1: Platform Runtime Semantics Still Need Tightening

The task-first platform direction is cleaner than the old sync model, but some
runtime metadata and docs still carry legacy "sync" wording. This does not
reintroduce the sync service, but the semantics are not fully cleaned yet.

### GAP-2: Batch API for Scheduled Tasks

Anthropic Batch API offers 50% off for non-real-time calls. All scheduled task runs qualify. Deferred until user scale justifies implementation (~50+ Pro users). See [TOKEN-ECONOMICS-ANALYSIS.md](../monetization/TOKEN-ECONOMICS-ANALYSIS.md).

---

## See Also

- [agent-execution-model.md](./agent-execution-model.md) — deep-dive on the 3-layer execution model
- [SERVICE-MODEL.md](./SERVICE-MODEL.md) — end-to-end system description
- [../monetization/TOKEN-ECONOMICS-ANALYSIS.md](../monetization/TOKEN-ECONOMICS-ANALYSIS.md) — per-consumer cost analysis
- [../integrations/RENDER-SERVICES.md](../integrations/RENDER-SERVICES.md) — infrastructure operations
