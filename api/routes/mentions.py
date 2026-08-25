"""Mentions routes — the viewer's To-do second source (ADR-605; ADR-492 D3).

`GET /api/mentions` is a per-viewer DERIVATION over the conversation
substrate (cast membership ∩ visibility window ∩ the write-time mention
stamp) — no inbox table exists or may exist. `POST /api/mentions/resolve`
advances the viewer's per-conversation resolution cursor
(`member_state['mention_resolutions']` — presentation state, the ADR-407
cursor precedent, never authorization). Two facts stay distinct (ADR-492
§7): the bell's BADGE keys on the attention cursor; membership in this
list keys on RESOLUTION, so a mention never silently clears by scroll-by.

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


class ResolveMentionRequest(BaseModel):
    conversation_id: str
    sequence: int

    class Config:
        extra = "forbid"


@router.post("/mentions/resolve")
async def resolve_mention(payload: ResolveMentionRequest, auth: UserClient) -> dict:
    """Mark mentions in one conversation dealt-with up to a sequence.

    Monotonic — resolving an older mention never un-resolves a newer act.
    """
    ws, principal = _scope(auth)
    try:
        from services.mentions import resolve_mentions_up_to

        resolve_mentions_up_to(ws, principal, payload.conversation_id, payload.sequence)
        return {"resolved": True}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("[MENTIONS] resolve failed: %s", e)
        raise HTTPException(status_code=500, detail="mention resolve failed")
