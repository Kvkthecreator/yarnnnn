# Feedback Loop Design

**Date:** 2026-04-15  
**Status:** Proposed  
**Extends:** [FEEDBACK-WORKFLOW-REDESIGN.md](./FEEDBACK-WORKFLOW-REDESIGN.md) — three-layer routing model  
**Depends on:** ADR-156 (Single Intelligence Layer), ADR-167 (List/Detail Surfaces), ADR-166 (Registry Coherence), ADR-178 (Task Creation Routes)

---

## Thesis

The existing three-layer feedback model (domain / agent / task) routes feedback correctly once the user gives it. The gap is earlier: users rarely think to give feedback spontaneously, and when they do, the surface provides no affordance to direct it.

This doc designs:
1. **Surface affordances** — where feedback buttons live, what they say, per `output_kind`
2. **Action taxonomy** — prompt-relay vs. direct-trigger mechanics
3. **The execute → feedback → iterate loop** — a structured, repeatable cycle
4. **When TP solicits feedback** — making the loop active rather than passive

The loop does not add new primitives. Everything routes through TP chat via pre-filled prompt relays. The loop is behavioral, not architectural.

---

## Current State

Three entry points exist today:
1. Email "Reply with feedback" → task-scoped TP
2. `/work?task=…` → typed feedback in chat
3. `/chat` → agent-level feedback only (no task context)

What's missing: **no affordance on the task detail page itself**. Users land on `/work?task=slug`, see the output, and have no prompted pathway to give feedback. The chat panel is present but passive — no pre-fill, no prompts, no structure.

---

## Design Principle: Prompt Relay Over Direct Trigger

All feedback actions are **prompt relays** — they pre-fill a message in the task-scoped chat input and surface it to the user. The user reviews and presses send. TP executes.

This is the correct architecture because:
- TP is the single intelligence layer (ADR-156). No background feedback jobs.
- Pre-filled prompts are reviewable, editable, and reversible before send.
- TP can ask clarifying questions, route to the right layer, and confirm actions.
- Direct triggers (bypass chat) would create a second write path and fragment history.

**Exception**: Run Now is a direct trigger (fires `ManageTask(action="trigger")`) — it is an operational action, not feedback. It belongs with Run/Pause/Edit in the task actions strip, not the feedback affordances.

---

## Feedback Affordance Placement

### Location: Task detail footer — below KindMiddle

A thin feedback strip sits below the KindMiddle component in `WorkDetail`, above the assigned agent footer. It is always visible when the task has at least one run (`last_run_at` is set).

It does not live in the left panel (there is no left panel on `/work` — ADR-167 list/detail, no persistent sidebar). It lives inline in the detail view, after the output.

```
WorkDetail
├── PageHeader (title + subtitle + actions)
├── ObjectiveBlock
├── KindMiddle (DeliverableMiddle / TrackingMiddle / ActionMiddle / MaintenanceMiddle)
├── FeedbackStrip ← NEW (only shown when last_run_at is set)
└── AssignedAgentFooter
```

### FeedbackStrip structure

```
┌─────────────────────────────────────────────────────────────┐
│  [primary action]           [secondary action]   [Edit in TP]│
└─────────────────────────────────────────────────────────────┘
```

Three affordances, all prompt relays:
- **Primary action** — output_kind-specific (see below)
- **Secondary action** — output_kind-specific (see below)
- **Edit in TP** — universal, always present: opens chat pre-filled with editing intent

---

## Per-output_kind Affordances

### `produces_deliverable`

User question: *"Is this output right?"*

| Button | Pre-filled prompt | TP routes to |
|--------|------------------|--------------|
| **This looks good** | `"This output looks good. Note it for future runs."` | `UpdateContext(target="task", feedback_type="positive")` → appends to feedback.md |
| **Something's off** | `"I want to change something about this output: "` (cursor at end) | TP asks what, then routes: task feedback.md or agent feedback.md |
| **Edit in TP** | `"Edit the latest [task title] output: "` | TP calls `ManageTask(action="steer")` |

**When to show**: Always when `last_run_at` is set and output exists.

---

