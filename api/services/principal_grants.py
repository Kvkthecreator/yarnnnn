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


# ---------------------------------------------------------------------------
# Provider identity (ADR-373 D2.a) — the foreign-LLM member is the PROVIDER
# (host-id), NOT the churning OAuth client_id.
# ---------------------------------------------------------------------------

def resolve_provider_id(
    *,
    client_id: Optional[str] = None,
    client_name: Optional[str] = None,
    redirect_uris: Optional[list] = None,
) -> Optional[str]:
    """Resolve an MCP client's OAuth identity to its STABLE provider/host id
    (ADR-373 D2.a) — `"chatgpt" | "claude.ai" | "gemini" | …`.

    The foreign-LLM membership principal is the provider, not the OAuth
    `client_id` (which a connector re-mints on every re-registration). Routes
    EVERY signal through the SINGLE canonical resolver — `resolve_host_id` (the
    ADR-379 Host Profiles registry, whose CI gate forbids host-name resolution
    leaking elsewhere). Tries the available signals strongest-first:

      1. client_name   — "ChatGPT" → chatgpt. (Claude's registered name is bare
                         "Claude", which the registry doesn't match — that's why
                         we also try the redirect_uri.)
      2. client_id     — ChatGPT's client_id carries "openai"/"chatgpt".
      3. redirect_uri  — the strongest signal for claude.ai
                         (https://claude.ai/api/mcp/auth_callback) and chatgpt.com.

    Returns the host-id, or None when no signal resolves (an unknown provider —
    the caller keeps the client_id as a best-effort principal so the member is
    still legible + revocable, just not collapsed across re-registrations).
    """
    from mcp_server.presentation.hosts import resolve_host_id

    for signal in (client_name, client_id):
        if signal:
            hid = resolve_host_id(signal)
            if hid:
                return hid
    for uri in (redirect_uris or []):
        hid = resolve_host_id(str(uri))
        if hid:
            return hid
    return None


#: host-id → operator-facing display label. The host-id is the stable provider
#: key (ADR-379 registry); this is just its friendly name for the roster. A
#: host-id not listed here falls back to the registry id itself (still legible).
_PROVIDER_LABELS = {
    "chatgpt": "ChatGPT",
    "claude.ai": "Claude",
    "claude_desktop": "Claude Desktop",
    "claude_code": "Claude Code",
    "gemini": "Gemini",
    "cursor": "Cursor",
    "copilot": "GitHub Copilot",
    "perplexity": "Perplexity",
}


def provider_label(principal_id: str) -> Optional[str]:
    """Friendly display name for a PROVIDER-keyed foreign-LLM principal (ADR-373
    D2.a), or None when `principal_id` is NOT a known host-id.

    None is the signal the caller uses to fall back to a legacy client_id name
    lookup (a pre-D2.a grant not yet migrated). A known host-id with no explicit
    label maps to the id itself (e.g. a future host) so it still renders.
    """
    from mcp_server.presentation.hosts import _BY_ID
    if principal_id in _BY_ID:
        return _PROVIDER_LABELS.get(principal_id, principal_id)
    return None


def resolve_provider_id_for_client(client_id: str) -> Optional[str]:
    """DB-backed `resolve_provider_id` — looks up the client row and resolves its
    provider id (ADR-373 D2.a). Used by the OAuth hooks + the backfill, which
    have the `client_id` and need the host-id to key the grant.

    Returns None when the client is unknown to the registry — callers fall back
    to the raw `client_id` so the member is still provisioned (legible +
    revocable), just not collapsed across the provider's re-registrations.
    """
    try:
        row = (
            _svc()
            .table("mcp_oauth_clients")
            .select("client_id, client_name, redirect_uris")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        ).data
        if not row:
            return resolve_provider_id(client_id=client_id)
        r = row[0]
        return resolve_provider_id(
            client_id=r.get("client_id"),
            client_name=r.get("client_name"),
            redirect_uris=r.get("redirect_uris"),
        )
    except Exception as exc:  # pragma: no cover — best-effort
        logger.warning("[ADR-373 D2.a] provider-id resolve failed for %s: %s", client_id, exc)
        return resolve_provider_id(client_id=client_id)


