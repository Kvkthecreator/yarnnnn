"""
Admin authentication and authorization.
Uses email-based allowlist for simple admin access control.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional
from dataclasses import dataclass

from supabase import Client
from fastapi import Depends, HTTPException, Header

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

from services.supabase import decode_jwt_payload, get_service_client


@lru_cache()
def get_admin_allowlist() -> list[str]:
    """Get list of admin emails from environment variable."""
    raw = os.environ.get("ADMIN_ALLOWED_EMAILS", "")
    if not raw:
        return []
    return [email.strip().lower() for email in raw.split(",") if email.strip()]


def is_admin_email(email: str | None) -> bool:
    """Check if email is in admin allowlist."""
    if not email:
        return False
    return email.lower() in get_admin_allowlist()


@dataclass
class AdminClient:
    """Wrapper for admin-authenticated requests with service client."""
    client: Client
    user_id: str
    email: str


def verify_admin_access(authorization: Optional[str] = Header(None)) -> AdminClient:
    """
    Verify admin access via email allowlist.
    Returns AdminClient with service-level database access.
    Use as FastAPI dependency for admin endpoints.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.replace("Bearer ", "")

    # Decode JWT to get user info
    try:
        payload = decode_jwt_payload(token)
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token: no email")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Check admin allowlist
    if not is_admin_email(email):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Return service client (bypasses RLS) for admin queries
    service_client = get_service_client()

    return AdminClient(client=service_client, user_id=user_id, email=email)


# Type alias for dependency injection
AdminAuth = Annotated[AdminClient, Depends(verify_admin_access)]
