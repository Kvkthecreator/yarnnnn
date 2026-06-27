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
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token

        token = get_access_token()
        # YarnnnAccessToken carries user_id (oauth_provider.py); the static
        # bearer path also stamps MCP_USER_ID onto it.
        user_id = getattr(token, "user_id", None)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] no request token user (%s); falling back to env", exc)

    if not user_id:
        user_id = os.environ.get("MCP_USER_ID")
        if not user_id:
            raise ValueError(
                "No authenticated user for MCP request and MCP_USER_ID unset."
            )

    # Client-qualified attribution (Finding 2, 2026-06-26): the revision's
    # authored_by must NAME the contributing LLM (yarnnn:mcp:<client>). The
    # earlier direct-only `_normalize_client_id(client_id)` mapping returned
    # None for claude.ai's OPAQUE registration-UUID client_id, so authored_by
    # silently fell back to bare `yarnnn:mcp` even though the provenance stamp
    # (which used the DB-backed lookup) resolved the name. Use the SAME DB-backed
    # resolver here so authored_by and provenance never diverge. It needs an auth
    # client to read mcp_oauth_clients, so build a base client ONCE, derive the
    # name with it, then re-stamp caller_identity on the same underlying client —
    # no second create_client(). (live test surfaced the divergence: authored_by=
    # yarnnn:mcp while provenance=mcp:Claude on the same write.)
    base = _build_client(user_id)
    client_name = None
    try:
        from services.mcp_composition import derive_client_name_from_token
        resolved = derive_client_name_from_token(base)
        if resolved and resolved != "unknown":
            client_name = resolved
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] client-name resolution failed (%s)", exc)

    if not client_name:
        return base
    return AuthenticatedClient(
        client=base.client,
        user_id=user_id,
        email=None,
        caller_identity=f"yarnnn:mcp:{client_name}",
    )


def resolve_request_host_id() -> str | None:
    """Resolve the calling host id for the CURRENT request (ADR-379), best-effort.

    Used by the DISCOVERY + RESOURCE-READ gates (server.py) — these run before any
    tool response, so the response-time `client_name` isn't available; they need
    the host identity here. Returns a HostProfile id ("chatgpt" | "claude.ai" | …)
    or None when the caller can't be identified.

    Resolution order, cheapest-first (discovery is hot and should avoid a DB hit
    unless needed):
      1. The token `client_id` resolved directly by substring (catches ChatGPT,
         whose client_id carries "openai"/"chatgpt"; zero DB).
      2. The DB-backed registered `client_name` lookup (catches claude.ai's opaque
         UUID via the registered name) — only when (1) misses.

    SAFE DEFAULT: None on any failure / unidentified caller. The gate treats None
    as a non-widget host (text-safe), so an unidentified host is never advertised a
    widget it might choke on — the same fail-closed posture as the response gate.
    """
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token
        token = get_access_token()
    except Exception:  # noqa: BLE001
        token = None
    client_id = getattr(token, "client_id", None) if token else None
    if not client_id:
        return None

    from mcp_server.presentation.hosts import resolve_host_id

    # (1) cheap direct resolve from the client_id itself (ChatGPT, etc.)
    direct = resolve_host_id(client_id)
    if direct:
        return direct

    # (2) DB-backed registered-name lookup (claude.ai opaque UUID). Best-effort.
    try:
        user_id = getattr(token, "user_id", None) or os.environ.get("MCP_USER_ID")
        if not user_id:
            return None
        base = _build_client(user_id)
        row = (
            base.client.table("mcp_oauth_clients")
            .select("client_name")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )
        name = (row.data or [{}])[0].get("client_name") if row.data else None
        return resolve_host_id(name) if name else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP Auth] host-id resolution failed (%s)", exc)
        return None
