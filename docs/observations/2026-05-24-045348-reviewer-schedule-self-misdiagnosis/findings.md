# findings.md — Reviewer schedule self-misdiagnosis

**Captured**: 2026-05-24T04:53Z. Hat-B observation.

## Expected behavior

When the Reviewer wakes (any source — cron_tick, substrate_event, addressed, etc.) and reasons about whether an expected fire has occurred, its reasoning is grounded in **the actual schedule + last-fire-time of each recurrence**, not the Reviewer's memory of what the cadence is supposed to be. If signal-evaluation fires once per RTH per `@market_open + 15min`, the Reviewer's standing-intent reasoning treats "one fire today" as expected, not as evidence of a missed-fire outage.

## Observed behavior

On 2026-05-22T21:01Z, during a heartbeat wake on alpha-trader main user (`2abf3f96…`), the Reviewer wrote to `/workspace/review/standing_intent.md`:

> *"signal-evaluation judgment recurrence failed to fire today during all scheduled RTH windows. Last execution attempt logged at 13:02 UTC expecting 13:45 UTC fire; no trace of execution since. Substrate stale (tickers 26h old). Flagging for operator investigation and standing down pending repair."*

This statement is materially false:

- `signal-evaluation` schedule in `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` is `"@market_open + 15min"` — **one fire per trading day**, not three.
- It fired correctly at 2026-05-22T13:46Z (`execution_events`: $0.249, `funnel_decision=escalate`, `status=success`).
- No second or third fire was scheduled for that day; the "all scheduled RTH windows" plural is a hallucination.
- The Reviewer conflated `signal-evaluation` (1×/RTH) with `track-universe`, which has three RTH snapshots (`["@market_open + 15min", "@market_open + 3h", "@market_close - 1h"]`).

The Reviewer then stood down, citing operator intervention required. No system fault existed. Subsequent operator perception of "23.5h dormancy" superimposed normal weekend market-closed quietness onto the false-alarm intent file, with the operator concluding "I'm not seeing autonomy" — when in fact the scheduler had fired ~1,420 successful empty ticks across the 23.7-hour window and the daily `outcome-reconciliation` recurrence had fired cleanly at 2026-05-23T05:00 UTC.

## Why this is the more important finding

A real scheduler outage would manifest as queued work piling up or wake_queue rows stuck in `locked` status. **The Reviewer's self-diagnostic claiming an outage that doesn't exist is harder to detect and more corrosive** because:

1. It produces "system broken" intent the operator reads and trusts.
2. It causes the Reviewer to stand down from work the system is actually doing fine.
3. The previous Hat-B session built an L6 closure narrative ("one alpha-trader fire away from full autonomy") on top of the Reviewer's substrate writes without independently verifying schedule semantics — propagating the hallucination into observation canon.
4. The operator's natural feedback ("I'm not seeing it") is correct intuition but tracks a phantom problem; without an independent audit, the team would have tried to "fix" a working system.

## Root cause

The Reviewer's wake envelope (`api/services/reviewer_envelope.py::load_reviewer_governance_envelope`) carries 9 universal entries (governance + pace + occupant + standing_intent) and a program-shaped envelope from bundle MANIFEST per ADR-281. It also carries an `operating_context_block` (`api/agents/reviewer_agent.py:284-364`) per ADR-274 that includes:

- Now (UTC ISO + local time)
- Operator timezone
- Market state (when bundle declares market context)
- Workspace tenure

**What is NOT in the envelope** (the gap):

- The literal `schedule:` strings from `_recurrences.yaml` entries the workspace owns
- `tasks.last_run_at` / `tasks.next_run_at` for each active recurrence (the scheduling index)
- Recent execution lineage — `execution_events` for the last N hours (what fired, when, with what outcome)

When the Reviewer reasons about "did signal-evaluation fire today as expected?", it must reach for ReadFile / GetSystemState mid-loop to perceive its own schedule — and in practice, it does not, falling back to memory of what the cadence supposedly is. The Reviewer wrote the standing_intent without consulting `_recurrences.yaml`, `tasks`, or `execution_events`.

ADR-285 (Holistic Wake Envelope, **Proposed** 2026-05-17) already anticipates this gap. Its D3 specifies adding `recent_execution_md` as a 10th universal envelope entry, written by a new mechanical primitive `MirrorRecentExecution`. **ADR-285 is not implemented**. The schedule self-misdiagnosis is the empirical case it predicted.

