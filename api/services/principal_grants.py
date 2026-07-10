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

#: Sentinel for "read axis not specified" → read ⊇ write (read mirrors write).
#: Distinct from None (an explicit "read axis = class default") and [] (deny-all).
_UNSET: Any = object()


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


def delete_tokens_for_client(client_id: str, user_id: Optional[str] = None) -> int:
    """Delete OAuth tokens for a client_id (ADR-386 D2 — REVOKE = eviction).

    The by-client sibling of the OAuth provider's by-token revoke. Removes the
    access + refresh tokens so the connection can no longer authenticate against
    the workspace — it must re-authorize from scratch to return. Returns the
    count of token rows deleted.

    ADR-431 D4: when `user_id` is given, the delete additionally scopes to that
    member's tokens (`mcp_oauth_*` carries `user_id`). This is what lets a
    revoke of "seulkim's ChatGPT" leave the owner's ChatGPT connected — the two
    share a provider (hence client_ids) but not a token-owner. When `user_id` is
    None the sweep is provider-wide (the pre-431 behavior — correct at N=1 and
    for legacy grants with no `connected_by`).

    Lives HERE (not in mcp_server/oauth_provider.py) deliberately: it is a plain
    DB delete with no MCP-SDK dependency, and oauth_provider imports the `mcp`
    package (3.11-only, absent from the api venv). Keeping the eviction helper
    here makes `evict_principal` testable under the api runner and keeps the two
    tables it touches co-located with the lifecycle that owns them.
    """
    svc = _svc()
    deleted = 0
    for table in ("mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens"):
        q = svc.table(table).delete().eq("client_id", client_id)
        if user_id is not None:
            q = q.eq("user_id", user_id)
        res = q.execute()
        deleted += len(res.data or [])
    logger.info(
        "[ADR-386/431] evicted client %s (user=%s) — %d OAuth token rows deleted",
        client_id, user_id or "all", deleted,
    )
    return deleted


def ensure_principal_grant(
    principal_id: str,
    workspace_id: str,
    role: str,
    scopes: Optional[list[str]] = None,
    granted_by: str = "system:adr386-lifecycle",
    connected_by: Optional[str] = None,
) -> dict:
    """Lazily ensure an active grant for (principal_id, workspace_id, connected_by)
    (ADR-386 D1 + ADR-431 D2).

    Idempotent on the ACTIVE partial-unique key, which ADR-431 widened to include
    `connected_by`: a foreign-LLM grant's identity is (provider, workspace, the
    connecting member). So two members connecting the same provider produce two
    grants — the second no longer no-ops onto the first. For human/agent grants
    `connected_by` is redundant (the index coalesces it to `principal_id`), so
    their behavior is byte-identical to pre-431.

    Returns the grant row dict. Best-effort at the call site (the OAuth hook
    wraps it so a failure never breaks the connect flow — the consult still
    falls back to the class default, ADR-386 §6.3).
    """
    svc = _svc()
    # Idempotency key mirrors the widened unique index (ADR-431): a distinct
    # connecting member is a distinct grant. `connected_by IS NULL` is matched
    # explicitly so a NULL-connected grant (human/agent) stays a singleton.
    q = (
        svc.table("principal_grants")
        .select("id, principal_id, workspace_id, role, scopes, status, connected_by")
        .eq("principal_id", principal_id)
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
    )
    q = q.eq("connected_by", connected_by) if connected_by else q.is_("connected_by", "null")
    existing = q.limit(1).execute()
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
            "connected_by": connected_by,  # ADR-431 — the authorizing member
        })
        .execute()
    )
    logger.info(
        "[ADR-386/431] auto-provisioned %s grant for principal=%s workspace=%s connected_by=%s",
        role, principal_id, workspace_id, connected_by,
    )
    return (inserted.data or [{}])[0]


def _load_active_grant(
    principal_id: str,
    workspace_id: str,
    connected_by: Optional[str] = None,
) -> Optional[dict]:
    """Load the active grant for a principal (ADR-431: disambiguated by the
    connecting member when given).

    `connected_by=None` preserves the pre-431 lookup (first active grant for the
    pair) — correct for the human/owner path (a singleton) and for lifecycle
    callers that name the provider without a member. When a specific member's
    connection is targeted (multi-member same-provider), pass `connected_by` to
    select that member's row.
    """
    q = (
        _svc()
        .table("principal_grants")
        .select("id, role, scopes, status, connected_by")
        .eq("principal_id", principal_id)
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
    )
    if connected_by is not None:
        q = q.eq("connected_by", connected_by)
    rows = q.limit(1).execute().data
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
    write_scopes: Optional[list[str]],
    connected_by: Optional[str] = None,
    read_scopes: Optional[list[str]] = _UNSET,
) -> dict:
    """Set a member's read + write scope axes (ADR-386 D2 NARROW; powerbox 2026-07-10).

    TWO INDEPENDENT AXES, each a list of PATH PREFIXES at arbitrary depth
    (`operation/`, `operation/marketing/`, `operation/reports/q3.md`). Polarity
    per axis: None → class default (unconfigured); [] → explicit deny-all;
    [..] → allow-list.

    `read_scopes` defaults to _UNSET → "read ⊇ write" (read mirrors write) — the
    common case and the byte-identical-to-ADR-373 default. Pass an explicit list
    (or []) to move the read axis independently (a read-only auditor: write=[],
    read=['operation/']).

    Authz-only: the OAuth token is untouched (the member stays connected); the
    gate then bounds BOTH reads and writes to the granted prefixes. The legacy
    `scopes` column is written as a transition mirror of write_scopes.

    ADR-431 D4: `connected_by` targets a specific member's grant. Rejects the
    owner grant (ADR-386 D4) → OwnerGrantImmutable. ValueError if no active grant.
    """
    grant = _load_active_grant(principal_id, workspace_id, connected_by)
    if grant is None:
        raise ValueError("no active grant for this principal in this workspace")
    if grant.get("role") == "owner":
        raise OwnerGrantImmutable("the owner grant cannot be narrowed")

    # read ⊇ write default: unspecified read axis mirrors write.
    effective_read = write_scopes if read_scopes is _UNSET else read_scopes

    updated = (
        _svc()
        .table("principal_grants")
        .update({
            "write_scopes": write_scopes,
            "read_scopes": effective_read,
            "scopes": write_scopes,  # deprecated mirror (= write) for the transition
        })
        .eq("id", grant["id"])
        .execute()
    )
    logger.info(
        "[POWERBOX] narrowed grant principal=%s workspace=%s write=%s read=%s",
        principal_id, workspace_id, write_scopes, effective_read,
    )
    return (updated.data or [{}])[0]


