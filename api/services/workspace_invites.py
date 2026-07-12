"""Workspace member invites — ADR-404 step 5 (ADR-373 D4 provisioning UX).

The provisioning path that makes the `member` role live: the owner invites
a human by email; accepting converts the invite into an active
`principal_grants` row (role='member', class-default scopes per ADR-373
D3) via the ADR-386 lifecycle helper. The grant — not the invite — is the
authorization fact; invites are transport.

Witness-dial note (ADR-405): a member's grant arrives with the class
default (operation/ + agents/ write regions, after-witness). Narrowing is
the existing ADR-386 verb on the members roster.

Service-client only (RLS: service-role-only on workspace_invites — the
routes do their own owner checks; the accept path authenticates the
acceptor's JWT and matches the invited email).
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

INVITE_TTL_DAYS = 14


class InviteError(Exception):
    """Invite lifecycle violation (not found / expired / wrong email / state)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _svc():
    from services.supabase import get_service_client
    return get_service_client()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def workspace_owner_id(workspace_id: str) -> Optional[str]:
    rows = (
        _svc().table("workspaces")
        .select("owner_id")
        .eq("id", workspace_id)
        .limit(1)
        .execute()
    ).data or []
    return rows[0]["owner_id"] if rows else None


def create_invite(
    *, workspace_id: str, email: str, invited_by: str, role: str = "member"
) -> dict[str, Any]:
    """Create (or refresh) a pending invite for an email.

    One pending invite per (workspace, email): re-inviting the same address
    revokes the prior pending invite and mints a fresh token/expiry — the
    "resend" affordance without a second verb.
    """
    email_norm = email.strip().lower()
    if not email_norm or "@" not in email_norm:
        raise InviteError("invalid_email", f"Not an email address: {email!r}")
    if role != "member":
        raise InviteError("invalid_role", "Only the member role is invitable (ADR-373 D4)")

    svc = _svc()

    # ADR-445 §6/§7 — the free→paid boundary gate. This is the ONLY headcount gate:
    # a FREE workspace is solo (included_seats: 1 = the owner); inviting a 2nd human
    # requires the paid plan. A PAID workspace grows its team freely — each new human
    # is a billed seat (ADR-445 §4), never blocked. So the gate fires ONLY on tiers
    # that offer no in-tier paid resolution, i.e. `free`. Projected human count =
    # active human members + still-pending invites + this one. AI principals are
    # never gated (free, §3); exempt workspaces grow freely. Fails CLOSED only on a
    # confident over-count on a free tier — a read error fails OPEN (never block a
    # legit invite over a transient DB hiccup).
    try:
        from services.billing_tiers import (
            DEFAULT_TIER,
            HUMAN_SEAT_ROLES,
            PAID_TIERS,
            normalize_tier,
            tier_included_seats,
        )

        ws_row = (
            svc.table("workspaces")
            .select("subscription_tier, billing_exempt")
            .eq("id", workspace_id)
            .limit(1)
            .execute()
        ).data
        ws = ws_row[0] if ws_row else {}
        tier = normalize_tier(ws.get("subscription_tier") or DEFAULT_TIER)
        # A paid workspace grows freely — the seat axis bills the extra human, it
        # does not refuse the invite. Only a non-exempt FREE workspace is capped.
        if not ws.get("billing_exempt", False) and tier not in PAID_TIERS:
            included = tier_included_seats(tier)
            grants = (
                svc.table("principal_grants")
                .select("principal_id")
                .eq("workspace_id", workspace_id)
                .eq("status", "active")
                .in_("role", list(HUMAN_SEAT_ROLES))
                .execute()
            ).data or []
            human_members = len({g.get("principal_id") for g in grants if g.get("principal_id")})
            pending = (
                svc.table("workspace_invites")
                .select("email")
                .eq("workspace_id", workspace_id)
                .eq("status", "pending")
                .neq("email", email_norm)  # a re-invite of THIS email refreshes, not adds
                .execute()
            ).data or []
            projected = human_members + len(pending) + 1  # +1 for this invite
            if projected > included:
                raise InviteError(
                    "upgrade_required",
                    "The free plan is for one person. Upgrade to the paid plan "
                    "to invite your team into this workspace.",
                )
    except InviteError:
        raise
    except Exception:  # noqa: BLE001 — fail OPEN on a read error (never block a legit invite)
        pass

    svc.table("workspace_invites").update({"status": "revoked"}).eq(
        "workspace_id", workspace_id
    ).eq("email", email_norm).eq("status", "pending").execute()

    row = {
        "workspace_id": workspace_id,
        "email": email_norm,
        "role": role,
        "token": secrets.token_urlsafe(24),
        "invited_by": invited_by,
        "status": "pending",
        "expires_at": (_now() + timedelta(days=INVITE_TTL_DAYS)).isoformat(),
    }
    result = svc.table("workspace_invites").insert(row).execute()
    if not result.data:
        raise InviteError("insert_failed", "Failed to create invite")
    return result.data[0]


