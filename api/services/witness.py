"""After-witness emission — ADR-405 D3/D5 (ADR-407 Phase 2, re-cut by ADR-410 D3).

A notification is the witness dial's "after" setting: when a consequential act
binds (or a proposal awaits/receives a decision), the workspace's accountable
principals are TOLD. Who is told is DERIVED at emission time from the grant
roster — the workspace's active HUMAN principals (owner + members), minus the
actor (self-witness is trivially satisfied, ADR-405 D4). Never stored as a
subscription matrix (DP29).

ADR-410 D3 (2026-07-06): the Phase-2 in_app `notifications` rows are RETIRED.
They were the bridge before the workspace timeline existed (ADR-408 D5.1);
keeping them made a SECOND store of what the attributed ledgers already say —
the DP29 shape of mistake. In-app attention is now pure derivation (the bell +
Notifications mount the timeline + witness queue). This module survives as the
OUTBOUND transport seam: `workspace_witnesses` is the recipient derivation,
and `emit_after_witness` is where email/push fan-out lands when those
transports build (ADR-405 §3) — today it derives recipients and stops.

Foreign-LLM / agent principals are never notification recipients — their
witness surface is the substrate itself (they read ledgers on their next
call).
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_HUMAN_ROLES = ["owner", "member"]


async def workspace_witnesses(
    client, workspace_id: str, exclude_user_id: Optional[str] = None
) -> list[str]:
    """The workspace's accountable human principals (user ids), minus the actor.

    Derived from principal_grants (active, human roles) + the workspaces owner
    row (covers any legacy workspace whose owner grant row predates ADR-386).
    """
    ids: set[str] = set()
    try:
        rows = (
            client.table("principal_grants")
            .select("principal_id, role")
            .eq("workspace_id", workspace_id)
            .eq("status", "active")
            .in_("role", _HUMAN_ROLES)
            .execute()
        )
        ids.update(r["principal_id"] for r in (rows.data or []) if r.get("principal_id"))
    except Exception as e:
        logger.warning("[WITNESS] grant roster read failed for %s: %s", workspace_id, e)

    try:
        ws = (
            client.table("workspaces")
            .select("owner_id")
            .eq("id", workspace_id)
            .limit(1)
            .execute()
        )
        if ws.data and ws.data[0].get("owner_id"):
            ids.add(ws.data[0]["owner_id"])
    except Exception as e:
        logger.warning("[WITNESS] owner read failed for %s: %s", workspace_id, e)

    if exclude_user_id:
        ids.discard(exclude_user_id)
    return sorted(ids)


async def emit_after_witness(
    client,
    *,
    workspace_id: Optional[str],
    actor_user_id: Optional[str],
    message: str,
    context: Optional[dict] = None,
    source_type: str = "system",
    source_id: Optional[str] = None,
    urgency: str = "normal",
) -> int:
    """The outbound after-witness seam (ADR-410 D3).

    Derives who would be told (the roster minus the actor) and returns the
    recipient count. The in_app rows this used to write are RETIRED — in-app
    attention derives from the timeline + witness queue (ADR-410 D1/D5), and
    a stored copy of what the ledgers already say violates DP29. When an
    outbound transport ships (email/push, ADR-405 §3), its per-recipient send
    loop lands HERE, reading each recipient's delivery preferences from
    member_state (ADR-407 D7). Best-effort: never fails the act.
    """
    # Unused until an outbound transport lands — kept in the signature so
    # call sites don't churn when it does.
    _ = (message, context, source_type, source_id, urgency)
    if not workspace_id:
        return 0
    try:
        witnesses = await workspace_witnesses(
            client, workspace_id, exclude_user_id=actor_user_id
        )
    except Exception as e:  # pragma: no cover — roster derivation is best-effort
        logger.warning("[WITNESS] roster derivation failed: %s", e)
        return 0

    # ADR-410 D3: no in_app writes. The outbound send loop will iterate
    # `witnesses` here when email/push transports build.
    return len(witnesses)
