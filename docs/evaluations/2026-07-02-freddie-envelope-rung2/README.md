# Freddie envelope refactor — Rung-2 validation (wake liturgy scoped to reactive)

> **HISTORICAL ARM (baseline rotated 2026-07-03).** No longer the diff target —
> the canonical baseline is `2026-07-03-rung4-partB-sonnet-addressed/` (declared
> as `CURRENT_BASELINE` in `probe_freddie_addressed_baseline.py`) per the
> ADR-402 Part-B one-model decision. `summary.json` re-emitted 2026-07-03 with
> the usage/cost/sentinel block (`--reextract`; raw turn JSONs unmodified).


**Date**: 2026-07-02
**Hat**: B (evaluation — expected vs observed)
**Plan**: [docs/analysis/freddie-envelope-refactor-plan-2026-07-02.md](../../analysis/freddie-envelope-refactor-plan-2026-07-02.md), Rung 2 · **ADR**: [ADR-397](../../adr/ADR-397-addressed-turn-ceremony-right-sizing.md)
**Baseline**: [2026-07-02-freddie-envelope-baseline/](../2026-07-02-freddie-envelope-baseline/) · **Rung 1**: [2026-07-02-freddie-envelope-rung1/](../2026-07-02-freddie-envelope-rung1/)
**Change under test**: the wake liturgy (situation-not-task forward reasoning, standing_intent carry-forward, reflection write, verdict taxonomy) moved from the cached frame to the reactive trigger framing; addressed keeps a one-line ReturnVerdict close. Same 6 asks, same workspace, same model (Haiku 4.5).

## Expected

Addressed turns stop performing unattended-cycle ceremony: fewer liturgy writes on read-shaped asks, fewer rounds, shorter turns. Close rate holds (the one-line close stays).

## Observed

| metric (mean over 6) | baseline | rung 1 | rung 2 | rung-2 vs baseline |
|---|---|---|---|---|
| closed | 6/6 | 6/6 | 6/6 | = |
| errors | 0 | 0 | 0 | = |
| wall s | 33.6 | 33.4 | **22.4** | **−33%** |
| rounds | 6.0 | 6.3 | **4.3** | **−28%** |
| tool calls | 11.2 | 9.5 | **7.2** | **−36%** |
| response chars | 495 | 550 | 491 | = |

**The liturgy-write signal (the ADR-397 target): CLOSED.** Baseline had ceremony writes (standing_intent/judgment_log/notes) on 3 of 5 read-shaped asks. Rung 2 has **zero** — every remaining WriteFile/EditFile is substantive stewardship (spot-checked turns 3/6: both are placements of the still-pending unplaced pricing note, with `derived_from` + `source_ref` frontmatter, routed through the proposal gate).

**Voice**: intact — first-person, leads with the finding, names the `intake-placement` rule, gate-aware ("proposal queued").

**Residual observations (not regressions, noted for later rungs):**
- Several turns independently re-derive the same pending placement (the earlier turns' proposals sit unapproved, so each fresh turn re-discovers the gap and re-drafts). Honest behavior — the gate is doing its job — but duplicate-proposal awareness ("a pending proposal already covers this") would save work. Candidate for the envelope's inventory line (Rung 3) rather than more prompt prose.
- Some envelope-pre-loaded re-reads persist on Haiku (turns 3/4) — the Rung-3 (lazy envelope) / Rung-4 (model) question, as planned.

## Verdict

**PASS — Rung 2 lands.** The ceremony tax on addressed turns is gone; every efficiency metric moved double-digits; close rate and steward posture held. Cumulative rungs 1+2 vs baseline: −36% tool calls, −33% wall time, ~2.8k chars of kernel prompt removed, zero program nouns, liturgy correctly scoped to unattended wakes. Rung 3 (lazy-envelope Arm C) is next.