def list_invites(workspace_id: str) -> list[dict[str, Any]]:
    """Pending invites for the workspace, newest first."""
    return (
        _svc().table("workspace_invites")
        .select("id, email, role, status, created_at, expires_at")
        .eq("workspace_id", workspace_id)
        .eq("status", "pending")
        .order("created_at", desc=True)
        .execute()
    ).data or []


def revoke_invite(workspace_id: str, invite_id: str) -> bool:
    result = (
        _svc().table("workspace_invites")
        .update({"status": "revoked"})
        .eq("id", invite_id)
        .eq("workspace_id", workspace_id)
        .eq("status", "pending")
        .execute()
    )
    return bool(result.data)


def get_invite_by_token(token: str) -> Optional[dict[str, Any]]:
    """The invite + workspace name, for the accept page preview."""
    rows = (
        _svc().table("workspace_invites")
        .select("id, workspace_id, email, role, status, expires_at, invited_by, accepted_principal_id")
        .eq("token", token)
        .limit(1)
        .execute()
    ).data or []
    if not rows:
        return None
    invite = rows[0]
    ws = (
        _svc().table("workspaces")
        .select("name")
        .eq("id", invite["workspace_id"])
        .limit(1)
        .execute()
    ).data or []
    invite["workspace_name"] = ws[0].get("name") if ws else None
    return invite


def accept_invite(*, token: str, user_id: str, user_email: Optional[str]) -> dict[str, Any]:
    """Convert a pending invite into an active member grant (ADR-386 D1).

    The acceptor's authenticated email must match the invited address —
    the invite token authorizes the ADDRESS, the JWT proves the person.
    """
    invite = get_invite_by_token(token)
    if invite is None:
        raise InviteError("not_found", "Invite not found")
    if invite["status"] == "accepted" and invite.get("accepted_principal_id") == user_id:
        # Idempotent re-accept: the same person re-clicking the link just
        # re-binds and enters — never an error.
        return {
            "workspace_id": invite["workspace_id"],
            "workspace_name": invite.get("workspace_name"),
            "role": invite["role"],
            "grant_id": None,
        }
    if invite["status"] != "pending":
        raise InviteError("not_pending", f"Invite is {invite['status']}")
    expires = invite.get("expires_at")
    if expires and datetime.fromisoformat(str(expires).replace("Z", "+00:00")) < _now():
        _svc().table("workspace_invites").update({"status": "expired"}).eq(
            "id", invite["id"]
        ).execute()
        raise InviteError("expired", "Invite has expired")
    if not user_email or user_email.strip().lower() != invite["email"]:
        raise InviteError(
            "email_mismatch",
            f"This invite was sent to {invite['email']} — sign in with that address",
        )
    if workspace_owner_id(invite["workspace_id"]) == user_id:
        raise InviteError("already_owner", "You own this workspace")

    from services.principal_grants import ensure_principal_grant
    grant = ensure_principal_grant(
        principal_id=user_id,
        workspace_id=invite["workspace_id"],
        role=invite["role"],
        granted_by=f"invite:{invite['invited_by']}",
    )

    _svc().table("workspace_invites").update({
        "status": "accepted",
        "accepted_at": _now().isoformat(),
        "accepted_principal_id": user_id,
    }).eq("id", invite["id"]).execute()

    return {
        "workspace_id": invite["workspace_id"],
        "workspace_name": invite.get("workspace_name"),
        "role": invite["role"],
        "grant_id": grant.get("id"),
    }


async def send_invite_email(*, email: str, token: str, workspace_name: Optional[str], inviter_email: Optional[str]) -> bool:
    """Best-effort invite email over the system Resend wire (ADR-202 pointer-only)."""
    try:
        from jobs.email import send_email
        from services.deep_links import app_url

        link = f"{app_url()}/invite/{token}"
        ws = workspace_name or "a YARNNN workspace"
        who = inviter_email or "The workspace owner"
        result = await send_email(
            to=email,
            subject=f"You're invited to {ws} on YARNNN",
            html=(
                f"<p>{who} invited you to collaborate in <strong>{ws}</strong> "
                f"— a shared, attributed workspace.</p>"
                f'<p><a href="{link}">Accept the invite</a> '
                f"(valid {INVITE_TTL_DAYS} days).</p>"
                f"<p style=\"color:#888\">If you don't have a YARNNN account yet, "
                f"sign up with this email address first, then open the link.</p>"
            ),
            text=f"{who} invited you to {ws} on YARNNN. Accept: {link}",
        )
        return bool(getattr(result, "success", False) or getattr(result, "id", None))
    except Exception as exc:  # noqa: BLE001 — email is transport, never blocks the invite
        logger.warning("[INVITES] invite email send failed for %s: %s", email, exc)
        return False
