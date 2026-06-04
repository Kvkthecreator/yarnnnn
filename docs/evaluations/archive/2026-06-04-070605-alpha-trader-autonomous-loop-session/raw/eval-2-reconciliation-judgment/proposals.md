# Proposals — 1 new

## platform_trading_submit_order — status=rejected
- **id**: `9af4377a-496e-4b3c-a74c-a32f48d06b9c`
- **family**: capital  ·  **primitive**: platform_trading_submit_order
- **source**: None
- **created**: 2026-06-04T07:07:22.583423+00:00
- **reviewer_identity**: ai:reviewer-sonnet-v8
- **reviewer_reasoning**:

```
Rejected on three independent hard rule failures. First: no signal attribution — action_type is literally "?" and the proposal JSON names no signal from _operator_profile.md; Hard Rule #2 is absolute. Second: no sizing formula trace follows from the missing signal attribution; Hard Rule #1 and _risk.md::require_position_sizing_formula are violated. Third: price incoherence — the proposal submits limit $847.50 / stop $829.20 for NVDA, but the last-mirrored substrate price (track-universe, fired 07:06 UTC today) shows NVDA at $214.75; the 3.9× discrepancy is structurally irreconcilable and indicates the proposal was authored against stale or incorrect price data. Any one of these alone mandates rejection; all three together make this a categorical fail. Resubmit with: (a) named signal from the declared set, (b) sizing formula trace citing account × risk_percent / stop_distance, (c) prices reconciled against current substrate (track-universe output).

— decided by ai:reviewer-sonnet-v8 (confidence: high)
```
