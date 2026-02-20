# ADR-068: Signal-Emergent Deliverables

**Date**: 2026-02-19
**Status**: Implemented
**Updated**: 2026-02-20 — Extended to all platforms (Slack, Notion)
**Extends**: ADR-061 (Two-Path Architecture) — adds a new Phase B orchestrator phase
**Extends**: ADR-060 (Background Conversation Analyst) — widens the signal input beyond TP sessions
**Relates to**: ADR-063 (Four-Layer Model), ADR-045 (Execution Strategies), ADR-018 (Recurring Deliverables)

---

## Implementation Status (2026-02-20)

Signal detection now supports **all 4 connected platforms**:

| Platform | Signal Types | Implementation |
|---|---|---|
| **Google Calendar** | Upcoming events (next 48h) | ✅ Live Google Calendar API |
| **Gmail** | Silent threads (5+ days quiet) | ✅ Live Gmail API |
| **Slack** | Channel silence (7+ days), unanswered DMs | ✅ MCP Slack server |
| **Notion** | Stale pages (14+ days), overdue tasks | ✅ Live Notion API |

See `api/services/signal_extraction.py` for full implementation.

---

## Context

### The current model's assumption

Every deliverable in the current model is **user-configured first**. The user (or TP on explicit request) creates a deliverable with a type, sources, schedule, and destination. The orchestrator executes that configuration on schedule. The deliverable defines what gets produced.

This is a pull model: the user must recognize a recurring need, articulate it, and configure a deliverable to serve it. The system executes what it was told.

### What this misses

The user's world acts on them continuously — across Slack, Gmail, Notion, Calendar — whether or not they've configured a deliverable to process it. A meeting appears on their calendar with someone they haven't corresponded with in two weeks. A client thread goes quiet after three exchanges. A conflict emerges between their stated priorities and their actual platform activity this week.

None of that triggers anything in the current model. The system is blind to it unless the user was prescient enough to configure a deliverable that would catch it.

### The analogy

Human cognition doesn't wait for a deliberate configuration step. A person goes about their day, across every platform and context they inhabit, and pattern-matching happens continuously — not by narrating their world to an assistant, but by being exposed to it. YARNNN currently only observes what the user *tells TP*. It doesn't observe the world the user is operating in.

ADR-060 (Conversation Analyst) partially addressed this by mining TP session content. But that only captures what the user *said*, which is a narrow slice of their actual activity. The richer signal is the platform activity itself: what arrived, what changed, what's absent, what's imminent.

---

## Decision

### Three deliverable origins

All deliverables are classified by how they came to exist:

| Origin | Created by | Trigger | Prior user intent |
|---|---|---|---|
| `user_configured` | User (via UI or TP explicit request) | Schedule or manual | Explicit |
| `analyst_suggested` | Conversation Analyst (ADR-060) | Daily cron | Implicit — detected from TP sessions |
| `signal_emergent` | Signal Processing phase (this ADR) | Daily/hourly cron | None required |

`user_configured` is the current default. `analyst_suggested` exists in partial form via ADR-060. `signal_emergent` is new.

### Signal-emergent deliverables

**CLARIFICATION (2026-02-20):** The name "signal-emergent deliverables" creates conceptual confusion. **Signals are behavioral observations; deliverables are work artifacts.** The term "signal-emergent" refers to **provenance** (how it came to exist), not **nature** (what it is).

A signal-emergent deliverable is a normal `deliverables` row with:
- `origin=signal_emergent` — Immutable provenance tracking
- `trigger_type=manual` — Initially one-time (no recurring schedule)
- Can be promoted to recurring (same as any deliverable)

**The two-phase model:**

**Phase 1: Signal Processing (Orchestration)**
- Extract behavioral signals from live platform APIs (deterministic, no LLM)
- Reason with LLM: "What does this user's world warrant right now?"
- Produce action recommendations (ephemeral data structures):
  - `create_signal_emergent` — Create new deliverable for novel work
  - `trigger_existing` — Advance next_run_at of existing deliverable
  - `no_action` — Signal doesn't meet confidence threshold

**Phase 2: Action Execution (Selective Artifact Creation)**
- For `create_signal_emergent`: Create deliverable row + execute immediately
- For `trigger_existing`: Update existing deliverable's next_run_at (pure orchestration)
- Record in `signal_history` for deduplication

**Lifecycle states:**

**One-time (default)**: The signal warrants immediate action that won't recur on a fixed schedule. A meeting prep brief for tomorrow's call. A catch-up draft for a contact thread that's gone quiet. The deliverable runs once, produces a version, and does not re-run unless the user promotes it.

**Promoted to recurring**: The user finds the output valuable and elects to make it recurring. The origin field stays `signal_emergent` but `trigger_type` becomes `schedule`, and the deliverable thereafter behaves identically to a `user_configured` scheduled deliverable.

This lifecycle — **observe → reason → produce → user reviews → optionally promote** — is the full proactive onboarding loop. The user never had to configure anything to receive the first output. Configuration emerges from value, not from foresight.

