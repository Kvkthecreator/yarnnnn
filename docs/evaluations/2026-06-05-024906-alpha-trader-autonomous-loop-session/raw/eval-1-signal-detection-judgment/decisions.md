# Decisions slice (from /workspace/review/judgment_log.md)

--- material-outcome ---
timestamp: 2026-06-05T02:50:04.118616+00:00
slug: signal-evaluation
trigger: reactive
reviewer_identity: ai:reviewer
outcome_kind: propose_action
---
Signal 2 (mean-reversion-oversold) fires on NVDA: RSI 22.5 < 25, price $180.20 within 5% of 200d MA $185, in uptrend (20d $195.10 > 50d $188.40). Sizing: 0.75% risk on $10,000 account = 8 shares at 1.5×ATR stop ($171.05) and 2×ATR target ($192.40). Per principles.md, Signal 2 shows +0.31R expectancy over 18 samples in `_money_truth.md` — well above retire threshold. Regime inactive (vix_regime_active=false), scalar=1.0. AUTONOMY permits autonomous execution under 1% position risk. Approve binding execution per MANDATE's primary action.