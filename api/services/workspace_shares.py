"""Shared-artifact wedge — ADR-437 D4.

The member-invite's generous sibling. A SHARE lets an existing principal share
a substrate artifact (a workspace_files path); the recipient opens the link and
the act of accessing IS the activation (ADR-437 D4) — the artifact is the
landing page, `trace` demonstrated on contact.

Two origins, one accept surface (ADR-437 D4.1): a share is created from the
cockpit ("Share" on an artifact) OR from an external LLM via the MCP `share`
verb; both mint the same share row and land on `/s/{token}`.

Broad by default — the Figma model (ADR-437 D4.2): accepting mints a member
grant with `scopes=None` → the class default (broad operation/ + agents/ write
regions, ADR-373 D3). The owner narrows via the powerbox (ADR-434); the share
never gates by default. Unlike an invite, a share is LINK-based (not
email-locked) — any authenticated principal who opens the link may accept.

The GRANT is the authorization fact (ADR-386); the share row is transport,
exactly like workspace_invites (migration 199 → this is migration 214).

Service-client only (RLS: service-role-only on workspace_shares — the routes
enforce the sharer's grant + authenticate the acceptor's JWT).
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# A share link is durable by default (no expiry). A caller may pass ttl_days for
# a time-boxed share; None (the default) means the link never expires.
DEFAULT_SHARE_TTL_DAYS: Optional[int] = None


class ShareError(Exception):
    """Share lifecycle violation (not found / revoked / expired / already-owner)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _svc():
    from services.supabase import get_service_client
    return get_service_client()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_share(
    *,
    workspace_id: str,
    shared_by: str,
    artifact_path: Optional[str] = None,
    label: Optional[str] = None,
    ttl_days: Optional[int] = DEFAULT_SHARE_TTL_DAYS,
) -> dict[str, Any]:
    """Mint a share link for an artifact (or a bare workspace share).

    Link-based: no per-recipient row. Re-sharing the same artifact mints a new
    link (multiple links to one artifact are fine — each is a durable token).
    """
    expires_at = (
        (_now() + timedelta(days=ttl_days)).isoformat() if ttl_days else None
    )
    row = {
        "workspace_id": workspace_id,
        "artifact_path": artifact_path,
        "label": label,
        "role": "member",
        "token": secrets.token_urlsafe(24),
        "shared_by": shared_by,
        "status": "active",
        "expires_at": expires_at,
    }
    result = _svc().table("workspace_shares").insert(row).execute()
    if not result.data:
        raise ShareError("insert_failed", "Failed to create share")
    return result.data[0]


def list_shares(workspace_id: str) -> list[dict[str, Any]]:
    """Active share links for the workspace, newest first."""
    return (
        _svc().table("workspace_shares")
        .select("id, artifact_path, label, role, status, created_at, expires_at, last_accepted_at")
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .execute()
    ).data or []


def revoke_share(workspace_id: str, share_id: str) -> bool:
    result = (
        _svc().table("workspace_shares")
        .update({"status": "revoked"})
        .eq("id", share_id)
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .execute()
    )
    return bool(result.data)


def get_share_by_token(token: str) -> Optional[dict[str, Any]]:
    """The share + workspace name, for the accept-page preview."""
    rows = (
        _svc().table("workspace_shares")
        .select("id, workspace_id, artifact_path, label, role, status, expires_at, shared_by")
        .eq("token", token)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return None
    share = rows[0]
    ws = (
        _svc().table("workspaces")
        .select("name")
        .eq("id", share["workspace_id"])
        .limit(1)
        .execute()
    ).data or []
    share["workspace_name"] = ws[0].get("name") if ws else None
    return share


def _workspace_owner_id(workspace_id: str) -> Optional[str]:
    rows = (
        _svc().table("workspaces")
        .select("owner_id")
        .eq("id", workspace_id)
        .limit(1)
        .execute()
    ).data or []
    return rows[0]["owner_id"] if rows else None


def accept_share(*, token: str, user_id: str) -> dict[str, Any]:
    """Bind an authenticated principal to the commons via a share link (ADR-437 D4.2).

    Link-based — any authenticated principal who opens the link may accept (the
    Figma default, no email lock). Accepting mints a BROAD member grant
    (`scopes=None` → class default, ADR-373 D3). Idempotent for the owner and
    for a re-accepting member (ensure_principal_grant is idempotent).
    """
    share = get_share_by_token(token)
    if share is None:
        raise ShareError("not_found", "Share link not found")
    if share["status"] != "active":
        raise ShareError("not_active", f"This share link is {share['status']}")
    expires = share.get("expires_at")
    if expires and datetime.fromisoformat(str(expires).replace("Z", "+00:00")) < _now():
        _svc().table("workspace_shares").update({"status": "expired"}).eq(
            "id", share["id"]
        ).execute()
        raise ShareError("expired", "This share link has expired")

    workspace_id = share["workspace_id"]

    # The owner already has the workspace — accepting their own share is a no-op
    # bind (they land on the artifact, no grant change).
    if _workspace_owner_id(workspace_id) == user_id:
        return {
            "workspace_id": workspace_id,
            "workspace_name": share.get("workspace_name"),
            "artifact_path": share.get("artifact_path"),
            "role": "owner",
            "grant_id": None,
        }

    # Broad-by-default (ADR-437 D4.2): scopes=None → class-default member write
    # regions at the gate (ADR-373 D3). The powerbox narrows later if the owner
    # wants (ADR-434); the share never gates by default.
    from services.principal_grants import ensure_principal_grant
    grant = ensure_principal_grant(
        principal_id=user_id,
        workspace_id=workspace_id,
        role="member",
        granted_by=f"share:{share['shared_by']}",
    )

    _svc().table("workspace_shares").update({
        "last_accepted_at": _now().isoformat(),
        "accepted_principal_id": user_id,
    }).eq("id", share["id"]).execute()

    return {
        "workspace_id": workspace_id,
        "workspace_name": share.get("workspace_name"),
        "artifact_path": share.get("artifact_path"),
        "role": "member",
        "grant_id": grant.get("id"),
    }
