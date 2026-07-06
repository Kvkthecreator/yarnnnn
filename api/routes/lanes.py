"""Lane routes — ADR-411 (implements ADR-408 D6 chat lanes).

A lane is a member's model-pinned helper thread over the shared workspace:
- `GET  /api/lanes`                — enabled flag + model registry + the
                                     member's lanes in the acting workspace
- `POST /api/lanes`                — create a lane (name + model)
- `GET  /api/lanes/{id}/messages`  — lane history (user/assistant text)
- `POST /api/lanes/{id}/messages`  — one turn (non-streaming; ADR-411 D2)
- `POST /api/lanes/{id}/archive`   — archive (the lane list hides it)

Scope: (workspace, principal) like every session post ADR-407 Phase 4 —
a lane is member-experience, never shared. The steward thread is not a
lane and never appears here (ADR-408 D6: no multi-chat at Altitude 1).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient
from services.workspace_context import effective_workspace_id

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_ACTIVE_LANES = 8      # UX bound, not policy (ADR-408 D6)
_MAX_NAME_LEN = 60
_HISTORY_WINDOW = 20       # messages sent to the model per turn
_MAX_MESSAGE_LEN = 32_000


class CreateLaneRequest(BaseModel):
    name: str
    model: str


class LaneTurnRequest(BaseModel):
    content: str


def _acting_workspace(auth: UserClient) -> Optional[str]:
    return effective_workspace_id(auth.user_id)


def _lane_row_to_dict(row: dict) -> dict:
    lane_meta = (row.get("context_metadata") or {}).get("lane") or {}
    return {
        "id": row["id"],
        "name": lane_meta.get("name") or "Lane",
        "model": lane_meta.get("model") or "",
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _get_lane(auth: UserClient, lane_id: str) -> dict:
    """Load one lane row, enforcing (workspace, principal) ownership."""
    res = (
        auth.client.table("chat_sessions")
        .select("id, user_id, workspace_id, status, context_metadata, created_at, updated_at")
        .eq("id", lane_id)
        .eq("session_type", "lane")
        .limit(1)
        .execute()
    )
    row = (res.data or [None])[0]
    if not row or row.get("user_id") != auth.user_id:
        raise HTTPException(status_code=404, detail="Lane not found")
    ws = _acting_workspace(auth)
    if ws and row.get("workspace_id") and row["workspace_id"] != ws:
        raise HTTPException(status_code=404, detail="Lane not found in this workspace")
    return row


@router.get("/lanes")
async def list_lanes(auth: UserClient) -> dict:
    """The lane list + capability envelope. `enabled` gates the FE strip —
    lanes exist only where the ADR-408 D4 router is live."""
    from services.lane_runner import LANE_MODELS
    from services.model_router import model_router_enabled

    enabled = model_router_enabled()
    lanes: list[dict] = []
    if enabled:
        q = (
            auth.client.table("chat_sessions")
            .select("id, user_id, workspace_id, status, context_metadata, created_at, updated_at")
            .eq("user_id", auth.user_id)
            .eq("session_type", "lane")
            .eq("status", "active")
            .order("created_at")
        )
        ws = _acting_workspace(auth)
        if ws:
            q = q.eq("workspace_id", ws)
        lanes = [_lane_row_to_dict(r) for r in (q.execute().data or [])]

    return {
        "enabled": enabled,
        "models": [
            {"id": mid, "label": meta["label"]}
            for mid, meta in LANE_MODELS.items()
        ],
        "lanes": lanes,
    }


@router.post("/lanes")
async def create_lane(req: CreateLaneRequest, auth: UserClient) -> dict:
    from services.lane_runner import LANE_MODELS
    from services.model_router import model_router_enabled

    if not model_router_enabled():
        raise HTTPException(status_code=403, detail="Lanes are not enabled (router off)")
    if req.model not in LANE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown lane model: {req.model}")
    name = (req.name or "").strip()[:_MAX_NAME_LEN]
    if not name:
        raise HTTPException(status_code=422, detail="Lane name required")

    ws = _acting_workspace(auth)
    active = (
        auth.client.table("chat_sessions")
        .select("id", count="exact")
        .eq("user_id", auth.user_id)
        .eq("session_type", "lane")
        .eq("status", "active")
    )
    if ws:
        active = active.eq("workspace_id", ws)
    count = active.execute().count or 0
    if count >= _MAX_ACTIVE_LANES:
        raise HTTPException(
            status_code=409,
            detail=f"Lane limit reached ({_MAX_ACTIVE_LANES}) — archive one first",
        )

    row = {
        "user_id": auth.user_id,
        "session_type": "lane",
        "status": "active",
        "context_metadata": {"lane": {"name": name, "model": req.model}},
    }
    if ws:
        row["workspace_id"] = ws
    res = auth.client.table("chat_sessions").insert(row).execute()
    created = (res.data or [None])[0]
    if not created:
        raise HTTPException(status_code=500, detail="Lane creation failed")
    logger.info("[LANE] created lane=%s model=%s ws=%s", created["id"][:8], req.model, (ws or "-")[:8])
    return _lane_row_to_dict(created)


@router.get("/lanes/{lane_id}/messages")
async def lane_messages(lane_id: str, auth: UserClient) -> dict:
    _get_lane(auth, lane_id)
    res = (
        auth.client.table("session_messages")
        .select("id, role, content, metadata, created_at")
        .eq("session_id", lane_id)
        .order("sequence_number")
        .limit(200)
        .execute()
    )
    return {
        "messages": [
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
                "metadata": r.get("metadata") or {},
            }
            for r in (res.data or [])
            if r.get("role") in ("user", "assistant")
        ]
    }


@router.post("/lanes/{lane_id}/messages")
async def lane_turn(lane_id: str, req: LaneTurnRequest, auth: UserClient) -> dict:
    """One lane turn (ADR-411 D2): persist the member's message, run the
    bounded tool loop on the lane's pinned model, persist + return the reply."""
    from services.lane_runner import lane_caller_identity, run_lane_turn
    from services.narrative import write_narrative_entry

    content = (req.content or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content required")
    if len(content) > _MAX_MESSAGE_LEN:
        raise HTTPException(status_code=422, detail="Message too long")

    lane = _get_lane(auth, lane_id)
    if lane.get("status") != "active":
        raise HTTPException(status_code=409, detail="Lane is archived")
    lane_meta = (lane.get("context_metadata") or {}).get("lane") or {}
    model = lane_meta.get("model") or ""

    # History window: user/assistant text only — tool traffic is per-turn
    # working state, never persisted (the transcript is not shared memory,
    # and it is not the tool ledger either; writes live in revisions).
    hist_res = (
        auth.client.table("session_messages")
        .select("role, content, sequence_number")
        .eq("session_id", lane_id)
        .order("sequence_number", desc=True)
        .limit(_HISTORY_WINDOW)
        .execute()
    )
    history = [
        {"role": r["role"], "content": r["content"] or ""}
        for r in reversed(hist_res.data or [])
        if r.get("role") in ("user", "assistant") and (r.get("content") or "").strip()
    ]

    # Persist the member's message before the LLM call (the turn is real
    # even if the provider errors — same posture as the steward thread).
    write_narrative_entry(
        auth.client, lane_id,
        role="user",
        summary=content,
        pulse="addressed",
        authored_by="operator",
    )

    result = await run_lane_turn(
        auth,
        model=model,
        history=history,
        user_message=content,
        member_label=getattr(auth, "email", None) or None,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=f"Lane turn failed: {result.get('error')}: {result.get('message')}",
        )

    reply = result.get("text") or ""
    write_narrative_entry(
        auth.client, lane_id,
        role="assistant",
        summary=reply or "[no reply]",
        pulse="addressed",
        authored_by=lane_caller_identity(auth.user_id, model),
        extra_metadata={
            "lane_model": model,
            "tools_called": result.get("tools_called") or [],
        },
    )
    # Touch the session's updated_at so lane ordering reflects activity.
    try:
        auth.client.table("chat_sessions").update({"updated_at": "now()"}).eq("id", lane_id).execute()
    except Exception:
        pass

    return {
        "reply": reply,
        "rounds": result.get("rounds"),
        "tools_called": result.get("tools_called") or [],
    }


@router.post("/lanes/{lane_id}/archive")
async def archive_lane(lane_id: str, auth: UserClient) -> dict:
    _get_lane(auth, lane_id)
    auth.client.table("chat_sessions").update({"status": "archived"}).eq("id", lane_id).execute()
    return {"success": True}
