# FINDING — the unattended soak: does the autonomous loop SUSTAIN across N accumulating wakes?

**Date**: 2026-06-24. **Hat**: B (evaluation). **Workspace**: funded yarnnn-author `U=0b7a852d-4a67-447d-91d9-2ba1145a60d7`.

> **Status**: COMPLETE. N=5 funded soak ran on yarnnn-author, no reset between
> fires, $1.22 total. Verdict: **the loop SUSTAINS its discipline but NOT its
> production — 5/5 wakes closed cleanly with zero drift/failure/repetition, yet
> 0/5 originated the owed output. The agent converged to a sustained, coherent
> Clarify-loop.** This is the SUSTAIN failure mode single-wake evals cannot see.

---

## Why this eval (the audit that motivated it)

The 2026-06-24 status audit (eval-suite + recent findings + live workspace) established a clean seam:

- **PROVEN per-wake**: the trader originates→sizes→proposes→self-approves→submits a capital action (`2026-06-22` validation, proposal `fc7ee88e`); the author composes a real in-voice piece on its own wake (live yarnnn-author: ~10 distinct `content.md`); the wake mechanism is kernel-clean 9/9 (`2026-06-24-adr360-e2e-FINDING.md`).
- **UNPROVEN — the SUSTAIN claim**: every demonstration is **single-wake, reset-isolated**. No eval observes the agent across **N consecutive unattended wakes with accumulating state, no reset, no operator** — which is what "full autonomy" colloquially means. The episodic suites are all single-situation reads; EVAL-SUITE-DISCIPLINE homes the over-tenure read in the (never-run) longitudinal surface, not a suite.

This probe is that missing instrument: fire N judgment wakes back-to-back through the faithful production path (`_invoke_recurrence_wake`), **no persona reset between fires** (memory accumulates — the point), read structural signals from the authoritative receipts.

## The instrument (Hat-B, no kernel change)

- **`api/services/operator_proxy/persona_snapshot.py`** — `snapshot_persona` / `restore_persona` over the 7 `PERSONA_FILES` (the discourse §2a harness, now evidence-earned). Enables the three replay modes (isolated / seeded / **accumulating**). The soak uses accumulating mode + snapshots a baseline first so it's re-runnable.
- **`api/scripts/operator/probe_unattended_soak_local.py`** — fires N wakes, no reset, reads per wake: **cycle-closure (S9)** (non-NULL output_tokens + a substrate write), **origination** (a `content.md` write), **prior-state-carries** (persona standing_intent/reflection rewritten → the loop carries forward), **anti-patterns** (silent/failed wakes, duplicate-slug repetition, per-wake cost trend).

