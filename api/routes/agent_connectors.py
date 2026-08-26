"""Agent connector opt-in routes — ADR-612.

Which of the member's granted connectors a being works against. The store and
the narrowing live in `services/agent_connectors.py`; this is the door.

⭐ NOT an `/agents` router. The pre-ADR-596 agent model's router was deleted
whole (commit 083d25d) and has NO successor verb — authority over a being is
unrepresentable (ADR-460 D3.a). Nothing here edits a being: the opt-in is the
MEMBER's preference about which of THEIR OWN connections a being may work
against, stored per (workspace, principal). The being's row is untouched, and
`AGENT_ROW_KEYS` gains nothing — which is the check that this stayed on the
right side of the cliff.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, HTTPException

from services.supabase import UserClient, get_service_client
from services.workspace_context import effective_workspace_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _scope(auth: UserClient) -> tuple[str, str]:
    ws = effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))
    if not ws:
        raise HTTPException(status_code=403, detail="No acting workspace resolves")
    return ws, auth.user_id


@router.get("/agent-connectors")
async def get_agent_connectors(auth: UserClient) -> dict:
    """Every being's opt-in in this workspace, plus what there is to opt into.

    Serves the GRANT side too (`available`) so the pane never has to guess
    what is connected — the same reason `_beings_payload` serves `desks`
    rather than letting the client rebuild them.
    """
    from services.agent_connectors import read_all
    from services.turn_reach import TURN_REACH_PLATFORMS

    ws, principal = _scope(auth)
    svc = get_service_client()

    connected: list[str] = []
    try:
        rows = (
            svc.table("platform_connections")
            .select("platform, status")
            .eq("user_id", principal)
            .execute()
        ).data or []
        connected = sorted({
            str(r.get("platform") or "").strip().lower()
            for r in rows
            if str(r.get("platform") or "").strip().lower() in TURN_REACH_PLATFORMS
            and str(r.get("status") or "").lower() in ("", "active", "connected")
        })
    except Exception:  # noqa: BLE001 — the opt-in map is still worth serving
        logger.warning("[AGENT_CONNECTORS] connection read failed", exc_info=True)

    return {
        # What a being COULD be scoped to: the reach-capable platforms this
        # member has actually connected. Scoping to something ungranted is
        # meaningless (`allowed_platforms` intersects), so the door does not
        # offer it.
        "available": connected,
        # Per being: the recorded opt-in. A being ABSENT from this map is not
        # scoped — it reaches everything granted (ADR-612 D2). The client must
        # not read absence as "nothing".
        "opt_in": read_all(svc, ws, principal),
    }


@router.put("/agent-connectors/{agent_slug}")
async def put_agent_connectors(
    agent_slug: str,
    auth: UserClient,
    platforms: Optional[list[str]] = Body(default=None, embed=True),
) -> dict:
    """Scope one being, or clear its scoping.

    `platforms: null` CLEARS (back to "not scoped" — everything granted).
    `platforms: []` is a real, different choice: this being reaches nothing.
    The two must stay distinguishable or the member cannot undo a scoping.
    """
    from services.agent_connectors import set_opt_in
    from services.agents_registry import resolve_agent
    from services.turn_reach import TURN_REACH_PLATFORMS

    # The being must EXIST. Fails closed on an unknown slug rather than
    # recording a preference for nobody, which would accumulate silently and
    # read as a working scope.
    if resolve_agent(agent_slug) is None:
        raise HTTPException(status_code=404, detail=f"No agent called '{agent_slug}'.")

    if platforms is not None:
        unknown = [
            p for p in platforms
            if str(p).strip().lower() not in TURN_REACH_PLATFORMS
        ]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Not reach-capable platforms: {sorted(unknown)}",
            )

    ws, principal = _scope(auth)
    try:
        updated = set_opt_in(
            get_service_client(), ws, principal, agent_slug, platforms
        )
    except Exception:  # noqa: BLE001
        logger.warning("[AGENT_CONNECTORS] write failed for %s", agent_slug,
                       exc_info=True)
        raise HTTPException(status_code=500, detail="Could not save that scoping")
    return {"saved": True, "opt_in": updated}
