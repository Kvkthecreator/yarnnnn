"""
Notification Service - ADR-040

Lightweight notification delivery via email (Resend).
Background notifications also insert a message into the user's chat session
for continuity when they return.

This service handles:
1. Persisting notification records for audit
2. Sending email notifications
3. Respecting user notification preferences
4. Inserting chat messages for background notifications
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    """Result of a notification send attempt."""
    id: str
    status: Literal["sent", "pending", "failed"]
    error: Optional[str] = None


async def send_notification(
    db_client,
    user_id: str,
    message: str,
    channel: Literal["email", "in_app"] = "email",
    urgency: Literal["low", "normal", "high"] = "normal",
    context: Optional[dict] = None,
    source_type: Literal["system", "monitor", "tp", "deliverable", "event_trigger", "suggestion"] = "system",
    source_id: Optional[str] = None,
) -> NotificationResult:
    """
    Send a notification to a user.

    For email: Sends via Resend and logs to notifications table.
    For in_app: Just logs to notifications table (TP handles display).

    Args:
        db_client: Supabase client (service role)
        user_id: Target user
        message: Notification text
        channel: Delivery channel (email or in_app)
        urgency: Priority level
        context: Optional related context (deliverable_id, url, etc.)
        source_type: What triggered this notification
        source_id: ID of triggering entity

    Returns:
        NotificationResult with status
    """
    # Create notification record
    try:
        notification = db_client.table("notifications").insert({
            "user_id": user_id,
            "message": message,
            "channel": channel,
            "urgency": urgency,
            "context": context or {},
            "source_type": source_type,
            "source_id": source_id,
            "status": "pending",
        }).execute()

        notification_id = notification.data[0]["id"]
    except Exception as e:
        logger.error(f"[NOTIFICATION] Failed to create record: {e}")
        return NotificationResult(id="", status="failed", error=str(e))

    # Deliver based on channel
    try:
        if channel == "email":
            # Check user preferences
            from jobs.unified_scheduler import should_send_email, get_user_email

            # Map source_type to notification preference type
            pref_type_map = {
                "deliverable": "deliverable_ready",
                "system": "deliverable_ready",  # Default to deliverable_ready for system
                "tp": "deliverable_ready",
                "event_trigger": "deliverable_ready",
                "monitor": "deliverable_ready",
                "suggestion": "suggestion_created",  # ADR-060
            }
            pref_type = pref_type_map.get(source_type, "deliverable_ready")

            if not await should_send_email(db_client, user_id, pref_type):
                logger.info(f"[NOTIFICATION] Skipped (user opted out): {message[:50]}...")
                _update_notification_status(db_client, notification_id, "sent")  # Mark as sent (opted out)
                return NotificationResult(id=notification_id, status="sent")

            user_email = await get_user_email(db_client, user_id)
            if not user_email:
                logger.warning(f"[NOTIFICATION] No email for user {user_id}")
                _update_notification_status(db_client, notification_id, "failed", "No email address")
                return NotificationResult(id=notification_id, status="failed", error="No email address")

            # Send email
            result = await _send_notification_email(
                to=user_email,
                message=message,
                urgency=urgency,
                context=context,
            )

            if result.success:
                _update_notification_status(db_client, notification_id, "sent")
                logger.info(f"[NOTIFICATION] Sent email to {user_email}: {message[:50]}...")

                # Insert message into chat session for continuity (background notifications only)
                # Skip if source_type is 'tp' since that means user is in active session
                if source_type != "tp":
                    await _insert_chat_notification(
                        db_client=db_client,
                        user_id=user_id,
                        message=message,
                        context=context,
                    )

                return NotificationResult(id=notification_id, status="sent")
            else:
                _update_notification_status(db_client, notification_id, "failed", result.error)
                return NotificationResult(id=notification_id, status="failed", error=result.error)

        elif channel == "in_app":
            # In-app notifications are just logged - TP session handles display
            _update_notification_status(db_client, notification_id, "sent")
            logger.info(f"[NOTIFICATION] Logged in-app: {message[:50]}...")
            return NotificationResult(id=notification_id, status="sent")

        else:
            _update_notification_status(db_client, notification_id, "failed", f"Unknown channel: {channel}")
            return NotificationResult(id=notification_id, status="failed", error=f"Unknown channel: {channel}")

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


async def _insert_chat_notification(
    db_client,
    user_id: str,
    message: str,
    context: Optional[dict],
) -> None:
    """
    Insert a notification message into the user's chat session.

    This ensures background notifications appear in chat history when user returns.
    Uses the daily session scope so the message appears in their current/recent session.
    """
    try:
        # Get or create user's daily session
        session_result = db_client.rpc(
            "get_or_create_chat_session",
            {
                "p_user_id": user_id,
                "p_project_id": None,
                "p_session_type": "thinking_partner",
                "p_scope": "daily"
            }
        ).execute()

        if not session_result.data:
            logger.warning(f"[NOTIFICATION] Could not get session for user {user_id}")
            return

        session_id = session_result.data.get("session_id")
        if not session_id:
            logger.warning(f"[NOTIFICATION] No session_id in result for user {user_id}")
            return

        # Format the notification as a TP message
        chat_message = f"📧 I sent you an email: {message}"

        # Append as assistant message with notification metadata
        db_client.rpc(
            "append_session_message",
            {
                "p_session_id": session_id,
                "p_role": "assistant",
                "p_content": chat_message,
                "p_metadata": {
                    "type": "notification",
                    "channel": "email",
                    "context": context or {},
                }
            }
        ).execute()

        logger.info(f"[NOTIFICATION] Inserted chat message for user {user_id}")

    except Exception as e:
        # Non-fatal - notification was still sent, just not shown in chat
        logger.warning(f"[NOTIFICATION] Failed to insert chat message: {e}")


async def _send_notification_email(
    to: str,
    message: str,
    urgency: str,
    context: Optional[dict],
) -> "EmailResult":
    """Send a notification email via Resend."""
    from jobs.email import send_email, EmailResult
    import os

    app_url = os.environ.get("APP_URL", "https://yarnnn.com")

    # Build context-aware CTA if available
    cta_html = ""
    cta_text = ""
    if context:
        if context.get("deliverable_id"):
            url = f"{app_url}/dashboard/deliverable/{context['deliverable_id']}"
            cta_html = f'<a href="{url}" style="display: inline-block; background: #111; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 6px; margin-top: 16px;">View Deliverable</a>'
            cta_text = f"\nView: {url}"
        elif context.get("url"):
            cta_html = f'<a href="{context["url"]}" style="display: inline-block; background: #111; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 6px; margin-top: 16px;">View Details</a>'
            cta_text = f"\nView: {context['url']}"

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
            <a href="{app_url}/dashboard/settings" style="color: #888;">Manage notifications</a>
        </p>
    </body>
    </html>
    """

    text = f"""{message}
{cta_text}

— yarnnn
Manage notifications: {app_url}/dashboard/settings
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


async def get_user_notifications(
    db_client,
    user_id: str,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Get notifications for a user.

    Args:
        db_client: Supabase client
        user_id: User ID
        status: Filter by status (optional)
        limit: Max notifications to return

    Returns:
        List of notification records
    """
    query = db_client.table("notifications")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .limit(limit)

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data or []


