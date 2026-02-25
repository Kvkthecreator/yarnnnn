"""
MCP OAuth 2.1 Authorization Server Provider — ADR-075

Implements OAuthAuthorizationServerProvider from the mcp SDK to enable
Claude.ai connectors and ChatGPT developer mode to authenticate via
standard OAuth 2.1 flow.

Flow:
1. Client registers dynamically (POST /register)
2. Client redirects user to /authorize
3. We redirect to Supabase Auth login
4. On Supabase callback, auto-approve + generate auth code
5. Client exchanges code for access token (POST /token)
6. Client uses access token on /mcp requests

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
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from services.supabase import get_service_client

logger = logging.getLogger(__name__)

# Token lifetimes
ACCESS_TOKEN_LIFETIME = 3600  # 1 hour
REFRESH_TOKEN_LIFETIME = 30 * 24 * 3600  # 30 days
AUTH_CODE_LIFETIME = 300  # 5 minutes


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
        """Auto-approve: generate auth code immediately and redirect back.

        In single-user mode, we skip the login step and directly issue
        an auth code for MCP_USER_ID. Multi-user mode would redirect to
        Supabase login first.
        """
        user_id = _get_mcp_user_id()
        code = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=AUTH_CODE_LIFETIME)

        # Store auth code
        self._client().table("mcp_oauth_codes").insert({
            "code": code,
            "client_id": client.client_id,
            "user_id": user_id,
            "redirect_uri": str(params.redirect_uri),
            "scope": " ".join(params.scopes) if params.scopes else "read",
            "code_challenge": params.code_challenge,
            "code_challenge_method": "S256",
            "state": params.state,
            "expires_at": expires_at.isoformat(),
        }).execute()

        logger.info(f"[MCP OAuth] Auto-approved auth for user {user_id}, client {client.client_id}")

        # Redirect back to client with auth code
        return construct_redirect_uri(
            str(params.redirect_uri),
            code=code,
            state=params.state,
        )

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
