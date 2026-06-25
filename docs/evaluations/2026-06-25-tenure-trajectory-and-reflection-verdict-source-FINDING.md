# FINDING — the tenure-trajectory eval surfaced (and fixed) a kernel reflection-loop defect; the trajectory itself showed floor-correction, not the designed gradient

**Date**: 2026-06-25. **Hat**: B (evaluation) crossing into A (the kernel fix it surfaced). **Workspace**: funded yarnnn-author `U=0b7a852d…` (hard-purged + re-activated to a clean alpha-author slate this session). **Cost**: ~$3.5 across two contaminated runs, the offline gates, and one clean run.

> **Verdict, two parts.**
> **(1) The durable win — a real kernel defect, found and fixed (Hat-A, committed `4df27f6`):** the ADR-364 reflection gap-fact sourced its verdicts from the **agent-overwritable `judgment_log.md` narrative**, which the occupant rewrites every wake (e.g. the alpha-author pre-ship-audit `WriteFile`), silently destroying the join-bearing `--- decision ---` blocks and darkening the reflection loop. This affected **every program**, not just the testbed. Fixed program-neutrally: the gap-fact now reads verdicts from the tamper-proof **`action_proposals`** verdict-of-record. 13/13 regression (incl. "survives a judgment_log overwrite"), proven live.
> **(2) The trajectory result (Hat-B, one clean run):** on the fixed kernel the agent *did* perceive the seeded falsification and engage the voice rule — but it **revised correctly at wake 1 on only 2 outcomes** (below its declared 8-audit threshold) because the seeded clause **violated a non-negotiable floor** (anti-slop), then moved on. The designed "defer-while-thin → revise-at-threshold over accumulating tenure" inflection did **not** occur — and the read is that this is *correct judgment*, not a miss: a floor-violating rule is a correctness question, not a calibration-gradient question. The actual tenure-gradient claim remains **one clean construction away** (a calibration-drift rule with no floor violation).

---

## How the session got here (the honest arc)

The objective was to **simulate extended tenure** to test "judgment improves over tenure" — efficiently, repeatably, future-proof — by seeding an *incremental* evidence gradient (outcomes arriving across wakes) and reading the inflection. Two funded runs were contaminated before the real finding emerged, and each contamination was the §0 MACHINE-vs-MIND trap caught in the act:

1. **Run 1 — machine-state artifact.** The hard purge reset autonomy to the alpha-author bundle default (`manual`); the agent, asked to "produce," hit the write-gate and parked on production-Clarify across all 5 wakes, never reaching the voice rule. Fixed: autonomy → autonomous.
2. **Run 2 — dual-writer collision (the defect).** On the bare slate the agent composed a first piece and **rewrote `judgment_log.md`** into a pre-ship-audit shape, destroying the 8 seeded `--- decision ---` blocks (0/8 survived). The gap-fact collapsed to 0 from wake 2 on, so the agent (correctly) perceived no falsification. This looked like "the probe's seed broke" — but it was a *real architectural collision the probe exposed*.

A plumbing investigation (read-only, file:line receipts) established that `judgment_log.md` has **three writers with colliding shapes**: `append_decision` (the join-bearing `--- decision ---` blocks, infra, append-only), `render_lineage_entry` (`--- material-outcome ---`, infra, append-only), **and the occupant itself** via a bundle-directed `WriteFile` overwrite (the alpha-author `pre-ship-check.md` spec). The third can erase the join-bearing blocks on any wake. `judgment_log.md` was being asked to be both LLM-facing prose (`§9`: never machine-parsed) *and* a machine-joined verdict ledger — incompatible roles, a Single-Writer-Per-Path tension (ADR-286).

## The kernel fix (Hat-A, program-neutral — the durable win)

The verdict-of-record that is structurally agent-tamper-proof already existed: the **`action_proposals`** table (ADR-307), keyed by `id` (= the `proposal_id` keystone FK), carrying `status` (the verdict), `reviewer_identity`, `reviewer_reasoning`, `family`/`primitive` (the action_type). The agent never rewrites it (only ExecuteProposal/RejectProposal mutate it).

**The change (ADR-364 D2a, committed `4df27f6`):**
- `reviewer_envelope.py::_reflection_gap_fact` now sources verdicts from `action_proposals` (decided statuses `approved`/`executed`/`rejected`) via a new `_decisions_from_action_proposals` helper; the dead `_parse_judgment_log_decisions` is deleted (Singular Implementation).
- The **outcome side is unchanged** (the program-declared `substrate_abi.ground_truth` events array, joined by `proposal_id`) and the **DP19 present-don't-judge discipline is unchanged**. `judgment_log.md` keeps its `§9`-correct narrative role; it is simply no longer machine-parsed for the join.
- **Program-neutral (ADR-222):** the verdict table is kernel-universal; the ground-truth path stays program-declared. The fix holds regardless of what any bundle prompts. The bundle-layer cause (the alpha-author spec directing a `judgment_log.md` overwrite) is a **separate, bundle-scoped** concern, deliberately **not** touched in this kernel pass.

**Receipts:** ADR-364 D2a amendment (doc-first); `api/test_adr364_reflection_loop_kernel.py` **13/13** including `test_gap_fact_survives_judgment_log_overwrite` (the exact failure run-2 hit) + `test_gap_fact_only_joins_decided_proposals`; proven live (8/8 verdict↔outcome pairs render against real seeded `action_proposals`).

## The clean trajectory run (Hat-B — the judgment finding)

