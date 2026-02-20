# Activity

> Layer 2 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Activity is the system provenance log — a record of what YARNNN has done. It answers the question "what happened recently?" rather than "what do I know about the user?" (Memory) or "what's on the platforms right now?" (Context).

Every time YARNNN completes something meaningful — runs a deliverable, syncs a platform, notes a memory, finishes a chat turn — it appends a row to `activity_log`. The log is append-only. Nothing is updated or deleted.

Recent activity is injected into every TP session at startup, so TP can answer "when did you last run my digest?" without a live database query.

**Analogy**: Activity is YARNNN's git commit log. It records what was done, when, and what the outcome was. It is not the output itself (that is Work) and not the content (that is Context).

---

## What it is not

- Not platform content — that is Context (`platform_content`)
- Not generated output — that is Work (`deliverable_versions`)
- Not stable user knowledge — that is Memory (`user_context`)
- Not a replacement for `deliverable_versions` or `session_messages` — those still hold the full records; Activity holds lightweight summaries

---

## Table: `activity_log`

Append-only. Written by service role only (no user-facing INSERT).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → auth.users |
| `event_type` | TEXT | Constrained enum (see below) |
| `event_ref` | UUID | FK to related record (version_id, session_id, etc.) |
| `summary` | TEXT | Human-readable one-liner for prompt injection |
| `metadata` | JSONB | Structured event detail |
| `created_at` | TIMESTAMPTZ | Auto |

**event_type values:**

| event_type | Written by | When | summary example |
|---|---|---|---|
| `deliverable_run` | `deliverable_execution.py` | After a version is generated | `"Weekly Digest v3 generated (staged)"` |
| `memory_written` | `project_tools.py` | After `create_memory` / `update_memory` | `"Noted: prefers bullet points"` |
| `platform_synced` | `platform_worker.py` | After a sync batch completes | `"Synced gmail: 12 items"` |
| `chat_session` | `chat.py` | At end of each chat turn | `"Chat turn complete (tools: platform_gmail_search)"` |

**RLS**: Users can SELECT their own rows. No INSERT/UPDATE/DELETE via user-facing clients — service role only.

---

## How Activity is written

Each write point is a single `write_activity()` call from `api/services/activity_log.py`. All calls are wrapped in `try/except pass` — a log failure is never allowed to block the primary operation.

```
deliverable_execution.py
  → version created, final_status known
  → write_activity("deliverable_run", summary="Weekly Digest v3 generated (staged)", ...)

platform_worker.py
  → sync batch returns successfully
  → write_activity("platform_synced", summary="Synced gmail: 12 items", ...)

project_tools.py (create_memory / update_memory)
  → user_context upsert succeeds
  → write_activity("memory_written", summary="Noted: prefers bullet points", ...)

chat.py
  → done: True signal after assistant response
  → write_activity("chat_session", summary="Chat turn complete", ...)
```

---

## How Activity is read

`working_memory.py → _get_recent_activity()` fetches the last 10 events within the last 7 days and includes them in the working memory dict. They are rendered by `format_for_prompt()` as a "Recent activity" block:

```
### Recent activity
- 2026-02-18 09:00 · Weekly Digest v3 generated (staged)
- 2026-02-18 08:45 · Synced gmail: 12 items
- 2026-02-17 14:30 · Chat turn complete (tools: platform_gmail_search)
- 2026-02-17 09:00 · Weekly Digest v2 generated (delivered)
- 2026-02-17 08:45 · Noted: prefers bullet points
```

This block consumes approximately 300 tokens of the 2,000 token working memory budget.

---

## What Activity enables

**TP grounding**: TP can answer "when did you last run my digest?" or "what happened in last night's sync?" from working memory, without a live database lookup mid-conversation.

**System transparency**: The log provides an auditable trail of what YARNNN has done for each user, useful for debugging and future frontend "activity feed" features.

**Cold-start awareness**: On a brand-new account, the block is empty. TP knows it has no history. This is better than silence — it's an explicit signal.

---

## Boundaries

| Question | Answer |
|---|---|
| Can users write to Activity directly? | No — service role only |
| Is Activity deleted when a deliverable is deleted? | No — the log is immutable |
| Does Activity replace `deliverable_versions`? | No — `deliverable_versions` holds the full generated content; Activity holds the summary event |
| Does Activity replace `session_messages`? | No — `session_messages` holds the full conversation; Activity holds the lightweight session event |
| What happens if a write_activity() call fails? | The calling operation continues — the log write is non-fatal by design |

---

## Volume expectations

- Deliverable runs: ~1–3/day per user (scheduled digests)
- Platform syncs: ~4–8/day per user (per platform_connections)
- Memory writes: occasional (user-driven or TP-driven during conversation)
- Chat turns: ~5–20/day per active user

Typical: ~20–40 rows/day per active user. No TTL — rows accumulate over time. At this volume, the table stays small indefinitely.

---

## Related

- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Activity layer design and implementation
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- `api/services/activity_log.py` — `write_activity()`, `get_recent_activity()`
- `api/services/working_memory.py` — `_get_recent_activity()`, prompt injection
- `supabase/migrations/060_activity_log.sql` — Schema