### `accumulates_context`

User question: *"Is this tracking the right things?"*

| Button | Pre-filled prompt | TP routes to |
|--------|------------------|--------------|
| **Looks comprehensive** | `"The [task title] context looks comprehensive. Keep it up."` | `UpdateContext(target="task", feedback_type="positive")` |
| **Missing something** | `"The [task title] context is missing: "` (cursor at end) | TP routes: new entity (ManageDomains), focus shift (TASK.md objective update), or criteria (task feedback.md) |
| **Edit in TP** | `"Adjust what [task title] tracks: "` | TP calls `ManageTask(action="update")` or `ManageDomains` |

**When to show**: Always when `last_run_at` is set.

---

### `external_action`

User question: *"Did this send the right thing?"*

| Button | Pre-filled prompt | TP routes to |
|--------|------------------|--------------|
| **Delivery was right** | `"The [task title] delivery looked right."` | `UpdateContext(target="task", feedback_type="positive")` |
| **Adjust what's sent** | `"Change what [task title] sends: "` | TP calls `ManageTask(action="update")` on TASK.md delivery/objective |
| **Edit in TP** | `"Edit [task title] settings: "` | TP calls `ManageTask(action="update")` |

**When to show**: Always when `last_run_at` is set.

---

### `system_maintenance`

No user-facing feedback affordance. TP owns these tasks. Users can ask TP questions about them via chat but there is no structured feedback relay. `FeedbackStrip` renders `null` for `system_maintenance`.

---

## The Execute → Feedback → Iterate Loop

The loop is three phases. TP owns phase transitions — no cron, no background job.

```
EXECUTE → [output exists] → FEEDBACK WINDOW → [feedback given or skipped] → ITERATE
    ↑                                                                            │
    └────────────────────────────── next run ───────────────────────────────────┘
```

### Phase 1: Execute

Task runs on schedule or manual trigger. Output lands in `/tasks/{slug}/outputs/latest/`. `last_run_at` updated. `FeedbackStrip` becomes visible.

### Phase 2: Feedback Window

The feedback window is the period between a run completing and the next run starting.

**Passive path** — user visits `/work?task=slug`, sees the output, uses `FeedbackStrip` affordances. No TP involvement until the user sends.

**Active path** — TP solicits feedback. After evaluating a task (`ManageTask(action="evaluate")`), TP can ask the user a targeted question in chat. TP should solicit feedback when:
- The task has ≥ 3 runs but zero feedback entries in `memory/feedback.md` (first feedback request)
- `memory/feedback.md` has not been updated in ≥ 14 days and the task is still active
- Evaluation detects a quality divergence from DELIVERABLE.md criteria (TP asks proactively)
- The task's mode is `goal` and the run is near the declared milestone (TP asks: "does this meet your goal?")

TP asks **one question only** per evaluate call. Not a form. Example:
> "I ran the Weekly Brief. The output covers the competitive section but the market section is thin — does that match what you wanted, or should I weight it differently?"

This is better than a generic "how was the output?" prompt because it demonstrates TP has read the output and formed an opinion. The specificity makes it easy to respond.

### Phase 3: Iterate

TP receives feedback, routes to the correct layer (domain / agent / task), writes the relevant file, and optionally triggers a rerun:
- Criteria feedback → `memory/feedback.md` + optional trigger
- Objective change → TASK.md `**Objective:**` update
- Agent style → `/agents/{slug}/memory/feedback.md`
- Domain entity → `ManageDomains`

After writing, TP confirms: "Updated. I'll apply this on the next run — want me to run it now?"

If yes: `ManageTask(action="trigger")`. If no: loop completes, next scheduled run picks up the new state.

---

## Feedback Solicitation Rules (TP Prompt Guidance)

These govern when TP proactively asks for feedback during `ManageTask(action="evaluate")`.

