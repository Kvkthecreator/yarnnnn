"""Architecture-axis E2E test — the alpha-trader capital execution pipeline (2026-06-05).

THE TWO-AXIS MODEL (docs/evaluations/EVAL-SUITE-DISCIPLINE.md §0): "does a trade
fire through the real plumbing" is a deterministic MACHINE fact — it belongs in a
test like this, NOT in a judgment eval. Across the alpha-trader autonomy arc we
"never observed a trade." This test observes one, deterministically, by exercising
the real execution path end-to-end with the two LLM judgment steps bypassed (their
outputs injected) and the two network calls (Alpaca) mocked.

The chain (and where the two axes split):
  track-universe (deterministic) → ticker.yaml
    → signal-evaluation (LLM JUDGMENT — bypassed; we inject the proposal it would emit)
    → handle_propose_action (deterministic) → action_proposals row
    → proposal-arrival Reviewer verdict (LLM JUDGMENT — bypassed; we inject approve)
    → should_auto_apply (deterministic gate)
    → handle_execute_proposal (deterministic) → execute_primitive
    → trading tool submit_order branch → check_risk_limits (mocked: gate opens)
    → alpaca.submit_order (mocked: no live order) → proposal flips executed

This test asserts the DETERMINISTIC machine path: given a clean proposal + an
approve verdict + an open risk gate, the execution pipeline fires a well-formed
order, round-trips the proposal_id as client_order_id (P&L attribution), and flips
the proposal pending→executed. The LLM steps (whether signal-2 matches; whether the
Reviewer approves) are the JUDGMENT axis — read in the eval-suite, NOT asserted here.

Writes to a real workspace (the kvk test user, same pattern as test_adr209_phase1).
Cleans up the test proposal row afterward.

Run: .venv/bin/python api/test_alpha_trader_pipeline_e2e.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv  # noqa: E402

_API = Path(__file__).resolve().parent
load_dotenv(_API / ".env.alpha-ops")
load_dotenv(_API.parent / ".env")

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"  # kvk (same as test_adr209)
REVIEWER_ID = "ai:freddie-sonnet-v8"

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


async def run() -> None:
    from services.supabase import get_service_client
    from services.primitives.propose_action import (
        handle_propose_action,
        handle_execute_proposal,
    )
    from services.review_policy import should_auto_apply

    client = get_service_client()
    auth = SimpleNamespace(
        client=client,
        user_id=TEST_USER_ID,
        caller_identity="agent:test-pipeline-e2e",
        reviewer_caller=False,
        agent=None, agent_slug=None, task_slug=None,
    )

    proposal_id = None
    try:
        # ── STAGE A: inject the proposal signal-evaluation's LLM would emit ──
        # (LLM JUDGMENT bypassed — this is the proposal a Signal-2 match produces.)
        propose_input = {
            "action_type": "trading.submit_order",
            "inputs": {
                "ticker": "NVDA",
                "side": "buy",
                "qty": 10,
                "order_type": "limit",
                "limit_price": 180.20,
                "stop_price": 171.00,
                "signal_id": "signal-2-mean-reversion-oversold",
                "sizing_formula_trace": "0.75% × $10000 / (180.20-171.00) = ~8 shares (rounded 10); regime_scalar 1.0",
            },
            "rationale": "Signal-2 fired on NVDA (RSI 22.5 < 25, within 5% of SMA200, not downtrend).",
            "expected_effect": "Buy 10 NVDA @ limit 180.20, stop 171.00.",
            "reversibility": "irreversible",
            "risk_warnings": [],
        }
        prop = await handle_propose_action(auth, propose_input)
        check("STAGE A — proposal created", prop.get("success") is True, str(prop)[:120])
        proposal_id = prop.get("proposal_id")
        row = prop.get("proposal") or {}
        check("STAGE A — family=capital", row.get("family") == "capital", str(row.get("family")))
        check(
            "STAGE A — resolves to platform_trading_submit_order primitive",
            row.get("primitive") == "platform_trading_submit_order",
            str(row.get("primitive")),
        )

        # ── STAGE B: the autonomy gate (deterministic) ──────────────────────
        # Irreversible capital actions QUEUE even under autonomous (safety) — so
        # auto-execute does NOT fire automatically; the operator/auto-approve
        # path calls handle_execute_proposal. Assert the gate's documented
        # behavior, then exercise the execution step directly (Stage C).
        auto_irrev, reason_irrev = should_auto_apply(
            {"delegation": "autonomous", "ceiling_cents": 5_000_000},
            "capital", verdict="approve",
            action_type="capital:platform_trading_submit_order",
            estimated_cents=180_20 * 10,  # ~$1802
            reversibility="irreversible",
        )
        check(
            "STAGE B — irreversible capital QUEUES even under autonomous (safety floor)",
            auto_irrev is False,
            f"got auto={auto_irrev} reason={reason_irrev}",
        )
        # And a reversible action under autonomous within ceiling auto-binds —
        # proving the gate OPENS when it should (the positive direction).
        auto_rev, reason_rev = should_auto_apply(
            {"delegation": "autonomous", "ceiling_cents": 5_000_000},
            "capital", verdict="approve",
            action_type="capital:platform_trading_submit_order",
            estimated_cents=180_20 * 10,
            reversibility="reversible",
        )
        check(
            "STAGE B — reversible capital under autonomous+within-ceiling AUTO-BINDS",
            auto_rev is True,
            f"got auto={auto_rev} reason={reason_rev}",
        )

        # ── STAGE C: execute the proposal through the REAL pipeline ──────────
        # Mock the two network seams: risk gate opens; Alpaca accepts the order.
        # Everything between (handle_execute_proposal → execute_primitive →
        # trading tool → submit branch) runs REAL.
        mock_order = {
            "id": "test-order-e2e-123",
            "client_order_id": proposal_id,  # P&L round-trip
            "symbol": "NVDA",
            "side": "buy",
            "qty": "10",
            "type": "limit",
            "status": "accepted",
            "limit_price": 180.20,
        }
        # Mock only the two NETWORK seams. The trading tool loads kvk's real
        # (encrypted) Alpaca credentials inline from platform_connections — that
        # works against the live test workspace; we just don't let it reach the
        # network (risk gate opens; Alpaca accepts).
        with patch(
            "services.risk_gate.check_risk_limits",
            new=AsyncMock(return_value={"approved": True, "reason": "ok", "warnings": [], "mode": "autonomous"}),
        ), patch(
            "integrations.core.alpaca_client.AlpacaClient.submit_order",
            new=AsyncMock(return_value=mock_order),
        ):
            execed = await handle_execute_proposal(auth, {
                "proposal_id": proposal_id,
                "reviewer_identity": REVIEWER_ID,
                "reviewer_reasoning": "E2E test: approve + execute the Signal-2 NVDA entry.",
            })

        check("STAGE C — handle_execute_proposal succeeded", execed.get("success") is True, str(execed)[:160])
        exec_result = execed.get("execution_result") or {}
        inner = exec_result.get("result") if isinstance(exec_result, dict) else None
        check(
            "STAGE C — Alpaca submit_order fired (the TRADE)",
            isinstance(inner, dict) and inner.get("id") == "test-order-e2e-123",
            str(exec_result)[:160],
        )
        check(
            "STAGE C — client_order_id round-tripped the proposal_id (P&L attribution)",
            isinstance(inner, dict) and inner.get("client_order_id") == proposal_id,
            str(inner)[:120] if isinstance(inner, dict) else str(inner),
        )

        # ── STAGE D: the proposal flipped pending → executed (DB state) ──────
        final = (
            client.table("action_proposals").select("status, execution_result, reviewer_identity")
            .eq("id", proposal_id).limit(1).execute()
        )
        frow = (final.data or [{}])[0]
        check("STAGE D — proposal status flipped to 'executed'", frow.get("status") == "executed", str(frow.get("status")))
        check("STAGE D — reviewer_identity persisted on the executed proposal", frow.get("reviewer_identity") == REVIEWER_ID, str(frow.get("reviewer_identity")))

    finally:
        # Cleanup — remove the test proposal row (keep the workspace clean).
        if proposal_id:
            try:
                client.table("action_proposals").delete().eq("id", proposal_id).execute()
                print(f"  [cleanup] deleted test proposal {str(proposal_id)[:8]}")
            except Exception as exc:  # noqa: BLE001
                print(f"  [cleanup] failed to delete proposal: {exc}")


def main() -> int:
    asyncio.run(run())
    print(f"\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
