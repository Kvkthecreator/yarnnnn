"""Architecture-axis integration test — the risk_gate rule battery (2026-06-05).

THE TWO-AXIS MODEL (docs/evaluations/EVAL-SUITE-DISCIPLINE.md §0): whether the
risk gate APPROVES or REJECTS a given order against given risk parameters is a
deterministic fact with a single right answer — a MACHINE question, tested here,
NOT a Reviewer judgment read.

This is the gate `api/test_alpha_trader_pipeline_e2e.py` MOCKS OPEN (it forces
`check_risk_limits` to approve so it can assert the downstream submit path). That
test proves "when the gate opens, the trade fires." This test proves the gate
itself: the 9 rules of `services.risk_gate.check_risk_limits` + the mode-semantics
fork (autonomous fails-closed on missing params; supervised warns). Together they
cover both halves of the execution safety floor the autonomous loop depends on.

What this pins (services/risk_gate.py::check_risk_limits, the deterministic battery):
  1. allowed_tickers whitelist        — reject when ticker not in the list
  2. blocked_tickers blacklist        — reject when ticker is blocked
  3. max_order_size_shares            — reject oversized share qty
  4. max_position_size_usd            — reject oversized notional (qty × price)
  5. max_position_percent_of_portfolio — reject when notional/equity exceeds pct
  6. max_daily_loss_usd               — reject new positions after loss threshold
  7. max_day_trades (PDT)             — reject when daytrade_count hits the cap
  8. require_stop_loss                — reject a naked order missing a stop
  9. missing ticker                   — reject an order with no ticker
  + mode fork: autonomous + no params → REJECT; supervised + no params → APPROVE+warn
  + the clean path: an order within every declared limit → APPROVE

The two external seams (`_load_risk_params` reading workspace_files;
`_fetch_account_state` reading Alpaca) are monkeypatched so the REAL rule logic
runs against controlled inputs. The whitelist/blacklist/size/stop/missing-ticker
rules need no account state at all; the pct/daily-loss/PDT rules consume the
patched account dict. Nothing touches the network or the DB.

Run: .venv/bin/python api/test_risk_gate_rule_battery.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import services.risk_gate as rg  # noqa: E402

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


# ── harness: run check_risk_limits with controlled params + account state ─────
# We patch the two readers (the only external seams) and let the REAL battery run.
def run_gate(
    proposed_order: dict,
    risk_params: dict | None,
    account_state: dict | None = None,
    mode: str = "autonomous",
) -> dict:
    """Drive check_risk_limits deterministically.

    risk_params=None exercises the missing-params mode fork (the readers are
    still patched, returning None, so no DB/network is touched).
    """
    async def _fake_load(client, user_id):  # noqa: ANN001
        return risk_params

    async def _fake_account(client, user_id):  # noqa: ANN001
        return account_state or {}

    orig_load, orig_account = rg._load_risk_params, rg._fetch_account_state
    rg._load_risk_params = _fake_load
    rg._fetch_account_state = _fake_account
    try:
        return asyncio.run(
            rg.check_risk_limits(client=None, user_id="test-user", proposed_order=proposed_order, mode=mode)
        )
    finally:
        rg._load_risk_params = orig_load
        rg._fetch_account_state = orig_account


# A baseline params set that PASSES so each test can violate exactly one rule.
def _base_params(**overrides) -> dict:
    p = {
        "max_order_size_shares": 100,
        "max_position_size_usd": 100_000,
        "max_position_percent_of_portfolio": 50,
        "max_daily_loss_usd": 10_000,
        "max_day_trades": 3,
        "require_stop_loss": False,
        # trading_hours_only intentionally OFF — its calendar correctness is
        # covered by test_market_hours_gate.py; this battery owns the other rules.
        "allowed_tickers": [],
        "blocked_tickers": [],
    }
    p.update(overrides)
    return p


# A clean order that satisfies the baseline params (limit order, has a stop).
def _base_order(**overrides) -> dict:
    o = {
        "ticker": "NVDA",
        "side": "buy",
        "qty": 10,
        "order_type": "limit",
        "limit_price": 180.0,
        "stop_price": 170.0,
    }
    o.update(overrides)
    return o


# ── 0. the clean path — within every limit → APPROVE ─────────────────────────
res = run_gate(_base_order(), _base_params(), account_state={"equity": 100_000})
check("clean order within all declared limits → approved", res["approved"], res.get("reason", ""))

# ── 1. allowed_tickers whitelist ─────────────────────────────────────────────
res = run_gate(_base_order(ticker="TSLA"), _base_params(allowed_tickers=["NVDA", "AAPL"]))
check(
    "ticker not in allowed_tickers → rejected",
    not res["approved"] and "not in allowed_tickers" in res["reason"],
    res.get("reason", ""),
)

# ── 2. blocked_tickers blacklist ─────────────────────────────────────────────
res = run_gate(_base_order(ticker="GME"), _base_params(blocked_tickers=["GME"]))
check(
    "ticker in blocked_tickers → rejected",
    not res["approved"] and "blocked_tickers" in res["reason"],
    res.get("reason", ""),
)

# ── 3. max_order_size_shares ─────────────────────────────────────────────────
res = run_gate(_base_order(qty=500), _base_params(max_order_size_shares=100))
check(
    "share qty over max_order_size_shares → rejected",
    not res["approved"] and "max_order_size_shares" in res["reason"],
    res.get("reason", ""),
)

# ── 4. max_position_size_usd (notional = qty × price) ────────────────────────
# qty 50 × limit 180 = $9,000 notional, cap $5,000.
res = run_gate(_base_order(qty=50, limit_price=180.0), _base_params(max_position_size_usd=5_000))
check(
    "notional over max_position_size_usd → rejected",
    not res["approved"] and "max_position_size_usd" in res["reason"],
    res.get("reason", ""),
)

# ── 5. max_position_percent_of_portfolio ─────────────────────────────────────
# qty 50 × 180 = $9,000 notional; equity $10,000 → 90% > cap 10%.
res = run_gate(
    _base_order(qty=50, limit_price=180.0),
    _base_params(max_position_percent_of_portfolio=10),
    account_state={"equity": 10_000},
)
check(
    "notional pct over max_position_percent_of_portfolio → rejected",
    not res["approved"] and "max_position_percent_of_portfolio" in res["reason"],
    res.get("reason", ""),
)

# ── 6. max_daily_loss_usd ────────────────────────────────────────────────────
# today's P&L -$250 ≤ -max_daily_loss 200 → blocked.
res = run_gate(
    _base_order(),
    _base_params(max_daily_loss_usd=200),
    account_state={"equity": 100_000, "todays_pnl": -250.0},
)
check(
    "today's P&L past max_daily_loss_usd → rejected (no new positions)",
    not res["approved"] and "max_daily_loss_usd" in res["reason"],
    res.get("reason", ""),
)

# ── 7. max_day_trades (PDT) ──────────────────────────────────────────────────
res = run_gate(
    _base_order(),
    _base_params(max_day_trades=3),
    account_state={"equity": 100_000, "daytrade_count": 3},
)
check(
    "daytrade_count at max_day_trades → rejected (PDT risk)",
    not res["approved"] and "max_day_trades" in res["reason"],
    res.get("reason", ""),
)

# ── 8. require_stop_loss ─────────────────────────────────────────────────────
# A market order with NO stop of any kind, require_stop_loss on.
naked = {"ticker": "NVDA", "side": "buy", "qty": 10, "order_type": "market"}
res = run_gate(naked, _base_params(require_stop_loss=True), account_state={"equity": 100_000})
check(
    "require_stop_loss=true + naked order (no stop) → rejected",
    not res["approved"] and "require_stop_loss" in res["reason"],
    res.get("reason", ""),
)
# ...and a bracket order satisfies require_stop_loss (the stop is structural).
bracket = {"ticker": "NVDA", "side": "buy", "qty": 10, "order_class": "bracket",
           "order_type": "limit", "limit_price": 180.0}
res = run_gate(bracket, _base_params(require_stop_loss=True), account_state={"equity": 100_000})
check(
    "require_stop_loss=true + bracket order → approved (stop is structural)",
    res["approved"],
    res.get("reason", ""),
)

# ── 9. missing ticker ────────────────────────────────────────────────────────
res = run_gate({"side": "buy", "qty": 10}, _base_params())
check(
    "order with no ticker → rejected (missing ticker)",
    not res["approved"] and "missing ticker" in res["reason"],
    res.get("reason", ""),
)

# ── 10. mode fork: autonomous + no params → fail closed ──────────────────────
res = run_gate(_base_order(), risk_params=None, mode="autonomous")
check(
    "autonomous + no risk params → REJECTED (fail closed)",
    not res["approved"] and "No risk parameters" in res["reason"],
    res.get("reason", ""),
)

# ── 11. mode fork: supervised + no params → approve with warning ─────────────
res = run_gate(_base_order(), risk_params=None, mode="supervised")
check(
    "supervised + no risk params → APPROVED with warning (preserves manual flow)",
    res["approved"] and any("Risk parameters not set" in w for w in res.get("warnings", [])),
    f"approved={res['approved']} warnings={res.get('warnings')}",
)

# ── 12. multiple violations accumulate into one reason ───────────────────────
# Oversized qty AND blocked ticker AND naked-but-required-stop, all at once.
res = run_gate(
    {"ticker": "GME", "side": "buy", "qty": 999, "order_type": "market"},
    _base_params(max_order_size_shares=100, blocked_tickers=["GME"], require_stop_loss=True),
    account_state={"equity": 100_000},
)
check(
    "multiple violations → single rejection naming all of them",
    not res["approved"]
    and "blocked_tickers" in res["reason"]
    and "max_order_size_shares" in res["reason"]
    and "require_stop_loss" in res["reason"],
    res.get("reason", ""),
)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
