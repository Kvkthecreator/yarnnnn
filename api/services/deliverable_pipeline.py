"""
Deliverable Pipeline Execution Service

ADR-018: Recurring Deliverables Product Pivot
ADR-019: Deliverable Types System

Implements the 3-step chained pipeline:
1. Gather - Research agent pulls latest context from sources
2. Synthesize - Content agent produces the deliverable (type-aware)
3. Stage - Validate and notify user for review

Each step creates a work ticket with dependency chaining.
Type-specific prompts and validation ensure quality for each deliverable type.
"""

import logging
import json
import re
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Literal
from functools import lru_cache

from services.work_execution import execute_work_ticket

logger = logging.getLogger(__name__)


# =============================================================================
# ADR-030 Phase 6: Optimization - Caching and Model Selection
# =============================================================================

# In-memory cache for source fetches (TTL-based)
# Key: hash of (user_id, provider, source_query, time_range_start)
# Value: (SourceFetchResult, cached_at)
_source_fetch_cache: dict[str, tuple[any, datetime]] = {}
_CACHE_TTL_MINUTES = 15  # Cache integration fetches for 15 minutes

# Haiku model for cost-effective extraction
HAIKU_MODEL = "claude-3-5-haiku-20241022"
SONNET_MODEL = "claude-sonnet-4-20250514"


def _cache_key(user_id: str, provider: str, source_query: str, time_range_start: Optional[datetime]) -> str:
    """Generate a cache key for source fetch results."""
    time_str = time_range_start.isoformat() if time_range_start else "none"
    key_data = f"{user_id}:{provider}:{source_query}:{time_str}"
    return hashlib.md5(key_data.encode()).hexdigest()


def _get_cached_result(cache_key: str) -> Optional[any]:
    """Get cached result if not expired."""
    if cache_key not in _source_fetch_cache:
        return None
    result, cached_at = _source_fetch_cache[cache_key]
    if datetime.utcnow() - cached_at > timedelta(minutes=_CACHE_TTL_MINUTES):
        del _source_fetch_cache[cache_key]
        return None
    return result


def _set_cached_result(cache_key: str, result: any) -> None:
    """Cache a result with current timestamp."""
    _source_fetch_cache[cache_key] = (result, datetime.utcnow())
    # Cleanup old entries periodically (keep max 100 entries)
    if len(_source_fetch_cache) > 100:
        oldest_key = min(_source_fetch_cache, key=lambda k: _source_fetch_cache[k][1])
        del _source_fetch_cache[oldest_key]


async def extract_with_haiku(
    raw_content: str,
    extraction_goal: str,
    max_output_chars: int = 3000,
) -> str:
    """
    ADR-030 Phase 6: Use Haiku for cost-effective content extraction.

    Haiku is ~10x cheaper than Sonnet and faster for extraction tasks.
    Use this for:
    - Filtering noise from integration data
    - Summarizing large batches of messages
    - Extracting key information before synthesis

    Args:
        raw_content: Raw content from integration
        extraction_goal: What to extract (e.g., "decisions and action items")
        max_output_chars: Maximum output length

    Returns:
        Extracted/filtered content
    """
    from services.anthropic import chat_completion

    if not raw_content or len(raw_content) < 100:
        return raw_content

    # Truncate if too large for Haiku context
    if len(raw_content) > 50000:
        raw_content = raw_content[:50000] + "\n\n[Content truncated for processing]"

    system = f"""You are a context extraction assistant. Your job is to filter and extract relevant information.

EXTRACTION GOAL: {extraction_goal}

RULES:
- Extract only information relevant to the goal
- Remove noise, small talk, and off-topic content
- Preserve key details: names, dates, decisions, action items
- Keep the output concise (max {max_output_chars} characters)
- Use bullet points or brief summaries
- If nothing relevant is found, say "No relevant content found."

Output the extracted content directly, no preamble."""

    try:
        result = await chat_completion(
            messages=[{"role": "user", "content": raw_content}],
            system=system,
            model=HAIKU_MODEL,
            max_tokens=max_output_chars // 3,  # Rough chars to tokens
        )
        return result.strip()
    except Exception as e:
        logger.warning(f"[HAIKU] Extraction failed, using raw content: {e}")
        return raw_content[:max_output_chars]


# =============================================================================
# ADR-029 Phase 2 + ADR-030 Phase 5: Integration Data Source Fetching
# =============================================================================

class SourceFetchResult:
    """ADR-030: Result of fetching an integration source."""
    def __init__(
        self,
        content: Optional[str] = None,
        items_fetched: int = 0,
        items_filtered: int = 0,
        time_range_start: Optional[datetime] = None,
        time_range_end: Optional[datetime] = None,
        delta_mode_used: bool = False,
        error: Optional[str] = None,
    ):
        self.content = content
        self.items_fetched = items_fetched
        self.items_filtered = items_filtered
        self.time_range_start = time_range_start
        self.time_range_end = time_range_end
        self.delta_mode_used = delta_mode_used
        self.error = error


async def fetch_integration_source_data(
    client,
    user_id: str,
    source: dict,
    last_run_at: Optional[datetime] = None,
    deliverable_id: Optional[str] = None,
    source_index: Optional[int] = None,
    version_id: Optional[str] = None,
) -> SourceFetchResult:
    """
    Fetch data from an integration source for the gather step.

    ADR-029 Phase 2: When a deliverable has integration_import sources,
    we fetch the actual data from the integration (Gmail, Slack, Notion)
    and include it in the context.

    ADR-030 Phase 5: Supports delta extraction mode, tracking fetch results.

    Args:
        client: Supabase client
        user_id: User ID
        source: Source dict with provider, source, filters, scope
        last_run_at: Deliverable's last_run_at for delta extraction
        deliverable_id: For tracking source runs
        source_index: Index of this source in the sources array
        version_id: Version ID for tracking

    Returns:
        SourceFetchResult with content and metadata
    """
    import os
    from datetime import timedelta
    from integrations.core.client import MCPClientManager
    from integrations.core.token_manager import TokenManager

    provider = source.get("provider")
    source_query = source.get("source", "inbox")
    filters = source.get("filters", {})
    scope = source.get("scope", {})

    if not provider:
        logger.warning("[GATHER] Integration source missing provider")
        return SourceFetchResult(error="Missing provider")

    # ADR-030: Determine time range based on scope mode
    scope_mode = scope.get("mode", "delta")
    fallback_days = scope.get("fallback_days", 7)
    recency_days = scope.get("recency_days")
    max_items = scope.get("max_items", 200)

    now = datetime.utcnow()
    time_range_start = None
    time_range_end = now
    delta_mode_used = False

    if scope_mode == "delta" and last_run_at:
        # Delta mode: fetch since last run
        time_range_start = last_run_at
        delta_mode_used = True
        logger.info(f"[GATHER] Delta mode: fetching since {last_run_at}")
    elif scope_mode == "fixed_window" and recency_days:
        # Fixed window mode: always fetch last N days
        time_range_start = now - timedelta(days=recency_days)
        logger.info(f"[GATHER] Fixed window: last {recency_days} days")
    else:
        # Fallback: use fallback_days
        time_range_start = now - timedelta(days=fallback_days)
        logger.info(f"[GATHER] Fallback: last {fallback_days} days")

    # Merge time range into filters
    enhanced_filters = filters.copy()
    if time_range_start:
        # Convert to "Nd" format for filter parsing
        days_ago = (now - time_range_start).days
        enhanced_filters["after"] = f"{days_ago}d"

    # ADR-030 Phase 6: Check cache for recent fetches
    use_haiku = scope.get("use_haiku_extraction", True)  # Default to Haiku for cost savings
    cache_key = _cache_key(user_id, provider, source_query, time_range_start)
    cached = _get_cached_result(cache_key)
    if cached:
        logger.info(f"[GATHER] Using cached result for {provider}:{source_query}")
        # Still track the source run even for cached results
        if deliverable_id and source_index is not None:
            try:
                client.table("deliverable_source_runs").insert({
                    "deliverable_id": deliverable_id,
                    "version_id": version_id,
                    "source_index": source_index,
                    "source_type": "integration_import",
                    "provider": provider,
                    "resource_id": source_query,
                    "scope_used": {**scope, "cached": True},
                    "time_range_start": time_range_start.isoformat() if time_range_start else None,
                    "time_range_end": time_range_end.isoformat(),
                    "status": "completed",
                    "items_fetched": cached.items_fetched,
                    "content_summary": "[cached result]",
                    "completed_at": datetime.utcnow().isoformat(),
                }).execute()
            except Exception as e:
                logger.warning(f"[GATHER] Failed to track cached source run: {e}")
        # Clone the cached result with updated time info
        result = SourceFetchResult(
            content=cached.content,
            items_fetched=cached.items_fetched,
            items_filtered=cached.items_filtered,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            delta_mode_used=delta_mode_used,
        )
        return result

    # Track the source run if we have tracking context
    source_run_id = None
    if deliverable_id and source_index is not None:
        try:
            run_result = client.table("deliverable_source_runs").insert({
                "deliverable_id": deliverable_id,
                "version_id": version_id,
                "source_index": source_index,
                "source_type": "integration_import",
                "provider": provider,
                "resource_id": source_query,
                "scope_used": scope,
                "time_range_start": time_range_start.isoformat() if time_range_start else None,
                "time_range_end": time_range_end.isoformat(),
                "status": "fetching",
            }).execute()
            if run_result.data:
                source_run_id = run_result.data[0]["id"]
        except Exception as e:
            logger.warning(f"[GATHER] Failed to create source run tracking: {e}")

    # Get user's integration
    integration_result = (
        client.table("user_integrations")
        .select("id, access_token_encrypted, refresh_token_encrypted, metadata, status")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .eq("status", "active")
        .single()
        .execute()
    )

    if not integration_result.data:
        logger.warning(f"[GATHER] No active {provider} integration for user")
        error_msg = f"No active {provider} integration"
        if source_run_id:
            _update_source_run(client, source_run_id, "failed", error_message=error_msg)
        return SourceFetchResult(error=error_msg)

    integration = integration_result.data
    token_manager = TokenManager()
    mcp_manager = MCPClientManager()

    try:
        if provider == "gmail":
            result = await _fetch_gmail_data(
                mcp_manager, token_manager, integration, user_id,
                source_query, enhanced_filters, max_items
            )
        elif provider == "slack":
            result = await _fetch_slack_data(
                mcp_manager, token_manager, integration, user_id,
                source_query, enhanced_filters, max_items
            )
        elif provider == "notion":
            result = await _fetch_notion_data(
                mcp_manager, token_manager, integration, user_id,
                source_query, enhanced_filters, max_items
            )
        elif provider in ("calendar", "google"):
            # ADR-046: Google Calendar integration
            # Note: "google" provider uses same integration record but routes to calendar fetch
            # For calendar sources, use the google integration
            if provider == "calendar":
                # Look for google integration instead
                calendar_integration_result = client.table("user_integrations").select(
                    "id, access_token_encrypted, refresh_token_encrypted, status, metadata"
                ).eq("user_id", user_id).eq("provider", "google").eq(
                    "status", "active"
                ).single().execute()

                if not calendar_integration_result.data:
                    # Try legacy gmail provider
                    calendar_integration_result = client.table("user_integrations").select(
                        "id, access_token_encrypted, refresh_token_encrypted, status, metadata"
                    ).eq("user_id", user_id).eq("provider", "gmail").eq(
                        "status", "active"
                    ).single().execute()

                if not calendar_integration_result.data:
                    logger.warning(f"[GATHER] No active Google/Gmail integration for calendar access")
                    error_msg = "No active Google integration for calendar"
                    if source_run_id:
                        _update_source_run(client, source_run_id, "failed", error_message=error_msg)
                    return SourceFetchResult(error=error_msg)

                integration = calendar_integration_result.data

            result = await _fetch_calendar_data(
                mcp_manager, token_manager, integration, user_id,
                source_query, enhanced_filters, max_items
            )
        else:
            logger.warning(f"[GATHER] Unsupported integration provider: {provider}")
            error_msg = f"Unsupported provider: {provider}"
            if source_run_id:
                _update_source_run(client, source_run_id, "failed", error_message=error_msg)
            return SourceFetchResult(error=error_msg)

        # ADR-030 Phase 6: Apply Haiku extraction if enabled and content is large
        if use_haiku and result.content and len(result.content) > 2000:
            extraction_goal = scope.get("extraction_goal", "key decisions, action items, and important updates")
            logger.info(f"[GATHER] Applying Haiku extraction for {provider} ({len(result.content)} chars)")
            extracted = await extract_with_haiku(
                raw_content=result.content,
                extraction_goal=extraction_goal,
                max_output_chars=3000,
            )
            # Track how much was filtered
            original_len = len(result.content)
            result.content = extracted
            result.items_filtered = result.items_filtered + (original_len - len(extracted)) // 100  # Rough estimate

        # ADR-030 Phase 6: Cache the result
        _set_cached_result(cache_key, result)
        logger.info(f"[GATHER] Cached result for {provider}:{source_query}")

        # Update source run with success
        if source_run_id:
            _update_source_run(
                client, source_run_id, "completed",
                items_fetched=result.items_fetched,
                items_filtered=result.items_filtered,
            )

        # Enrich result with time range info
        result.time_range_start = time_range_start
        result.time_range_end = time_range_end
        result.delta_mode_used = delta_mode_used
        return result

    except Exception as e:
        logger.error(f"[GATHER] Failed to fetch {provider} data: {e}")
        error_msg = str(e)
        if source_run_id:
            _update_source_run(client, source_run_id, "failed", error_message=error_msg)
        return SourceFetchResult(error=error_msg)


