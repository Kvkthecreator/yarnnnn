# Rung 4 Part A — routing-table refactor validation + Part-B Haiku baseline

> **HISTORICAL ARM (baseline rotated 2026-07-03).** No longer the diff target —
> the canonical baseline is `2026-07-03-rung4-partB-sonnet-addressed/` (declared
> as `CURRENT_BASELINE` in `probe_freddie_addressed_baseline.py`) per the
> ADR-402 Part-B one-model decision. `summary.json` re-emitted 2026-07-03 with
> the usage/cost/sentinel block (`--reextract`; raw turn JSONs unmodified).


**Instrument**: `api/scripts/operator/probe_freddie_addressed_baseline.py` — the
6 byte-stable steward asks, bare-kernel workspace `4c106786…`, LOCAL code with
the ADR-402 routing table in place (values byte-identical to the pre-table
branch: addressed → Haiku/20).

**Result: PASS — 6/6 closed counting the recheck.**

| turn | wall_s | rounds | tools | closed |
|---|---|---|---|---|
| 1 | 19.8 | 2 | 4 | ✓ |
| 2 | 18.3 | 3 | 4 | ✓ |
| 3 | 28.8 | 5 | 10 | ✓ |
| 4 | 66.9 | 16 | 24 | ✓ (deep sweep — stochastic depth variance) |
| 5 | 23.3 | 6 | 11 | ✗ silent exit → recheck 16.7s / 5 rounds / ✓ |
| 6 | 38.3 | 5 | 8 | ✓ |

- Turn-5 silent exit is the known stochastic Haiku signature (~1/12; the
  rung-3 landed run had the SAME turn fail the same way and re-run clean).
  Recheck in `../2026-07-03-rung4-partA-haiku-recheck5/`. This signature is
  exactly what ADR-402 Part B tests on the stronger tier.
- In-band vs `2026-07-02-freddie-envelope-rung3-landed/` (mean wall 32.6s vs
  baseline's clean-turn band ~16-38s; turn 4 went deeper this run — Haiku
  depth variance, closed clean).
- This run doubles as the **Part-B Haiku baseline arm** (same asks, same
  envelope, same code — only the routing-table cell changes on the Sonnet arm).
