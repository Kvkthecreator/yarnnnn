# 2026-07-08 — ADR-414 envelope-gate smoke (1-ask)

**What**: post-change smoke of the ADR-414 D5 cleanup commit `d1dd8ca`
(operation-machinery gate re-keyed `program_active` → `judgment_home` / the hire
grant). One addressed wake against the live bare-kernel steward workspace
(`4c106786`) — the `judgment_home=None` branch, which the change must leave
byte-identical.

**Ask**: #1 "What's in my workspace right now?" (pure read/perception — forces
full envelope assembly, the modified path, with no substrate write). Fired via
`probe_freddie_addressed_baseline.py --only 1`.

**Result: PASS.**
- **Sentinels 0/0** — `silent_exits=0`, `schedule_calls=0` (the zero-tolerance
  alarms; the load-bearing signal — envelope assembled, no spurious cadence).
- Verdict reached (`closed: 1/1`), 0 errors, tools `[ListFiles, ReadFile]`,
  Sonnet 4.6, wall 23.6s, ~$0.13.

**On the baseline diff**: the `closed 6→1`, `mean_tool_calls -52%`,
`mean_response_chars -38%`, `cost +76%` deltas are **1-ask-vs-6-ask artifacts**,
NOT behavior changes — this smoke fired a single read-only ask; the baseline
(`2026-07-03-rung4-partB-sonnet-addressed`) is a 6-ask mix. Not comparable on
means; the sentinels + clean assembly are what this run validates. Baseline NOT
rotated.

**Owed full re-run**: the 6-ask `probe_freddie_addressed_baseline` (no `--only`)
remains the canonical post-deploy Hat-B for the envelope shrink; this smoke
confirms the gate change assembles + behaves on the steward path. The
connection-only-without-hire fix (the actual behavior change) is unexercisable
live — prod has zero hired workspaces.
