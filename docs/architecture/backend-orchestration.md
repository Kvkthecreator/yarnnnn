# Backend Orchestration Pipeline

**Canonical reference for YARNNN's backend processing pipeline.**

Last updated: 2026-02-25 (ADR-077 sync overhaul, ADR-076 direct API clients)

## Overview

YARNNN's backend runs as four Render services that share a single codebase:

| Service | Type | Schedule | Role |
|---------|------|----------|------|
| `yarnnn-api` | Web Service | Always-on | API endpoints, manual triggers |
| `yarnnn-worker` | Background Worker | Always-on | RQ job processing (platform sync) |
| `yarnnn-unified-scheduler` | Cron Job | `*/5 * * * *` | All scheduled processing |
| `yarnnn-mcp-server` | Web Service | Always-on | MCP server for Claude.ai/Desktop (ADR-075) |

The pipeline flows: **Sync → Signal → Deliverable → Memory**, with `activity_log` as the central nervous system connecting all subsystems.

```
External APIs → platform_content → [Signal LLM] → deliverables → [Execution LLM] → deliverable_versions
                                                                                   → [Delivery: Email/Slack]
                                                                   ↑
chat_sessions → [Memory LLM] → user_context ────────────────────────┘
                                     ↑                (injected as context)
activity_log ←── ALL subsystems ─────┘
```

---

## 1. Platform Sync (Worker)

**File**: `api/workers/platform_worker.py`
**Entry point**: RQ background job, enqueued by API routes or scheduler import phase
**External APIs**: This is the ONLY subsystem that calls external platform APIs.

### Flow

1. Look up `platform_connections` for user/provider
2. Read `landscape.selected_sources` for per-source sync (ADR-056)
3. Dispatch to provider handler (ADR-077: all fully paginated with platform-specific hardening):
   - **Slack**: `SlackAPIClient` → paginated history (1000 initial/500 incremental), thread expansion, user resolution, system message filtering
   - **Gmail**: `GoogleAPIClient` → paginated messages (200/label), concurrent fetch, 30-day initial window
   - **Notion**: `NotionAPIClient` → recursive block fetch (depth=3), database query support, rate limiting
   - **Calendar**: `GoogleAPIClient` → events -7d to +14d, pagination, `syncToken` for incremental sync
4. Each item stored via `_store_platform_content()` with:
   - `retained=False` (ephemeral by default)
   - TTL-based `expires_at`: Slack 14d, Gmail 30d, Notion 90d, Calendar 2d (ADR-077)
   - Content-hash dedup (upsert on `content_hash`)
   - Unix epoch → ISO 8601 timestamp conversion (Slack `ts` format)
5. Update `sync_registry` cursors for incremental sync
6. Update `platform_connections.last_synced_at`
7. Write `platform_synced` event to `activity_log`

### Tables

| Reads | Writes |
|-------|--------|
| `platform_connections` | `platform_content` (upsert) |
| `sync_registry` (cursors) | `sync_registry` (cursor update) |
| | `platform_connections` (last_synced_at) |
| | `activity_log` (platform_synced) |

---

## 2. Signal Processing (Scheduler + Manual Trigger)

**Files**: `api/services/signal_extraction.py`, `api/services/signal_processing.py`
**Entry points**: Scheduler hourly phase, `POST /signal-processing/trigger`
**ADR**: ADR-068 (Phase 3+4 complete)

### Phase 1: Signal Extraction (Deterministic — No LLM)

`extract_signal_summary()` reads from `platform_content` — NO live API calls (ADR-073).

- Query `platform_connections` for active platforms
- Read `platform_content` per platform with time windows:
  - Calendar: non-expired or retained, limit 50
  - Gmail: fetched in last 7 days, limit 30
  - Slack: fetched in last 2 days, limit 100
  - Notion: non-expired or retained, limit 20
- Build `SignalSummary` with content summaries per platform

### Phase 2: Signal Reasoning (Single LLM Call)

`process_signal()` — LLM: `claude-haiku-4-5-20251001` (cost-efficient routing)

- Skip if < 3 total content items
- Build prompt with: platform content summaries, `user_context` (memory), recent `activity_log`, existing deliverables with Layer 4 content (recent version output, ADR-069)
- Parse LLM response into `SignalAction` objects
- Filter by confidence (≥ 0.60), deduplicate by type, check against existing deliverable types

### Phase 3: Action Execution (Selective Artifact Creation)

`execute_signal_actions()`:

| Action | What happens |
|--------|-------------|
| `create_signal_emergent` | Check `signal_history` for dedup → Create `deliverables` row (origin=signal_emergent) → Record in `signal_history` → **Immediately execute** via `execute_deliverable_generation()` |
| `trigger_existing` | Update existing deliverable's `next_run_at` to now (pure orchestration) |
| `no_action` | Signal below threshold or deduplicated |

