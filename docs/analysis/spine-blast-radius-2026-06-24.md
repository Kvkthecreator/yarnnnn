# Blast-radius map: the ask-shaped wake re-founding — what survives, what re-derives, what fires the ask

**Date**: 2026-06-24
**Hat**: B → A. Companion to `the-wake-is-a-pre-authored-ask-2026-06-24.md` (the spine, receipt-backed by `2026-06-24-spine-present-tense-ask-VALIDATION.md`). This doc maps the change surface honestly so "near-clean-slate" has a concrete boundary, hardens the open edge ("what fires the ask"), and scopes the uncommitted ADR-359 working-tree edits.
**Status**: Pre-ratification conviction. No code moved by this doc.

---

## 0. First, the conflation that was making this hard to reason about

"Recurrence" and "wake" are two different things the current system fuses, and the fusion is the confusion:

- A **wake** is a *firing event* — something that says "act now." There are exactly five sources (ADR-296 v2, `services/wake_sources/`): `cron_tick`, `addressed`, `proposal_arrival`, `substrate_event`, `manual_fire`. This layer is sound and **survives**.
- A **recurrence** is *one configuration of the `cron_tick` source* — a stored `{slug, schedule, prompt}` in `_recurrences.yaml`. The `schedule` says *when to fire*; the `prompt` is *the ask the wake carries*.

**The bug, stated precisely**: the recurrence's stored `prompt` IS the ask, and a bundle-authored stored prompt is structurally **standing-state framing** ("assess the operation against its mandate"), never a **present-tense imperative** ("compose this week's scene now"). The probe proved the difference is decisive: same agent/substrate, `addressed`'s live `user_message` composes, `cron_tick`'s stored `recurrence.prompt` defers (`wake_sources/cron_tick.py` hands `{recurrence, context}`; `wake_sources/addressed.py` hands `user_message`).

So you are not confusing two things that should stay separate. You are correctly sensing that **recurrence-as-stored-prompt is doing a job it is structurally bad at: carrying the ask.** The re-founding separates them: the *wake* (firing) stays; the *ask* (the present-tense imperative) gets constructed at fire-time, not stored as standing prose.

---

## 1. The survival table — what the spine does NOT touch

The substrate floor and the firing plumbing are already CC-analogues done right. They survive intact.

| Layer | Files (~LOC) | Verdict | Why |
|---|---|---|---|
| **Authored substrate** | `authored_substrate.py`, `workspace_files`/`_versions`/`_blobs` (ADR-209) | **KEEP whole** | CC's filesystem + attribution. The moat's floor. Untouched. |
| **Primitives as tools** | `services/primitives/*` (ADR-168/321/322/337) | **KEEP whole** | CC's tools. The agent reads/writes substrate on demand — exactly CC's "read files via tools, don't pre-dump." |
| **Cost substrate** | `budget.py` (~306, ADR-327) | **KEEP whole** | `_budget.yaml` = dollar envelope; "how often is the agent's allocation problem, not an operator dial." The spine's exact economic shape. (`pace.py` already deleted — CLAUDE.md stale.) |
| **Wake firing plumbing** | `wake.py`, `wake_queue.py`, `wake_drainer.py`, `scheduling.py` (~3,200) | **KEEP, light edits** | The 5 sources + single-lane drain + budget gate. This is the "something must fire in the operator's absence" machinery. Survives; only the *payload it builds* changes (§3). |
| **Consequential gate** | ADR-307 permission gate + ADR-352 ask-vs-act + witness dial | **KEEP whole** | CC's `getActionsSection` (reversibility + blast radius + ask-if-risky), one paragraph. The moat's real independence. Untouched. |
| **Ground-truth calibration** | Axiom 8, `_money_truth.md`/outcome reconciliation | **KEEP whole** | The other real independence source. Untouched. |
| **Mechanical recurrences** | `track-*` entries (`mode: mechanical`, ADR-335) | **KEEP whole** | Zero-LLM deterministic intake. Not judgment wakes; carry no ask. They FEED events that become asks (§2). |
| **Reactive hooks** | `substrate_event.py` + `_hooks.yaml` | **KEEP, becomes central** | A substrate transition IS a present-tense ask by construction ("this draft is ready — audit it"). The spine *promotes* this path. |

