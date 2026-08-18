"""The bounded derive turn — ONE implementation of the standing lanes'
judgment call (ADR-580 D6).

Three standing lanes revise a living file from fresh source material with one
criterion-governed, tool-less LLM turn: radar (``report.md`` from the watch
signal), Strings (a designated leaf from declared sources), and the connector
derive (a selector digest from ``inbound/{platform}/{selector}/`` raw). Radar
shipped the shape; Strings copied it; a third copy is the drift ADR-580 D6
ends — the turn's MECHANICS live here, and each lane keeps what is genuinely
its own: input assembly, posture, placement, write confinement, and metering
taxonomy.

The turn is deliberately minimal:

  - **No tools, one user message** — a derive is bounded by construction
    (the ADR-394 §103 discipline: derive is never an open loop).
  - **Router-gated**: a disabled router is CONFIGURATION, not a failed
    derive (the ADR-557 D1 radar precedent) — callers meter
    ``router_disabled`` as skipped, never as weather.
  - **The empty answer is honest and first-class**: a lane must never
    manufacture a revision on an unchanged world (the ADR-401 D5 lesson —
    spend follows judgment cadence, not intake chatter).

Callers branch on ``DeriveTurn.status`` and keep their own metering:

    turn = await run_bounded_derive_turn(model=..., system=..., user_msg=...)
    if turn.status == "router_disabled": ...  # meter skipped, reason=config
    if turn.status == "raised":          ...  # meter failed, detail=turn.error
    if turn.status == "no_change":       ...  # meter skipped, honest zero
    text = turn.text                          # status == "ok"
"""

from __future__ import annotations

import logging
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)


def strip_fence(note: str) -> str:
    """Drop a whole-note ``` fence if the model wrapped it despite the contract.

    Pure. Only strips when the note OPENS with a fence and CLOSES with one —
    a fenced code block *inside* the note is content and stays. (Moved verbatim
    from ``services.radar`` by ADR-580 D6; radar re-exports it.)
    """
    s = (note or "").strip()
    if not s.startswith("```"):
        return s
    lines = s.splitlines()
    if len(lines) < 2 or not lines[-1].strip().startswith("```"):
        return s
    return "\n".join(lines[1:-1]).strip()


class DeriveTurn(NamedTuple):
    """One bounded derive turn's outcome. ``status`` is the branch key."""

    status: str                    # "ok" | "no_change" | "router_disabled" | "raised"
    text: str                      # fence-stripped body ("" unless status == "ok")
    ledger_model: Optional[str]    # the model the ledger records (None when no call ran)
    usage: dict                    # token usage kwargs for record_execution_event
    error: Optional[str]           # exception text (status == "raised" only)


async def run_bounded_derive_turn(
    *,
    model: str,
    system: str,
    user_msg: str,
    max_tokens: int,
    timeout: float,
    no_change_tokens: tuple = ("NO_CHANGE",),
) -> DeriveTurn:
    """Run one bounded, tool-less derive turn through the routed transport.

    ``model`` is the ``provider/model`` form (LANE_MODELS / SYSTEM_CALLS
    vocabulary). ``no_change_tokens`` are the exact sentinel bodies the lane's
    posture contracts for an honest empty answer; membership is tested on the
    fence-stripped text. Never raises past its own boundary.
    """
    from services.model_router import model_router_enabled, route_completion

    if not model_router_enabled():
        return DeriveTurn("router_disabled", "", None, {}, None)

    try:
        routed = await route_completion(
            model,
            [{"role": "user", "content": user_msg}],
            system=system,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    except Exception as e:  # noqa: BLE001 — the lane meters, never crashes the tick
        logger.exception("[DERIVE_TURN] completion raised: %s", e)
        return DeriveTurn("raised", "", None, {}, str(e))

    text = strip_fence(routed.text or "")
    if not text or text in tuple(no_change_tokens):
        return DeriveTurn("no_change", "", routed.ledger_model, routed.usage, None)
    return DeriveTurn("ok", text, routed.ledger_model, routed.usage, None)


__all__ = ["DeriveTurn", "run_bounded_derive_turn", "strip_fence"]
