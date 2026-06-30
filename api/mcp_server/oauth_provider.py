"""
MCP OAuth 2.1 Authorization Server Provider — ADR-075

Implements OAuthAuthorizationServerProvider from the mcp SDK to enable
Claude.ai connectors and ChatGPT developer mode to authenticate via
standard OAuth 2.1 flow.

Flow (ADR-310 D4 — real login, multi-user):
1. Client registers dynamically (POST /register)
2. Client redirects user to /authorize
3. /authorize writes a PENDING auth code (user_id=NULL) and redirects the
   operator to {APP_URL}/mcp/authorize (the web app)
4. Web app authenticates the operator, then calls GET /api/mcp/oauth-callback
   (on the API service, JWT-scoped), which binds the real Supabase user_id
   onto the pending code and bounces back to the client redirect_uri
5. Client exchanges code for access token (POST /token) — a code whose
   user_id is still NULL is rejected, so login is mandatory
6. Client uses access token on /mcp requests; each request resolves its own
   user via the token (mcp_server/auth.py::resolve_request_client)

Token storage: Supabase tables (mcp_oauth_clients, mcp_oauth_codes,
mcp_oauth_access_tokens, mcp_oauth_refresh_tokens).
"""

import os
import json
import time
import secrets
import hashlib
import base64
import logging
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode, quote

from pydantic import AnyUrl

from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
    AccessToken,
    RefreshToken,
    OAuthAuthorizationServerProvider,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from services.supabase import get_service_client

logger = logging.getLogger(__name__)

# Token lifetimes
ACCESS_TOKEN_LIFETIME = 3600  # 1 hour
REFRESH_TOKEN_LIFETIME = 30 * 24 * 3600  # 30 days
AUTH_CODE_LIFETIME = 300  # 5 minutes


def _ensure_foreign_llm_grant(user_id: str, client_id: str, granted_by: str) -> None:
    """Auto-provision a foreign-LLM membership grant for an MCP client (ADR-386 D1/D1.a).

    Called from BOTH OAuth token-mint paths — `exchange_authorization_code`
    (first connect, granted_by='system:oauth-connect') and
    `exchange_refresh_token` (silent rotation, granted_by='system:oauth-refresh').
    The connected LLM was ALREADY authorized at the mcp class default by the
    consult (ADR-373); this makes that membership a legible, revocable row
    (principal_id == client_id).

    Idempotent (the partial-unique index makes a steady-state rotation a no-op).
    The refresh site is what HEALS the live population — every connector in
    production authorized before the hook deployed and stays alive via silent
    refresh rotation, so authorize-only never fired for them (D1.a, 2026-06-30).

    Singular Implementation: one helper, two hook sites, so the two paths cannot
    drift. BEST-EFFORT — a grant-ensure failure must NEVER break the OAuth flow:
    the consult still falls back to the class default, so the LLM is not locked
    out.
    """
    try:
        from services.supabase import resolve_owner_workspace_id
        from services.principal_grants import (
            ensure_principal_grant, resolve_provider_id_for_client,
        )

        workspace_id = resolve_owner_workspace_id(user_id)
        if workspace_id:
            # ADR-373 D2.a: the member is the PROVIDER (host-id), not the churning
            # OAuth client_id. Resolve the stable host-id so re-registrations map
            # to ONE grant. Falls back to the client_id when the provider is
            # unknown to the registry (still legible + revocable, just not
            # collapsed across re-registrations).
            provider_id = resolve_provider_id_for_client(client_id) or client_id
            ensure_principal_grant(
                principal_id=provider_id,
                workspace_id=workspace_id,
                role="foreign-llm",
                granted_by=granted_by,
            )
        else:
            logger.debug(
                "[ADR-386] no owner workspace for user %s — skipping grant "
                "auto-provision (LLM still writes via class default).", user_id,
            )
    except Exception as exc:  # pragma: no cover — never break OAuth on this
        logger.warning(
            "[ADR-386] foreign-llm grant auto-provision failed for client %s "
            "(OAuth flow unaffected; consult falls to class default): %s",
            client_id, exc,
        )


class YarnnnAccessToken(AccessToken):
    """Access token with user_id for data scoping."""
    user_id: str


class YarnnnAuthCode(AuthorizationCode):
    """Auth code with user_id."""
    user_id: str


class YarnnnRefreshToken(RefreshToken):
    """Refresh token with user_id."""
    user_id: str


def _get_mcp_user_id() -> str:
    """Get the MCP_USER_ID for auto-approve mode."""
    user_id = os.environ.get("MCP_USER_ID")
    if not user_id:
        raise ValueError("MCP_USER_ID required for auto-approve OAuth")
    return user_id