# =============================================================================
# Convenience functions for common notification scenarios
# =============================================================================

async def notify_deliverable_ready(
    db_client,
    user_id: str,
    deliverable_id: str,
    deliverable_title: str,
) -> NotificationResult:
    """Send notification when a deliverable is ready for review."""
    return await send_notification(
        db_client=db_client,
        user_id=user_id,
        message=f'"{deliverable_title}" is ready for review.',
        channel="email",
        urgency="normal",
        context={"deliverable_id": deliverable_id},
        source_type="deliverable",
        source_id=deliverable_id,
    )


async def notify_deliverable_delivered(
    db_client,
    user_id: str,
    deliverable_id: str,
    deliverable_title: str,
    destination: str,
    external_url: Optional[str] = None,
) -> NotificationResult:
    """Send notification when a deliverable has been delivered."""
    context = {"deliverable_id": deliverable_id, "destination": destination}
    if external_url:
        context["url"] = external_url

    return await send_notification(
        db_client=db_client,
        user_id=user_id,
        message=f'"{deliverable_title}" was delivered to {destination}.',
        channel="email",
        urgency="low",
        context=context,
        source_type="deliverable",
        source_id=deliverable_id,
    )


async def notify_deliverable_failed(
    db_client,
    user_id: str,
    deliverable_id: str,
    deliverable_title: str,
    error: str,
) -> NotificationResult:
    """Send notification when a deliverable generation/delivery fails."""
    return await send_notification(
        db_client=db_client,
        user_id=user_id,
        message=f'Failed to generate "{deliverable_title}": {error[:100]}',
        channel="email",
        urgency="high",
        context={"deliverable_id": deliverable_id, "error": error},
        source_type="deliverable",
        source_id=deliverable_id,
    )


async def notify_event_triggered(
    db_client,
    user_id: str,
    deliverable_id: str,
    deliverable_title: str,
    event_type: str,
    platform: str,
) -> NotificationResult:
    """Send notification when an event triggers a deliverable."""
    return await send_notification(
        db_client=db_client,
        user_id=user_id,
        message=f'"{deliverable_title}" was triggered by a {platform} {event_type}.',
        channel="email",
        urgency="low",
        context={"deliverable_id": deliverable_id, "platform": platform, "event_type": event_type},
        source_type="event_trigger",
        source_id=deliverable_id,
    )


# =============================================================================
# ADR-060: Suggested Deliverable Notifications
# =============================================================================

async def notify_suggestion_created(
    db_client,
    user_id: str,
    suggestion_count: int,
    titles: list[str],
) -> NotificationResult:
    """
    Send notification when new deliverable suggestions are created.

    ADR-060: Background Conversation Analyst creates suggestions from patterns.
    Users receive a summary notification to review in /deliverables.
    """
    import os
    app_url = os.environ.get("APP_URL", "https://yarnnn.com")

    if suggestion_count == 1:
        message = f'I noticed a pattern in your conversations and suggested a new deliverable: "{titles[0]}". Review it in your deliverables.'
    else:
        titles_str = ", ".join(f'"{t}"' for t in titles[:3])
        if len(titles) > 3:
            titles_str += f" and {len(titles) - 3} more"
        message = f"I noticed {suggestion_count} patterns in your conversations and suggested new deliverables: {titles_str}. Review them in your deliverables."

    return await send_notification(
        db_client=db_client,
        user_id=user_id,
        message=message,
        channel="email",
        urgency="low",
        context={"url": f"{app_url}/deliverables", "suggestion_count": suggestion_count},
        source_type="suggestion",  # ADR-060: Uses email_suggestion_created preference
        source_id=None,
    )
