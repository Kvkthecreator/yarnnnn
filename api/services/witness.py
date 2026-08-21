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
the DP29 shape of mistake. In-app attention is pure derivation (the bell +
Notifications mount the timeline + witness queue).

ADR-489 D4 (2026-07-28), re-cut by ADR-593 D2: the outbound send loop routes
each recipient through the one gated send path
(`services.notifications.send_notification` with kind="decisions") — the
recipient's member_state notification_prefs `email.decisions` dial
('all' | 'high' | 'none', default 'high') decides, so default behavior stays
quiet (the bell remains the canonical after-witness channel; push is opt-in).
Transport rows are workspace-stamped (ADR-407 D8), written only on actual
sends. Still no in_app rows, ever.

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
    """The outbound after-witness transport (ADR-410 D3 seam; ADR-489 D4 send).

    Derives who is told (the roster minus the actor, ADR-405 D5) and routes
    each recipient through the ONE gated send path — email under the
    recipient's `email.decisions` dial (member_state notification_prefs,
    default 'high' → quiet at normal urgency). In-app attention stays pure
    derivation (no in_app rows — ADR-410 D3 preserved). Returns the number
    of recipients an email actually went to. Best-effort: never fails the
    act.
    """
    if not workspace_id:
        return 0
    try:
        witnesses = await workspace_witnesses(
            client, workspace_id, exclude_user_id=actor_user_id
        )
    except Exception as e:  # pragma: no cover — roster derivation is best-effort
        logger.warning("[WITNESS] roster derivation failed: %s", e)
        return 0

    sent = 0
    for recipient in witnesses:
        try:
            from services.notifications import send_notification

            result = await send_notification(
                client,
                recipient,
                message,
                kind="decisions",  # ADR-593 D1 — the witness dial, renamed
                urgency=urgency,  # type: ignore[arg-type]
                context=context,
                source_type=source_type,
                source_id=source_id,
                workspace_id=workspace_id,
            )
            if result.id:
                sent += 1
        except Exception as e:  # pragma: no cover — one recipient never blocks another
            logger.warning("[WITNESS] send failed for %s: %s", recipient[:8], e)
    return sent