Write `signal_processed` event to `activity_log` (uses service client for RLS bypass).

### Tables

| Reads | Writes |
|-------|--------|
| `platform_content` | `deliverables` (signal-emergent) |
| `platform_connections` | `signal_history` |
| `user_context` | `activity_log` (signal_processed) |
| `activity_log` (recent) | `deliverable_versions` (via execution) |
| `deliverables` + `deliverable_versions` (Layer 4) | |
| `signal_history` (dedup) | |

---

## 3. Deliverable Execution

**File**: `api/services/deliverable_execution.py`
**Entry points**: Scheduler (scheduled), Signal Processing (emergent), API manual trigger
**ADR**: ADR-042 (simplified flow), ADR-066 (delivery-first, no approval gate)
**LLM**: `claude-sonnet-4-20250514`

### Flow

1. `check_deliverable_freshness()` — compare `sync_registry` state against threshold (ADR-049)
2. Create `deliverable_versions` row (status=generating)
3. Create `work_tickets` row (status=running)
4. Select execution strategy based on `type_classification.binding`:

| Strategy | What it reads |
|----------|--------------|
| `platform_bound` | `platform_content` from single platform |
| `cross_platform` | `platform_content` from all platforms |
| `research` | Web research (Anthropic native) |
| `hybrid` | Research + Platform in parallel |

5. Log inputs to `work_execution_log`
6. Single LLM call with type-specific prompt from `deliverable_pipeline.py`
7. Store draft to `deliverable_versions` (draft_content + final_content)
8. `mark_content_retained()` on consumed `platform_content` IDs (ADR-073)
9. Record `source_snapshots` for audit trail (ADR-049)
10. Complete `work_tickets`
11. `DeliveryService.deliver_version()` — email-first (ADR-066)
12. Update `deliverable_versions` status = delivered | failed
13. Write `deliverable_run` event to `activity_log`

### Tables

| Reads | Writes |
|-------|--------|
| `deliverables` (config) | `deliverable_versions` |
| `platform_content` (via strategy) | `work_tickets` |
| `sync_registry` (freshness) | `work_execution_log` |
| `deliverable_versions` (version numbering) | `platform_content` (retained=true) |
| | `source_snapshots` |
| | `deliverables` (last_run_at) |
| | `activity_log` (deliverable_run) |

---

## 4. Memory Extraction (Nightly Cron)

**File**: `api/services/memory.py`
**Entry point**: Scheduler at 00:00 UTC
**ADR**: ADR-064 (implicit memory), ADR-067 (session continuity)
**LLM**: `claude-sonnet-4-20250514`

Memory is fully implicit — TP has no explicit memory tools.

### Three Write Paths

**a) Conversation Extraction** — `process_conversation()`
- Query yesterday's `chat_sessions` (type=thinking_partner)
- Skip if < 3 user messages
- LLM extracts structured facts: key, value, confidence
- Upsert to `user_context` with source priority: `user_stated > conversation > feedback > pattern`

**b) Session Summaries** — `generate_session_summary()` (ADR-067)
- For sessions with ≥ 5 user messages
- LLM generates prose summary
- Written to `chat_sessions.summary`
- Read by `working_memory._get_recent_sessions()` for cross-session continuity

**c) Activity Pattern Detection** — `process_patterns()`
- Rule-based (no LLM): day-of-week, time-of-day, type preferences, edit patterns
- Reads last 30 days of `activity_log`
- Writes to `user_context` with confidence=0.6

### Tables

| Reads | Writes |
|-------|--------|
| `chat_sessions` | `user_context` |
| `session_messages` | `chat_sessions` (summary) |
| `activity_log` (patterns) | `activity_log` (memory_written) |
| `user_context` (dedup/priority) | |

---

## 5. Unified Scheduler — All Phases

**File**: `api/jobs/unified_scheduler.py`
**Entry point**: Render cron `*/5 * * * *`, `cd api && python -m jobs.unified_scheduler`

| Phase | Frequency | What it does | Key function |
|-------|-----------|-------------|-------------|
| Deliverables | Every 5 min | Execute due deliverables (`next_run_at <= now`) | `execute_deliverable_generation()` |
| Work Tickets | Every 5 min | Execute due work tickets | `execute_work_ticket()` |
| Import Jobs | Every 5 min | Process pending `integration_import_jobs` | `process_import_job()` |
| Signal Processing | Hourly | Two passes per user (calendar_only + non_calendar) | `extract_signal_summary()` → `process_signal()` → `execute_signal_actions()` |
| Content Cleanup | Hourly | Delete expired non-retained `platform_content` | `cleanup_expired_content()` |
| Weekly Digests | Hourly | Generate and email workspace digests | Direct LLM + email |
| Memory Extraction | Daily 00:00 UTC | Extract memories from yesterday's sessions | `process_conversation()` + `generate_session_summary()` |
| Activity Patterns | Daily 00:00 UTC | Detect behavioral patterns from activity_log | `process_patterns()` |
| Conversation Analysis | Daily 06:00 UTC | Suggest deliverables from chat patterns | `run_analysis_for_user()` |
| Heartbeat | Every 5 min | Write `scheduler_heartbeat` per active user | `write_activity()` |