### The signal processing phase

The Path B orchestrator (ADR-061) gains a third phase alongside the existing Analysis and Execution phases:

```
PATH B — Backend Orchestrator
  ┌──────────────────────────────────────────────────┐
  │ Phase 1 — SIGNAL PROCESSING  (daily or hourly)   │
  │                                                   │
  │  Input A: Layer 3 snapshot                        │
  │    What arrived / changed / is imminent           │
  │    across all user-connected platform scopes      │
  │    (channels, labels, pages, calendars)           │
  │                                                   │
  │  Input B: Layer 1 (Memory)                        │
  │    User's stated priorities, relationships,       │
  │    communication patterns, commitments            │
  │                                                   │
  │  Input C: Layer 2 (Activity)                      │
  │    What the system has done recently              │
  │    What deliverables have already run             │
  │    What has already been surfaced                 │
  │                                                   │
  │  Processing: Single LLM call (orchestrator agent) │
  │    "What does this user's world warrant right now │
  │     that isn't already being handled?"            │
  │                                                   │
  │  Output:                                          │
  │    → Trigger existing deliverable early           │
  │    → Create signal_emergent deliverable (one-time)│
  │    → Create analyst_suggested deliverable (paused)│
  │    → Nothing (no signal warrants action)          │
  │                                                   │
  └──────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────┐
  │ Phase 2 — ANALYSIS  (daily)                       │
  │  Mine TP sessions for recurring patterns          │
  │  → analyst_suggested deliverables (ADR-060)       │
  └──────────────────────────────────────────────────┘
  ┌──────────────────────────────────────────────────┐
  │ Phase 3 — EXECUTION  (per-schedule)               │
  │  Run due deliverables → deliverable_versions      │
  └──────────────────────────────────────────────────┘
```

Phase 1 is new. Phases 2 and 3 are existing (Phase 2 not yet implemented per ADR-060; Phase 3 is live).

### Signal extraction — what "Layer 3 snapshot" means

The signal processing phase does not dump raw platform content into an LLM call. It queries **live platform APIs** (Google Calendar, Gmail, Slack, Notion) to get the fresh, current state of the user's external world, then produces a **behavioral signal summary** — not content, but events and patterns:

```
Signal summary (example, not literal schema):
- Calendar: 3 events tomorrow. One with [contact] not emailed in 11 days.
- Gmail: 2 threads with external contacts went silent this week (no reply in 5+ days)
- Slack: User mentioned in #product-decisions 4 times today, no response to 2 of them
- Notion: Page "Q1 Roadmap" edited by [colleague] — user is tagged owner
- Gaps: No communication with [client] in 8 days (avg cadence: 3 days)
```

This summary is structured, compact, and cross-platform. It is the input the LLM reasons over. The raw messages, emails, and pages are not passed — just the behavioral signal extracted from them.

**Critically**: Signal extraction queries **live APIs**, NOT the `filesystem_items` cache. The whole point of hourly cron execution is to see the real-time state for time-sensitive signals like "meeting in 6 hours" or "thread went silent yesterday". The cache is stale (2-24h depending on sync frequency) and inappropriate for proactive signal detection.

This extraction is a deterministic pass (no LLM needed), producing structured data from live API responses: timestamps, senders/recipients, mentions, edit history, attendee lists.

### What the orchestration agent reasons over

Given the signal summary + user memory + recent activity, the agent answers one question:

> "What does this user's world warrant right now that isn't already being handled by their configured deliverables and recent system activity?"

