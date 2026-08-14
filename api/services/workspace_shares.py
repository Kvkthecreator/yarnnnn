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


def _canonical_artifact_path(path: Optional[str]) -> Optional[str]:
    """ADR-517 D5 — ONE spelling for workspace_shares.artifact_path: absolute
    (`/workspace/…`, the substrate's own path identity). The write is the
    normalizer; readers must not compensate (migration 234 backfilled the
    historical rows, and the 2026-08-03 unrevocable-link defect class ends
    here)."""
    if not path:
        return None
    return path if path.startswith("/workspace/") else "/workspace/" + path.lstrip("/")


def assert_may_mint_share(user_id: str, workspace_id: str) -> None:
    """ADR-517 D3 — the mint-authority gate, called by BOTH origins (cockpit
    route + MCP `share` verb; species-blind per ADR-405).

    Minting a grant is governance ("anything that mutates WHO may act",
    routes/workspace.py::_require_owner_workspace) — so the free-for-all
    (ADR-437 D4 / ADR-408 D1) is narrowed:

      1. The owner always may.
      2. The workspace dial (`workspaces.share_mint_policy`): 'owner-only'
         refuses every non-owner.
      3. Otherwise write-holders mint: a `viewer`-role grant may not, and an
         explicit write-deny-all member (`write_scopes = []`) may not — a
         member narrowed to nothing is a viewer in fact.

    Raises ShareError('mint_forbidden', …) — the escalation door ADR-515 §6.1
    named (a read-only holder minting a member link) closes here.
    """
    if _workspace_owner_id(workspace_id) == user_id:
        return

    ws = (
        _svc().table("workspaces")
        .select("share_mint_policy")
        .eq("id", workspace_id)
        .limit(1)
        .execute()
    ).data or []
    if ws and (ws[0].get("share_mint_policy") or "write-holders") == "owner-only":
        raise ShareError(
            "mint_forbidden",
            "Only the workspace owner may create share links in this workspace",
        )

    grants = (
        _svc().table("principal_grants")
        .select("role, write_scopes")
        .eq("principal_id", user_id)
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    ).data or []
    if not grants:
        raise ShareError("mint_forbidden", "You do not have a grant to this workspace")
    grant = grants[0]
    if grant.get("role") == "viewer" or grant.get("write_scopes") == []:
        raise ShareError(
            "mint_forbidden",
            "A view-only grant cannot create share links (ADR-517: minting a "
            "grant is governance — ask the workspace owner)",
        )


def create_share(
    *,
    workspace_id: str,
    shared_by: str,
    artifact_path: Optional[str] = None,
    label: Optional[str] = None,
    ttl_days: Optional[int] = DEFAULT_SHARE_TTL_DAYS,
    role: str = "member",
) -> dict[str, Any]:
    """Mint a share link for an artifact (or a bare workspace share).

    Link-based: no per-recipient row. Re-sharing the same artifact mints a new
    link (multiple links to one artifact are fine — each is a durable token).

    Authorization is the CALLER's job: routes/shares.py and the MCP verb both
    call `assert_may_mint_share` first (ADR-517 D3).

    `role` is the grant SHAPE the sharer chose (ADR-465 D3, ratified 2026-08-02):
      - "member" (default) — accept mints the broad class-default grant.
      - "viewer" — accept mints a birth-narrowed viewer grant (write deny-all,
        read scoped to the artifact) so "just look at this" never over-grants.
    """
    if role not in ("member", "viewer"):
        raise ShareError("invalid_role", f"Unknown share role {role!r} (member|viewer)")
    expires_at = (
        (_now() + timedelta(days=ttl_days)).isoformat() if ttl_days else None
    )
    row = {
        "workspace_id": workspace_id,
        "artifact_path": _canonical_artifact_path(artifact_path),
        "label": label,
        "role": role,
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
    """Active share links for the workspace, newest first.

    ADR-534 D2 — the projection carries the TOKEN, so a caller can render the
    live link's URL. This is a deliberate widening of the AUTHENTICATED list,
    argued on its own rather than folded into a presentation change:

      1. the endpoint is already gated (`_acting_workspace` →
         `principal_reaches_workspace`);
      2. every caller who can list can already REVOKE — strictly more power
         over the same object than reading its URL;
      3. `create_share`'s response has always returned the link, so the shape
         is not new; a LIST of them is;
      4. a capability the owner cannot see is one they cannot audit
         (ADR-529 D1.2: "a link you cannot see is one you cannot verify").

    The PUBLIC projection (`SharePreviewResponse`, ADR-513 D2) is untouched —
    no token crosses to an anonymous reader. `test_adr534_standing_address.py`
    asserts both halves as a pair, so widening one without the other fails.
    """
    return (
        _svc().table("workspace_shares")
        .select("id, artifact_path, label, role, status, created_at, expires_at, last_accepted_at, token")
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .order("created_at", desc=True)
        .execute()
    ).data or []


def revoke_share(workspace_id: str, share_id: str, *, revoked_by: str) -> bool:
    """Revoke a share link — ADR-517 D4: the owner revokes any link; the
    minter revokes their own. (The prior any-grant-holder rule was the mint
    hole's mirror — a denial door instead of an escalation door.)

    Raises ShareError('revoke_forbidden', …) when the caller is neither.
    Returns False only when no active share matches (not-found semantics).
    """
    rows = (
        _svc().table("workspace_shares")
        .select("id, shared_by")
        .eq("id", share_id)
        .eq("workspace_id", workspace_id)
        .eq("status", "active")
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return False
    if revoked_by != rows[0].get("shared_by") and _workspace_owner_id(workspace_id) != revoked_by:
        raise ShareError(
            "revoke_forbidden",
            "Only the workspace owner or the link's creator may revoke it",
        )
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
    # Mint-default names read as UNNAMED (workspace identity phase 1) — the
    # share landing keeps its generic phrasing for an unnamed workspace.
    from services.supabase import display_workspace_name
    share["workspace_name"] = display_workspace_name(ws[0].get("name")) if ws else None
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

    # The grant shape follows the share row (ADR-465 D3):
    #   member → broad-by-default (ADR-437 D4.2): scopes=None → class-default
    #            member write regions at the gate (ADR-373 D3).
    #   viewer → role='viewer' (ADR-517 D1, amending ADR-437 D4.3's
    #            role-stays-member): the axes still carry the narrowing
    #            (write_scopes=[] deny-all; read_scopes scoped to the
    #            artifact), and now the DATABASE can see the shape it
    #            enforces — migration 234's write policies exclude
    #            viewer-role grants. Widening a viewer is a re-grant (role
    #            change by the owner), never an axes edit.
    # Either way ensure_principal_grant returns an EXISTING active grant
    # untouched, so a member who opens a view link is never downgraded.
    from services.principal_grants import ensure_principal_grant

    share_role = share.get("role") or "member"
    if share_role == "viewer":
        artifact = share.get("artifact_path")
        grant = ensure_principal_grant(
            principal_id=user_id,
            workspace_id=workspace_id,
            role="viewer",
            granted_by=f"share-view:{share['shared_by']}",
            write_scopes=[],
            read_scopes=[artifact] if artifact else None,
        )
    else:
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
        # The share's shape, not the grant row's role — the accept surface shows
        # the honest consequence ("View {artifact} — read-only" vs full access).
        "role": share_role,
        "grant_id": grant.get("id"),
    }