def evict_principal(
    principal_id: str,
    workspace_id: str,
    connected_by: Optional[str] = None,
) -> dict:
    """REVOKE = full eviction (ADR-386 D2/D3 + ADR-431 D4).

    Two coupled effects:
      1. flip the grant to `status='revoked'` (the audit record of the eviction);
      2. delete the principal's OAuth access + refresh tokens — the principal can
         no longer authenticate, read, or write.

    ADR-431 D4: `connected_by` targets a SPECIFIC member's connection when the
    same provider is connected by several members — and the token sweep then
    scopes to that member's tokens (by `user_id`), so revoking "seulkim's
    ChatGPT" leaves the owner's ChatGPT connected. When `connected_by` is None
    (owner/human singleton, or a legacy provider-wide revoke) the sweep is
    provider-wide (pre-431 behavior).

    Because a revoked principal has no token, it never reaches the gate, so the
    consult needs no `revoked`-aware branch (ADR-386 D3). Reconnecting requires
    a fresh OAuth authorize, which re-auto-provisions a new active grant (D1).

    Rejects the owner grant (ADR-386 D4) — raises OwnerGrantImmutable.
    Raises ValueError if no active grant exists for the pair.
    """
    grant = _load_active_grant(principal_id, workspace_id, connected_by)
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
    # we fall back to deleting by the principal_id directly. ADR-431 D4: scope
    # the delete to the connecting member's tokens (`token_user`) so a co-member
    # sharing the provider is not disconnected. Best-effort: a token-delete
    # failure must not leave the grant un-revoked — the status flip already
    # happened above.
    tokens_deleted = 0
    # The grant's own connected_by (persisted) is authoritative for the token
    # scope even when the caller passed None (the singleton lookup still found
    # a member-owned grant).
    token_user = connected_by or grant.get("connected_by")
    try:
        role = grant.get("role")
        client_ids: list[str] = []
        if role in ("foreign-llm", "platform", "a2a"):
            client_ids = client_ids_for_provider(workspace_id, principal_id)
        # Fallback: a legacy client_id-keyed grant (or unknown provider) — the
        # principal_id IS the client_id, so delete by it directly.
        for cid in (client_ids or [principal_id]):
            tokens_deleted += delete_tokens_for_client(cid, token_user)
    except Exception as exc:  # pragma: no cover — best-effort token sweep
        logger.warning(
            "[ADR-386] token eviction for principal=%s failed: %s "
            "(grant already revoked; principal can't write, but tokens linger)",
            principal_id, exc,
        )

    logger.info(
        "[ADR-386/431] evicted principal=%s workspace=%s connected_by=%s (grant revoked, %d tokens deleted)",
        principal_id, workspace_id, token_user, tokens_deleted,
    )
    return {"principal_id": principal_id, "status": "revoked", "tokens_deleted": tokens_deleted}


def cascade_member_ai_connections(member_id: str, workspace_id: str) -> list[dict]:
    """Revoke the AI connections a departing member authorized (ADR-431 D5).

    When a human member is evicted, the foreign-LLM / a2a / platform grants they
    connected (`connected_by = member_id`) go with them — a member's departure
    takes their AI connections. Each is a full eviction (grant revoked + the
    member's tokens for that provider deleted, D4-scoped).

    Called by the member-revoke route AFTER the member's own grant is revoked.
    Best-effort per connection; returns the list of eviction results. Owner is
    never a `connected_by` target for eviction (owner grants are immutable,
    ADR-386 D4), so no owner AI connection is ever orphaned this way.
    """
    rows = (
        _svc()
        .table("principal_grants")
        .select("principal_id, role, connected_by")
        .eq("workspace_id", workspace_id)
        .eq("connected_by", member_id)
        .eq("status", "active")
        .in_("role", ["foreign-llm", "a2a", "platform"])
        .execute()
    ).data or []
    results = []
    for r in rows:
        try:
            results.append(evict_principal(r["principal_id"], workspace_id, member_id))
        except Exception as exc:  # pragma: no cover — best-effort cascade
            logger.warning(
                "[ADR-431 D5] cascade revoke of %s (connected_by %s) failed: %s",
                r["principal_id"], member_id, exc,
            )
    if results:
        logger.info(
            "[ADR-431 D5] member %s eviction cascaded to %d AI connection(s)",
            member_id, len(results),
        )
    return results
