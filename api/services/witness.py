"""After-witness emission — ADR-405 D3/D5, operationalized (ADR-407 Phase 2).

A notification is the witness dial's "after" setting: when a consequential act
binds (or a proposal awaits/receives a decision), the workspace's accountable
principals are TOLD. Who is told is DERIVED at emission time from the grant
roster — the workspace's active HUMAN principals (owner + members), minus the
actor (self-witness is trivially satisfied, ADR-405 D4). Never stored as a
subscription matrix (DP29); the `notifications` table stays the transport
record only.

Scope honesty (ADR-405 §3): the in-app transport lands here; per-member
email/push fan-out is the deferred transport-scaling follow-on. Foreign-LLM /
agent principals are not notification recipients — their witness surface is
the substrate itself (they read ledgers on their next call).

N=1 byte-identity: with one human in the workspace, witnesses-minus-actor is
empty and emission is a no-op — nothing changes for the existing population.
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
    """Tell the workspace's witnesses (minus the actor) that an act happened.

    In-app transport per recipient (one notifications row each — the ADR-405
    D3 pointer, not a second source of truth). Best-effort: emission failure
    never fails the act. Returns the number of recipients reached.
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

    if not witnesses:
        return 0

    from services.notifications import send_notification

    reached = 0
    for uid in witnesses:
        try:
            await send_notification(
                client,
                uid,
                message,
                channel="in_app",
                urgency=urgency,  # type: ignore[arg-type]
                context=context,
                source_type=source_type,  # type: ignore[arg-type]
                source_id=source_id,
            )
            reached += 1
        except Exception as e:
            logger.warning("[WITNESS] emission to %s failed: %s", uid[:8], e)
    return reached
