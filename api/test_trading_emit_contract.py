"""Architecture-axis test — the trading emit-contract validator (2026-06-19).

THE TWO-AXIS MODEL (docs/evaluations/EVAL-SUITE-DISCIPLINE.md §0): whether a
trading proposal's emitted shape matches the executor's schema is a
deterministic fact with a single right answer — a MACHINE question, tested
here, NOT a Reviewer judgment read.

This pins `services.primitives.trading_emit_contract.validate_and_repair_
trading_emit`, the propose-time guard that closes the gap in
`docs/evaluations/2026-06-19-execution-emit-contract-gap-FINDING.md`: the
signal-evaluation Reviewer reasoned a stop correctly but serialized it into a
shape no executor reads (plain submit_order + `stop_loss_price`), so the stop
was invisible to the risk gate and rejected "no stop" at EXECUTION time. The
validator repairs the known drifts at PROPOSE time or fails loudly.

Each test case is a real receipt from the finding (kvk proposals 9c3e3555,
126fc0ed, b06d53ed, 815ecc18) or the executor contract in platform_tools.py.

Run as a script (deterministic check()/sys.exit, mirrors the repo's gate
convention — pytest does not surface the sys.exit summary):
    api/venv/bin/python api/test_trading_emit_contract.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "api")

from services.primitives.trading_emit_contract import validate_and_repair_trading_emit


_passed = 0
_failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")


# ── 1. The live bug (kvk 9c3e3555): plain submit_order + stop_loss_price ──────
# The exact emit from today's capability run. Must promote to bracket and lift
# the stop to the canonical field so the gate sees it.
r = validate_and_repair_trading_emit(
    "trading.submit_order",
    {"qty": 4, "side": "buy", "ticker": "NVDA", "order_type": "limit",
     "limit_price": 847.5, "stop_loss_price": 829.2},
)
check("9c3e3555: promoted to bracket", r["action_type"] == "trading.submit_bracket_order", r)
check("9c3e3555: stop lifted to stop_loss_stop_price", r["inputs"].get("stop_loss_stop_price") == 829.2, r["inputs"])
check("9c3e3555: entry lifted to entry_limit_price", r["inputs"].get("entry_limit_price") == 847.5, r["inputs"])
check("9c3e3555: drifted stop_loss_price purged", "stop_loss_price" not in r["inputs"], r["inputs"])
check("9c3e3555: drifted limit_price purged", "limit_price" not in r["inputs"], r["inputs"])
# It had no take-profit → bracket requires one → must FAIL LOUDLY, not silently.
check("9c3e3555: missing TP → loud error (not silent)", r["error"] is not None and "take_profit" in r["error"], r["error"])

# ── 2. A complete, contract-perfect bracket passes untouched ──────────────────
r = validate_and_repair_trading_emit(
    "trading.submit_bracket_order",
    {"ticker": "NVDA", "side": "buy", "qty": 8, "entry_limit_price": 180.20,
     "take_profit_limit_price": 192.40, "stop_loss_stop_price": 171.05,
     "time_in_force": "day"},
)
check("clean bracket: no error", r["error"] is None, r)
check("clean bracket: no repairs", r["repaired"] == [], r["repaired"])
check("clean bracket: unchanged action_type", r["action_type"] == "trading.submit_bracket_order", r)
check("clean bracket: stop preserved", r["inputs"]["stop_loss_stop_price"] == 171.05, r["inputs"])

# ── 3. plain submit_order with a stop AND a target → full promotion ───────────
# A stop-bearing plain order that also names a target repairs to a complete,
# valid bracket (the happy repair path the signal-evaluation emit should hit).
r = validate_and_repair_trading_emit(
    "trading.submit_order",
    {"ticker": "NVDA", "side": "buy", "qty": 4, "order_type": "limit",
     "limit_price": 180.20, "stop_loss_price": 171.05, "take_profit_price": 192.40},
)
check("full promote: bracket", r["action_type"] == "trading.submit_bracket_order", r)
check("full promote: no error", r["error"] is None, r)
check("full promote: stop", r["inputs"].get("stop_loss_stop_price") == 171.05, r["inputs"])
check("full promote: target", r["inputs"].get("take_profit_limit_price") == 192.40, r["inputs"])
check("full promote: entry", r["inputs"].get("entry_limit_price") == 180.20, r["inputs"])
check("full promote: records the repair", any("promoted" in x for x in r["repaired"]), r["repaired"])

# ── 4. bracket with a drifted stop alias only (stop_loss) → rename, no promote ─
r = validate_and_repair_trading_emit(
    "trading.submit_bracket_order",
    {"ticker": "NVDA", "side": "buy", "qty": 8, "entry_limit_price": 180.20,
     "take_profit_limit_price": 192.40, "stop_loss": 171.05},
)
check("bracket alias: stop renamed", r["inputs"].get("stop_loss_stop_price") == 171.05, r["inputs"])
check("bracket alias: alias purged", "stop_loss" not in r["inputs"], r["inputs"])
check("bracket alias: no error", r["error"] is None, r)

# ── 5. a genuinely plain order with NO stop passes as plain (not over-promoted) ─
# A market/limit order the operator legitimately wants WITHOUT a stop must NOT
# be force-promoted — the validator only acts on stop-bearing or drifted emits.
r = validate_and_repair_trading_emit(
    "trading.submit_order",
    {"ticker": "AAPL", "side": "buy", "qty": 10, "order_type": "market"},
)
check("plain no-stop: stays submit_order", r["action_type"] == "trading.submit_order", r)
check("plain no-stop: no error", r["error"] is None, r)
check("plain no-stop: no repairs", r["repaired"] == [], r["repaired"])

# ── 6. malformed payload (kvk 126fc0ed: missing required fields) → loud error ──
r = validate_and_repair_trading_emit(
    "trading.submit_order",
    {"side": "buy", "order_type": "limit"},  # missing ticker + qty
)
check("126fc0ed: missing ticker/qty → error", r["error"] is not None, r)
check("126fc0ed: error names the missing fields", "ticker" in r["error"] and "qty" in r["error"], r["error"])

# ── 7. trailing stop: minimal required set passes ─────────────────────────────
r = validate_and_repair_trading_emit(
    "trading.submit_trailing_stop",
    {"ticker": "NVDA", "side": "sell", "qty": 8, "trail_percent": 3.0},
)
check("trailing: passes with required set", r["error"] is None, r)
check("trailing: unchanged", r["action_type"] == "trading.submit_trailing_stop", r)

# ── 8. non-trading action_type passes through untouched (scope guard) ─────────
r = validate_and_repair_trading_emit(
    "commerce.issue_refund",
    {"order_id": "abc", "amount_cents": 500},
)
check("non-trading: passthrough no error", r["error"] is None, r)
check("non-trading: passthrough no repairs", r["repaired"] == [], r)
check("non-trading: inputs untouched", r["inputs"] == {"order_id": "abc", "amount_cents": 500}, r["inputs"])

# ── 9. FLOOR DISCIPLINE (DP24): the validator never relaxes a risk rule ───────
# A repaired order still carries its real sizing — the validator changes SHAPE,
# never VALUES. The 33.9%-of-portfolio order (kvk b06d53ed) is repaired to a
# bracket but its qty is untouched, so the risk gate's max_position_percent
# rule still rejects it downstream. The validator does not make a bad order pass.
r = validate_and_repair_trading_emit(
    "trading.submit_order",
    {"ticker": "NVDA", "side": "buy", "qty": 100, "order_type": "limit",
     "limit_price": 180.20, "stop_loss_price": 171.05, "take_profit_price": 192.40},
)
check("b06d53ed: qty untouched by repair (floor intact)", r["inputs"]["qty"] == 100, r["inputs"])
check("b06d53ed: stop value untouched", r["inputs"]["stop_loss_stop_price"] == 171.05, r["inputs"])


print(f"\n{_passed} passed, {_failed} failed")
sys.exit(0 if _failed == 0 else 1)
