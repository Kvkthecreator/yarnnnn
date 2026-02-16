"""
Conversation Analysis Service - ADR-060/061

Detects patterns in user conversations and creates suggested deliverables.
Runs as part of unified_scheduler.py Analysis Phase (daily).

This is a SERVICE FUNCTION, not a separate agent, per ADR-061 Two-Path Architecture.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from services.anthropic import get_anthropic_client

logger = logging.getLogger(__name__)

# Model for analysis
ANALYSIS_MODEL = "claude-sonnet-4-20250514"


@dataclass
class AnalystSuggestion:
    """A suggested deliverable detected from conversation patterns."""
    confidence: float  # 0.0 - 1.0
    deliverable_type: str  # e.g., "status_report", "slack_channel_digest"
    title: str
    description: str
    suggested_frequency: str  # "daily", "weekly", "biweekly", "monthly"
    suggested_sources: list[dict] = field(default_factory=list)
    detection_reason: str = ""
    source_sessions: list[str] = field(default_factory=list)


# Deliverable types available for suggestion
SUGGESTABLE_TYPES = {
    # Platform-bound (single platform)
    "slack_channel_digest": {
        "binding": "platform_bound",
        "primary_platform": "slack",
        "description": "Weekly digest of a Slack channel",
    },
    "gmail_inbox_brief": {
        "binding": "platform_bound",
        "primary_platform": "gmail",
        "description": "Daily inbox summary with priority triage",
    },
    # Cross-platform
    "status_report": {
        "binding": "cross_platform",
        "description": "Status update across all connected platforms",
    },
    "weekly_status": {
        "binding": "cross_platform",
        "description": "Weekly summary of activity across platforms",
    },
    # Research
    "research_brief": {
        "binding": "research",
        "description": "Web research on a specific topic",
    },
}


ANALYSIS_SYSTEM_PROMPT = """You are analyzing user conversations to detect implicit work patterns.

Your task: Identify recurring information needs that could become automated deliverables.

**What to look for:**
1. **Explicit frequency mentions**: "every week", "daily", "monthly", "on Mondays"
2. **Repeated queries**: Same type of question asked 2+ times (e.g., "what happened in #engineering")
3. **Audience references**: "for the board", "for my manager", "client update"
4. **Platform-specific patterns**: Slack channel summaries, email triage, Notion updates

**Output JSON array of suggestions:**
```json
[
  {
    "confidence": 0.75,
    "deliverable_type": "slack_channel_digest",
    "title": "Weekly #engineering Digest",
    "description": "Summary of key discussions in #engineering channel",
    "suggested_frequency": "weekly",
    "suggested_sources": [{"type": "slack", "channel": "engineering"}],
    "detection_reason": "User asked about #engineering activity 3 times"
  }
]
```

**Confidence scoring:**
- 0.80+: Explicit request with frequency and clear scope
- 0.60-0.79: Clear pattern but implicit (repeated queries, mentioned audience)
- 0.40-0.59: Possible pattern but ambiguous
- <0.40: Too weak to suggest

**Valid deliverable_type values:**
- slack_channel_digest: Slack channel summary
- gmail_inbox_brief: Email inbox triage
- status_report: Cross-platform status update
- weekly_status: Weekly activity summary
- research_brief: Web research on a topic

**Valid frequency values:**
- daily, weekly, biweekly, monthly

Return ONLY the JSON array, no other text.
Return empty array [] if no patterns detected with confidence >= 0.40.
"""


async def get_recent_sessions(
    client,
    user_id: str,
    days: int = 7,
) -> list[dict]:
    """
    Get recent chat sessions with messages for a user.

    Args:
        client: Supabase client
        user_id: User UUID
        days: How many days back to look

    Returns:
        List of sessions with their messages
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        # Get sessions from last N days
        sessions_result = (
            client.table("chat_sessions")
            .select("id, started_at, context_metadata")
            .eq("user_id", user_id)
            .gte("started_at", since.isoformat())
            .order("started_at", desc=True)
            .limit(50)  # Cap at 50 sessions
            .execute()
        )

        sessions = []
        for session in (sessions_result.data or []):
            # Get messages for this session
            messages_result = (
                client.table("session_messages")
                .select("role, content, created_at")
                .eq("session_id", session["id"])
                .order("sequence_number")
                .execute()
            )

            sessions.append({
                "id": session["id"],
                "started_at": session["started_at"],
                "messages": messages_result.data or [],
            })

        return sessions

    except Exception as e:
        logger.warning(f"[ANALYSIS] Failed to get sessions for {user_id}: {e}")
        return []