def _update_source_run(
    client,
    source_run_id: str,
    status: str,
    items_fetched: int = 0,
    items_filtered: int = 0,
    error_message: Optional[str] = None,
):
    """Update a source run record with results."""
    try:
        update_data = {
            "status": status,
            "items_fetched": items_fetched,
            "items_filtered": items_filtered,
            "completed_at": datetime.utcnow().isoformat(),
        }
        if error_message:
            update_data["error_message"] = error_message
        client.table("deliverable_source_runs").update(update_data).eq(
            "id", source_run_id
        ).execute()
    except Exception as e:
        logger.warning(f"[GATHER] Failed to update source run: {e}")


async def _fetch_gmail_data(
    mcp_manager,
    token_manager,
    integration: dict,
    user_id: str,
    source_query: str,
    filters: dict,
    max_items: int = 30,
) -> SourceFetchResult:
    """Fetch Gmail messages and format as context."""
    import os

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return SourceFetchResult(error="Missing Google OAuth credentials")

    refresh_token = token_manager.decrypt(integration["refresh_token_encrypted"])
    if not refresh_token:
        return SourceFetchResult(error="Missing Gmail refresh token")

    # Build query from source and filters
    query_parts = []

    if source_query.startswith("query:"):
        query_parts.append(source_query.split(":", 1)[1])
    elif source_query != "inbox":
        query_parts.append(source_query)

    if filters.get("from"):
        query_parts.append(f"from:{filters['from']}")
    if filters.get("subject_contains"):
        query_parts.append(f"subject:{filters['subject_contains']}")
    if filters.get("after"):
        # Convert "7d" to date
        after_val = filters["after"]
        if after_val.endswith("d"):
            from datetime import timedelta
            days = int(after_val[:-1])
            date_str = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
            query_parts.append(f"after:{date_str}")
        else:
            query_parts.append(f"after:{after_val}")

    query = " ".join(query_parts) if query_parts else None

    # Fetch messages
    fetch_limit = min(max_items, 50)  # Cap at 50 for performance
    messages = await mcp_manager.list_gmail_messages(
        user_id=user_id,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        query=query,
        max_results=fetch_limit,
    )

    if not messages:
        return SourceFetchResult(
            content="[Gmail] No messages found matching criteria",
            items_fetched=0,
        )

    # Fetch full content for top messages
    items_to_fetch = min(len(messages), 15)  # Cap full fetch at 15
    lines = [f"[Gmail Integration Data - {len(messages)} messages]\n"]
    items_fetched = 0

    for msg in messages[:items_to_fetch]:
        msg_id = msg.get("id")
        if msg_id:
            try:
                full_msg = await mcp_manager.get_gmail_message(
                    user_id=user_id,
                    message_id=msg_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                )

                headers = full_msg.get("headers", {})
                subject = headers.get("Subject", headers.get("subject", "(no subject)"))
                from_addr = headers.get("From", headers.get("from", "unknown"))
                date = headers.get("Date", headers.get("date", ""))
                body = full_msg.get("body", full_msg.get("snippet", ""))

                if len(body) > 500:
                    body = body[:500] + "..."

                lines.append(f"---\nFrom: {from_addr}\nDate: {date}\nSubject: {subject}\n{body}\n")
                items_fetched += 1

            except Exception as e:
                logger.warning(f"[GATHER] Failed to fetch Gmail message {msg_id}: {e}")

    return SourceFetchResult(
        content="\n".join(lines),
        items_fetched=items_fetched,
        items_filtered=len(messages) - items_fetched,
    )


async def _fetch_slack_data(
    mcp_manager,
    token_manager,
    integration: dict,
    user_id: str,
    source_query: str,
    filters: dict,
    max_items: int = 50,
) -> SourceFetchResult:
    """Fetch Slack messages and format as context."""
    access_token = token_manager.decrypt(integration["access_token_encrypted"])
    metadata = integration.get("metadata", {}) or {}
    team_id = metadata.get("team_id")

    if not access_token or not team_id:
        return SourceFetchResult(error="Missing Slack credentials")

    channel_id = filters.get("channel_id") or source_query

    if not channel_id:
        return SourceFetchResult(error="No Slack channel specified")

    fetch_limit = min(max_items, 100)  # Cap at 100
    messages = await mcp_manager.get_slack_channel_history(
        user_id=user_id,
        channel_id=channel_id,
        bot_token=access_token,
        team_id=team_id,
        limit=fetch_limit,
    )

    if not messages:
        return SourceFetchResult(
            content="[Slack] No messages found in channel",
            items_fetched=0,
        )

    lines = [f"[Slack Integration Data - #{channel_id} - {len(messages)} messages]\n"]
    items_fetched = 0

    for msg in messages[:50]:  # Cap output at 50 messages
        text = msg.get("text", "")
        user = msg.get("user", "unknown")

        if text:
            lines.append(f"[{user}] {text}")
            items_fetched += 1

    return SourceFetchResult(
        content="\n".join(lines),
        items_fetched=items_fetched,
        items_filtered=len(messages) - items_fetched,
    )


async def _fetch_notion_data(
    mcp_manager,
    token_manager,
    integration: dict,
    user_id: str,
    source_query: str,
    filters: dict,
    max_items: int = 10,
) -> SourceFetchResult:
    """Fetch Notion page content and format as context."""
    access_token = token_manager.decrypt(integration["access_token_encrypted"])

    if not access_token:
        return SourceFetchResult(error="Missing Notion access token")

    page_id = filters.get("page_id") or source_query

    if not page_id:
        return SourceFetchResult(error="No Notion page specified")

    page_content = await mcp_manager.get_notion_page_content(
        user_id=user_id,
        page_id=page_id,
        auth_token=access_token,
    )

    if not page_content:
        return SourceFetchResult(
            content="[Notion] Page not found or empty",
            items_fetched=0,
        )

    title = page_content.get("title", "Untitled")
    content = page_content.get("content", "")

    if len(content) > 3000:
        content = content[:3000] + "... [truncated]"

    return SourceFetchResult(
        content=f"[Notion Integration Data - {title}]\n\n{content}",
        items_fetched=1,
        items_filtered=0,
    )


async def _fetch_calendar_data(
    mcp_manager,
    token_manager,
    integration: dict,
    user_id: str,
    source_query: str,
    filters: dict,
    max_items: int = 50,
) -> SourceFetchResult:
    """
    ADR-046: Fetch Google Calendar events and format as context.

    Used for:
    - Meeting prep deliverables
    - Weekly calendar preview
    - 1:1 prep with attendee context

    Source query format:
    - "primary" - User's primary calendar
    - "<calendar_id>" - Specific calendar

    Filters:
    - time_min: Start time (RFC3339 or relative like "now", "+2h")
    - time_max: End time (RFC3339 or relative like "+24h", "+7d")
    - attendee: Filter to events with specific attendee email
    - recurring: Only show recurring events (true/false)
    """
    import os
    import httpx
    from datetime import timedelta

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return SourceFetchResult(error="Missing Google OAuth credentials")

    refresh_token_encrypted = integration.get("refresh_token_encrypted")
    if not refresh_token_encrypted:
        return SourceFetchResult(error="Missing Google refresh token")

    refresh_token = token_manager.decrypt(refresh_token_encrypted)

    # Parse time filters
    def parse_time(val: str, default_offset_days: int = 0) -> str:
        """Parse time value to RFC3339 format."""
        if not val:
            return (datetime.utcnow() + timedelta(days=default_offset_days)).isoformat() + "Z"
        if val == "now":
            return datetime.utcnow().isoformat() + "Z"
        if val.startswith("+"):
            # Relative time: +2h, +24h, +7d
            val = val[1:]
            if val.endswith("h"):
                delta = timedelta(hours=int(val[:-1]))
            elif val.endswith("d"):
                delta = timedelta(days=int(val[:-1]))
            else:
                delta = timedelta(days=int(val))
            return (datetime.utcnow() + delta).isoformat() + "Z"
        # Assume RFC3339 format
        return val

    time_min = parse_time(filters.get("time_min", "now"), 0)
    time_max = parse_time(filters.get("time_max", "+7d"), 7)
    calendar_id = source_query if source_query else "primary"

    try:
        # Get fresh access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }
            )

            if token_response.status_code != 200:
                return SourceFetchResult(error=f"Failed to refresh Google token: {token_response.text}")

            access_token = token_response.json().get("access_token")

            # Fetch events
            events_response = await client.get(
                f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "maxResults": min(max_items, 250),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                }
            )

            if events_response.status_code != 200:
                return SourceFetchResult(error=f"Failed to fetch calendar events: {events_response.text}")

            events = events_response.json().get("items", [])

        if not events:
            return SourceFetchResult(
                content=f"[Calendar] No events found from {time_min} to {time_max}",
                items_fetched=0,
            )

        # Apply filters
        filtered_events = events
        attendee_filter = filters.get("attendee")
        recurring_only = filters.get("recurring")

        if attendee_filter:
            filtered_events = [
                e for e in filtered_events
                if any(a.get("email", "").lower() == attendee_filter.lower()
                       for a in e.get("attendees", []))
            ]

        if recurring_only:
            filtered_events = [e for e in filtered_events if e.get("recurringEventId")]

        # Format events as context
        lines = [f"[Google Calendar Events - {len(filtered_events)} events from {calendar_id}]\n"]

        for event in filtered_events:
            start = event.get("start", {})
            end = event.get("end", {})
            start_time = start.get("dateTime") or start.get("date", "")
            end_time = end.get("dateTime") or end.get("date", "")

            # Format attendees
            attendees = event.get("attendees", [])
            attendee_strs = []
            for a in attendees[:5]:  # Limit to first 5 attendees
                status = a.get("responseStatus", "needsAction")
                status_emoji = {"accepted": "✓", "declined": "✗", "tentative": "?", "needsAction": "•"}.get(status, "•")
                name = a.get("displayName") or a.get("email", "Unknown")
                if a.get("organizer"):
                    name += " (organizer)"
                attendee_strs.append(f"  {status_emoji} {name}")

            if len(attendees) > 5:
                attendee_strs.append(f"  ... and {len(attendees) - 5} more")

            lines.append(f"---")
            lines.append(f"Event: {event.get('summary', 'Untitled')}")
            lines.append(f"When: {start_time} to {end_time}")

            if event.get("location"):
                lines.append(f"Location: {event['location']}")

            if event.get("hangoutLink"):
                lines.append(f"Meeting Link: {event['hangoutLink']}")

            if attendee_strs:
                lines.append("Attendees:")
                lines.extend(attendee_strs)

            if event.get("description"):
                desc = event["description"]
                if len(desc) > 300:
                    desc = desc[:300] + "..."
                lines.append(f"Description: {desc}")

            if event.get("recurringEventId"):
                lines.append("(Recurring event)")

            lines.append("")

        return SourceFetchResult(
            content="\n".join(lines),
            items_fetched=len(filtered_events),
            items_filtered=len(events) - len(filtered_events),
        )

    except Exception as e:
        logger.error(f"[GATHER] Calendar fetch error: {e}")
        return SourceFetchResult(error=f"Calendar fetch failed: {str(e)}")


# =============================================================================
# ADR-019: Type-Specific Prompt Templates
# =============================================================================

