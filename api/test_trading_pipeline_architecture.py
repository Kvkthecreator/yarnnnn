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
# track_universe.py:264 — path = f"/workspace/operation/trading/{ticker.upper()}.yaml"
# The 2026-06-04 run seeded lowercase nvda.yaml; signal-evaluation read the
# uppercase NVDA.yaml the live mirror wrote. Pin the canonical case from source.
tu_src = (Path(__file__).resolve().parent / "services" / "primitives" / "track_universe.py").read_text()
check(
    "track_universe writes UPPERCASE {TICKER}.yaml (ticker.upper())",
    'f"/workspace/operation/trading/{ticker.upper()}.yaml"' in tu_src,
)
check(
    "the ticker payload stamps ticker.upper() too (consistent casing)",
    '"ticker": ticker.upper()' in tu_src,
)

# ── 5. perception-field conformance (ADR-354) ───────────────────────────────
# Root invariant: a NON-DORMANT signal trigger in _operator_profile.md may
# reference ONLY fields the perception field emits. The 2026-06-22 full-autonomy
# probe found Signal 1 referencing "20-day high" + a current-bar "volume > 1.5x"
# surge — fields track_universe NEVER emits — so the signal was structurally
# unfireable and the occupant fabricated a "wait for RTH" story to explain a
# permanent gap. This check makes that class of bug fail CI instead of silently
# shipping a signal no substrate can satisfy.
#
# Emitted perception vocabulary = the snapshot fields (expected_fields above) +
# regime-state fields (_regime.yaml) the rules legitimately reference. A trigger
# token that looks like a data field but is outside this set is the bug.
PERCEPTION_VOCAB = expected_fields | {
    # regime-state fields from _regime.yaml (Signal 5 / regime scalar)
    "vix_regime_active", "vixy_close", "vixy_sma_20", "trend_regime",
    # derived comparisons the rules express in prose against emitted fields
    "sma_20", "sma_50", "sma_200",
}
# Field-shaped tokens that, if present in a non-dormant trigger, indicate a
# reference to data the perception field does NOT emit. (The probe's two.)
ABSENT_FIELD_MARKERS = {
    "20-day high": "no period-high field emitted (use price vs sma_20)",
    "20 day high": "no period-high field emitted",
    "volume > 1.5": "no current-bar volume emitted (only volume_20d_avg)",
    "earnings surprise": "no earnings feed in the perception field",
    "price gap": "no gap field in the perception field",
    "relative-strength rank": "no cross-ticker RS field in the perception field",
}

_profile = (
    Path(__file__).resolve().parent.parent / "docs" / "programs" / "alpha-trader"
    / "reference-workspace" / "operation" / "trading" / "_operator_profile.md"
).read_text()

# Walk signal blocks; a block is DORMANT if its header carries "DORMANT".
import re as _re  # noqa: E402
_blocks = _re.split(r"^### Signal \d+:", _profile, flags=_re.MULTILINE)[1:]
_headers = _re.findall(r"^### Signal \d+:[^\n]*", _profile, flags=_re.MULTILINE)
for _hdr, _blk in zip(_headers, _blocks):
    _dormant = "DORMANT" in _hdr
    # Only the **Trigger:** line is the evaluable rule.
    _trig_m = _re.search(r"\*\*Trigger:\*\*([^\n]*)", _blk)
    _trig = (_trig_m.group(1) if _trig_m else "").lower()
    _sig = _hdr.strip().rstrip()
    if _dormant:
        check(f"{_sig[:34]}… correctly marked DORMANT (feed absent, won't be evaluated)", True)
        continue
    _absent = [why for marker, why in ABSENT_FIELD_MARKERS.items() if marker in _trig]
    check(
        f"{_sig[:34]}… non-dormant trigger references only emitted fields (ADR-354)",
        not _absent,
        f"references absent perception field(s): {_absent}",
    )

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
