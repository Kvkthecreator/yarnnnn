"""Principal-grant lifecycle (ADR-386) — the grant CREATE/GOVERN layer.

ADR-373 shipped the grant CONSULT (the gate reads `principal_grants` and
authorizes per-principal). This module is the LIFECYCLE that brings grant rows
into existence and governs them:

  - ensure_principal_grant — lazily create a grant (idempotent on the active
    partial-unique key). Called on OAuth connect to auto-provision a foreign-LLM
    member (ADR-386 D1).
  - narrow_grant — tighten a member's write-region `scopes` below its class
    default (authz only; the OAuth token is untouched). ADR-386 D2.
  - evict_principal — REVOKE = full eviction: flip the grant to `revoked` AND
    delete the principal's OAuth tokens, so it can neither authenticate nor
    write. ADR-386 D2/D3.

OWNER IMMUTABILITY (ADR-386 D4): narrow_grant + evict_principal hard-reject any
grant with `role='owner'` — the operator cannot lock themselves out through this
surface. The reject is a raised PermissionError (the route maps it to 403).

All writes use the SERVICE client (the grant table is the gate's authority; it
must not depend on the caller's own, mid-transition RLS).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OwnerGrantImmutable(PermissionError):
    """Raised when a lifecycle verb targets the owner grant (ADR-386 D4)."""


def _svc():
    from services.supabase import get_service_client
    return get_service_client()


def delete_tokens_for_client(client_id: str) -> int:
    """Delete ALL OAuth tokens for a client_id (ADR-386 D2 — REVOKE = eviction).

    The by-client sibling of the OAuth provider's by-token revoke. When the
    operator evicts a foreign-LLM member (principal_id == OAuth client_id,
    ADR-373 D2), this removes every access + refresh token for that client, so
    it can no longer authenticate against the workspace — it must re-authorize
    from scratch to return. Returns the count of token rows deleted.

    Lives HERE (not in mcp_server/oauth_provider.py) deliberately: it is a plain
    DB delete with no MCP-SDK dependency, and oauth_provider imports the `mcp`
    package (3.11-only, absent from the api venv). Keeping the eviction helper
    here makes `evict_principal` testable under the api runner and keeps the two
    tables it touches co-located with the lifecycle that owns them.
    """
    svc = _svc()
    deleted = 0
    for table in ("mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens"):
        res = svc.table(table).delete().eq("client_id", client_id).execute()
        deleted += len(res.data or [])
    logger.info("[ADR-386] evicted client %s — %d OAuth token rows deleted", client_id, deleted)
    return deleted


def ensure_principal_grant(
    principal_id: str,
    workspace_id: str,
    role: str,
    scopes: Optional[list[str]] = None,
    granted_by: str = "system:adr386-lifecycle",
) -> dict:
    """Lazily ensure an active grant for (principal_id, workspace_id) (ADR-386 D1).

    Idempotent: if an active grant already exists for the pair (the
    `uq_principal_grant_active` partial-unique index), this is a no-op and
    returns the existing row. Otherwise inserts a fresh active grant.

    Returns the grant row dict. Best-effort at the call site (the OAuth hook
    wraps it so a failure never breaks the connect flow — the consult still
    falls back to the class default, ADR-386 §6.3).
    """
    svc = _svc()
    existing = (
        svc.table("principal_grants")
        .select("id, principal_id, workspace_id, role, scopes, status")
        .eq("principal_id", principal_id)
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    inserted = (
        svc.table("principal_grants")
        .insert({
            "principal_id": principal_id,
            "workspace_id": workspace_id,
            "role": role,
            "scopes": scopes,  # None → class default at the gate (ADR-373 D3)
            "granted_by": granted_by,
            "status": "active",
        })
        .execute()
    )
    logger.info(
        "[ADR-386] auto-provisioned %s grant for principal=%s workspace=%s",
        role, principal_id, workspace_id,
    )
    return (inserted.data or [{}])[0]


def _load_active_grant(principal_id: str, workspace_id: str) -> Optional[dict]:
    rows = (
        _svc()
        .table("principal_grants")
        .select("id, role, scopes, status")
        .eq("principal_id", principal_id)
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    ).data
    return rows[0] if rows else None


def narrow_grant(
    principal_id: str,
    workspace_id: str,
    scopes: list[str],
) -> dict:
    """Tighten a member's write-region `scopes` (ADR-386 D2 — NARROW).

    Authz-only: writes `principal_grants.scopes`; the OAuth token is untouched
    (the member stays connected, can still read). The gate's allow-list path
    (ADR-373 D2) then denies writes outside the narrowed set.

    Rejects the owner grant (ADR-386 D4) — raises OwnerGrantImmutable.
    Raises ValueError if no active grant exists for the pair.
    """
    grant = _load_active_grant(principal_id, workspace_id)
    if grant is None:
        raise ValueError("no active grant for this principal in this workspace")
    if grant.get("role") == "owner":
        raise OwnerGrantImmutable("the owner grant cannot be narrowed")

    updated = (
        _svc()
        .table("principal_grants")
        .update({"scopes": scopes})
        .eq("id", grant["id"])
        .execute()
    )
    logger.info(
        "[ADR-386] narrowed grant principal=%s workspace=%s scopes=%s",
        principal_id, workspace_id, scopes,
    )
    return (updated.data or [{}])[0]


def evict_principal(
    principal_id: str,
    workspace_id: str,
) -> dict:
    """REVOKE = full eviction (ADR-386 D2/D3).

    Two coupled effects:
      1. flip the grant to `status='revoked'` (the audit record of the eviction);
      2. delete the principal's OAuth access + refresh tokens (by client_id) —
         the principal can no longer authenticate, read, or write.

    Because a revoked principal has no token, it never reaches the gate, so the
    consult needs no `revoked`-aware branch (ADR-386 D3). Reconnecting requires
    a fresh OAuth authorize, which re-auto-provisions a new active grant (D1).

    Rejects the owner grant (ADR-386 D4) — raises OwnerGrantImmutable.
    Raises ValueError if no active grant exists for the pair.
    """
    grant = _load_active_grant(principal_id, workspace_id)
    if grant is None:
        raise ValueError("no active grant for this principal in this workspace")
    if grant.get("role") == "owner":
        raise OwnerGrantImmutable("the owner grant cannot be revoked")

    svc = _svc()
    svc.table("principal_grants").update({"status": "revoked"}).eq("id", grant["id"]).execute()

    # Delete the principal's OAuth tokens (the eviction). principal_id for a
    # foreign-LLM IS its OAuth client_id (ADR-373 D2 / resolve_principal_id), so
    # delete by client_id. Best-effort: a token-delete failure must not leave the
    # grant un-revoked — the status flip already happened above.
    tokens_deleted = 0
    try:
        tokens_deleted = delete_tokens_for_client(principal_id)
    except Exception as exc:  # pragma: no cover — best-effort token sweep
        logger.warning(
            "[ADR-386] token eviction for principal=%s failed: %s "
            "(grant already revoked; principal can't write, but tokens linger)",
            principal_id, exc,
        )

    logger.info(
        "[ADR-386] evicted principal=%s workspace=%s (grant revoked, %d tokens deleted)",
        principal_id, workspace_id, tokens_deleted,
    )
    return {"principal_id": principal_id, "status": "revoked", "tokens_deleted": tokens_deleted}
