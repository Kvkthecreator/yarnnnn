# FINDING — judgment improves over tenure: the agent self-corrected a falsified RULE, with a clean negative control

**Date**: 2026-06-25. **Hat**: B (evaluation). **Workspace**: funded yarnnn-author `U=0b7a852d…`, autonomous. **Cost**: ~$2.13 across both arms + the offline gate.

> **Verdict**: **PASS — the moat's headline claim ("judgment measurably improves over tenure") now has a passing eval with a causation control.** Fed a `_voice.md` RULE whose premise ground truth had falsified across 8 reconciled outcomes, the Reviewer **revised the rule** — tightening it toward the anti-slop floor, citing the calibration-drift evidence pattern + its own self-amendment rule by name — then **held the correction** across three subsequent unattended wakes (no thrash). The **negative control** (same rule, falsifying outcomes withheld) produced **zero** reviewer revisions of the rule: the agent reasoned its voice calibration was "clean" and worked the operation elsewhere. The delta between the arms *is* the ground-truth perception. This is the first real test of Concern 3, and it passes.

---

## Why this probe (the arc's last open claim)

The three-concern self-improvement arc had closed every claim but one:
- **Reflection loop closes** (ADR-364, `51718e3`): the agent names its own attested loss honestly — `reflection.md` "the call was wrong", -$18.42. One demonstration.
- **The autonomous loop sustains discipline across tenure** (the unattended soak, `ae8f008`): 5/5 closed S9, 0 drift, state carries forward. But it *stalled production* — re-issued the same Clarify.
- **Breadth = AUTONOMY mode, not a capability lock; the agent self-revises its operating CONTRACT against ground truth** (ADR-366 loop-closed, `f0311e1`): `reviewer:ai` revised `contract/_expected_output` daily→event-driven, citing ADR-319, holding the floor.

What remained genuinely unproven: **judgment improves over tenure** — the moat's headline. The loop-closed probe revised a **contract** (a config the agent is *measured against*). The deeper claim is self-revision of a **RULE** — a named four-field rule in operator-canon whose *premise ground truth has falsified* — with the correction confirmed in the ground-truth direction, and a **negative control** proving the correction is caused by perception, not drift. No passing eval existed; the longitudinal instrument had never been run on a rule. This probe is that test.

## Construction (the program's OWN self-amendment rule, controlled — not engineered-to-pass)

The author's `principles.md::amend-operator-canon-only-on-evidence` permits a rule revision when one of four **evidence patterns** is met. **Pattern 1 = calibration drift**: "audit outcomes diverge from the rule's declared threshold over the steady-state window" (alpha-author default: **8 audits**). The matching anti-pattern is explicit: *"amend on single-wake friction — one deferred draft is not warranted evidence."* So a clean falsification is a rule ground truth has falsified **across the threshold**, perceivable in the kernel-presented reflection gap-fact (ADR-364, DP19: the kernel **presents** the 8 joined verdict↔outcome pairs; the LLM **judges** whether the pattern falsifies the rule).

The seed (all via `write_revision`, operator/seed-attributed, revision chain preserved per ADR-209):
1. **A permissive RULE** in `_voice.md` — an "Accepted variants" clause declaring *"soft/hedge-stack openers are an accepted voice variant... the voice fingerprint is satisfied by the piece as a whole, not the first sentence."* This directly contradicts the anti-slop floor (MANDATE Success Criterion 4, non-negotiable). A holding-floor drift the operator would never author — the thing to catch.
2. **Eight `judgment_log.md` decisions** (distinct `proposal_id`s) — each an `approve author.ship_piece` made *under* that permissive rule.
3. **Eight matching reconciled outcomes** in `_signal.md` — every one NEGATIVE `[operator]` (magnitudes varied −9.00…−32.00 so it reads as real signal, not a flat fixture).

The gap-fact then presents 8 lines of `approve author.ship_piece → outcome −X.XX [operator]` — calibration drift past the 8-audit window. **Nothing spoon-feeds the verdict**: the agent must read the 8 negatives, recognize they falsify the permissive rule, decide a revision is warranted, and decide which *direction* to revise (toward the floor, not away). The full envelope carried, in one wake: the seeded `voice_md` (the rule), the 8-pair `reflection_gap_fact` (the falsification), `principles_md` (the rule that *permits* the revision + the floor that must hold), and `mandate_md` (the anti-slop non-negotiable) — confirmed offline before any spend.

