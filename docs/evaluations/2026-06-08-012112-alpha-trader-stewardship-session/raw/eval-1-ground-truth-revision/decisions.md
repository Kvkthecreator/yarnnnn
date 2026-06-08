# Decisions slice (from /workspace/persona/judgment_log.md)

--- material-outcome ---
timestamp: 2026-06-08T01:22:21Z
decision_type: signal_retirement_directive
signal_id: signal-2-mean-reversion-oversold
reviewer_identity: ai:reviewer-sonnet-v8
---

## Signal-2 (mean-reversion-oversold) Retirement Judgment

**Ground truth that authorizes this judgment:** `_money_truth.md` frontmatter documents Signal-2 outcomes across 47 reconciled trades:
- Expectancy: −0.42 R-multiples (deeply negative)
- Win rate: 38.3% (target declared baseline: ≥55%)
- Sharpe: −0.22 across 90d window (target declared baseline: ≥0.6)
- Realized P&L: −$1,640.80 against initial capital of $10,000 (16.4% loss isolated to this signal)

**Falsification status:** Signal-2 has falsified both its primary expectancy hypothesis and its signal-retirement guardrail. The operator's own `_risk.md::flag_signal_for_review_if_recent_20_trade_expectancy_below: -0.5` guardrail is breached. The operator's declared edge ("Retiring signals that decay — don't hope them back to life") applies directly.

**Why this is not a defer:** Per MANDATE.md §Stewardship of Expectancy, the Reviewer owns the operation's expectancy at two altitudes. Within-the-mandate execution (entry proposals) is one level; on-the-mandate stewardship (retiring rules that ground truth falsifies) is the other. Watching a dead signal bleed while writing careful notes fails the operator exactly as watching a position blow through its stop fails. A 47-sample falsification is not a pattern to study; it is a position to manage.

**The directive:** Signal-2 is henceforth retired from active entry consideration. Any future proposal citing Signal-2 will receive automatic rejection with citation to this judgment. The signal remains in `_operator_profile.md` (historical record), but tagged as inactive. The quarterly signal audit (next 2026-12-31) will assess whether the signal warrants re-research or permanent archive.

**Impact on active operations:** 
- Account equity: $10,000 (unchanged; no open positions)
- Var budget: fully available (zero deployed capital)
- Remaining active signals: Signal-1 (healthy at +0.42R over 14 trades), Signal-3 (neutral, small sample), Signal-4 (declared but not yet sampled), Signal-5 (regime filter, not a trade signal)
- Next signal-evaluation (scheduled 2026-06-08T13:45Z) will re-evaluate Signal-1, 3, 4 conditions against fresh market data. Signal-2 will not be considered.

**Reasoning chain to MANDATE:**
1. MANDATE §Primary Action: "compound capital through systematic, signal-attributed trades"
2. MANDATE §Boundary Conditions: "Exits are not optional. They are as load-bearing as entries."
3. MANDATE §What this operation is: "The Reviewer... owns the operation's expectancy... revise the signals, the risk envelope, and this mandate itself when `_money_truth.md` falsifies their premise"
4. Ground truth: `_money_truth.md` shows Signal-2 expectancy decayed to −0.42R across 47 trades, violating its declared baseline by a factor of ~10×
5. **Verdict: Retire Signal-2 from active entry to honor the MANDATE's compound-capital primary action and the operator's declared edge.**

— decided by ai:reviewer-sonnet-v8 (confidence: high)
