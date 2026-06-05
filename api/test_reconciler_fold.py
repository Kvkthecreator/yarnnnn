"""Architecture-axis integration test — the outcome-reconciler fold (2026-06-05).

THE TWO-AXIS MODEL (docs/evaluations/EVAL-SUITE-DISCIPLINE.md §0): how raw fills
fold into _money_truth.md (totals, by_signal attribution, rolling 7d/30d/90d
windows) is a deterministic computation with a single right answer — a MACHINE
question, tested here, NOT a Reviewer read.

This is the carry-over's architecture gap #2: the existing tests that touch
_money_truth.md (test_adr242 cockpit render, test_adr317 email parse) read
PRE-SEEDED windows — none exercise the FOLD that produces them. The reconciler
fold is what the EOD reconciliation-judgment eval depends on: the Reviewer reads
reconciled windows and attributes P&L to signals. If the fold math is wrong, the
Reviewer reasons over wrong numbers and the judgment read is meaningless. This
pins the fold so the judgment eval is fed a trustworthy situation.

Two layers tested:
  1. Pure math (services.outcomes.ledger._apply_entries + _compute_window):
     controlled candidates → exact totals, by_action_type, by_signal, and the
     rolling-window membership (events at 1d/10d/45d ago land in 7d/30d/90d as
     expected).
  2. The real fold path (fold_outcome_candidates with the two I/O seams
     —_read_money_truth_file + _upsert_money_truth_file— patched): proves the
     idempotency contract (duplicate alpaca_order_id keys skip) and the
     parse↔render round-trip preserves frontmatter state.

Synthetic fills carry recent executed_at timestamps at known offsets relative to
now, so window membership is deterministic without a frozen clock.

Run: .venv/bin/python api/test_reconciler_fold.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import services.outcomes.ledger as ledger  # noqa: E402
from services.outcomes.ledger import (  # noqa: E402
    _apply_entries,
    _compute_window,
    _format_cents,
    _init_money_truth,
    fold_outcome_candidates,
)
from services.outcomes.trading import TradingOutcomeProvider  # noqa: E402

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


NOW = datetime.now(timezone.utc)
PROVIDER = TradingOutcomeProvider()


def _fill(order_id: str, value_cents: int, signal_id: str | None, days_ago: float) -> dict:
    """A synthetic reconciled fill (OutcomeCandidate shape)."""
    executed = NOW - timedelta(days=days_ago)
    cand = {
        "action_type": "trading.submit_order_paper",
        "action_inputs": {"ticker": "NVDA"},
        "executed_at": executed,
        "outcome_label": "closed_profit" if value_cents > 0 else "closed_loss",
        "context_domain": "trading",
        "reconciliation_confidence": "high",
        "outcome_value_cents": value_cents,
        "outcome_currency": "USD",
        "outcome_metadata": {"alpaca_order_id": order_id, "symbol": "NVDA"},
    }
    if signal_id:
        cand["signal_id"] = signal_id
    return cand


# ── 1. PURE MATH — totals + by_action + by_signal from a controlled batch ────
# Three fills: +$200 (signal-2, 1d ago), -$80 (signal-2, 10d ago), +$150
# (signal-1, 45d ago). Aggregate = +$270 over 3 events.
perf = _init_money_truth("trading")
batch = [
    _fill("ord-A", 20_000, "signal-2-mean-reversion-oversold", days_ago=1),
    _fill("ord-B", -8_000, "signal-2-mean-reversion-oversold", days_ago=10),
    _fill("ord-C", 15_000, "signal-1-momentum-breakout", days_ago=45),
]
_apply_entries(perf, batch, PROVIDER)

check(
    "totals.reconciled_event_count == 3",
    perf["totals"]["reconciled_event_count"] == 3,
    str(perf["totals"]),
)
check(
    "totals.aggregate_value_cents == +27000 (200 - 80 + 150 dollars)",
    perf["totals"]["aggregate_value_cents"] == 27_000,
    str(perf["totals"]),
)

# by_signal attribution: signal-2 has 2 fills net +$120 (1 win, 1 loss);
# signal-1 has 1 fill +$150 (1 win).
s2 = perf["by_signal"]["signal-2-mean-reversion-oversold"]
s1 = perf["by_signal"]["signal-1-momentum-breakout"]
check(
    "by_signal[signal-2]: count 2, value +12000, wins 1, losses 1",
    s2["count"] == 2 and s2["value_cents"] == 12_000 and s2["wins"] == 1 and s2["losses"] == 1,
    str(s2),
)
check(
    "by_signal[signal-1]: count 1, value +15000, wins 1, losses 0",
    s1["count"] == 1 and s1["value_cents"] == 15_000 and s1["wins"] == 1 and s1["losses"] == 0,
    str(s1),
)

# ── 2. ROLLING WINDOWS — membership by executed_at offset ────────────────────
# 7d window: only ord-A (1d). 30d: ord-A + ord-B (1d, 10d). 90d: all three.
r7, r30, r90 = perf["rolling_7d"], perf["rolling_30d"], perf["rolling_90d"]
check(
    "rolling_7d: 1 event (only the 1d-ago fill), value +20000",
    r7["count"] == 1 and r7["value_cents"] == 20_000,
    str(r7),
)
check(
    "rolling_30d: 2 events (1d + 10d), value +12000",
    r30["count"] == 2 and r30["value_cents"] == 12_000,
    str(r30),
)
check(
    "rolling_90d: 3 events (all), value +27000",
    r90["count"] == 3 and r90["value_cents"] == 27_000,
    str(r90),
)

# Per-signal rolling windows track in lockstep: signal-2's 30d holds both its
# fills (1d + 10d); its 7d holds only the 1d fill.
check(
    "by_signal[signal-2].rolling_7d: 1 event +20000 (the 1d win only)",
    s2["rolling_7d"]["count"] == 1 and s2["rolling_7d"]["value_cents"] == 20_000,
    str(s2.get("rolling_7d")),
)
check(
    "by_signal[signal-2].rolling_30d: 2 events +12000",
    s2["rolling_30d"]["count"] == 2 and s2["rolling_30d"]["value_cents"] == 12_000,
    str(s2.get("rolling_30d")),
)

# ── 3. _compute_window in isolation — boundary correctness ───────────────────
events = [
    {"executed_at": (NOW - timedelta(days=2)).isoformat(), "value_cents": 500},
    {"executed_at": (NOW - timedelta(days=8)).isoformat(), "value_cents": -300},
    {"executed_at": (NOW - timedelta(days=40)).isoformat(), "value_cents": 100},
]
w7 = _compute_window(events, NOW, 7)
check(
    "_compute_window(7d): 1 event, +500, 1 win 0 loss",
    w7 == {"count": 1, "value_cents": 500, "wins": 1, "losses": 0},
    str(w7),
)
w30 = _compute_window(events, NOW, 30)
check(
    "_compute_window(30d): 2 events, +200, 1 win 1 loss",
    w30 == {"count": 2, "value_cents": 200, "wins": 1, "losses": 1},
    str(w30),
)

# ── 4. _format_cents — signed dollar rendering ───────────────────────────────
check("_format_cents(+27000) == $270.00", _format_cents(27_000) == "$270.00")
check("_format_cents(-8000) == -$80.00", _format_cents(-8_000) == "-$80.00")
check("_format_cents(None) == $0.00", _format_cents(None) == "$0.00")

# ── 5. FOLD PATH — idempotency: duplicate alpaca_order_id skips ──────────────
# Patch the two I/O seams so the REAL fold runs against an in-memory file.
_store: dict[str, str] = {}


async def _fake_read(client, user_id, domain):  # noqa: ANN001
    from services.outcomes.ledger import _parse_money_truth_file
    content = _store.get(domain)
    return _parse_money_truth_file(content) if content else None


async def _fake_upsert(client, user_id, domain, content):  # noqa: ANN001
    _store[domain] = content
    return True


def run_fold(candidates):
    orig_read, orig_upsert = ledger._read_money_truth_file, ledger._upsert_money_truth_file
    # high_impact actuation reads workspace_files (load_high_impact_thresholds);
    # neutralize it so the fold path doesn't touch the DB.
    import services.outcomes.high_impact as hi
    orig_hi = hi.load_high_impact_thresholds
    ledger._read_money_truth_file = _fake_read
    ledger._upsert_money_truth_file = _fake_upsert
    hi.load_high_impact_thresholds = lambda client, user_id: {}
    try:
        return asyncio.run(
            fold_outcome_candidates(None, "test-user", PROVIDER, candidates)
        )
    finally:
        ledger._read_money_truth_file = orig_read
        ledger._upsert_money_truth_file = orig_upsert
        hi.load_high_impact_thresholds = orig_hi


_store.clear()
first = run_fold([
    _fill("ord-X", 10_000, "signal-2-mean-reversion-oversold", days_ago=1),
    _fill("ord-Y", -5_000, "signal-2-mean-reversion-oversold", days_ago=2),
])
check(
    "fold #1: 2 appended, 0 duplicate",
    first["appended"] == 2 and first["skipped_duplicate"] == 0,
    str(first),
)

# Re-fold the SAME order ids → all skip as duplicate (idempotency contract).
second = run_fold([
    _fill("ord-X", 10_000, "signal-2-mean-reversion-oversold", days_ago=1),
    _fill("ord-Y", -5_000, "signal-2-mean-reversion-oversold", days_ago=2),
])
check(
    "fold #2 (same order ids): 0 appended, 2 duplicate (idempotent)",
    second["appended"] == 0 and second["skipped_duplicate"] == 2,
    str(second),
)

# A new order id folds in on top of the existing state (incremental accumulation).
third = run_fold([_fill("ord-Z", 30_000, "signal-1-momentum-breakout", days_ago=3)])
check(
    "fold #3 (new order id): 1 appended on top of prior state",
    third["appended"] == 1 and third["skipped_duplicate"] == 0,
    str(third),
)

# ── 6. ROUND-TRIP — the persisted file parses back to correct accumulated state
from services.outcomes.ledger import _parse_money_truth_file  # noqa: E402

final = _parse_money_truth_file(_store["trading"])
check(
    "round-trip: persisted file parses; 3 total events accumulated (X, Y, Z)",
    final is not None and final["totals"]["reconciled_event_count"] == 3,
    str(final["totals"]) if final else "parse returned None",
)
check(
    "round-trip: aggregate value +35000 (100 - 50 + 300 dollars)",
    final["totals"]["aggregate_value_cents"] == 35_000,
    str(final["totals"]),
)
check(
    "round-trip: by_signal carries both signals after incremental folds",
    "signal-2-mean-reversion-oversold" in final["by_signal"]
    and "signal-1-momentum-breakout" in final["by_signal"],
    str(list(final["by_signal"].keys())),
)
check(
    "round-trip: processed_event_keys deduped + namespaced (3 keys)",
    len(final["processed_event_keys"]) == 3
    and all(k.startswith("alpaca_order_id:") for k in final["processed_event_keys"]),
    str(final["processed_event_keys"]),
)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
