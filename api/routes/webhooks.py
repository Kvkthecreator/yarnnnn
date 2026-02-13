"""
Webhook handlers for external integrations.

ADR-031 Phase 4: Event Triggers

Endpoints:
- POST /user-signup - Handle new user signup notifications from Supabase
- POST /slack/events - Handle Slack Events API (ADR-031)
- POST /gmail/push - Handle Gmail push notifications (ADR-031)
"""

import os
import json
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional, List

import httpx
from fastapi import APIRouter, Request, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()
log = logging.getLogger(__name__)

# Environment configuration
SLACK_WEBHOOK_URL = os.environ.get("SLACK_SIGNUP_WEBHOOK_URL")
SUPABASE_WEBHOOK_SECRET = os.environ.get("SUPABASE_WEBHOOK_SECRET")
PLATFORM_NAME = os.environ.get("PLATFORM_NAME", "yarnnn")


async def send_slack_notification(message: str, blocks: Optional[List] = None) -> bool:
    """Send a notification to Slack."""
    if not SLACK_WEBHOOK_URL:
        log.warning("SLACK_SIGNUP_WEBHOOK_URL not configured - skipping notification")
        return False

    payload = {"text": message}
    if blocks:
        payload["blocks"] = blocks

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10.0,
            )
            if response.status_code == 200:
                log.info("Slack notification sent successfully")
                return True
            else:
                log.error(f"Slack notification failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        log.error(f"Failed to send Slack notification: {e}")
        return False


def verify_supabase_webhook(payload: bytes, signature: str) -> bool:
    """Verify Supabase webhook signature."""
    if not SUPABASE_WEBHOOK_SECRET:
        log.warning("SUPABASE_WEBHOOK_SECRET not configured - skipping verification")
        return True  # Allow if no secret configured

    expected = hmac.new(
        SUPABASE_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


@router.post("/user-signup")
async def handle_user_signup_webhook(request: Request):
    """
    Handle new user signup webhook from Supabase.

    Configure this in Supabase Dashboard:
    1. Go to Database -> Webhooks
    2. Create webhook on `auth.users` table for INSERT events
    3. Set URL to: https://yarnnn-api.onrender.com/webhooks/user-signup
    4. Add header: X-Webhook-Secret: <your-secret>
    """
    body = await request.body()
    signature = request.headers.get("X-Webhook-Secret", "")

    # Verify webhook signature if secret is configured
    if SUPABASE_WEBHOOK_SECRET:
        if not hmac.compare_digest(signature, SUPABASE_WEBHOOK_SECRET):
            log.warning("Invalid webhook signature for user-signup")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret",
            )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Extract user info from Supabase webhook payload
    # Supabase sends: { type: "INSERT", table: "users", schema: "auth", record: {...} }
    record = payload.get("record", {})
    event_type = payload.get("type", "")

    if event_type != "INSERT":
        # Only handle new signups
        return {"status": "ok", "message": "Ignored non-INSERT event"}

    user_id = record.get("id", "unknown")
    email = record.get("email", "unknown")
    created_at = record.get("created_at", "")
    provider = record.get("raw_app_meta_data", {}).get("provider", "email")

    log.info(f"New user signup: {email} (provider: {provider})")

    # Format timestamp
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        formatted_time = dt.strftime("%B %d, %Y at %I:%M %p UTC")
    except (ValueError, AttributeError):
        formatted_time = created_at or "Unknown time"

    # Send Slack notification with rich formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎉 New User Signup on {PLATFORM_NAME}!",
                "emoji": True,
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Platform:*\n{PLATFORM_NAME}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Email:*\n{email}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Provider:*\n{provider.title()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Signed up:*\n{formatted_time}"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{PLATFORM_NAME} • User ID: `{user_id[:8]}...`"
                }
            ]
        }
    ]

    await send_slack_notification(
        f"[{PLATFORM_NAME}] New user signup: {email} via {provider}",
        blocks=blocks,
    )

    return {"status": "ok", "message": "Notification sent"}


# =============================================================================
# ADR-031 Phase 4: Slack Events API Webhook
# =============================================================================

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")


def verify_slack_signature(
    body: bytes,
    timestamp: str,
    signature: str,
) -> bool:
    """
    Verify Slack request signature.

    Uses HMAC-SHA256 with Slack signing secret.
    """
    if not SLACK_SIGNING_SECRET:
        log.warning("SLACK_SIGNING_SECRET not configured - skipping verification")
        return True

    # Check timestamp to prevent replay attacks (5 min window)
    try:
        ts = int(timestamp)
        now = int(datetime.now().timestamp())
        if abs(now - ts) > 300:
            log.warning("Slack request timestamp too old")
            return False
    except ValueError:
        return False

    # Compute expected signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_sig = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        sig_basestring.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_sig)


