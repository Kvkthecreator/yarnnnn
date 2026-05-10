# Ticker Snapshot Spec

Schema for the per-ticker snapshot files written by the `track-universe`
recurrence to `/workspace/context/trading/{ticker}.yaml`.

## File format

YAML, one file per ticker. Lowercase ticker as filename
(e.g. `nvda.yaml`, `aapl.yaml`).

## Required fields

```yaml
ticker: NVDA
last_updated: 2026-05-10T08:15:00Z      # ISO-8601 with timezone
last_close: 925.40                       # most-recent 1Hour bar close
last_volume: 14_823_000                  # most-recent 1Hour bar volume
prev_close: 918.20                       # prior session's official close

# Price/volume technicals (computed from latest bars + 30-day window)
sma_20: 891.30
sma_50: 845.10
rsi_14: 62.4
atr_14: 22.30
volume_30d_avg: 11_500_000
volume_relative: 1.29                    # last_volume / volume_30d_avg

# Optional fundamentals (filled when available; null otherwise)
market_cap_usd: 2_270_000_000_000
sector: "Technology"
earnings_next: 2026-05-22                # null if not scheduled

# Optional flags
data_stale: false                        # true if Alpaca returned >2h old bars
```

## Quality criteria

- Every required field is populated; `null` is acceptable only on optional fields
- Numerical values are unquoted YAML numbers, not strings
- `last_updated` matches the bar timestamp, not the recurrence fire time
- When Alpaca returns stale data (e.g., over a long weekend), set `data_stale: true`
  rather than backfilling with stale values
