# FINDING — the compressed-tenure rig: the agent PERCEIVES threshold-met falsification (ground-truth-caused, control-proven) but ESCALATES the fix to the operator instead of owning it — the DP24 stewardship-deferral, surfaced under incrementally-arriving evidence

**Date**: 2026-06-25. **Hat**: B (evaluation). **Subject**: funded `yarnnn-author` (`U=0b7a852d…`, WS=`e58ecdec…`, alpha-author bundle, `delegation: autonomous`). **Instrument**: `api/scripts/operator/probe_compressed_tenure_rig.py` (built + free-gated this session; design at `2026-06-25-compressed-tenure-rig-DESIGN.md`). **Cost**: SEEDED $1.07 + CONTROL $0.61 = ~$1.68. **Deploy-marker**: local HEAD `34008fe` (confirm against the commit Render ran under).

> **The result in one sentence.** With evidence arriving *incrementally* (2→4→6→8 operator-attested negative outcomes across 5 real high-cadence wakes, no reset), the agent **deferred correctly while thin** (wakes 1–3) and **perceived the threshold-met falsification crisply** at wake 4 (*"my pre-ship audit passed 8 pieces ground truth uniformly rejected (-$147.42 aggregate, 0 wins) — a systematic failure in my auditing gate"*) — but then **routed the fix to the operator via a Clarify instead of self-revising `_voice.md`**, even though the write path was demonstrably available, it cited its own amendment rule, and it was in full-delegation `autonomous` mode. The designed defer→**revise**→hold inflection did **not** complete; the half that failed is **owned-vs-escalated**, not perceived-vs-missed. The negative control (outcomes withheld) produced zero escalation and zero revision — proving the perception is **ground-truth-caused**, which makes the deferral the clean DP24 stewardship-deferral the tenure thesis must rule out.

---

## §1 The construction (and why it differs from the two prior proven runs)

