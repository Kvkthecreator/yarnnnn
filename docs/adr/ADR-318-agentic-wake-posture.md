# ADR-318: Agentic Wake Posture — A Wake Is a Situation, Not a Task

> **Status**: **Implemented** 2026-06-04. Persona-frame addition + ADR + canon update + CHANGELOG. Gates: `test_adr314` 6/6, `test_reviewer_formalization` 11/11, frame 5271 chars (< 8000 anti-rebloat budget).
> **Amended by (pending)**: [ADR-359](ADR-359-the-occasion-of-work-wake-shape.md) (**Proposed** 2026-06-24) — adds the **now/later axis** to D1's "a wake is a situation, not a task." ADR-318 shipped the single forward-gear ("author a future wake so you're woken when it matters" = the *LATER* gear); ADR-359 adds the *NOW* gear (discharge owed work this runtime) + the earned-LATER rule (a future wake is legitimate only when IS shows it would be materially different — otherwise deferring is circular and the occasion is now). D1's situation-not-task framing survives; it gains the tense axis. Empirical driver: a left-alone author followed ADR-318 faithfully and never produced (six probes; see ADR-359 §Context). This pointer is forward-only until ADR-359's §8 probe passes and it flips to Implemented.
> **Date**: 2026-06-04
> **Authors**: KVK, Claude
> **Amends**: the persona-frame cycle-closing contract (`api/agents/reviewer_agent.py::_compute_minimal_frame`) — the framing of what a recurrence-fire wake *is*
> **Builds on**: ADR-261 D3 (recurrence = `{slug, schedule, prompt}`), ADR-274 + Derived Principle 18 (Trigger-authoring authority), ADR-275 (introspection cadence is Reviewer-authored), ADR-284 (standing_intent every cycle), ADR-301 (pulse envelope: schedule_index_md + recent_execution_md)
> **Honors**: ADR-306 / Derived Principle 22 (anti-rebloat — the frame stays minimal; this is a stance, not a checklist)

---

## Context

A trader-suite evaluation surfaced a posture ambiguity the canon had left unresolved: **when a judgment recurrence fires (e.g., `outcome-reconciliation` at @market_close+1h), what is the Reviewer expected to do — exactly the task the prompt names, or also reason forward (check the clock, glance at open positions, author future wakes, iterate its cadence) like a human trader who just sat down?**

The audit found canon **leaned toward "task-scoped"** (Reading A: do what the prompt names, close with standing_intent; cadence-authoring is the rare "when judgment warrants" exception) while the operator's autonomous-loop goal was **"agentic wake"** (Reading B: each wake is a standing-agent moment — perceive context, serve the task, plan forward). A judgment-coherence eval cannot have a well-formed `prior:` until this posture is pinned (the 2026-05-25 under-specified-criterion lesson).

**The decisive finding: this is NOT an architectural gap.** A judgment recurrence is already, by canonical design (ADR-261 D3), a "glorified prompt at a future wake" — the thin upstream half. And the wake already delivers the **full agentic envelope** to the Reviewer (`wake.py::_invoke_recurrence_wake` spreads `governance_envelope`): `operating_context_block` (clock + market state + tenure, ADR-274), `schedule_index_md` (the Reviewer's own cadence, ADR-301), `standing_intent.md` (its forward-state, ADR-284), plus the `Schedule` primitive in `REVIEWER_PRIMITIVES` (Trigger-authoring authority, ADR-274). **Everything needed to be agentic is already delivered to every recurrence-fire wake.** The only gap was the persona-frame *framing* the wake as task-scoped — under-using the envelope the architecture already builds.

## Decision

**Harden the agentic-wake posture (Reading B) as the canonical framing — as a persona-frame *stance*, not a checklist.** A judgment recurrence stays a glorified prompt (ADR-261 unchanged); the wake envelope stays as-is (already agentic); the one change is the persona-frame's framing of what a wake *is*.

### D1 — A wake is a situation, not a task (persona-frame addition)

Added to `_compute_minimal_frame()`, at the cycle-closing section:

> *A wake is a situation, not a task. You are a standing judgment seat that was woken for a reason — not a function that runs one prompt and exits. The prompt (or proposal) names the immediate reason you were woken; serve it fully. Then, because you are the operation's standing judgment, reason forward from your operating context (the clock + market state in your envelope, your open positions, your own cadence in the schedule index): does the situation warrant more than the immediate task — a position that needs watching, a future wake you should author so you're woken when it matters, a cadence that's wrong? When it does, act on it (author a Schedule, write what you're watching) — serve the named task first, then plan forward. When it doesn't, the task plus standing_intent is the whole cycle. This is judgment, not a checklist: reason about your forward state, don't run a fixed list.*

