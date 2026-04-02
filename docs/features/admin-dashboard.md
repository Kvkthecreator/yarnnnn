# Admin Dashboard

Operational metrics and cost analytics at `/admin`. Access restricted to emails in `ADMIN_ALLOWED_EMAILS` env var.

## Endpoints

| Endpoint | Purpose | Data Source |
|----------|---------|-------------|
| `GET /api/admin/stats` | Overview: users, agents, tasks, sessions, messages | `workspaces`, `agents`, `tasks`, `chat_sessions`, `session_messages` |
| `GET /api/admin/token-usage?days=N` | Token costs, cache efficiency, per-caller breakdown | `agent_runs.metadata`, `session_messages.metadata` |
| `GET /api/admin/execution-stats` | Task run frequency, credits, scheduler health | `agent_runs`, `work_credits`, `activity_log` |
| `GET /api/admin/users` | User list with tier, agents, tasks, credits | `workspaces`, `agents`, `tasks`, `chat_sessions`, `work_credits` |
| `GET /api/admin/export/users` | Excel export of users | Same as `/users` |
| `GET /api/admin/export/report` | Multi-sheet Excel (summary, users, tokens, executions) | All above |
| `POST /api/admin/trigger-agent/{id}` | Test agent run (requires `x-service-key`) | `agents`, task pipeline |

## Dashboard Sections

### 1. Overview Stats
Six stat cards: Users (7d trend), Agents, Tasks (7d trend), Sessions (7d trend), Messages, Credits used/limit.

### 2. Token Usage & Cost
- **Summary**: Total cost, input/output tokens, API calls, cache hit %
- **Daily cost chart**: Stacked bar (Chat vs Task Pipeline), scaled proportionally
- **Breakdown table**: Per day/caller with input, output, cache read, cost
- **Period selector**: 7d / 14d / 30d toggle

Data comes from:
- `agent_runs.metadata` — `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `model`
- `session_messages.metadata` — same fields, for assistant messages only

Cost estimation uses Anthropic pricing:
- Sonnet 4: $3/MTok input, $15/MTok output
- Haiku 4.5: $0.80/MTok input, $4/MTok output

### 3. Task Execution
- Run counts: 24h / 7d / 30d
- Scheduler health: last heartbeat, heartbeats in 24h
- Per-task table: slug, agent, role, run count (total/7d), avg tokens, last run

### 4. Users
- Per-user row: email, tier, agents, tasks, sessions, credits used this month, last active
- Export as Excel

## Token Observability Pipeline

### Log-level (real-time, Render logs)
Every Claude API call logs:
```
[TOKENS] in=1234 out=567 cache_create=800 cache_read=5000 cache_hit=62% model=claude-sonnet-4-20250514
```
Streaming rounds include `round=N`.

Search Render logs for `[TOKENS]` to see all API calls.

### DB-level (queryable, admin dashboard)
- **Task pipeline**: `agent_runs.metadata` stores `input_tokens`, `output_tokens`, `model`, `task_slug`, `trigger_type` per run
- **Chat**: `session_messages.metadata` stores `input_tokens`, `output_tokens` per assistant message
- **Credits**: `work_credits` stores `action_type`, `credits_consumed`, `agent_id` per action

### Dashboard-level (visual, `/admin`)
Aggregates DB data into daily summaries by caller (chat vs task_pipeline).

## Prompt Caching

System prompts are split into static (cached) and dynamic (uncached) content blocks:

- **TP chat**: Static = identity + behaviors + tools + platforms (~10K tokens, `cache_control: ephemeral`). Dynamic = working memory context.
- **Task pipeline**: Entire system prompt cached across tool rounds within one execution.
- **Cache TTL**: 5 minutes (Anthropic ephemeral cache).

Expected `cache_hit_pct`:
- 0% on first message of session or first task execution
- 60-80% on subsequent turns/rounds within the same session
- Overall average: 30-50% depending on session length

## Key Files

| File | Purpose |
|------|---------|
| `api/routes/admin.py` | All admin endpoints |
| `api/services/admin_auth.py` | Email allowlist auth |
| `api/services/anthropic.py` | `_prepare_system()`, `[TOKENS]` logging |
| `api/agents/tp_prompts/__init__.py` | TP prompt caching (static/dynamic split) |
| `api/services/task_pipeline.py` | Task prompt caching |
| `web/app/admin/page.tsx` | Dashboard frontend |
| `web/types/admin.ts` | TypeScript types |
| `web/lib/api/client.ts` | API client (`api.admin.*`) |

## Removed (stale)

These endpoints were deleted during the dashboard rebuild (2026-04-02):

- `GET /admin/memory-stats` — memory system metrics (stale since ADR-106 workspace migration)
- `GET /admin/document-stats` — document pipeline metrics (stale)
- `GET /admin/chat-stats` — separate chat engagement (folded into overview)
- `GET /admin/sync-health` — platform sync health (deleted by ADR-153)
- `GET /admin/pipeline-stats` — signal/trigger metrics (dissolved by ADR-141)
- `POST /admin/trigger-sync/{user_id}/{provider}` — deprecated by ADR-153
- `POST /admin/backfill-sources/{user_id}` — one-time migration utility
