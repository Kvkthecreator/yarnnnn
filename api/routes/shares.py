"""Shared-artifact wedge routes — ADR-437 D4.

The cockpit origin of a share (the "Share" affordance) + the one accept surface
(`/s/{token}`). The MCP `share` verb (the second origin, ADR-437 D4.1) lands in
the MCP server as an additive follow-on; both origins mint the same share row
via `services.workspace_shares` and land here.

Kept OFF `routes/workspace.py` deliberately (that file is heavily co-edited);
a share is its own bounded concern with its own router.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient, principal_reaches_workspace, resolve_owner_workspace_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Models ───────────────────────────────────────────────────────────────────

class ShareCreateRequest(BaseModel):
    # The shared artifact (a workspace_files path). None = a bare workspace
    # share (invite-shaped, no artifact context).
    artifact_path: Optional[str] = None
    label: Optional[str] = None
    ttl_days: Optional[int] = None  # None = a durable link (never expires)


class ShareSummary(BaseModel):
    id: str
    artifact_path: Optional[str] = None
    label: Optional[str] = None
    role: str
    status: str
    created_at: str = ""
    expires_at: Optional[str] = None
    share_link: Optional[str] = None


class ShareListResponse(BaseModel):
    shares: list[ShareSummary]


class SharePreviewResponse(BaseModel):
    workspace_name: Optional[str] = None
    artifact_path: Optional[str] = None
    label: Optional[str] = None
    role: str
    status: str


class ShareAcceptResponse(BaseModel):
    success: bool
    workspace_id: str
    workspace_name: Optional[str] = None
    artifact_path: Optional[str] = None
    role: str


def _acting_workspace(auth: UserClient) -> str:
    """The workspace the caller is acting in (X-Workspace-Id → owner fallback).

    A member may share within a commons they hold a grant to; the owner shares
    their own. `principal_reaches_workspace` is the authority check.
    """
    ws = auth.workspace_id or resolve_owner_workspace_id(auth.user_id)
    if not ws:
        raise HTTPException(status_code=400, detail="No workspace resolved for this principal")
    if not principal_reaches_workspace(auth.user_id, ws):
        raise HTTPException(status_code=403, detail="You do not have a grant to this workspace")
    return ws


# ── Cockpit origin: create / list / revoke ───────────────────────────────────

@router.post("/workspace/shares", response_model=ShareSummary)
async def create_workspace_share(body: ShareCreateRequest, auth: UserClient) -> ShareSummary:
    """Mint a share link for an artifact (ADR-437 D4 — the cockpit origin).

    Any principal with a grant to the workspace may share (a member shares
    within the commons, ADR-408 D1 free-for-all). Accepting the link mints a
    broad member grant (ADR-437 D4.2).
    """
    from services.deep_links import app_url
    from services.workspace_shares import ShareError, create_share

    workspace_id = _acting_workspace(auth)
    try:
        share = create_share(
            workspace_id=workspace_id,
            shared_by=auth.user_id,
            artifact_path=body.artifact_path,
            label=body.label,
            ttl_days=body.ttl_days,
        )
    except ShareError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ShareSummary(
        id=share["id"],
        artifact_path=share.get("artifact_path"),
        label=share.get("label"),
        role=share["role"],
        status=share["status"],
        created_at=str(share.get("created_at") or ""),
        expires_at=share.get("expires_at"),
        share_link=f"{app_url()}/s/{share['token']}",
    )


@router.get("/workspace/shares", response_model=ShareListResponse)
async def list_workspace_shares(auth: UserClient) -> ShareListResponse:
    from services.workspace_shares import list_shares

    workspace_id = _acting_workspace(auth)
    return ShareListResponse(shares=[
        ShareSummary(
            id=r["id"], artifact_path=r.get("artifact_path"), label=r.get("label"),
            role=r["role"], status=r["status"],
            created_at=str(r.get("created_at") or ""),
            expires_at=r.get("expires_at"),
        )
        for r in list_shares(workspace_id)
    ])


@router.post("/workspace/shares/{share_id}/revoke")
async def revoke_workspace_share(share_id: str, auth: UserClient) -> dict:
    from services.workspace_shares import revoke_share

    workspace_id = _acting_workspace(auth)
    if not revoke_share(workspace_id, share_id):
        raise HTTPException(status_code=404, detail="No active share with that id")
    return {"success": True, "id": share_id}


# ── The one accept surface: preview / accept ──────────────────────────────────

@router.get("/s/{token}", response_model=SharePreviewResponse)
async def preview_share(token: str, auth: UserClient) -> SharePreviewResponse:
    """Accept-page preview: workspace name + the shared artifact + state.

    Auth-gated (a principal must be signed in to see + accept), but any
    authenticated principal may preview — the link is not email-locked.
    """
    from services.workspace_shares import get_share_by_token

    share = get_share_by_token(token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share link not found")
    return SharePreviewResponse(
        workspace_name=share.get("workspace_name"),
        artifact_path=share.get("artifact_path"),
        label=share.get("label"),
        role=share["role"],
        status=share["status"],
    )


@router.post("/s/{token}/accept", response_model=ShareAcceptResponse)
async def accept_workspace_share(token: str, auth: UserClient) -> ShareAcceptResponse:
    """Bind the acceptor to the commons via a share link (ADR-437 D4.2).

    Link-based — any authenticated principal may accept (the Figma default).
    Mints a BROAD member grant; the FE binds via X-Workspace-Id on success.
    """
    from services.workspace_shares import ShareError, accept_share

    try:
        result = accept_share(token=token, user_id=auth.user_id)
    except ShareError as e:
        status = {"not_found": 404, "expired": 410, "not_active": 409}.get(e.code, 400)
        raise HTTPException(status_code=status, detail=str(e))
    return ShareAcceptResponse(
        success=True,
        workspace_id=result["workspace_id"],
        workspace_name=result.get("workspace_name"),
        artifact_path=result.get("artifact_path"),
        role=result["role"],
    )