def client_ids_for_provider(workspace_id: str, provider_id: str) -> list[str]:
    """All OAuth `client_id`s registered to a provider/host (ADR-373 D2.a).

    Eviction needs this: the grant is keyed on the host-id (e.g. `claude.ai`),
    but tokens are keyed on `client_id`. To "revoke Claude" we must delete every
    Claude session's tokens — so resolve every registered client whose provider
    id matches. Scans `mcp_oauth_clients` (all registrations) and filters by the
    resolved provider id. (Workspace scoping is via the token's user_id at the
    delete site; the client registry itself is not workspace-keyed.)
    """
    try:
        rows = (
            _svc()
            .table("mcp_oauth_clients")
            .select("client_id, client_name, redirect_uris")
            .execute()
        ).data or []
    except Exception as exc:  # pragma: no cover — best-effort
        logger.warning("[ADR-373 D2.a] client enumeration failed: %s", exc)
        return []
    out = []
    for r in rows:
        if resolve_provider_id(
            client_id=r.get("client_id"),
            client_name=r.get("client_name"),
            redirect_uris=r.get("redirect_uris"),
        ) == provider_id:
            out.append(r["client_id"])
    return out


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


# The grant scope that authorizes funding the workspace (subscribe / top-up /
# manage billing). ADR-416 D1: billing authority is a grant, owner-default,
# extendable to a member's grant `scopes` — decoupled from who-may-SPEND (any
# member draws the pool). "Who may fund" is a grant, never a species/role-enum,
# coherent with the ADR-373/405 permission model.
BILLING_AUTHORITY_SCOPE = "billing"


def has_billing_authority(principal_id: str, workspace_id: str) -> bool:
    """True iff this principal may fund the workspace (subscribe / top-up / manage
    billing) — ADR-416 D1.

    Owner-default, and BYTE-IDENTICAL to the pre-ADR-416 owner-only routes: the
    ground-truth owner check is `workspaces.owner_id == principal_id` — NOT the
    presence of an `owner`-role grant. (Verified on live data: 2 legacy workspaces
    have an owner with no owner-grant row — the ADR-373 grant backfill didn't cover
    every pre-existing owner. Keying billing authority on the grant alone would 403
    those real owners. The `owner_id` column is the authoritative ownership fact;
    the grant is the extension mechanism, not the owner's proof.)

    So a principal has billing authority iff EITHER:
      1. it is the workspace's `owner_id` (the owner-default — always authorized,
         regardless of grant provisioning state), OR
      2. its active grant carries the `billing` scope (the extensible grant — a
         co-owner/admin the owner has granted).

    This is the ONLY place the billing-authority rule lives. Fail-closed on error.
    """
    try:
        # (1) The ground-truth owner check — authoritative, grant-independent.
        ws = (
            _svc()
            .table("workspaces")
            .select("owner_id")
            .eq("id", workspace_id)
            .limit(1)
            .execute()
        ).data
        if ws and str(ws[0].get("owner_id")) == str(principal_id):
            return True

        # (2) The extensible grant — a non-owner principal granted `billing`.
        grant = _load_active_grant(principal_id, workspace_id)
        if grant is None:
            return False
        if grant.get("role") == "owner":  # defensive: grant-owner also authorized
            return True
        scopes = grant.get("scopes") or []
        return BILLING_AUTHORITY_SCOPE in scopes
    except Exception:  # pragma: no cover — fail-closed on lookup error
        return False


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

    # Delete the principal's OAuth tokens (the eviction). ADR-373 D2.a: the
    # foreign-LLM principal_id is the PROVIDER host-id (e.g. `claude.ai`), but
    # tokens are keyed on `client_id` — and a provider has MANY client_ids (one
    # per re-registration). So sweep EVERY client_id registered to this provider,
    # not just `principal_id` (which now matches no token row). For a legacy
    # client_id-keyed grant (pre-D2.a) `client_ids_for_provider` returns [] and
    # we fall back to deleting by the principal_id directly. Best-effort: a
    # token-delete failure must not leave the grant un-revoked — the status flip
    # already happened above.
    tokens_deleted = 0
    try:
        role = grant.get("role")
        client_ids: list[str] = []
        if role in ("foreign-llm", "platform", "a2a"):
            client_ids = client_ids_for_provider(workspace_id, principal_id)
        # Fallback: a legacy client_id-keyed grant (or unknown provider) — the
        # principal_id IS the client_id, so delete by it directly.
        for cid in (client_ids or [principal_id]):
            tokens_deleted += delete_tokens_for_client(cid)
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
