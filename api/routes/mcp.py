"""MCP OAuth login callback — ADR-310 D4 (Auth Piece 2).

Completes the real-login leg of the MCP OAuth flow. The MCP server's
/authorize stores a PENDING auth code (user_id=NULL) and redirects the
operator to the web app to authenticate. After login, the web app calls
GET /api/mcp/oauth-consent (read-only) to describe the requesting client,
shows an explicit approve/deny screen, and only on approval calls
POST /api/mcp/oauth-callback (with the operator's JWT) to bind the real
Supabase user onto the pending code and bounce the browser back to the
OAuth client's registered redirect_uri. (Security 2026-08-01: bind is
POST-on-consent, not auto-bind on page load — closes a forced-consent
account-takeover where opening an attacker's ?code= link silently bound
the victim's account to the attacker's client.)

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

from typing import Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.supabase import UserClient, get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()


class MCPConsentInfo(BaseModel):
    """What the operator is being asked to approve — shown on the consent screen
    BEFORE any bind write. Read-only; carries no capability."""
    client_name: Optional[str]
    client_id: str
    redirect_host: str


class MCPCallbackResponse(BaseModel):
    redirect_url: str


def _load_pending_code(svc, code: str) -> dict:
    """Fetch + validate a pending code row (existence + expiry). Shared by the
    describe (GET) and consent (POST) legs. Does NOT write."""
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
    expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        svc.table("mcp_oauth_codes").delete().eq("code", code).execute()
        raise HTTPException(status_code=410, detail="Authorization request expired. Please retry the connection.")
    return row


@router.get("/oauth-consent", response_model=MCPConsentInfo)
async def mcp_oauth_consent_info(
    auth: UserClient,
    code: str = Query(..., description="Pending MCP auth code from /authorize"),
) -> MCPConsentInfo:
    """Describe the OAuth client behind a pending code so the operator can make
    an informed approve/deny decision. READ-ONLY — binds nothing.

    Security (2026-08-01): this replaces the old auto-bind on page load. The
    bind write now happens only on the POST /oauth-callback consent leg, so a
    logged-in operator who merely OPENS an attacker-crafted `?code=` link no
    longer silently binds their account to the attacker's client. Requires a
    valid JWT (auth) so an anonymous scan can't enumerate pending clients.
    """
    svc = get_service_client()
    row = _load_pending_code(svc, code)

    # Already bound to someone else → refuse to even describe (no info leak).
    existing_user = row.get("user_id")
    if existing_user and existing_user != auth.user_id:
        raise HTTPException(status_code=409, detail="This authorization request is already bound to another account.")

    client_name = None
    client_row = (
        svc.table("mcp_oauth_clients")
        .select("client_name")
        .eq("client_id", row.get("client_id"))
        .limit(1)
        .execute()
    )
    if client_row.data:
        client_name = client_row.data[0].get("client_name")

    redirect_host = urlsplit(row["redirect_uri"]).netloc or row["redirect_uri"]
    return MCPConsentInfo(
        client_name=client_name,
        client_id=row.get("client_id"),
        redirect_host=redirect_host,
    )


@router.post("/oauth-callback", response_model=MCPCallbackResponse)
async def mcp_oauth_callback(
    auth: UserClient,
    code: str = Query(..., description="Pending MCP auth code from /authorize"),
) -> MCPCallbackResponse:
    """Bind the authenticated operator to a pending MCP auth code AFTER explicit
    consent, then return the OAuth client redirect URL for the browser.

    Security (2026-08-01): this is now a POST, invoked only when the operator
    clicks "Approve" on the consent screen — never on page load. The operator's
    identity comes from the validated JWT (auth.user_id), carried as a Bearer
    header — which is why this returns JSON rather than a 302 (a top-level
    browser redirect would not carry the JWT). Uses the service client for the
    bind write because the mcp_oauth_* tables are service-scoped.
    """
    svc = get_service_client()
    row = _load_pending_code(svc, code)

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

    # Bind the real operator onto the pending code (consent granted).
    if not existing_user:
        svc.table("mcp_oauth_codes").update({"user_id": auth.user_id}).eq("code", code).execute()
        logger.info(
            "[MCP OAuth] Bound user %s to auth code, client %s (consent)",
            auth.user_id[:8], row.get("client_id"),
        )

    # Build the OAuth client redirect target (code + original state). The web
    # handoff page navigates the browser here.
    #
    # Deferred deliberately: the `mcp` SDK costs ~600 modules of resident
    # baseline at API boot, and this one helper on the OAuth-callback path is
    # the API service's only use of it. (The MCP SERVER is a separate Render
    # service with its own process — this router only brokers the OAuth
    # handoff.) Import at call time so a boot that never sees a callback never
    # pays for it.
    from mcp.server.auth.provider import construct_redirect_uri

    redirect_uri = row["redirect_uri"]
    state = row.get("state")
    target = construct_redirect_uri(redirect_uri, code=code, state=state)
    return MCPCallbackResponse(redirect_url=target)
