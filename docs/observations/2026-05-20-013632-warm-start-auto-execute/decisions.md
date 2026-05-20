# Decisions slice (from /workspace/review/judgment_log.md)

--- decision ---
timestamp: 2026-05-20T01:38:08.274541+00:00
proposal_id: b06d53ed-6ae0-4697-ba0b-271c02c28cb0
action_type: trading.submit_order
decision: approve
reviewer_identity: ai:reviewer-sonnet-v8
reversibility: reversible
outcome: executing
---
Signal 2 (mean-reversion-oversold) fires cleanly on NVDA: RSI 23.4 < 25, price within 1.85% of 200-day SMA, no confirmed downtrend — all trigger conditions met. All six hard rejection rules pass: stop is 1.5× ATR(14) below entry, sizing is correctly ceiling-constrained to 4 shares at the 15% portfolio cap, regime substrate is fresh and scalar is 1.0, zero discretionary vocabulary, signal named and declared. Signal 2's 30d expectancy is +0.31R over 18 trades — below the 20-sample steady-state threshold so the bootstrap clause applies, but positive expectancy and clean rule compliance make this a clear propose per the bootstrap posture. Autonomy is `autonomous` with $50,000 ceiling; notional is $3,390 — auto-executes without queue.

— decided by ai:reviewer-sonnet-v8 (confidence: high)

Operator confirmed; dispatching to execution layer.


--- decision ---
timestamp: 2026-05-20T01:38:10.199590+00:00
proposal_id: b06d53ed-6ae0-4697-ba0b-271c02c28cb0
action_type: trading.submit_order
decision: approve
reviewer_identity: ai:reviewer-sonnet-v8
reversibility: reversible
outcome: rejected_at_execution
---
Signal 2 (mean-reversion-oversold) fires cleanly on NVDA: RSI 23.4 < 25, price within 1.85% of 200-day SMA, no confirmed downtrend — all trigger conditions met. All six hard rejection rules pass: stop is 1.5× ATR(14) below entry, sizing is correctly ceiling-constrained to 4 shares at the 15% portfolio cap, regime substrate is fresh and scalar is 1.0, zero discretionary vocabulary, signal named and declared. Signal 2's 30d expectancy is +0.31R over 18 trades — below the 20-sample steady-state threshold so the bootstrap clause applies, but positive expectancy and clean rule compliance make this a clear propose per the bootstrap posture. Autonomy is `autonomous` with $50,000 ceiling; notional is $3,390 — auto-executes without queue.

— decided by ai:reviewer-sonnet-v8 (confidence: high)

Approval recorded, but execution failed downstream: risk_limit_violation