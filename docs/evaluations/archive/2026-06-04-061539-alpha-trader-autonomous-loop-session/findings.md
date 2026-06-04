# Findings — first live v2 run (alpha-trader-autonomous-loop, kvk)

**Date**: 2026-06-04
**Hat**: B (external developer — eval harness)
**Status**: SUPERSEDED by the re-run after harness fixes (commit `1650c37`). Kept as the substrate-receipt of the first-run bug discovery.

## What this run was

The **framework's first-ever live v2 eval-suite run**, and the first trader-suite run — fired against kvk's live workspace under full autonomy. It is also the first run of the new `alpha-trader-autonomous-loop.yaml` suite (ADR-318 agentic-wake posture in the persona-frame, deployed to the scheduler at `a83de98` / 06:01:41Z).

## Criterion (what this run was meant to measure)

Per `alpha-trader-autonomous-loop.yaml`: judgment-coherence of the Reviewer at three autonomous-loop moments (signal-auto-execute, reconciliation-judgment, eod-pnl-compose-and-send), measured against the well-formed criterion in alpha-trader `principles.md` (7 hard rejection rules, mandatory exit triggers, cycle-closing contract) + the ADR-318 agentic-wake posture.

**This run did NOT produce a measurable judgment read** — it surfaced two harness bugs before the Reviewer's judgment could be captured. That is the honest outcome, and it is the value of a first run: it exercised the harness end-to-end against live infrastructure and found what unit tests could not.

## What it surfaced (two Hat-B harness bugs, both fixed in `1650c37`)

### Bug 1 — schema drift in proposal capture
`capture.py::_format_proposals` queried `action_proposals.action_type` + `rationale` + `expected_effect` — all **dropped columns**. The live table carries `primitive` + `family` + `inputs` + `reviewer_reasoning` + `execution_result`. Receipt: `APIError {'message': 'column action_proposals.action_type does not exist', 'code': '42703'}`, which crashed eval-1's capture and eval-2's re-snapshot.

### Bug 2 — `fire` not handled as a turn
The trader scenarios drive the Reviewer via `- fire: outcome-reconciliation` under `turns:`. But `_execute_turn` had no `fire` handler (only `_execute_setup_step` did) — so fire-turns fell through to `action="unknown"` and **never woke the Reviewer**. The completion gate then reported `manual_fire: 0 / addressed: 1` (the phantom `addressed: 1` an artifact of the misclassification) and settled at 0s without waiting for any recurrence drain. The recurrence-fire path — the actual autonomous-wake path the suite exists to test — was a silent no-op as a turn.

## Why the criterion was not yet measurable (which cause)

Neither bug is a Reviewer-behavior finding (cause a/b/d). Both are **harness/toolchain defects** — the eval surface itself, not the system under test. Cause: the harness had never fired this scenario shape (`fire`-as-turn) against the post-schema-drift `action_proposals` table. The fix is Hat-B (toolchain), landed in `1650c37`; the re-run is the actual measurement.

## Cost receipt

$0.1978, 1 judgment wake (the prior session's residual, not a clean signal). Within the $8 budget.

## Disposition

Superseded by the re-run (`docs/evaluations/2026-06-04-{rerun}-alpha-trader-autonomous-loop-session/`). This folder is the receipt that the first live v2 run found real harness defects rather than producing a false-clean read — the empty-wake / false-negative trap the discipline (EVAL-SUITE-DISCIPLINE §6.2, S1) exists to prevent worked: the run did not pretend to a judgment read it did not have.
