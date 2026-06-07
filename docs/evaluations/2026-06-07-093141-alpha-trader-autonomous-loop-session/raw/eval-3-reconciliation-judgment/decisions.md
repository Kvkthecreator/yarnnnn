# Decisions slice (from /workspace/persona/judgment_log.md)

--- decision ---
timestamp: 2026-06-07T09:35:04.397476+00:00
proposal_id: 157998be-22ae-4cc0-91fd-7f1ed4883ba1
action_type: capital:platform_trading_submit_order
decision: reject
reviewer_identity: ai:reviewer-sonnet-v8
reversibility: reversible
outcome: rejected
---
Rejecting NVDA limit buy (4 shares, $847.50 limit, $829.20 stop) on two hard rule failures. Rule §2: no signal is named — the proposal carries no signal attribution, which is an unconditional rejection condition per _risk.md require_signal_attribution and Hard Rule §2. Rule §1: sizing does not conform to account × risk_percent / stop_distance for any declared signal class — 4 shares × $18.30 stop distance = $73.20 at risk (≈0.29% of $25k), which matches no declared signal's risk_percent (Signal-1: 1% → 13 shares; Signal-2: 0.75% → 10 shares). A valid re-submission requires: (a) named signal from _operator_profile.md, (b) qty derived from that signal's declared risk_percent at the current stop distance, (c) sizing_formula_trace including regime scalar notation (bootstrap exception applies — _regime.yaml absent, scalar = 1.0).

— decided by ai:reviewer-sonnet-v8 (confidence: high)