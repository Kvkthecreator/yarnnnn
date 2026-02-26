# ADR-067: Session Architecture — Follow Claude Code's Model Fully

**Status**: Implemented
**Date**: 2026-02-19
**Supersedes**: ADR-049 (Context Freshness Model) — session scope and history management sections
**Related**: ADR-006 (Session and Message Architecture), ADR-064 (Unified Memory Service), ADR-061 (Two-Path Architecture)

---

## Context

### The current model and its problems

YARNNN's current session model (ADR-049) was built on one core assumption:

> *"Sessions are for API coherence (tool_use/tool_result blocks), not context memory. Context continuity comes from deliverable state and platform freshness, not history."*

This was wrong in practice, and has produced four compounding gaps:

**1. Hard cliff at session boundary.**
The session boundary is UTC midnight. At midnight, the current session ends and a new one begins with no thread continuity. Working memory updates overnight — preferences stated today are not available until tomorrow. The user experiences a sudden reset.

**2. Hard truncation within a session with no recovery.**
`MAX_HISTORY_TOKENS = 50,000`. When the budget fills, the oldest messages are silently dropped — no summary, no indication, no recovery. In YARNNN this happens faster than in a typical Claude Code session: live platform tool calls (Slack reads, Gmail searches, Notion fetches) bulk up history at 2-5k tokens per turn. A user doing a multi-step platform workflow exhausts this within a single productive session.

**3. Session boundary conflated with backend cron cadence.**
`scope="daily"` uses UTC midnight as the session boundary — the same boundary as the nightly cron. These are different concerns. A user in Singapore at 11:30pm UTC gets a 30-minute session before a hard reset. The backend cron should run on its own schedule, independent of when a conversation ends.

**4. Session summaries never written.**
`chat_sessions.summary` exists in the schema and is already queried by `working_memory.py → _get_recent_sessions()` and rendered in `format_for_prompt()` as "Recent conversations." The infrastructure is fully built. The column is just never populated. Every working memory prompt renders an empty "Recent conversations" block.

### Why Claude Code's model applies directly — and more urgently

Claude Code operates in a static environment (codebase). YARNNN operates in a dynamic one (live platform data). This makes compaction *more* necessary for YARNNN:

- Tool results from live platform reads (Slack history, Gmail threads, Notion pages) are large and consume history budget fast
- The conversational surface is richer — users iteratively refine deliverables, discuss preferences, review content — all of which produces history that is contextually important but quickly fills the window
- Working memory updates overnight, not in real-time — so within-session context is the only continuity mechanism a user has during the day

Claude Code's three mechanisms solve exactly these problems. There is no architectural reason to deviate from them.

### The three Claude Code mechanisms and YARNNN's infrastructure status

| Claude Code mechanism | YARNNN equivalent | Infrastructure |
|---|---|---|
| Auto-compaction (context-window trigger) | In-session compaction | `build_history_for_claude()` exists; needs compaction path |
| CLAUDE.md (re-read at session start) | `user_context` working memory block | Live and working |
| Auto memory (MEMORY.md, written by Claude) | `chat_sessions.summary` | Schema + reader exist; writer missing |
| Context-window boundary | Inactivity-based boundary | One RPC change in Supabase migration |

The session summary reader and formatter (`_get_recent_sessions()`, `format_for_prompt()`) are already implemented in `working_memory.py:242-273`. The "Recent conversations" section already renders — it just has nothing to render. The missing piece is the writer.

---

## Decision

Follow Claude Code's session architecture fully. Three changes, all decided here:

### 1. Auto-compaction (in-session)

**Trigger**: When `build_history_for_claude()` detects that the selected messages would exceed **80% of `MAX_HISTORY_TOKENS`** (40,000 of 50,000 tokens), trigger compaction instead of silent truncation.

**Mechanism** (following Claude Code exactly):

1. Take the messages that would be truncated (the oldest portion)
2. Make a single LLM call to generate a compaction summary of those messages
3. Prepend the summary as an assistant-role "compaction block" to the remaining (recent) messages
4. Drop the original truncated messages from the API call — they are retained in `session_messages` for audit, but not sent to the model

