# ADR-067: Session Compaction and Conversational Continuity

**Status**: Proposed
**Date**: 2026-02-19
**Supersedes**: ADR-049 (Context Freshness Model) — session scope and history management sections
**Related**: ADR-006 (Session and Message Architecture), ADR-064 (Unified Memory Service), ADR-061 (Two-Path Architecture)

---

## Context

### The current model and its problems

YARNNN's current session model (ADR-049) was built on one core assumption:

> *"Sessions are for API coherence (tool_use/tool_result blocks), not context memory. Context continuity comes from deliverable state and platform freshness, not history."*

This assumption was reasonable when YARNNN was primarily a deliverable orchestrator — TP's main job was to create and run deliverables, and those deliverables carried their own state. In practice, as TP has evolved into a more capable conversational assistant, the assumption has three failure modes:

**1. Hard cliff at session boundary.**
The session boundary is UTC midnight. At midnight, the current session ends and a new one begins. The user loses the entire conversation thread. Working memory (user_context) only updates when the nightly cron runs — so preferences stated today are not available until tomorrow morning. The user experiences a sudden reset.

**2. Hard truncation within a session.**
`MAX_HISTORY_TOKENS = 50,000`. When the budget fills, the oldest messages are silently dropped. A productive 3-hour session can exhaust this. TP loses the beginning of its own reasoning with no indication to the user.

**3. Session boundary conflated with backend cron cadence.**
`scope="daily"` in chat.py uses UTC midnight as the session boundary. This is the same boundary used by the nightly memory extraction cron. These are different concerns — conversational continuity versus batch processing — being accidentally treated as the same domain. A user in Singapore who starts a conversation at 11:30pm gets a 30-minute session before a hard reset.

**4. Session summaries never written.**
`chat_sessions.summary` exists in the schema and is referenced in the working memory format as "Recent conversations." It is never populated. The "Recent conversations" block in every working memory prompt renders empty.

### How Claude Code handles this

Claude Code uses **auto-compaction** — a precise mechanism worth understanding before mapping it to YARNNN:

**Trigger**: When input tokens reach ~95% of the context window (roughly 150k of 200k tokens). Not time-based. Not session-boundary-based.

**Mechanism**: When compaction triggers, Claude Code generates a structured summary of the conversation history. Older message blocks are dropped. The summary is prepended to the remaining context as a `compaction` block — treated as content Claude itself previously generated. The model continues from the compaction point with full awareness of prior work.

**Format**: The compaction block wraps the summary in `<summary></summary>` tags and is prepended to the message list. Prior message blocks are dropped. The model receives its own summary as the starting point for continuation.

**What carries over between invocations**: CLAUDE.md (re-read at every session start), auto memory (`MEMORY.md`, maintained by Claude itself, first 200 lines). Raw conversation history from a prior session does not automatically carry over — but the user can explicitly resume via `--continue` or `--resume <session-id>`.

**Session resumption**: Claude Code stores session files locally. `--continue` resumes the most recent session including its full message history (or compaction-reduced history). Sessions are identified by UUID.

### Key insight from the Claude Code model

Claude Code separates two distinct concerns:

| Concern | Mechanism | Boundary |
|---|---|---|
| **In-session continuity** | Message history with auto-compaction | Context window pressure |
| **Cross-session continuity** | CLAUDE.md + auto memory | Explicit (user reads CLAUDE.md; Claude writes memory) |

YARNNN currently conflates both concerns with a single time-based boundary (UTC midnight) and provides no compaction. The result: neither within-session continuity (breaks on overflow) nor cross-session continuity (empty summary block) is reliably served.

---

## Decision

### Two changes, independent of each other

#### Change 1: Session summaries written at natural break points

At the end of each day's session (detected by the nightly cron as "sessions started yesterday with no messages today"), write a `chat_sessions.summary`. This is the YARNNN equivalent of Claude Code's auto memory — a structured prose summary of what the conversation covered.

**Format** (to be injected into working memory "Recent conversations" block):

```
[2026-02-19] Worked on Q2 board update structure — settled on 4-section format
(Overview, Metrics, Risks, Next Steps). User wants financials added. Deliverable
paused; user will provide numbers. Also set up weekly #engineering digest.
```

**Trigger**: Nightly cron (`unified_scheduler.py`, midnight UTC) — same job that processes memory extraction. After processing `process_conversation()` for a session, also call `generate_session_summary()` if the session had sufficient activity (≥ 5 user messages).

**Implementation**: Single LLM call to `memory.py → generate_session_summary()`. Input: full session messages. Output: 2-5 sentence prose summary focused on decisions, in-progress work, and stated intent. Written to `chat_sessions.summary`.

**Working memory injection**: `working_memory.py → build_working_memory()` already has a "Recent conversations" section. Currently empty. Populate it with summaries from the last 3 sessions (within 14-day window), most recent first.

**Token budget impact**: Summaries are short (50-100 tokens each). 3 summaries = ~300 tokens within the existing 2,000 token working memory budget.

#### Change 2: Decouple session boundary from UTC midnight

The `scope="daily"` hard cut at UTC midnight is wrong for two reasons: it is timezone-naive (a user in Singapore gets a 30-minute session at 11:30pm UTC), and it conflates conversational UX with backend scheduling.

**Replace with inactivity-based boundary**: A new session is created when the user sends their first message after N hours of inactivity (default: 4 hours). The specific threshold is configurable; 4 hours captures the natural "different work context" boundary without breaking same-day continuity.

**Implementation in `get_or_create_session()`**: Change the daily RPC logic to check `last_message_at` on the current session instead of `DATE(started_at) = CURRENT_DATE`. If the most recent session's last message was within the inactivity window, reuse it. Otherwise create a new one.