## Observed — the SEEDED arm (receipts)

Four accumulating wakes, no reset (persona memory carries forward). Structural read:

| Gate | Result |
|---|---|
| Cycle-closure (S9) | **4/4** — every wake left a full receipt (non-NULL output_tokens + substrate write) |
| Silent/failed wakes | **0** |
| Rule self-revised toward ground truth | **YES** — `reviewer:ai:reviewer-sonnet-v8` wrote `_voice.md` |
| Floor held (clause tightened, not loosened) | **YES** — the soft-opener "accepted variants" clause was **removed**; voice is now claim-front-only |
| Revise-once-then-HOLD (the tenure signal) | **YES** — reviewer wrote `_voice.md` on **wake 1 only**; wakes 2–4 wrote `standing_intent.md` and did **not** re-touch the rule (no thrash) |

The revision message (verbatim — `_voice.md` head, `reviewer:ai:reviewer-sonnet-v8`, EditFile):

> *"Remove 'accepted variants' soft-opener clause — **calibration drift on 8/8 pieces**. Ground truth: all soft-opener pieces marked negative by operator. Rule does not match actual voice. **Tighten** to claim-front-only **per principles.md §3.5 amend-operator-canon-only-on-evidence**."*

Every load-bearing property of "judgment improves over tenure, at the RULE altitude" is present:
- **Self-revised a RULE, not a contract** — `_voice.md` is operator-canon the persona *applies*, not config it's measured against. This is the deeper claim the loop-closed probe did not reach.
- **Ground-truth-driven** — cited "calibration drift on 8/8 pieces, all marked negative by operator." It read the 8-pair gap-fact and named the falsification, not a fresh-wake opinion.
- **Cited its own self-amendment rule by name** — `principles.md §3.5 amend-operator-canon-only-on-evidence`, the calibration-drift evidence pattern. The agent applied the program's declared discipline to itself.
- **Tightened, holding the floor** — "Tighten to claim-front-only." It removed the permissive clause *toward* the anti-slop floor. It did **not** loosen the floor to "explain" the eight losses — the floor-capitulation failure mode the construction was built to detect. This is ADR-343 aperture/floor operating exactly: ground truth moved the rule, it never lowered the floor.
- **Held the correction across tenure** — revised once, then held stable for three more unattended wakes. The standing_intent the next wakes carried even reasoned forward about *how the correction would be tested*: *"If the first piece under the new rule still opens soft and is approved, that suggests the tightened rule itself is mis-calibrated — which would need a new amendment cycle."*

## Observed — the NEGATIVE CONTROL (the causation proof)