ADR-274's `Operating Context` block (implemented) gives the Reviewer "what time is it." ADR-285's `recent_execution_md` would give the Reviewer "what has happened recently." Neither gives the Reviewer "what is my own declared cadence and when did each of my recurrences last fire" — the substrate counterpart of the schedule index.

## Hat-A recommendation

**Implement ADR-285 D3 (Recent Execution Lineage)** with a refined scope informed by this finding: the substrate the Reviewer needs is not only "what fired" (recent_execution_md per ADR-285) but also **"what is supposed to fire and when"** — the schedule index projected as substrate.

Two paths, mutually reinforcing:

1. **Ship ADR-285 D3 as drafted** — `MirrorRecentExecution` writes `/workspace/memory/_recent_execution.md` with last N execution_events rows per recurrence + notable patterns. The envelope helper reads it. Cost: one new mechanical primitive, one envelope-decl line.

2. **Add a `_schedule_index.md` mirror** (new, derived from this finding) — a sibling mechanical primitive `MirrorScheduleIndex` writes `/workspace/memory/_schedule_index.md` containing each active recurrence's slug + literal `schedule:` string + `last_run_at` + `next_run_at` + paused flag, sourced from the `tasks` scheduling index. The envelope helper reads it. The Reviewer's `_PERSONA_FRAME` gets a "Schedule discipline" section instructing: *"Before claiming a recurrence missed an expected fire, read `_schedule_index.md` for its declared schedule and last fire. Do not reason about cadence from memory."*

Both files are mechanical-primitive-written, no LLM-time derivation, fully aligned with Derived Principle 19 ("kernel does not compute for the prompt"). Together they close the gap the operator's "I'm not seeing it" intuition surfaced.

Alternative scope-narrowed Hat-A: do ADR-285 D3 only, accept that the Reviewer will still need ReadFile / GetSystemState for schedule-specific reasoning. Cost-equivalent but leaves the schedule-hallucination class unaddressed.

Recommended scope: **both files** — they are kernel-universal, cheap, derive from data the system already has, and together they validate FOUNDATIONS Derived Principle 21's "wake-fired, paced by operator-declared pace" by giving the Reviewer the substrate to reason correctly about its own pace and fires.

## Surface area touched (Hat-A)

- New: `api/services/primitives/mirror_recent_execution.py` (per ADR-285 D4)
- New: `api/services/primitives/mirror_schedule_index.py` (new — companion to MirrorRecentExecution)
- New: kernel-universal mechanical recurrence triggering both mirrors at known cadence (per ADR-285: cron-tick frequency or piggyback on existing maintenance recurrence)
- `api/services/reviewer_envelope.py::_UNIVERSAL_ENVELOPE_DECLS`: +2 entries (`recent_execution_md`, `schedule_index_md`)
- `api/agents/reviewer_agent.py::_PERSONA_FRAME`: add "Schedule discipline" section
- ADRs: ratify ADR-285 (and amend if the new MirrorScheduleIndex companion is in scope) → mark Implemented
- `api/prompts/CHANGELOG.md` entry for persona-frame addition

## What this observation does NOT recommend

- No changes to `unified_scheduler.py`, `wake_queue.py`, `wake_drainer.py`. They are working correctly.
- No changes to `pace.py` or `_pace.yaml` substrate. The pace surface (ADR-298 + ADR-300) is sound; the bug is in Reviewer reasoning, not the pace dial.
- No new ADR for "time awareness" as a separate concern — ADR-274 already canonized time as a wake-envelope concern; the gap is that ADR-285's complement (recent + schedule lineage) is not yet shipped.

## Cross-finding implication

The operator's intuition that "wake and pace" coherence may need a stronger envelope is validated by this finding. A comprehensive audit of the ADRs covering this surface (274 / 275 / 276 / 281 / 284 / 285 / 296 v2 / 298 / 300) is queued as a follow-on Hat-B audit — see operator's request in the session transcript for "comprehensive discourse" on wake + pace + time-awareness coherence. That audit may surface additional gaps or confirm that ADR-285 closure is sufficient.

## Status

**Hat-B finding captured.** Hat-A fix queued — to be drafted as ADR-285 ratification (Phase 1 Implemented status) plus a small companion amendment for `MirrorScheduleIndex`. Three-commit shape: this observation (Hat-B) committed first; the fix (Hat-A) lands in separate commit referencing this folder; resolution addendum (Hat-B) appended after fix lands and the next post-deploy substrate-event wake validates the Reviewer correctly reads `_schedule_index.md` before claiming missed fires.
