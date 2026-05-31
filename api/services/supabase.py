"""
Supabase client configuration
"""
from __future__ import annotations

import os
import json
import base64
from functools import lru_cache
from typing import Iterator, Optional, Tuple
from dataclasses import dataclass

from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions as ClientOptions
from fastapi import Depends, HTTPException, Header

# Python 3.9 compatible Annotated import
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (Supabase handles verification via RLS)."""
    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        raise ValueError(f"Failed to decode JWT: {e}")


@dataclass
class AuthenticatedClient:
    """Wrapper that holds Supabase client, user ID, and email.

    ADR-288 D1: ``caller_identity`` carries the ADR-209 attribution string
    for substrate writes performed through this auth (e.g., ``"operator"``,
    ``"reviewer:ai:reviewer-sonnet-v8"``, ``"yarnnn:mcp"``,
    ``"system:<recurrence-slug>"``). Defaults to ``"operator"`` because the
    only path that constructs ``AuthenticatedClient`` is the route-level JWT
    handler ``get_user_client`` — the operator hit the API. Non-operator
    callers (Reviewer wake, mechanical recurrence, MCP, specialist
    dispatch) build their own auth namespaces and set ``caller_identity``
    explicitly at construction time.
    """
    client: Client
    user_id: str
    email: Optional[str] = None
    caller_identity: str = "operator"


@lru_cache()
def get_supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL must be set")
    return url


@lru_cache()
def get_service_client() -> Client:
    """Get Supabase client with service key (bypasses RLS)."""
    url = get_supabase_url()
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        raise ValueError("SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


def get_user_client(
    authorization: Optional[str] = Header(None),
) -> Iterator[AuthenticatedClient]:
    """
    Get Supabase client with user's JWT for RLS enforcement.
    Yields an AuthenticatedClient with both the client and user_id.
    Use as FastAPI dependency.

    Memory discipline: this dependency runs on every authenticated request,
    including the always-on frontend polls (``/api/workspace/nav``,
    ``/api/recurrences``, ``/api/cockpit/pace`` every ~60s). Each ``create_client``
    builds a ``postgrest`` client wrapping its own ``httpx.Client`` connection
    pool. Without an explicit teardown these pools (TLS connections + buffers)
    accumulate over the process lifetime — the slow RSS creep that OOM-killed
    yarnnn-api on 2026-06-01 (~5 MB/hr until it crossed the 512 MB ceiling).

    Two guards:
      1. ``auto_refresh_token=False`` + ``persist_session=False`` — we never run
         the sign-in flow here (the JWT is decoded locally and applied directly
         to postgrest), so the gotrue auto-refresh ``threading.Timer`` is pure
         overhead. Disabling it removes any chance of an orphaned refresh timer.
      2. ``finally: client.postgrest.aclose()`` — releases the per-request
         connection pool as soon as the request completes, instead of leaving it
         for GC. This is the load-bearing fix.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.replace("Bearer ", "")

    # Decode JWT to get user ID and email
    try:
        payload = decode_jwt_payload(token)
        user_id = payload.get("sub")
        email = payload.get("email")  # Supabase includes email in JWT
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    url = get_supabase_url()
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not key:
        raise ValueError("SUPABASE_ANON_KEY must be set")

    options = ClientOptions(auto_refresh_token=False, persist_session=False)
    client = create_client(url, key, options)
    # Set the auth token for RLS
    client.postgrest.auth(token)

    try:
        yield AuthenticatedClient(client=client, user_id=user_id, email=email)
    finally:
        # Release the request-scoped postgrest connection pool. SyncPostgrestClient
        # exposes aclose() (async); the wrapped httpx.Client.close() is the sync
        # release we actually need. Close defensively so a teardown error never
        # masks the response.
        try:
            client.postgrest.session.close()
        except Exception:  # pragma: no cover - teardown best-effort
            pass


# Type alias for dependency injection
UserClient = Annotated[AuthenticatedClient, Depends(get_user_client)]
ServiceClient = Annotated[Client, Depends(get_service_client)]
