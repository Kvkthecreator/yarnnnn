"""ADR-294 Phase 2 — Proposal template registry for scenario runner.

A scenario's `emit_proposal: {template: <name>}` resolves a named template
here to a structured `handle_propose_action` payload. Templates are hand-
authored to exercise specific Reviewer decision paths — they pass the
Reviewer's framework checks by construction so we can validate the
auto-execute branch under autonomous mode.

Templates are versioned in this file (committed to repo). Same singular-
implementation discipline applies: don't fork templates across files; if
a new variant is needed, add it here.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

# Signal 2 Mean-reversion-oversold on NVDA — hand-authored to pass the
# Reviewer's six-check chain per alpha-trader playbook §3A.2.
# Identical content to scripts/alpha_ops/emit_test_proposal.py::TEST_PROPOSAL
# — that copy stays for backwards-compat with the alpha-ops harness; new
# scenario callers use this registry.
SIGNAL_2_NVDA: dict[str, Any] = {
    "action_type": "trading.submit_order",
    "reversibility": "reversible",
    "task_slug": "trade-proposal",
    "agent_slug": "analyst",
    "inputs": {
        "ticker": "NVDA",
        "side": "buy",
        "qty": 4,
        "order_type": "limit",
        "limit_price": 847.50,
        "time_in_force": "day",
        "stop_loss_price": 829.20,
    },
    "rationale": (
        "Signal 2 (Mean-reversion-oversold) fired on NVDA.\n\n"
        "Check 1 — Signal attribution: Signal 2 per _operator_profile.md §3A.2.\n\n"
        "Check 2 — Signal rule compliance:\n"
        "  RSI(14) = 23.4 < 25 (PASS)\n"
        "  Price $847.50 within 1.85% of 200-day SMA $832.10 (PASS)\n"
        "  Not in confirmed downtrend: 20-SMA > 50-SMA (PASS)\n"
        "  NVDA in declared universe (PASS)\n\n"
        "Check 3 — Risk-limit compliance:\n"
        "  Position size: 4 × $847.50 = $3,390 = 13.6% of $25K book (PASS)\n"
        "  Per-trade risk: 4 × $18.30 stop-distance = $73.20 = 0.29% of book (PASS)\n"
        "  Sector concentration (Tech after add): 13.6% (PASS)\n"
        "  Open positions: 0 (under 6 cap: PASS)\n\n"
        "Check 4 — Signal expectancy (read from _money_truth.md):\n"
        "  Recent 30d expectancy: +0.31R (above -0.5R decay: PASS)\n"
        "  Recent 30d Sharpe: +0.68 (above 0.3 retirement: PASS)\n\n"
        "Check 5 — Position-sizing math:\n"
        "  account_equity = $25,000\n"
        "  risk_percent (Signal 2) = 0.75% = $187.50\n"
        "  regime_scalar (VIX < 25): 1.0\n"
        "  stop_distance = 1.5 × ATR(14) = $18.30\n"
        "  shares = $187.50 / $18.30 = 10.2 → constrained to 4 by 15% ceiling.\n\n"
        "Check 6 — Portfolio diversification:\n"
        "  Current open positions: 0 (fresh paper account).\n"
    ),
    "expected_effect": (
        "Buy 4 NVDA at $847.50 limit (day order). Stop at $829.20 "
        "(−$73.20 max risk). Target: RSI(14) back to 50 OR $871.90 "
        "(2× ATR above entry), whichever first."
    ),
    "risk_warnings": [],
    "expires_in_hours": 4,
}


TEMPLATES: dict[str, dict[str, Any]] = {
    "signal-2-nvda": SIGNAL_2_NVDA,
}


def get_template(name: str) -> dict[str, Any]:
    """Resolve a template by name. Raises KeyError on unknown."""
    if name not in TEMPLATES:
        raise KeyError(
            f"Unknown proposal template {name!r}. Available: {list(TEMPLATES)}. "
            "Add new templates to services/operator_proxy/proposal_templates.py."
        )
    return dict(TEMPLATES[name])  # defensive copy — caller may mutate