**Format** (matching Claude Code's `<summary>` pattern):

```python
compaction_block = {
    "role": "assistant",
    "content": [{
        "type": "text",
        "text": f"<summary>\n{compaction_text}\n</summary>"
    }]
}
```

The model receives the compaction block as the first message in its history — content it previously generated — followed by the recent messages. All prior message blocks are absent from the API call.

**Compaction prompt** (analogous to Claude Code's default):

> "Summarise the conversation above for continuity. The reader will have no access to the original messages — only this summary. Focus on: decisions made, work in progress, user preferences stated, platform actions taken, and anything left unresolved."

**Storage**: Write the compaction summary to `chat_sessions.compaction_summary` (new column). On subsequent turns, if a compaction exists for the session, prepend it before the recent message window — do not re-generate.

**Why 80% trigger**: Compacting at 80% (40k of 50k tokens) leaves headroom for the compaction LLM call itself and ensures the summary is generated while the full context is still available, not in extremis.

### 2. Session summaries (cross-session auto memory)

At the end of each session (detected by the nightly cron: sessions started yesterday, processed during memory extraction), generate a `chat_sessions.summary`.

**This is the YARNNN equivalent of Claude Code's auto memory (MEMORY.md)** — a persistent, concise record of what the conversation produced that carries forward to the next session's working memory.

**Trigger**: Nightly cron (`unified_scheduler.py`, midnight UTC), after `process_conversation()` for each session. Called for sessions with ≥ 5 user messages.

**Implementation**: Add `generate_session_summary()` to `api/services/memory.py`. Single LLM call. Input: full session messages. Output: 2-5 sentence prose summary focused on decisions, in-progress work, and stated intent.

**Example**:
> [2026-02-19] Worked on Q2 board update — settled on 4-section structure (Overview, Metrics, Risks, Next Steps). User wants financials added; deliverable paused pending numbers. Also set up weekly #engineering digest.

**Working memory injection**: `_get_recent_sessions()` in `working_memory.py` already queries `chat_sessions.summary` and the `format_for_prompt()` function already renders "Recent conversations." No changes needed to the reader path — only the writer (nightly cron) needs to be wired.

**Token budget**: Summaries are short (50-100 tokens each). 3 summaries within a 14-day window = ~300 tokens within the existing 2,000 token working memory budget.

### 3. Inactivity-based session boundary

**Replace** `DATE(started_at) = CURRENT_DATE` (UTC midnight hard cut) with an inactivity-based boundary.

**Rule**: Find the most recent session for this user. If its `last_message_at` is within N hours (default: **4 hours**), reuse it. Otherwise create a new session.

**Why 4 hours**: Captures the natural "different work context" gap (e.g., morning work vs. evening work) without breaking same-working-session continuity. This threshold should eventually be user-configurable.

**Backend cron is unaffected**: The nightly cron continues to run at midnight UTC. It processes all sessions from the prior calendar day by date range (`created_at` between yesterday and today). The cron cadence is a scheduling concern; session boundaries are a UX concern. They are now fully decoupled.

**Implementation**: Update `get_or_create_chat_session()` RPC in Supabase. Requires adding `last_message_at` to `chat_sessions` (via trigger on `session_messages` insert, or explicit update in `append_message()`).

---

## What is explicitly deferred

**Session resumption by ID**: `ChatRequest.session_id` exists in the API but is ignored. Explicit session resumption (`--resume` equivalent) is useful but requires frontend UX design. Deferred.

**Real-time memory extraction on session close**: When the inactivity boundary triggers (new session created after 4h silence), the prior session could be immediately processed for memory extraction rather than waiting until midnight. This is a natural extension of Phase 2 — deferred to a follow-up.

**Compaction for tool result payloads**: Large tool results (full Slack history, Gmail threads) could be individually summarised before being stored in `session_messages`, reducing per-turn token cost before compaction is even needed. Deferred — the session-level compaction handles this indirectly.

---

## Implementation sequence

### Phase 1 — Session summaries (writer side) — ~30 lines

No infrastructure changes. Just wire the nightly cron writer:

1. Add `generate_session_summary(client, messages) -> str` to `api/services/memory.py`
2. In `unified_scheduler.py`, after `process_conversation()` for each session, call it and write to `chat_sessions.summary`
3. The reader path in `working_memory.py` and `format_for_prompt()` already works — "Recent conversations" block will populate immediately

### Phase 2 — Inactivity boundary — migration + one function change

1. Add `last_message_at TIMESTAMPTZ` to `chat_sessions` schema
2. Add trigger on `session_messages` insert to update `chat_sessions.last_message_at`
3. Update `get_or_create_chat_session()` RPC: replace date-equality check with inactivity window check
4. Update `chat.py` comment from ADR-049 to ADR-067

### Phase 3 — In-session compaction — `build_history_for_claude()` + new column

1. Add `compaction_summary TEXT` to `chat_sessions` schema
2. In `build_history_for_claude()`: after truncation calculation, check if truncated tokens > 40k threshold; if so, call compaction LLM and write to `chat_sessions.compaction_summary`
3. At session history load in `chat.py`: if `compaction_summary` exists for session, prepend compaction block to `existing_messages` before passing to `build_history_for_claude()`
4. Update `get_session_messages()` to also return session-level `compaction_summary`

---

## Consequences

### Positive

- **Continuous conversational thread** — within a session (compaction) and across sessions (summaries), TP maintains coherent context
- **No more silent truncation** — when history fills, the model gets a summary of what was dropped, not a blind cut
- **"Recent conversations" block useful from day one** — Phase 1 alone populates what has always been empty
- **Session boundary reflects UX intent** — a 4-hour gap creates a new session; picking up a thread after 30 minutes doesn't
- **Backend and UX concerns fully decoupled** — nightly cron schedule and session boundary are independent

### Negative

- **Compaction costs tokens** — one additional LLM call per session when the budget threshold is hit; and one per session per night for the summary. Both are small inputs → small outputs.
- **Inactivity threshold is a judgment call** — 4 hours may not suit all users or all timezones. Future: per-user preference.
- **ADR-053 TP conversation limits need review** — currently counts new sessions; inactivity-based boundary changes session creation frequency.

### Neutral

- **Existing session data unchanged** — old sessions without summaries or compaction work as before; "Recent conversations" renders empty for them (same as today)
- **API surface unchanged** — no changes to `/chat` request/response format
- **`session_messages` audit log preserved** — compaction drops messages from API calls but retains them in the DB

---

## Mapping: Claude Code → YARNNN (final)

| Dimension | Claude Code | YARNNN (after ADR-067) |
|---|---|---|
| **In-session overflow** | Auto-compaction block, prepended to remaining history | Same mechanism, triggered at 80% of 50k token budget |
| **Cross-session memory** | CLAUDE.md (rules) + auto memory MEMORY.md (learned) | `user_context` (rules/preferences) + `chat_sessions.summary` (learned) |
| **Session boundary** | Context-window-driven | Inactivity-based (4h default) |
| **Compaction format** | `<summary>` block as assistant content | Same |
| **Summary writer** | Claude writes to MEMORY.md during compaction | Nightly cron writes to `chat_sessions.summary` |
| **Session resumption** | `--continue` / `--resume <id>` | Deferred |

---

## Related

- [Sessions](../features/sessions.md) — Session lifecycle documentation
- [Memory](../features/memory.md) — Memory extraction (nightly cron, same job as session summaries)
- [Backend Orchestration](../architecture/backend-orchestration.md) — Nightly cron context (independent domain)
- [ADR-049](ADR-049-context-freshness-model-SUPERSEDED.md) — Superseded: session scope and history sections
- [ADR-006](ADR-006-session-message-architecture.md) — Session and message schema
- [ADR-064](ADR-064-unified-memory-service.md) — Memory extraction service (Phase 1 extends this)
- `api/routes/chat.py` — Session creation, history building
- `api/services/working_memory.py` — Working memory assembly (reader already built)
- `api/services/memory.py` — Memory and summary extraction
- `api/jobs/unified_scheduler.py` — Nightly cron (Phase 1 trigger)
- `supabase/migrations/008_chat_sessions.sql` — Session schema (Phase 2 + 3 migrations)
