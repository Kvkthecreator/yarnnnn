"""Notification transport — email via Resend (ADR-593 recut of ADR-489/ADR-040).

The axiom (ADR-593): **apps declare semantics, the kernel derives emission,
the OS routes/presents/manages.** In-app attention is pure derivation (the
bell + Notifications surface mount the workspace timeline + witness queue —
ADR-410; nothing here feeds them). This module is the OUTBOUND seam only.

The `notifications` table is TRANSPORT ONLY (ADR-405 D3 / ADR-410 D3): a row
records an outbound send to a recipient principal, workspace-stamped
(ADR-407 D8). Rows are written only when a send actually happens.

`send_notification` is the ONE chokepoint for system-Resend email to a
principal (ADR-593 D3): it gates by the recipient's per-kind dial, records,
then sends. Named exemptions — the workspace invite (recipient is a raw email
address; no principal exists yet) and the account test email (an explicitly
requested diagnostic to self). Everything else that emails a principal routes
here; the ADR-593 gate enforces the `jobs.email` import roster.

Preference gating reads member_state['notification_prefs'] — the ONE prefs
store (ADR-489 D5, keying preserved: per (workspace, principal) — mute one
commons, not all). Shape (ADR-593 D2):

    { "email": { "decisions": "all"|"high"|"none", "reports": "all"|"none",
                 "mentions": "all"|"none" } }

Only WIRED kinds are accepted (validate_notification_prefs — the member-state
PUT 422s on anything else). The gate FAILS CLOSED: if the store cannot be
read, no send happens (emailing someone who chose 'none' because the store
hiccuped is a correctness violation; a missed courtesy email is a
degradation).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# ADR-593 D1 — the kind registry: declared semantics, ONE owner per kind.
#
# `owner` is 'kernel' or an app slug. A kind has exactly one owner — that is
# what stops the per-app double-count (Files/Text/Studio all display the same
# file edit; the substrate act belongs to the kernel and appears once) and
# keeps ADR-405 D5's "no subscription matrix" intact.
#
# `email_default` None = DECLARED, NOT WIRED: no live send path exists, so the
# pane renders a named refusal (`email_note`) instead of a dial. A dial the
# code doesn't honor is the F1 defect this ADR repaired — never ship one.
# =============================================================================
NOTIFICATION_KINDS: list[dict] = [
    {
        "key": "decisions",
        "owner": "kernel",
        "label": "Decisions & activity",
        "description": "Proposals awaiting you, and teammates' or agents' acts in this workspace.",
        "email_default": "high",  # all | high | none — the ADR-489 D4 witness dial, renamed
        "email_note": None,
    },
    {
        "key": "reports",
        "owner": "kernel",
        "label": "Reports",
        "description": "Recurring reports the workspace produces for you (today: the daily reconciliation).",
        "email_default": "none",  # opt-in preserved from the _preferences.yaml era (ADR-593 D4)
        "email_note": None,
    },
    {
        "key": "mentions",
        "owner": "chat",
        "label": "Mentions",
        "description": "When someone — a teammate or an agent — @mentions you in a conversation.",
        # WIRED (ADR-605): the mention stamp lands at the turn write
        # (routes/lanes.py → services/mentions.py) and the email rides this
        # chokepoint. Default 'none' — OPT-IN, operator-ruled 2026-08-25:
        # internal notifications stabilize to a comprehensive level BEFORE
        # outbound expansion; email is machinery a member turns on, never a
        # default the system assumes. (The first cut shipped 'all' for one
        # deploy — an unflagged upgrade of the aligned "if they've opted in"
        # wording; recorded in ADR-605's amendment note.) The suppression
        # window (≤1 per recipient+conversation per EMAIL_SUPPRESSION_MINUTES,
        # derived from the transport ledger) still guards whoever opts in.
        "email_default": "none",
        "email_note": None,
    },
    {
        "key": "runs",
        "owner": "agents",
        "label": "Agent runs",
        "description": "Run failures and completions.",
        "email_default": None,  # failures already reach the bell as material (ADR-489 D1)
        "email_note": "In-app only — failures already surface in the bell. Email lands when a real send path exists.",
    },
]

# Derived, never hand-kept beside the registry.
EMAIL_DIAL_DEFAULTS: dict = {
    k["key"]: k["email_default"] for k in NOTIFICATION_KINDS if k["email_default"]
}

# The wired kinds + the ungated-but-recorded direct kind (ADR-593 D3).
NotificationKind = Literal["decisions", "reports", "mentions", "direct"]

_VALID_DIALS = ("all", "high", "none")


def validate_notification_prefs(value) -> list[str]:
    """Shape-check a notification_prefs value (ADR-593 D2). Returns errors.

    Only wired kinds, only known dials — a typo'd enum is refused at the
    door, never stored as permanent silence.
    """
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["notification_prefs must be an object"]
    unknown_top = set(value.keys()) - {"email"}
    if unknown_top:
        errors.append(f"unknown keys: {sorted(unknown_top)}")
    email = value.get("email", {})
    if not isinstance(email, dict):
        return errors + ["'email' must be an object of kind -> dial"]
    for kind, dial in email.items():
        if kind not in EMAIL_DIAL_DEFAULTS:
            errors.append(f"unknown or unwired kind: {kind}")
        elif dial not in _VALID_DIALS:
            errors.append(f"invalid dial for {kind}: {dial!r} (expected one of {list(_VALID_DIALS)})")
    return errors


@dataclass
class NotificationResult:
    """Result of a notification send attempt."""
    id: str
    status: Literal["sent", "pending", "failed", "skipped"]
    error: Optional[str] = None


async def get_notification_prefs(
    client, user_id: str, workspace_id: Optional[str] = None
) -> Optional[dict]:
    """The recipient's notification prefs — member_state['notification_prefs']
    keyed (workspace, principal), defaults when unset (ADR-489 D5).

    Returns None when the store CANNOT BE READ — the caller must fail closed
    (ADR-593 D3). An unset row is not an error: it reads the defaults.
    """
    try:
        ws = workspace_id
        if not ws:
            from services.workspace_context import effective_workspace_id
            ws = effective_workspace_id(user_id)
        if not ws:
            # No workspace resolves → no commons to be told about; quiet.
            return {"email": dict(EMAIL_DIAL_DEFAULTS)}
        row = (
            client.table("member_state")
            .select("value")
            .eq("workspace_id", ws)
            .eq("principal_id", user_id)
            .eq("key", "notification_prefs")
            .limit(1)
            .execute()
        )
        email = dict(EMAIL_DIAL_DEFAULTS)
        if row.data:
            value = row.data[0].get("value") or {}
            if isinstance(value, dict) and isinstance(value.get("email"), dict):
                for kind, dial in value["email"].items():
                    if kind in EMAIL_DIAL_DEFAULTS and dial in _VALID_DIALS:
                        email[kind] = dial
        return {"email": email}
    except Exception as e:
        logger.error("[NOTIFICATION] prefs read failed for %s — failing closed: %s", user_id[:8], e)
        return None


def _pref_allows(prefs: Optional[dict], kind: NotificationKind, urgency: str) -> bool:
    """The gate (ADR-593 D3). prefs=None means the store was unreadable →
    fail closed. 'direct' is ungated by policy (an explicitly instructed
    operator-addressed act — the instruction is the consent) but still
    recorded by send_notification."""
    if kind == "direct":
        return True
    if prefs is None:
        return False
    dial = (prefs.get("email") or {}).get(kind, EMAIL_DIAL_DEFAULTS.get(kind, "none"))
    if dial == "all":
        return True
    if dial == "high":
        return urgency == "high"
    return False


async def send_notification(
    db_client,
    user_id: str,
    message: str,
    *,
    kind: NotificationKind,
    urgency: Literal["low", "normal", "high"] = "normal",
    context: Optional[dict] = None,
    source_type: str = "system",
    source_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    subject: Optional[str] = None,
    html: Optional[str] = None,
    text: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> NotificationResult:
    """Send one email notification to one recipient principal.

    The ONE chokepoint (ADR-593 D3): gate by the recipient's per-kind dial →
    write the transport row → send. Pref-gated BEFORE any row is written; the
    row records an actual send attempt (workspace-stamped, ADR-407 D8).
    Callers with a composed email pass subject/html(/text); otherwise the
    standard pointer template renders from `message` (ADR-202: pointer-only).
    """
    try:
        if not workspace_id:
            from services.workspace_context import effective_workspace_id
            workspace_id = effective_workspace_id(user_id)
    except Exception:
        workspace_id = None

    prefs = await get_notification_prefs(db_client, user_id, workspace_id)
    if not _pref_allows(prefs, kind, urgency):
        reason = "prefs unreadable — failing closed" if prefs is None else f"dial quiet for kind={kind}"
        logger.info(f"[NOTIFICATION] Skipped ({reason}): {message[:50]}...")
        return NotificationResult(id="", status="skipped")

    from jobs.unified_scheduler import get_user_email

    user_email = await get_user_email(db_client, user_id)
    if not user_email:
        logger.warning(f"[NOTIFICATION] No email for user {user_id}")
        return NotificationResult(id="", status="failed", error="No email address")

    # Transport record — written because a send is actually happening.
    try:
        row = {
            "user_id": user_id,
            "message": message,
            "channel": "email",
            "urgency": urgency,
            "context": context or {},
            "source_type": source_type,
            "source_id": source_id,
            "status": "pending",
        }
        if workspace_id:
            row["workspace_id"] = workspace_id
        notification = db_client.table("notifications").insert(row).execute()
        notification_id = notification.data[0]["id"]
    except Exception as e:
        logger.error(f"[NOTIFICATION] Failed to create transport record: {e}")
        return NotificationResult(id="", status="failed", error=str(e))

    try:
        if html is not None:
            from jobs.email import send_email
            result = await send_email(
                to=user_email,
                subject=subject or message.split("\n")[0][:60],
                html=html,
                text=text,
                reply_to=reply_to,
            )
        else:
            result = await _send_notification_email(
                to=user_email,
                message=message,
                urgency=urgency,
                context=context,
            )
        if result.success:
            _update_notification_status(db_client, notification_id, "sent")
            logger.info(f"[NOTIFICATION] Sent email to {user_email}: {message[:50]}...")
            return NotificationResult(id=notification_id, status="sent")
        _update_notification_status(db_client, notification_id, "failed", result.error)
        return NotificationResult(id=notification_id, status="failed", error=result.error)
    except Exception as e:
        logger.error(f"[NOTIFICATION] Delivery failed: {e}")
        _update_notification_status(db_client, notification_id, "failed", str(e))
        return NotificationResult(id=notification_id, status="failed", error=str(e))


def _update_notification_status(
    db_client,
    notification_id: str,
    status: str,
    error: Optional[str] = None,
) -> None:
    """Update notification status in database."""
    try:
        update = {"status": status}
        if status == "sent":
            update["sent_at"] = datetime.now(timezone.utc).isoformat()
        if error:
            update["error_message"] = error

        db_client.table("notifications").update(update).eq("id", notification_id).execute()
    except Exception as e:
        logger.warning(f"[NOTIFICATION] Failed to update status: {e}")


async def _send_notification_email(
    to: str,
    message: str,
    urgency: str,
    context: Optional[dict],
) -> "EmailResult":
    """Send a notification email via Resend."""
    from jobs.email import send_email, EmailResult
    from services.deep_links import app_url as _app_url, team_url, review_url, overview_url

    app_url = _app_url()

    # Build context-aware CTA if available.
    # ADR-202 §2: notifications are pointer-only — deep-link CTA, never
    # action-on-email button. All routes go through deep_links helpers.
    cta_html = ""
    cta_text = ""
    if context:
        # ADR-194 Phase 2a: proposal notifications link into the Queue pane
        # of Overview (or specific proposal on Review).
        if context.get("proposal_id"):
            url = review_url(proposal=context["proposal_id"])
            cta_label = "Review in cockpit"
        # ADR-201: agent notifications now route to /team?agent=<slug>
        elif context.get("agent_slug"):
            url = team_url(agent=context["agent_slug"])
            cta_label = "View agent"
        elif context.get("agent_id"):
            # Legacy: agent_id instead of slug — frontend redirects. Preserved
            # for callers that don't yet pass slug.
            url = team_url(agent=context["agent_id"])
            cta_label = "View agent"
        elif context.get("url"):
            # Pre-built deep-link from caller — honor it.
            url = context["url"]
            cta_label = "View details"
        else:
            url = overview_url()
            cta_label = "Open cockpit"
        cta_html = f'<a href="{url}" style="display: inline-block; background: #111; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 6px; margin-top: 16px;">{cta_label}</a>'
        cta_text = f"\nView: {url}"

    # Urgency affects subject prefix
    subject_prefix = ""
    if urgency == "high":
        subject_prefix = "[Action Required] "

    # ADR-593 D5: the manage link lands on the Notifications pane itself.
    manage_url = f"{app_url}/settings?settings.pane=notification-settings"

    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <p style="color: #333; font-size: 16px; line-height: 1.5;">{message}</p>
        {cta_html}
        <p style="color: #888; font-size: 12px; margin-top: 32px;">
            — yarnnn
            <br>
            <a href="{manage_url}" style="color: #888;">Manage notifications</a>
        </p>
    </body>
    </html>
    """

    text = f"""{message}
{cta_text}

— yarnnn
Manage notifications: {manage_url}
"""

    # Use first line of message as subject (truncated)
    subject_line = message.split('\n')[0][:60]
    if len(message.split('\n')[0]) > 60:
        subject_line += "..."

    return await send_email(
        to=to,
        subject=f"{subject_prefix}{subject_line}",
        html=html,
        text=text,
    )
