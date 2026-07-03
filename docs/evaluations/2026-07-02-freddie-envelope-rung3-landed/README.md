# ADR-400 landing validation — the thin envelope as production

> **HISTORICAL ARM (baseline rotated 2026-07-03).** No longer the diff target —
> the canonical baseline is `2026-07-03-rung4-partB-sonnet-addressed/` (declared
> as `CURRENT_BASELINE` in `probe_freddie_addressed_baseline.py`) per the
> ADR-402 Part-B one-model decision. `summary.json` re-emitted 2026-07-03 with
> the usage/cost/sentinel block (`--reextract`; raw turn JSONs unmodified).
>
> **Renumber note (2026-07-03)**: the envelope-collapse ADR was renumbered
> **ADR-400 → ADR-403** (number collision with the Files-surface ADR-400;
> commit `34bc995`). This dated receipt keeps its original "ADR-400" prose as
> historical artifact; the live file is
> [ADR-403-the-envelope-collapse-lands.md](../../adr/ADR-403-the-envelope-collapse-lands.md),
> whose banner explains.


**Date**: 2026-07-02 · **Hat**: B · **ADR**: [ADR-403 (né 400)](../../adr/ADR-403-the-envelope-collapse-lands.md)
**Path under test**: the LANDED production builder (`_governance_prefix` [cache-marked] + `_volatile_suffix`), no env toggle — the fat envelope, framing, and Arm toggle are deleted. Same 6 byte-stable asks + the bare-steward reactive wake, Haiku.

## Results

**Addressed**: turns 2/3/4/6 clean on the first pass (19–35s, 2–5 rounds, 5–13 tools, proper steward reports). Two first-pass anomalies, both resolved on re-run:
- **Turn 1 `lock_wait_timeout` (422s, 0 rounds) — an artifact, not the envelope**: the immediately-prior crashed run (the `_os_probe` leftover-import bug this validation caught pre-commit) died holding the wake-queue single-in-flight lane; turn 1 waited it out. Re-run post-clear: 18.2s / 5 tools / closed (`turn-1-recheck.json`).
- **Turn 5 silent exit (3 rounds, 7 tools, no verdict)** — did not reproduce on re-run (19.8s / 7 tools / closed, `turn-5-recheck.json`); consistent with the known Haiku stochastic base rate, not a landed-shape regression (Arm-B v2 was 6/6 on the same shape).

**Reactive** (bare-steward `--live`, landed path): ledger `success`, 10 rounds; three-halves heuristic HALF-1 + HALF-3 PASS; HALF-2's `floor` flag is a substring false positive — "The **stewardship floor**" is the steward's own principles.md vocabulary (ADR-343's kernel-derived concept), not capital judgment. Trace: `bare-steward-live-wake-landed.json`.

## Also validated by this run

- The pending-proposals snapshot line renders (decided-and-queued work named to the agent).
- The ADR-390 commons leads (verbatim, the validated attribution catch-fix) render in the volatile suffix.
- Gates: envelope set green per-file (adr301/275/274/284/302/314/323/383/reviewer-contract/perception/adr364/adr289). Pre-existing failures NOT touched: `test_attribution_fact::test_dedupes_to_current_head_per_path`, `test_adr336::test_alpha_author_bundle_declares_the_watch` (both fail on pre-change code too — receipts in session).

## Watch item

First live alpha-trader proposal wake post-deploy (the dogfood lane — off-critical-path per ADR-380; the one trigger shape not probed on this exact landed build).