TYPE_PROMPTS = {
    "status_report": """You are writing a {detail_level} status report for {audience}.

Subject: {subject}

SECTIONS TO INCLUDE:
{sections_list}

TONE: {tone}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write in {tone} tone appropriate for {audience}
- Be specific with accomplishments - use concrete examples
- Keep blockers actionable - suggest next steps when possible
- Length target: {length_guidance}
- Do NOT invent specific dates, numbers, or metrics not in the context

Write the status report now:""",

    "stakeholder_update": """You are writing a {formality} stakeholder update for {audience_type}.

Company/Project: {company_or_project}
Relationship Context: {relationship_context}

SECTIONS TO INCLUDE:
{sections_list}

SENSITIVITY: {sensitivity} information

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Maintain a {formality} tone throughout
- Lead with the executive summary - 2-3 sentences capturing the essence
- Balance highlights with challenges - avoid pure positive spin
- Make the outlook section actionable with clear next steps
- Do NOT include specific financials unless explicitly provided in context

Write the stakeholder update now:""",

    "research_brief": """You are writing a {depth} research brief on {focus_area} intelligence.

SUBJECTS TO COVER:
{subjects_list}

PURPOSE: {purpose}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Key takeaways should be actionable, not just summaries
- Findings must be specific and tied to sources when possible
- Connect implications to the user's context and purpose
- Recommendations should be concrete and prioritized
- Depth level: {depth} (scan: 300-500 words, analysis: 500-1000, deep_dive: 1000+)

Write the research brief now:""",

    "meeting_summary": """You are writing a {format} summary for: {meeting_name}

Meeting Type: {meeting_type}
Participants: {participants}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Action items MUST have clear owners when possible
- Decisions should be explicitly stated, not implied
- Discussion points should be substantive, not filler
- Format: {format} (narrative, bullet_points, or structured)
- Keep it concise but complete

Write the meeting summary now:""",

    "custom": """Produce the following deliverable: {title}

DESCRIPTION:
{description}

{structure_notes}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Follow any structure guidelines provided above
- Maintain appropriate professional tone
- Be thorough but concise

Write the deliverable now:""",

    # ==========================================================================
    # Beta Tier Prompts
    # ==========================================================================

    "client_proposal": """You are writing a {tone} client proposal for {client_name}.

PROJECT TYPE: {project_type}
SERVICE CATEGORY: {service_category}

SECTIONS TO INCLUDE:
{sections_list}

{pricing_instruction}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Personalize to the client's specific context and needs
- Be clear about the value proposition and outcomes
- Deliverables should be specific, not vague
- {tone} tone throughout
- Make it persuasive but honest

Write the proposal now:""",

    "performance_self_assessment": """You are writing a {review_period} performance self-assessment for a {role_level} level employee.

SECTIONS TO INCLUDE:
{sections_list}

TONE: {tone}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Accomplishments should include measurable impact when possible
- Be {tone} - {tone_guidance}
- Acknowledge both strengths and growth areas
- Be forward-looking with goals for the next period
{quantify_instruction}

Write the self-assessment now:""",

    "newsletter_section": """You are writing a {section_type} section for the newsletter: {newsletter_name}

AUDIENCE: {audience}
VOICE: {voice}
LENGTH: {length}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Start with an engaging hook, not a boring opener
- Maintain consistent {voice} voice throughout
- Keep to {length} length target
- Include clear CTA if applicable
- Don't sound generic or AI-written

Write the newsletter section now:""",

    "changelog": """You are writing {release_type} release notes for {product_name}.

AUDIENCE: {audience}
FORMAT: {format}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Categorize changes clearly (new, improved, fixed)
- Use {format} language appropriate for {audience}
- Highlight user benefits, not just technical changes
- Flag any breaking changes prominently
{links_instruction}

Write the release notes now:""",

    "one_on_one_prep": """You are preparing a manager's prep doc for a {meeting_cadence} 1:1 with {report_name}.

RELATIONSHIP: {relationship}
FOCUS AREAS: {focus_areas}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Make it personalized to this specific individual
- Balance recognition with areas to discuss
- Include actionable discussion topics, not just observations
- Build on previous conversations when context available
- Keep it focused on the selected focus areas

Write the 1:1 prep doc now:""",

    "board_update": """You are writing a {update_type} board update for {company_name}.

COMPANY STAGE: {stage}
TONE: {tone}

SECTIONS TO INCLUDE:
{sections_list}

{comparisons_instruction}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Lead with the executive summary (2-3 sentences)
- Be metrics-forward with context on what they mean
- {tone} tone - {tone_guidance}
- Clear asks section - don't bury requests
- Keep it concise - board members are busy
- 500-1000 words total

Write the board update now:""",

    # ==========================================================================
    # ADR-029 Phase 3: Email-Specific Deliverable Prompts
    # ==========================================================================

    "inbox_summary": """You are writing a {summary_period} inbox summary for the user.

INBOX SCOPE: {inbox_scope}
PRIORITIZATION: {prioritization}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Start with a quick overview of inbox activity (message count, key senders)
- Highlight urgent items that need immediate attention
- Clearly separate action-required emails from FYI items
- For threads to close, suggest which can be archived or responded to quickly
- Keep summaries scannable - use bullet points, not long paragraphs
- If thread context is included, summarize key decision points

Write the inbox summary now:""",

    "reply_draft": """You are drafting a reply to an email thread.

TONE: {tone}
THREAD ID: {thread_id}

SECTIONS TO INCLUDE:
{sections_list}

{quote_instruction}

{suggested_actions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Match the tone of the original sender where appropriate
- Be {tone} but genuine - don't sound robotic
- Acknowledge their points before responding
- If suggesting next steps, be specific about actions/dates
- Keep the reply focused - don't introduce unrelated topics
- If quoting, only quote the most relevant parts

Write the reply draft now:""",

    "follow_up_tracker": """You are creating a follow-up tracker for the user's email.

TRACKING PERIOD: {tracking_period}
PRIORITIZATION: {prioritize_by}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Identify threads that need a response from the user
- Highlight overdue items prominently at the top
- For "waiting on others" - note who we're waiting on and since when
- List commitments the user made that may need follow-through
- Include thread links if available for quick access
- Suggest priority order for tackling the backlog

Write the follow-up tracker now:""",

    "thread_summary": """You are summarizing an email thread.

THREAD ID: {thread_id}
DETAIL LEVEL: {detail_level}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- List all participants and their roles in the conversation
- Create a timeline of key exchanges
- Clearly state any decisions that were made
- Highlight unresolved questions or open items
- If action items exist, list them with owners if mentioned
- Keep summary {detail_level} - {detail_guidance}

Write the thread summary now:""",

    # ==========================================================================
    # ADR-035: Platform-First Wave 1 Prompts
    # ==========================================================================

    "slack_channel_digest": """You are creating a Slack channel digest.

FOCUS: {focus}
SECTIONS TO INCLUDE:
{sections_list}

PLATFORM SIGNALS TO PRIORITIZE:
- Threads with {reply_threshold}+ replies (hot discussions)
- Messages with {reaction_threshold}+ reactions (notable content)
- Questions that went unanswered (gaps worth surfacing)
- Decision language ("we decided", "agreed", "let's go with")

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Format as Slack-native content using bullet points and clear headers
- Bold key decisions and action items
- Keep it scannable - no long paragraphs
- For hot threads, include the thread starter + key takeaway
- Link to original messages where relevant
- Keep total length under 2000 characters for Slack readability
- Prioritize signal over noise - skip casual chat

Write the channel digest now:""",

    "slack_standup": """You are drafting a standup from Slack activity.

SOURCE MODE: {source_mode}
FORMAT: {format}

SECTIONS TO INCLUDE:
{sections_list}

LOOK FOR THESE SIGNALS:
- Completion language: "done", "shipped", "merged", "finished", "completed"
- Progress language: "working on", "in progress", "reviewing", "starting"
- Blocker language: "stuck on", "waiting for", "blocked by", "need help"

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Extract accomplishments from messages showing completion
- Identify in-progress work from activity mentions
- Surface blockers explicitly mentioned
- Format: {format} (bullet points or short narrative)
- Be concise - standups should be quick to read
- Don't fabricate items - only use what's in the context
- If {source_mode} is "team", group by person

Write the standup now:""",

    "gmail_inbox_brief": """You are creating a daily inbox brief to help triage email.

FOCUS: {focus}
SECTIONS TO INCLUDE:
{sections_list}

PRIORITIZE:
- Unread emails from priority senders
- Threads waiting for user response
- Emails with action items or deadlines mentioned
- Thread stalls (conversations that went quiet)

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Start with urgent/time-sensitive items
- Group by category: urgent, action-required, FYI, can-archive
- For each email, include: sender, subject, and one-line summary
- Highlight any mentioned deadlines or dates
- Suggest which emails can be batch-responded
- Keep the brief scannable - use bullet points
- Total length: 300-500 words

Write the inbox brief now:""",

    "notion_page_summary": """You are summarizing recent activity on a Notion page/database.

SUMMARY TYPE: {summary_type}
MAX DEPTH: {max_depth} subpage levels

SECTIONS TO INCLUDE:
{sections_list}

LOOK FOR:
- Recent edits and who made them
- New content added (sections, pages, blocks)
- Completed tasks (checkboxes, status changes)
- Unresolved comments or questions
- Structural changes (new subpages, reorganization)

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Lead with the most significant changes
- Note who made key changes when attribution available
- For changelog type: be specific about what changed
- For overview type: summarize current state
- For activity type: focus on recent human activity
- Mention unresolved comments that need attention
- Keep it concise - 200-400 words

Write the page summary now:""",
}


# Section templates for each type
SECTION_TEMPLATES = {
    # Tier 1 - Stable
    "status_report": {
        "summary": "Summary/TL;DR - Brief overview of the current state",
        "accomplishments": "Accomplishments - What was completed this period",
        "blockers": "Blockers/Challenges - Issues impeding progress",
        "next_steps": "Next Steps - Planned work for the upcoming period",
        "metrics": "Key Metrics - Relevant numbers and measurements",
    },
    "stakeholder_update": {
        "executive_summary": "Executive Summary - The key message in 2-3 sentences",
        "highlights": "Key Highlights - Major wins and positive developments",
        "challenges": "Challenges & Mitigations - Issues and how they're being addressed",
        "metrics": "Metrics Snapshot - Key performance indicators",
        "outlook": "Outlook - Focus areas for the next period",
    },
    "research_brief": {
        "key_takeaways": "Key Takeaways - The most important actionable insights",
        "findings": "Findings - Detailed research results by topic/subject",
        "implications": "Implications - What these findings mean for the business",
        "recommendations": "Recommendations - Suggested actions based on the research",
    },
    "meeting_summary": {
        "context": "Meeting Context - Purpose and attendees",
        "discussion": "Key Discussion Points - Main topics covered",
        "decisions": "Decisions Made - Explicit agreements reached",
        "action_items": "Action Items - Tasks with owners and deadlines",
        "followups": "Follow-ups - Topics for the next meeting",
    },
    # Beta Tier
    "client_proposal": {
        "executive_summary": "Executive Summary - Hook and value proposition",
        "needs_understanding": "Understanding of Needs - What the client wants to achieve",
        "approach": "Our Approach - How we'll solve the problem",
        "deliverables": "Deliverables - What the client will receive",
        "timeline": "Timeline - Key milestones and dates",
        "investment": "Investment - Pricing and payment terms",
        "social_proof": "Why Us - Relevant experience and testimonials",
    },
    "performance_self_assessment": {
        "summary": "Summary - Overview of the review period",
        "accomplishments": "Key Accomplishments - Major wins with impact",
        "goals_progress": "Goals Progress - Status on previously set goals",
        "challenges": "Challenges & Learnings - Obstacles faced and lessons learned",
        "development": "Development Areas - Skills and areas for growth",
        "next_period_goals": "Goals for Next Period - Focus areas ahead",
    },
    "newsletter_section": {
        "hook": "Hook/Intro - Attention-grabbing opener",
        "main_content": "Main Content - The core message or story",
        "highlights": "Highlights - Key callouts or quotes",
        "cta": "Call to Action - What readers should do next",
    },
    "changelog": {
        "highlights": "Highlights - Most important changes",
        "new_features": "New Features - Newly added functionality",
        "improvements": "Improvements - Enhanced existing features",
        "bug_fixes": "Bug Fixes - Issues resolved",
        "breaking_changes": "Breaking Changes - Changes requiring action",
        "whats_next": "What's Next - Preview of upcoming work",
    },
    "one_on_one_prep": {
        "context": "Context Since Last 1:1 - What's happened",
        "topics": "Topics to Discuss - Agenda items",
        "recognition": "Recognition - Wins to call out",
        "concerns": "Concerns - Issues to address",
        "career": "Career & Development - Growth discussion",
        "previous_actions": "Previous Action Items - Follow-up on past commitments",
    },
    "board_update": {
        "executive_summary": "Executive Summary - The key message in 2-3 sentences",
        "metrics": "Key Metrics - Performance indicators with context",
        "strategic_progress": "Strategic Progress - Movement on key initiatives",
        "challenges": "Challenges - Issues and mitigations",
        "financials": "Financials - Cash, runway, burn",
        "asks": "Asks - What you need from the board",
        "outlook": "Outlook - Focus for next period",
    },
    # ADR-029 Phase 3: Email-Specific Section Templates
    "inbox_summary": {
        "overview": "Overview - Quick stats on inbox activity",
        "urgent": "Urgent - Items requiring immediate attention",
        "action_required": "Action Required - Emails needing your response",
        "fyi_items": "FYI - Informational items, no action needed",
        "threads_to_close": "Threads to Close - Conversations ready to wrap up",
    },
    "reply_draft": {
        "acknowledgment": "Acknowledgment - Brief response to their points",
        "response_body": "Response - Main content of your reply",
        "next_steps": "Next Steps - Proposed actions or timeline",
        "closing": "Closing - Sign-off appropriate to relationship",
    },
    "follow_up_tracker": {
        "overdue": "Overdue - Threads past expected response time",
        "due_soon": "Due Soon - Items to address this week",
        "waiting_on_others": "Waiting On - Pending responses from others",
        "commitments_made": "Commitments - Things you said you'd do",
    },
    "thread_summary": {
        "participants": "Participants - Who's in this conversation",
        "timeline": "Timeline - Key exchanges in chronological order",
        "key_points": "Key Points - Main topics and positions",
        "decisions": "Decisions - What was agreed or decided",
        "open_questions": "Open Questions - Unresolved items",
    },
    # ADR-035: Platform-First Wave 1 Section Templates
    "slack_channel_digest": {
        "hot_threads": "Hot Threads - Discussions with high engagement",
        "key_decisions": "Key Decisions - What was decided or agreed",
        "unanswered_questions": "Unanswered Questions - Open items needing response",
        "mentions": "Notable Mentions - Important callouts or highlights",
    },
    "slack_standup": {
        "done": "Done - What was completed",
        "doing": "In Progress - What's currently being worked on",
        "blockers": "Blockers - What's blocking progress",
    },
    "gmail_inbox_brief": {
        "urgent": "Urgent - Time-sensitive items",
        "action_required": "Action Required - Emails needing your response",
        "fyi": "FYI - Informational items, no action needed",
        "follow_ups": "Follow-ups - Threads to revisit",
    },
    "notion_page_summary": {
        "changes": "Recent Changes - What was modified",
        "new_content": "New Content - What was added",
        "completed_tasks": "Completed Tasks - Items marked done",
        "open_comments": "Open Comments - Unresolved discussions",
    },
    # ADR-046: Calendar-Triggered Section Templates
    "meeting_prep": {
        "attendee_context": "Attendee Context - Recent interactions with meeting participants",
        "open_items": "Open Items - Unresolved discussions or decisions",
        "recent_updates": "Recent Updates - Relevant project or topic updates",
        "suggested_topics": "Suggested Topics - Discussion points to raise",
        "previous_meeting": "Previous Meeting - Notes from last occurrence (if recurring)",
    },
    "weekly_calendar_preview": {
        "overview": "Week Overview - Meeting count, hours, busy/free patterns",
        "key_people": "Key People - Who you're meeting with most",
        "recurring": "Recurring Meetings - Regular syncs and 1:1s",
        "high_priority": "High Priority - Meetings needing extra attention",
        "prep_suggestions": "Prep Suggestions - Meetings worth preparing for",
    },
}


