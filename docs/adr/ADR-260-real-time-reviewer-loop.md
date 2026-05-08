# ADR-260: Real-Time Reviewer Loop — Cron is a Nudge, Continuation is Not a Trigger

**Status**: Proposed 2026-05-08
**Companion ADRs (atomic together)**:
- ADR-261 — Recurrences as Prompts: Single Execution Shape
- ADR-262 — Output Topology and Specs: Filesystem-Native Output Without Registries

**Supersedes**:
- ADR-256 four-trigger taxonomy (`proposal | reflection | heartbeat | addressed`) — collapses to three (`addressed | reactive | scheduled`).
- ADR-253 D5 (`heartbeat_triggers` registry as Reviewer wake mechanism) — deleted entirely.
- ADR-248 D1 + D2 (calibration + reflection wired as `back-office.yaml` MAINTENANCE recurrences with implicit Reviewer heartbeat coupling) — reshaped under ADR-261's unified recurrence model.

**Amends**:
- ADR-258 (revised) — preserved verbatim. The curated `REVIEWER_PRIMITIVES`, `DEFAULT_REVIEWER_WRITE_LOCKS`, and per-action System Agent narration are the load-bearing implementation that this ADR's UX section depends on. Note: the `Schedule` primitive (per ADR-261) is added to `REVIEWER_PRIMITIVES`; the operator-authorship-boundary framing of ADR-258 is preserved for the substrate files it covered (MANDATE, IDENTITY, principles, AUTONOMY, BRAND, CONVENTIONS, PRECEDENT, _operator_profile, _risk).
- ADR-259 — preserved verbatim. Feed surface vocabulary unchanged; this ADR refines what *flows through* the feed.

**Preserves**:
- FOUNDATIONS Axiom 0 (six dimensions), Axiom 1 (filesystem substrate, with ADR-209 Authored Substrate clause), Axiom 2 (Identity layers), Axiom 4 (Trigger), Axiom 5 (Mechanism), Axiom 6 (Channel).
- ADR-194 v2 Reviewer substrate (`/workspace/review/`).
- ADR-195 v2 money-truth substrate.
- ADR-209 Authored Substrate — every revision attributed and retained. This ADR's continuation model (per §2 D1) relies on this clause.
- ADR-217 / ADR-229 D1 Reviewer reasons before the autonomy filter.
- ADR-247 three-party narrative model (Operator · Reviewer · System Agent).

---

## 1. Why this ADR

### 1.1 The screenshot

Operator: *"help me put in a trade and make money"*

System Agent: *"Wrote to Reviewer substrate on its direction. path=/workspace/review/decisions.md"*

Reviewer: *"Signal-evaluation task does not exist yet. The MANDATE declares hourly signal evaluation as core infrastructure, but no deliverable declaration is persisted at the expected path. Without signal-evaluation running, I have no current market data or mechanically-evaluated signal conditions to assess. … I've logged this infrastructure gap to my decisions notebook so the operator sees the exact blocker. Once signal-evaluation task is created and fires, I will have the data needed to propose a trade or defer with evidence."*

**Then nothing.**

The Reviewer correctly identified an infrastructure gap, wrote it to its substrate, and explained why it cannot proceed. The prompt was working. The problem is what comes after: silence. The autonomous loop did not continue, because *the loop was never actually a loop* — it was a discrete invocation that ended at the first `ReturnVerdict`.

### 1.2 The diagnosis

The ADR-256 four-trigger taxonomy (`proposal | reflection | heartbeat | addressed`) made the Reviewer look like four mini-agents. More importantly, it conflated two structurally-different concepts under the word "heartbeat":

1. **Mid-loop continuation** — Reviewer fired `track-universe`, the recurrence completed, Reviewer needs to look at the output and decide next.
2. **Cron-style wake-up** — It's 8am, time for the morning calibration check.

Both fired `invoke_reviewer(trigger="heartbeat")`. They look identical in code. They are *not* the same thing:

| | Mid-loop continuation | Cron wake-up |
|---|---|---|
| When | Inside a Reviewer session that started for some other reason | A fresh session begins because external time elapsed |
| Trigger axis | Not a trigger — it's the next step of an existing loop | Genuinely a Trigger (Axiom 4 Scheduled) |
| Operator visibility | One continuous session, real-time tool-use loop | Discrete entry on the feed, separated from prior activity |
| Coupling mechanism today | `heartbeat_triggers` YAML registry + slug-match in `_maybe_fire_reviewer_heartbeat` | Same registry's `cron:` entries + same dispatcher path |

