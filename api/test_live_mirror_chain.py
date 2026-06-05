"""Architecture-axis integration test — the live-mirror chain (2026-06-05).

THE TWO-AXIS MODEL (docs/evaluations/EVAL-SUITE-DISCIPLINE.md §0): the carry-over's
"hardest E2E" — connect the indicator computation (test_trading_pipeline_
architecture.py) to the execution path (test_alpha_trader_pipeline_e2e.py) THROUGH
the real mechanical mirror. Instead of SEEDING a ticker snapshot (which §0.2
forbids — the live mirror overwrites it, and the casing race lands it where
signal-evaluation can't read it), this MOCKS THE INPUT (alpaca.get_bars returns
synthetic Signal-2-matching bars), runs the REAL track-universe orchestration +
write path, and asserts a GENUINE NVDA.yaml lands that actually satisfies the
operator's Signal-2 numeric rule.

This is the §0-correct way to produce a guaranteed signal situation: control the
input, let the real machine produce the snapshot. It pins the whole deterministic
chain a judgment eval depends on — "when the market warrants Signal-2, does a
NVDA.yaml that genuinely matches Signal-2 land for the Reviewer to act on?" — at
zero LLM cost. The LLM signal-evaluation step (the boolean rule applied by the
Reviewer) is the judgment boundary; this test asserts up to "a matching snapshot
exists," which is exactly the clean situation the eval should be fed.

Signal-2 (mean-reversion-oversold) per docs/programs/alpha-trader/reference-
workspace/context/trading/_operator_profile.md §"Signal 2":
  RSI(14) < 25  AND  price within 5% of 200-day SMA  AND  sma_20 > sma_50.

The four external seams of handle_track_universe are mocked (credentials,
universe list, alpaca.get_bars, write_revision); EVERYTHING ELSE runs real —
the get_bars loop, _compute_indicators, _write_ticker_yaml (UPPERCASE path +
yaml.dump), and the orchestration return shape.

Run: .venv/bin/python api/test_live_mirror_chain.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml as _yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import services.primitives.track_universe as tu  # noqa: E402

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


# ── synthetic bars: mild long-run uptrend + shallow recent dip ───────────────
# Tuned so the REAL _compute_indicators lands in Signal-2 territory:
#   drift 1.0008/day over ~200 bars keeps price near sma_200 (uptrend, so
#   sma_20 > sma_50 → not-downtrend), and an 8-day shallow 0.994/day dip pushes
#   RSI well under 25 without crashing price away from sma_200.
# Alpaca returns newest-first; the writer reverses internally, so newest-first.
def _signal2_bars(n: int = 210, base: float = 180.0, drift: float = 1.0008,
                  dip_days: int = 8, dip: float = 0.994) -> list[dict]:
    prices: list[float] = []
    p = base
    for _ in range(n - dip_days):
        p *= drift
        prices.append(p)
    for _ in range(dip_days):
        p *= dip
        prices.append(p)
    bars_oldest_first = [
        {"open": c, "high": c * 1.003, "low": c * 0.997, "close": c, "volume": 40_000_000}
        for c in prices
    ]
    return list(reversed(bars_oldest_first))  # newest-first (Alpaca shape)


# ── mock harness: control the 4 seams, run the REAL handle_track_universe ─────
class _FakeAlpaca:
    async def get_bars(self, api_key, api_secret, symbol, timeframe, limit):  # noqa: ANN001
        # Return Signal-2-matching bars for NVDA; empty for anything else.
        return _signal2_bars() if symbol.upper() == "NVDA" else []


class _Auth:
    def __init__(self):
        self.user_id = "test-user"
        self.client = object()  # never touched — the readers are mocked


_written: dict[str, str] = {}


def run_track_universe(universe: list[str]):
    """Run handle_track_universe with all external seams mocked."""
    async def _fake_creds(client, user_id):  # noqa: ANN001
        return ("fake-key", "fake-secret", True)

    async def _fake_universe(client, user_id):  # noqa: ANN001
        return universe

    def _fake_write_revision(client, *, user_id, path, content, **kw):  # noqa: ANN001
        _written[path] = content

    orig_creds = tu._load_trading_credentials
    orig_universe = tu._read_universe
    orig_get_client = None
    # get_trading_client is imported inside the function body; patch the module
    # it's imported from.
    import integrations.core.alpaca_client as ac
    orig_get_client = ac.get_trading_client
    import services.authored_substrate as auth_sub
    orig_write = auth_sub.write_revision

    tu._load_trading_credentials = _fake_creds
    tu._read_universe = _fake_universe
    ac.get_trading_client = lambda: _FakeAlpaca()
    auth_sub.write_revision = _fake_write_revision
    try:
        return asyncio.run(tu.handle_track_universe(_Auth(), {}))
    finally:
        tu._load_trading_credentials = orig_creds
        tu._read_universe = orig_universe
        ac.get_trading_client = orig_get_client
        auth_sub.write_revision = orig_write


# ── run the real chain ───────────────────────────────────────────────────────
_written.clear()
result = run_track_universe(["NVDA"])

# ── 1. the orchestration succeeds + reports the right shape ──────────────────
check("track-universe returns success", result.get("success") is True, str(result))
check("items_processed == 1 (NVDA)", result.get("items_processed") == 1, str(result))
check(
    "paths_written contains UPPERCASE NVDA.yaml (the casing contract)",
    result.get("paths_written") == ["/workspace/context/trading/NVDA.yaml"],
    str(result.get("paths_written")),
)
check("no errors", not result.get("errors"), str(result.get("errors")))

# ── 2. the written file actually landed at the UPPERCASE path ────────────────
nvda_path = "/workspace/context/trading/NVDA.yaml"
check(
    "write_revision wrote NVDA.yaml (not lowercase nvda.yaml)",
    nvda_path in _written and "/workspace/context/trading/nvda.yaml" not in _written,
    str(list(_written.keys())),
)

# ── 3. the written YAML parses + carries the writer-exact fields ─────────────
# Strip the leading "# ... comment" header line the writer prepends.
raw = _written[nvda_path]
body = "\n".join(line for line in raw.splitlines() if not line.startswith("#"))
snap = _yaml.safe_load(body)
check("written YAML parses to a dict", isinstance(snap, dict), repr(snap)[:120])
check("ticker stamped UPPERCASE NVDA", snap.get("ticker") == "NVDA", str(snap.get("ticker")))
expected_fields = {"ticker", "last_updated", "price", "sma_20", "sma_50",
                   "sma_200", "rsi_14", "atr_14", "volume_20d_avg"}
check(
    "written snapshot carries exactly the writer's field set",
    set(snap.keys()) == expected_fields,
    f"got {set(snap.keys())}",
)
check(
    "field is 'price' (NOT 'last_close') — the signal-rule field name",
    "price" in snap and "last_close" not in snap,
)

# ── 4. THE LOAD-BEARING ASSERTION — the snapshot genuinely satisfies Signal-2 ─
# This is what the seed-the-file approach could never guarantee deterministically.
# Apply the operator's Signal-2 numeric rule to the GENUINE computed values.
rsi = snap["rsi_14"]
price = snap["price"]
sma_200 = snap["sma_200"]
sma_20 = snap["sma_20"]
sma_50 = snap["sma_50"]
within_pct = abs(price - sma_200) / sma_200 * 100

check(
    "Signal-2 cond 1: RSI(14) < 25 (genuinely oversold)",
    rsi < 25,
    f"rsi_14={rsi}",
)
check(
    "Signal-2 cond 2: price within 5% of 200-day SMA",
    within_pct <= 5,
    f"price={price:.2f} sma_200={sma_200:.2f} within={within_pct:.2f}%",
)
check(
    "Signal-2 cond 3: not in confirmed downtrend (sma_20 > sma_50)",
    sma_20 > sma_50,
    f"sma_20={sma_20:.2f} sma_50={sma_50:.2f}",
)
check(
    "ALL THREE Signal-2 conditions hold on the REAL computed snapshot",
    rsi < 25 and within_pct <= 5 and sma_20 > sma_50,
    f"rsi={rsi} within={within_pct:.2f}% sma20>{sma_20:.2f}>{sma_50:.2f}",
)

# ── 5. insufficient-bars ticker is skipped, not crashed ──────────────────────
_written.clear()
result2 = run_track_universe(["NVDA", "ZZZZ"])  # ZZZZ → empty bars
check(
    "mixed universe: NVDA processed, ZZZZ skipped with an error (not a crash)",
    result2.get("items_processed") == 1
    and any("ZZZZ" in e for e in result2.get("errors", [])),
    str(result2),
)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
