"""
One-shot harness to emit a test trading proposal against a persona
workspace, exercising the Reviewer dispatch path end-to-end.

Usage:
    .venv/bin/python api/scripts/alpha_ops/emit_test_proposal.py alpha-trader

What it does:
  1. Constructs a realistic Signal 2 (Mean-reversion-oversold) proposal
     on NVDA — shape matches the playbook §3A.2 signal rules + §3A.3
     risk rules + recent_20_trade_expectancy above the -0.5R guardrail
     so the Reviewer's six-check chain should APPROVE.
  2. Inserts an action_proposals row via the same handle_propose_action
     primitive agents call. This triggers on_proposal_created which
     routes through review_proposal_dispatch.py and fires the AI
     Reviewer (Simons persona per ADR-216 Commit 2) when modes.md
     declares bounded_autonomous.
  3. Prints the returned decision + polls decisions.md for the
     persona-aware reasoning entry.

This is an E2E instrumentation script for ADR-216 Commit 5 validation.
Not called in normal operation — agents emit proposals themselves.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

# Add api/ to path for services imports
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from _shared import load_registry  # noqa: E402


# Signal 2 Mean-reversion-oversold on NVDA — hand-authored to pass Reviewer Six Checks
# per playbook §3A.2 rules + §3A.3 risk constraints. Sizing tuned to fit
# max_position_percent_of_portfolio: 15 on a $25K book (ceiling $3,750).
TEST_PROPOSAL = {
    "action_type": "trading.submit_order",
    "reversibility": "reversible",
    "task_slug": "trade-proposal",
    "agent_slug": "analyst",
    "inputs": {
        "ticker": "NVDA",
        "side": "buy",
        "qty": 4,                              # 4 × $847.50 = $3,390 = 13.6% of book (under 15% cap)
        "order_type": "limit",
        "limit_price": 847.50,
        "time_in_force": "day",
        "stop_loss_price": 829.20,             # 1.5× ATR(14) = 18.30 below entry
    },
    "rationale": (
        "Signal 2 (Mean-reversion-oversold) fired on NVDA at 2026-04-24T14:32 EDT.\n\n"
        "Check 1 — Signal attribution: Signal 2 per _operator_profile.md §3A.2.\n\n"
        "Check 2 — Signal rule compliance:\n"
        "  RSI(14) = 23.4 < 25 (PASS)\n"
        "  Price $847.50 within 1.85% of 200-day SMA $832.10 (< 5% quality filter: PASS)\n"
        "  Not in confirmed downtrend: 20-SMA $849.10 > 50-SMA $846.80 (PASS)\n"
        "  NVDA in declared universe (PASS)\n\n"
        "Check 3 — Risk-limit compliance:\n"
        "  Position size: 4 × $847.50 = $3,390 = 13.6% of $25K book (under 15% cap: PASS)\n"
        "  Per-trade risk: 4 × $18.30 stop-distance = $73.20 = 0.29% of book (under 2% cap: PASS)\n"
        "  Sector concentration (Tech after add): 13.6% (under 40% cap: PASS)\n"
        "  Open positions: 1 (under 6 cap: PASS)\n"
        "  Day-trade: no, hold minimum 1 day (PASS)\n\n"
        "Check 4 — Signal expectancy (synthesized — no real _performance.md yet):\n"
        "  Recent 20-trade expectancy: +0.31R (above -0.5R decay guardrail: PASS)\n"
        "  Recent 40-trade Sharpe: +0.68 (above 0.3 retirement threshold: PASS)\n\n"
        "Check 5 — Position-sizing math:\n"
        "  account_equity = $25,000\n"
        "  risk_percent (Signal 2) = 0.75% = $187.50\n"
        "  regime_scalar (VIX = 18.2, below 25 threshold): 1.0\n"
        "  stop_distance = 1.5 × ATR(14) = 1.5 × $12.20 = $18.30\n"
        "  position_size_shares = ($25,000 × 0.0075 × 1.0) / $18.30 = 10.2\n"
        "  Constrained to 4 by per-position 15% ceiling.\n\n"
        "Check 6 — Portfolio-level diversification:\n"
        "  Current open positions: 0 (fresh paper account).\n"
        "  Sector concentration (Tech after add): 13.6%, no stacking (PASS).\n"
    ),
    "expected_effect": (
        "Buy 4 NVDA at $847.50 limit (day order). Stop at $829.20 "
        "(−$73.20 max risk). Target: RSI(14) back to 50 OR $871.90 "
        "(2× ATR above entry), whichever first. Time stop: exit on "
        "day 10 regardless."
    ),
    "risk_warnings": [],
    "expires_in_hours": 4,
}


async def emit_proposal(user_id: str) -> dict:
    """Run handle_propose_action against the persona's service-role client."""
    from supabase import create_client
    from services.primitives.propose_action import handle_propose_action

    supabase_url = os.environ.get("SUPABASE_URL") or "https://noxgqcwynkzqabljjyon.supabase.co"
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_key:
        raise SystemExit("SUPABASE_SERVICE_KEY env var required")

    client = create_client(supabase_url, supabase_key)
    auth = SimpleNamespace(client=client, user_id=user_id)

    print(f"Emitting proposal for user {user_id[:8]} ...")
    result = await handle_propose_action(auth, TEST_PROPOSAL)
    return result


def read_decisions_md(user_id: str) -> str | None:
    """Read /workspace/review/decisions.md for the persona after the fact."""
    import sys
    _alpha_ops = Path(__file__).resolve().parent
    if str(_alpha_ops) not in sys.path:
        sys.path.insert(0, str(_alpha_ops))
    from _shared import pg_connect

    conn = pg_connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT content FROM workspace_files WHERE user_id = %s AND path = %s",
            (user_id, "/workspace/review/decisions.md"),
        )
        row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("persona", help="Persona slug (default: alpha-trader)", default="alpha-trader", nargs="?")
    args = ap.parse_args()

    reg = load_registry()
    persona = reg.require(args.persona)

    print(f"Persona: {persona.slug} ({persona.email})")
    print(f"  user_id: {persona.user_id}")
    print()

    result = asyncio.run(emit_proposal(persona.user_id))
    print()
    print("handle_propose_action result:")
    import json
    print(json.dumps(result, indent=2, default=str))
    print()

    # Give the dispatcher a second to finish its async chain + Sonnet call
    import time
    time.sleep(3)

    decisions = read_decisions_md(persona.user_id)
    if decisions:
        print("=" * 70)
        print("/workspace/review/decisions.md — last ~40 lines")
        print("=" * 70)
        lines = decisions.splitlines()
        for line in lines[-40:]:
            print(line)
    else:
        print("(decisions.md not yet written — Phase 2b dispatcher may not have fired)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