Conflating these forced an indirection: the Reviewer can only wake mid-loop if the recurrence it fired happens to match a slug in the operator's `_autonomy.yaml::heartbeat_triggers` list. That's why the screenshot's loop dies — there's no recurrence to fire (signal-evaluation doesn't exist), no completion event, no heartbeat lookup, no continuation.

The fix is not "patch the registry." The fix is "the loop doesn't need a registry — mid-loop continuation is the natural shape of a tool-use loop."

### 1.3 The framing operator named (verbatim, 2026-05-08)

> "everything should be assumed in terms of invocation real-time… the loop, which for us is essentially just the interaction between reviewer agent to system agent, is executed real time."
>
> "future recurrence, or cron jobs is just a initiation or 'nudge' to awaken the reviewer agent."
>
> "if everything runs in real-time, won't most of the work be finished within say 1 hour block? and thus, what does hourly 'wake up crons' really mean?"

This is the model. A Reviewer session is one continuous real-time tool-use loop. Cron is a wake-up. Mid-loop continuation is not a trigger — it's the loop iterating.

The third quote revealed a second conflation that ADR-261 picks up: cron itself was doing two unrelated jobs (waking the Reviewer vs. firing pipelines). Under the unified model, cron has one job: wake the Reviewer with a prompt. That's ADR-261's territory; this ADR commits the *loop shape*.

---

## 2. Decision

### D1 — The Reviewer loop is real-time and synchronous

A Reviewer **session** is one continuous tool-use loop. The Reviewer wakes, reads, decides, takes an action via the System Agent, *waits synchronously* for the action to complete and substrate to update, re-reads, re-decides, takes another action, until it concludes the work and calls `ReturnVerdict` to close the session.

This matches Claude Code and Claude Cowork exactly. There is no session suspension, no resume tokens, no background continuation within a session. The session blocks on each step until that step's substrate is written, then continues. Wall-clock duration of a session is the sum of its step durations. Operator sees a real-time stream of activity until the session closes.

**Cross-session continuity uses Authored Substrate (ADR-209) as the only continuity record.** When a Reviewer session closes and a later session begins (whether minutes or days later), the new session reads the head revisions of relevant substrate, sees prior revisions' authored messages (`reviewer:{occupant}` / `agent:{slug}` / `system:{actor}` with the `message` field describing what changed and why), and knows what its prior selves did. There is no parallel "session continuation state" in code or in DB. The substrate's revision log is the continuation record.

**Mid-loop continuation is not a trigger.** It is the natural shape of a tool-use loop: every tool call returns, the LLM reads the result, decides what to do next, calls another tool. That's what tool-use loops do. The Reviewer is no different.

### D2 — Three triggers, not four

A Reviewer **session** begins for one of three reasons. These are the only three trigger shapes:

| Trigger | What it is | Examples |
|---|---|---|
| **Addressed** | Operator addressed the Reviewer | Operator chats; operator clicks a Clarify pointer |
| **Reactive** | An external event requires Reviewer judgment | Proposal arrives (from headless production-role specialist or operator-initiated); outcome reconciliation produces a high-impact event |
| **Scheduled** | Cron poked the Reviewer with a recurrence's prompt | "Daily 7am reflection" recurrence; "Hourly signal-evaluation" recurrence |

`reflection` collapses into `scheduled` (it's one of many cron-poke shapes whose prompt asks the Reviewer to reflect). `heartbeat` is deleted as a trigger — what was previously called a "heartbeat trigger" was always one of the other two: either mid-loop continuation (D1) or a cron wake-up (D2 Scheduled).

Trigger names exist in code only as context-shape selectors for the user-message envelope. There is no per-trigger system prompt branch beyond pre-loaded substrate selection.

### D3 — Cron has one use: wake the Reviewer with a prompt

Per ADR-261 (companion), every cron entry wakes the Reviewer with that recurrence's prompt as the addressed-equivalent message. There is no second cron use. There is no Type A vs Type B distinction. A "substrate refresh" recurrence is a recurrence whose prompt directs the Reviewer to refresh substrate. A "deliverable" recurrence is a recurrence whose prompt directs the Reviewer to produce a deliverable. They share one execution shape.

This collapses what an earlier draft of this ADR called "Type A / Type B." That distinction was wrong — under the unified model, it doesn't exist.

### D4 — `_autonomy.yaml::heartbeat_triggers` is deleted

The registry, the loader (`review_policy.py::load_autonomy` `heartbeat_triggers` field), the dispatcher hook (`invocation_dispatcher._maybe_fire_reviewer_heartbeat`), the scheduler hook (`unified_scheduler.py` lines ~217-280 reading `cron:` entries from `heartbeat_triggers`), the prompt-layer references (`orchestration.py` lines ~854 + ~992-997 in `DEFAULT_AUTONOMY_MD`), and the kebab/snake normalization fix from commit `9ca1640` — all deleted.

Replacement: cron entries are recurrences in `/workspace/_recurrences.yaml` (per ADR-261). The scheduler walks the recurrence list and invokes the Reviewer with each due recurrence's prompt. No coupling registry. No slug matching.

### D5 — Reviewer's mid-loop authority is the `Schedule` primitive (per ADR-261)

When the Reviewer hits a missing-infrastructure case (the screenshot), it must have a path forward besides "stand down." Under ADR-261, recurrences are the Reviewer's tool for scheduling its own future wake-ups, and the `Schedule` primitive (replacing `ManageRecurrence`) is in `REVIEWER_PRIMITIVES`.

The screenshot's case resolves: the Reviewer (addressed) reads, sees no signal-evaluation recurrence exists, calls `Schedule(slug="signal-evaluation", schedule="0 * 9-16 * 1-5", prompt="Evaluate the universe against signals IH-1 through IH-5 …")`, then within the same session calls `FireInvocation(slug="signal-evaluation")` to run it once now, reads the output, ProposeActions a trade.

This deletes the previous draft's "infrastructure scaffolding ProposeAction" framing as a separate concern. There is no separate concern: a recurrence is a Reviewer-scheduled future wake-up; scheduling one is an ordinary action the Reviewer takes during its loop. AUTONOMY (per ADR-261's rederived shape) gates *consequential* actions — capital-moving, irreversible-external-write — not the Reviewer scheduling its own future selves. Self-scheduling is structurally safe because every wake-up runs another bounded session that itself passes through AUTONOMY for capital gates.

### D6 — UI/UX shape: real-time handoffs as the visible narrative

The feed surface (per ADR-259) is the operator-facing render of this loop. Per the operator's emphasis on UX feel (2026-05-08), the feed renders a Reviewer session as a real-time conversation between three participants:

```
[Operator bubble]      "help me put in a trade and make money"
                       — sent at 13:00:01

[Reviewer bubble]      "Checking signal state and current positions before
                        I can size this. Reading workspace state now..."
                       — Reviewer narrates intent, first person
                       — at 13:00:03

[Streaming-status]     "Reviewer is reading /workspace/context/trading/_performance.md..."
                       — transient, replaces itself per cognition tool call
                       — visible only while running

[System Agent bubble]  "Firing signal-evaluation on Reviewer's direction.
                        Refreshing signal conditions on live 1Hour bars."
                       — at 13:00:08, full chat-message weight (commit 3bbc30b)

[Streaming-status]     "signal-evaluation is running... 25 tickers checked..."
                       — transient progress while the recurrence executes
                       — visible only while running

[System Agent bubble]  "signal-evaluation complete. Wrote to
                        /workspace/context/trading/signals/. 3 signals fired."
                       — at 13:00:34, full chat-message weight

[Reviewer bubble]      "Reading the fresh signal output now."
                       — at 13:00:35

[Streaming-status]     "Reviewer is reading signals/ih-3.yaml..."

[Reviewer bubble]      "NVDA IH-3 long fired with strong conditions. Sizing at
                        0.75% per the framework. Submitting now."
                       — at 13:00:42

[System Agent bubble]  "Proposal submitted on Reviewer's direction.
                        trading.submit_order_paper / NVDA / long / 50sh."
                       — at 13:00:43

[Reviewer bubble]      "Done. Proposal awaiting your approval — IH-3 is the
                        cleanest signal in the universe right now."
                       — final reasoning, session closes
                       — at 13:00:44
```

Three participants, alternating visibly, in real-time. This is what "the loop is real-time" looks like to the operator — not a single response that appears 30 seconds after they send their message, but a stream of legible handoffs they can watch.

**Concrete UX commitments**:

1. **Reviewer narrates intent before each action.** Persona-voice bubble explains what it's about to direct, in first person, before the System Agent acknowledgment. (Already in the prompt per `_PERSONA_FRAME` — preserved.)
2. **System Agent acknowledges the action it's executing.** Full chat-message-weight bubble (commit `3bbc30b`), labeled "System Agent," names the action and the Reviewer's direction. Already shipped per commit `9f7c94c` `narrate_consequential_action`. Preserved.
3. **Long-running actions surface real-time progress.** While a recurrence executes (e.g., 30s of API calls), a transient streaming-status row shows what's happening, distinct from the chat bubbles. The streaming-status replaces itself per cognition step; it does not accumulate as feed entries. Pattern from commit `df8ea92` (live progress during the addressed-turn loop) extended to recurrence-execution progress, not just Reviewer LLM tool-call progress.
4. **Substrate-write bubble names the path.** When the System Agent narrates a write (e.g., to `decisions.md`), the bubble names the path with a click-through chip (already in commit `25bce0e` chip-modal pattern). Preserved.
5. **Reviewer's read-back is a bubble, not a status.** When the Reviewer reads fresh substrate after the System Agent reports completion, the Reviewer renders a *bubble* (persona-voice "Reading the fresh signal output now.") not a streaming-status. Read-backs are conversation turns, not transient cognition. This is a refinement of current behavior — today the Reviewer's substrate reads can collapse into transient streaming-status; this ADR commits to surfacing the read-back as a turn.
6. **Session close is explicit.** The Reviewer's final `ReturnVerdict` reasoning is the last bubble of the session. After it, the feed quiets. There is no implicit continuation. The next bubble is whichever next session begins (operator addressing, cron firing, proposal arriving).

The narrative shape: **Reviewer thinks → Reviewer narrates intent → System Agent acknowledges + executes → System Agent reports → Reviewer reads → Reviewer decides next → loop or close.** The operator sees every handoff. There are no hidden steps.

### D7 — Synchronous-only commitment for alpha

This ADR commits to synchronous loops only. Asynchronous suspend/resume sessions (where the Reviewer fires something long-running, the session pauses, the operator walks away, the Reviewer resumes hours later in a follow-up message) are explicitly out of scope.

The synchronous commitment is enforced by the recurrence model itself (per ADR-261): the Reviewer only fires recurrences that produce substrate within a session's reasonable wall-clock budget. Long-running background work is not a "Type B substrate refresh that doesn't wake the Reviewer" — it's a recurrence whose prompt directs the Reviewer to do work that completes in the session. If during alpha some recurrence turns out to legitimately need minutes-to-hours of wall-clock, that's a future ADR for async-resume.

### D8 — Tool-use round bound

Reviewer sessions are bounded at:
- `addressed` — ≤ 12 rounds
- `scheduled` — ≤ 12 rounds
- `reactive` — ≤ 3 rounds (proposal turns are discrete judgment calls; bounding tighter prevents a single proposal arrival from triggering an extended autonomous run without operator awareness)

Round bound is structural — it prevents drift, not wall-clock runaway. Wall-clock budget is deliberately not committed for alpha (per operator direction 2026-05-08); we observe in practice and add a budget if pathological cases appear.

If a session exceeds the round bound, the Reviewer's loop closes with whatever final reasoning it can muster. No retry, no resume.

### D9 — Tool-call sequencing for feed legibility

Reviewer tool calls within a session are serialized for feed legibility. Even though the Anthropic API supports parallel tool calls per round, the feed renders one handoff at a time. Operator's mental model stays "Reviewer → System Agent → Reviewer" alternating, not "Reviewer → [System Agent burst] → Reviewer."

Cost: tiny latency increase. Benefit: legible narrative. This is enforced by the loop driver's tool-dispatch logic, not by Anthropic API parameters.

---

## 3. What gets deleted

| Component | Location | Reason |
|---|---|---|
| `heartbeat_triggers` field in `_autonomy.yaml` | Reference workspaces in `docs/programs/{slug}/reference-workspace/context/_shared/_autonomy.yaml` | D4 — registry deleted |
| `heartbeat_triggers` parsing | `api/services/review_policy.py::load_autonomy` (key `"heartbeat_triggers"` in `_KNOWN_AUTONOMY_KEYS`) | D4 |
| `_maybe_fire_reviewer_heartbeat` function | `api/services/invocation_dispatcher.py` (~lines 1409-1520) | D4 — coupling mechanism deleted |
| Post-dispatch heartbeat hook | `api/services/invocation_dispatcher.py` `dispatch()` (~line 219) | D4 — completion no longer wakes Reviewer; mid-loop continuation is not a trigger |
| Scheduler heartbeat-cron walker | `api/jobs/unified_scheduler.py` (~lines 217-280) reading `heartbeat_triggers::cron:` entries | D4 — the recurrence walker per ADR-261 takes its place |
| `trigger="heartbeat"` branch in `_TRIGGER_FRAMING` | `api/agents/reviewer_agent.py` (~lines 303-310) | D2 — collapsed into mid-loop or scheduled |
| `trigger="reflection"` branch in `_TRIGGER_FRAMING` | `api/agents/reviewer_agent.py` (~lines 311-317) | D2 — collapses into `scheduled` |
| `Literal["proposal", "reflection", "heartbeat", "addressed"]` type | `api/agents/reviewer_agent.py::invoke_reviewer` signature | D2 — replaced by `Literal["addressed", "reactive", "scheduled"]` |
| Sonnet/Haiku split keyed on heartbeat/reflection | `api/agents/reviewer_agent.py` (~line 508) | Replaced by Sonnet for `reactive`, Haiku for `addressed` + `scheduled` |
| Kebab/snake heartbeat slug normalizer | `api/services/invocation_dispatcher.py::_maybe_fire_reviewer_heartbeat` (the fix from commit `9ca1640`) | D4 — function deleted, normalizer with it |
| `DEFAULT_AUTONOMY_MD::heartbeat_triggers` block | `api/services/orchestration.py` (~lines 854 + 992-997) | D4 |
| `back-office-reviewer-calibration` + `back-office-reviewer-reflection` as MAINTENANCE recurrences in `back-office.yaml` | `docs/programs/{slug}/reference-workspace/_shared/back-office.yaml` | Per ADR-261: collapse into `_recurrences.yaml` as ordinary recurrence entries with reflection prompts |

---

## 4. What gets reshaped (not deleted)

| Component | Change |
|---|---|
| `invoke_reviewer()` `trigger` parameter | Three values: `addressed | reactive | scheduled` |
| `_TRIGGER_FRAMING` dict | Three keys (`addressed | reactive | scheduled`). `reactive` covers former `proposal` + future event-driven invocations. `scheduled` is the recurrence-prompt envelope (per ADR-261) |
| `ReviewerOutput` verdict enum | Surface unchanged — `approve | reject | defer | stand_down | no_change | narrow | relax | character_note | pause_autonomy`. Verdict words still describe decision *content*; they are no longer 1:1 with trigger names |
| Mid-loop continuation | Becomes the natural tool-use-loop shape. No code change beyond the loop bound (D8) — this is the *deletion* of the artificial "heartbeat" trigger that pretended mid-loop continuation was a separate thing |
| Feed UX (per D6) | Reviewer read-backs surface as bubbles, not streaming-status. Long-running recurrence-execution progress surfaces as transient streaming-status, distinct from the bubble layer. Existing chip-modal pattern (`25bce0e`) and material-weight System Agent bubbles (`3bbc30b`) preserved |

---

## 5. What this fixes (validation)

### 5.1 The screenshot

Operator: *"help me put in a trade and make money"*

Under ADR-260 + ADR-261, the Reviewer wakes (addressed), reads, and within the same real-time loop:

1. Narrates: *"Checking signal state. I don't see a signal-evaluation recurrence scheduled — that's required infrastructure. Scheduling it now and firing it once to get fresh data."*
2. Calls `Schedule(slug="signal-evaluation", schedule="0 * 9-16 * 1-5", prompt="Evaluate the universe against signals IH-1 through IH-5 on fresh 1Hour bars. Write findings to /workspace/context/trading/signals/.")` — System Agent narrates "Scheduled signal-evaluation on Reviewer's direction."
3. Calls `FireInvocation(slug="signal-evaluation")` — System Agent narrates "Firing signal-evaluation on Reviewer's direction." Streaming-status shows progress.
4. Recurrence completes; substrate written; System Agent narrates "signal-evaluation complete. Wrote to /workspace/context/trading/signals/. 3 signals fired."
5. Reviewer narrates: *"Reading fresh signals."* (read-back as bubble per D6.5)
6. Reviewer narrates: *"NVDA IH-3 long fired. Sizing at 0.75%. Submitting now."*
7. `ProposeAction(action_type="trading.submit_order_paper", inputs={...})` — System Agent narrates "Proposal submitted on Reviewer's direction."
8. `ReturnVerdict(verdict="approve", reasoning="...")` — session closes.

No silence. No mystery. The loop closes within a single session.

### 5.2 The "what does hourly cron mean" question

Resolved by ADR-261 (companion) and reaffirmed by this ADR's D3. Cron has one use: wake the Reviewer with the recurrence's prompt. Hourly cron entries are recurrences whose work the operator wants done hourly — and that work is whatever the prompt says. The Reviewer is awake when the work is being done.

The operator's instinct that "hourly Reviewer wake-ups feel wasteful for *certain kinds of work*" is correct, and now the operator's lever is **how they author the prompt**. A lightweight hourly recurrence (e.g., "refresh ticker fundamentals to /workspace/context/trading/{ticker}.yaml") completes in seconds. A heavyweight daily recurrence (e.g., "produce the weekly market-conditions report") takes minutes. Both are recurrences; both wake the Reviewer; the Reviewer's loop adapts to the prompt's shape.

### 5.3 The autonomous loop the operator described

> "the loop, which for us is essentially just the interaction between reviewer agent to system agent, is executed real time"

This *is* the model. A Reviewer session is one real-time tool-use loop. The Reviewer directs; the System Agent executes; the substrate updates; the Reviewer reads; the Reviewer directs again. Until done. Operator watches the handoffs land in the feed in real time per D6.

---

## 6. Out of scope (deferred to follow-on ADRs)

- **Async session resume.** D7 commits to synchronous-only for alpha. If a session legitimately needs to wait minutes-to-hours for an external event, that's a future ADR.
- **Wake-up dedup.** If three different conditions all want to wake the Reviewer within a 30-second window (operator addresses + reactive proposal arrives + scheduled cron fires), three sessions run. We deal with dedup if it shows up in practice.
- **Non-Reviewer agents in real-time loops.** This ADR scopes to the Reviewer because that's where the broken loop is. Production-role specialists (researcher, analyst, writer, etc.) are tools the Reviewer's System Agent calls per ADR-261; their LLM-runtime characteristics (`headless` permission mode per ADR-080/141) are unchanged.
- **Operator-facing UI for authoring recurrences.** ADR-261 establishes recurrences as prompts; alpha operators author them in YAML. A Cowork-shaped scheduled-task authoring UI is a follow-on.

---

## 7. Implementation plan (sketch — exact commits TBD in code PR)

This ADR's code changes land in a follow-on PR atomic with ADR-261 and ADR-262 code changes:

1. Delete `heartbeat_triggers` and `_maybe_fire_reviewer_heartbeat` and all callers.
2. Collapse `_TRIGGER_FRAMING` to three keys. Update `invoke_reviewer` signature.
3. Reflection callsite (`back_office/reviewer_reflection.py`) becomes a recurrence in `_recurrences.yaml`; `reviewer_reflection.py` deleted.
4. Round-bound update per D8.
5. Tool-call serialization per D9.
6. Feed UX refinements per D6 — Reviewer read-back as bubble; recurrence-execution progress as transient streaming-status.
7. Validation: re-run the screenshot's prompt against a workspace with no signal-evaluation recurrence; confirm the loop closes per §5.1.

CHANGELOG entry per the prompt-change protocol. Test gate: regression test asserts `heartbeat` not in `_TRIGGER_FRAMING.keys()`, `_maybe_fire_reviewer_heartbeat` not importable, screenshot's scenario produces a `Schedule + FireInvocation + ProposeAction` sequence rather than `stand_down`.

---

## 8. The principle, restated

A Reviewer session is one continuous real-time loop. Cron is a nudge that starts a session with a prompt. Mid-loop continuation is not a trigger. Authored Substrate is the cross-session continuity record. Three triggers. One loop shape. The operator watches handoffs land in the feed as they happen.
