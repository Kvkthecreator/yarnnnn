"""
MCP Server Authentication Bridge — ADR-075

Resolves YARNNN_TOKEN env var into a user-scoped Supabase client.
Reuses the same JWT decoding and client creation pattern as the FastAPI
auth layer (services/supabase.py), but reads the token from environment
instead of an HTTP Authorization header.

For stdio transport: one process = one user. Auth runs once at startup.
For HTTP transport (Phase 2): auth will move to per-request.
"""

import os
import logging

from supabase import create_client

from services.supabase import (
    AuthenticatedClient,
    decode_jwt_payload,
    get_supabase_url,
)

logger = logging.getLogger(__name__)


def get_authenticated_client() -> AuthenticatedClient:
    """
    Create a user-scoped Supabase client from YARNNN_TOKEN env var.

    The token is a Supabase JWT (same format as web session tokens).
    JWT is decoded (not verified — Supabase RLS handles verification)
    to extract user_id and email, then used to create an RLS-scoped client.

    Returns:
        AuthenticatedClient with .client, .user_id, .email

    Raises:
        ValueError: If YARNNN_TOKEN is missing or invalid
    """
    token = os.environ.get("YARNNN_TOKEN")
    if not token:
        raise ValueError(
            "YARNNN_TOKEN environment variable required. "
            "Generate a token from yarnnn.com Settings page."
        )

    # Decode JWT to extract user identity (same as supabase.get_user_client)
    payload = decode_jwt_payload(token)
    user_id = payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise ValueError("Invalid YARNNN_TOKEN: no user ID in token payload")

    # Create user-scoped Supabase client with RLS enforcement
    url = get_supabase_url()
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if not anon_key:
        raise ValueError("SUPABASE_ANON_KEY must be set")

    client = create_client(url, anon_key)
    client.postgrest.auth(token)

    logger.info(f"[MCP Auth] Authenticated as user {user_id} ({email})")

    return AuthenticatedClient(client=client, user_id=user_id, email=email)
