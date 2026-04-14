# ADR-179: System Event Cards — Chat as Event Log

**Date:** 2026-04-14
**Status:** Proposed
**Deciders:** Kevin
**Extends:** ADR-155 (TP Notification Channel — scopes first implementation)
**Governed by:** USER-JOURNEY.md v1.2

---

## Context

Significant system events (workspace init, task triggered, task completed) currently surface as nothing — silent state changes, maybe a toast that disappears. The user has no record of what happened, no way to follow up conversationally, and no sense of the system being alive.

Three gaps this creates:

1. **Cold-start trust gap** — user lands on `/chat` after signup and sees a blank chat with a "tell me about yourself" form. No signal that anything was set up.
2. **Task execution feedback gap** — user triggers a task (manually or via TP) and has no record in chat that it started or finished. Next session, TP has no chat-history context for what ran.
3. **Onboarding "done" state missing** — no moment where the system acknowledges the workspace is set up and running.

The existing TP notification channel design (TP-NOTIFICATION-CHANNEL.md) describes a full vision with FAB states, progress tracking, and rich notification types. This ADR scopes the first implementation to what's actually needed.

---

## Decision

**System events produce pre-composed assistant messages (system cards) in the TP chat stream. No LLM call. TP reads them as history on the next real turn.**

The chat stream is a **record of what happened**, not a live process monitor. No in-progress state. Two bookend cards per significant action: one when it starts, one when it finishes.

---

## Principles

1. **Zero LLM for system cards.** Pre-composed text, written by the frontend or backend at event time. TP does not generate these — it reads them.
2. **No progress tracking.** Users aren't waiting at the screen for 30–120 second task executions. A start card + completion card is sufficient. No polling, no streaming updates.
3. **Chat must be visible when TP is responding.** When ContextSetup submits, the modal closes and the chat panel is in view, scrolled to bottom, with TP's response streaming in. This is the only moment that requires a real TP turn — and it already is one.
4. **Session-closed events are covered by working memory.** If a task completes when no session is open, no card is queued. TP's working memory already surfaces task run timestamps — on next session open, TP knows what ran while the user was away.

---

## System Cards — Defined Set

### Card: `workspace_init_complete`

**Trigger:** Auth callback completes `initialize_workspace()`, user lands on `/chat` for the first time.
**Mechanism:** Frontend seeds this as the first assistant message in the empty session, from the init result returned by the callback. No API call needed — the callback already returns the init summary.

**Content:**
```
Your workspace is ready.

9 agents · 3 tasks · daily update scheduled for 9am

Tell me what you work on and I'll set things up from there.
```

**TP reads it as:** context for why the workspace is in a fresh state. Proceeds naturally from the user's first message.

---

### Card: `task_triggered`

**Trigger:** `ManageTask(action="trigger")` returns successfully — either from TP mid-conversation, or from a TaskSetup submission.
**Mechanism:** TP's response text already acknowledges the trigger. No separate card needed if TP is the one triggering. If triggered outside a TP turn (future — manual trigger button), frontend writes the card.

**Content:**
```
[Task name] is running — first results in a few minutes.
```

---

### Card: `task_complete`

**Trigger:** `execute_task()` completes in the scheduler. Session must be open to receive the card.
**Mechanism:** Scheduler writes a completion event to a lightweight queue. Frontend polls or receives via Supabase realtime. If session is open, renders the card at the bottom of chat. If session is closed, discards — working memory covers it.

**Content:**
```
[Task name] finished.  [View →]
```

The `[View →]` link routes to `/work?task=[slug]`.

---

### Not a card: background scheduled runs

Recurring tasks that run on schedule (not triggered mid-session) do not produce cards. The daily-update email + working memory on next session open is sufficient signal. Adding cards for every background run would create noise in the chat history.

---

## What This Is Not

- **Not a progress bar.** No streaming updates mid-execution.
- **Not a toast.** Cards persist in chat history. Toasts disappear.
- **Not a TP-generated message.** TP does not write these. They are pre-composed.
- **Not a notification center.** There is no separate notification UI. Chat is the only channel.
- **Not a replacement for the daily-update.** Background scheduled runs are covered by the daily-update email, not cards.

---

## Implementation Scope

### Phase 1 — init card + ContextSetup visibility (frontend only)

| What | Where | Notes |
|------|-------|-------|
| Seed `workspace_init_complete` card | `web/app/auth/callback/page.tsx` | Init result already returned — use it to compose the message and insert as first session message |
| Chat-visible guarantee on ContextSetup submit | `web/components/chat-surface/ContextSetup.tsx` | Modal dismiss → chat panel in view, scrolled to bottom |

### Phase 2 — task completion cards

| What | Where | Notes |
|------|-------|-------|
| Scheduler writes completion event | `api/services/task_pipeline.py` | Lightweight write — slug, title, completed_at, output path |
| Frontend subscribes via Supabase realtime | `web/contexts/TPContext.tsx` or `web/hooks/useTaskCompletionCards.ts` | Filter to current user, session-open only |
| Render completion card | `web/components/chat-surface/SystemCard.tsx` (new) | Reuses InlineActionCard visual pattern |

### Out of scope for Phase 1+2

- FAB ambient state (Working/Notified/Attention) — TP-NOTIFICATION-CHANNEL.md future extension
- In-progress task state
- Cards for background scheduled runs
- Rich notification type variants beyond init + task

---

## Relation to Existing Patterns

- **InlineActionCard** — system cards reuse this visual pattern (border, icon, content, optional action link). Same component, `type="system"` variant.
- **TP-NOTIFICATION-CHANNEL.md** — this ADR implements the first phase of that design. FAB states and queued notifications are future extension.
- **working_memory.py** — out-of-session task completion coverage. Cards and working memory are complementary, not redundant: cards are in-session real-time; working memory is cross-session awareness.
- **ADR-155** — inference side effects (UpdateContext tool results) already surface via TP's natural response text. No separate card needed for inference events.

---

## Rejected Alternatives

**Progress cards / streaming task state** — rejected. Task execution is 30–120 seconds. Users are not watching the screen. Progress creates anxiety without payoff and adds polling complexity for no UX gain. Two bookend cards (start + done) are sufficient.

**Dedicated notification center** — rejected. A separate notification UI fragments attention and adds surface area. Chat history already persists. The user's mental model should be: "check chat to see what happened," not "check notifications AND chat."

**TP-generated event summaries** — rejected. TP generating a message for every system event induces unnecessary LLM calls and tokens. TP's role is judgment and conversation, not narrating its own tool calls. Pre-composed cards are cheaper, faster, and more consistent.
