"""
Event Trigger Service - ADR-031 Phase 4, ADR-040

Handles event-driven deliverable triggering from platform events.

Supports:
- Slack events (mentions, DMs, channel messages)
- Gmail events (new emails, thread updates)
- Notion events (page changes) [future]

Event Flow:
1. Platform webhook → event_triggers.handle_event()
2. Match event to deliverables with matching trigger config
3. Apply cooldown/throttle rules (ADR-040: database-backed)
4. Queue matched deliverables for processing

Usage:
    from services.event_triggers import (
        handle_slack_event,
        handle_gmail_event,
        get_deliverables_for_event,
    )
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Event Types
# =============================================================================

class SlackEventType(str, Enum):
    """Slack event types that can trigger deliverables."""
    APP_MENTION = "app_mention"       # @bot mention in channel
    MESSAGE_IM = "message_im"         # DM to bot
    MESSAGE_CHANNEL = "message"       # Message in subscribed channel
    REACTION_ADDED = "reaction_added" # Reaction on a message


class GmailEventType(str, Enum):
    """Gmail event types that can trigger deliverables."""
    NEW_MESSAGE = "new_message"       # New email received
    THREAD_UPDATE = "thread_update"   # Reply to existing thread


class NotionEventType(str, Enum):
    """Notion event types that can trigger deliverables."""
    PAGE_UPDATED = "page_updated"     # Page content changed
    DATABASE_ROW_ADDED = "row_added"  # New row in database


@dataclass
class PlatformEvent:
    """Normalized event from any platform."""
    platform: Literal["slack", "gmail", "notion"]
    event_type: str
    user_id: str            # YARNNN user ID (from integration lookup)
    resource_id: str        # Channel ID, label, page ID
    resource_name: Optional[str]
    event_data: dict        # Raw event payload
    event_ts: datetime      # When event occurred

    # Optional context
    thread_id: Optional[str] = None  # Thread ts for Slack, thread ID for Gmail
    sender_id: Optional[str] = None  # Who triggered the event
    sender_name: Optional[str] = None
    content_preview: Optional[str] = None


@dataclass
class CooldownConfig:
    """Cooldown configuration to prevent rapid re-triggering."""
    type: Literal["per_thread", "per_channel", "per_sender", "global"]
    duration_minutes: int = 5
    max_triggers_per_duration: int = 1


@dataclass
class EventTriggerConfig:
    """
    Event trigger configuration for a deliverable.

    Stored in deliverable.trigger_config when trigger_type='event'.
    """
    platform: Literal["slack", "gmail", "notion"]
    event_types: list[str]  # Which event types to respond to
    resource_ids: list[str]  # Which resources to monitor (channels, labels, pages)
    cooldown: Optional[CooldownConfig] = None

    # Optional filters
    sender_filter: Optional[list[str]] = None  # Only trigger for specific senders
    keyword_filter: Optional[list[str]] = None  # Only trigger if content contains keywords


@dataclass
class TriggerMatch:
    """A matched deliverable for an event."""
    deliverable_id: str
    deliverable_title: str
    user_id: str
    should_skip: bool = False
    skip_reason: Optional[str] = None


# =============================================================================
# Cooldown Management - ADR-040: Database-backed cooldown
# =============================================================================

def _get_cooldown_key(
    deliverable_id: str,
    cooldown_type: str,
    event: PlatformEvent,
) -> str:
    """Generate a unique cooldown key based on config type."""
    if cooldown_type == "per_thread":
        return f"{deliverable_id}:thread:{event.thread_id or event.resource_id}"
    elif cooldown_type == "per_channel":
        return f"{deliverable_id}:channel:{event.resource_id}"
    elif cooldown_type == "per_sender":
        return f"{deliverable_id}:sender:{event.sender_id or 'unknown'}"
    else:  # global
        return f"{deliverable_id}:global"


async def check_cooldown_db(
    db_client,
    deliverable_id: str,
    cooldown: CooldownConfig,
    event: PlatformEvent,
) -> tuple[bool, Optional[str]]:
    """
    Check if a deliverable is in cooldown for this event.

    ADR-040: Uses database (event_trigger_log) instead of in-memory cache.

    Returns:
        Tuple of (is_in_cooldown, reason)
    """
    key = _get_cooldown_key(deliverable_id, cooldown.type, event)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=cooldown.duration_minutes)

    try:
        result = db_client.table("event_trigger_log")\
            .select("triggered_at")\
            .eq("cooldown_key", key)\
            .gte("triggered_at", cutoff.isoformat())\
            .order("triggered_at", desc=True)\
            .limit(1)\
            .execute()

        if result.data:
            last_trigger = datetime.fromisoformat(result.data[0]["triggered_at"].replace("Z", "+00:00"))
            elapsed = now - last_trigger
            remaining = timedelta(minutes=cooldown.duration_minutes) - elapsed
            return True, f"Cooldown: {int(remaining.total_seconds() / 60)}m remaining"

        return False, None

    except Exception as e:
        logger.warning(f"[COOLDOWN] Database check failed, allowing trigger: {e}")
        return False, None


async def record_trigger_db(
    db_client,
    deliverable_id: str,
    cooldown: CooldownConfig,
    event: PlatformEvent,
    result: str = "executed",
    skip_reason: Optional[str] = None,
) -> None:
    """
    Record that a deliverable was triggered for cooldown tracking.

    ADR-040: Logs to event_trigger_log table for audit and cooldown tracking.
    """
    key = _get_cooldown_key(deliverable_id, cooldown.type, event)

    try:
        db_client.table("event_trigger_log").insert({
            "user_id": event.user_id,
            "deliverable_id": deliverable_id,
            "platform": event.platform,
            "event_type": event.event_type,
            "resource_id": event.resource_id,
            "event_data": event.event_data,
            "cooldown_key": key,
            "result": result,
            "skip_reason": skip_reason,
        }).execute()
    except Exception as e:
        logger.warning(f"[COOLDOWN] Failed to log trigger: {e}")


# =============================================================================
# Event Matching
# =============================================================================

async def get_deliverables_for_event(
    db_client,
    event: PlatformEvent,
) -> list[TriggerMatch]:
    """
    Find deliverables that should trigger for this event.

    Queries deliverables where:
    - trigger_type = 'event'
    - trigger_config matches the event platform and resource
    - status = 'active'

    Returns list of matched deliverables with cooldown status.
    """
    # Query deliverables with event triggers for this user
    result = (
        db_client.table("deliverables")
        .select("id, user_id, title, trigger_type, trigger_config, status")
        .eq("user_id", event.user_id)
        .eq("status", "active")
        .eq("trigger_type", "event")
        .execute()
    )

    matches = []

    for row in result.data or []:
        trigger_config = row.get("trigger_config", {})

        # Check platform match
        if trigger_config.get("platform") != event.platform:
            continue

        # Check event type match
        event_types = trigger_config.get("event_types", [])
        if event_types and event.event_type not in event_types:
            continue

        # Check resource match
        resource_ids = trigger_config.get("resource_ids", [])
        if resource_ids and event.resource_id not in resource_ids:
            continue

        # Check sender filter
        sender_filter = trigger_config.get("sender_filter")
        if sender_filter and event.sender_id not in sender_filter:
            continue

        # Check keyword filter
        keyword_filter = trigger_config.get("keyword_filter")
        if keyword_filter and event.content_preview:
            content_lower = event.content_preview.lower()
            if not any(kw.lower() in content_lower for kw in keyword_filter):
                continue

        # Check cooldown (ADR-040: database-backed)
        should_skip = False
        skip_reason = None

        cooldown_config = trigger_config.get("cooldown")
        if cooldown_config:
            cooldown = CooldownConfig(
                type=cooldown_config.get("type", "global"),
                duration_minutes=cooldown_config.get("duration_minutes", 5),
                max_triggers_per_duration=cooldown_config.get("max_triggers_per_duration", 1),
            )
            is_cooldown, reason = await check_cooldown_db(db_client, row["id"], cooldown, event)
            if is_cooldown:
                should_skip = True
                skip_reason = reason

        matches.append(TriggerMatch(
            deliverable_id=row["id"],
            deliverable_title=row["title"],
            user_id=row["user_id"],
            should_skip=should_skip,
            skip_reason=skip_reason,
        ))

    logger.info(
        f"[EVENT_TRIGGER] Matched {len(matches)} deliverables for "
        f"{event.platform}:{event.event_type} on {event.resource_id}"
    )

    return matches


# =============================================================================
# Platform-Specific Event Handlers
# =============================================================================

async def handle_slack_event(
    db_client,
    event_payload: dict,
) -> list[TriggerMatch]:
    """
    Handle incoming Slack event and find matching deliverables.

    Args:
        db_client: Supabase client
        event_payload: Raw Slack event payload

    Returns:
        List of matched deliverables
    """
    event_type = event_payload.get("type")

    # Extract event details based on type
    if event_type in ("app_mention", "message"):
        channel_id = event_payload.get("channel")
        user = event_payload.get("user")
        text = event_payload.get("text", "")
        ts = event_payload.get("ts")
        thread_ts = event_payload.get("thread_ts")

        # Determine if this is a DM
        channel_type = event_payload.get("channel_type")
        if channel_type == "im":
            event_type = "message_im"
    else:
        logger.debug(f"[SLACK_EVENT] Ignoring event type: {event_type}")
        return []

    # Look up YARNNN user from Slack team/user
    team_id = event_payload.get("team")
    yarnnn_user_id = await _lookup_user_from_slack(db_client, team_id, channel_id)

    if not yarnnn_user_id:
        logger.warning(f"[SLACK_EVENT] No YARNNN user found for Slack team {team_id}")
        return []

    # Build normalized event
    event = PlatformEvent(
        platform="slack",
        event_type=event_type,
        user_id=yarnnn_user_id,
        resource_id=channel_id,
        resource_name=None,  # Would need API call to get name
        event_data=event_payload,
        event_ts=datetime.fromtimestamp(float(ts), tz=timezone.utc) if ts else datetime.now(timezone.utc),
        thread_id=thread_ts,
        sender_id=user,
        content_preview=text[:200] if text else None,
    )

    return await get_deliverables_for_event(db_client, event)


async def handle_gmail_event(
    db_client,
    push_notification: dict,
    user_id: str,
) -> list[TriggerMatch]:
    """
    Handle incoming Gmail push notification and find matching deliverables.

    Args:
        db_client: Supabase client
        push_notification: Gmail push notification payload
        user_id: YARNNN user ID (from webhook routing)

    Returns:
        List of matched deliverables
    """
    # Gmail push notifications are minimal - they just indicate change
    # We need to fetch actual messages to determine event details
    history_id = push_notification.get("historyId")

    # For now, treat as generic new message event
    # Full implementation would fetch history and determine specific changes

    event = PlatformEvent(
        platform="gmail",
        event_type="new_message",
        user_id=user_id,
        resource_id="inbox",  # Would be determined by which labels changed
        resource_name="Inbox",
        event_data=push_notification,
        event_ts=datetime.now(timezone.utc),
    )

    return await get_deliverables_for_event(db_client, event)


# =============================================================================
# User Lookup Helpers
# =============================================================================

async def _lookup_user_from_slack(
    db_client,
    team_id: str,
    channel_id: str,
) -> Optional[str]:
    """
    Look up YARNNN user ID from Slack team/channel.

    Uses the platform_connections table to find the user.
    """
    try:
        # Query integrations with matching team_id in metadata
        result = (
            db_client.table("platform_connections")
            .select("user_id, metadata")
            .eq("platform", "slack")
            .eq("status", "connected")
            .execute()
        )

        for row in result.data or []:
            metadata = row.get("metadata", {})
            if metadata.get("team_id") == team_id:
                return row["user_id"]

        return None

    except Exception as e:
        logger.error(f"[SLACK_LOOKUP] Failed to lookup user: {e}")
        return None


# =============================================================================
# Trigger Execution
# =============================================================================

async def execute_event_triggers(
    db_client,
    matches: list[TriggerMatch],
    event: PlatformEvent,
) -> dict:
    """
    Execute matched deliverables that aren't in cooldown.

    Args:
        db_client: Supabase client
        matches: List of matched deliverables
        event: The triggering event

    Returns:
        Dict with execution summary
    """
    from services.deliverable_execution import execute_deliverable_generation

    executed = 0
    skipped = 0
    errors = []

    for match in matches:
        if match.should_skip:
            logger.info(
                f"[EVENT_TRIGGER] Skipping {match.deliverable_title}: {match.skip_reason}"
            )
            skipped += 1
            continue

        try:
            # Get full deliverable for execution
            deliverable_result = (
                db_client.table("deliverables")
                .select("*")
                .eq("id", match.deliverable_id)
                .single()
                .execute()
            )
            if not deliverable_result.data:
                errors.append(f"Deliverable not found: {match.deliverable_id}")
                continue

            deliverable = deliverable_result.data

            # ADR-042: Execute with simplified single-call flow
            result = await execute_deliverable_generation(
                client=db_client,
                user_id=match.user_id,
                deliverable=deliverable,
                trigger_context={
                    "type": "event",
                    "platform": event.platform,
                    "event_type": event.event_type,
                    "resource_id": event.resource_id,
                    "event_ts": event.event_ts.isoformat(),
                },
            )

            if result.get("success"):
                executed += 1

                # ADR-040: Record trigger to database for cooldown tracking
                cooldown_config = deliverable.get("trigger_config", {}).get("cooldown")
                if cooldown_config:
                    cooldown = CooldownConfig(
                        type=cooldown_config.get("type", "global"),
                        duration_minutes=cooldown_config.get("duration_minutes", 5),
                    )
                    await record_trigger_db(db_client, match.deliverable_id, cooldown, event, result="executed")

                logger.info(f"[EVENT_TRIGGER] ✓ Executed {match.deliverable_title}")
            else:
                # Log failed trigger
                cooldown_config = deliverable.get("trigger_config", {}).get("cooldown")
                if cooldown_config:
                    cooldown = CooldownConfig(
                        type=cooldown_config.get("type", "global"),
                        duration_minutes=cooldown_config.get("duration_minutes", 5),
                    )
                    await record_trigger_db(
                        db_client, match.deliverable_id, cooldown, event,
                        result="failed", skip_reason=result.get("error")
                    )
                errors.append(f"{match.deliverable_title}: {result.get('error')}")

        except Exception as e:
            logger.error(f"[EVENT_TRIGGER] ✗ Failed {match.deliverable_title}: {e}")
            errors.append(f"{match.deliverable_title}: {str(e)}")

    return {
        "executed": executed,
        "skipped": skipped,
        "errors": errors,
    }