**Backend cron is unaffected**: The nightly cron still runs at midnight UTC. It processes all sessions from the prior day by date range, regardless of when those sessions started or ended. The cron cadence is a scheduling concern; session boundaries are a UX concern.

---

## What is NOT decided here (deferred)

**In-session compaction**: When the 50k token history budget is exhausted, the current behavior is silent truncation from the oldest end. The Claude Code equivalent — generating a summary of the dropped messages and prepending it as a compaction block — is the right long-term fix. This is deferred because:

- 50k tokens covers most practical sessions (approximately 35,000 words of conversation)
- The inactivity boundary change (Change 2) will reduce the likelihood of single-session overflow
- Implementing the compaction block properly requires changes to `build_history_for_claude()` and the message storage format

When implemented, in-session compaction should follow the Claude Code pattern exactly: trigger at ~80% of budget, generate a summary block, prepend it to the remaining messages, drop all prior messages from the API call (but retain them in `session_messages` for audit).

**Session resumption by ID**: `ChatRequest.session_id` exists in the API but is ignored. Explicit session resumption (`--resume` equivalent) is a useful feature for power users. Deferred pending UX design.

**Real-time memory extraction**: Preferences stated during a conversation are currently only available in working memory the next morning (nightly cron). Triggering `process_conversation()` at session close (inactivity boundary detected) would make them available immediately. Deferred to a follow-up.

---

## Implementation plan

### Phase 1 — Session summaries (immediate value, no UX change)

1. Add `generate_session_summary()` to `api/services/memory.py`
   - Input: list of session messages
   - Output: 2-5 sentence prose summary
   - Single LLM call, same model as `process_conversation()`
   - Only called for sessions with ≥ 5 user messages

2. Call from nightly cron (`unified_scheduler.py`) after `process_conversation()`:
   ```python
   summary = await generate_session_summary(client, messages)
   if summary:
       client.table("chat_sessions").update({"summary": summary}).eq("id", session_id).execute()
   ```

3. Update `working_memory.py → build_working_memory()`:
   - Query last 3 `chat_sessions` rows where `summary IS NOT NULL AND started_at > now - 14 days`
   - Format into "Recent conversations" block (already exists, currently empty)

4. Update `api/prompts/CHANGELOG.md` with new working memory block content.

### Phase 2 — Inactivity-based session boundary

1. Add `last_message_at` tracking to `chat_sessions` (via trigger or explicit update on message append)

2. Update `get_or_create_chat_session()` RPC in `supabase/migrations/`:
   - Replace `DATE(started_at) = CURRENT_DATE` logic with inactivity check
   - New logic: find the most recent session for this user; if its `last_message_at` is within 4 hours, return it; otherwise create new
   - Inactivity threshold configurable via env var (`SESSION_INACTIVITY_HOURS`, default 4)

3. Update `chat.py` comment and ADR reference from ADR-049 to ADR-067.

4. Update `docs/features/sessions.md` with new boundary model.

---

## Consequences

### Positive

- **"Recent conversations" block becomes useful** — Phase 1 alone populates the working memory block that's been empty since the field was added
- **Cross-session continuity without raw history** — TP can reference what was discussed last session without needing the full message thread
- **Session boundary matches user intent** — A user starting a new work context after lunch gets a new session; a user continuing a thread from this morning stays in the same session
- **Backend cron is cleanly decoupled** — The nightly job has no dependency on the UX session boundary; it just processes all sessions from the prior day regardless of when they ended

### Negative

- **Session summaries cost tokens** — One additional LLM call per session per night. Low cost (short input, short output), but a real addition to nightly cron runtime.
- **Inactivity threshold is a judgment call** — 4 hours may not be right for all users. May need per-user configuration later.
- **Inactivity model changes session count** — A user who chats for 30 minutes in the morning and 30 minutes in the afternoon may now be in one session instead of two (if within 4 hours). TP conversation limits (ADR-053) count new sessions — this needs a review.

### Neutral

- **Existing session data unchanged** — Old sessions without summaries continue to work; the "Recent conversations" block simply renders empty for them (same as today)
- **API surface unchanged** — No changes to the chat endpoint request/response format

---

## Mapping: Claude Code → YARNNN

| Claude Code mechanism | YARNNN equivalent | Status |
|---|---|---|
| Auto-compaction block | In-session compaction (deferred) | Not yet |
| CLAUDE.md | `user_context` (working memory block) | Live |
| Auto memory (MEMORY.md) | `chat_sessions.summary` injected into working memory | Phase 1 |
| `--continue` / `--resume` | Session resumption by ID (deferred) | Not yet |
| Context-window-driven boundary | Inactivity-based boundary | Phase 2 |
| Per-session `<summary>` block | `chat_sessions.summary` prose block | Phase 1 |

---

## Related

- [Sessions](../features/sessions.md) — Session lifecycle documentation (update after Phase 2)
- [Memory](../features/memory.md) — Memory extraction (nightly cron, same job as session summaries)
- [Backend Orchestration](../features/backend-orchestration.md) — Nightly cron context
- [ADR-049](ADR-049-context-freshness-model.md) — Superseded: session scope and history sections
- [ADR-006](ADR-006-session-message-architecture.md) — Session and message schema
- [ADR-064](ADR-064-unified-memory-service.md) — Memory extraction service (Phase 1 extends this)
- `api/routes/chat.py` — Session creation and history building
- `api/services/working_memory.py` — Working memory assembly
- `api/services/memory.py` — Memory and summary extraction
- `api/jobs/unified_scheduler.py` — Nightly cron (Phase 1 trigger)
- `supabase/migrations/008_chat_sessions.sql` — Session schema (Phase 2 migration)
