"""
Supabase client configuration
"""
from __future__ import annotations

import os
import json
import base64
from functools import lru_cache
from typing import Optional, Tuple
from dataclasses import dataclass

from supabase import create_client, Client
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
    """Wrapper that holds both the Supabase client and the authenticated user ID."""
    client: Client
    user_id: str


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


def get_user_client(authorization: Optional[str] = Header(None)) -> AuthenticatedClient:
    """
    Get Supabase client with user's JWT for RLS enforcement.
    Returns an AuthenticatedClient with both the client and user_id.
    Use as FastAPI dependency.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.replace("Bearer ", "")

    # Decode JWT to get user ID
    try:
        payload = decode_jwt_payload(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    url = get_supabase_url()
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not key:
        raise ValueError("SUPABASE_ANON_KEY must be set")

    client = create_client(url, key)
    # Set the auth token for RLS
    client.postgrest.auth(token)

    return AuthenticatedClient(client=client, user_id=user_id)


# Type alias for dependency injection
UserClient = Annotated[AuthenticatedClient, Depends(get_user_client)]
ServiceClient = Annotated[Client, Depends(get_service_client)]
