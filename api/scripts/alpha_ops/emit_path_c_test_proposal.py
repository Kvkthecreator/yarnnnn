#!/usr/bin/env python3
"""
Path C: Autonomous Reviewer-approval validation for alpha-trader-1.

Path B confirmed the execution chain works under operator-click-Approve.
Path C tests the autonomous path: AUTONOMY.md eligibility → AI Reviewer
(Sonnet) → auto-approve → handle_execute_proposal → Alpaca paper order.

Prerequisites validated by author_autonomy_for_path_c.py:
  - AUTONOMY.md written in parser-compatible schema (trading: level=bounded_autonomous,
    ceiling_cents=200000)
  - is_eligible_for_auto_approve returns (True, ...) for $715 reversible
    submit_order

This script emits a small REVERSIBLE SPY buy with full Simons-style 6-check
rationale so the AI Reviewer's persona reasoning has substrate to evaluate.
The proposal must be marked reversible (which paper money effectively is)
because the autonomy gate's reversibility check defers irreversibles
unconditionally.

Pass signal:
  - action_proposals.status='executed'
  - reviewer_identity='ai:reviewer-sonnet-v5' (NOT 'human:...')
  - execution_result.id is an Alpaca order UUID
  - /workspace/review/decisions.md has new entry attributed to ai:reviewer-sonnet-v5

Defer signal (correct behavior, NOT a failure of the system):
  - reviewer_identity='ai:reviewer-sonnet-v5' but verdict='defer'
  - Reasoning cites empty _performance.md / thin track record (Check 4
    narrowing per ADR-217 D4)
  - Proposal stays pending, awaits human click

Fail signal (system bug):
  - No reviewer_identity stamped (eligibility filter rejected unexpectedly)
  - or 'reviewer-layer:observed' (observe-only fallback fired despite
    eligibility passing in the dry-run)

Usage:
    python -m api.scripts.alpha_ops.emit_path_c_test_proposal alpha-trader
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


# Path C proposal: 1 SPY share, REVERSIBLE, with Simons-style 6-check
# rationale. Sized at ~$715 — well under the $2,000 AUTONOMY ceiling.
TEST_PROPOSAL = {
    "action_type": "trading.submit_order",
    # Reversibility: paper money has no real loss exposure, and the order
    # itself can be unwound by a market sell. Marking reversible is
    # operationally honest for paper validation.
    "reversibility": "reversible",
    "task_slug": "trade-proposal",
    "agent_slug": "analyst",
    "inputs": {
        "ticker": "SPY",
        "side": "buy",
        "qty": 1,
        "order_type": "limit",
        "limit_price": 715.00,
        "time_in_force": "day",
    },
    "rationale": (
        "Path C autonomous-Reviewer validation test (2026-04-28).\n\n"
        "This proposal exercises the AUTONOMY.md → AI Reviewer auto-approve\n"
        "→ Alpaca paper execution path. Sized within the $2K autonomy\n"
        "ceiling for paper-validation phase.\n\n"
        "## Simons six-check framing (for the AI Reviewer's reasoning)\n\n"
        "Check 1 — Signal attribution: This is a Path C VALIDATION test,\n"
        "not a real signal-driven proposal. _operator_profile.md declares\n"
        "5 signals (IH-1..IH-5); none fired this cycle. Reviewer should\n"
        "weight this as 'system test, low stakes' rather than 'genuine\n"
        "trading conviction'.\n\n"
        "Check 2 — Signal rule compliance: N/A (no signal). The proposal\n"
        "is a tiny SPY long for system validation; SPY is in the declared\n"
        "universe; sizing is within risk constraints.\n\n"
        "Check 3 — Risk-limit compliance:\n"
        "  Position size: 1 × $715 = $715 (well under any cap)\n"
        "  Per-trade risk: ~0.7% of $94 effective balance — actually high\n"
        "    in % terms because YARNNN balance is small, but irrelevant to\n"
        "    paper account ($25K paper buying power)\n"
        "  Sector concentration: SPY = broad-market, low concentration\n"
        "  Open positions: 0 (after Path B SPY trade is reconciled, may\n"
        "    show 1 — confirm fresh state)\n"
        "  Day-trade: no, hold N/A — this is a validation order\n\n"
        "Check 4 — Signal expectancy: N/A (no signal, no _performance.md\n"
        "track record). The Reviewer is being asked to approve a system\n"
        "test, not a thesis-driven trade. Per ADR-217 D4, Check 4 may\n"
        "narrow autonomy when track record is thin — but the operator's\n"
        "explicit AUTONOMY ceiling for paper-validation phase IS the\n"
        "delegation here. Operator authored ceiling_cents=200000 knowing\n"
        "_performance.md is empty.\n\n"
        "Check 5 — Position-sizing math: 1 share, $715 limit, single-leg.\n"
        "No bracket because this is a validation order, not a real entry.\n\n"
        "Check 6 — Portfolio-level diversification: SPY is the broadest\n"
        "possible diversification — no concentration risk.\n\n"
        "## What the operator is asking the Reviewer to validate\n\n"
        "Whether the AUTONOMY.md → eligibility → AI Reviewer → execute\n"
        "chain works end-to-end. If the Reviewer correctly recognizes this\n"
        "as a low-stakes paper-validation order within the operator's\n"
        "explicit delegation ceiling AND approves, the system has closed\n"
        "the loop on autonomous trading capability.\n\n"
        "If the Reviewer defers citing empty _performance.md (Check 4\n"
        "narrowing), that's also a valid Phase B observation: the persona\n"
        "is correctly conservative when track record is thin, but at the\n"
        "cost of never being able to BUILD that track record without\n"
        "human-click bootstrap. That tension is itself worth surfacing.\n"
    ),
    "expected_effect": (
        "Buy 1 SPY share at $715 limit (day order). Total notional $715, "
        "well under $2K AUTONOMY ceiling. Paper account buying power "
        "decreases by notional. No real money at risk. Order may not "
        "fill if SPY > $715 at submission — that's fine, the test is "
        "the approval path, not the fill."
    ),
    "risk_warnings": [
        "Path C validation order — not signal-driven. Reviewer should "
        "treat as system test, not thesis trade."
    ],
    "expires_in_hours": 4,  # Tighter than Path B since AI Reviewer fires immediately
}


async def emit_proposal(user_id: str) -> dict:
    from supabase import create_client
    from services.primitives.propose_action import handle_propose_action

    supabase_url = os.environ.get("SUPABASE_URL") or "https://noxgqcwynkzqabljjyon.supabase.co"
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_key:
        raise SystemExit("SUPABASE_SERVICE_KEY env var required")

    client = create_client(supabase_url, supabase_key)
    auth = SimpleNamespace(client=client, user_id=user_id)

    print(f"Emitting Path C reversible test proposal (1 SPY @ $715 limit) for user {user_id[:8]} ...")
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
        print(f"Proposal {proposal_id} emitted.")
        print(f"on_proposal_created should fire eligibility → AI Reviewer synchronously.")
        print(f"Check action_proposals row in ~10s for reviewer_identity stamping.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
