"""
Webhook handlers for external integrations.

Endpoints:
- POST /user-signup - Handle new user signup notifications from Supabase
"""

import os
import json
import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional, List

import httpx
from fastapi import APIRouter, Request, HTTPException, status

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