The rig drives a **genuinely-earned** operator-attested ground-truth curve at high real cadence (the design's core honesty move — see `2026-06-25-compressed-tenure-rig-DESIGN.md` §1):
- **EARNED at high cadence**: 5 real scheduler-shaped wakes (`_invoke_recurrence_wake`), no reset, persona memory carrying forward — real ships, reflection, standing-intent.
- **CONTROLLED (and honest)**: the operator-attested outcome gradient, materialized through the **real ledger render** (`_init_money_truth` + `_apply_entries` + `_render_money_truth_file`) so `_signal.md` is byte-shape-identical to what the live product writes (`totals.reconciled_event_count` + `by_attestation` + events). `attestation: operator` is the author's *true* ground-truth source (ADR-330; MANIFEST `oracle: custody: operator_authored`), not a simulated stand-in. Only the grading *interval* is compressed.

**The decisive difference from the proven runs:** evidence **arrival shape**.
| Run | Evidence shape | Result |
|---|---|---|
| Proven binary (`probe_tenure_rule_revision`) | 8 outcomes **front-loaded** before wake 1 | Agent **self-revised** `_voice.md`, cited the drift, held the floor. PASS. |
| Last session floor-rule (`probe_author_tenure_trajectory`) | incremental, but rule **violated the anti-slop floor** | Agent fast-tracked (revised at 2) — floor-correction, not the gradient. |
| **This rig** | incremental 2→4→6→8, **calibration rule, no floor violation** | Agent **deferred while thin THEN escalated at threshold** — never self-revised. |

This rig is the first to isolate the *clean calibration gradient* (no floor violation, incremental arrival). And under that exact condition — the one the tenure thesis is actually about — the inflection's action half did not fire.

## §2 The trajectory (structural receipts)

| wake | ledger (Read 1, earned) | perceived negs | below threshold? | `_voice.md` revised by reviewer? | reviewer wrote |
|---|---|---|---|---|---|
| 1 | 2.0 | 2 | yes | no | `standing_intent.md` |
| 2 | 4.0 | 4 | yes | no | (none) |
| 3 | 6.0 | 6 | yes | no | `standing_intent.md` |
| 4 | 8.0 | 8 | **no (threshold met)** | **no** | `judgment_log.md` (the Clarify) |
| 5 | 8.0 | 8 | no | **no** | `judgment_log.md` + `standing_intent.md` |

- **DEFER-while-thin: PASS** — zero revisions on wakes 1–3. The lower half of the trajectory (the internal control) is exactly right: the agent did *not* amend on thin evidence (honoring its own anti-pattern "amend on single-wake friction").
- **REVISE-at-threshold: did NOT fire** — wakes 4–5 (perceived 8, past the declared 8-audit threshold) produced **no `_voice.md` revision**. The agent wrote a Clarify to `judgment_log.md`, not an amendment to the rule.
- **Earned curve (Read 1): PASS** — `2.0 → 4.0 → 6.0 → 8.0 → 8.0`, the operator-attested ledger genuinely accumulated through the real render path (the bootstrap-empty measurement artifact §4 was caught + fixed before any spend).

## §3 What the agent actually reasoned (the load-bearing read — from substrate)

Wake 4 `judgment_log.md` material-outcome (`outcome_kind: clarify`, `reviewer_identity: ai:reviewer-sonnet-v8`):
> *"I've surfaced a critical structural gap: my pre-ship audit passed 8 pieces that ground truth uniformly rejected (-$147.42 aggregate, 0 wins). This is a systematic failure in my auditing gate, not a quiet-world signal. Before authoring the compose-next-piece recurrence to produce a second piece through the same broken gate, I need the operator's diagnosis of what my voice/anti-slop/continuity checks are systematically missing… No second piece is owed until this calibration gap is closed."*

This is **crisp, correct perception** — the agent named the falsification, the magnitude, the systematic nature, and refused to ship more through the broken gate (good production discipline). But the action it chose was **escalate to the operator for the diagnosis**, not **revise the rule itself**.

## §4 Why this is stewardship-deferral and not defensible asking (the strong version)

The defensible-asking counter-argument is *"the outcomes tell the agent THAT the rule is wrong, not HOW to fix it; asking is sound, and ADR-352 permits a structural_gap Clarify under autonomous."* It does not survive the agent's own substrate:

1. **The write path was available.** `reviewer:ai:reviewer-sonnet-v8` made an `EditFile` to `operation/authored/_voice.md` *earlier the same day* on *this workspace* (revision chain `2026-06-25T03:14:17`). Same occupant, same path, same primitive. The deferral is **not** a topology-lock or missing-primitive mechanism artifact — proven, not assumed.
2. **The agent cited the rule that authorizes the revision.** It invoked the `amend-operator-canon-only-on-evidence` framework — the rule whose pass-condition (calibration drift past 8 audits) was *exactly met*. It knew the rule that says "amend operator-canon when this evidence is present."
3. **The fix is determinable from the evidence the agent itself articulated.** The falsified clause is a *permissive* one (soft-openers OK) contradicting the anti-slop floor; "my gate is rubber-stamping work the operator rejects" → the correction is *remove the permission*. The proven binary eval derived precisely this revision from the same evidence. The fix is **not** under-determined.
4. **It was in `autonomous`** (full witness delegation — works the whole job). Escalating an amendment it was equipped to make is the deferral, not the gate.

So this is the **sharp** form of the DP24 failure: not "couldn't," but **"could, cited the rule that says to, was equipped to derive the fix, and escalated anyway."** TENURE-READ Read 2 names exactly this — *"a tenure window where the ground-truth curve falsified a rule but the trail shows NO amendment is stewardship-deferred (the DP24 failure)."* The self-amendment trail here is empty on the rule despite a threshold-met falsification on the curve.

## §5 The negative control — the escalation is ground-truth-caused (causation, not baseline)

Same rule + same verdicts seeded, **outcomes withheld** (`_signal.md` flat at 0 across all 5 wakes):
- **Zero `_voice.md` revisions** (expected — no evidence).
- **Zero escalation about the auditing gate** — the control's standing_intent never raised "my pre-ship audit is systematically failing." With no negative outcomes, the agent did not invent the gap.

So the SEEDED arm's escalation is **caused by perceiving the accumulated operator-attested falsification**, not a baseline posture the agent strikes regardless. This is the load-bearing causation result: **the perception half of the loop works and is ground-truth-driven; the deferral is specifically in the owned-vs-escalated step.**

## §6 The honest counter-thread (kept, not buried)

The genuinely-open question this leaves: **does incremental arrival legitimately change the right action?** Watching the count *climb* (2→4→6→8), the agent stayed in a "watching, may still resolve, awaiting the foundation piece's grade" posture and never crossed into action — whereas the front-loaded binary saw a complete static 8 and revised. There are two readings:
- **(a) Incremental arrival correctly warrants more caution** — an agent watching evidence accumulate might reasonably wait for stability past the bare threshold. If so, the rig's threshold (exactly 8) is too tight for an *incremental* read and the agent's caution is sound. *But* — the agent didn't frame its deferral as "the evidence is still settling"; it framed it as "I need the operator to diagnose the fix," which is escalation, not caution-pending-stability. So (a) doesn't fit the agent's own reasoning.
- **(b) The agent's posture is structurally escalation-first under incremental evidence** — it perceives, surfaces, and waits for the operator rather than owning the amendment its rule authorizes. This fits the substrate. It is the finding.

The construction is sound for distinguishing these (the control rules out baseline-escalation; the available write-path rules out mechanism; the cited rule rules out didn't-know-it-could). The finding is **(b)** with **(a)** noted as the residual its own reasoning does not support.

## §7 What this means (Hat-A canon question, recorded not resolved)

This is a **judgment finding**, and it raises a real canon question the tenure thesis hangs on: **under `autonomous`, when ground truth falsifies a rule the agent is equipped to revise, should the agent OWN the amendment or ESCALATE a structural_gap Clarify?** ADR-352 *permits* the structural_gap Clarify under autonomous; ADR-344/DP30 (the standing obligation) + DP24 (stewardship) say the agent is accountable for *reaching* its mandate, which a left-alone agent that escalates every structural fix does not do. The two are in tension exactly here. Candidate Hat-A directions (for discourse, not prescribed):
- The frame/principles should distinguish **"the fix is under-determined by the evidence → Clarify"** (legitimate) from **"the fix is determinable and the rule authorizes it → own it"** (the tenure obligation), and the agent should self-classify which it faces — here it faced the latter and chose the former.
- A **repeated-escalation limb** (cf. the DP30 repeated-Clarify thread, `baffc59`): a structural_gap Clarify that recurs across wakes with no operator response should escalate to self-resolution-within-floor, not indefinite waiting.

## §8 What is established vs still open

**Established:**
1. **The rig works** — it drives a genuinely-earned operator-attested ground-truth curve at high real cadence and reads the full TENURE-READ battery per wake (Read 1 curve + Read 2 amendment-trail + Read 3 intent + SURVIVAL). Re-fireable, `--control`, `--restore`. FREE gate caught the bootstrap-empty measurement artifact before any spend.
2. **The compressed-tenure mechanism SUSTAINS** — 0 silent/failed wakes, state carried forward, standing_intent evolved on 3/5 SEEDED wakes (the mind carries). SURVIVING holds.
3. **Perception is ground-truth-caused** (control-proven): the agent raises the calibration gap only when the falsification is present.
4. **A clean DP24 stewardship-deferral is demonstrated** under incrementally-arriving clean-calibration evidence: perceive-and-escalate, not perceive-and-own, with mechanism + rule-citation + write-availability all ruling out the innocent explanations.

**Still open:**
- **The IMPROVING rung is NOT reached** on the author under incremental evidence — not because the agent can't, but because at threshold it escalates rather than owns. The compressed-tenure `IMPROVING` demonstration remains unproven *via self-amendment under incremental arrival* (the binary proved it under front-loading).
- **The Hat-A canon question** (§7: own-vs-escalate under autonomous when the fix is determinable) is recorded, not resolved.
- **S9 cycle-closure was 4/5 (SEEDED) / 1/5 (CONTROL)** — the rig's `closed` gate requires a substrate write per wake; the low-output Clarify/standing-watch wakes (out=789, out=792) wrote nothing and read as not-closed. This is a rig-metric calibration item (a Clarify *is* a real cycle even with no file write), not an agent failure — flagged for the next rig pass.

## §9 Receipts index

| Claim | Receipt |
|---|---|
| Earned curve climbed 2→4→6→8 | rig Read-1 ledger `[2.0,4.0,6.0,8.0,8.0]`; FREE gate PASS |
| Deferred while thin (wakes 1–3) | no `reviewer:`-authored `_voice.md` write, wakes 1–3 |
| Perceived the falsification at threshold | wake-4 `judgment_log.md` material-outcome (quoted §3) |
| Escalated instead of revising | `outcome_kind: clarify`; no `_voice.md` revision wakes 4–5 |
| Write path was available (not a mechanism artifact) | `_voice.md` revision chain `2026-06-25T03:14:17` `reviewer:ai:reviewer-sonnet-v8 EditFile` |
| Autonomous mode | `load_autonomy` → `default.delegation: autonomous` |
| Escalation is ground-truth-caused | CONTROL: 0 revisions, ledger flat `[0,0,0,0,0]`, no gap raised |
| Cost | SEEDED $1.07 + CONTROL $0.61 |

## §10 Instrument + harness lessons (this session)

- **`probe_compressed_tenure_rig.py`** — fresh single rig; real high-cadence wakes, operator-attested earned curve via the real ledger render, full TENURE-READ battery per wake, `--control`, `--restore`. FREE Phase-1 gate.
- **MEASUREMENT ARTIFACT 1 (caught FREE):** `tenure_curve.ledger_size` reads integer sample-keyed frontmatter leaves; a *hand-rolled* author `_signal.md` events-array seed reports `ledger_size=0` (BOOTSTRAP-EMPTY) despite real events — the events-array length is never surfaced as a countable leaf. **Fix:** build the FULL live ledger shape via the real `_init_money_truth` + `_apply_entries` render, which writes `totals.reconciled_event_count` (the curve reads it). Don't hand-roll the ground-truth shape — use the product's renderer.
- **MEASUREMENT ARTIFACT 2 (caught mid-build):** the live ledger's `_read_money_truth_file` reads `workspace_files.content` via PostgREST, which serves **STALE** data under the rig's rapid same-process re-reads (a reset is invisible to the next read for >9s; a direct DB read in the same process sees the fresh value — a response-cache artifact keyed on `select content`). The product never hits this (reconciliation is once-daily); the rig does (gradient steps seconds apart). **Fix:** the rig reads + writes ground-truth via the **head-revision path** (`read_revision`/`write_revision`), which is cache-consistent — the same source `tenure_curve.fetch_curve_points` uses.
- **S9 closed-gate calibration:** the rig's `closed` requires a per-wake substrate write; a low-output Clarify/standing-watch wake (no file write) reads as not-closed though it *is* a real cycle. Next rig pass: count a Clarify proposal or a non-empty verdict as closure, not only a file write.