**~6,500 LOC of the ~7,200 in the wake/reviewer band survives.** The re-derivation is concentrated, not sprawling.

---

## 2. The re-derivation table — what changes, and how it SHRINKS

The prosthetics that simulate a present principal. All concentrated in `reviewer_agent.py` (2,105 LOC; 92 hits of `stand_down`/`non_performance`/`recovered_verdict`/`silent_exit`/`ReturnVerdict`/`standing_intent`) + the ask-construction sites.

| Prosthetic | Where | Fate under the spine |
|---|---|---|
| **Verdict enum** (`stand_down`, `non_performance`, …) | `reviewer_agent.py` RETURN_VERDICT_TOOL | **SHRINK to proposal/judgment verdicts only** (`approve`/`reject`/`defer` for consequential acts). `stand_down`/`non_performance` were terminal moves for a *contract that requires a close*; under "answer the ask, then stop," an unanswered ask is visible *as* an unanswered ask — no verdict needed for "did nothing." |
| **Recovery synthesizer** (fabricates `stand_down`/`non_performance` on silent exit) | `reviewer_agent.py` silent-exit + budget-exhaustion paths | **DELETE.** This exists *only* because the loop demands a terminal move; it is the literal mechanism that "privileges inaction" (the falsification's structural-fact #2). CC has no analogue: silence is silence. With ask-shaped wakes, a wake that produces nothing on an answerable ask is a *visible non-completion of that ask* (the ask persists/re-fires), not a fabricated clean close. |
| **Terminal-move contract** ("close with verdict or standing_intent") | `reviewer_agent.py::_compute_minimal_frame` | **SHRINK to CC's "stop when the ask is answered."** `standing_intent` survives as a *useful artifact* (what I watched, why I'm waiting) but stops being a *required terminal move* — it's optional output, like CC writing a note. |
| **~20-section pre-framed envelope** | `reviewer_envelope.py` + `reviewer_agent.py::_build_user_message` | **SHRINK toward CLAUDE.md-shape**: static cached governance (MANDATE + principles + AUTONOMY) + **the ask** + tool-readable substrate. The per-wake re-read of 20 framed blocks → read-on-demand (CC's model). Governance is the persistent system-prompt analogue; the ask is the user-message analogue; everything else the agent fetches when the ask needs it. |
| **Wake-taxonomy / recurrence-types** (named judgment slugs, `mode: judgment`) | `_recurrences.yaml`, `recurrence.py`, `scheduling.py` | **RE-SHAPE, not delete** (§4). The schedule survives; the stored standing-state `prompt` is replaced by an ask-builder. |
| **Occasion header** (ADR-359 D1) | `reviewer_envelope.py::_compute_occasion_fact` | **REPURPOSE as ask-content** (§5). The computed owed-vs-produced fact is good *raw material for an ask*; it was just delivered as a header in a maintenance frame instead of as the ask itself. |

**Net**: the change DELETES more than it adds. The implementation gets *smaller* — your thesis. The 92 verdict/recovery hits collapse toward CC's zero; the 20-section envelope collapses toward 3.

---

## 3. The uncommitted ADR-359 working-tree edits — scoped (operator: "do whatever, this discourse overrides in full")

The uncommitted diff (`occupant_contract.py` + `reviewer_agent.py` + `reviewer_envelope.py` + `reviewer_audit.py`, CHANGELOG `[2026.06.24.1]`) added three things. Spine verdict on each:

| ADR-359 edit | Spine verdict | Rationale |
|---|---|---|
| **D1 `_compute_occasion_fact()`** (computed owed-vs-produced) | **KEEP the computation, REPURPOSE the delivery** | The *fact* (scene owed, 0 produced, nothing gates it) is exactly the raw material an ask-builder needs. The spine doesn't want it as a *header in a heartbeat frame*; it wants it as *the body of the ask* ("compose the owed scene now — here's why nothing gates it"). The function survives; its caller changes from "render header #21" to "build the present-tense ask." |
| **D2 occasion-nudge** (mid-loop "stop, produce now") | **DELETE** | This is a prosthetic *on top of* a prosthetic — it patches the recovery synthesizer to nudge before fabricating a close. The probe proved the nudge is *unnecessary when the wake is ask-shaped* (it never fired and production happened anyway). It only exists to rescue a standing-state-framed wake. Ask-shaped wakes don't need rescuing. |
| **D2(b) `non_performance` verdict** | **DELETE** | Same root: a terminal move for "owed but didn't produce." Under the spine, that state IS "the ask went unanswered" — visible without a verdict. Adds enum surface the spine is trying to retire. |
| **D3 envelope ordering** (occasion leads) | **MOOT** | Reordering headers is irrelevant once the ask *is* the message rather than one header among twenty. |

**Disposition**: I will **revert the uncommitted edits** (they encode the header-in-a-frame approach the spine supersedes), but **preserve `_compute_occasion_fact` as a standalone helper** to be re-wired as the ask-builder's input. Net: keep ~40 lines (the computation), drop ~250 (the nudge + non_performance + ordering + frame prose). This is the singular-implementation discipline — we don't ship two answers to "how does owed-output reach the agent."

---

## 4. The hardened thesis — what fires the ask (the open edge, now load-bearing)

The probe proved an *operator-typed* ask composes. The autonomy claim needs: **in the operator's absence, something must construct and fire a present-tense ask.** Three originators, in order of how naturally ask-shaped they are:

### 4a. Event-originated asks (the clean majority — already ask-shaped)
A real-world change IS a present-tense ask. These need almost nothing new — the event *is* the imperative:
- **Perception-field observation** (ADR-335): a watched source changed → "the thing you watch moved — here's the delta; judge it." (`substrate_event` / mechanical `track-*` → reactive hook.)
- **Ground-truth arrival** (Axiom 8): an outcome reconciled → "a trade you made resolved −$X — calibrate." Already the trader's working path.
- **Substrate transition** (`_hooks.yaml`): a draft hit `ready_for_review` → "this is ready — audit it." Already ask-shaped.
- **A proposal arrived** (`proposal_arrival`): another agent/foreign write proposes → "judge this proposal." Already ask-shaped.

**These are why the trader works**: its asks are fired by the market, not stored as prompts. The spine generalizes the trader's accidental correctness into the model.

### 4b. Cadence-originated asks (the author case — the real design work)
Some owed-output is *genuinely time-driven* with no external event to fire it (the author's weekly scene; a Monday status email). For these the *schedule* must fire **an ask, not a stored standing-state prompt**. The design constraint, proven by the probe: the fired thing must be **present-tense, imperative, the-wake-is-about-this** ("compose this week's scene now"), not framing ("assess the operation"). Mechanically this is small: at fire-time, an **ask-builder** composes the imperative from (a) the owed-output contract (`_expected_output.yaml`) + (b) the computed occasion fact (the repurposed ADR-359 D1) + (c) the gap (owed vs produced). The schedule says *when*; the ask-builder says *what's being asked* — and it asks rather than frames.

### 4c. The agnostic janitorial recurrences you proposed — KEEP, and they're the proof the model is right
Your instinct — "keep recurrences agnostic, like daily-update-email-to-user or weekly-stale-substrate-cleanup" — is exactly correct, and here's *why* it works where the judgment recurrences didn't:

**A janitorial recurrence is already an ask, not framing.** "Email the operator today's summary" and "clean up stale substrate" are *imperatives with a concrete deliverable* — they're shaped like `addressed` asks, not like "assess the operation against its mandate." They'll fire-and-do for the same reason the probe composed: the wake is *about* a specific act. So the model isn't "delete all recurrences" — it's:

> **Recurrences survive as a thin, agnostic set of cadence-fired ASKS** — each an imperative with a deliverable (email this; clean that; compose the owed scene). What dies is the **named judgment recurrence whose prompt is standing-state framing.** The schedule layer is fine; the *ask it fires* must be imperative.

This makes the recurrence directory **radically simpler and program-agnostic**: a workspace ships a handful of cadence-fired asks (kernel-universal janitorial: daily-digest, stale-cleanup; + program owed-output: the weekly scene, the trade-review) — all imperatives, none framing, none requiring a per-program judgment-prompt library. That IS the CC-agnostic shape: a tiny, universal set of "do this specific thing on this cadence," plus events that fire asks, plus the operator addressing the seat.

---

## 5. The end-state architecture (one picture)

```
WAKE SOURCES (firing — KEEP)        →  ASK (present-tense imperative — NEW shape)  →  AGENT (CC-shaped loop)
─────────────────────────────────      ────────────────────────────────────────       ──────────────────────
addressed     (operator typed)      →  user_message verbatim                        →  static governance
proposal_arrival (proposal landed)  →  "judge this proposal: …"                         (MANDATE+principles+
substrate_event (draft ready, etc.) →  hook's imperative                                 AUTONOMY, cached)
ground-truth arrival                →  "outcome resolved −$X: calibrate"            →  + THE ASK
cadence (time-driven owed-output)   →  ask-builder(_expected_output + occasion)     →  + tools (read substrate
   ├ janitorial (agnostic)          →    "email the digest" / "clean stale"             on demand)
   └ program owed-output            →    "compose this week's scene now"           →  acts on the ask, STOPS
                                                                                        (no terminal-move
                                                                                         contract; unanswered
                                                                                         ask = visible, re-fires)
budget (ADR-327) gates all firing — KEEP.   consequential gate (ADR-307/352) binds all acts — KEEP.
```

What dies: the stored standing-state judgment prompt, the verdict-as-terminal-move, the recovery synthesizer, the 20-section per-wake frame, the per-program judgment-prompt library. What's born: the **ask-builder** (small) + the discipline that **every cadence/event fires an imperative, never framing.**

---

## 6. Sequence (proposed; each gated, probe-before-canon)

1. **Stability re-run** of the spine probe (1 run so far; confirm the ask composes repeatably + on the trader without regressing its working path).
2. **Revert ADR-359 edits, preserve `_compute_occasion_fact`** as the ask-builder's input (§3).
3. **Build the ask-builder** + wire `cron_tick` judgment recurrences to fire an *imperative ask* instead of the stored framing prompt — re-run the author probe through the FAITHFUL `cron_tick` path (the probe used `addressed`; this proves it under autonomous firing, the real autonomy claim §4b).
4. **Collapse the recurrence directory** to agnostic cadence-fired asks (§4c) — janitorial + owed-output, no named judgment prompts. Re-run both bundles.
5. **Shrink `reviewer_agent.py`**: delete recovery synthesizer + terminal-move contract + the retired verdict surface; loop terminates CC-style. This is the largest single deletion; gate it on the prior steps proving the agent doesn't need the safety net.
6. **Collapse the envelope** to governance(static) + ask + on-demand reads.
7. Canon cascade (FOUNDATIONS/ESSENCE/ADR-318/persona-frame) — *after* the code proves out, doc-first amendments to match.

The blast radius is real but **concentrated and net-subtractive**: ~6,500 LOC survives, the re-derivation is mostly *deletion* in one file + one small new builder. The rewrite is "near-clean-slate" only in the envelope+loop; the substrate, firing, budget, and gate floors are kept. That is exactly the operator's thesis — the right reframing makes the implementation smaller, and lands it where CC sits: a tiny universal set of asks, events that fire asks, and an agent that answers them and stops.