async def get_user_deliverables(
    client,
    user_id: str,
) -> list[dict]:
    """
    Get existing deliverables for duplicate detection.

    Args:
        client: Supabase client
        user_id: User UUID

    Returns:
        List of existing deliverables
    """
    try:
        result = (
            client.table("deliverables")
            .select("id, title, deliverable_type, sources, status")
            .eq("user_id", user_id)
            .in_("status", ["active", "paused"])
            .execute()
        )
        return result.data or []

    except Exception as e:
        logger.warning(f"[ANALYSIS] Failed to get deliverables for {user_id}: {e}")
        return []


async def get_user_knowledge(
    client,
    user_id: str,
) -> list[dict]:
    """
    Get user knowledge entries for context.

    Args:
        client: Supabase client
        user_id: User UUID

    Returns:
        List of knowledge entries
    """
    try:
        result = (
            client.table("knowledge_entries")
            .select("content, tags, entry_type")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("importance", desc=True)
            .limit(20)
            .execute()
        )
        return result.data or []

    except Exception as e:
        logger.warning(f"[ANALYSIS] Failed to get knowledge for {user_id}: {e}")
        return []


def _format_sessions_for_analysis(sessions: list[dict]) -> str:
    """Format sessions as text for LLM analysis."""
    parts = []

    for session in sessions:
        session_id = session["id"][:8]  # Short ID for reference
        date = session.get("started_at", "unknown")[:10]

        messages = session.get("messages", [])
        if not messages:
            continue

        # Format conversation
        conv_lines = [f"[Session {session_id} - {date}]"]
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:500]  # Truncate long messages
            if role == "user":
                conv_lines.append(f"User: {content}")
            elif role == "assistant":
                conv_lines.append(f"Assistant: {content[:200]}...")  # Shorter for assistant

        parts.append("\n".join(conv_lines))

    return "\n\n---\n\n".join(parts)


def _format_existing_deliverables(deliverables: list[dict]) -> str:
    """Format existing deliverables for duplicate detection."""
    if not deliverables:
        return "None"

    lines = []
    for d in deliverables:
        lines.append(f"- {d['title']} ({d['deliverable_type']})")

    return "\n".join(lines)


