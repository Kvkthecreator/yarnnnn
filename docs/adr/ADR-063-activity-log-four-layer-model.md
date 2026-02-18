# ADR-063: Activity Log — Four-Layer Model (Memory / Activity / Context / Work)

**Status**: Accepted
**Date**: 2026-02-18
**Relates to**: ADR-059 (Simplified Context Model), ADR-062 (Platform Context Architecture)

---

## Context

ADR-062 clarified the three-layer model (Memory / Context / Work) and confirmed that `filesystem_items` is a conversational search cache — not a source of truth, not used by deliverable execution. It is retained for its specific load-bearing purpose: serving `Search(scope="platform_content")` via ILIKE on cached platform content.

After that clarification, a further question was raised: does Yarnnn have a record of what *it* has done? The answer is no.

Currently:
- `chat_sessions` / `session_messages` stores conversation turns but no summary of what happened
- `deliverable_versions` stores generated output but no execution event record
- `working_memory.py` injects up to 3 recent session summaries — but only if sessions have a populated `summary` field (which nothing currently writes)
- No unified log of YARNNN activity exists across both pipelines

This is a gap. TP, when starting a new session, has no grounded view of recent system activity. It cannot answer questions like "when did you last run my digest?" or "what happened in our last session?" without querying platform data or making assumptions.

---

## Finding: Two Independent Pipelines, No Shared Footprint

The cross-check audit confirmed that Yarnnn has two completely independent pipelines:

```
Pipeline 1: Chat (api/routes/chat.py)
  → User sends message
  → TP streams response (may use tools, search, platform calls)
  → Messages appended to session_messages
  → No summary written anywhere

Pipeline 2: Deliverable execution (deliverable_execution.py → deliverable_pipeline.py)
  → unified_scheduler.py triggers execution
  → Live API reads → LLM generation → deliverable_version created
  → work_execution_log tracks step-by-step progress (ephemeral)
  → No persistent event record written after completion
```

`working_memory.py → build_working_memory()` currently reads:
- `user_context` (Memory)
- `deliverables` (up to 5 active, with sources and schedule)
- `platform_connections` (status and last_synced_at)
- `chat_sessions` (up to 3 recent, last 7 days — summary field, which is never populated)

**The gap**: there is no persistent, structured record of what YARNNN has actually done. The working memory block injected into each TP session is accurate about *what is configured* but blind to *what has recently happened*.

---

## Decision: Introduce `activity_log` as a Fourth Layer

The three-layer model (Memory / Context / Work) is correct and complete for describing *stored state*. A fourth concept — Activity — describes *what the system has done*. It is distinct from all three:

| Layer | Answers | Table(s) |
|---|---|---|
| **Memory** | What TP knows about you | `user_context` |
| **Activity** | What YARNNN has done | `activity_log` (new) |
| **Context** | What's in your platforms right now | `filesystem_items` + live APIs |
| **Work** | What TP has produced | `deliverables` + `deliverable_versions` |

**Activity is not Memory**: Memory is user-owned stable facts. Activity is system provenance — timestamped events written by pipelines, never by the user.

**Activity is not Context**: Context is platform content (emails, Slack messages, Notion pages). Activity is YARNNN's own footprint.

**Activity is not Work**: Work is the generated output itself. Activity is the record that generation ran, when, what was read, and what was produced.

---

## What `activity_log` Records

Every write is from a system pipeline, never from the user. Events are immutable — no updates, no deletes.

| event_type | Written by | summary example |
|---|---|---|
| `deliverable_run` | deliverable_execution.py | "Generated Weekly Digest v3 (draft)" |
| `memory_written` | TP tools (create_memory / update_memory) | "Noted: prefers bullet points" |
| `platform_synced` | platform_worker.py | "Synced Slack #general: 47 messages" |
| `chat_session` | chat.py (on session end / summary) | "Session: discussed digest cadence" |

The log is append-only. It is not a replacement for `deliverable_versions`, `session_messages`, or `sync_registry` — those continue to serve their existing roles. `activity_log` is a lightweight summary layer on top of all pipelines.

---

## Schema

```sql
CREATE TABLE activity_log (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_type    TEXT        NOT NULL,  -- 'deliverable_run', 'memory_written', 'platform_synced', 'chat_session'
    event_ref     UUID,                  -- FK to relevant record: version_id, session_id, etc.
    summary       TEXT        NOT NULL,  -- Human-readable one-liner
    metadata      JSONB,                 -- Event-specific detail (deliverable_id, platform, key, etc.)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own activity" ON activity_log
    FOR SELECT USING (auth.uid() = user_id);
-- No UPDATE / DELETE policies — log is append-only from service role

-- Performance: recent activity queries
CREATE INDEX activity_log_user_recent ON activity_log (user_id, created_at DESC);
CREATE INDEX activity_log_event_type  ON activity_log (user_id, event_type, created_at DESC);
```

