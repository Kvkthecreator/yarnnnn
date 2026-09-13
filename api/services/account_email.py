"""Account email — the always-on class (ADR-650).

The ADR-593 chokepoint governs email about WORKSPACE ACTIVITY: each kind has a
dial, opt-in or quiet, and the store is consulted before every send (§6, the
Layer-2 rule). Account correspondence is a different relationship. A welcome
cannot be opt-in — no preference exists before the account; a farewell cannot
be opt-in — no principal exists after it. The invite already set the precedent
(ADR-593 D3: "no principal exists yet to hold a pref"). ADR-650 generalises it
into one FIXED kind, ``account``: never dialled, always recorded, one owner
(the kernel), one composer (this module), one shell (``email_shell``).

Four events, one hook site each, all at the SERVICE layer where the act is:

  welcome          the ``inserted`` branch of ``ensure_owner_workspace``
                   (``services/supabase.py``) — fires once per account by
                   construction, so it needs no idempotency key of its own
  welcome_joined   ``accept_invite`` (``services/workspace_invites.py``) when
                   the grant is the principal's FIRST membership anywhere
  removed          ``evict_principal`` (``services/principal_grants.py``) for a
                   human ``member`` grant — the AI-connection cascade re-enters
                   with non-human roles and sends nothing
  account_deleted  ``DELETE /account/deactivate`` (``routes/account.py``) — the
                   address is resolved BEFORE the auth row goes and the mail is
                   sent AFTER the delete succeeds, to the raw address, over the
                   wire directly: the third named exemption to the D3 roster,
                   because ``notifications.user_id`` cascades on auth delete and
                   no transport row can outlive the principal. This module only
                   COMPOSES that one; the route (already on the roster) sends.

Execution is inline and best-effort (no worker, no queue — the platform rule):
``dispatch`` schedules the send on the running loop when there is one (an
async route) and on a daemon thread with its own loop when there is not (the
sync auth dependency runs in a threadpool). The act that triggered the mail
never waits on it and never fails for it.

Pointer-only (ADR-202): every mail carries one CTA into the product and a
footer that names why it arrived. User-supplied strings are escaped.
"""

from __future__ import annotations

import asyncio
import html as _html
import logging
import threading
from typing import Awaitable, Optional

from services.deep_links import notification_settings_url, overview_url
from services.email_shell import paragraph, render_email

logger = logging.getLogger(__name__)

KIND = "account"
SOURCE_TYPE = "account"

# A fire-and-forget task must be referenced until it finishes, or the loop may
# collect it mid-flight.
_pending: set = set()


# =============================================================================
# Dispatch — inline, non-blocking, never load-bearing for the act
# =============================================================================

async def _guarded(coro: Awaitable) -> None:
    try:
        await coro
    except Exception as e:  # noqa: BLE001 — mail failure is logged, never raised
        logger.warning("[ACCOUNT-EMAIL] send failed: %s", e)


