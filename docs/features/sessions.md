# Sessions

> How TP conversations start, continue, and end — and what carries over between them.

---

## The short version

- One session per day (UTC). New day = new session.
- Within a session, TP has the full conversation history (up to a token budget).
- Across sessions, TP only knows what's in **working memory** — profile, preferences, recent activity, active deliverables. Raw conversation history does not carry over.
- There is no summarization. Old messages are just truncated when the budget fills.
- There is no explicit session close. Sessions stay `active` indefinitely.

---

## Session lifecycle

### Starting a session

Every chat message goes through `get_or_create_session()` in [chat.py](../../api/routes/chat.py). The default scope is `"daily"`:

- **If a session already exists for today** (UTC date match): reuse it
- **If not**: create a new `chat_sessions` row

The daily boundary is a hard UTC midnight cutoff — `DATE(started_at) = CURRENT_DATE` in the Supabase RPC. First message after midnight creates a fresh session regardless of how recent the last one was.

### Within a session

Every user message and assistant response is appended to `session_messages` with a monotonically increasing `sequence_number`. Tool calls and results are stored in the assistant message's `metadata.tool_history` so they can be reconstructed as proper `tool_use`/`tool_result` blocks on subsequent turns (required by the Anthropic API).

When building context for each new message, the last 50 messages are fetched (ordered by sequence) and truncated to a **50,000 token budget** — most recent messages win. No compression, no summarization — just a hard cut from the oldest end.

### Ending a session

There is no explicit session close. Sessions stay `active` until the next day creates a new one. `ended_at` exists in the schema but is never set by any current code.

---

## What carries over between sessions

When a new session starts, TP gets a fresh **working memory block** injected into its system prompt. This is the only cross-session continuity mechanism.

| What's in working memory | Source | How it gets there |
|---|---|---|
| Name, role, company, timezone | `user_context` | User sets via Context page |
| Tone and verbosity preferences | `user_context` | User sets or nightly extraction |
| Facts, instructions, preferences | `user_context` | User sets or nightly extraction |
| Active deliverables (up to 5) | `deliverables` | Always live |
| Connected platforms + sync freshness | `platform_connections` | Always live |
| Recent activity (last 10 events, 7-day window) | `activity_log` | Written by pipeline + sync |
| Recent session summaries | `chat_sessions.summary` | Not currently generated |

**What does NOT carry over:**
- Raw conversation history (previous sessions' messages are not fetched)
- Tool execution results
- Anything TP inferred but didn't explicitly learn during the session

### Memory extraction from conversations

Preferences stated during a conversation are extracted by the **nightly cron** (`unified_scheduler.py`, midnight UTC) which processes all prior day's sessions in batch. A preference stated today becomes part of working memory tomorrow morning.

There is no real-time session-end extraction wired yet. The Context page is the only way to get something into working memory immediately.

---

## Contrast with Claude Code

Claude Code compacts conversation history via auto-summarization when context fills up. YARNNN does not do this — the design decision (ADR-049) is that sessions are for **API coherence** (tool_use/tool_result pairing), not memory. Context continuity comes from working memory and live platform reads, not conversation history.

| | Claude Code | YARNNN |
|---|---|---|
| Session boundary | Unlimited (compacts on overflow) | Daily (UTC midnight) |
| History in session | Compressed when full | Truncated (oldest dropped) |
| Cross-session memory | CLAUDE.md + compacted history | Working memory block (user_context + deliverables + activity) |
| Summarization | Auto-compaction | Not implemented |
| Session end | Explicit close / context limit | None (always active) |

The practical implication: if a user had a long conversation yesterday about their preferences, TP won't remember the conversation details today — but it will know the extracted preferences (after the nightly cron runs).

---

## Known gaps

1. **No real-time extraction** — preferences from a conversation land in working memory overnight, not immediately.
2. **No session summaries** — `chat_sessions.summary` is never written, so the "Recent conversations" block in working memory always renders empty.
3. **No explicit close** — sessions accumulate as `active` indefinitely.
4. **`session_id` parameter ignored** — `ChatRequest.session_id` exists but the backend always uses daily-scope auto-create; users can't resume a specific old session from the frontend.

---

## Related

- [Memory](./memory.md) — what persists across sessions and how it's written
- [ADR-049](../adr/ADR-049-context-freshness-model.md) — why no summarization
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — activity log in working memory
- `api/routes/chat.py` — session creation, message append, history building
- `supabase/migrations/008_chat_sessions.sql` — schema and RPC
- `api/services/working_memory.py` — what TP receives at session start
