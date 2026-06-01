"""MCP OAuth login callback — ADR-310 D4 (Auth Piece 2).

Completes the real-login leg of the MCP OAuth flow. The MCP server's
/authorize stores a PENDING auth code (user_id=NULL) and redirects the
operator to the web app to authenticate. After login, the web app calls
GET /api/mcp/oauth-callback (with the operator's JWT) to bind the real
Supabase user onto the pending code and bounce the browser back to the
OAuth client's registered redirect_uri.

Why this route lives on the API service (not the MCP service): the MCP
service authenticates with a service key and never sees operator JWTs. The
API service already validates Supabase JWTs on every route (UserClient), so
the user UUID is established by the operator's own authenticated session —
not from any client-supplied value. The pending code is the only thing the
browser carries across; the user identity comes from the JWT.

No alpha gate (ADR-310 D4 decision): any authenticated yarnnn operator may
bind a pending code against their own workspace.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from mcp.server.auth.provider import construct_redirect_uri
from pydantic import BaseModel

from services.supabase import UserClient, get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPCallbackResponse(BaseModel):
    redirect_url: str


@router.get("/oauth-callback", response_model=MCPCallbackResponse)
async def mcp_oauth_callback(
    auth: UserClient,
    code: str = Query(..., description="Pending MCP auth code from /authorize"),
) -> MCPCallbackResponse:
    """Bind the authenticated operator to a pending MCP auth code, then return
    the OAuth client redirect URL for the browser to navigate to.

    The operator's identity comes from the validated JWT (auth.user_id),
    carried as a Bearer header by the web app's api client — which is why this
    returns JSON rather than a 302 (a top-level browser redirect would not
    carry the JWT). The web handoff page navigates to redirect_url itself. The
    pending code carries the OAuth client's redirect_uri + state, round-tripped
    exactly. Uses the service client for the bind write because the
    mcp_oauth_* tables are service-scoped (same as the MCP server).
    """
    svc = get_service_client()

    result = (
        svc.table("mcp_oauth_codes")
        .select("*")
        .eq("code", code)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Unknown or expired authorization request.")

    row = result.data[0]

    # Expiry check — mirrors load_authorization_code.
    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        svc.table("mcp_oauth_codes").delete().eq("code", code).execute()
        raise HTTPException(status_code=410, detail="Authorization request expired. Please retry the connection.")

    # Idempotency / replay guard: if already bound, only the original binder
    # may re-complete (e.g. a double-submit). A different user must not be able
    # to re-bind someone else's pending code.
    existing_user = row.get("user_id")
    if existing_user and existing_user != auth.user_id:
        logger.warning(
            "[MCP OAuth] callback user %s != already-bound %s for code; refusing rebind",
            auth.user_id[:8], str(existing_user)[:8],
        )
        raise HTTPException(status_code=409, detail="This authorization request is already bound to another account.")

    # Bind the real operator onto the pending code.
    if not existing_user:
        svc.table("mcp_oauth_codes").update({"user_id": auth.user_id}).eq("code", code).execute()
        logger.info(
            "[MCP OAuth] Bound user %s to auth code, client %s",
            auth.user_id[:8], row.get("client_id"),
        )

    # Build the OAuth client redirect target (code + original state). The web
    # handoff page navigates the browser here.
    redirect_uri = row["redirect_uri"]
    state = row.get("state")
    target = construct_redirect_uri(redirect_uri, code=code, state=state)
    return MCPCallbackResponse(redirect_url=target)
