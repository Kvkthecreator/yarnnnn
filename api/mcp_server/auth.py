"""
MCP Server Authentication Bridge — ADR-075 + ADR-310

Service key + per-request user identity. Service key bypasses RLS; every
query uses explicit .eq("user_id", user_id), so isolation is correct once
the right user_id flows in.

Two identity sources, in priority order (ADR-310 D4 — per-request identity):
  1. The per-request OAuth access token's user_id (the real authenticating
     user, set by YarnnnOAuthProvider.load_access_token). This is what makes
     the connector multi-user: each operator's own LLM authenticates as
     themselves and reaches their own substrate.
  2. MCP_USER_ID env var — fallback for the static-bearer path and stdio
     transport (one process = one user). The static bearer's YarnnnAccessToken
     already carries MCP_USER_ID as its user_id, so even that path flows
     through source 1; the env fallback is the last resort.

For stdio transport: one process = one user (MCP_USER_ID).
For HTTP transport: per-request identity from the validated token.
"""

import os
import logging

from services.supabase import (
    AuthenticatedClient,
    get_service_client,
)

logger = logging.getLogger(__name__)


def _build_client(user_id: str, client_name: str | None = None) -> AuthenticatedClient:
    """Build a service-key client scoped to a specific user_id.

    Service key bypasses RLS; isolation comes from explicit .eq("user_id", …)
    on every query (same pattern as unified_scheduler). ADR-288 D1:
    caller_identity sets the default authored_by for MCP-routed writes through
    execute_primitive().

    Client-qualified attribution: when the contributing LLM is known (resolved
    from the OAuth session), caller_identity becomes ``yarnnn:mcp:<client>``
    (e.g. ``yarnnn:mcp:claude.ai``) so every foreign write — and the `trace`
    chain — NAMES THE ROOM, not just "an MCP write". This is the cross-LLM
    provenance story made literal: trace shows "contributed via claude.ai →
    filed by the Reviewer". Validates under the ``yarnnn:`` prefix
    (is_valid_author), so no schema/validation change. Falls back to the bare
    ``yarnnn:mcp`` when the client can't be identified.
    """
    caller_identity = f"yarnnn:mcp:{client_name}" if client_name and client_name != "unknown" else "yarnnn:mcp"
    return AuthenticatedClient(
        client=get_service_client(),
        user_id=user_id,
        email=None,
        caller_identity=caller_identity,
    )


def resolve_request_client() -> AuthenticatedClient:
    """Resolve the authenticated client for the CURRENT request (ADR-310 D4).

    Reads the per-request OAuth token's user_id (the real authenticating
    operator) via the FastMCP auth context. Falls back to MCP_USER_ID only
    when no token user is present (stdio / misconfiguration). This is the
    single entry point every HTTP tool handler should call — it replaces
    reading the boot-time lifespan singleton, which pinned every request to
    one user regardless of who authenticated.
    """
    user_id = None
    client_name = None
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        token = get_access_token()
        # YarnnnAccessToken carries user_id (oauth_provider.py); the static
        # bearer path also stamps MCP_USER_ID onto it.
        user_id = getattr(token, "user_id", None)
        # client-qualified attribution: map the OAuth client_id to a short name
        # so the revision's authored_by NAMES the contributing LLM. Direct map
        # only here (the DB-backed client_name lookup lives in the provenance
        # stamp path, which has an auth client in hand); covers the common case
        # where the client_id is recognizable.
        client_id = getattr(token, "client_id", None)
        if client_id:
            from services.mcp_composition import _normalize_client_id
            client_name = _normalize_client_id(client_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] no request token user (%s); falling back to env", exc)

    if not user_id:
        user_id = os.environ.get("MCP_USER_ID")
        if not user_id:
            raise ValueError(
                "No authenticated user for MCP request and MCP_USER_ID unset."
            )
    return _build_client(user_id, client_name=client_name)