```
After evaluating a task:
- If feedback.md has 0 entries AND task has ≥ 3 runs:
    Ask ONE specific question about the most recent output quality.
    Reference a concrete detail from the output. Do not ask generically.

- If feedback.md last_updated > 14 days AND task.mode == "recurring":
    Ask ONE check-in question. "Still tracking what you need?"

- If quality score diverges from DELIVERABLE.md criteria:
    Flag the specific divergence. "The executive summary is 3x the spec length — intentional?"

- If task.mode == "goal" AND run approaches milestone:
    Ask if the output meets the milestone. Surface the milestone from DELIVERABLE.md.

- Otherwise: no feedback solicitation.

NEVER ask for feedback more than once per evaluate call.
NEVER use generic feedback prompts ("How was this output?").
ALWAYS reference a specific detail from the output or criteria.
```

---

## Daily Update Special Case

`daily-update` is essential (`essential: true`) and runs every morning. The feedback loop applies, but with different default posture:

- No `FeedbackStrip` primary action ("This looks good") — the daily update is ambient, not evaluated
- Only "Something's off" and "Edit in TP" affordances
- TP evaluation cadence: check-in once per week, not after every run
- Email reply-with-feedback still works (routes through task-scoped TP)

The daily update is the floor artifact, not a quality-evaluated deliverable. The feedback loop should be lighter.

---

## What This Does NOT Add

- **No inline edit forms** in the Work surface. All feedback goes through TP chat.
- **No feedback modal or overlay**. The strip is inline, not a pop-up.
- **No rating UI** (stars, thumbs). Structured ratings are low-signal; specific text feedback is high-signal.
- **No automatic feedback extraction from behavior**. ADR-156 killed background extraction jobs. Feedback is explicit.
- **No scheduled feedback requests to users** (email/notification prompts). TP asks in conversation when the user is present. External nudges are out of scope.
- **No new primitives**. Existing `ManageTask`, `UpdateContext`, `ManageDomains` handle everything.

---

## Implementation Plan

### Phase 1 — FeedbackStrip component (frontend only)

New file: `web/components/work/details/FeedbackStrip.tsx`

Props:
```ts
interface FeedbackStripProps {
  task: Task;           // for slug, title, output_kind
  hasOutput: boolean;   // only render if last_run_at + output exists
  onPromptRelay: (prompt: string) => void;  // pre-fills chat input
}
```

`onPromptRelay` calls the existing chat pre-fill mechanism in `WorkDetail` (the task-scoped chat panel already accepts pre-fill via the `?prefill=` param or a prop).

Mount point: `WorkDetail.tsx`, between `KindMiddle` and `AssignedAgentFooter`.

**Does not require any backend changes.** Prompt relays use existing chat infrastructure.

### Phase 2 — TP evaluate prompt guidance (backend prompt)

Add the feedback solicitation rules above to `api/agents/tp_prompts/onboarding.py` under a new `FEEDBACK_LOOP` section.

Update `api/prompts/CHANGELOG.md` with the entry.

### Phase 3 — evaluate auto-trigger wiring (already partially in place)

ADR-178 Phase C wired inference auto-trigger post-evaluate. The same evaluate call can carry feedback solicitation. No new trigger mechanism needed — it's a prompt instruction change.

---

## Relationship to FEEDBACK-WORKFLOW-REDESIGN.md

FEEDBACK-WORKFLOW-REDESIGN.md covers the **routing model** — how TP decides which layer to write to once feedback is received. This doc covers the **collection model** — how feedback enters the system in the first place.

The two docs are complements, not overlapping. FEEDBACK-WORKFLOW-REDESIGN.md does not need changes — the three-layer routing it describes is the execution path this doc feeds into.

---

## Open Questions

1. **Chat panel presence on `/work`**: Does the task detail view already render a chat input? If not, `onPromptRelay` needs to navigate to `/chat?task=slug&prefill=...` instead of injecting inline. Check `WorkDetail.tsx` current implementation.

2. **`last_run_at` availability**: `FeedbackStrip` requires `last_run_at` from the `Task` type. Verify it's in `TaskDetail` API response (`api/routes/tasks.py`) and in `web/types/index.ts`.

3. **Goal-mode milestone detection**: Phase 2 TP guidance references milestone proximity. DELIVERABLE.md milestone parsing is not yet implemented. Phase 2 guidance should degrade gracefully if milestone field is absent.
