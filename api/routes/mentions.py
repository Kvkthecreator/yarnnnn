"""Mentions routes — the viewer's To-do second source (ADR-605; ADR-492 D3).

`GET /api/mentions` is a per-viewer DERIVATION over the conversation
substrate (cast membership ∩ visibility window ∩ the write-time mention
stamp) — no inbox table exists or may exist. `POST /api/mentions/read`
advances the viewer's per-conversation READ cursor
(`member_state['mention_resolutions']` — presentation state, the ADR-407
cursor precedent, never authorization).

ADR-637: ONE cursor decides membership, and VISITING the conversation
advances it (`GET /api/lanes/{id}/messages` calls the same seam). This
endpoint is the second caller — dismissing from the queue without visiting.
It is not the only way out, which is what the pre-637 design made it.

Scope: (workspace, principal) like every member-experience read — the
workspace resolves from the request, the principal is the caller.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient
from services.workspace_context import effective_workspace_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _scope(auth: UserClient) -> tuple:
    ws = effective_workspace_id(auth.user_id, getattr(auth, "workspace_id", None))
    if not ws:
        raise HTTPException(status_code=403, detail="No acting workspace resolves")
    return ws, auth.user_id


@router.get("/mentions")
async def list_my_mentions(auth: UserClient, limit: int = 20) -> dict:
    """Unresolved mentions of the caller in the acting workspace, newest first."""
    ws, principal = _scope(auth)
    try:
        from services.mentions import list_mentions

        return {"mentions": list_mentions(ws, principal, limit=limit)}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("[MENTIONS] list failed: %s", e)
        raise HTTPException(status_code=500, detail="mentions derivation failed")


class MarkReadRequest(BaseModel):
    conversation_id: str
    sequence: int

    class Config:
        extra = "forbid"


@router.post("/mentions/read")
async def mark_mentions_read(payload: MarkReadRequest, auth: UserClient) -> dict:
    """Advance the caller's read cursor for one conversation without visiting.

    Monotonic — marking an older point read never un-reads a newer act.
    """
    ws, principal = _scope(auth)
    try:
        from services.mentions import mark_read_up_to

        mark_read_up_to(ws, principal, payload.conversation_id, payload.sequence)
        return {"read": True}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("[MENTIONS] mark-read failed: %s", e)
        raise HTTPException(status_code=500, detail="mention mark-read failed")
