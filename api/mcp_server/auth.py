"""
MCP Server Authentication Bridge — ADR-075

Uses service key + MCP_USER_ID for durable, non-expiring authentication.
Matches the pattern used by platform_worker and unified_scheduler:
service key bypasses RLS, all queries use explicit .eq("user_id", user_id).

For stdio transport: one process = one user. Auth runs once at startup.
For HTTP transport: auth runs once at startup (single-user server).
"""

import os
import logging

from services.supabase import (
    AuthenticatedClient,
    get_service_client,
)

logger = logging.getLogger(__name__)


def get_authenticated_client() -> AuthenticatedClient:
    """
    Create a service-key Supabase client scoped to MCP_USER_ID.

    Uses SUPABASE_SERVICE_KEY (bypasses RLS) with explicit user_id
    filtering — the same pattern as platform_worker and unified_scheduler.
    No token expiration; works indefinitely.

    Returns:
        AuthenticatedClient with .client, .user_id, .email

    Raises:
        ValueError: If MCP_USER_ID is missing
    """
    user_id = os.environ.get("MCP_USER_ID")
    if not user_id:
        raise ValueError(
            "MCP_USER_ID environment variable required. "
            "Set to the Supabase user UUID from the users table."
        )

    client = get_service_client()

    logger.info(f"[MCP Auth] Service-key auth for user {user_id}")

    return AuthenticatedClient(client=client, user_id=user_id, email=None)
