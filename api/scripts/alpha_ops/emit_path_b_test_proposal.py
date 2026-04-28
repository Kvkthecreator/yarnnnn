#!/usr/bin/env python3
"""
Path B: Execution-chain isolation test for alpha-trader-1 (seulkim88).

Emits a tiny SPY paper proposal (1 share, market order) via handle_propose_action
so the operator can click Approve in cockpit Queue. Validates the entire chain
from propose_action → on_proposal_created (likely observe-only here, since
AUTONOMY.md schema mismatch + irreversibility rule defer auto-approval) →
operator-click-Approve → handle_execute_proposal → _handle_trading_tool →
risk_gate → alpaca_client.submit_order → Alpaca paper account.

Why this exists
---------------
The autonomous loop (Tracker → signal-eval → propose_action → Reviewer auto-
approve → execute) has multiple architectural gates that we want to validate
INDEPENDENTLY before relying on them in concert. This script bypasses Tracker
+ signal-eval + AI Reviewer auto-approve, and tests just the execution chain
under operator-click-Approve.

Pass signal: action_proposals.status='executed', execution_result.id is an
Alpaca order UUID, paper portfolio reflects the fill.

Fail signal: tells you which gate (risk_gate / Alpaca 4xx / field-name
mismatch) needs fixing before paper orders work end-to-end.

Usage
-----
    python -m api.scripts.alpha_ops.emit_path_b_test_proposal alpha-trader

Then ask the operator to open cockpit /work or /review and click Approve on
the new pending proposal.
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

_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from _shared import load_registry  # noqa: E402


# Tiny market-buy of 1 SPY share. Total notional ~$715 (well within paper
# account buying power). Field schema matches platform_tools._handle_trading_tool
# requirements (ticker, side, qty, order_type) — NOT the symbol/type schema
# the seed_seulkim_test_data.py script used (which would fail at the handler's
# field check).
TEST_PROPOSAL = {
    "action_type": "trading.submit_order",
    "reversibility": "irreversible",  # Honest — once filled, reversal requires a sell order
    "task_slug": "trade-proposal",
    "agent_slug": "analyst",
    "inputs": {
        "ticker": "SPY",
        "side": "buy",
        "qty": 1,
        "order_type": "market",
        "time_in_force": "day",
    },
    "rationale": (
        "Path B execution-chain validation test (2026-04-28).\n\n"
        "This is NOT a real signal-driven order. It's a tiny SPY market-buy "
        "to validate that handle_execute_proposal → _handle_trading_tool → "
        "risk_gate → alpaca_client.submit_order works end-to-end on the "
        "alpha-trader-1 paper account.\n\n"
        "Operator: click Approve in cockpit to execute. The order will land "
        "in the alpaca paper account (suffix X4DJ) at next-RTH-open if "
        "submitted outside hours.\n\n"
        "Pass: action_proposals.status='executed', execution_result.id is "
        "an Alpaca order UUID. Fail: rejected_at_execution with a specific "
        "reason — that's the gate to fix before relying on the autonomous "
        "loop for real paper orders."
    ),
    "expected_effect": (
        "Buy 1 SPY share at market. Total notional ~$715. Paper account "
        "buying power decreases by notional. No real money at risk."
    ),
    "risk_warnings": [
        "Test proposal — not driven by a fired signal. "
        "Operator approval is the validation point, not the trade thesis."
    ],
    "expires_in_hours": 24,  # Plenty of time for operator to click during business hours
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

    print(f"Emitting Path B test proposal (1 SPY share, market) for user {user_id[:8]} ...")
    result = await handle_propose_action(auth, TEST_PROPOSAL)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("persona", help="Persona slug", default="alpha-trader", nargs="?")
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

    proposal_id = result.get("proposal_id") or result.get("proposal", {}).get("id")
    if proposal_id:
        print(f"Next step: operator clicks Approve on proposal {proposal_id} in cockpit.")
        print(f"  cockpit URL: https://yarnnn.com/work")
        print(f"  or /review (if the FE surfaces proposals there)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
