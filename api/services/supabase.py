"""
Supabase client configuration
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from supabase import create_client, Client
from fastapi import Depends, HTTPException, Header

# Python 3.9 compatible Annotated import
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated


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


def get_user_client(authorization: Optional[str] = Header(None)) -> Client:
    """
    Get Supabase client with user's JWT for RLS enforcement.
    Use as FastAPI dependency.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.replace("Bearer ", "")
    url = get_supabase_url()
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not key:
        raise ValueError("SUPABASE_ANON_KEY must be set")

    client = create_client(url, key)
    # Set the auth token for RLS
    client.postgrest.auth(token)
    return client


# Type alias for dependency injection
UserClient = Annotated[Client, Depends(get_user_client)]
ServiceClient = Annotated[Client, Depends(get_service_client)]