async def analyze_conversation_patterns(
    client,
    user_id: str,
    sessions: list[dict],
    existing_deliverables: list[dict],
    user_knowledge: list[dict],
) -> list[AnalystSuggestion]:
    """
    Analyze recent conversations for recurring patterns.

    Args:
        client: Supabase client
        user_id: User UUID
        sessions: Recent chat sessions with messages
        existing_deliverables: Current user deliverables (avoid duplicates)
        user_knowledge: Knowledge entries for context

    Returns:
        List of suggestions with confidence scores
    """
    if not sessions:
        logger.info(f"[ANALYSIS] No sessions to analyze for user {user_id}")
        return []

    # Count total messages
    total_messages = sum(len(s.get("messages", [])) for s in sessions)
    if total_messages < 5:
        logger.info(f"[ANALYSIS] Too few messages ({total_messages}) for user {user_id}")
        return []

    # Format inputs
    sessions_text = _format_sessions_for_analysis(sessions)
    existing_text = _format_existing_deliverables(existing_deliverables)

    # Build analysis prompt
    user_prompt = f"""Analyze these conversations for recurring work patterns:

## Recent Conversations (last 7 days)
{sessions_text}

## Existing Deliverables (avoid duplicates)
{existing_text}

Identify patterns that could become automated deliverables.
Return JSON array of suggestions with confidence >= 0.40.
Return empty array [] if no clear patterns found.
"""

    try:
        anthropic_client = get_anthropic_client()

        response = await anthropic_client.messages.create(
            model=ANALYSIS_MODEL,
            max_tokens=2000,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract text response
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text += block.text

        # Parse JSON
        response_text = response_text.strip()
        if response_text.startswith("```"):
            # Remove markdown code blocks
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        suggestions_data = json.loads(response_text)

        # Convert to AnalystSuggestion objects
        suggestions = []
        session_ids = [s["id"] for s in sessions[:10]]  # Reference first 10 sessions

        for item in suggestions_data:
            confidence = item.get("confidence", 0)
            if confidence < 0.40:
                continue

            # Validate deliverable_type
            d_type = item.get("deliverable_type", "custom")
            if d_type not in SUGGESTABLE_TYPES and d_type != "custom":
                d_type = "custom"

            suggestions.append(AnalystSuggestion(
                confidence=confidence,
                deliverable_type=d_type,
                title=item.get("title", "Untitled"),
                description=item.get("description", ""),
                suggested_frequency=item.get("suggested_frequency", "weekly"),
                suggested_sources=item.get("suggested_sources", []),
                detection_reason=item.get("detection_reason", ""),
                source_sessions=session_ids,
            ))

        logger.info(
            f"[ANALYSIS] User {user_id}: analyzed {len(sessions)} sessions, "
            f"found {len(suggestions)} suggestions"
        )

        return suggestions

    except json.JSONDecodeError as e:
        logger.warning(f"[ANALYSIS] Failed to parse response for {user_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"[ANALYSIS] Analysis failed for {user_id}: {e}", exc_info=True)
        return []


def _is_duplicate(
    suggestion: AnalystSuggestion,
    existing_deliverables: list[dict],
) -> bool:
    """
    Check if a suggestion duplicates an existing deliverable.

    Matches on deliverable_type + similar sources.
    """
    for existing in existing_deliverables:
        if existing.get("deliverable_type") != suggestion.deliverable_type:
            continue

        # Same type - check if sources overlap
        existing_sources = existing.get("sources", [])
        if not existing_sources and not suggestion.suggested_sources:
            # Both have no sources - likely duplicate
            return True

        # Check for source overlap (simplified)
        for es in existing_sources:
            for ss in suggestion.suggested_sources:
                if es.get("provider") == ss.get("type"):
                    # Same provider type - likely duplicate
                    return True

    return False


async def create_suggested_deliverable(
    client,
    user_id: str,
    suggestion: AnalystSuggestion,
) -> Optional[str]:
    """
    Create a deliverable with status='suggested' and analyst_metadata.

    Args:
        client: Supabase client
        user_id: User UUID
        suggestion: Analyst suggestion

    Returns:
        Deliverable ID if created, None if duplicate or error
    """
    # Get existing deliverables for duplicate check
    existing = await get_user_deliverables(client, user_id)

    if _is_duplicate(suggestion, existing):
        logger.info(
            f"[ANALYSIS] Skipping duplicate: {suggestion.title} ({suggestion.deliverable_type})"
        )
        return None

    deliverable_id = str(uuid4())
    version_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Build type_classification from suggestable type config
    type_config = SUGGESTABLE_TYPES.get(suggestion.deliverable_type, {})
    type_classification = {
        "binding": type_config.get("binding", "cross_platform"),
        "temporal_pattern": "scheduled",
        "freshness_requirement_hours": 4,
    }
    if "primary_platform" in type_config:
        type_classification["primary_platform"] = type_config["primary_platform"]

    # Build schedule from frequency
    schedule = {
        "frequency": suggestion.suggested_frequency,
        "time": "09:00",
        "timezone": "UTC",
    }
    if suggestion.suggested_frequency == "weekly":
        schedule["day"] = "monday"

    try:
        # Create deliverable
        deliverable_data = {
            "id": deliverable_id,
            "user_id": user_id,
            "title": suggestion.title,
            "description": suggestion.description,
            "deliverable_type": suggestion.deliverable_type,
            "type_classification": type_classification,
            "schedule": schedule,
            "sources": suggestion.suggested_sources,
            "status": "paused",  # Suggested deliverables start paused
            "created_at": now,
            "updated_at": now,
        }

        client.table("deliverables").insert(deliverable_data).execute()

        # Create initial version with 'suggested' status and analyst_metadata
        version_data = {
            "id": version_id,
            "deliverable_id": deliverable_id,
            "version_number": 1,
            "status": "suggested",
            "analyst_metadata": {
                "confidence": suggestion.confidence,
                "detected_pattern": suggestion.deliverable_type,
                "source_sessions": suggestion.source_sessions,
                "detection_reason": suggestion.detection_reason,
            },
            "created_at": now,
        }

        client.table("deliverable_versions").insert(version_data).execute()

        logger.info(
            f"[ANALYSIS] Created suggestion: {suggestion.title} "
            f"(confidence={suggestion.confidence:.2f})"
        )

        return deliverable_id

    except Exception as e:
        logger.error(f"[ANALYSIS] Failed to create suggestion: {e}", exc_info=True)
        return None


async def run_analysis_for_user(
    client,
    user_id: str,
) -> int:
    """
    Run full analysis pipeline for a single user.

    Args:
        client: Supabase client
        user_id: User UUID

    Returns:
        Number of suggestions created
    """
    # Gather inputs
    sessions = await get_recent_sessions(client, user_id, days=7)
    if len(sessions) < 2:
        return 0

    existing = await get_user_deliverables(client, user_id)
    knowledge = await get_user_knowledge(client, user_id)

    # Analyze
    suggestions = await analyze_conversation_patterns(
        client, user_id, sessions, existing, knowledge
    )

    # Create suggestions that meet threshold
    created = 0
    for suggestion in suggestions:
        if suggestion.confidence >= 0.50:
            result = await create_suggested_deliverable(client, user_id, suggestion)
            if result:
                created += 1

    return created