# Length guidance by detail level
LENGTH_GUIDANCE = {
    "brief": "200-400 words - concise and to the point",
    "standard": "400-800 words - balanced detail",
    "detailed": "800-1500 words - comprehensive coverage",
    "scan": "300-500 words - quick overview",
    "analysis": "500-1000 words - moderate depth",
    "deep_dive": "1000+ words - thorough exploration",
}


def normalize_sections(sections) -> dict:
    """Normalize sections to dict format.

    Handles both:
    - List format: ['summary', 'accomplishments'] -> {'summary': True, 'accomplishments': True}
    - Dict format: {'summary': True, 'accomplishments': False} -> unchanged
    """
    if sections is None:
        return {}
    if isinstance(sections, list):
        return {s: True for s in sections}
    return sections


def build_sections_list(deliverable_type: str, config: dict) -> str:
    """Build formatted sections list based on enabled sections in config."""
    sections = normalize_sections(config.get("sections", {}))
    templates = SECTION_TEMPLATES.get(deliverable_type, {})

    enabled = []
    for section_key, is_enabled in sections.items():
        if is_enabled and section_key in templates:
            enabled.append(f"- {templates[section_key]}")

    if not enabled:
        # Default to all sections if none specified
        enabled = [f"- {desc}" for desc in templates.values()]

    return "\n".join(enabled)


# =============================================================================
# ADR-031: Platform Variant Prompts
# =============================================================================

VARIANT_PROMPTS = {
    "slack_digest": """You are creating a Slack channel digest.

CHANNEL: {channel_name}
TIME PERIOD: {time_period}

The digest should highlight what's important, not just summarize everything.
Focus on platform-semantic signals in the context.

SECTIONS TO GENERATE:

## 🔥 Hot Threads
Threads with high engagement (many replies, reactions). What were people talking about?

## ❓ Unanswered Questions
Questions that haven't been answered yet. Flag these for attention.

## ⏳ Stalled Discussions
Threads that started but went quiet - may need follow-up.

## ✅ Action Items
Concrete tasks or follow-ups mentioned in conversations.

## 📋 Decisions Made
Decisions that were reached in discussions.

## 💬 Key Discussions
Other notable conversations worth knowing about.

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Be concise but specific - use names and details from context
- If a section has nothing notable, skip it entirely
- Format for Slack: use *bold* for emphasis, bullet points for lists
- Include message timestamps or rough times when referencing discussions
- Prioritize actionable information over general chatter
- If you detect urgency markers or blockers, highlight them prominently

Generate the digest now:""",

    "email_summary": """You are creating an email inbox summary.

INBOX: {inbox_name}
TIME PERIOD: {time_period}

Summarize the key emails and threads that need attention.

SECTIONS TO GENERATE:

## 🚨 Urgent / Needs Response
Emails requiring immediate attention or response.

## 📥 Action Required
Emails with action items or requests for you.

## 📧 FYI / Updates
Informational emails that are good to know about.

## 🔄 Threads to Follow Up
Email threads that may need your follow-up.

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Prioritize by urgency and importance
- Include sender names and subjects
- Summarize the core request or information
- Skip purely administrative or automated emails
- Note deadlines if mentioned

Generate the summary now:""",

    # ADR-031 Phase 5: Gmail Archetypes
    "email_draft_reply": """You are drafting a reply to an email thread.

ORIGINAL EMAIL CONTEXT:
{email_context}

SENDER: {sender_name}
SUBJECT: {subject}

GATHERED CONTEXT (user's notes, related info):
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write a professional, clear response
- Address all points raised in the original email
- Be concise but thorough
- Match the formality level of the original sender
- Include a clear action or next step if appropriate
- Use appropriate greeting and sign-off

Draft the reply now (start with greeting, end with sign-off):""",

    "email_follow_up": """You are drafting a follow-up email.

CONTEXT FOR FOLLOW-UP:
{follow_up_context}

RECIPIENT: {recipient_name}
ORIGINAL SUBJECT: {subject}
DAYS SINCE LAST CONTACT: {days_since}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write a polite, professional follow-up
- Reference the previous communication briefly
- Restate the key ask or topic clearly
- Provide any new information if relevant
- End with a specific call to action
- Keep it concise - respect their time

Draft the follow-up email now:""",

    "email_weekly_digest": """You are creating a weekly email digest for the user.

ACCOUNT: {account_email}
TIME PERIOD: {time_period}

Create a summary of the user's email activity and outstanding items.

SECTIONS TO GENERATE:

## 📊 This Week's Overview
Quick stats: emails received, sent, threads active.

## 🔴 Overdue Responses
Emails that have been waiting for your response for too long.

## ⏰ Time-Sensitive
Emails with upcoming deadlines or meetings.

## 💬 Active Threads
Important ongoing conversations.

## 📌 Flagged for Review
Emails the user starred or flagged but hasn't addressed.

## ✅ Completed This Week
Threads that were resolved or closed this week.

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Be specific about senders, subjects, and dates
- Highlight anything overdue prominently
- Note patterns (e.g., "3 emails from Sarah unread")
- Provide actionable suggestions
- Keep the tone helpful, not overwhelming

Generate the digest now:""",

    "email_triage": """You are helping triage incoming emails.

INBOX: {inbox_name}
NEW EMAILS COUNT: {email_count}

Categorize and prioritize these emails to help the user manage their inbox efficiently.

CATEGORIES TO ASSIGN:

### 🔴 Respond Today
Must respond within 24 hours.

### 🟡 Respond This Week
Should respond but not urgent.

### 🟢 FYI Only
No response needed, just awareness.

### 📁 Archive
Can be archived without action.

### 🗑️ Skip/Delete
Newsletters, promotions, or irrelevant.

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

INSTRUCTIONS:
- For each email, state: [CATEGORY] From: Subject - Brief reason
- Consider sender importance (boss vs newsletter)
- Look for deadlines, questions, or requests
- Group similar emails (e.g., "5 newsletter emails → Archive")
- Be decisive - avoid "maybe" categories

Triage the emails now:""",

    "notion_page": """You are creating content for a Notion page.

PAGE TITLE: {page_title}
PURPOSE: {purpose}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Use clear headers (##) to structure content
- Include callout blocks for important notes (> **Note:** ...)
- Use checkboxes for action items (- [ ] Task here)
- Tables where appropriate for comparisons or data
- Keep formatting clean and scannable

Generate the page content now:""",

    # ==========================================================================
    # ADR-031 Phase 6: Cross-Platform Synthesizer Prompts
    # ==========================================================================

    "weekly_status": """You are creating a weekly status report synthesized from multiple platforms.

PROJECT: {project_name}
TIME PERIOD: {time_period}
PLATFORMS INCLUDED: {platforms_used}

This is a CROSS-PLATFORM synthesis - you have context from multiple sources that need to be unified into a cohesive status update.

{cross_platform_context}

{recipient_context}

{past_versions}

SECTIONS TO GENERATE:

## 📊 Executive Summary
2-3 sentences capturing the week's overall status and key takeaways.

## ✅ Accomplishments
What was completed this week? Pull from all platforms - Slack discussions, email threads, Notion updates.

## 🚧 In Progress
What's actively being worked on? Note any blockers or dependencies.

## 📋 Action Items
Concrete next steps. Include owners if mentioned in context.

## 🔮 Looking Ahead
What's coming next week? Upcoming deadlines, milestones, or decisions.

## 💬 Key Discussions
Notable conversations or decisions from across platforms that stakeholders should know about.

INSTRUCTIONS:
- Synthesize information across platforms - don't just list by source
- Identify connections between discussions on different platforms
- Prioritize by importance, not by platform
- Be concise but specific - use names, dates, and details from context
- If the same topic appears on multiple platforms, consolidate into one mention
- Highlight any cross-platform coordination or alignment issues

Generate the weekly status now:""",

    "project_brief": """You are creating a project brief synthesized from multiple platforms.

PROJECT: {project_name}
PLATFORMS INCLUDED: {platforms_used}

This brief consolidates all available context about this project from connected platforms into a comprehensive overview.

{cross_platform_context}

{recipient_context}

{past_versions}

SECTIONS TO GENERATE:

## 🎯 Project Overview
What is this project? What are the goals?

## 👥 Key People
Who's involved? Pull names from Slack conversations, email threads, Notion pages.

## 📅 Timeline & Milestones
Key dates, deadlines, and milestones mentioned across platforms.

## 📊 Current Status
Where does the project stand right now? What phase/stage?

## 🔑 Key Decisions Made
Important decisions captured in any platform.

## ❓ Open Questions
Unresolved questions or pending decisions from discussions.

## 📎 Resources & Links
Any documents, pages, or resources referenced in context.

INSTRUCTIONS:
- This is a living brief - synthesize the current state, not a historical record
- Connect dots between platforms (e.g., email decision that led to Slack discussion)
- Highlight any conflicts or inconsistencies found across sources
- Be comprehensive but organized - this is a reference document
- Include specific details: names, dates, numbers from the context

Generate the project brief now:""",

    "cross_platform_digest": """You are creating a digest synthesizing activity across multiple platforms.

USER: {user_name}
TIME PERIOD: {time_period}
PLATFORMS: {platforms_used}

This digest gives the user a unified view of what's happening across all their connected platforms.

{cross_platform_context}

{recipient_context}

{past_versions}

SECTIONS TO GENERATE:

## 🔥 Needs Attention
Items requiring action from any platform - urgent emails, unanswered Slack mentions, stale Notion tasks.

## 📧 Email Highlights
Key emails from the period - summarize, don't list everything.

## 💬 Slack Highlights
Important Slack conversations, decisions, or requests.

## 📝 Notion Updates
Significant changes to Notion pages or databases.

## 🔄 Cross-Platform Connections
Where the same topic or thread spans multiple platforms.

## ✅ Completed This Period
What got resolved or closed across platforms.

INSTRUCTIONS:
- Prioritize by urgency and importance, not by platform
- If something appears on multiple platforms, mention the connection
- Be selective - highlight what matters, not everything
- Use the user's name when something is directed at them
- Include enough context to act on each item

Generate the cross-platform digest now:""",

    "activity_summary": """You are creating an activity summary across multiple platforms.

TIME PERIOD: {time_period}
PLATFORMS: {platforms_used}

Create a high-level summary of activity for quick consumption.

{cross_platform_context}

{recipient_context}

{past_versions}

STRUCTURE:

## 📈 At a Glance
Quick stats: messages, emails, updates across platforms.

## 🎯 Top Priorities
The 3-5 most important items across all platforms.

## 💡 Key Takeaways
What the user most needs to know from this period.

## 👀 Watch List
Items to keep an eye on in the coming days.

INSTRUCTIONS:
- Be extremely concise - this is a quick summary
- Prioritize ruthlessly - only the most important items
- Cross-reference between platforms where relevant
- Make it actionable - what should the user do next?

Generate the activity summary now:""",

    # ==========================================================================
    # ADR-046: Calendar-Triggered Deliverable Prompts
    # ==========================================================================

    "meeting_prep": """You are preparing a context brief for an upcoming meeting.

MEETING: {meeting_title}
WHEN: {meeting_time}
ATTENDEES: {attendees_list}
{meeting_description}

CONTEXT SOURCES:
{gathered_context}

{recipient_context}

{past_versions}

SECTIONS TO INCLUDE:
{sections_list}

INSTRUCTIONS:
- Focus on what the user needs to know BEFORE this meeting
- Summarize recent interactions with each attendee from the context
- Highlight any open items, pending decisions, or unresolved discussions
- Include relevant project updates or blockers
- Suggest 2-3 talking points or questions to raise
- Keep it scannable - use bullet points and clear headers
- If recurring meeting, note what was discussed in previous occurrence if available

Write the meeting prep brief now:""",

    "weekly_calendar_preview": """You are creating a weekly calendar preview for the user.

WEEK OF: {week_start}
CALENDAR SUMMARY:
{calendar_summary}

ADDITIONAL CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

STRUCTURE:

## 📅 Week Overview
{meeting_count} meetings, {total_hours} hours of scheduled time.
Busiest day: {busiest_day}
Free blocks: {free_blocks}

## 👥 Key People This Week
Who you're meeting with most, and notable external meetings.

## 🔄 Recurring Meetings
Your regular 1:1s, syncs, and standups this week.

## ⚡ High-Priority
Meetings that likely need prep or are particularly important.

## 💭 Suggested Prep
Meetings that would benefit from a meeting prep deliverable.

INSTRUCTIONS:
- Provide a high-level view of the week ahead
- Identify patterns (heavy meeting days, back-to-back blocks)
- Call out meetings with external attendees
- Suggest which meetings need prep work
- Keep it brief and scannable

Generate the weekly calendar preview now:""",
}