---

## 6. Observability

### activity_log — Central Nervous System

Every subsystem writes events here. Event types:

| Event Type | Writer | Trigger |
|-----------|--------|---------|
| `platform_synced` | `platform_worker.py` | After sync completes |
| `signal_processed` | `signal_processing.py` | After signal reasoning pass |
| `deliverable_run` | `deliverable_execution.py` | After version created |
| `deliverable_approved` | `routes/deliverables.py` | User approves version |
| `deliverable_rejected` | `routes/deliverables.py` | User rejects version |
| `deliverable_scheduled` | `unified_scheduler.py` | Deliverable queued for execution |
| `memory_written` | `memory.py` | After memory extraction |
| `integration_connected` | `routes/integrations.py` | OAuth connected |
| `integration_disconnected` | `routes/integrations.py` | OAuth disconnected |
| `chat_session` | `chat.py` | Session ends |
| `scheduler_heartbeat` | `unified_scheduler.py` | Every 5 min per active user |

### Consumers

- **Working memory** (`working_memory.py`): Injects last 10 events (7-day window) into TP system prompt
- **Signal processing**: Recent activity as context for LLM reasoning
- **System status** (`routes/system.py`): Renders background job cards on system page
- **Pattern detection** (`memory.py`): 30-day activity for behavioral analysis
- **TP primitive** (`primitives/system_state.py`): `GetSystemState` for TP self-awareness

### System Status Endpoint

`GET /api/system/status` — pure read, writes nothing.

Reads: `workspaces` (tier), `platform_connections`, `sync_registry`, `platform_content` (counts), `activity_log` (job status per event_type).

---

## 7. LLM Usage

| Model | Used by | Purpose |
|-------|---------|---------|
| `claude-haiku-4-5-20251001` | Signal processing | Signal reasoning (cost-efficient) |
| `claude-sonnet-4-20250514` | Deliverable execution | Draft generation |
| `claude-sonnet-4-20250514` | Memory extraction | Fact extraction from sessions |
| `claude-sonnet-4-20250514` | Session summaries | Cross-session continuity |
| `claude-sonnet-4-20250514` | Conversation analysis | Suggested deliverables |

---

## 8. Key Database Tables

| Table | Layer | Written by | Read by |
|-------|-------|-----------|---------|
| `platform_content` | Context | Sync worker | Signals, Deliverables, TP, Cleanup |
| `sync_registry` | Context | Sync worker | Freshness checks, System status |
| `platform_connections` | Context | Sync worker, OAuth | Sync, Signals, System status |
| `deliverables` | Work | Signals, Analysis, User | Scheduler, Execution |
| `deliverable_versions` | Work | Execution | Signals (Layer 4), User review |
| `user_context` | Memory | Memory extraction, User edits | TP, Signals, Working memory |
| `activity_log` | Activity | ALL subsystems | Working memory, Signals, System status, Patterns |
| `signal_history` | Work | Signal processing | Signal dedup |
| `work_tickets` | Work | Execution | Scheduler |
| `chat_sessions` | Activity | Chat endpoints, Memory (summary) | Memory extraction, Analysis |
| `session_messages` | Activity | Chat endpoints | Memory extraction, Analysis |

---

## 9. Manual Trigger Paths

| Endpoint | What it does |
|----------|-------------|
| `POST /signal-processing/trigger` | Same as scheduler signal phase for single user. 5-min rate limit. |
| `POST /integrations/{provider}/sync` | Enqueues RQ job for platform worker |
| `POST /deliverables/{id}/run` | Direct execution of a single deliverable |

---

## Design Principles

1. **Single fetch path** (ADR-073): Platform Worker is the ONLY subsystem calling external APIs. Everything else reads `platform_content`.
2. **Content retention** (ADR-072): All synced content starts ephemeral with TTL. Deliverable execution marks consumed content as retained. Expired non-retained content cleaned up hourly.
3. **Implicit memory** (ADR-064): No explicit memory tools for TP. Extraction happens nightly.
4. **Delivery-first** (ADR-066): No approval gate. Deliverables deliver immediately after generation.
5. **activity_log as nervous system**: Every subsystem writes events. Multiple consumers read for different purposes (TP awareness, system page, pattern detection).