def dispatch(coro: Awaitable) -> None:
    """Schedule one account email without blocking the caller.

    Running loop (an async route called the service directly) → a task on it.
    No loop (``get_user_client`` is a sync dependency, run in a threadpool) →
    a daemon thread runs the coroutine to completion on its own loop. Either
    way the request returns without waiting on Resend.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None:
        task = loop.create_task(_guarded(coro))
        _pending.add(task)
        task.add_done_callback(_pending.discard)
        return
    threading.Thread(
        target=lambda: asyncio.run(_guarded(coro)),
        name="account-email",
        daemon=True,
    ).start()


# =============================================================================
# Helpers
# =============================================================================

def _svc():
    from services.supabase import get_service_client
    return get_service_client()


def _workspace_label(workspace_id: Optional[str], fallback: Optional[str] = None) -> str:
    """The workspace's chosen name, or a generic phrase while it still wears
    the mint default (never leak "My Workspace" to someone it isn't "my" to)."""
    from services.supabase import display_workspace_name
    name = display_workspace_name(fallback)
    if name is None and workspace_id:
        try:
            rows = (
                _svc().table("workspaces").select("name").eq("id", workspace_id).limit(1).execute()
            ).data or []
            name = display_workspace_name(rows[0].get("name")) if rows else None
        except Exception as e:  # noqa: BLE001
            logger.warning("[ACCOUNT-EMAIL] workspace name read failed: %s", e)
    return name or "your workspace"


def _footer(reason: str) -> str:
    return (
        f"{reason} Account emails are always sent. "
        f'Emails about workspace activity are set on the '
        f'<a href="{notification_settings_url()}" style="color:inherit;">Notifications pane</a>.'
    )


def is_first_membership(user_id: str, workspace_id: str) -> bool:
    """True when the grant just minted in ``workspace_id`` is the principal's
    only active human grant and they own no workspace — their first day."""
    try:
        from services.supabase import resolve_owner_workspace_id
        if resolve_owner_workspace_id(user_id):
            return False
        rows = (
            _svc().table("principal_grants")
            .select("workspace_id")
            .eq("principal_id", user_id)
            .eq("status", "active")
            .in_("role", ["owner", "member"])
            .execute()
        ).data or []
        others = [r for r in rows if r.get("workspace_id") != workspace_id]
        return not others
    except Exception as e:  # noqa: BLE001 — an unreadable roster means no mail, never a wrong one
        logger.warning("[ACCOUNT-EMAIL] first-membership read failed for %s: %s", user_id[:8], e)
        return False


async def _send(
    user_id: str,
    *,
    workspace_id: Optional[str],
    message: str,
    subject: str,
    html: str,
    text: str,
):
    from services.notifications import send_notification
    return await send_notification(
        _svc(),
        user_id,
        message,
        kind=KIND,
        source_type=SOURCE_TYPE,
        workspace_id=workspace_id,
        subject=subject,
        html=html,
        text=text,
    )


# =============================================================================
# The four events
# =============================================================================

async def send_welcome(user_id: str, workspace_id: str):
    """Owner genesis — the account's first day."""
    home = overview_url()
    subject = "Welcome to yarnnn"
    html = render_email(
        preheader="Your workspace is ready.",
        heading="Your workspace is ready",
        body_html=(
            paragraph(
                "yarnnn is a shared workspace where every file records who changed it "
                "and every change can be walked back — yours, your teammates', and "
                "the agents you invite in."
            )
            + paragraph(
                "Start by dropping a file into <strong>Documents</strong>, or open a "
                "chat and ask for something."
            )
        ),
        cta_label="Open yarnnn",
        cta_url=home,
        footer_html=_footer("You're receiving this because an account was created with this address."),
    )
    text = (
        "Welcome to yarnnn.\n\n"
        "Your workspace is ready: a shared workspace where every file records who "
        "changed it and every change can be walked back.\n\n"
        f"Open yarnnn: {home}\n"
    )
    return await _send(
        user_id, workspace_id=workspace_id, message="Welcome to yarnnn",
        subject=subject, html=html, text=text,
    )


async def send_welcome_joined(user_id: str, workspace_id: str, workspace_name: Optional[str] = None):
    """First membership — the joiner's first day, named by the workspace they landed in."""
    ws = _html.escape(_workspace_label(workspace_id, workspace_name))
    home = overview_url()
    subject = f"You joined {ws}"
    html = render_email(
        preheader=f"You now hold a member grant in {ws}.",
        heading=f"You're in {ws}",
        body_html=(
            paragraph(
                f"You accepted an invite and now hold a member grant in <strong>{ws}</strong> "
                f"— a shared workspace where every change is recorded under the name of "
                f"whoever made it, yours included."
            )
            + paragraph("Open it to see what's there and where your work goes.")
        ),
        cta_label="Open the workspace",
        cta_url=home,
        footer_html=_footer("You're receiving this because you accepted an invite with this address."),
    )
    text = (
        f"You joined {ws} on yarnnn — a shared workspace where every change is "
        f"recorded under the name of whoever made it.\n\nOpen it: {home}\n"
    )
    return await _send(
        user_id, workspace_id=workspace_id, message=f"You joined {ws}",
        subject=subject, html=html, text=text,
    )


async def send_removed(user_id: str, workspace_id: str):
    """A human member's grant was revoked by the owner."""
    ws = _html.escape(_workspace_label(workspace_id))
    home = overview_url()
    subject = f"You were removed from {ws}"
    html = render_email(
        preheader=f"Your access to {ws} was revoked.",
        heading=f"Your access to {ws} ended",
        body_html=(
            paragraph(
                f"The owner of <strong>{ws}</strong> revoked your grant. You can no "
                f"longer open its files or conversations. Your own workspace and any "
                f"other memberships are unaffected."
            )
            + paragraph("If you think this was a mistake, ask the owner for a new invite.")
        ),
        cta_label="Open yarnnn",
        cta_url=home,
        footer_html=_footer("You're receiving this because a workspace you belonged to removed you."),
    )
    text = (
        f"Your access to {ws} on yarnnn ended: the owner revoked your grant. "
        f"Your own workspace and other memberships are unaffected.\n\n"
        f"If this was a mistake, ask the owner for a new invite.\n\nOpen yarnnn: {home}\n"
    )
    return await _send(
        user_id, workspace_id=workspace_id, message=f"You were removed from {ws}",
        subject=subject, html=html, text=text,
    )


def compose_account_deleted(email: str) -> tuple[str, str, str]:
    """The farewell — composed here, SENT by ``routes/account.py`` over the raw
    wire (the third ADR-593 D3 exemption: no principal remains to key a
    transport row). Returns (subject, html, text)."""
    addr = _html.escape(email)
    subject = "Your yarnnn account was deleted"
    html = render_email(
        preheader="Your account and its data have been removed.",
        heading="Your account is gone",
        body_html=(
            paragraph(
                f"The yarnnn account for <strong>{addr}</strong> was deleted, along with "
                f"its workspace files, their revision history, and its sign-in."
            )
            + paragraph(
                "If you didn't do this, sign up again with the same address and your "
                "account starts fresh — nothing from before is recoverable."
            )
        ),
        footer_html="This is the last email yarnnn sends to this address.",
    )
    text = (
        f"The yarnnn account for {email} was deleted, along with its workspace files, "
        f"their revision history, and its sign-in.\n\n"
        "If you didn't do this, sign up again with the same address; nothing from "
        "before is recoverable.\n"
    )
    return subject, html, text


__all__ = [
    "KIND",
    "dispatch",
    "is_first_membership",
    "send_welcome",
    "send_welcome_joined",
    "send_removed",
    "compose_account_deleted",
]
