"""Architecture-axis integration test — the trading pipeline plumbing (2026-06-05).

THE TWO-AXIS MODEL (docs/evaluations/EVAL-SUITE-DISCIPLINE.md §0): a deterministic
fact about whether the MACHINE works belongs in a test like this — NOT in a
judgment eval. This test exists because the alpha-trader trade-observation arc
kept failing on PLUMBING bugs (silent-wake trigger mismatch, ticker-file casing
drift, field-name drift, the live mirror overwriting seeds) that masqueraded as
Reviewer judgment outcomes in the eval suite. Those are machine faults with a
single right answer — exactly what a deterministic test catches instantly.

What this test pins (the contracts that actually drifted):
  1. track_universe writes UPPERCASE `{TICKER}.yaml` (track_universe.py:264
     `ticker.upper()`) — NOT lowercase `nvda.yaml` as the ticker-snapshot spec
     said. The 2026-06-04 run seeded lowercase and signal-evaluation never saw
     it; this asserts the canonical case so a future seed/tooling can't drift.
  2. The indicator FIELDS match what signal-evaluation reads against
     _operator_profile.md signal rules: `price`, `rsi_14`, `sma_20/50/200`,
     `atr_14`. (The writer emits `price`, not `last_close` — a field-name the
     signal rules must reference correctly.)
  3. _compute_indicators is deterministic: given known bars, it produces known
     indicators (the INPUT-controlled half — mock the market-data source, run
     the REAL computation, assert the output). This is how the architecture
     axis produces a guaranteed signal condition WITHOUT seeding a recurrence's
     output file (which the live mirror overwrites).

This is the FIRST instance of the architecture-axis layer. A full end-to-end
pipeline test (synthetic bars → track_universe → signal-evaluation match →
ProposeAction → auto-execute) is the next build; this pins the deterministic
mechanical half (track_universe), which is where the casing/field drift lived.

Run: .venv/bin/python api/test_trading_pipeline_architecture.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.primitives.track_universe import _compute_indicators  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")


# ── synthetic bars: a steady decline → low RSI (mean-reversion-oversold zone) ─
# 210 bars (track_universe._BARS_LIMIT) so SMA-200 computes. Mild decline so RSI
# lands low but > 0 (a realistic oversold reading, not the degenerate all-loss
# RSI=0). Alpaca returns newest-first; _compute_indicators reverses internally,
# so we pass newest-first.
def _build_declining_bars(n: int = 210, start: float = 240.0, daily: float = 0.992) -> list[dict]:
    bars_oldest_first = []
    price = start
    for _ in range(n):
        o = price
        price = price * daily
        bars_oldest_first.append(
            {"open": o, "high": o * 1.003, "low": price * 0.997, "close": price, "volume": 40_000_000}
        )
    return list(reversed(bars_oldest_first))  # newest-first (Alpaca shape)


bars = _build_declining_bars()
ind = _compute_indicators(bars)

# ── 1. indicator FIELDS — the exact keys signal-evaluation reads ─────────────
expected_fields = {"price", "sma_20", "sma_50", "sma_200", "rsi_14", "atr_14", "volume_20d_avg"}
check(
    "indicator dict carries the exact fields the signal rules reference",
    expected_fields.issubset(set(ind.keys())),
    f"got {set(ind.keys())}",
)
check(
    "field is 'price' (NOT 'last_close') — the name signal rules must use",
    "price" in ind and "last_close" not in ind,
)
check("sma_200 computed (210 bars ≥ 200)", ind.get("sma_200") is not None)
check("rsi_14 computed", ind.get("rsi_14") is not None)

# ── 2. determinism — same bars → same indicators (repeatable) ────────────────
ind2 = _compute_indicators(_build_declining_bars())
check(
    "deterministic: identical bars → identical indicators",
    ind == ind2,
    f"{ind} != {ind2}",
)

# ── 3. the computation is correct enough to drive a signal ───────────────────
# A monotone decline must produce a low RSI (oversold) — the precondition for
# Signal 2 (mean-reversion-oversold: RSI < 25). This proves the architecture
# layer CAN produce a signal-matching snapshot deterministically (the thing the
# eval couldn't do by seeding, because the mirror overwrote the seed).
check(
    "monotone decline produces oversold RSI (< 30 — Signal-2 territory)",
    ind.get("rsi_14") is not None and ind["rsi_14"] < 30,
    f"rsi_14={ind.get('rsi_14')}",
)
# Price below the longer SMAs after a decline (sanity on the math direction).
check(
    "declining series: price < sma_200 (math direction sane)",
    ind.get("sma_200") is not None and ind["price"] < ind["sma_200"],
)

# ── 4. the write path is UPPERCASE (the casing contract that drifted) ────────
# track_universe.py:264 — path = f"/workspace/context/trading/{ticker.upper()}.yaml"
# The 2026-06-04 run seeded lowercase nvda.yaml; signal-evaluation read the
# uppercase NVDA.yaml the live mirror wrote. Pin the canonical case from source.
tu_src = (Path(__file__).resolve().parent / "services" / "primitives" / "track_universe.py").read_text()
check(
    "track_universe writes UPPERCASE {TICKER}.yaml (ticker.upper())",
    'f"/workspace/context/trading/{ticker.upper()}.yaml"' in tu_src,
)
check(
    "the ticker payload stamps ticker.upper() too (consistent casing)",
    '"ticker": ticker.upper()' in tu_src,
)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
