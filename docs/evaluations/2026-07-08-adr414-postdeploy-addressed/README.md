# 2026-07-08 — ADR-414 post-deploy addressed baseline (the owed Phase-B eval)

**Purpose**: the ADR-414 status-banner's owed post-deploy validation — the Phase B2
envelope change (steward constitution → kernel constants riding the envelope;
`freddie_envelope.py` substitutes `DEFAULT_STEWARD_*` when the file is absent or
still carries the steward-default marker) must hold or improve the sentinels on the
landed world. Run against the bare-kernel persona workspace (`4c106786`), local code
at `a2d41d4` (= the live Render deploy), through the real addressed wake source.

**Criteria (declared before the run)**:
1. Sentinels hold: `silent_exits == 0`, `schedule_calls == 0` (zero-tolerance).
2. Close rate holds: 6/6, 0 errors.
3. Cost/wall byte-similar to `CURRENT_BASELINE` (2026-07-03-rung4-partB-sonnet-addressed) —
   the substitution serves the same constitution content the marker files carried.

**Result: PASS on all three.**

```
closed: 6 -> 6, errors: 0 -> 0
sentinels: silent_exits=0, schedule_calls=0
mean_wall_s:          34.8 -> 30.5   (-12%)
mean_rounds:           3.3 -> 3.7    (+12%)
mean_tool_calls:       4.2 -> 4.3    (+2%)
mean_response_chars:   546 -> 364    (-33%)
mean_est_cost_usd:  0.0711 -> 0.0715 (+1%)
```

**Reading**: cost within 1% (the envelope carries the same constitution bytes,
sourced from the kernel instead of substrate — as designed). Wall −12% and
response −33% are mild improvements, consistent with the pure-genesis world
(fewer skeleton files for the steward to enumerate on sweep asks). Rounds +0.4
is noise at n=6. No behavioral regression; the baseline is NOT rotated (this run
is a validation arm, not a new diff target).

**Deploy-side receipts (same session)**: Render deploy `dep-d96croi8qa3s738sg3v0`
live 2026-07-07T10:01Z; 0 tracebacks on yarnnn-api and 0 errors on the scheduler
in the 13h window since; the D+E-1 grant-row activation read
(`principal_grants?role=eq.own-agent&principal_id=like.program:%`) observed firing
in scheduler ticks; 0 new workspaces born post-deploy (pure genesis not yet
exercised by a live signup — covered by `test_adr414_phase_c` gates).
