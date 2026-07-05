"""Member-state routes — ADR-407 Phase 3 (the member-experience home).

GET/PUT one principal's first-person state within the acting workspace:
shell/window layout ('shell'), the attention read cursor ('attention'),
notification delivery preferences ('notification_prefs'), drafts.

Scope: (workspace, principal) — the workspace resolves like every other
request (X-Workspace-Id → owner fallback); the principal is the caller.
A member's desktop follows them across devices; each workspace gets its
own desktop. Presentation state only — never consulted for authorization
(ADR-405 D5), never authored substrate (no revision ceremony).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from services.supabase import UserClient
from services.workspace_context import effective_workspace_id

logger = logging.getLogger(__name__)

router = APIRouter()

_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

# Presentation payloads stay small — a window layout is a few KB; anything
# larger is content trying to sneak out of the substrate.
_MAX_VALUE_BYTES = 64 * 1024


def _scope(auth: UserClient) -> tuple[str, str]:
    ws = effective_workspace_id(auth.user_id)
    if not ws:
        raise HTTPException(status_code=403, detail="No acting workspace resolves")
    return ws, auth.user_id


@router.get("/member-state/{key}")
async def get_member_state(key: str, auth: UserClient) -> dict:
    if not _KEY_RE.match(key):
        raise HTTPException(status_code=400, detail="Invalid key")
    ws, principal = _scope(auth)
    try:
        result = (
            auth.client.table("member_state")
            .select("value, updated_at")
            .eq("workspace_id", ws)
            .eq("principal_id", principal)
            .eq("key", key)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if rows:
            return {"key": key, "value": rows[0]["value"], "updated_at": rows[0]["updated_at"]}
        return {"key": key, "value": None, "updated_at": None}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[MEMBER_STATE] get %s failed: %s", key, e)
        raise HTTPException(status_code=500, detail="member_state read failed")


@router.put("/member-state/{key}")
async def put_member_state(key: str, auth: UserClient, value: Any = Body(...)) -> dict:
    if not _KEY_RE.match(key):
        raise HTTPException(status_code=400, detail="Invalid key")
    import json
    if len(json.dumps(value)) > _MAX_VALUE_BYTES:
        raise HTTPException(status_code=413, detail="member_state value too large")
    ws, principal = _scope(auth)
    try:
        auth.client.table("member_state").upsert(
            {
                "workspace_id": ws,
                "principal_id": principal,
                "key": key,
                "value": value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="workspace_id,principal_id,key",
        ).execute()
        return {"key": key, "saved": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("[MEMBER_STATE] put %s failed: %s", key, e)
        raise HTTPException(status_code=500, detail="member_state write failed")