**Row size**: Tiny. Summary is a single sentence, metadata is a compact object. Expected volume: ~5–20 events/day per user. No TTL needed at scale.

---

## Working Memory Integration

`build_working_memory()` gains a new section injected between "Connected platforms" and session end — approximately 300 tokens of budget.

**Format** (injected into system prompt):
```
### Recent activity
- 2026-02-18 09:00 · Weekly Digest v3 generated (draft, pending review)
- 2026-02-18 08:45 · Synced Gmail/Inbox: 12 emails
- 2026-02-17 14:30 · Session: discussed digest cadence, updated schedule
- 2026-02-17 09:00 · Weekly Digest v2 generated (approved, sent to Slack)
```

Query: last 10 events across all types, last 7 days.

This gives TP a grounded, factual answer to "when did you last run my digest?" without requiring a live database query mid-conversation.

---

## What This ADR Does Not Change

- `filesystem_items` — unchanged, kept for conversational Search
- `deliverable_versions` — unchanged, primary output store
- `session_messages` — unchanged, full message history
- `sync_registry` — unchanged, per-resource sync cursor
- `work_execution_log` — unchanged, ephemeral execution step tracking
- `user_context` — unchanged, Memory layer
- Platform sync pipeline — platform_worker adds one `activity_log` INSERT after a successful sync batch; no structural changes
- Deliverable execution pipeline — adds one `activity_log` INSERT after version is created; no structural changes

---

## What Changes

| File | Change |
|---|---|
| `supabase/migrations/060_activity_log.sql` | New table + indexes + RLS (new) |
| `api/services/activity_log.py` | `write_activity()` helper (new) |
| `api/services/deliverable_execution.py` | Call `write_activity("deliverable_run", ...)` after version created |
| `api/workers/platform_worker.py` | Call `write_activity("platform_synced", ...)` after sync batch completes |
| `api/routes/chat.py` | Call `write_activity("chat_session", ...)` when session summary is available |
| `api/services/working_memory/tools.py` (TP tools) | Call `write_activity("memory_written", ...)` on create_memory / update_memory |
| `api/services/working_memory.py` | Read last 10 activity_log rows, inject "Recent activity" block |

---

## On filesystem_items: Not Replaced

Replacing `filesystem_items` with `activity_log` was considered and rejected. They are orthogonal:

- `filesystem_items` holds **platform content** (message text, email bodies, page content). It is what `Search(scope="platform_content")` runs ILIKE against. There is no equivalent in `activity_log`.
- `activity_log` holds **event summaries** of what YARNNN did. It has no content to search through.

`filesystem_items` cannot be removed without eliminating conversational Search or replacing it with live fan-out to platform APIs (a viable future option, but deferred per ADR-062).

---

## Updated Four-Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│  MEMORY  (user_context)                                      │
│  What TP knows about you — stable, explicit, user-owned     │
│  Injected into every TP session (working memory)            │
└─────────────────────────────────────────────────────────────┘
         Written by: user directly, TP during conversation

┌─────────────────────────────────────────────────────────────┐
│  ACTIVITY  (activity_log)                                    │
│  What YARNNN has done — system provenance, append-only      │
│  Recent events injected into every TP session               │
└─────────────────────────────────────────────────────────────┘
         Written by: deliverable pipeline, platform sync,
                     chat pipeline, TP memory tools

┌─────────────────────────────────────────────────────────────┐
│  CONTEXT  (filesystem_items + live platform APIs)           │
│  What's in your platforms right now — ephemeral, large      │
│  Accessed on demand: Search (cache) or live fetch           │
└─────────────────────────────────────────────────────────────┘
         Written by: platform_worker (cache),
                     live API calls at execution time

┌─────────────────────────────────────────────────────────────┐
│  WORK  (deliverables + deliverable_versions)                 │
│  What TP produces — structured, versioned, exported         │
│  Always generated from live Context reads                   │
└─────────────────────────────────────────────────────────────┘
         Written by: deliverable execution pipeline
```

---

## Reference Model Comparison

| Concept | Claude Code | Clawdbot | Yarnnn |
|---|---|---|---|
| **Memory** | CLAUDE.md | SOUL.md / USER.md | `user_context` |
| **Activity** | Git commit log | Script execution log | `activity_log` |
| **Context** | Source files (read on demand) | Local filesystem | `filesystem_items` + live API |
| **Work** | Build output | Script output | `deliverable_versions` |
| **Execution** | Shell commands | Skills | Deliverable pipeline (live reads) |

---

## Related

- [ADR-059](ADR-059-simplified-context-model.md) — Memory table consolidation (user_context)
- [ADR-062](ADR-062-platform-context-architecture.md) — Three-layer model, filesystem_items mandate
- [context-pipeline.md](../architecture/context-pipeline.md) — Architectural overview (to be updated)
- [SCHEMA.md](../database/SCHEMA.md) — Database schema reference (to be updated)
