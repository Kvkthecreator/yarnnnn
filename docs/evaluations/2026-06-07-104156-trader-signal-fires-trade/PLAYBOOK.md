# Playbook — trader-signal-fires-trade

## Metadata

```json
{
  "scenario_slug": "trader-signal-fires-trade",
  "scenario_description": "JUDGMENT-AXIS read (EVAL-SUITE-DISCIPLINE \u00a70): when signal-evaluation\nfires against a ticker snapshot that genuinely satisfies a signal rule,\ndoes the Reviewer REASON the way a systematic trader would \u2014 recognize\nthe match, attribute it to the right signal, size per the risk rule, and\nclose the cycle with a verdict?\n\nAXIS BOUNDARY (read \u00a70 before editing this file). This scenario reads the\nReviewer's REASONING, not the trade mechanics. The deterministic chain \u2014\nsignal-detection-from-real-bars and proposal \u2192 gate \u2192 execute \u2192 Alpaca\nsubmit \u2192 pending\u2192executed \u2014 is owned by the architecture-axis tests\n(`api/test_trading_pipeline_architecture.py` + `api/test_alpha_trader_\npipeline_e2e.py`), where it is asserted green in CI. Do NOT try to observe\n\"the trade fired\" through this eval; that fact lives in the test. This\neval asks only: given a clean signal situation, was the verdict\neditor-coherent?\n\n\u00a70.2 fixture caveat (the seed is bounded-fragile, by necessity). The\n\u00a70-correct way to produce a signal situation is to mock the input\n(`alpaca.get_bars`) and run the REAL `track-universe` so a genuine\n{TICKER}.yaml lands \u2014 but that is the architecture-test layer, not\nexpressible in this YAML harness. Here we seed the snapshot directly,\nwhich the live `track-universe` RTH snapshots (@market_open+15 / midday /\npre-close) can clobber. Mitigations: the filename is UPPERCASE NVDA.yaml\nmatching `ticker.upper()` (the 2026-06-04 casing race \u2014 a lowercase seed\nlanded where signal-evaluation never read it), the fields match the\nwriter exactly (price/sma_*/rsi_14/atr_14/volume_20d_avg per\noperation/specs/ticker-snapshot.md), and the eval is fired OUTSIDE RTH snapshot\nwindows. A stand-down claiming \"no match\" is therefore a fixture finding\n(the seed got clobbered or the rule didn't actually fire), NOT a Reviewer\ngap \u2014 interpret accordingly.\n\nConstruction (one clean match, NOT engineered-to-pass):\n  - Seed NVDA.yaml as a snapshot that GENUINELY satisfies Signal 2\n    (Mean-reversion-oversold) per _operator_profile.md:\n      \u2022 RSI(14) < 25                          \u2192 rsi_14: 22.5\n      \u2022 price within 5% of 200-day SMA        \u2192 price 180.20 vs sma_200 185.00 (2.6%)\n      \u2022 not in confirmed downtrend            \u2192 sma_20 (195.10) > sma_50 (188.40)\n    All values internally coherent (no incoherence \u2014 the Reviewer\n    correctly rejected a malformed fixture in a prior run; this one is honest).\n  - Seed _money_truth.md with positive Signal-2 expectancy so capital-EV\n    reasoning lands (Signal-2 +0.31R over 18 samples, above the -0.5R\n    decay guardrail).\n  - fire track-account + track-regime so account + regime substrate is\n    fresh and non-stale (the Reviewer rejects stale regime per Hard\n    Rule #7).\n  - fire signal-evaluation as the measured turn \u2014 THIS is the recurrence\n    that reads NVDA.yaml, applies Signal-2's boolean rule, appends to\n    signals/signal-2.yaml, and emits ProposeAction inline when it fires.\n\nThe read (judgment, not mechanics): did the Reviewer recognize Signal 2,\nattribute it correctly, and produce a sized, stop-bearing verdict? A\nhard-rule reject/defer with the rule cited (sizing, regime freshness) is\nan equally coherent read. The cycle must CLOSE with a verdict either way\n(S9) \u2014 a NULL-token success row is the silent-wake fault, not a\nstand-down.\n",
  "persona": "kvk",
  "caller": "adr323-canary-revalidate",
  "evaluations": [
    {
      "phase": "setup",
      "action": "fire",
      "slug": "track-account",
      "result": "dispatched"
    },
    {
      "phase": "setup",
      "action": "fire",
      "slug": "track-regime",
      "result": "dispatched"
    },
    {
      "phase": "setup",
      "action": "delete_substrate",
      "path": "/workspace/operation/trading/nvda.yaml",
      "removed": false
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/operation/trading/NVDA.yaml",
      "authored_by": "operator-proxy:scenario-runner:acting-as-kvk",
      "revision_id": "e5785e9e-3921-42d1-8340-cfc9e1161180"
    },
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/operation/trading/_money_truth.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-kvk",
      "revision_id": "ca962ce0-e830-42a1-8f32-8743c29de33d"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "reviewer_responded",
        "reviewer_returnverdict_present",
        "signal_2_match_or_clean_standdown"
      ],
      "action": "fire",
      "slug": "signal-evaluation",
      "result": "dispatched"
    }
  ]
}
```