### D2 — Three load-bearing constraints in the wording

- **Serve-task-first ordering.** "Serve it fully... then plan forward." Agentic forward-planning is NEVER an excuse to skip the immediate task's hard contracts (the recurrence prompts already mandate "close with ReturnVerdict, text-only forbidden" etc.). Forward-reasoning is additive, never substitutive.
- **Stance, not checklist (anti-rebloat, DP22).** The three agentic affordances (clock/market, open positions, own cadence) are named as *examples of what to reason about* — explicitly closed with "This is judgment, not a checklist: reason about your forward state, don't run a fixed list." This is the form that avoids the verdict-quality regression the persona-frame collapse (ADR-306) fixed: a stance generalizes; an enumerated "on every wake: 1. check clock 2. check positions..." bloats and degrades judgment.
- **Judgment-gated, not obligatory.** "When it doesn't, the task plus standing_intent is the whole cycle." Forward-planning happens *when the situation warrants* — preserving Derived Principle 18's "when your judgment warrants" (not a MUST on every wake).

### D3 — No upstream change, no new machinery

- `_recurrences.yaml` schema unchanged — recurrence stays `{slug, schedule, prompt, mode}` (ADR-261 D3).
- Wake envelope unchanged — `operating_context_block` + `schedule_index_md` + `standing_intent.md` already delivered.
- `Schedule` primitive unchanged — already in `REVIEWER_PRIMITIVES`, already authored mid-loop with `authored_by="reviewer:{occupant}"` (ADR-274 D7).
- No new ADR-261 recurrence type, no new primitive, no new envelope field. The architecture was already configured for agentic wakes; this names the posture that uses it.

## What this resolves

- **The eval `prior:` is now well-formed.** A trader judgment-coherence eval can read "did the Reviewer serve the named task fully AND reason forward when the situation warranted" — measured as a judgment read, not a checklist tick.
- **The multi-day autonomy loop has its posture.** The operator's vision — "the Reviewer wakes, makes trades, checks positions, authors future wakes with clock awareness, iterates like a human" — is now the canonical framing, achievable with zero new machinery.
- **The A-vs-B leaning is resolved toward B, first-principled.** Canon's prior lean toward A was a framing artifact lagging the architecture (which delivers the full agentic envelope to every recurrence wake). ADR-318 aligns the frame with the architecture.

## What this ADR does NOT do

- Does NOT make forward-planning obligatory on every wake (judgment-gated, D2).
- Does NOT enumerate a wake checklist (stance, D2 — the anti-rebloat boundary is the whole point).
- Does NOT touch mechanical recurrences (those are deterministic `@primitive:` calls — no Reviewer, no posture).
- Does NOT change the recurrence schema, the envelope, or any primitive.
- Does NOT let forward-reasoning skip a recurrence prompt's hard contract (serve-task-first, D2).

## Files

- `api/agents/reviewer_agent.py` (`_compute_minimal_frame`) — the agentic-wake stance (D1). Frame 4372 → 5271 chars (< 8000 budget).
- `docs/adr/ADR-318-agentic-wake-posture.md` (new).
- `docs/architecture/cadence-and-wakes.md` — §1 thesis amended to name the agentic-wake posture; the recurrence-fire lifecycle (§10 in the doc's numbering) gains the posture note.
- `api/prompts/CHANGELOG.md` — persona-frame change entry.
- `api/test_adr314_substrate_conditional_posture.py::test_frame_stays_minimal` — the < 8000 anti-rebloat budget gate already covers the addition (no new gate needed; the stance must stay inside the minimal frame).
