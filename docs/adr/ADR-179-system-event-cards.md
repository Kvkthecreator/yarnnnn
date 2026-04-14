# ADR-179: System Event Cards — Chat as Event Log

**Date:** 2026-04-14
**Status:** Proposed
**Deciders:** Kevin
**Extends:** TP-NOTIFICATION-CHANNEL.md (scopes first implementation)
**Governed by:** USER-JOURNEY.md v1.2

---

## Context

Significant system events (workspace init, task triggered, task completed) currently surface as nothing — silent state changes the user has no record of, no way to follow up on, and no sense of the system being alive.

Three gaps this creates:

1. **Cold-start trust gap** — user lands on `/chat` after signup and sees a blank chat with a "tell me about yourself" form. No signal that anything was set up for them.
2. **Task execution feedback gap** — user triggers a task and has no record in chat that it started or finished. On the next session, TP has no conversation history showing what ran.
3. **Onboarding done-state missing** — no moment where the system acknowledges the workspace is set up and work is running.

---

## Decision

**System events are persisted as `session_messages` rows with `role='assistant'` and `metadata.system_card` set. Zero LLM cost. TP reads them as conversation history on every subsequent turn. The frontend renders them as a distinct card component based on the metadata type.**

Two invariants:

1. **Persisted, not ephemeral.** Every system card is a real `session_messages` row. It survives page refresh. TP reads it as history. It is part of the conversation record.
2. **Zero LLM.** Pre-composed content, written by the backend at event time. TP does not generate these. It reads them and continues naturally from them.

The chat stream is a **record of what happened**, not a live process monitor. No in-progress state. Two bookend cards per significant action: start and done.

---

## Mechanism

### Write path — backend

System cards are written by the backend using the existing `append_message()` function in `api/routes/chat.py`:

```python
await append_message(
    client=client,
    session_id=session_id,
    role="assistant",
    content="<plain text TP reads as history>",
    metadata={"system_card": "<card_type>", ...card_data}
)
```

`append_message` already exists, already handles the RPC + fallback insert, already accepts `metadata`. No new infrastructure needed.

The session is resolved via `get_or_create_session()` (also in `chat.py`) before the write. If no session exists for the user yet, one is created.

### Read path — frontend

The frontend chat history fetch already returns `metadata` on each message. When rendering a message:

- `metadata.system_card` present → render `<SystemCard type={metadata.system_card} data={metadata} />`
- `metadata.system_card` absent → render as normal TP message

TP sees the `content` field as plain prose — no markdown cards, no structured data. The metadata is frontend-only rendering context.

---

## System Cards — Defined Set

### `workspace_init_complete`

**When:** `initialize_workspace()` completes with `already_initialized == False` inside `GET /user/onboarding-state` (`api/routes/memory.py`).

**Written by:** `get_onboarding_state()` — after `initialize_workspace()` returns, resolve/create the user's TP session, write the card.

**Content (what TP reads):**
```
Your workspace is ready. I've set up 9 agents, scaffolded your directories, and scheduled a daily update at 9am. Tell me what you work on and I'll set up the rest.
```

**Metadata:**
```json
{
  "system_card": "workspace_init_complete",
  "agents_created": 9,
  "tasks_created": ["daily-update", "back-office-agent-hygiene", "back-office-workspace-cleanup"]
}
```

**TP reads it as:** why the workspace is in a fresh state. On the user's first message, TP continues naturally — no need to re-explain or re-introduce.

---

### `task_triggered`

**When:** `ManageTask(action="trigger")` returns successfully and the trigger was user-initiated (via TP response or TaskSetup submission).

**Written by:** Not a separate card. When TP triggers a task mid-conversation, its response text already contains the acknowledgement ("I've triggered Track Competitors — first results in a few minutes"). No duplicate card needed. The TP response itself is the record.

For future non-TP triggers (e.g. a manual "Run now" button on `/work`), a card would be written at that point. Out of scope for Phase 1.

---

### `task_complete`

**When:** `execute_task()` completes successfully in `api/services/task_pipeline.py`.

**Written by:** End of `execute_task()`, after output is written and delivery fires. Resolve the user's active TP session. If a session exists and was active within the last 4 hours (same inactivity window as `get_or_create_session`), write the card. If no active session, skip — working memory covers it on next open.

