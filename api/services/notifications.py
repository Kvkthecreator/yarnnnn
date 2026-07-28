"""Notification transport — email via Resend (ADR-489 recut of ADR-040).

The `notifications` table is TRANSPORT ONLY (ADR-405 D3 / ADR-410 D3): a row
records an outbound send to a recipient principal, workspace-stamped
(ADR-407 D8). In-app attention is pure derivation — the bell + Notifications
surface mount the workspace timeline + witness queue; nothing here feeds
them. Rows are written only when a send actually happens (a transport record
records transport, not decisions not to send).

Preference gating reads member_state['notification_prefs'] — the ONE prefs
store (ADR-489 D5; the ADR-407 D7 fold executed; `user_notification_
preferences` dropped by migration 223):

    { "delivery_email": true, "failure_email": true, "witness_email": "high" }

`witness_email` ∈ 'all' | 'high' | 'none' is the after-witness push dial
(ADR-405 D2): the in-app bell stays the canonical after-witness channel;
email push is opt-in ('all') or reserved for high-urgency emissions
(default 'high' — quiet unless something demands it).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# ADR-489 D5 — the pref keys and their quiet defaults. Presentation-layer,
# never authorization (ADR-405 D5).
DEFAULT_NOTIFICATION_PREFS: dict = {
    "delivery_email": True,   # agent output delivered
    "failure_email": True,    # generation/delivery failed
    "witness_email": "high",  # after-witness peer-act push: all | high | none
}

PrefKind = Literal["delivery", "failure", "witness"]


@dataclass
class NotificationResult:
    """Result of a notification send attempt."""
    id: str
    status: Literal["sent", "pending", "failed"]
    error: Optional[str] = None


async def get_notification_prefs(
    client, user_id: str, workspace_id: Optional[str] = None
) -> dict:
    """The recipient's notification prefs — member_state['notification_prefs']
    keyed (workspace, principal), defaults when unset (ADR-489 D5)."""
    prefs = dict(DEFAULT_NOTIFICATION_PREFS)
    try:
        ws = workspace_id
        if not ws:
            from services.workspace_context import effective_workspace_id
            ws = effective_workspace_id(user_id)
        if not ws:
            return prefs
        row = (
            client.table("member_state")
            .select("value")
            .eq("workspace_id", ws)
            .eq("principal_id", user_id)
            .eq("key", "notification_prefs")
            .limit(1)
            .execute()
        )
        if row.data:
            value = row.data[0].get("value") or {}
            if isinstance(value, dict):
                prefs.update(value)
    except Exception as e:
        logger.warning("[NOTIFICATION] prefs read failed for %s: %s", user_id[:8], e)
    return prefs


def _pref_allows(prefs: dict, pref: PrefKind, urgency: str) -> bool:
    if pref == "delivery":
        return bool(prefs.get("delivery_email", True))
    if pref == "failure":
        return bool(prefs.get("failure_email", True))
    # witness — the after-witness push dial (ADR-489 D4).
    dial = prefs.get("witness_email", "high")
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
    urgency: Literal["low", "normal", "high"] = "normal",
    context: Optional[dict] = None,
    source_type: str = "system",
    source_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    pref: PrefKind = "delivery",
) -> NotificationResult:
    """Send one email notification to one recipient principal.

    The single writer into the `notifications` transport table. Pref-gated
    BEFORE any row is written; the row is the record of an actual send
    attempt (workspace-stamped, ADR-407 D8). Email is the only channel —
    the ADR-040 `in_app` branch is deleted (ADR-410 D3: in-app attention is
    derivation, never rows).
    """
    try:
        if not workspace_id:
            from services.workspace_context import effective_workspace_id
            workspace_id = effective_workspace_id(user_id)
    except Exception:
        workspace_id = None

    prefs = await get_notification_prefs(db_client, user_id, workspace_id)
    if not _pref_allows(prefs, pref, urgency):
        logger.info(f"[NOTIFICATION] Skipped (recipient opted out, pref={pref}): {message[:50]}...")
        return NotificationResult(id="", status="sent")

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

    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <p style="color: #333; font-size: 16px; line-height: 1.5;">{message}</p>
        {cta_html}
        <p style="color: #888; font-size: 12px; margin-top: 32px;">
            — yarnnn
            <br>
            <a href="{app_url}/settings" style="color: #888;">Manage notifications</a>
        </p>
    </body>
    </html>
    """

    text = f"""{message}
{cta_text}

— yarnnn
Manage notifications: {app_url}/settings
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


# =============================================================================
# Convenience functions for common notification scenarios
# =============================================================================

async def notify_agent_delivered(
    db_client,
    user_id: str,
    agent_id: str,
    agent_title: str,
    destination: str,
    external_url: Optional[str] = None,
    delivery_platform: Optional[str] = None,
) -> NotificationResult:
    """Send notification when an agent has been delivered.

    When delivery_platform is "email", the content email already landed in
    the recipient's inbox — the content IS the notification (ADR-040/066),
    and the delivery is already recorded in destination_delivery_log (the
    emissions Out lens). No email, no duplicate audit row (ADR-489 D5).
    """
    if delivery_platform == "email":
        logger.info(
            f"[NOTIFICATION] Skipped delivery notification — content delivered via {delivery_platform}"
        )
        return NotificationResult(id="", status="sent")

    context = {"agent_id": agent_id, "destination": destination}
    if external_url:
        context["url"] = external_url

    return await send_notification(
        db_client=db_client,
        user_id=user_id,
        message=f'"{agent_title}" was delivered to {destination}.',
        urgency="low",
        context=context,
        source_type="agent",
        source_id=agent_id,
        pref="delivery",
    )


async def notify_agent_failed(
    db_client,
    user_id: str,
    agent_id: str,
    agent_title: str,
    error: str,
) -> NotificationResult:
    """Send notification when an agent generation/delivery fails."""
    return await send_notification(
        db_client=db_client,
        user_id=user_id,
        message=f'Failed to generate "{agent_title}": {error[:100]}',
        urgency="high",
        context={"agent_id": agent_id, "error": error},
        source_type="agent",
        source_id=agent_id,
        pref="failure",
    )