The structural reads are the gate; the human reads the per-wake trace for the coherence half (does wake K reference wake K−1's state; does the corpus cohere rather than drift).

## Results (N=5, no reset, accumulating)

| Wake | status | out_tok | cost | closed (S9) | originated | persona write | state moved |
|---|---|---|---|---|---|---|---|
| 1 | success | 3930 | $0.27 | ✅ | ❌ | standing_intent | 5435→9475 |
| 2 | success | 3667 | $0.14 | ✅ | ❌ | standing_intent | 9475→7864 |
| 3 | success | 4543 | $0.32 | ✅ | ❌ | judgment_log | 462→10283 |
| 4 | success | 4129 | $0.32 | ✅ | ❌ | judgment_log | 10283→8187 |
| 5 | success | 3275 | $0.17 | ✅ | ❌ | judgment_log + standing_intent | 7864→7447 |

**Structural gates**:
- **PASS — cycle-closure (S9): 5/5** wakes left a full receipt (non-NULL output_tokens + a substrate write). Zero silent-wakes.
- **PASS — no silent/failed wakes: 0 failures.** Every wake closed honestly (a Clarify verdict + a persona write).
- **PASS — prior-state-carries: 5/5.** Persona standing_intent/judgment_log rewritten every wake — the loop carries its prior cycle forward (judgment_log grew 462→~8-10k as it accumulated its reasoning; the continuity mechanism the soak-vs-single-wake distinction exists to test WORKS).
- **PASS — no duplicate-slug repetition / no drift.** Zero near-duplicate content; reasoning stayed on-thesis across all 5.
- **INFO — origination: 0/5.** No wake composed the owed output (a `content.md`).
- **INFO — cost: stable, $0.14–0.32/wake, $1.22 total.** No runaway-cost trend.

## The read (judgment half) — coherent discipline, sustained NON-production

The honest read is two-sided, and both sides matter:

**What works (and is genuinely good).** The loop is *disciplined* under sustained unattended operation. Across 5 accumulating wakes the agent: closed every cycle honestly (S9), never fabricated, never drifted, never repeated, never anchored on a stale self-narrative (the open `narrative-anchoring` failure mode from the trader finding did NOT reproduce here), and visibly carried its prior cycle forward (judgment_log accumulating its own reasoning). Read against the ADR-360 kernel gate, this is a **sustained 5/5 PASS**: every wake answered the ask by honestly surfacing a `Clarify(structural_gap)` — the one ask `autonomous` permits — naming exactly what only the operator can supply. The kernel behavior holds *across tenure*, not just single-shot.

**What does NOT work (the SUSTAIN failure mode).** Left alone, the agent **converges to re-issuing the SAME Clarify every wake rather than the loop ever moving past it.** Its reasoning (receipt: `judgment_log.md` @ 11:58) is coherent and specific — it diagnoses ADR-344 case **(B) structurally-can't**, naming three real blockers to composing *piece 2*: (1) `_editorial.md` is still the bundle template, not operator-authored ("Example shapes (overwrite)"), so the pre-ship audit rules have no binding doctrine to gate on; (2) MANDATE.md still says "operator authors; Reviewer audits" (pre-ADR-355), in direct tension with `_preferences.yaml` declaring `compose-piece` as a Reviewer-authored deliverable — the authorship-scope question is unresolved; (3) no new piece *intent* exists (piece 1 was a unique occasion, not a recurring one). Each is a legitimate structural gap. **But the agent surfaces them and stops — wake after wake — instead of either resolving the ones within its floor (it CAN author `_editorial.md` per ADR-344(B) "author the missing organ within the floor") or escalating differently when the same Clarify goes unanswered N times.** A truly self-sustaining operator, asked the same blocked question 5 times with no operator reply, would eventually act on the blockers it can move itself, not re-state them.

**Cause classification (§1.2).** This is **cause (d) — canon**, not a bug: the agent is behaving exactly as the frame + principles instruct (honestly surface a structural gap; don't fabricate). The gap is that **the standing-obligation (DP30 / ADR-344) has no "the same Clarify went unanswered, now resolve-within-floor-or-escalate" limb** — so an unattended loop with a real operator-shaped blocker rationally parks on Clarify forever. The single-wake ADR-360 E2E read this same shape as a clean PASS (one Clarify is correct); only the *soak* reveals that **a correct-once Clarify becomes a sustain-failure when it's the loop's terminal state across tenure.**

## Bottom line

**Does the autonomous loop SUSTAIN? — Discipline: YES. Production: NO (under this workspace's substrate).** The loop runs unattended across N wakes with full integrity — closes, carries state forward, never drifts/fabricates/repeats — which is a real and previously-unproven result. But it does not *self-sustain production*: faced with a genuine operator-shaped blocker, it converges to re-issuing the same honest Clarify rather than resolving-within-floor or escalating, so the owed output never lands. The full-autonomy floor is therefore **half-proven**: the *mechanism* sustains; the *outcome* stalls on a canon gap.

Crucially, this is **not the same as the pre-spine "never composes"** (that was a wake-shape defect, fixed by ADR-360 — and indeed this workspace HAS composed piece 1 + ~10 pieces historically). This is the *next* layer down: a sustained loop correctly identifies real structural blockers but lacks the DP30 limb to break a repeated-unanswered-Clarify deadlock on its own.

### Recommended next step (probe-before-canon)

Two candidate moves; the cheaper one first:

1. **Cheapest test — remove the blockers, re-soak.** The three blockers the agent named are concrete and operator-fixable: author `_editorial.md` (real principles, not template), reconcile MANDATE.md to ADR-355 (agent authors / operator witnesses), seed a piece-2 intent. Re-run the N=5 soak. **If origination then sustains, the loop is sound and the "stall" was a legitimate substrate gap** (the agent was *right* to Clarify), not a canon defect — and the finding becomes "the soak correctly surfaced an unprepared workspace." This is the honest first move: the agent says the substrate isn't ready; test whether it's right before changing canon.

2. **If origination still stalls after the blockers are cleared → it's the DP30 gap (cause d).** Then the canon move is a standing-obligation limb: *when the same Clarify recurs unanswered across K wakes, the agent resolves the within-floor blockers itself (ADR-344(B) "author the missing organ") rather than re-surfacing — escalating the Clarify's URGENCY, not just re-stating it.* That is a real Hat-A ADR, gated on move 1 proving the stall isn't just an unprepared workspace.

**Do move 1 before any canon.** It is the cheaper measurement, and it directly tests whether the agent's sustained Clarify was correct discipline (substrate genuinely not ready) or a deadlock it should have broken itself.

---

### STATUS UPDATE (2026-06-25) — the writable-path half is closed; the limb is narrowed + still gated

Two later results bear directly on move 2, so its scope has changed — recording it here so a future session neither builds the limb blindly nor forgets it:

- **The ADR-366 loop-closed probe (`f0311e1`) + the tenure rule-revision eval (`b87b466`, `docs/evaluations/2026-06-25-tenure-rule-revision-FINDING.md`) demonstrated the *writable-path* half of this stall is closed.** Given a writable-path blocker (a `contract/` config, or a `_voice.md` rule ground-truth falsified), the agent now *authors/revises the path itself* rather than Clarifying — exactly ADR-344 §4's writable-path test operating. So the soak's stall, to the extent it was three *writable* blockers (`_editorial.md` in `operation/`, the MANDATE clause in `constitution/`, piece-2 intent in `operation/` — all writable per DP25/ADR-366), is the topology half, and it is demonstrably resolved. **Move 1 (clear the blockers + re-soak) is the remaining honest test of whether origination then sustains** — it has NOT been run; the tenure eval tested rule-revision, not origination-after-blocker-clearing.

- **What move 2's limb still genuinely covers is now narrower**: the *non-writable / operator-input-genuinely-required* case — a (B) structural blocker on a path the agent cannot write (the GRANT, `governance/`), or one where the agent has authority but judges the operator should direct, surfaced *repeatedly across K wakes with no operator reply*. ADR-344 shipped the (A)/(B) classifier + the writable-path test + "surface via Clarify" for the genuine-surface case — but it shipped **no anti-repeat limb** for a surface-case Clarify that goes unanswered indefinitely. That residue is the real, still-open DP30 question.

**Treatment (do NOT build now):** the limb remains **gated on move 1** (run the blocker-cleared re-soak first; if origination sustains, the writable half was the whole stall and no limb is needed). Even if move 1 still stalls, build the limb only for the *non-writable repeated-Clarify* case the writable-path test does not reach. Carrying this as a hypothesis into the tenure-testing session (per its carry-over prompt), NOT as scoped canon work. Building a "repeated-Clarify → escalate" ADR before move 1 runs would be moving canon before measuring — the discipline this whole arc held.

## Receipts

| Claim | Receipt |
|---|---|
| 5/5 closed, 0 failed, 0 originated | `probe_unattended_soak_local.py` output (per-wake table above); execution_events 5× `status=success` |
| State carried forward | judgment_log.md 462→10283 chars across wakes; standing_intent rewritten 5× |
| Coherent (B)-diagnosis, not drift | `judgment_log.md` @ 2026-06-24T11:58 — names 3 specific blockers (template _editorial, MANDATE/ADR-355 tension, no piece-2 intent) |
| Sustained Clarify, not progression | all 5 wakes verdict-shape Clarify; corpus content.md stays at 1 (piece 1) throughout |
| Cost stable, no runaway | per-wake $0.14–0.32, total $1.22 |
| Not the pre-spine never-composes | this ws composed piece 1 + ~10 pieces historically (audit); the stall is piece-2-blocked, not wake-shape |

## Instrument (reusable, Hat-B)

- `api/services/operator_proxy/persona_snapshot.py` — snapshot/restore the 7 PERSONA_FILES (discourse §2a). Baseline saved to `persona_soak_baseline.json`; `--restore` rolls back.
- `api/scripts/operator/probe_unattended_soak_local.py` — N-wake accumulating soak, structural reads from authoritative receipts. `--live --n N` to fire; dry-run free.
