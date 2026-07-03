# Freddie envelope refactor — Rung-1 validation (re-carved _TRIGGER_FRAMING)

> **HISTORICAL ARM (baseline rotated 2026-07-03).** No longer the diff target —
> the canonical baseline is `2026-07-03-rung4-partB-sonnet-addressed/` (declared
> as `CURRENT_BASELINE` in `probe_freddie_addressed_baseline.py`) per the
> ADR-402 Part-B one-model decision. `summary.json` re-emitted 2026-07-03 with
> the usage/cost/sentinel block (`--reextract`; raw turn JSONs unmodified).


**Date**: 2026-07-02
**Hat**: B (evaluation — expected vs observed)
**Plan**: [docs/analysis/freddie-envelope-refactor-plan-2026-07-02.md](../../analysis/freddie-envelope-refactor-plan-2026-07-02.md), Rung 1
**Baseline**: [2026-07-02-freddie-envelope-baseline/](../2026-07-02-freddie-envelope-baseline/) (main @ `482b157`, pre-re-carve)
**Change under test**: `_TRIGGER_FRAMING` re-carve — steward-first, program-neutral; addressed ~4.6k→~1.5k chars, reactive ~2.9k→~1.1k. Same 6 asks, same workspace, same model (Haiku 4.5, 20 rounds).

## Expected

Pure removal → NO behavior regression (close rate, posture), deterministic input-token cut, kernel purity (zero program nouns). Behavioral economy gains were NOT the primary Rung-1 claim (those are rungs 2–3 + model tier).

## Observed

| metric (mean over 6) | baseline | rung 1 | read |
|---|---|---|---|
| closed | 6/6 | 6/6 | no regression |
| errors | 0 | 0 | no regression |
| wall s | 33.6 | 33.4 | flat |
| rounds | 6.0 | 6.3 | flat |
| tool calls | 11.2 | 9.5 | −15% (modest; high variance N=6) |
| response chars | 495 | 550 | flat |

**Deterministic wins (attributable, not variance):**
- ~1,200 tokens removed from every addressed-turn prompt; ~450 from every reactive wake.
- Zero program nouns in kernel framing — CI-enforced from this commit (`api/test_adr383_trigger_framing_recarved.py`).
- The bare-steward incoherence (trading instructions delivered to a stewardship workspace) is structurally gone.

**Qualitative (spot-read turns 1/4/5):** steward voice intact and arguably sharper — first-person, leads with the takeaway, cites `intake-placement` by name, routes writes through the gate ("pending your approval"), and correctly draws the authority boundary on connections ("your call, not mine"). More substantive actions (EditFile/ProposeAction) replacing some pure-liturgy writes — consistent with "decide what your principles.md calls for and do it" replacing the kernel menu.

**Honest caveats:**
- The workspace mutates across runs (baseline turns left proposals/notes), so per-ask tool mixes are not strictly comparable; only structural aggregates + the deterministic deltas are load-bearing.
- Liturgy-ish writes on read-shaped asks persist (turns 1/3/6 still close with WriteFiles) — expected; that is Rung 2's target (ceremony right-sizing), not Rung 1's.
- Re-reading some pre-loaded files persists on Haiku despite the instruction — expected; that is Rung 3 (lazy envelope) / Rung 4 (model) territory.

## Verdict

**PASS — Rung 1 lands.** No regression on close/posture; deterministic token + purity wins; modest tool-economy improvement. Proceed to Rung 2.