class YarnnnOAuthProvider(
    OAuthAuthorizationServerProvider[YarnnnAuthCode, YarnnnRefreshToken, YarnnnAccessToken]
):
    """OAuth provider backed by Supabase tables.

    Auto-approves authorization for any request (single-user mode).
    Issues tokens scoped to MCP_USER_ID.
    """

    def _client(self):
        return get_service_client()

    # --- Client Registration ---

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        result = (
            self._client()
            .table("mcp_oauth_clients")
            .select("*")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None

        row = result.data[0]
        return OAuthClientInformationFull(
            client_id=row["client_id"],
            client_secret=row.get("client_secret"),
            redirect_uris=row.get("redirect_uris", []),
            client_name=row.get("client_name"),
            grant_types=row.get("grant_types", ["authorization_code"]),
            response_types=row.get("response_types", ["code"]),
            scope=row.get("scope"),
            token_endpoint_auth_method=row.get("token_endpoint_auth_method", "none"),
        )

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        redirect_uris = [str(u) for u in (client_info.redirect_uris or [])]
        self._client().table("mcp_oauth_clients").insert({
            "client_id": client_info.client_id,
            "client_secret": client_info.client_secret,
            "redirect_uris": redirect_uris,
            "client_name": client_info.client_name,
            "grant_types": client_info.grant_types,
            "response_types": client_info.response_types,
            "scope": client_info.scope,
            "token_endpoint_auth_method": client_info.token_endpoint_auth_method,
        }).execute()
        logger.info(f"[MCP OAuth] Registered client: {client_info.client_id} ({client_info.client_name})")

    # --- Authorization ---

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """ADR-310 D4: real login. Store a PENDING auth code (no user yet) and
        redirect the operator to yarnnn.com to authenticate.

        The pending code captures the OAuth request (client, redirect_uri, PKCE,
        state, scope) but carries user_id=NULL. The web app logs the operator in
        and hands off to GET /api/mcp/oauth-callback, which binds the real
        Supabase user_id onto the code and redirects back to the OAuth client's
        redirect_uri. A code with NULL user_id is never exchangeable
        (load_authorization_code rejects it), so login is mandatory.
        """
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=AUTH_CODE_LIFETIME)

        # Store PENDING auth code — user_id bound later by the web callback.
        self._client().table("mcp_oauth_codes").insert({
            "code": code,
            "client_id": client.client_id,
            "user_id": None,  # PENDING — bound at /api/mcp/oauth-callback
            "redirect_uri": str(params.redirect_uri),
            "scope": " ".join(params.scopes) if params.scopes else "read",
            "code_challenge": params.code_challenge,
            "code_challenge_method": "S256",
            "state": params.state,
            "expires_at": expires_at.isoformat(),
        }).execute()

        logger.info(
            f"[MCP OAuth] Pending auth code for client {client.client_id} — "
            f"redirecting to web login"
        )

        # Redirect the browser to the web app's MCP-authorize page. After the
        # operator authenticates, the web app calls /api/mcp/oauth-callback with
        # the pending code; that route binds the user and completes the redirect
        # back to the OAuth client.
        app_url = os.environ.get("APP_URL", "https://yarnnn.com").rstrip("/")
        return f"{app_url}/mcp/authorize?{urlencode({'code': code})}"

    # --- Authorization Code Exchange ---

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> YarnnnAuthCode | None:
        result = (
            self._client()
            .table("mcp_oauth_codes")
            .select("*")
            .eq("code", authorization_code)
            .eq("client_id", client.client_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None

        row = result.data[0]
        expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            # Expired — clean up
            self._client().table("mcp_oauth_codes").delete().eq("code", authorization_code).execute()
            return None

        # ADR-310 D4: a PENDING code (user not yet bound by the web login
        # callback) is never exchangeable — reject without deleting so the
        # in-flight login can still complete and bind it.
        if not row.get("user_id"):
            logger.info("[MCP OAuth] Rejected exchange of pending (unbound) auth code")
            return None

        scopes = row.get("scope", "read").split(" ")

        return YarnnnAuthCode(
            code=row["code"],
            scopes=scopes,
            expires_at=expires_at.timestamp(),
            client_id=row["client_id"],
            code_challenge=row.get("code_challenge", ""),
            redirect_uri=row["redirect_uri"],
            redirect_uri_provided_explicitly=True,
            user_id=row["user_id"],
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: YarnnnAuthCode
    ) -> OAuthToken:
        user_id = authorization_code.user_id
        scopes = authorization_code.scopes

        # Generate tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        # Store access token
        self._client().table("mcp_oauth_access_tokens").insert({
            "token": access_token,
            "client_id": client.client_id,
            "user_id": user_id,
            "scopes": scopes,
            "expires_at": (now + timedelta(seconds=ACCESS_TOKEN_LIFETIME)).isoformat(),
        }).execute()

        # Store refresh token
        self._client().table("mcp_oauth_refresh_tokens").insert({
            "token": refresh_token,
            "client_id": client.client_id,
            "user_id": user_id,
            "scopes": scopes,
        }).execute()

        # Delete used auth code
        self._client().table("mcp_oauth_codes").delete().eq("code", authorization_code.code).execute()

        logger.info(f"[MCP OAuth] Issued tokens for user {user_id}, client {client.client_id}")

        # ADR-386 D1: auto-provision the foreign-LLM membership grant on first
        # connect. Best-effort — never breaks the OAuth flow.
        _ensure_foreign_llm_grant(user_id, client.client_id, "system:oauth-connect")

        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_LIFETIME,
            scope=" ".join(scopes),
            refresh_token=refresh_token,
        )

    # --- Refresh Token ---

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> YarnnnRefreshToken | None:
        result = (
            self._client()
            .table("mcp_oauth_refresh_tokens")
            .select("*")
            .eq("token", refresh_token)
            .eq("client_id", client.client_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None

        row = result.data[0]
        return YarnnnRefreshToken(
            token=row["token"],
            client_id=row["client_id"],
            scopes=row.get("scopes", ["read"]),
            user_id=row["user_id"],
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: YarnnnRefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        user_id = refresh_token.user_id
        effective_scopes = scopes if scopes else refresh_token.scopes

        # Rotate: new access token + new refresh token
        new_access = secrets.token_urlsafe(32)
        new_refresh = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        # Store new access token
        self._client().table("mcp_oauth_access_tokens").insert({
            "token": new_access,
            "client_id": client.client_id,
            "user_id": user_id,
            "scopes": effective_scopes,
            "expires_at": (now + timedelta(seconds=ACCESS_TOKEN_LIFETIME)).isoformat(),
        }).execute()

        # Store new refresh token
        self._client().table("mcp_oauth_refresh_tokens").insert({
            "token": new_refresh,
            "client_id": client.client_id,
            "user_id": user_id,
            "scopes": effective_scopes,
        }).execute()

        # Delete old refresh token (rotation)
        self._client().table("mcp_oauth_refresh_tokens").delete().eq("token", refresh_token.token).execute()

        logger.info(f"[MCP OAuth] Rotated tokens for user {user_id}")

        # ADR-386 D1.a (2026-06-30): provision on the REFRESH path too. Every
        # connector in production authorized BEFORE the auto-provision hook
        # shipped and stays alive via this silent rotation — authorize-only
        # never fired for them, so they had no grant + the External-Agents pane
        # read empty while they were demonstrably writing. Idempotent (no-op once
        # the grant exists); a pre-hook connector self-heals here. Best-effort.
        _ensure_foreign_llm_grant(user_id, client.client_id, "system:oauth-refresh")

        return OAuthToken(
            access_token=new_access,
            token_type="Bearer",
            expires_in=ACCESS_TOKEN_LIFETIME,
            scope=" ".join(effective_scopes),
            refresh_token=new_refresh,
        )

    # --- Access Token ---

    async def load_access_token(self, token: str) -> YarnnnAccessToken | None:
        # First check static bearer token for backward compatibility
        static_token = os.environ.get("MCP_BEARER_TOKEN")
        if static_token and token == static_token:
            return YarnnnAccessToken(
                token=token,
                client_id="internal",
                scopes=["read"],
                user_id=_get_mcp_user_id(),
            )

        # Look up OAuth access token
        result = (
            self._client()
            .table("mcp_oauth_access_tokens")
            .select("*")
            .eq("token", token)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None

        row = result.data[0]
        expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            # Expired — clean up
            self._client().table("mcp_oauth_access_tokens").delete().eq("token", token).execute()
            return None

        return YarnnnAccessToken(
            token=row["token"],
            client_id=row["client_id"],
            scopes=row.get("scopes", ["read"]),
            expires_at=int(expires_at.timestamp()),
            user_id=row["user_id"],
        )

    # --- Revocation ---

    async def revoke_token(
        self, token: YarnnnAccessToken | YarnnnRefreshToken
    ) -> None:
        if isinstance(token, YarnnnAccessToken):
            self._client().table("mcp_oauth_access_tokens").delete().eq("token", token.token).execute()
        elif isinstance(token, YarnnnRefreshToken):
            self._client().table("mcp_oauth_refresh_tokens").delete().eq("token", token.token).execute()
        logger.info(f"[MCP OAuth] Revoked token for client {token.client_id}")