**Content (what TP reads):**
```
Track Competitors finished its first run. Output is in /tasks/track-competitors/outputs/latest/.
```

**Metadata:**
```json
{
  "system_card": "task_complete",
  "task_slug": "track-competitors",
  "task_title": "Track Competitors",
  "output_path": "/tasks/track-competitors/outputs/latest/",
  "run_at": "2026-04-14T09:03:11Z"
}
```

**Frontend renders:** "Track Competitors finished. [View →]" — link routes to `/work?task=track-competitors`.

**TP reads it as:** confirmation that the task ran. If the user follows up ("what did it find?"), TP can call `ReadFile` on the output path directly from this history context.

---

### Not a card: background scheduled runs

Recurring tasks that run on schedule (not user-triggered) do not produce cards. The daily-update email + working memory on next session open is sufficient. Cards for every background run would add noise to the conversation history with no conversational value.

---

## What This Is Not

- **Not ephemeral.** Cards are `session_messages` rows — they persist, survive refresh, and are part of TP's conversation history.
- **Not a progress bar.** No mid-execution updates. Start (TP's own response) + done (completion card).
- **Not a toast.** Toasts disappear. Cards are permanent conversation history.
- **Not TP-generated.** TP reads these, it does not write them.
- **Not a notification center.** Chat is the only channel.

---

## Implementation

### Phase 1 — `workspace_init_complete` card

| What | File | Detail |
|------|------|--------|
| Write init card after `initialize_workspace()` | `api/routes/memory.py` — `get_onboarding_state()` | Call `get_or_create_session()` + `append_message()` from `chat.py`. Only when `already_initialized == False`. |
| `SystemCard` component | `web/components/chat-surface/SystemCard.tsx` (new) | Renders based on `metadata.system_card`. Reuses `InlineActionCard` visual pattern. |
| Chat history rendering | `web/components/chat-surface/ChatMessageList.tsx` or equivalent | Check `metadata.system_card` on each message — render `SystemCard` instead of prose. |
| Chat-visible guarantee on ContextSetup submit | `web/components/chat-surface/ContextSetup.tsx` | Modal dismiss → chat panel in view, scrolled to bottom, TP response streaming. |

### Phase 2 — `task_complete` card

| What | File | Detail |
|------|------|--------|
| Write completion card | `api/services/task_pipeline.py` — end of `execute_task()` | Resolve active session (4h window). Write card if session found. Skip if not. |
| Frontend renders completion card | `web/components/chat-surface/SystemCard.tsx` | `task_complete` variant — task title + "View →" link. |
| Realtime push (optional) | Supabase realtime subscription on `session_messages` | If user is in `/chat` when card is written, it appears without refresh. Falls back gracefully to next load. |

### Out of scope

- FAB ambient state (Working/Notified/Attention) — TP-NOTIFICATION-CHANNEL.md future
- Cards for background scheduled runs
- `task_triggered` card (covered by TP response text)

---

## Relation to Existing Infrastructure

| Existing piece | Role in this ADR |
|---------------|-----------------|
| `append_message()` in `chat.py` | Write path for all system cards — already handles RPC + fallback insert + metadata |
| `get_or_create_session()` in `chat.py` | Session resolution before every card write |
| `session_messages.metadata` column | Already exists, already returned in history fetch |
| `initialize_workspace()` in `workspace_init.py` | Returns `already_initialized` flag — gates the init card write |
| `execute_task()` in `task_pipeline.py` | Write point for `task_complete` card |
| `InlineActionCard` | Visual pattern for `SystemCard` component |

No new tables. No new API endpoints. No new columns. The entire mechanism runs on existing infrastructure.

---

## Rejected Alternatives

**Frontend-seeded messages** — rejected. A message that only exists in the browser is invisible to TP, lost on refresh, and not part of the conversation record. System cards must be persisted as `session_messages` rows to have any value as TP context.

**Progress cards / streaming task state** — rejected. Task execution is 30–120 seconds. Users are not watching the screen. Progress creates anxiety without payoff and adds polling complexity for no UX gain.

**Dedicated notification center** — rejected. A separate notification UI fragments attention. Chat history already persists. The mental model should be: "check chat to see what happened."

**TP-generated event summaries** — rejected. TP generating a message for every system event induces unnecessary LLM calls and tokens. TP's role is judgment and conversation, not narrating deterministic system actions.