Constraints it applies:
- **Deduplication**: Don't create a signal-emergent deliverable if a configured deliverable is already scheduled to handle the same signal within 24 hours
- **Recency**: Don't re-surface a signal that was already surfaced in the last N days
- **Confidence threshold**: Only act on signals above a minimum confidence score (same as ADR-060's 0.50 threshold)
- **Scope**: Only reason over platform sources the user has explicitly connected and scoped

### Schema addition

One new column on `deliverables`:

```sql
ALTER TABLE deliverables
  ADD COLUMN origin TEXT NOT NULL DEFAULT 'user_configured'
  CHECK (origin IN ('user_configured', 'analyst_suggested', 'signal_emergent'));
```

All existing rows default to `user_configured`. No migration of existing data required.

Signal-emergent deliverables created by the orchestrator have `origin = 'signal_emergent'`. When a user promotes one to recurring, the `origin` field is preserved — it records how the deliverable came to exist, not what it currently is.

### One-time deliverable lifecycle

Signal-emergent one-time deliverables use the existing schema fields:

```python
{
  "origin": "signal_emergent",
  "trigger_type": "manual",       # no recurring schedule
  "schedule": {},                 # empty — no next_run_at calculated
  "next_run_at": null,            # never scheduled to re-run
  "status": "active",             # active but one-time
  "governance": "manual",         # surfaces for user review before delivery
}
```

The orchestrator creates the deliverable row and immediately queues an execution. The execution produces a `deliverable_version` with `status: "staged"`. The user sees it in their deliverables view, reviews it, and either:

- **Approves** → delivers, deliverable status moves to `archived` after delivery (one-time, done)
- **Rejects** → deliverable archived, version discarded
- **Makes recurring** → `trigger_type` updated to `schedule`, `schedule` set, deliverable stays `active`

### Promotion to recurring

The `enable_suggested_version` endpoint (ADR-060) already handles the accept-and-activate path for `analyst_suggested` deliverables. Signal-emergent promotion to recurring is a separate action: it doesn't promote a version, it upgrades the deliverable's trigger model. A new endpoint or an update to the existing settings flow handles this:

```
POST /deliverables/{id}/promote-to-recurring
  body: { schedule: ScheduleConfig }
  → updates trigger_type, schedule, next_run_at
  → origin stays signal_emergent (provenance preserved)
```

---

## What this is NOT

**Not TP generating deliverable content.** The signal processing phase is Path B (orchestrator). TP does not participate in signal processing, deliverable creation, or content generation. ADR-061's path separation is preserved completely.

**Not a new agent type.** The orchestration agent reasoning over the signal summary is the same `DeliverableAgent` operating in a new context. No new agent class. Complexity is in the input preparation (signal extraction), not in the agent.

**Not replacing user-configured deliverables.** `user_configured` deliverables remain the primary model. Signal-emergent deliverables are additive — they fill gaps the user didn't configure for.

**Not real-time.** Signal processing runs on a cron schedule. The latency is bounded by the cron frequency and the platform sync freshness. Near-real-time processing via platform webhooks is a future extension; the `EventTriggerConfig` schema already supports it.

**Not pure orchestration.** While Phase 1 is orchestration (signal extraction → reasoning), Phase 2 creates persistent deliverable artifacts for novel work. The system uses `trigger_existing` for pure orchestration when an existing deliverable already handles the signal, but creates new `signal_emergent` deliverables when no suitable recurring deliverable exists. This hybrid model allows both smart scheduling (triggering existing work early) and proactive discovery (creating new work the user didn't configure).

---

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| ADR-018 (Recurring Deliverables) | Signal-emergent deliverables use the same `deliverables` table. Origin field distinguishes them. |
| ADR-060 (Conversation Analyst) | Phase 2 in the new orchestrator model. Signal Processing (Phase 1) is a separate, wider-signal input. Both produce suggested/emergent deliverables. |
| ADR-061 (Two-Path Architecture) | Signal Processing is a new phase in Path B. Path A (TP) is unchanged. |
| ADR-063 (Four-Layer Model) | Signal extraction reads Layer 3 (Context) behaviorally, not as content retrieval. Layer 2 (Activity) provides recency/deduplication context. |
| ADR-045 (Execution Strategies) | Signal-emergent deliverables use existing execution strategies. A one-time meeting prep brief uses the same `PlatformBoundStrategy` as a configured meeting_prep deliverable. |

---

## Open questions

1. **Signal extraction granularity** — How detailed should the behavioral signal summary be? Per-contact cadence tracking requires analyzing Gmail thread history via live API calls. Should signal extraction fetch full thread histories or just recent messages?

2. **Phase 1 frequency** — Daily is safe and predictable. Hourly catches more time-sensitive signals (meeting in 3 hours) but increases compute cost and requires freshness checks to avoid re-processing the same signals. Start daily; move to hourly for calendar/meeting signals specifically?

3. **Deduplication window** — If a signal-emergent deliverable was already created for a contact drift two days ago, how long before the same contact drift signal is eligible again? Per-signal-type deduplication windows probably make more sense than a global threshold.

4. **User control surface** — How does the user configure which signal types they want the system to act on? Some users want proactive meeting briefs; others find them noise. This is a notification preference extension — `user_notification_preferences` already exists (ADR-051); signal-emergent types can be added there.

5. **Cost model** — Signal processing adds an LLM call per active user per cron cycle. At scale, this is non-trivial. Per-tier rate limiting or a minimum-activity threshold (only run if user has had platform activity in the last N days) is probably necessary before launch.

---

## Implementation sequence

**Phase 1** — Schema and scaffolding
- Add `origin` column to `deliverables`
- Define the signal summary data structure
- Implement deterministic signal extraction via live platform API calls (Google Calendar, Gmail)

**Phase 2** — Orchestrator reasoning pass
- Implement signal processing function (single LLM call, structured output)
- Wire into `unified_scheduler.py` as Phase 1 (daily, before existing analysis)
- Output: create signal-emergent deliverable rows + queue execution

**Phase 3** — Lifecycle completion
- Implement `promote-to-recurring` endpoint
- Add signal-emergent origin handling in deliverables UI (differentiate from user-configured in the list view)
- Add user preferences for signal types (opt-in/opt-out per signal class)

**Phase 4** — Frequency tuning
- Move calendar/meeting signal processing to hourly for time-sensitive signals
- Implement per-signal deduplication windows