async def process_slack_event(event_payload: dict):
    """
    Process a Slack event in the background.

    Finds matching deliverables and triggers execution.
    """
    from supabase import create_client
    from services.event_triggers import (
        handle_slack_event,
        execute_event_triggers,
        PlatformEvent,
    )

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        log.error("Supabase credentials not configured")
        return

    try:
        supabase = create_client(supabase_url, supabase_key)

        # Find matching deliverables
        matches = await handle_slack_event(supabase, event_payload)

        if matches:
            # Build event for execution
            event = PlatformEvent(
                platform="slack",
                event_type=event_payload.get("type", "message"),
                user_id=matches[0].user_id,  # All matches have same user
                resource_id=event_payload.get("channel", ""),
                resource_name=None,
                event_data=event_payload,
                event_ts=datetime.now(),
                thread_id=event_payload.get("thread_ts"),
                sender_id=event_payload.get("user"),
                content_preview=event_payload.get("text", "")[:200],
            )

            # Execute triggers
            result = await execute_event_triggers(supabase, matches, event)
            log.info(f"[SLACK_EVENT] Executed: {result}")

    except Exception as e:
        log.error(f"[SLACK_EVENT] Error processing event: {e}")


@router.post("/slack/events")
async def handle_slack_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Slack Events API webhook.

    This endpoint handles:
    1. URL verification challenge (required for Slack app setup)
    2. Event callbacks (app_mention, message, etc.)

    Configure in Slack App:
    1. Go to Event Subscriptions
    2. Enable Events
    3. Set Request URL to: https://your-api.com/webhooks/slack/events
    4. Subscribe to: app_mention, message.im, message.channels
    """
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    # Verify signature if secret is configured
    if SLACK_SIGNING_SECRET:
        if not verify_slack_signature(body, timestamp, signature):
            log.warning("[SLACK_EVENT] Invalid signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        log.info("[SLACK_EVENT] URL verification challenge received")
        return {"challenge": payload.get("challenge")}

    # Handle event callback
    if payload.get("type") == "event_callback":
        event = payload.get("event", {})
        event_type = event.get("type")

        log.info(f"[SLACK_EVENT] Received event: {event_type}")

        # Add team_id to event for user lookup
        event["team"] = payload.get("team_id")

        # Ignore bot messages to prevent loops
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            log.debug("[SLACK_EVENT] Ignoring bot message")
            return {"ok": True}

        # Process event in background
        background_tasks.add_task(process_slack_event, event)

        return {"ok": True}

    return {"ok": True}


# =============================================================================
# ADR-031 Phase 4: Gmail Push Notifications
# =============================================================================

async def process_gmail_notification(notification: dict, user_id: str):
    """
    Process a Gmail push notification in the background.

    Finds matching deliverables and triggers execution.
    """
    from supabase import create_client
    from services.event_triggers import (
        handle_gmail_event,
        execute_event_triggers,
        PlatformEvent,
    )

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        log.error("Supabase credentials not configured")
        return

    try:
        supabase = create_client(supabase_url, supabase_key)

        # Find matching deliverables
        matches = await handle_gmail_event(supabase, notification, user_id)

        if matches:
            # Build event for execution
            event = PlatformEvent(
                platform="gmail",
                event_type="new_message",
                user_id=user_id,
                resource_id="inbox",
                resource_name="Inbox",
                event_data=notification,
                event_ts=datetime.now(),
            )

            # Execute triggers
            result = await execute_event_triggers(supabase, matches, event)
            log.info(f"[GMAIL_EVENT] Executed: {result}")

    except Exception as e:
        log.error(f"[GMAIL_EVENT] Error processing notification: {e}")


@router.post("/gmail/push")
async def handle_gmail_push(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Gmail Push Notification webhook.

    Gmail push notifications use Google Cloud Pub/Sub.
    The notification contains a base64-encoded message with historyId.

    Configure in Google Cloud:
    1. Create Pub/Sub topic for Gmail
    2. Create push subscription pointing to this endpoint
    3. Call Gmail watch() to subscribe to changes

    Note: This requires the user_id to be embedded in the push subscription
    endpoint URL or decoded from the notification data.
    """
    import base64

    body = await request.body()

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Extract Pub/Sub message
    message = payload.get("message", {})
    data_b64 = message.get("data", "")

    if not data_b64:
        log.warning("[GMAIL_PUSH] No data in message")
        return {"ok": True}

    try:
        data = json.loads(base64.b64decode(data_b64))
    except (json.JSONDecodeError, ValueError) as e:
        log.error(f"[GMAIL_PUSH] Failed to decode message data: {e}")
        return {"ok": True}

    email_address = data.get("emailAddress")
    history_id = data.get("historyId")

    log.info(f"[GMAIL_PUSH] Notification for {email_address}, historyId={history_id}")

    # Look up YARNNN user from email
    # In production, this would query platform_connections table
    user_id = await _lookup_user_from_gmail(email_address)

    if user_id:
        background_tasks.add_task(
            process_gmail_notification,
            {"historyId": history_id, "emailAddress": email_address},
            user_id,
        )

    return {"ok": True}


async def _lookup_user_from_gmail(email_address: str) -> Optional[str]:
    """
    Look up YARNNN user ID from Gmail email address.

    Uses the platform_connections table to find the user.
    """
    from supabase import create_client

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        return None

    try:
        supabase = create_client(supabase_url, supabase_key)

        result = (
            supabase.table("platform_connections")
            .select("user_id, metadata")
            .eq("platform", "gmail")
            .eq("status", "connected")
            .execute()
        )

        for row in result.data or []:
            metadata = row.get("metadata", {})
            if metadata.get("email") == email_address:
                return row["user_id"]

        return None

    except Exception as e:
        log.error(f"[GMAIL_LOOKUP] Failed to lookup user: {e}")
        return None