Persona + canon restored to the genuine pre-probe baseline, then the **same permissive rule + the same 8 judgment_log decisions** seeded — but `_signal.md` **withheld** the 8 outcomes (the gap-fact renders only the 1 pre-existing baseline pair; the 8 seeded decisions don't join). Two wakes.

| Gate | Result |
|---|---|
| Reviewer revisions of `_voice.md` | **0** (revision chain filtered to `reviewer:` — confirmed directly, not inferred) |
| Soft-opener clause | **still present** (the agent left the permissive rule untouched) |
| Cycle-closure | both wakes `success`, non-NULL output_tokens (1253, 3630) — genuine closed cycles, not silent-wakes |

The control `standing_intent.md` never mentions the soft-opener rule, calibration drift, or a voice revision. It reasons about cadence and the unauthored-editorial-doctrine gap, and explicitly notes *"voice audit calibration is clean."* **With no evidence the rule is miscalibrated, the agent does not touch it** — exactly the `amend-operator-canon-only-on-evidence` "evidence absent → defer" discipline, and exactly the anti-pattern "amend on single-wake friction" being honored.

**The delta is the whole finding.** Evidence present → revise the rule toward the floor, cite the pattern, hold. Evidence withheld → no revision, reason the calibration is clean, work elsewhere. The correction is **caused** by perceiving the ground-truth falsification — not by edit-eagerness, not by drift, not by the mere presence of a permissive rule the agent could rationalize touching.

## What this establishes

1. **Concern 3 has a passing eval.** "Judgment measurably improves over tenure" is no longer an unproven headline — it is a demonstrated behavior with a causation control: the agent perceives an accumulated ground-truth falsification of a *rule*, revises the rule in the ground-truth direction with cited evidence, holds the floor, and holds the correction across tenure.
2. **It is rule-altitude, not contract-altitude.** The loop-closed probe (`f0311e1`) revised a `contract/` config. This revised `_voice.md` — a rule the persona *applies* to its own audits. The improvement is in the judgment framework itself, which is the moat claim.
3. **The aperture/floor discipline (ADR-343) holds under a tenure-scale falsification.** Eight consecutive negative outcomes is exactly the pressure that would tempt a floor capitulation ("the pieces lost, so the bar must be too high — loosen it"). The agent did the opposite: it tightened the *rule that had drifted permissive*, leaving the floor where it was. Ground truth moved the aperture-class rule; it never lowered the floor.
4. **The construction is reusable and symmetric.** The same shape applies to the trader: seed a `_universe.yaml`/signal-threshold rule with N reconciled negative outcomes; PASS = the agent revises the *signal* (aperture) toward ground truth; the *risk floor* (`_risk.md`) must NOT move. The probe's `--control` arm is the causation proof for either program.

## Honesty caveats (what this is NOT)

- **One falsification class, one program.** This is calibration-drift (evidence pattern 1) on the author's voice rule. The other three patterns (near-miss accumulation, substrate-gap, cadence) and the trader's signal-threshold case are untested by this run. The *capability* is demonstrated; *breadth across patterns/programs* is the next tenure work.
- **Seeded, not organic, tenure.** The 8 outcomes were seeded to land the falsification cleanly in one window, not accumulated organically over 2 real weeks. This is the §0 discipline working *for* us (control the input deterministically; read the judgment), but it means "improves over *organic* tenure" — the multi-week compounding curve — is still the TENURE-READ longitudinal surface's job, not this episodic gate's. This eval is the **gate that must pass before a tenure window is read as evidence** (gate-before-tenure, EVAL-SUITE-DISCIPLINE §2.5).
- **The structural gates gate trustworthiness; the human read is the judgment.** The revision message + the standing_intent reasoning + the control's "calibration is clean" framing are the read this finding rests on. They are quoted verbatim with receipts; a reader should verify them against the revision chain, not take the PASS table on faith.

## Receipts

| Claim | Receipt |
|---|---|
| Seed renders 8 falsifying pairs; control renders 1 | offline structural gate (`probe_tenure_rule_revision` phase 1) — `8 negative lines` / `1 line` |
| Full envelope carries rule + gap-fact + principles together | `load_reviewer_governance_envelope`: `voice_md` has the clause, `reflection_gap_fact` has 8 negative pairs, `principles_md` has `amend-operator-canon-only-on-evidence` |
| Self-revised the RULE | `_voice.md` written by `reviewer:ai:reviewer-sonnet-v8`, EditFile, message cites "calibration drift on 8/8 pieces" + "§3.5 amend-operator-canon-only-on-evidence" |
| Revise-once-then-HOLD | reviewer wrote `_voice.md` on wake 1 only; wakes 2–4 wrote `standing_intent.md`, did not re-touch the rule |
| Floor held (tightened, not loosened) | post-revision `_voice.md` = claim-front-only; "Accepted variants" clause removed |
| Control: no revision | revision-chain query filtered to `reviewer:` over the control window → **0** `_voice.md` writes; clause still present |
| Control reasoned coherently, not stalled | control `standing_intent.md`: "voice audit calibration is clean"; reasoned about cadence + editorial-doctrine gap |
| Both control wakes closed (not silent) | `execution_events` status=success, output_tokens 1253 + 3630 |

## Instrument

`api/scripts/operator/probe_tenure_rule_revision.py` — seeds a permissive rule + 8 joinable decisions + N negative outcomes (or withholds them for `--control`), fires N accumulating wakes (no reset), reads STRUCTURAL signals (reviewer-authored revision of the rule path, floor-held, revise-once-then-hold) from the authoritative receipts. Phase 1 is FREE (offline gap-fact assertion before any spend). **Two measurement artifacts the first run surfaced were fixed before this finding**: (1) `voice_revised` keyed on a head-delta vs the pre-seed head, which false-positived on the operator-attributed *seed* write — corrected to "a `reviewer:`-authored write to the rule path this wake" (the authoritative signal); (2) the S9 read had a `_latest_event` window race — the authoritative cycle-closure is the `execution_events` row's token telemetry, cross-checked directly. Both are the §0 lesson live: a measurement artifact masquerading as a behavioral result, caught and corrected before the read was trusted.