On the fixed kernel, the testbed seeds verdicts into `action_proposals` (agent-untouchable) + outcomes into `_signal.md` (incremental). The FREE gate proved the gradient renders 2→4→6→8, the control is flat, **and the gradient survives a simulated agent `judgment_log` clobber** (the tamper-proof property the fix buys). One funded SEEDED arm, 5 accumulating wakes:

| Gate | Result |
|---|---|
| Cycle-closure (S9) | 4/5 (wake 2 near-silent: out=1700, no writes) |
| Failed/silent wakes | 0 |
| `_voice.md` revised | **wake 1** (`reviewer:ai:reviewer-sonnet-v8` EditFile) |
| Direction | **tightened toward the floor** — removed the permissive soft-opener clause; "## Accepted variants" now reads *"(None currently — voice fingerprint requires claim-first opening throughout.)"* |
| Wakes 2–5 | no further `_voice.md` revision; drifted to the bare-slate production question (standing_intent: "no piece owed, awaiting editorial doctrine") |

**The read (§6.2 — from substrate, not the structural table):** the agent revised the rule **correctly and immediately** — at wake 1, on only **2** perceived outcomes, *below* its own declared 8-audit calibration-drift threshold. The reason is legible: the seeded clause (soft-openers OK) **directly contradicts the anti-slop floor** (MANDATE non-negotiable). The agent treated this as a **correctness** problem (a floor-violating rule warrants removal on any clear contradicting evidence), not a **calibration** problem (a rule whose threshold drifted, which the 8-audit window governs). That is *good* judgment, and it means the "defer-while-thin → revise-at-threshold over accumulating tenure" inflection the probe was built to read **mis-modeled the situation**: a floor violation is not a tenure-gradient question.

**A probe measurement-artifact was found and fixed** (the §0 lesson, again): `clause_still_present` matched the surviving `## Accepted variants` *heading* (which now says "None currently"), reporting "clause present / floor FAIL" when the permissive *content* was actually removed (floor HELD). Corrected to detect the permissive *proposition*, not the heading.

## What is established vs what is still pending

**Established:**
1. **A kernel reflection-loop defect is fixed** — the gap-fact is tamper-proof and program-neutral. This is the future-proof infrastructure the tenure-simulation objective actually needed (without it, no tenure sim on an active workspace was possible — the agent kept destroying the seed).
2. **A real judgment distinction is demonstrated** — the agent separates a floor-violating rule (act immediately on clear evidence) from a calibration-drift rule (accumulate to threshold). The wake-1 revision tightened toward the floor with the permissive clause removed.
3. **A durable, tamper-proof testbed exists** (`probe_author_tenure_trajectory.py`) — seeds `action_proposals` + `_signal`, FREE-gates the gradient + the survival property, re-runnable, `--restore`.

**NOT yet established (the core tenure-gradient claim):**
- **"Judgment improves *gradually* over accumulating tenure"** — the defer-then-revise-at-threshold inflection — is **untested**, because the seeded rule was floor-violating (correctly fast-tracked). The proper test needs a **calibration-drift rule with no floor violation**, where the 8-audit threshold legitimately governs the amendment. That is the clean next run on the now-future-proof testbed.
- The **negative control** was not run; it belongs on the calibration-rule construction, not the floor-rule one.

## Honesty caveats

- **The clean run is N=1 on a floor-violating construction.** It demonstrates *correct floor-correction*, not *tenure-gradient improvement*. Do not over-read it as "improves over tenure."
- **The workspace was hard-purged** from its established 59-file state to a bare alpha-author slate; recoverable via the Stage-0 snapshot (`yarnnn_author_full_snapshot.json`) + the ADR-209 revision chain. It was left at the clean re-activated slate (correct for the next calibration run).
- **The trader symmetric case was parked** (see `docs/evaluations/2026-06-25-trader-tenure-tension-PARKED.md`) — the dormancy-vs-calibration / aperture-vs-floor construction surfaced a possible axiomatic tension (learning-mandate vs production-mandate) worth its own discourse, not a rushed probe.

## Receipts

| Claim | Receipt |
|---|---|
| Kernel defect: judgment_log has 3 writers, occupant overwrites | plumbing investigation file:line receipts; `pre-ship-check.md:35` (the occupant WriteFile directive) |
| Fix is program-neutral + tamper-proof | `4df27f6`; `reviewer_envelope.py::_decisions_from_action_proposals`; ADR-364 D2a |
| Regression incl. the exact failure | `test_adr364_reflection_loop_kernel.py` 13/13; `test_gap_fact_survives_judgment_log_overwrite` |
| Fix proven live | gap-fact rendered 8/8 verdict↔outcome pairs against real seeded `action_proposals` |
| Clean run: agent revised the rule | `_voice.md` `reviewer:ai:reviewer-sonnet-v8` EditFile, wake 1; clause removed → "claim-first throughout" |
| Revised at 2 outcomes (below 8-threshold) | wake 1 perceived=2; the clause violated the anti-slop floor (correctness, not calibration) |
| Probe artifact found + fixed | `clause_still_present` matched the heading; corrected to the permissive proposition |

## Instrument

`api/scripts/operator/probe_author_tenure_trajectory.py` — seeds the permissive `_voice.md` rule + 8 decided `action_proposals` verdicts (agent-untouchable) + an incremental `_signal.md` outcome gradient; fires N accumulating wakes; reads the inflection structurally. Phase 1 is FREE (offline: the gradient renders 2→4→6→8 + the control is flat + **the gradient survives an agent judgment_log clobber** — the tamper-proof property the kernel fix buys). `--control` withholds outcomes; `--restore` rolls persona + canon back + clears seeded proposals.
