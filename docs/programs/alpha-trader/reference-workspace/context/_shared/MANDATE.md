# Mandate — alpha-trader

> **Operator**: author this file. Keep what serves you, delete what doesn't, and add what's missing for your edge. The platform reads this as the gate for task creation (per ADR-207).

## What this operation is

This operation exists to **compound capital through systematic, signal-attributed trades**. The Reviewer is the operator's active principal — its job is to push toward trades when conditions warrant, not to sit waiting for the operator to ask. The operation is failing if signals fire within the operator's declared rules and the Reviewer does not propose; it is also failing if signals do not fire and the Reviewer proposes anyway.

Growth target: **net positive expectancy over rolling 90 days, subject to risk envelope honored**. Discipline is the floor; growth is the ceiling.

## Primary Action

Submit equity / option orders to broker, sized per declared risk rule, attributed to a named signal. **Every position has an exit.** The operation is incomplete if entries are taken and exits are not enforced — stops, targets, and max-hold are non-negotiable, and the Reviewer is responsible for closing positions whose conditions trigger, not just opening positions whose signals fire.

This is the value-moving external write your operation produces. Everything else in the workspace orbits this.

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
- **Monitoring**: mechanical position-mirror sensors keep `/workspace/context/portfolio/positions/{symbol}.yaml` fresh continuously. The Reviewer reads substrate, never broker APIs as primary perception.
- **Exit**: stop hit / target reached / max-hold day reached → ProposeAction(close) is mandatory in the same Reviewer session that perceives the trigger. Silent stand-down on an exit trigger is a structural failure.

## Daily Discipline

- Pre-market: review overnight, check signal triggers, decide universe.
- Mid-day: monitor open positions against stops, no impulse adds. Mechanical mirroring keeps state fresh; the Reviewer reads it.
- Post-market: log fills, update `_performance.md`, note regime observations.

## Outcome Signal

> Author here: how do you know the operation worked? What's the leading indicator vs the lagging indicator?

Example shape (the floor is self-funding; the ceiling is compounding):
- Leading: signal expectancy stable or rising over rolling 90 days; var budget honored; stop discipline respected; lifecycle closures complete (every entry has its matching exit).
- Lagging (floor): rolling Sharpe > 1.0; max drawdown < 8%; live P&L pays for platform cost.
- Lagging (growth): net positive return over rolling 90 days subject to risk envelope; account equity at the end of any rolling 90-day window is higher than at the start by at least the risk-free rate.

## What is OUT of scope

- Discretionary momentum trades not attributable to a declared signal.
- Position sizes derived from "I have high conviction this time."
- Holding past stop because "the thesis hasn't changed."
- Adding to losing positions.
- Treating exits as optional. Exits are as load-bearing as entries.
