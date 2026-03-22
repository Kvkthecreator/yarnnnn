"""
Event Trigger Service - ADR-031 Phase 4, ADR-040

Handles event-driven agent triggering from platform events.

Supports:
- Slack events (mentions, DMs, channel messages)
- Notion events (page changes) [future]

ADR-131: Gmail events removed (sunset).

Event Flow:
1. Platform webhook → event_triggers.handle_event()
2. Match event to agents with matching trigger config
3. Apply cooldown/throttle rules (ADR-040: database-backed)
4. Queue matched agents for processing

Usage:
    from services.event_triggers import (
        handle_slack_event,
        get_agents_for_event,
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
    """Slack event types that can trigger agents."""
    APP_MENTION = "app_mention"       # @bot mention in channel
    MESSAGE_IM = "message_im"         # DM to bot
    MESSAGE_CHANNEL = "message"       # Message in subscribed channel
    REACTION_ADDED = "reaction_added" # Reaction on a message


class NotionEventType(str, Enum):
    """Notion event types that can trigger agents."""
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
    Event trigger configuration for an agent.

    Stored in agent.trigger_config when trigger_type='event'.
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
    """A matched agent for an event."""
    agent_id: str
    agent_title: str
    user_id: str
    should_skip: bool = False
    skip_reason: Optional[str] = None


# =============================================================================
# Cooldown Management - ADR-040: Database-backed cooldown
# =============================================================================

def _get_cooldown_key(
    agent_id: str,
    cooldown_type: str,
    event: PlatformEvent,
) -> str:
    """Generate a unique cooldown key based on config type."""
    if cooldown_type == "per_thread":
        return f"{agent_id}:thread:{event.thread_id or event.resource_id}"
    elif cooldown_type == "per_channel":
        return f"{agent_id}:channel:{event.resource_id}"
    elif cooldown_type == "per_sender":
        return f"{agent_id}:sender:{event.sender_id or 'unknown'}"
    else:  # global
        return f"{agent_id}:global"


async def check_cooldown_db(
    db_client,
    agent_id: str,
    cooldown: CooldownConfig,
    event: PlatformEvent,
) -> tuple[bool, Optional[str]]:
    """
    Check if an agent is in cooldown for this event.

    ADR-040: Uses database (event_trigger_log) instead of in-memory cache.

    Returns:
        Tuple of (is_in_cooldown, reason)
    """
    key = _get_cooldown_key(agent_id, cooldown.type, event)
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
    agent_id: str,
    cooldown: CooldownConfig,
    event: PlatformEvent,
    result: str = "executed",
    skip_reason: Optional[str] = None,
) -> None:
    """
    Record that an agent was triggered for cooldown tracking.

    ADR-040: Logs to event_trigger_log table for audit and cooldown tracking.
    """
    key = _get_cooldown_key(agent_id, cooldown.type, event)

    try:
        db_client.table("event_trigger_log").insert({
            "user_id": event.user_id,
            "agent_id": agent_id,
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

async def get_agents_for_event(
    db_client,
    event: PlatformEvent,
) -> list[TriggerMatch]:
    """
    Find agents that should trigger for this event.

    Queries agents where:
    - trigger_type = 'event'
    - trigger_config matches the event platform and resource
    - status = 'active'

    Returns list of matched agents with cooldown status.
    """
    # Query agents with event triggers for this user
    result = (
        db_client.table("agents")
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
            agent_id=row["id"],
            agent_title=row["title"],
            user_id=row["user_id"],
            should_skip=should_skip,
            skip_reason=skip_reason,
        ))

    logger.info(
        f"[EVENT_TRIGGER] Matched {len(matches)} agents for "
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
    Handle incoming Slack event and find matching agents.

    Args:
        db_client: Supabase client
        event_payload: Raw Slack event payload

    Returns:
        List of matched agents
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

    return await get_agents_for_event(db_client, event)


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
    Execute matched agents that aren't in cooldown.

    Args:
        db_client: Supabase client
        matches: List of matched agents
        event: The triggering event

    Returns:
        Dict with execution summary
    """
    from services.trigger_dispatch import dispatch_trigger

    executed = 0
    skipped = 0
    errors = []

    for match in matches:
        if match.should_skip:
            logger.info(
                f"[EVENT_TRIGGER] Skipping {match.agent_title}: {match.skip_reason}"
            )
            skipped += 1
            continue

        try:
            # Get full agent for execution
            agent_result = (
                db_client.table("agents")
                .select("*")
                .eq("id", match.agent_id)
                .single()
                .execute()
            )
            if not agent_result.data:
                errors.append(f"Agent not found: {match.agent_id}")
                continue

            agent = agent_result.data

            # ADR-088: Route through dispatch — event triggers accumulate context (medium)
            result = await dispatch_trigger(
                client=db_client,
                agent=agent,
                trigger_type="event",
                trigger_context={
                    "type": "event",
                    "platform": event.platform,
                    "event_type": event.event_type,
                    "resource_id": event.resource_id,
                    "event_ts": event.event_ts.isoformat(),
                    "content_preview": event.content_preview,
                },
                signal_strength="medium",
            )

            if result.get("success"):
                executed += 1

                # ADR-040: Record trigger to database for cooldown tracking
                cooldown_config = agent.get("trigger_config", {}).get("cooldown")
                if cooldown_config:
                    cooldown = CooldownConfig(
                        type=cooldown_config.get("type", "global"),
                        duration_minutes=cooldown_config.get("duration_minutes", 5),
                    )
                    await record_trigger_db(db_client, match.agent_id, cooldown, event, result="executed")

                logger.info(f"[EVENT_TRIGGER] ✓ Executed {match.agent_title}")
            else:
                # Log failed trigger
                cooldown_config = agent.get("trigger_config", {}).get("cooldown")
                if cooldown_config:
                    cooldown = CooldownConfig(
                        type=cooldown_config.get("type", "global"),
                        duration_minutes=cooldown_config.get("duration_minutes", 5),
                    )
                    await record_trigger_db(
                        db_client, match.agent_id, cooldown, event,
                        result="failed", skip_reason=result.get("error")
                    )
                errors.append(f"{match.agent_title}: {result.get('error')}")

        except Exception as e:
            logger.error(f"[EVENT_TRIGGER] ✗ Failed {match.agent_title}: {e}")
            errors.append(f"{match.agent_title}: {str(e)}")

    return {
        "executed": executed,
        "skipped": skipped,
        "errors": errors,
    }
