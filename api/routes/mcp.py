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


class ConsentTier(BaseModel):
    """One grantable tier on the consent screen (ADR-563 am.1)."""
    scope: str
    label: str
    # What this tier permits, from the same table `assert_scope` enforces.
    grants: list[str]


class MCPConsentInfo(BaseModel):
    """What the operator is being asked to approve — shown on the consent screen
    BEFORE any bind write. Read-only; carries no capability.

    Answers the three questions a consent screen must answer, which this one did
    not until 2026-08-17: **who am I approving as** (`account_email`), **what
    will it reach** (`workspace_name`), and **what may it do** (`tiers` — the
    operator picks one, ADR-563 am.1).

    Before, it showed only the client and its redirect host, and the FE printed a
    FIXED sentence — "read and write your memory" — that was wrong in both
    directions: 'memory' is pre-ADR-512 vocabulary (the unit of interop is the
    FILE), and a legacy `read` token can also DELETE and mint member-grant share
    links. ADR-563 made the tiers real; this makes them visible, which is the
    half that was still owed.
    """
    client_name: Optional[str]
    client_id: str
    redirect_host: str
    # WHO — the account this connection would be bound to. The bind takes its
    # identity from the JWT, so on a shared browser (or a second Google account)
    # the operator could previously approve as someone they did not intend.
    account_email: Optional[str]
    # WHERE — the workspace this connection will reach. `None` while the
    # workspace still wears the mint default name (`display_workspace_name`), so
    # the FE can say "your workspace" rather than leak "My Workspace".
    # This is the DEFAULT the binding resolves to when the operator does not
    # choose, computed through the SAME resolver the connector itself will use —
    # so the screen cannot promise one workspace while the token reaches another.
    # The operator CAN override it: ADR-573 (built 2026-08-17, `ec58956`) put a
    # picker on the consent screen and a validated `workspace_id` on the bind.
    # Do not re-describe that as deferred. This comment previously asserted the
    # opposite for three days after the picker shipped, and a 2026-08-20
    # connector audit read it as the live contract and concluded the picker was
    # missing. Gate: `test_adr573_no_stale_deferral_claims.py`.
    workspace_name: Optional[str]
    workspace_id: Optional[str]
    # WHAT — the operator CHOOSES it (ADR-563 am.1). Each tier carries its own
    # sentences from the enforcement table; `default_scope` is preselected. The
    # client's requested scope is not shown as the grant because it does not
    # decide it: ChatGPT asks for whatever it registered with and Claude asks
    # for nothing, so describing the request described an accident.
    tiers: list[ConsentTier]
    default_scope: str


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

    # WHERE this connection will land. Resolved through the SAME function the
    # connector's own auth uses (ADR-373 D6's `resolve_mcp_workspace` wraps it),
    # so the screen cannot promise one workspace while the token reaches
    # another — the display/gate divergence ADR-501 D1 named.
    from services.supabase import (
        resolve_workspace_for_principal,
        display_workspace_name,
    )

    workspace_id = None
    workspace_name = None
    try:
        workspace_id = resolve_workspace_for_principal(auth.user_id)
        if workspace_id:
            ws = (
                svc.table("workspaces")
                .select("name")
                .eq("id", workspace_id)
                .limit(1)
                .execute()
            )
            if ws.data:
                workspace_name = display_workspace_name(ws.data[0].get("name"))
    except Exception as exc:  # pragma: no cover — description must not fail
        # Best-effort, matching `resolve_mcp_workspace`'s own posture: a
        # resolution failure degrades to "your workspace" rather than blocking
        # the operator from connecting at all.
        logger.warning("[MCP consent] workspace resolve failed: %s", exc)

    # WHAT it may do — the operator's choice among the grantable tiers.
    from services.mcp_scopes import consent_tiers, DEFAULT_GRANT

    return MCPConsentInfo(
        client_name=client_name,
        client_id=row.get("client_id"),
        redirect_host=redirect_host,
        account_email=auth.email,
        workspace_name=workspace_name,
        workspace_id=workspace_id,
        tiers=[ConsentTier(**t) for t in consent_tiers()],
        default_scope=DEFAULT_GRANT,
    )


@router.post("/oauth-callback", response_model=MCPCallbackResponse)
async def mcp_oauth_callback(
    auth: UserClient,
    code: str = Query(..., description="Pending MCP auth code from /authorize"),
    workspace_id: Optional[str] = Query(
        None,
        description=(
            "ADR-573: the workspace to bind this connection to. Must be one the "
            "operator reaches. Omitted → the principal's default (ADR-373 D6)."
        ),
    ),
    scope: Optional[str] = Query(
        None,
        description=(
            "ADR-563 am.1: the tier the operator granted — one of the grantable "
            "tiers. Omitted → the tier the consent screen preselects."
        ),
    ),
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

    # ADR-563 am.1: the granted tier. Only a grantable tier binds — the legacy
    # full-access `read` is honoured on old tokens and never minted.
    from services.mcp_scopes import GRANTABLE_TIERS, DEFAULT_GRANT

    granted = scope or DEFAULT_GRANT
    if granted not in GRANTABLE_TIERS:
        raise HTTPException(status_code=400, detail="Unknown permission level.")

    # ADR-573: the chosen workspace, validated against the operator's REACH.
    # Fail closed — a workspace the operator cannot reach is a 403, never a
    # silent fall back to their default. Silently substituting a different
    # workspace than the one addressed is precisely the incorrect-success
    # ADR-373 D6 was built to end; doing it at the consent door would put it
    # straight back, with the operator believing they chose.
    bound_workspace: Optional[str] = None
    if workspace_id:
        from services.supabase import ReachUndecidable, principal_reaches_workspace

        try:
            reaches = principal_reaches_workspace(auth.user_id, workspace_id)
        except ReachUndecidable as exc:
            # The lookup broke; reach is UNKNOWN. Refuse the bind (fail-closed)
            # but never as "you do not have access" — that is a claim about the
            # operator's grant we are in no position to make.
            logger.error(
                "[ADR-573] reach undecidable for %s→%s — refusing bind: %s",
                auth.user_id[:8], workspace_id[:8], exc,
            )
            raise HTTPException(
                status_code=503,
                detail="Could not verify your access just now. Please try again.",
            ) from exc
        if not reaches:
            logger.warning(
                "[ADR-573] user %s cannot reach workspace %s — refusing bind",
                auth.user_id[:8], workspace_id[:8],
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have access to that workspace.",
            )
        bound_workspace = workspace_id

    # Bind the real operator onto the pending code (consent granted).
    if not existing_user:
        # The bind is the ONE writer of the code's scope (ADR-563 am.1).
        update = {"user_id": auth.user_id, "scope": granted}
        # Only written when chosen: leaving it NULL means "resolve the
        # principal's default", which is the pre-573 behaviour every existing
        # connector already has.
        if bound_workspace:
            update["workspace_id"] = bound_workspace
        svc.table("mcp_oauth_codes").update(update).eq("code", code).execute()
        logger.info(
            "[MCP OAuth] Bound user %s to auth code, client %s, workspace %s, scope %s (consent)",
            auth.user_id[:8], row.get("client_id"),
            (bound_workspace or "(default)")[:8], granted,
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