def _build_variant_prompt(
    platform_variant: str,
    deliverable: dict,
    gathered_context: str,
    recipient_text: str,
    past_versions: str,
) -> Optional[str]:
    """
    Build a platform-variant-specific prompt.

    Returns None if variant not supported (falls back to base type).
    """
    template = VARIANT_PROMPTS.get(platform_variant)
    if not template:
        return None

    # Extract metadata for template
    title = deliverable.get("title", "Deliverable")
    sources = deliverable.get("sources", [])
    destination = deliverable.get("destination", {})

    # Common fields
    fields = {
        "gathered_context": gathered_context,
        "recipient_context": recipient_text,
        "past_versions": past_versions,
        "time_period": "Last 7 days",  # Could make this configurable
    }

    if platform_variant == "slack_digest":
        # Extract channel name from sources or destination
        channel_name = "Channel"
        for source in sources:
            if source.get("provider") == "slack":
                channel_name = source.get("resource_name") or source.get("source", "Channel")
                break
        if not channel_name or channel_name == "Channel":
            channel_name = destination.get("target", title)

        fields["channel_name"] = channel_name

    elif platform_variant == "email_summary":
        inbox_name = "Inbox"
        for source in sources:
            if source.get("provider") == "gmail":
                inbox_name = source.get("resource_name") or source.get("source", "Inbox")
                break
        fields["inbox_name"] = inbox_name

    elif platform_variant == "email_draft_reply":
        # Extract email context from type_config or sources
        type_config = deliverable.get("type_config", {})
        fields["email_context"] = type_config.get("email_context", gathered_context[:2000])
        fields["sender_name"] = type_config.get("sender_name", "Sender")
        fields["subject"] = type_config.get("subject", title)

    elif platform_variant == "email_follow_up":
        type_config = deliverable.get("type_config", {})
        fields["follow_up_context"] = type_config.get("follow_up_context", gathered_context[:1000])
        fields["recipient_name"] = type_config.get("recipient_name", destination.get("target", "Recipient"))
        fields["subject"] = type_config.get("subject", title)
        fields["days_since"] = type_config.get("days_since", "7")

    elif platform_variant == "email_weekly_digest":
        # Extract account email from sources
        account_email = "your inbox"
        for source in sources:
            if source.get("provider") == "gmail":
                account_email = source.get("resource_name") or source.get("source", "your inbox")
                break
        fields["account_email"] = account_email

    elif platform_variant == "email_triage":
        inbox_name = "Inbox"
        email_count = 0
        for source in sources:
            if source.get("provider") == "gmail":
                inbox_name = source.get("resource_name") or source.get("source", "Inbox")
                break
        # Count emails from context (rough estimate)
        email_count = gathered_context.count("Subject:") or gathered_context.count("From:")
        fields["inbox_name"] = inbox_name
        fields["email_count"] = str(email_count) if email_count > 0 else "multiple"

    elif platform_variant == "notion_page":
        fields["page_title"] = title
        fields["purpose"] = deliverable.get("description", "Documentation")

    # ADR-031 Phase 6: Cross-platform synthesizer variants
    elif platform_variant in ("weekly_status", "project_brief", "cross_platform_digest", "activity_summary"):
        # These variants use cross-platform context from the synthesizer service
        type_config = deliverable.get("type_config", {})

        # Project name from config or title
        fields["project_name"] = type_config.get("project_name", title)
        fields["user_name"] = type_config.get("user_name", "User")

        # Platforms used - extracted from synthesizer context or sources
        platforms = set()
        for source in sources:
            if provider := source.get("provider"):
                platforms.add(provider)
        fields["platforms_used"] = ", ".join(sorted(platforms)) if platforms else "Multiple platforms"

        # For synthesizers, the gathered_context is already formatted with cross-platform structure
        # Use a separate field name for clarity in the template
        fields["cross_platform_context"] = gathered_context

    try:
        return template.format(**fields)
    except KeyError as e:
        logger.warning(f"[VARIANT] Missing field in template: {e}")
        return None


def build_type_prompt(
    deliverable_type: str,
    config: dict,
    deliverable: dict,
    gathered_context: str,
    recipient_text: str,
    past_versions: str,
) -> str:
    """Build the type-specific synthesis prompt."""

    # ADR-031: Check for platform_variant first
    platform_variant = deliverable.get("platform_variant")
    if platform_variant:
        variant_prompt = _build_variant_prompt(
            platform_variant=platform_variant,
            deliverable=deliverable,
            gathered_context=gathered_context,
            recipient_text=recipient_text,
            past_versions=past_versions,
        )
        if variant_prompt:
            return variant_prompt

    template = TYPE_PROMPTS.get(deliverable_type, TYPE_PROMPTS["custom"])

    # Common fields
    fields = {
        "gathered_context": gathered_context,
        "recipient_context": recipient_text,
        "past_versions": past_versions,
        "title": deliverable.get("title", "Deliverable"),
    }

    if deliverable_type == "status_report":
        fields.update({
            "subject": config.get("subject", deliverable.get("title", "")),
            "audience": config.get("audience", "stakeholders"),
            "sections_list": build_sections_list(deliverable_type, config),
            "detail_level": config.get("detail_level", "standard"),
            "tone": config.get("tone", "formal"),
            "length_guidance": LENGTH_GUIDANCE.get(
                config.get("detail_level", "standard"),
                "400-800 words"
            ),
        })

    elif deliverable_type == "stakeholder_update":
        fields.update({
            "audience_type": config.get("audience_type", "stakeholders"),
            "company_or_project": config.get("company_or_project", deliverable.get("title", "")),
            "relationship_context": config.get("relationship_context", "N/A"),
            "sections_list": build_sections_list(deliverable_type, config),
            "formality": config.get("formality", "professional"),
            "sensitivity": config.get("sensitivity", "confidential"),
        })

    elif deliverable_type == "research_brief":
        subjects = config.get("subjects", [])
        fields.update({
            "focus_area": config.get("focus_area", "market"),
            "subjects_list": "\n".join(f"- {s}" for s in subjects) if subjects else "- General research",
            "purpose": config.get("purpose", "Inform decision-making"),
            "sections_list": build_sections_list(deliverable_type, config),
            "depth": config.get("depth", "analysis"),
        })

    elif deliverable_type == "meeting_summary":
        participants = config.get("participants", [])
        fields.update({
            "meeting_name": config.get("meeting_name", deliverable.get("title", "")),
            "meeting_type": config.get("meeting_type", "team_sync"),
            "participants": ", ".join(participants) if participants else "Team members",
            "sections_list": build_sections_list(deliverable_type, config),
            "format": config.get("format", "structured"),
        })

    # Beta Tier
    elif deliverable_type == "client_proposal":
        fields.update({
            "client_name": config.get("client_name", "the client"),
            "project_type": config.get("project_type", "new_engagement").replace("_", " "),
            "service_category": config.get("service_category", "consulting"),
            "sections_list": build_sections_list(deliverable_type, config),
            "tone": config.get("tone", "consultative"),
            "pricing_instruction": "Include pricing/investment section" if config.get("include_pricing", True) else "Do NOT include specific pricing",
        })

    elif deliverable_type == "performance_self_assessment":
        review_period = config.get("review_period", "quarterly")
        role_level = config.get("role_level", "ic")
        tone = config.get("tone", "balanced")
        tone_guidance = {
            "humble": "acknowledge contributions without overselling",
            "balanced": "confidently state accomplishments while acknowledging growth areas",
            "confident": "clearly articulate value and impact",
        }
        fields.update({
            "review_period": review_period,
            "role_level": role_level.replace("_", " "),
            "sections_list": build_sections_list(deliverable_type, config),
            "tone": tone,
            "tone_guidance": tone_guidance.get(tone, "balanced perspective"),
            "quantify_instruction": "- Quantify impact with specific numbers, percentages, and metrics wherever possible" if config.get("quantify_impact", True) else "",
        })

    elif deliverable_type == "newsletter_section":
        length = config.get("length", "medium")
        length_words = {"short": "100-200 words", "medium": "200-400 words", "long": "400-800 words"}
        fields.update({
            "newsletter_name": config.get("newsletter_name", "Newsletter"),
            "section_type": config.get("section_type", "main_story").replace("_", " "),
            "audience": config.get("audience", "customers"),
            "sections_list": build_sections_list(deliverable_type, config),
            "voice": config.get("voice", "brand"),
            "length": length_words.get(length, "200-400 words"),
        })

    elif deliverable_type == "changelog":
        fields.update({
            "product_name": config.get("product_name", "the product"),
            "release_type": config.get("release_type", "weekly"),
            "audience": config.get("audience", "mixed"),
            "sections_list": build_sections_list(deliverable_type, config),
            "format": config.get("format", "user_friendly").replace("_", "-"),
            "links_instruction": "- Include links to documentation or features where available" if config.get("include_links", True) else "",
        })

    elif deliverable_type == "one_on_one_prep":
        focus_areas = config.get("focus_areas", ["performance", "growth"])
        fields.update({
            "report_name": config.get("report_name", "the team member"),
            "meeting_cadence": config.get("meeting_cadence", "weekly"),
            "relationship": config.get("relationship", "direct_report").replace("_", " "),
            "sections_list": build_sections_list(deliverable_type, config),
            "focus_areas": ", ".join(focus_areas),
        })

    elif deliverable_type == "board_update":
        tone = config.get("tone", "balanced")
        tone_guidance = {
            "optimistic": "emphasize progress and opportunities while being honest",
            "balanced": "present both wins and challenges with equal weight",
            "candid": "be direct about challenges and what's needed",
        }
        fields.update({
            "company_name": config.get("company_name", "the company"),
            "stage": config.get("stage", "seed").replace("_", " "),
            "update_type": config.get("update_type", "quarterly"),
            "sections_list": build_sections_list(deliverable_type, config),
            "tone": tone,
            "tone_guidance": tone_guidance.get(tone, "balanced perspective"),
            "comparisons_instruction": "Include comparisons vs. last period and vs. plan where data is available" if config.get("include_comparisons", True) else "",
        })

    # =========================================================================
    # ADR-029 Phase 3: Email-Specific Types
    # =========================================================================

    elif deliverable_type == "inbox_summary":
        fields.update({
            "summary_period": config.get("summary_period", "daily"),
            "inbox_scope": config.get("inbox_scope", "unread"),
            "sections_list": build_sections_list(deliverable_type, config),
            "prioritization": config.get("prioritization", "by_urgency").replace("_", " "),
        })

    elif deliverable_type == "reply_draft":
        suggested_actions = config.get("suggested_actions", [])
        fields.update({
            "thread_id": config.get("thread_id", ""),
            "tone": config.get("tone", "professional"),
            "sections_list": build_sections_list(deliverable_type, config),
            "quote_instruction": "Include relevant quotes from the original message" if config.get("include_original_quotes", True) else "Do not quote the original message",
            "suggested_actions": f"USER HINTS:\n{chr(10).join('- ' + a for a in suggested_actions)}" if suggested_actions else "",
        })

    elif deliverable_type == "follow_up_tracker":
        fields.update({
            "tracking_period": config.get("tracking_period", "7d"),
            "sections_list": build_sections_list(deliverable_type, config),
            "prioritize_by": config.get("prioritize_by", "age").replace("_", " "),
        })

    elif deliverable_type == "thread_summary":
        detail_level = config.get("detail_level", "brief")
        detail_guidance = "concise and scannable" if detail_level == "brief" else "thorough with context"
        fields.update({
            "thread_id": config.get("thread_id", ""),
            "sections_list": build_sections_list(deliverable_type, config),
            "detail_level": detail_level,
            "detail_guidance": detail_guidance,
        })

    # =========================================================================
    # ADR-046: Calendar-Triggered Types
    # =========================================================================

    elif deliverable_type == "meeting_prep":
        # Extract meeting info from config
        meeting_info = config.get("meeting", {})
        attendees = meeting_info.get("attendees", [])
        attendee_names = [a.get("display_name") or a.get("email", "Unknown") for a in attendees[:10]]
        fields.update({
            "meeting_title": meeting_info.get("title", config.get("meeting_title", "Upcoming Meeting")),
            "meeting_time": meeting_info.get("start", config.get("meeting_time", "")),
            "attendees_list": ", ".join(attendee_names) if attendee_names else "Not specified",
            "meeting_description": f"MEETING DESCRIPTION:\n{meeting_info.get('description', '')}" if meeting_info.get("description") else "",
            "sections_list": build_sections_list(deliverable_type, config),
        })

    elif deliverable_type == "weekly_calendar_preview":
        # Extract calendar summary info
        calendar_summary = config.get("calendar_summary", {})
        fields.update({
            "week_start": config.get("week_start", "this week"),
            "calendar_summary": calendar_summary.get("raw", "See events in context"),
            "meeting_count": str(calendar_summary.get("meeting_count", "multiple")),
            "total_hours": str(calendar_summary.get("total_hours", "N/A")),
            "busiest_day": calendar_summary.get("busiest_day", "N/A"),
            "free_blocks": calendar_summary.get("free_blocks", "See calendar for details"),
            "sections_list": build_sections_list(deliverable_type, config),
        })

    else:  # custom and any unknown types
        fields.update({
            "description": config.get("description", deliverable.get("description", "")),
            "structure_notes": f"STRUCTURE NOTES:\n{config.get('structure_notes', '')}" if config.get("structure_notes") else "",
        })

    # Format the template
    try:
        return template.format(**fields)
    except KeyError as e:
        logger.warning(f"Missing field in prompt template: {e}")
        # Fall back to custom template
        return TYPE_PROMPTS["custom"].format(**{
            "title": deliverable.get("title", "Deliverable"),
            "description": config.get("description", ""),
            "structure_notes": "",
            "gathered_context": gathered_context,
            "recipient_context": recipient_text,
            "past_versions": past_versions,
        })


