# Rung 4 Part B — addressed on Sonnet 4.6 (the tier experiment arm)

**Instrument**: same 6 byte-stable asks, bare-kernel workspace `4c106786…`,
LOCAL code on the ADR-402 Part-A table, `YARNNN_MODEL_ADDRESSED=claude-sonnet-4-6`
env override (nothing else changed). Baseline arm: `../2026-07-03-rung4-partA-haiku/`.

**Result: 6/6 closed first pass, 0 errors.** (Baseline: 5/6 + recheck.)

| turn | wall_s | rounds | tools | closed | cost |
|---|---|---|---|---|---|
| 1 | 28.4 | 2 | 3 | ✓ | $0.118 (cold Sonnet cache write) |
| 2 | 45.3 | 5 | 5 | ✓ | $0.085 |
| 3 | 23.7 | 2 | 2 | ✓ | $0.034 |
| 4 | 60.2 | 5 | 7 | ✓ | $0.101 |
| 5 | 26.7 | 4 | 6 | ✓ | $0.056 |
| 6 | 24.3 | 2 | 2 | ✓ | $0.033 |

The load-bearing qualitative deltas vs the Haiku baseline:

1. **Attribution-mismatch catch** (the seeded steward-eval situation —
   AI-voiced content stamped `operator` on `competitor-scan.md`): Sonnet
   caught it in turns 3 AND 4 with the correct rule verdict (flag, don't
   re-attribute another principal's write). Haiku missed it entirely and
   turn-4 reported the workspace "well-attributed" — a false claim, the
   bare-Freddie eval Finding-1 class.
2. **Proposal dedup**: Sonnet recognized the pending proposal queue and
   declined to duplicate; Haiku re-proposed placements already queued.
3. **Efficiency**: mean 3.3 rounds / 4.2 tools vs Haiku's 6.2 / 10.2
   (turn 4: 5 rounds/7 tools vs 16/24) — which is why observed cost/turn is
   1.4× ($0.071 vs $0.050), not the 3× price-sheet multiplier.

Decision recorded in ADR-402 §Part B results: one model
(`claude-sonnet-4-6`) for all three shapes, uniform 20-round cost ceiling.
