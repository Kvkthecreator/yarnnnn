"""
Webhook handlers for external integrations.

Endpoints:
- POST /user-signup - Handle new user signup notifications from Supabase
- POST /resend/events - Handle Resend delivery outcome webhooks

ADR-131: Gmail push notifications removed (sunset).
ADR-271: Slack event-trigger endpoint removed (pre-ADR-261 task pipeline dead path).
"""

import os
import json
import base64
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional, List, Any

import httpx
from fastapi import APIRouter, Request, HTTPException, status
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


def _decode_resend_secret(secret: str) -> bytes:
    """
    Decode Resend webhook secret for HMAC verification.

    Resend uses Svix-style secrets (`whsec_...`) where the suffix is base64.
    """
    raw = (secret or "").strip()
    if raw.startswith("whsec_"):
        raw = raw[6:]
    try:
        return base64.b64decode(raw)
    except Exception:
        # Fallback to raw bytes for local/dev secrets.
        return raw.encode("utf-8")


def verify_resend_signature(
    payload: bytes,
    svix_id: str,
    svix_timestamp: str,
    svix_signature: str,
) -> bool:
    """
    Verify Resend webhook signature (Svix format).

    Headers:
      - svix-id
      - svix-timestamp
      - svix-signature (one or more `v1,<base64>` values)
    """
    secret = os.environ.get("RESEND_WEBHOOK_SECRET")
    if not secret:
        log.warning("RESEND_WEBHOOK_SECRET not configured - skipping verification")
        return True

    if not svix_id or not svix_timestamp or not svix_signature:
        return False

    signed = f"{svix_id}.{svix_timestamp}.{payload.decode('utf-8')}"
    expected = base64.b64encode(
        hmac.new(_decode_resend_secret(secret), signed.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")

    signatures: list[str] = []
    for part in svix_signature.split():
        if part.startswith("v1,"):
            signatures.append(part.split(",", 1)[1])

    if not signatures and svix_signature.startswith("v1,"):
        signatures.append(svix_signature.split(",", 1)[1])

    return any(hmac.compare_digest(sig, expected) for sig in signatures)


def _map_resend_event_to_delivery_status(event_type: str) -> Optional[str]:
    """Map Resend event types to agent_runs.delivery_status values."""
    normalized = (event_type or "").lower()
    if normalized == "email.delivered":
        return "delivered"
    if normalized in {"email.bounced", "email.complained"}:
        return "failed"
    return None


def _map_resend_event_to_log_status(event_type: str) -> str:
    """Map Resend event type to email_delivery_log.status."""
    normalized = (event_type or "").lower()
    if normalized.startswith("email."):
        return normalized.split(".", 1)[1]
    return normalized or "unknown"


def _extract_resend_message_id(payload: dict[str, Any]) -> Optional[str]:
    """Extract provider message ID from Resend webhook payload."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return data.get("email_id") or data.get("id") or payload.get("email_id")


def _extract_recipient(
    data: dict[str, Any],
    destination: Optional[dict[str, Any]],
) -> Optional[str]:
    """Extract recipient from webhook payload, fallback to export destination."""
    to_value = data.get("to")
    if isinstance(to_value, list) and to_value:
        return str(to_value[0])
    if isinstance(to_value, str) and to_value:
        return to_value

    if isinstance(destination, dict):
        target = destination.get("target")
        if isinstance(target, str) and target:
            return target

    return None


def _merge_export_outcome(
    existing: Any,
    event_type: str,
    payload: dict[str, Any],
    observed_at: str,
) -> dict[str, Any]:
    """Merge a new webhook event into export_log.outcome."""
    event_entry = {
        "event_type": event_type,
        "observed_at": observed_at,
        "provider_event_id": payload.get("id"),
    }
    current = existing if isinstance(existing, dict) else {}
    history = current.get("events", [])
    if not isinstance(history, list):
        history = []
    history = (history + [event_entry])[-10:]
    return {
        **current,
        "provider": "resend",
        "latest_event": event_entry,
        "events": history,
    }


def _record_resend_webhook(payload: dict[str, Any]) -> int:
    """
    Persist Resend webhook outcome onto export_log and related run status.

    Returns number of export_log rows updated.
    """
    from services.supabase import get_service_client

    message_id = _extract_resend_message_id(payload)
    if not message_id:
        log.warning("[RESEND_WEBHOOK] Missing message ID in payload")
        return 0

    event_type = payload.get("type", "unknown")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    observed_at = (
        payload.get("created_at")
        or data.get("created_at")
        or datetime.now(timezone.utc).isoformat()
    )
    delivery_status = _map_resend_event_to_delivery_status(event_type)
    email_log_status = _map_resend_event_to_log_status(event_type)

    client = get_service_client()
    rows = (
        client.table("export_log")
        .select("id, agent_run_id, destination, outcome")
        .eq("provider", "email")
        .eq("external_id", message_id)
        .execute()
    )
    export_rows = rows.data or []

    if not export_rows:
        log.warning(
            f"[RESEND_WEBHOOK] No export_log row matched message_id={message_id}, event={event_type}"
        )
        return 0

    for row in export_rows:
        outcome = _merge_export_outcome(row.get("outcome"), event_type, payload, observed_at)
        (
            client.table("export_log")
            .update({
                "outcome": outcome,
                "outcome_observed_at": observed_at,
            })
            .eq("id", row["id"])
            .execute()
        )

        if delivery_status:
            run_update = {"delivery_status": delivery_status}
            if delivery_status == "failed":
                run_update["delivery_error"] = f"Email provider event: {event_type}"
            (
                client.table("agent_runs")
                .update(run_update)
                .eq("id", row["agent_run_id"])
                .execute()
            )

        recipient = _extract_recipient(data, row.get("destination"))
        if recipient:
            try:
                client.table("email_delivery_log").insert({
                    "scheduled_message_id": None,
                    "recipient": recipient,
                    "subject": data.get("subject"),
                    "provider": "resend",
                    "provider_message_id": message_id,
                    "status": email_log_status,
                    "status_updated_at": observed_at,
                }).execute()
            except Exception as e:
                # Non-fatal (legacy table, optional observability sink)
                log.warning(f"[RESEND_WEBHOOK] Failed to write email_delivery_log: {e}")

    return len(export_rows)


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
# Resend Webhook Events (Email Delivery Outcomes)
# =============================================================================


@router.post("/resend/events")
async def handle_resend_events(request: Request):
    """
    Handle Resend webhook events and persist post-send outcomes.

    This updates:
    - export_log.outcome / outcome_observed_at
    - agent_runs.delivery_status for terminal failures (bounce/complaint)
    - email_delivery_log (best-effort observability sink)
    """
    body = await request.body()
    svix_id = request.headers.get("svix-id", "")
    svix_timestamp = request.headers.get("svix-timestamp", "")
    svix_signature = request.headers.get("svix-signature", "")

    if os.environ.get("RESEND_WEBHOOK_SECRET"):
        if not verify_resend_signature(body, svix_id, svix_timestamp, svix_signature):
            log.warning("[RESEND_WEBHOOK] Invalid signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    processed = _record_resend_webhook(payload)
    return {"ok": True, "processed": processed}


# =============================================================================
# ADR-031 Phase 4: Slack Events API Webhook
# =============================================================================

# ADR-131: Gmail push notification endpoint removed (sunset)
# ADR-271: Slack event-trigger endpoint removed (pre-ADR-261 task pipeline dead path)
