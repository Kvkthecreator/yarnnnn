# Regime State Spec

Schema for `/workspace/operation/trading/_regime.yaml` — the portfolio-level
regime state read by the Reviewer at sizing time.

## Why this file exists

`_operator_profile.md` declares **Signal 5: Volatility-regime filter** —
when VIX is elevated, all signal sizing multiplies by 0.5. `_risk.md` line
33 sets `apply_vix_regime_scalar: true`. Without this file, the regime
predicate has no substrate to live in and the scalar is silently ignored
at proposal time.

This file is the canonical substrate for the regime predicate. Written by
the `track-regime` recurrence, read by the Reviewer at every proposal.

## VIX data source — VIXY proxy

Alpaca does not carry the CBOE Volatility Index (`^VIX`) spot value as a
tradeable instrument. The next-best Alpaca-native proxy is **VIXY**
(ProShares VIX Short-Term Futures ETF). VIXY tracks VIX futures, not VIX
spot, so it carries:

1. **Contango decay** — when futures are above spot (the usual state),
   VIXY drifts down even as VIX is flat.
2. **Threshold translation** — the operator-declared "VIX > 25" predicate
   does not translate to "VIXY > 25" cleanly; calibration matters.

The operator declared the predicate in spot-VIX terms. Until a non-Alpaca
data source is wired (out of scope for this iteration), the Reviewer uses
VIXY thresholds calibrated against the operator's declared spot-VIX rule:

- `vixy_active_threshold` — VIXY level corresponding to spot VIX ≈ 25
  during normal contango. Operator-tunable. Default: `22.0`.
- `vixy_deactivation_threshold` — VIXY level corresponding to spot VIX
  ≈ 20 (per the operator's "VIX < 20 for 5 days" deactivation rule).
  Default: `17.5`.

These defaults are placeholders. The operator should refine them after
observing live VIXY behavior alongside spot VIX (which they can read
externally) for at least 30 days.

## File format

YAML, single file at `/workspace/operation/trading/_regime.yaml`.

## Required fields

```yaml
last_updated: 2026-05-13T20:30:00Z       # ISO-8601 UTC, when this file was written

# VIXY proxy state
vixy_close: 19.40                         # most-recent 1Day VIXY close from Alpaca
vixy_sma_20: 18.10                        # 20-trading-day SMA of VIXY close
vixy_active_threshold: 22.0               # mirror from this spec; operator-tunable in spec only
vixy_deactivation_threshold: 17.5         # mirror from this spec; operator-tunable in spec only

# Computed regime predicate
vix_regime_active: false                  # vixy_close > vixy_active_threshold AND vixy_close > vixy_sma_20
deactivation_streak_days: 3               # consecutive trading days vixy_close < vixy_deactivation_threshold

# Trend regime (SPY-derived)
spy_close: 587.20                         # most-recent SPY 1Day close
spy_sma_20: 581.40
spy_sma_50: 569.80
trend_regime: uptrend                     # uptrend | chop | downtrend
                                          # uptrend  = spy_sma_20 > spy_sma_50 AND spy_close > spy_sma_20
                                          # downtrend = spy_sma_20 < spy_sma_50 AND spy_close < spy_sma_20
                                          # chop = neither

# Optional flags
data_stale: false                         # true if Alpaca returned >24h old bars
```

## Sizing impact

`vix_regime_active` is the single field the Reviewer reads at proposal
time. When `true`, every entry proposal's `position_size` is multiplied
by 0.5, and `sizing_formula_trace` must include the line:

```
regime_scalar: 0.5 (VIX regime active — VIXY=<close> > threshold=<value> AND > sma_20=<value>)
```

When `false`:

```
regime_scalar: 1.0 (VIX regime inactive)
```

`trend_regime` is reported in `pre-market-brief` and `weekly-performance-review`
but is NOT a sizing input. The operator can promote it to a sizing input
in `principles.md` if observation warrants — that's a `principles.md`
evolution, not a schema change here.

## Quality criteria

- Every required field is populated; `null` only acceptable on optional
  fields
- Numerical values are unquoted YAML numbers, not strings
- `last_updated` matches the latest bar's session-close timestamp, not
  the recurrence fire time
- When Alpaca data is stale (>24h old) or unreachable, set
  `data_stale: true` and keep prior values rather than zeroing them out;
  the `principles.md` freshness gate will block proposals while stale

## Operator tunable fields

Two values in this spec — `vixy_active_threshold` and
`vixy_deactivation_threshold` — are operator-tunable defaults. To change
them, edit this spec file; the `track-regime` recurrence reads the spec
and propagates the values into `_regime.yaml` on its next fire. The
spec is the authority; the YAML is the mirror.
