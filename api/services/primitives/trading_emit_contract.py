"""Trading emit-contract validator — propose-time guard (2026-06-19 finding).

Closes the execution gap named in
`docs/evaluations/2026-06-19-execution-emit-contract-gap-FINDING.md`: the
signal-evaluation Reviewer reasons CORRECTLY (sizes the position, names a
stop) but serializes the order into a shape no executor reads — a plain
`submit_order` carrying the stop under the invented key `stop_loss_price`
(executors read `stop_price` for plain / `stop_loss_stop_price` for bracket).
The stop is then invisible to the risk gate, which rejects "no stop" at
EXECUTION time — silently, looking like a judgment failure. The judgment was
fine; the serialization was not.

This validator runs at PROPOSE time (in handle_propose_action), so a
contract-noncompliant trading emit either:
  • is deterministically REPAIRED to the executor's exact schema (the known,
    observed drifts only — never a guess), or
  • fails LOUDLY with an actionable error the next wake can correct,
instead of dying quietly at execution.

DISCIPLINE — this does NOT touch the floor (FOUNDATIONS DP24). It does not
relax any risk rule. It makes the Reviewer's ALREADY-CORRECT stop reach the
gate in the shape the gate reads. A repaired order is exactly as gated as a
hand-perfect one; the gate still rejects it if sizing/var/regime/hours fail.
The single job here is contract-shape fidelity between judgment and execution.

EXECUTOR CONTRACTS (the source of truth — services/platform_tools.py):
  platform_trading_submit_order          requires {ticker, side, qty, order_type}
                                          optional {limit_price, stop_price}
  platform_trading_submit_bracket_order  requires {ticker, side, qty,
                                          take_profit_limit_price,
                                          stop_loss_stop_price}
                                          optional {entry_type, entry_limit_price}
  platform_trading_submit_trailing_stop  requires {ticker, side, qty}
                                          optional {trail_percent, trail_price}
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Required + recognized fields per trading action_type (mirrors the executor
# `tool_input.get(...)` reads in platform_tools.py — keep in lockstep).
_TRADING_CONTRACTS: dict[str, dict[str, Any]] = {
    "trading.submit_order": {
        "required": ("ticker", "side", "qty", "order_type"),
        "optional": ("limit_price", "stop_price", "time_in_force"),
        "stop_field": "stop_price",
    },
    "trading.submit_bracket_order": {
        "required": ("ticker", "side", "qty", "take_profit_limit_price", "stop_loss_stop_price"),
        "optional": ("entry_type", "entry_limit_price", "time_in_force"),
        "stop_field": "stop_loss_stop_price",
    },
    "trading.submit_trailing_stop": {
        "required": ("ticker", "side", "qty"),
        "optional": ("trail_percent", "trail_price", "time_in_force"),
        "stop_field": None,
    },
}

# Known drifted stop-field aliases the model has emitted (observed: kvk
# proposal 9c3e3555 used `stop_loss_price`). Mapped to the bracket stop field
# because a stop-bearing entry must be a bracket to survive require_stop_loss.
_STOP_ALIASES = ("stop_loss_price", "stop_loss", "stop", "sl", "stop_loss_stop")
# Known drifted take-profit aliases.
_TP_ALIASES = ("take_profit_price", "take_profit", "target_price", "tp", "limit_target")
# Known drifted entry-price aliases (plain `limit_price` becomes the bracket
# entry leg when we promote a stop-bearing plain order).
_ENTRY_ALIASES = ("limit_price", "entry_price", "entry")


def _first_present(inputs: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        v = inputs.get(k)
        if v is not None:
            return v
    return None


def validate_and_repair_trading_emit(action_type: str, inputs: dict) -> dict:
    """Validate (and deterministically repair) a trading proposal's emit shape.

    Returns:
        {action_type, inputs, repaired: list[str], error: str | None}

    `error` is non-None when the emit is contract-noncompliant AND not
    repairable from the data present — the proposal should NOT be stored;
    the caller surfaces the error so the next wake re-emits correctly.
    `repaired` lists the deterministic fixes applied (for the audit trail /
    decision_context). Non-trading action_types pass through untouched.
    """
    if action_type not in _TRADING_CONTRACTS:
        return {"action_type": action_type, "inputs": inputs, "repaired": [], "error": None}

    inputs = dict(inputs)  # never mutate the caller's dict
    repaired: list[str] = []

    # ── Repair 1: a stop under a drifted alias ──────────────────────────────
    # If the canonical stop field is absent but a known alias carries a value,
    # the model meant a protected order. Lift the alias to the bracket stop and
    # promote the action to a bracket (a plain submit_order can't carry a stop
    # the gate reads → require_stop_loss would reject it).
    has_canonical_bracket_stop = inputs.get("stop_loss_stop_price") is not None
    has_canonical_plain_stop = inputs.get("stop_price") is not None
    aliased_stop = _first_present(inputs, _STOP_ALIASES)

    if action_type == "trading.submit_order" and (has_canonical_plain_stop or aliased_stop):
        # A plain order with ANY stop → promote to bracket so the stop survives
        # the gate as the SL leg (platform_tools submit_order has no SL leg the
        # broker honors as a protective stop; require_stop_loss wants a bracket).
        stop_val = inputs.get("stop_price") or aliased_stop
        entry_val = _first_present(inputs, _ENTRY_ALIASES)
        tp_val = _first_present(inputs, _TP_ALIASES)
        action_type = "trading.submit_bracket_order"
        repaired.append("promoted submit_order→submit_bracket_order (carried a stop)")
        inputs["stop_loss_stop_price"] = stop_val
        if entry_val is not None and inputs.get("entry_limit_price") is None:
            inputs["entry_limit_price"] = entry_val
            inputs.setdefault("entry_type", "limit")
        if tp_val is not None and inputs.get("take_profit_limit_price") is None:
            inputs["take_profit_limit_price"] = tp_val
        # purge the now-migrated drifted keys
        for k in (*_STOP_ALIASES, "stop_price", *_ENTRY_ALIASES, *_TP_ALIASES):
            inputs.pop(k, None)
    elif action_type == "trading.submit_bracket_order" and not has_canonical_bracket_stop and aliased_stop:
        inputs["stop_loss_stop_price"] = aliased_stop
        for k in _STOP_ALIASES:
            inputs.pop(k, None)
        repaired.append(f"renamed drifted stop alias → stop_loss_stop_price")

    # ── Repair 2: a take-profit under a drifted alias (bracket only) ────────
    if action_type == "trading.submit_bracket_order" and inputs.get("take_profit_limit_price") is None:
        tp_val = _first_present(inputs, _TP_ALIASES)
        if tp_val is not None:
            inputs["take_profit_limit_price"] = tp_val
            for k in _TP_ALIASES:
                inputs.pop(k, None)
            repaired.append("renamed drifted take-profit alias → take_profit_limit_price")

    # ── Repair 3: a bracket entry under a drifted alias ─────────────────────
    if action_type == "trading.submit_bracket_order" and inputs.get("entry_limit_price") is None:
        entry_val = _first_present(inputs, _ENTRY_ALIASES)
        if entry_val is not None:
            inputs["entry_limit_price"] = entry_val
            inputs.setdefault("entry_type", "limit")
            for k in _ENTRY_ALIASES:
                inputs.pop(k, None)
            repaired.append("renamed drifted entry alias → entry_limit_price")

    # ── Validate against the (possibly repaired) contract ───────────────────
    contract = _TRADING_CONTRACTS[action_type]
    missing = [f for f in contract["required"] if inputs.get(f) is None]
    if missing:
        return {
            "action_type": action_type,
            "inputs": inputs,
            "repaired": repaired,
            "error": (
                f"trading_emit_contract: {action_type} is missing required field(s) "
                f"{missing} after repair. The executor "
                f"(platform_{action_type.replace('.', '_')}) requires "
                f"{list(contract['required'])}. Re-emit with the exact schema — "
                f"a stop-bearing entry MUST be trading.submit_bracket_order with "
                f"stop_loss_stop_price + take_profit_limit_price (see the "
                f"signal-evaluation recurrence Step 4 contract)."
            ),
        }

    if repaired:
        logger.info(
            "[TRADING_EMIT_CONTRACT] repaired %s emit: %s",
            action_type, "; ".join(repaired),
        )
    return {"action_type": action_type, "inputs": inputs, "repaired": repaired, "error": None}