# =============================================================================
# ADR-019: Validation Functions
# =============================================================================

def validate_status_report(content: str, config: dict) -> dict:
    """Validate a status report output."""
    issues = []

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    content_lower = content.lower()

    # Check required sections are present
    section_keywords = {
        "summary": ["summary", "tl;dr", "overview", "at a glance"],
        "accomplishments": ["accomplishments", "completed", "achieved", "done", "wins"],
        "blockers": ["blockers", "challenges", "issues", "obstacles", "risks"],
        "next_steps": ["next steps", "upcoming", "planned", "looking ahead", "next week"],
        "metrics": ["metrics", "numbers", "kpis", "data", "performance"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check length
    word_count = len(content.split())
    detail_level = config.get("detail_level", "standard")
    expected = {
        "brief": (200, 500),
        "standard": (400, 1000),
        "detailed": (800, 2000),
    }
    min_words, max_words = expected.get(detail_level, (400, 1000))

    if word_count < min_words * 0.7:  # 30% tolerance
        issues.append(f"Too short: {word_count} words (expected {min_words}+)")
    if word_count > max_words * 1.5:
        issues.append(f"Too long: {word_count} words (expected ~{max_words})")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_stakeholder_update(content: str, config: dict) -> dict:
    """Validate a stakeholder update output."""
    issues = []

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    content_lower = content.lower()

    section_keywords = {
        "executive_summary": ["executive summary", "summary", "overview", "at a glance"],
        "highlights": ["highlights", "wins", "achievements", "key developments"],
        "challenges": ["challenges", "obstacles", "issues", "mitigations"],
        "metrics": ["metrics", "numbers", "kpis", "performance"],
        "outlook": ["outlook", "looking ahead", "next period", "focus areas"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for executive summary at the start
    if "executive_summary" in required_sections:
        # Should appear in first 20% of content
        first_portion = content[:len(content) // 5].lower()
        if not any(kw in first_portion for kw in ["summary", "overview"]):
            issues.append("Executive summary should appear at the beginning")

    # Check word count (stakeholder updates should be substantial)
    word_count = len(content.split())
    if word_count < 300:
        issues.append(f"Too brief for stakeholder update: {word_count} words (expected 300+)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_research_brief(content: str, config: dict) -> dict:
    """Validate a research brief output."""
    issues = []

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    content_lower = content.lower()

    section_keywords = {
        "key_takeaways": ["key takeaways", "takeaways", "key findings", "main points"],
        "findings": ["findings", "research shows", "analysis reveals", "discovered"],
        "implications": ["implications", "means for", "impact", "consequences"],
        "recommendations": ["recommendations", "suggest", "recommend", "action items"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check depth/length
    word_count = len(content.split())
    depth = config.get("depth", "analysis")
    expected = {
        "scan": (250, 600),
        "analysis": (400, 1200),
        "deep_dive": (800, 2500),
    }
    min_words, max_words = expected.get(depth, (400, 1200))

    if word_count < min_words * 0.7:
        issues.append(f"Too shallow for {depth}: {word_count} words (expected {min_words}+)")

    # Check for generic/vague content
    vague_phrases = ["it is important", "various factors", "many aspects", "in general"]
    vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
    if vague_count > 3:
        issues.append("Content may be too generic - add more specific insights")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_meeting_summary(content: str, config: dict) -> dict:
    """Validate a meeting summary output."""
    issues = []

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    content_lower = content.lower()

    section_keywords = {
        "context": ["attendees", "context", "purpose", "participants"],
        "discussion": ["discussed", "discussion", "talked about", "covered"],
        "decisions": ["decisions", "decided", "agreed", "resolved"],
        "action_items": ["action items", "action:", "todo", "next steps", "assigned"],
        "followups": ["follow-up", "followup", "next meeting", "parking lot"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check that action items have owners (look for @ or name patterns)
    if "action_items" in required_sections:
        action_section = re.search(
            r'action items?.*?(?=\n[A-Z]|\n##|\Z)',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if action_section:
            action_text = action_section.group()
            # Look for owner patterns: "@name", "Name:", "[Name]", "(Name)"
            has_owners = bool(re.search(r'[@\[\(]?\b[A-Z][a-z]+\b[\]\)]?:', action_text))
            if not has_owners and len(action_text) > 50:
                issues.append("Action items should have assigned owners")

    # Word count check
    word_count = len(content.split())
    if word_count < 150:
        issues.append(f"Too brief: {word_count} words (expected 150+)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_custom(content: str, config: dict) -> dict:
    """Validate a custom deliverable - minimal validation."""
    issues = []

    word_count = len(content.split())
    if word_count < 50:
        issues.append(f"Content too short: {word_count} words")

    # Custom deliverables get a neutral score
    score = 0.6 if len(issues) == 0 else 0.4
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


# =============================================================================
# Beta Tier Validation Functions
# =============================================================================

def validate_client_proposal(content: str, config: dict) -> dict:
    """Validate a client proposal output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "executive_summary": ["summary", "overview", "introduction"],
        "needs_understanding": ["understand", "needs", "requirements", "goals", "objectives"],
        "approach": ["approach", "methodology", "how we", "our process"],
        "deliverables": ["deliverables", "you will receive", "we will provide"],
        "timeline": ["timeline", "schedule", "milestones", "weeks", "phases"],
        "investment": ["investment", "pricing", "cost", "fee", "budget"],
        "social_proof": ["experience", "clients", "similar", "case", "testimonial"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for generic/vague content
    vague_phrases = ["best practices", "industry-leading", "comprehensive solution", "world-class"]
    vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
    if vague_count > 2:
        issues.append("Content may be too generic - add more specifics")

    word_count = len(content.split())
    if word_count < 300:
        issues.append(f"Too short for a proposal: {word_count} words (expected 300+)")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_performance_self_assessment(content: str, config: dict) -> dict:
    """Validate a performance self-assessment output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "summary": ["summary", "overview", "period"],
        "accomplishments": ["accomplishments", "achieved", "completed", "delivered"],
        "goals_progress": ["goals", "objectives", "targets", "progress"],
        "challenges": ["challenges", "obstacles", "difficulties", "learned"],
        "development": ["development", "growth", "improve", "skills"],
        "next_period_goals": ["next", "upcoming", "focus", "plan to"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for quantification if enabled
    if config.get("quantify_impact", True):
        has_numbers = bool(re.search(r'\d+%|\d+x|\$\d+|\d+ (users|customers|projects|deals)', content))
        if not has_numbers:
            issues.append("Consider adding quantified impact (%, numbers, metrics)")

    word_count = len(content.split())
    review_period = config.get("review_period", "quarterly")
    expected = {"quarterly": (400, 1000), "semi_annual": (600, 1500), "annual": (800, 2000)}
    min_words, _ = expected.get(review_period, (400, 1000))
    if word_count < min_words * 0.7:
        issues.append(f"Too short for {review_period} review: {word_count} words")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_newsletter_section(content: str, config: dict) -> dict:
    """Validate a newsletter section output."""
    issues = []

    word_count = len(content.split())
    length = config.get("length", "medium")
    expected = {"short": (80, 250), "medium": (180, 500), "long": (350, 1000)}
    min_words, max_words = expected.get(length, (180, 500))

    if word_count < min_words * 0.7:
        issues.append(f"Too short: {word_count} words (expected {min_words}+)")
    if word_count > max_words * 1.5:
        issues.append(f"Too long: {word_count} words (expected ~{max_words})")

    # Check for CTA if enabled
    sections = config.get("sections", {})
    if sections.get("cta", True):
        cta_keywords = ["click", "sign up", "learn more", "check out", "try", "get started", "visit"]
        if not any(kw in content.lower() for kw in cta_keywords):
            issues.append("Missing call to action")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_changelog(content: str, config: dict) -> dict:
    """Validate a changelog output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "highlights": ["highlights", "notable", "major"],
        "new_features": ["new", "added", "introducing"],
        "improvements": ["improved", "enhanced", "better", "updated"],
        "bug_fixes": ["fixed", "bug", "resolved", "issue"],
        "breaking_changes": ["breaking", "migration", "deprecated"],
        "whats_next": ["next", "upcoming", "roadmap", "coming soon"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    word_count = len(content.split())
    if word_count < 100:
        issues.append(f"Too brief: {word_count} words (expected 100+)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_one_on_one_prep(content: str, config: dict) -> dict:
    """Validate a 1:1 prep output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "context": ["context", "since last", "recent", "update"],
        "topics": ["topics", "discuss", "agenda", "talk about"],
        "recognition": ["recognition", "kudos", "great", "well done", "appreciate"],
        "concerns": ["concerns", "issues", "blockers", "challenges"],
        "career": ["career", "growth", "development", "goals"],
        "previous_actions": ["action items", "follow up", "previous", "last time"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for personalization
    report_name = config.get("report_name", "")
    if report_name and report_name.lower() not in content_lower:
        issues.append(f"Not personalized to {report_name}")

    word_count = len(content.split())
    if word_count < 150:
        issues.append(f"Too brief: {word_count} words (expected 150+)")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_board_update(content: str, config: dict) -> dict:
    """Validate a board update output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "executive_summary": ["summary", "overview", "tldr"],
        "metrics": ["metrics", "kpis", "numbers", "growth", "revenue", "users"],
        "strategic_progress": ["strategic", "progress", "initiatives", "goals"],
        "challenges": ["challenges", "risks", "concerns", "obstacles"],
        "financials": ["financials", "cash", "runway", "burn", "revenue"],
        "asks": ["asks", "need", "request", "help with", "decision"],
        "outlook": ["outlook", "next quarter", "ahead", "plan"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Board updates should have metrics
    if sections.get("metrics", True):
        has_numbers = bool(re.search(r'\d+%|\$\d+|\d+k|\d+M|\d+ (users|customers)', content))
        if not has_numbers:
            issues.append("Missing quantified metrics")

    # Check if asks section is clear
    if sections.get("asks", True):
        if "asks" not in content_lower and "need" not in content_lower and "request" not in content_lower:
            issues.append("Asks section should be explicit")

    word_count = len(content.split())
    if word_count < 400:
        issues.append(f"Too brief for board update: {word_count} words (expected 400+)")
    if word_count > 1200:
        issues.append(f"Too long: {word_count} words (board members are busy, target 500-1000)")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


# =============================================================================
# ADR-029 Phase 3: Email-Specific Validation Functions
# =============================================================================

def validate_inbox_summary(content: str, config: dict) -> dict:
    """Validate an inbox summary output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "overview": ["overview", "summary", "inbox", "messages", "emails"],
        "urgent": ["urgent", "immediate", "asap", "priority", "critical"],
        "action_required": ["action", "required", "respond", "reply", "need to"],
        "fyi_items": ["fyi", "informational", "no action", "awareness"],
        "threads_to_close": ["close", "archive", "wrap up", "complete", "done"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for structure (should have bullet points or sections)
    has_structure = "- " in content or "• " in content or "##" in content
    if not has_structure:
        issues.append("Summary should be scannable - use bullet points or sections")

    word_count = len(content.split())
    if word_count < 100:
        issues.append(f"Too brief: {word_count} words (expected 100+)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_reply_draft(content: str, config: dict) -> dict:
    """Validate a reply draft output."""
    issues = []
    content_lower = content.lower()

    # Reply drafts should have a greeting and closing
    has_greeting = any(g in content_lower[:100] for g in ["hi", "hello", "dear", "hey", "good morning", "good afternoon"])
    has_closing = any(c in content_lower[-200:] for c in ["best", "thanks", "regards", "cheers", "sincerely", "thank you"])

    if not has_greeting:
        issues.append("Reply should start with an appropriate greeting")
    if not has_closing:
        issues.append("Reply should have a closing/sign-off")

    # Check for acknowledgment if enabled
    sections = config.get("sections", {})
    if sections.get("acknowledgment", True):
        ack_keywords = ["thank you for", "thanks for", "regarding", "re:", "about your", "in response"]
        if not any(kw in content_lower for kw in ack_keywords):
            issues.append("Consider acknowledging the original message")

    word_count = len(content.split())
    if word_count < 30:
        issues.append(f"Reply too brief: {word_count} words")
    if word_count > 500:
        issues.append(f"Reply may be too long: {word_count} words (consider being more concise)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_follow_up_tracker(content: str, config: dict) -> dict:
    """Validate a follow-up tracker output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "overdue": ["overdue", "past due", "late", "pending", "no response"],
        "due_soon": ["due soon", "this week", "upcoming", "coming up"],
        "waiting_on_others": ["waiting", "pending from", "awaiting", "no reply from"],
        "commitments_made": ["committed", "promised", "said", "agreed to", "will"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Should have specific items (look for names, dates, or bullet points)
    has_items = "- " in content or "• " in content or re.search(r'\d{1,2}[/-]\d{1,2}', content)
    if not has_items:
        issues.append("Tracker should list specific follow-up items")

    word_count = len(content.split())
    if word_count < 50:
        issues.append(f"Too brief: {word_count} words (expected 50+)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_thread_summary(content: str, config: dict) -> dict:
    """Validate a thread summary output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "participants": ["participants", "involved", "from", "between", "with"],
        "timeline": ["timeline", "on", "at", "started", "then", "followed by"],
        "key_points": ["key points", "main", "discussed", "topics", "covered"],
        "decisions": ["decided", "decision", "agreed", "concluded", "resolved"],
        "open_questions": ["open", "questions", "unclear", "tbd", "pending", "unresolved"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    detail_level = config.get("detail_level", "brief")
    word_count = len(content.split())
    expected = {"brief": (100, 400), "detailed": (300, 1000)}
    min_words, max_words = expected.get(detail_level, (100, 400))

    if word_count < min_words * 0.7:
        issues.append(f"Too brief for {detail_level} summary: {word_count} words")
    if word_count > max_words * 1.5:
        issues.append(f"Too long for {detail_level} summary: {word_count} words")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


# =============================================================================
# ADR-035: Platform-First Wave 1 Validators
# =============================================================================

def validate_slack_channel_digest(content: str, config: dict) -> dict:
    """Validate a Slack channel digest output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "hot_threads": ["thread", "discussion", "conversation", "talked about", "replies"],
        "key_decisions": ["decided", "decision", "agreed", "concluded", "going with"],
        "unanswered_questions": ["question", "unanswered", "?", "unclear", "need to know"],
        "mentions": ["mention", "highlight", "notable", "important", "attention"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Slack digests should be concise
    char_count = len(content)
    if char_count > 2500:
        issues.append(f"Too long for Slack: {char_count} chars (max ~2000)")

    # Should have bullet points for scannability
    has_bullets = "- " in content or "• " in content or "* " in content
    if not has_bullets:
        issues.append("Digest should use bullet points for scannability")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_slack_standup(content: str, config: dict) -> dict:
    """Validate a Slack standup output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "done": ["done", "completed", "finished", "shipped", "merged"],
        "doing": ["doing", "working on", "in progress", "continuing", "starting"],
        "blockers": ["blocker", "blocked", "stuck", "waiting", "need"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Standups should be brief
    word_count = len(content.split())
    if word_count > 250:
        issues.append(f"Standup too verbose: {word_count} words (aim for <200)")
    if word_count < 30:
        issues.append(f"Standup too brief: {word_count} words")

    # Check for bullet format
    format_type = config.get("format", "bullet")
    if format_type == "bullet" and not ("- " in content or "• " in content):
        issues.append("Bullet format requested but no bullets found")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_gmail_inbox_brief(content: str, config: dict) -> dict:
    """Validate a Gmail inbox brief output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "urgent": ["urgent", "immediate", "asap", "time-sensitive", "deadline"],
        "action_required": ["action", "respond", "reply", "need to", "follow up"],
        "fyi": ["fyi", "informational", "no action", "reference", "note"],
        "follow_ups": ["follow up", "revisit", "check back", "pending"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Should have structure
    has_bullets = "- " in content or "• " in content
    if not has_bullets:
        issues.append("Brief should use bullet points for scannability")

    # Inbox briefs should be concise
    word_count = len(content.split())
    if word_count < 50:
        issues.append(f"Brief too short: {word_count} words")
    if word_count > 600:
        issues.append(f"Brief too long: {word_count} words (aim for 300-500)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_notion_page_summary(content: str, config: dict) -> dict:
    """Validate a Notion page summary output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "changes": ["change", "modified", "updated", "edited", "revised"],
        "new_content": ["new", "added", "created", "inserted"],
        "completed_tasks": ["completed", "done", "finished", "checked", "resolved"],
        "open_comments": ["comment", "open", "unresolved", "discussion", "thread"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check word count
    word_count = len(content.split())
    if word_count < 50:
        issues.append(f"Summary too brief: {word_count} words")
    if word_count > 500:
        issues.append(f"Summary too long: {word_count} words (aim for 200-400)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_output(deliverable_type: str, content: str, config: dict) -> dict:
    """
    Validate generated content based on deliverable type.

    Returns:
        {
            "valid": bool,
            "issues": list[str],
            "score": float  # 0.0 to 1.0
        }
    """
    validators = {
        # Tier 1 - Stable
        "status_report": validate_status_report,
        "stakeholder_update": validate_stakeholder_update,
        "research_brief": validate_research_brief,
        "meeting_summary": validate_meeting_summary,
        "custom": validate_custom,
        # Beta Tier
        "client_proposal": validate_client_proposal,
        "performance_self_assessment": validate_performance_self_assessment,
        "newsletter_section": validate_newsletter_section,
        "changelog": validate_changelog,
        "one_on_one_prep": validate_one_on_one_prep,
        "board_update": validate_board_update,
        # ADR-029 Phase 3: Email-specific
        "inbox_summary": validate_inbox_summary,
        "reply_draft": validate_reply_draft,
        "follow_up_tracker": validate_follow_up_tracker,
        "thread_summary": validate_thread_summary,
        # ADR-035: Platform-First Wave 1
        "slack_channel_digest": validate_slack_channel_digest,
        "slack_standup": validate_slack_standup,
        "gmail_inbox_brief": validate_gmail_inbox_brief,
        "notion_page_summary": validate_notion_page_summary,
    }

    validator = validators.get(deliverable_type, validate_custom)
    return validator(content, config)


async def execute_deliverable_pipeline(
    client,
    user_id: str,
    deliverable_id: str,
    version_number: int,
    trigger_context: Optional[dict] = None,
) -> dict:
    """
    Execute the full deliverable pipeline.

    Creates a new version, runs gather → synthesize → stage,
    and updates the deliverable with last_run_at.

    Args:
        client: Supabase client
        user_id: User UUID
        deliverable_id: Deliverable UUID
        version_number: Version number to create
        trigger_context: Optional context about what triggered this execution
            ADR-031 Phase 4: For event triggers, includes:
            - type: "event" or "schedule"
            - platform: "slack" or "gmail"
            - event_type: "app_mention", "message_im", etc.
            - resource_id: Channel/thread that triggered
            - event_ts: When the event occurred

    Returns:
        Pipeline result with version_id, status, and message
    """
    trigger_type = trigger_context.get("type", "schedule") if trigger_context else "schedule"
    logger.info(f"[PIPELINE] Starting: deliverable={deliverable_id}, version={version_number}, trigger={trigger_type}")

    # Get deliverable details
    deliverable_result = (
        client.table("deliverables")
        .select("*")
        .eq("id", deliverable_id)
        .single()
        .execute()
    )

    if not deliverable_result.data:
        return {"success": False, "error": "Deliverable not found"}

    deliverable = deliverable_result.data
    project_id = deliverable.get("project_id")

    # Create version record
    version_result = (
        client.table("deliverable_versions")
        .insert({
            "deliverable_id": deliverable_id,
            "version_number": version_number,
            "status": "generating",
        })
        .execute()
    )

    if not version_result.data:
        return {"success": False, "error": "Failed to create version"}

    version = version_result.data[0]
    version_id = version["id"]

    try:
        # Step 1: Gather
        logger.info(f"[PIPELINE] Step 1: Gather")
        gather_result = await execute_gather_step(
            client=client,
            user_id=user_id,
            project_id=project_id,
            deliverable=deliverable,
            version_id=version_id,
        )

        if not gather_result.get("success"):
            await update_version_status(client, version_id, "rejected")
            return {
                "success": False,
                "version_id": version_id,
                "status": "rejected",
                "message": f"Gather step failed: {gather_result.get('error')}",
            }

        gathered_context = gather_result.get("output", "")

        # Step 2: Synthesize
        logger.info(f"[PIPELINE] Step 2: Synthesize")
        synthesize_result = await execute_synthesize_step(
            client=client,
            user_id=user_id,
            project_id=project_id,
            deliverable=deliverable,
            version_id=version_id,
            gathered_context=gathered_context,
            gather_work_id=gather_result.get("work_id"),
        )

        if not synthesize_result.get("success"):
            await update_version_status(client, version_id, "rejected")
            return {
                "success": False,
                "version_id": version_id,
                "status": "rejected",
                "message": f"Synthesize step failed: {synthesize_result.get('error')}",
            }

        draft_content = synthesize_result.get("output", "")

        # Step 3: Stage
        logger.info(f"[PIPELINE] Step 3: Stage")
        stage_result = await execute_stage_step(
            client=client,
            version_id=version_id,
            draft_content=draft_content,
            deliverable=deliverable,
        )

        # Update deliverable last_run_at
        client.table("deliverables").update({
            "last_run_at": datetime.utcnow().isoformat(),
        }).eq("id", deliverable_id).execute()

        # ADR-028/029: Handle full_auto governance - auto-approve and deliver
        governance = deliverable.get("governance", "manual")
        destination = deliverable.get("destination")
        final_status = "staged"
        delivery_result = None

        if governance == "full_auto" and destination:
            logger.info(f"[PIPELINE] Full-auto: auto-approving and delivering version={version_id}")

            # Auto-approve the version
            client.table("deliverable_versions").update({
                "status": "approved",
                "final_content": draft_content,  # Use draft as final
                "approved_at": datetime.utcnow().isoformat(),
            }).eq("id", version_id).execute()
            final_status = "approved"

            # Trigger delivery
            try:
                from services.delivery import get_delivery_service
                delivery_service = get_delivery_service(client)
                delivery_result = await delivery_service.deliver_version(
                    version_id=version_id,
                    user_id=user_id
                )
                logger.info(
                    f"[PIPELINE] Full-auto delivery complete: {delivery_result.status.value}"
                )
                if delivery_result.status.value == "success":
                    final_status = "delivered"
            except Exception as e:
                logger.error(f"[PIPELINE] Full-auto delivery failed: {e}")
                # Don't fail the pipeline, content is still approved

        logger.info(f"[PIPELINE] Complete: version={version_id}, status={final_status}")

        return {
            "success": True,
            "version_id": version_id,
            "status": final_status,
            "message": "Deliverable ready for review" if final_status == "staged" else "Deliverable delivered",
            "delivery": delivery_result.model_dump() if delivery_result else None,
        }

    except Exception as e:
        logger.error(f"[PIPELINE] Error: {e}")
        try:
            await update_version_status(client, version_id, "rejected")
        except Exception:
            pass  # Don't fail if status update fails
        return {
            "success": False,
            "version_id": version_id,
            "status": "rejected",
            "message": str(e),
        }


async def execute_gather_step(
    client,
    user_id: str,
    project_id: str,
    deliverable: dict,
    version_id: str,
) -> dict:
    """
    Step 1: Gather context from sources.

    Uses research agent to pull latest information from configured sources.
    Output is saved as a memory with source_type='agent_output'.

    ADR-029 Phase 2: For integration_import sources, we fetch actual data
    from the integration (Gmail, Slack, Notion) via MCP.

    ADR-030 Phase 5: Supports delta extraction mode using last_run_at.
    """
    from dateutil import parser as dateparser

    sources = deliverable.get("sources", [])
    title = deliverable.get("title", "Deliverable")
    deliverable_id = deliverable.get("id")

    # ADR-030: Get last_run_at for delta extraction
    last_run_at = None
    last_run_str = deliverable.get("last_run_at")
    if last_run_str:
        try:
            last_run_at = dateparser.parse(last_run_str)
            if last_run_at.tzinfo:
                last_run_at = last_run_at.replace(tzinfo=None)  # Use naive UTC
        except Exception as e:
            logger.warning(f"[GATHER] Could not parse last_run_at: {e}")

    # Build gather prompt
    source_descriptions = []
    integration_data_sections = []
    source_fetch_results = []

    # ADR-030 Phase 6: Collect integration sources for parallel fetching
    integration_sources = []
    for idx, source in enumerate(sources):
        source_type = source.get("type", "description")
        value = source.get("value", "")
        label = source.get("label", "")

        if source_type == "url":
            source_descriptions.append(f"- Web source: {value}")
        elif source_type == "document":
            source_descriptions.append(f"- Document: {label or value}")
        elif source_type == "integration_import":
            provider = source.get("provider", "unknown")
            source_query = source.get("source", "")
            source_descriptions.append(f"- Integration ({provider}): {source_query or 'default'}")
            integration_sources.append((idx, source))
        else:
            source_descriptions.append(f"- Context: {value}")

    # ADR-030 Phase 6: Parallel fetching for integration sources
    # Different providers can be fetched in parallel safely
    # Same provider sources are also safe as they use different API endpoints
    if integration_sources:
        logger.info(f"[GATHER] Fetching {len(integration_sources)} integration sources in parallel")

        async def fetch_with_index(idx: int, source: dict) -> tuple[int, SourceFetchResult]:
            """Wrapper to track source index with result."""
            provider = source.get("provider", "unknown")
            logger.info(f"[GATHER] Parallel fetch: {provider} (delta={last_run_at is not None})")
            result = await fetch_integration_source_data(
                client=client,
                user_id=user_id,
                source=source,
                last_run_at=last_run_at,
                deliverable_id=deliverable_id,
                source_index=idx,
                version_id=version_id,
            )
            return (idx, result)

        # Fetch all integration sources in parallel
        fetch_tasks = [fetch_with_index(idx, source) for idx, source in integration_sources]
        indexed_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Process results in order
        for item in indexed_results:
            if isinstance(item, Exception):
                logger.error(f"[GATHER] Parallel fetch exception: {item}")
                source_fetch_results.append(SourceFetchResult(error=str(item)))
            else:
                idx, fetch_result = item
                source_fetch_results.append(fetch_result)
                if fetch_result.content:
                    integration_data_sections.append(fetch_result.content)
                elif fetch_result.error:
                    logger.warning(f"[GATHER] Source fetch error: {fetch_result.error}")

    # ADR-030: Compute source fetch summary
    sources_total = len([s for s in sources if s.get("type") == "integration_import"])
    sources_succeeded = len([r for r in source_fetch_results if r.content and not r.error])
    sources_failed = len([r for r in source_fetch_results if r.error])
    delta_mode_used = any(r.delta_mode_used for r in source_fetch_results)

    # Store source fetch summary on the version
    if source_fetch_results:
        try:
            time_range_start = min(
                (r.time_range_start for r in source_fetch_results if r.time_range_start),
                default=None
            )
            time_range_end = max(
                (r.time_range_end for r in source_fetch_results if r.time_range_end),
                default=None
            )
            summary = {
                "sources_total": sources_total,
                "sources_succeeded": sources_succeeded,
                "sources_failed": sources_failed,
                "delta_mode_used": delta_mode_used,
                "time_range_start": time_range_start.isoformat() if time_range_start else None,
                "time_range_end": time_range_end.isoformat() if time_range_end else None,
            }
            client.table("deliverable_versions").update({
                "source_fetch_summary": summary,
            }).eq("id", version_id).execute()
        except Exception as e:
            logger.warning(f"[GATHER] Failed to update source fetch summary: {e}")

    sources_text = "\n".join(source_descriptions) if source_descriptions else "No specific sources configured"

    # Include fetched integration data in the prompt
    integration_context = ""
    if integration_data_sections:
        integration_context = "\n\n## Integration Data (Fetched)\n\n" + "\n\n".join(integration_data_sections)

    # ADR-031: Fetch ephemeral context for this deliverable's sources
    ephemeral_context_text = ""
    try:
        from services.ephemeral_context import get_context_summary_for_generation

        ephemeral_summary = await get_context_summary_for_generation(
            db_client=client,
            user_id=user_id,
            deliverable_sources=sources,
            max_items=100,
        )
        if ephemeral_summary:
            ephemeral_context_text = f"\n\n## Recent Platform Context (Ephemeral)\n\n{ephemeral_summary}"
            logger.info(f"[GATHER] Included ephemeral context ({len(ephemeral_summary)} chars)")
    except Exception as e:
        logger.warning(f"[GATHER] Failed to fetch ephemeral context (non-fatal): {e}")

    gather_prompt = f"""Gather the latest context and information for producing: {title}

Description: {deliverable.get('description', 'No description provided')}

Configured sources:
{sources_text}
{integration_context}
{ephemeral_context_text}

Your task:
1. Review and synthesize any available information from the sources
2. Pay special attention to signals in the ephemeral context (hot threads, unanswered questions, stalled items)
3. Identify key updates, changes, or new data since the last delivery
4. Note any gaps or missing information that might be needed
5. Summarize the gathered context in a structured format

Output a comprehensive context summary that will be used to produce the deliverable."""

    # Create work ticket
    # Note: user_id is required for RLS when project_id is NULL (ambient work)
    ticket_data = {
        "task": gather_prompt,
        "agent_type": "synthesizer",  # ADR-045: Renamed from "research"
        "project_id": project_id,
        "user_id": user_id,  # Required for ambient work RLS policy
        "parameters": json.dumps({
            "deliverable_id": deliverable["id"],
            "step": "gather",
        }),
        "status": "pending",
        "deliverable_id": deliverable["id"],
        "deliverable_version_id": version_id,
        "pipeline_step": "gather",
        "chain_output_as_memory": True,
    }

    ticket_result = client.table("work_tickets").insert(ticket_data).execute()

    if not ticket_result.data:
        return {"success": False, "error": "Failed to create gather work ticket"}

    ticket_id = ticket_result.data[0]["id"]

    # Execute the work
    result = await execute_work_ticket(
        client=client,
        user_id=user_id,
        ticket_id=ticket_id,
    )

    if result.get("success"):
        # Save output as memory
        output_content = ""
        outputs = result.get("outputs", [])
        if outputs:
            output_content = outputs[0].get("content", "")

        if output_content:
            await save_as_memory(
                client=client,
                user_id=user_id,
                project_id=project_id,
                content=f"[GATHER] {output_content}",
                source_type="agent_output",
                tags=["pipeline:gather", f"deliverable:{deliverable['id']}"],
            )

        return {
            "success": True,
            "work_id": ticket_id,
            "output": output_content,
        }

    return {
        "success": False,
        "error": result.get("error", "Gather execution failed"),
    }


async def execute_synthesize_step(
    client,
    user_id: str,
    project_id: str,
    deliverable: dict,
    version_id: str,
    gathered_context: str,
    gather_work_id: Optional[str] = None,
) -> dict:
    """
    Step 2: Synthesize the deliverable content.

    ADR-019: Uses type-specific prompts based on deliverable_type and type_config.
    Falls back to generic prompt for legacy deliverables without type.
    """
    title = deliverable.get("title", "Deliverable")
    recipient = deliverable.get("recipient_context", {})

    # ADR-019: Get deliverable type and config
    deliverable_type = deliverable.get("deliverable_type", "custom")
    type_config = deliverable.get("type_config", {})

    # Get past versions for preference learning
    past_versions = await get_past_versions_context(client, deliverable["id"])

    # Build recipient context text
    recipient_text = ""
    if recipient:
        recipient_parts = []
        if recipient.get("name"):
            recipient_parts.append(f"Recipient: {recipient['name']}")
        if recipient.get("role"):
            recipient_parts.append(f"Role: {recipient['role']}")
        if recipient.get("priorities"):
            recipient_parts.append(f"Key priorities: {', '.join(recipient['priorities'])}")
        if recipient.get("notes"):
            recipient_parts.append(f"Notes: {recipient['notes']}")
        if recipient_parts:
            recipient_text = "RECIPIENT CONTEXT:\n" + "\n".join(recipient_parts)

    # ADR-019: Build type-specific prompt
    synthesize_prompt = build_type_prompt(
        deliverable_type=deliverable_type,
        config=type_config,
        deliverable=deliverable,
        gathered_context=gathered_context,
        recipient_text=recipient_text,
        past_versions=past_versions,
    )

    logger.info(f"[SYNTHESIZE] Using type-specific prompt for type={deliverable_type}")

    # ADR-028: Infer style_context from destination platform if set
    # Priority: 1) explicit type_config.style_context, 2) destination.platform, 3) none
    style_context = type_config.get("style_context")

    if not style_context:
        # Try to infer from destination
        destination = deliverable.get("destination")
        if destination and destination.get("platform"):
            platform = destination["platform"]
            # Map platform to style context
            style_context = platform  # slack, notion, etc. match style profile names
            logger.info(f"[SYNTHESIZE] Inferred style_context={style_context} from destination.platform")

    # Build parameters for content agent
    agent_params = {
        "deliverable_id": deliverable["id"],
        "step": "synthesize",
    }
    if style_context:
        agent_params["style_context"] = style_context
        logger.info(f"[SYNTHESIZE] Using style_context={style_context}")

    # Create work ticket with dependency
    # Note: user_id is required for RLS when project_id is NULL (ambient work)
    ticket_data = {
        "task": synthesize_prompt,
        "agent_type": "deliverable",  # ADR-045: Renamed from "content"
        "project_id": project_id,
        "user_id": user_id,  # Required for ambient work RLS policy
        "parameters": json.dumps(agent_params),
        "status": "pending",
        "deliverable_id": deliverable["id"],
        "deliverable_version_id": version_id,
        "pipeline_step": "synthesize",
        "depends_on_work_id": gather_work_id,
        "chain_output_as_memory": True,
    }

    ticket_result = client.table("work_tickets").insert(ticket_data).execute()

    if not ticket_result.data:
        return {"success": False, "error": "Failed to create synthesize work ticket"}

    ticket_id = ticket_result.data[0]["id"]

    # Execute the work
    result = await execute_work_ticket(
        client=client,
        user_id=user_id,
        ticket_id=ticket_id,
    )

    if result.get("success"):
        output_content = ""
        outputs = result.get("outputs", [])
        if outputs:
            output_content = outputs[0].get("content", "")

        if output_content:
            await save_as_memory(
                client=client,
                user_id=user_id,
                project_id=project_id,
                content=f"[SYNTHESIZE] {output_content[:500]}...",  # Truncate for memory
                source_type="agent_output",
                tags=["pipeline:synthesize", f"deliverable:{deliverable['id']}"],
            )

        return {
            "success": True,
            "work_id": ticket_id,
            "output": output_content,
        }

    return {
        "success": False,
        "error": result.get("error", "Synthesize execution failed"),
    }


async def execute_stage_step(
    client,
    version_id: str,
    draft_content: str,
    deliverable: dict,
) -> dict:
    """
    Step 3: Stage the deliverable for review.

    ADR-019: Runs type-specific validation before staging.
    Updates version with draft content and sets status to 'staged'.
    Stores validation results for quality tracking.
    """
    # ADR-019: Run type-specific validation
    deliverable_type = deliverable.get("deliverable_type", "custom")
    type_config = deliverable.get("type_config", {})

    validation_result = validate_output(deliverable_type, draft_content, type_config)

    logger.info(
        f"[STAGE] Validation for type={deliverable_type}: "
        f"valid={validation_result['valid']}, score={validation_result['score']:.2f}, "
        f"issues={validation_result['issues']}"
    )

    # Store validation result
    try:
        client.table("deliverable_validation_results").insert({
            "version_id": version_id,
            "is_valid": validation_result["valid"],
            "validation_score": validation_result["score"],
            "issues": json.dumps(validation_result["issues"]),
            "validator_version": "1.0.0",  # Track validation logic version
        }).execute()
    except Exception as e:
        logger.warning(f"[STAGE] Failed to store validation result: {e}")

    # Update version with draft content
    update_result = (
        client.table("deliverable_versions")
        .update({
            "draft_content": draft_content,
            "status": "staged",
            "staged_at": datetime.utcnow().isoformat(),
        })
        .eq("id", version_id)
        .execute()
    )

    if not update_result.data:
        return {"success": False, "error": "Failed to stage version"}

    # TODO: Send staging notification email
    # This will use the existing email infrastructure
    # For now, just log it
    logger.info(f"[STAGE] Version {version_id} staged for review")

    return {
        "success": True,
        "validation": validation_result,
    }


async def get_past_versions_context(client, deliverable_id: str) -> str:
    """
    Get context from past versions including feedback patterns.

    Returns a formatted string with learned preferences from edit history.
    """
    # Get recent approved versions with edits
    versions_result = (
        client.table("deliverable_versions")
        .select("version_number, edit_categories, edit_distance_score, feedback_notes")
        .eq("deliverable_id", deliverable_id)
        .eq("status", "approved")
        .order("version_number", desc=True)
        .limit(5)
        .execute()
    )

    versions = versions_result.data or []

    if not versions:
        return ""

    # Aggregate feedback patterns
    patterns = []
    for v in versions:
        categories = v.get("edit_categories", {})
        if categories:
            if categories.get("additions"):
                patterns.append(f"User added: {', '.join(categories['additions'][:3])}")
            if categories.get("deletions"):
                patterns.append(f"User removed: {', '.join(categories['deletions'][:3])}")

        if v.get("feedback_notes"):
            patterns.append(f"Feedback: {v['feedback_notes']}")

    if not patterns:
        return ""

    return f"""
LEARNED PREFERENCES (from past versions):
{chr(10).join(f'- {p}' for p in patterns[:10])}

Apply these preferences when producing this version."""


async def save_as_memory(
    client,
    user_id: str,
    project_id: str,
    content: str,
    source_type: str = "agent_output",
    tags: Optional[list] = None,
) -> Optional[str]:
    """
    Save content as a project memory.
    """
    memory_data = {
        "user_id": user_id,
        "project_id": project_id,
        "content": content,
        "source_type": source_type,
        "importance": 0.8,
        "tags": tags or [],
    }

    result = client.table("memories").insert(memory_data).execute()

    if result.data:
        return result.data[0]["id"]
    return None


async def update_version_status(client, version_id: str, status: str):
    """Update version status."""
    client.table("deliverable_versions").update({
        "status": status,
    }).eq("id", version_id).execute()
