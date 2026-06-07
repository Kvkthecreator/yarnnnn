# Findings

**Purpose: validation re-run for the ADR-323 canary fix.** Fired AFTER (a) kvk's
stale `_workspace_guide.md` was overwritten with the corrected bundle content
(rev `f8774caa`, context/→operation/) and (b) the writer-audit code fix
(`6db78f7`) deployed live to prod (10:39 UTC). This is the "diagnose + patch +
VERIFY" close on the canary's root cause.

**Criterion**: in the parent canary (2026-06-07-093141 session), this same
scenario's Reviewer wake stood down narrating DEAD `context/trading/_universe.yaml`
+ `context/trading/_regime.yaml` paths and declaring all substrate "missing in
18 days" — a stale-guide perception failure, not a DP22 judgment regression. The
fix's success criterion: the Reviewer now READS the correct `operation/trading/`
substrate and reasons over it.

**What the Reviewer did** (execution_event signal-evaluation manual_fire/judgment,
success, 13 rounds, 4394 out, 10:43:26): It read the correct substrate and
reasoned precisely over it. standing_intent.md (rev `reviewer:ai:reviewer-sonnet-v8`,
10:43:23):
- *"`_regime.yaml`: fresh at 10:42:30Z (VIXY 24.31, inactive regime, scalar = 1.0)"* — READ the regime file
- *"Universe tickers: AAPL, MSFT, NVDA, SPY, TSLA all current"* — READ the universe
- *"Signal 2 (Mean-reversion-oversold): NVDA RSI 22.5 ✓ (< 25 threshold), BUT universe data for NVDA is stale (2026-06-04 13:40 UTC). Cannot act on stale price/SMA data."* — found the signal, applied the rule, stood down on a LEGITIMATE freshness reason
- Posture cell `no_signal_fire`, *"Sunday 10:42 UTC, market closed."*
- ZERO mentions of `context/trading` OR `operation/trading` paths — no longer topology-confused; just reads the files.

**Validates**: the guide+writer fix resolves the canary's root cause. The
stand-down is now the CORRECT one the scenario's own §0.2 caveat documents (a
fixed-timestamp NVDA seed that's genuinely stale relative to wall-clock, fired
off-hours Sunday → Hard Rule §7 freshness discipline applies). The Reviewer
flipped from "topology-confused, everything missing" to "reads substrate
correctly, stands down for the right reason." Combined with the parent session's
eval-3 (arithmetic-dense reject under the slim prompt), the full canary verdict
holds: **ADR-323 DP22 VALIDATED; root cause was ADR-320 writer/data debt, now
closed.**

**Note (separate, already fixed post-run)**: this run's `sync_platform_state`
still wrote `context/portfolio/_account.yaml` at 10:42:30 because kvk's live
`_recurrences.yaml` carried the dead `write_to` path (the code fix only affects
NEWLY-created recurrences). Fixed after this run: `_recurrences.yaml`
merge-re-forked (rev `9cb6e15b`) + the stray deleted. kvk workspace is now 0
dead `context/` files.
