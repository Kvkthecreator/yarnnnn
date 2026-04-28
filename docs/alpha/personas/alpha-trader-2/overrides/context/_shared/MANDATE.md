# Mandate — alpha-trader-2 (Stat-Arb Pairs)

> Workspace authored 2026-04-28 by operator on behalf via Phase B parallel-loop test.

## Primary Action

The single external write that moves value: **submit a two-leg
beta-neutral pair trade on Alpaca paper** (long one ticker, short
its cointegrated counterpart, sized vol-targeted at 0.5% per pair).

## Core thesis

Statistical pairs trading on cointegrated US-equity pairs. The
hypothesis is **NOT** that any individual ticker goes up — it is that
**the spread between two cointegrated tickers reverts to its rolling
mean** when it deviates by more than 2 standard deviations.

This is the Simons-flavor edge:
- **Statistical anchor, not vibes.** Each pair's mean-reversion is
  measurable (cointegration test, rolling z-score). When the math
  says it has broken, the pair is dropped from the universe.
- **Many small bets.** 5-20 trades/week across 6 pairs, not 1-2 big
  directional swings.
- **Beta-neutral by construction.** A pair trade is long one leg
  and short its β·other-leg, so the broad-market move washes out.
  The bet is purely on the *spread*.

## Performance objective (Phase 1, paper)

The objective is **R-multiple positive after 30 closed pairs trades**:
- Net cumulative R > 0 (sum of all pair-trade R values)
- Win rate > 55% (pairs trades historically 55-65% on cointegrated US equities)
- Average winner ≥ average loser (per Kelly-fraction sizing logic)
- Max drawdown from cumulative-R peak < 6R

If after 30 trades the system is net negative, that's honest signal
the strategy has no edge on this universe in this regime — and the
correct response is **stop trading**, audit signals, restate thesis.
Not "try harder."

## Boundary conditions

- **Paper account only**, until +5R cumulative across at least 30 trades
  AND win rate ≥ 55% AND max single-pair drawdown < 3R.
- **Pairs from declared universe only** (see _operator_profile.md).
  No discretionary single-leg directional trades. No options. No
  crypto. No ad-hoc additions to the pair universe.
- **No position adds** (Kelly-fractional initial size is the only size).
- **Hard time stop at 5 trading days** regardless of P&L. No
  perpetual carries.

## Daily loss governance

Per _risk.md: 1.5% daily loss → flat all open pairs, no new entries
until next session. 3% drawdown from session-start equity → halt for
remainder of session. 6R cumulative drawdown → halt strategy entirely
pending operator review.

## Reviewer authority

The Reviewer (Simons-inspired persona, see review/IDENTITY.md +
review/principles.md) has **full auto-approval authority during paper
phase** for any proposed pair trade that:
- Is from the declared pair universe
- Has computed |z| > 2.0 with documented entry math
- Sized at exactly 0.5% per pair (no override)
- Two legs are beta-neutral within ±5% notional

Out-of-mandate proposals (different universe, sizing override,
single-leg, or pair without cointegration evidence) → automatic reject.

