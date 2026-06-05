# Ticker Snapshot Spec

Schema for the per-ticker snapshot files written by the `track-universe`
recurrence to `/workspace/operation/trading/{ticker}.yaml`.

## File format

YAML, one file per ticker. **UPPERCASE** ticker as filename
(e.g. `NVDA.yaml`, `AAPL.yaml`) — the `track-universe` primitive writes
`/workspace/operation/trading/{TICKER}.yaml` via `ticker.upper()`
(`api/services/primitives/track_universe.py`).

> **Spec corrected 2026-06-05.** This previously documented lowercase
> filenames + a `last_close` field; both drifted from the code (which writes
> UPPERCASE filenames and a `price` field). The drift caused a seeded snapshot
> to land in a file `signal-evaluation` never read (see
> `docs/evaluations/2026-06-04-114939-…` finding). The actual fields the
> `track-universe` writer emits — and that the signal rules must reference —
> are: `price`, `sma_20`, `sma_50`, `sma_200`, `rsi_14`, `atr_14`,
> `volume_20d_avg`, plus `ticker` + `last_updated`. Both contracts (casing +
> field names) are locked by `api/test_trading_pipeline_architecture.py`.

## Required fields

> This example is the **exact** field set the `track-universe` writer emits
> (`api/services/primitives/track_universe.py` `_compute_indicators` +
> `_write_ticker_yaml`). It is locked by
> `api/test_trading_pipeline_architecture.py` — do not add fields here that the
> writer does not emit, or the signal rules will reference data that never lands.

```yaml
ticker: NVDA                             # always UPPERCASE (ticker.upper())
last_updated: 2026-05-10T08:15:00Z       # ISO-8601 with timezone; the recurrence fire time
price: 925.40                            # most-recent 1Day bar close (closes[-1])

# Technicals (computed from the daily-bar window)
sma_20: 891.30
sma_50: 845.10
sma_200: 812.70
rsi_14: 62.4
atr_14: 22.30
volume_20d_avg: 11_500_000
```

## Quality criteria

- Every field above is emitted by the writer on every successful run; the
  signal rules in `_operator_profile.md` must reference only these fields
- Numerical values are unquoted YAML numbers, not strings
- The filename is UPPERCASE (`NVDA.yaml`), matching `ticker.upper()` in the writer
- When fewer than 200 daily bars are available, `track-universe` skips the ticker
  with an `insufficient bars` error rather than writing a partial snapshot
