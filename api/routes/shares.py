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

from fastapi import APIRouter, HTTPException, Response
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
    # ADR-465 D3 — the grant shape: "member" (broad, default) | "viewer"
    # (birth-narrowed read-only grant; "just look at this" never over-grants).
    role: str = "member"


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


class WalkEntry(BaseModel):
    """One step of the public attribution walk (ADR-513 D2) — metadata only:
    who, when, what-message. Never revision content, never diffs."""
    authored_by: Optional[str] = None
    when: Optional[str] = None
    change: Optional[str] = None


class SharePreviewResponse(BaseModel):
    workspace_name: Optional[str] = None
    artifact_path: Optional[str] = None
    label: Optional[str] = None
    role: str
    status: str
    # ADR-513: the public projection — the shared artifact + its walk. The
    # response model IS the boundary (D2): additions here are additions to
    # what an anonymous reader can see; keep deliberate.
    artifact_name: Optional[str] = None
    artifact_kind: Optional[str] = None      # "html" | "text"
    artifact_content: Optional[str] = None   # current content only, capped
    truncated: bool = False
    walk: list[WalkEntry] = []


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
            role=body.role,
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

#: ADR-513: the public content cap — generous for prose; a capability link is a
#: view, not an export lane (the git export is the egress door, ADR-510).
PUBLIC_CONTENT_CAP = 400_000
#: The walk is a demonstration, not an archive — the full chain is members-only.
PUBLIC_WALK_CAP = 12


@router.get("/s/{token}", response_model=SharePreviewResponse)
async def preview_share(token: str, response: Response) -> SharePreviewResponse:
    """The PUBLIC artifact view (ADR-513) — no auth: the token is the capability.

    A stranger clicking a share link sees the artifact + its attribution walk
    (who · when · what-message) before any sign-up ask — the moat demonstrated
    on contact (ADR-437 D4, made literal). Accepting (becoming a principal)
    stays auth-gated on the POST below. Lifecycle is enforced here too (D4):
    a revoked or expired link goes dark — this closes the pre-existing hole
    where inactive shares still previewed.

    The anonymous reader is NOT a principal: service-client reads scoped by
    the share's own workspace, projected through the response model (D2 — the
    narrow boundary: no shared_by, no workspace_id, no revision content/diffs,
    no second file).
    """
    from datetime import datetime, timezone

    from services.supabase import get_service_client
    from services.workspace_shares import get_share_by_token

    # Capability links must be neither cached by intermediaries nor indexed;
    # revocation must be the end of them (ADR-513 D4).
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"

    share = get_share_by_token(token)
    if share is None:
        raise HTTPException(status_code=404, detail="Share link not found")
    if share["status"] != "active":
        raise HTTPException(status_code=410, detail=f"This share link is {share['status']}")
    expires = share.get("expires_at")
    if expires and datetime.fromisoformat(str(expires).replace("Z", "+00:00")) < datetime.now(timezone.utc):
        get_service_client().table("workspace_shares").update({"status": "expired"}).eq(
            "id", share["id"]
        ).execute()
        raise HTTPException(status_code=410, detail="This share link has expired")

    out = SharePreviewResponse(
        workspace_name=share.get("workspace_name"),
        artifact_path=share.get("artifact_path"),
        label=share.get("label"),
        role=share["role"],
        status=share["status"],
    )

    artifact_rel = share.get("artifact_path")
    if artifact_rel:
        svc = get_service_client()
        abs_path = artifact_rel if artifact_rel.startswith("/workspace/") \
            else "/workspace/" + artifact_rel.lstrip("/")
        rows = (
            svc.table("workspace_files")
            .select("path, content")
            .eq("workspace_id", share["workspace_id"])
            .eq("path", abs_path)
            .limit(1)
            .execute()
        ).data or []
        if rows:
            content = rows[0].get("content") or ""
            out.truncated = len(content) > PUBLIC_CONTENT_CAP
            out.artifact_content = content[:PUBLIC_CONTENT_CAP]
            leaf = abs_path.rsplit("/", 1)[-1]
            out.artifact_name = share.get("label") or leaf
            out.artifact_kind = "html" if leaf.lower().endswith((".html", ".htm")) else "text"
            walk_rows = (
                svc.table("workspace_file_versions")
                .select("authored_by, created_at, message")
                .eq("workspace_id", share["workspace_id"])
                .eq("path", abs_path)
                .order("created_at", desc=True)
                .limit(PUBLIC_WALK_CAP)
                .execute()
            ).data or []
            out.walk = [
                WalkEntry(
                    authored_by=r.get("authored_by"),
                    when=r.get("created_at"),
                    change=r.get("message"),
                )
                for r in walk_rows
            ]
    return out


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
