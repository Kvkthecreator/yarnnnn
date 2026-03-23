# ADR-135: Chat as Coordination Substrate

> **Status**: Proposed
> **Date**: 2026-03-23
> **Authors**: KVK, Claude
> **Supersedes**: Activity-event-only PM communication (ADR-126 agent_pulsed events)
> **Evolves**: ADR-124 (Meeting Room), ADR-128 (Coherence Protocol), ADR-133 (PM Phase Dispatch)

---

## Context

The PM agent has multiple decision surfaces (pulse, headless run, chat) that don't coordinate. PM decisions are logged as activity events — machine-readable audit records invisible in the chat timeline. The user sees "PM pulsed — unknown" instead of meaningful coordination messages.

Meanwhile, the project chat session exists as a persistent conversation surface (24h rotation, ADR-125). It already supports agent-attributed messages with role-colored bubbles. But only user-initiated conversations produce messages — autonomous PM coordination is invisible.

### The insight

A real team communicates through a shared channel. The PM announces decisions. Contributors report completions. Handoffs are visible. Status updates are natural language, not log entries.

The project chat session should BE this coordination channel — not just for user↔agent conversation, but for agent↔agent communication visible to the user.

---

## Decision

### Chat session is the primary coordination surface

When agents take significant autonomous actions, they write a message to the project chat session. These messages are:
- **Attributed** — tagged with `author_agent_id`, `author_agent_slug`, `author_role`
- **Visible** — appear in the chat timeline alongside user messages
- **Natural language** — written as a team member would communicate, not as log entries
- **Durable** — persist in session_messages (24h rotation with compaction summary)

### What gets written to chat

| Event | Author | Example Message |
|-------|--------|----------------|
| PM dispatches contributor | PM | "Dispatching @slack-briefer — platform data is fresh, time for the daily recap" |
| Contributor completes run | Contributor | "Recap complete. 12 items across 5 channels. Key finding: pricing discussion in #product" |
| PM advances phase | PM | "Phase 1 complete. Moving to synthesis — @board-writer, your brief is ready" |
| PM triggers assembly | PM | "All contributions ready. Assembling and delivering now" |
| PM detects issue | PM | "Briefer output is thin (3 items). May need more platform data" |
| Assembly delivered | PM | "Delivered: Quarterly Review v2 → board@company.com" |
| PM escalates | PM | "Need help: missing analyst capability for this objective. @composer?" |

### What stays as activity events only

Activity events remain as the **audit trail** — machine-readable, filterable, structured metadata. They don't go away. But they're no longer the user-facing surface for PM coordination.

| Event | Still logged as activity? | Also written to chat? |
|-------|--------------------------|----------------------|
| agent_pulsed (tier 1 wait) | Yes | No — too noisy |
| agent_pulsed (tier 2 observe) | Yes | No — too noisy |
| pm_pulsed (tier 3 coordination) | Yes | **Yes — PM announces decisions** |
| contributor_dispatched | Yes | **Yes — PM announces dispatch** |
| phase_advanced | Yes | **Yes — PM announces phase change** |
| agent_run (generation complete) | Yes | **Yes — contributor reports completion** |
| agent_approved/rejected | Yes | No — user action, already in chat context |

### PM decision log (workspace file)

In addition to chat messages, PM writes a rolling decision log to `memory/pm_log.md`. This gives PM continuity across pulse/headless/chat contexts:

```markdown
## 2026-03-23 14:30 — dispatch
Dispatched slack-briefer. Platform data fresh (synced 2h ago). Daily recap due.

## 2026-03-23 14:00 — wait
No fresh content since last run. All contributors idle.

## 2026-03-23 12:00 — assess_quality
Briefer output thin (3 items). Steering: focus on #product and #engineering.
```

Every PM decision context (Tier 3, headless, chat) reads `pm_log.md` before deciding. Every context appends to it after deciding.

---

## Implementation

### New service: `api/services/pm_coordination.py`

Single helper that all PM decision surfaces call:

```python
async def pm_announce(client, user_id, project_slug, agent, message, decision_type):
    """Write PM decision to chat session + pm_log.md + activity event."""
    # 1. Write to project chat session
    session = await get_or_create_project_session(client, user_id, project_slug)
    await append_message(client, session["id"], "assistant", message, metadata={
        "author_agent_id": agent["id"],
        "author_agent_slug": get_agent_slug(agent),
        "author_role": "pm",
        "autonomous": True,  # distinguishes from user-prompted responses
    })
    # 2. Append to memory/pm_log.md
    # 3. Log activity event (audit trail)
```

Similarly for contributors:

```python
async def contributor_report(client, user_id, project_slug, agent, message):
    """Write contributor completion message to chat session."""
```

### Callers

- `agent_pulse.py` `_tier3_pm_coordination()` → calls `pm_announce()` after dispatch/advance/generate decisions
- `agent_execution.py` post-delivery → calls `contributor_report()` with run summary
- `agent_execution.py` `_handle_pm_decision()` → calls `pm_announce()` after assemble/steer/assess

### What gets deleted

- Activity events remain but are **no longer the user-facing surface** for PM coordination
- The "RECENT ACTIVITY" section in workfloor tab becomes the PM decision log (from `pm_log.md`), not raw activity events
- "PM pulsed — unknown" messages disappear from user view — replaced by meaningful PM announcements

---

## Trade-offs

### Accepted

1. **Chat session grows faster** — autonomous messages add to session size. Accepted because 24h rotation + compaction handles this. Autonomous messages are typically 1-2 sentences.
2. **PM messages may feel noisy** — if PM pulses frequently with "no action needed." Mitigated: only significant decisions (dispatch, advance, assemble, issue detected) get chat messages. Routine "wait" decisions go to pm_log.md only.

### Rejected

1. **Separate "system messages" channel** — would fragment the conversation. The whole point is one unified timeline.
2. **Activity events as user-facing** — tried this (ADR-126). Results in "PM pulsed — unknown" UX. Activity events are for systems, not users.
