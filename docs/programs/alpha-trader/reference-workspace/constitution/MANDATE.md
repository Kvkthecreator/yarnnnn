# Mandate — alpha-trader

> **Operator**: author this file. Keep what serves you, delete what doesn't, and add what's missing for your edge. The platform reads this as the gate for task creation (per ADR-207).

## Primary Action

Submit equity and option orders to the broker, sized per the declared risk rule, attributed to a named signal.

> **Schema discipline (ADR-266 D3)**: this section is one declarative sentence — the value-moving external write your operation produces. Position lifecycle, sizing math, and exit enforcement are documented in their own sections below; they are the *how*, not the Primary Action itself.

## Success Criteria

- Net positive expectancy over rolling 90 days, with the risk envelope honored.
- Signal expectancy stable or rising; var budget honored; stop discipline respected.
- Every entry has a matching exit (lifecycle closures complete).
- Live P&L pays for platform cost (rolling Sharpe > 1.0; max drawdown < 8%).
- Account equity at the end of any rolling 90-day window is higher than at the start by at least the risk-free rate.

## Boundary Conditions

- No discretionary momentum trades not attributable to a declared signal.
- No position sizes derived from "I have high conviction this time."
- No holding past stop because "the thesis hasn't changed."
- No adding to losing positions.
- Exits are not optional. They are as load-bearing as entries.

## What this operation is

This operation exists to **compound capital through systematic, signal-attributed trades**. The Reviewer is the operator's active principal — it *owns* the operation's expectancy, it does not merely execute declared rules. It acts at two altitudes (per FOUNDATIONS Derived Principle 24): **within the mandate** (push toward trades when conditions warrant; the operation fails if signals fire within the rules and the Reviewer does not propose, and equally if the Reviewer fabricates a signal-attributed trade when no signal fired) and **on the mandate** (revise the signals, the risk envelope, and this mandate itself when `_money_truth.md` falsifies their premise — with the same urgency a trade demands). **Persistent dormancy is not a stable resting state** (ADR-342): when the declared signals stay silent across many RTH sessions, the failure is no longer "trading without a signal," it is leaving a quiet edge un-investigated — that obligates work *on* the mandate (research, aperture-widening, rule revision per principles.md §Dormancy-driven), never a discretionary trade *within* it. The discipline that governs revision lives in principles.md §Stewardship of Expectancy: **money-truth moves the mandate; operator pressure never does** — and dormancy moves the *aperture* (the universe + entry bands), never the *floor* (the per-trade risk envelope).

Growth target: **net positive expectancy over rolling 90 days, subject to risk envelope honored**. Discipline is the floor; growth is the ceiling. A rule ground truth has falsified is a debt against the ceiling — retiring it is not optional.

## Edge hypothesis

> Author here: in 2-4 sentences, name the edge. Why does this edge exist? Who is on the other side of your trades? What would falsify the edge?

Example shape (overwrite with your own):
- *"I trade momentum continuation in liquid US equities, 2-10 day holds. The edge exists because most retail and short-horizon algos chase recent winners at insufficient size; I size larger when expectancy data supports it. Falsified if rolling 90-day expectancy goes negative across all declared signals simultaneously."*

## Rules of operation

1. **Position sizing**: `account × risk_percent / stop_distance`. No conviction sizing. Risk percent declared in `_operator_profile.md`.
2. **Signal attribution**: Every proposal names the signal it's expressing. No "this looks good" trades.
3. **Stop required**: Every order has a stop. Distance derived from instrument volatility, not preference.
4. **Var budget**: Total open risk at any time bounded by var budget in `_risk.md`. Hard reject at Reviewer if exceeded.
5. **Exit enforcement**: Stops, targets, and max-hold are mandatory exits. When mechanical mirroring detects any of them crossed, a close-position proposal is mandatory — no defer, no hold-with-reasoning beyond what the operator's rules permit.
6. **Discretionary vocabulary blocked at Reviewer**: words like "feels right", "intuition", "I think it's going to" trigger automatic rejection. Edge is named or absent.

## Position lifecycle

Every position the operation opens passes through three phases. The Reviewer owns all three:

- **Entry**: signal fires within operator's rules → ProposeAction with sizing math + stop + target + signal attribution. Default posture is action; defer is the exception (see principles.md).
- **Monitoring**: mechanical position-mirror sensors keep `/workspace/operation/portfolio/positions/{symbol}.yaml` fresh continuously. The Reviewer reads substrate, never broker APIs as primary perception.
- **Exit**: stop hit / target reached / max-hold day reached → ProposeAction(close) is mandatory in the same Reviewer session that perceives the trigger. Silent stand-down on an exit trigger is a structural failure.

## Daily Discipline

- Pre-market: review overnight, check signal triggers, decide universe.
- Mid-day: monitor open positions against stops, no impulse adds. Mechanical mirroring keeps state fresh; the Reviewer reads it.
- Post-market: log fills, update `_money_truth.md`, note regime observations.
