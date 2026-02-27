# Sessions

> How TP conversations start, continue, and end — and what carries over between them.

---

## The short version (current model — ADR-067 implemented)

- Sessions use **inactivity-based boundaries** (4-hour gap = new session). The UTC midnight hard cut was removed.
- Within a session, TP has the full conversation history (up to a 50,000 token budget).
- **In-session compaction** triggers at 80% of budget — a summary block is prepended rather than silently truncating oldest messages.
- Across sessions, TP knows what's in **working memory** — profile, preferences, recent activity, active deliverables, and **recent session summaries** (last 3 within 14-day window).
- Session summaries are written by the nightly cron to `chat_sessions.summary`.

---

## Session lifecycle

### Starting a session

Every chat message goes through `get_or_create_session()` in [chat.py](../../api/routes/chat.py):

- **If a session exists with activity within the last 4 hours**: reuse it (inactivity-based boundary, ADR-067)
- **If not**: create a new `chat_sessions` row

The previous UTC midnight hard cut was replaced with an inactivity-based boundary in ADR-067. A user continuing a thread from this morning stays in the same session; a user starting after a 4+ hour gap gets a new one. The nightly cron continues to run at UTC midnight regardless — backend scheduling and session management are decoupled.

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
| Recent session summaries | `chat_sessions.summary` | **Not currently written — always empty** |

**What does NOT carry over:**
- Raw conversation history (previous sessions' messages are not fetched)
- Tool execution results
- Anything TP inferred but didn't explicitly learn during the session

### Memory extraction from conversations

Preferences stated during a conversation are extracted by the **nightly cron** (`unified_scheduler.py`, midnight UTC) which processes all prior day's sessions in batch. A preference stated today becomes part of working memory tomorrow morning.

There is no real-time session-end extraction. The Context page is the only way to get something into working memory immediately.

---

## Contrast with Claude Code

Claude Code uses auto-compaction — context-window-pressure-driven, not time-based — and maintains cross-session continuity via CLAUDE.md and auto memory.

| | Claude Code | YARNNN (ADR-067 implemented) |
|---|---|---|
| **Session boundary** | Context-window-driven | Inactivity-based (4h default) |
| **In-session overflow** | Auto-compaction (`<summary>` block prepended) | Compaction at 80% of 50k token budget |
| **Cross-session memory** | CLAUDE.md + auto memory (MEMORY.md) | `user_context` + deliverables + activity + `chat_sessions.summary` |
| **Session summaries** | Auto-generated during compaction | Written by nightly cron |
| **Session resumption** | `--continue` / `--resume <id>` | Not supported (session_id ignored, deferred) |

The practical implication today: if a user had a long conversation yesterday about their preferences, TP won't remember the conversation details today — but it will know the extracted preferences (after the nightly cron runs).

---

## Architecture direction (ADR-067)

[ADR-067](../adr/ADR-067-session-compaction-architecture.md) follows Claude Code's session model fully — three changes, all decided:

### Phase 1 — Session summaries (cross-session auto memory)

The YARNNN equivalent of Claude Code's auto memory (MEMORY.md). The nightly cron writes a prose summary to `chat_sessions.summary` after processing memory extraction for each session. The "Recent conversations" working memory block — currently always empty — is populated with the last 3 summaries within a 14-day window.

The reader is already built: `working_memory.py → _get_recent_sessions()` queries `chat_sessions.summary` and `format_for_prompt()` renders "Recent conversations." Only the writer (nightly cron) needs wiring — ~30 lines.

**Example summary**:
> [2026-02-19] Worked on Q2 board update — settled on 4-section structure. User wants financials added; deliverable paused pending numbers. Also set up weekly #engineering digest.

### Phase 2 — Inactivity-based session boundary

The UTC midnight hard cut is replaced with an inactivity-based boundary (default: 4 hours). A user continuing a thread from this morning stays in the same session; a user starting a new work context after a break gets a new one.

The nightly cron continues to run at UTC midnight regardless — backend scheduling and conversational session management are now decoupled.

### Phase 3 — In-session compaction

The YARNNN equivalent of Claude Code's auto-compaction. When the history budget reaches 80% (40k of 50k tokens), instead of silently truncating the oldest messages, a compaction summary is generated and prepended as an assistant-role `<summary>` block. The model continues from the compaction point with full awareness of prior work — the same mechanism Claude Code uses.

Compaction text is stored in `chat_sessions.compaction_summary` and reused on subsequent turns — the summary is generated once per overflow event, not on every turn.

---

## Remaining gaps

1. **No real-time extraction** — preferences from a conversation land in working memory overnight, not immediately. *(Deferred in ADR-067)*
2. **No explicit close** — sessions accumulate as `active` indefinitely; `ended_at` is never set.
3. **`session_id` parameter ignored** — `ChatRequest.session_id` exists but the backend always uses inactivity-scope auto-create; users can't resume a specific old session from the frontend. *(Deferred in ADR-067)*

### Resolved (ADR-067)
- Session summaries — nightly cron writes `chat_sessions.summary`; "Recent conversations" block populates
- In-session compaction — `maybe_compact_history()` triggers at 80% budget; `<summary>` block prepended
- UTC midnight boundary — replaced with 4-hour inactivity check; nightly cron decoupled

---

## Related

- [Memory](./memory.md) — what persists across sessions and how it's written
- [Backend Orchestration](../architecture/backend-orchestration.md) — nightly cron context (different domain from session management)
- [ADR-067](../adr/ADR-067-session-compaction-architecture.md) — Session compaction and continuity architecture (implemented)
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — activity log in working memory
- `api/routes/chat.py` — session creation, message append, history building
- `supabase/migrations/008_chat_sessions.sql` — schema and RPC
- `api/services/working_memory.py` — what TP receives at session start
