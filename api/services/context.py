"""
Context Builder for TP Session Start (ADR-038)

Builds the context object injected into the TP system prompt at session start.
This is YARNNN's equivalent of Claude Code reading CLAUDE.md + scanning project structure.

The context gives TP immediate awareness of:
- Who the user is (profile, preferences, timezone)
- What they're working on (active deliverables)
- What's connected (platforms + sync status + freshness)
- Recent conversation history (session summaries)

This eliminates the need for runtime memory searches in ~90% of interactions.

Usage:
    context = await build_session_context(user_id, supabase_client)
    system_prompt = TP_PROMPT_TEMPLATE.format(context=json.dumps(context, indent=2))
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# --- Configuration ---

MAX_DELIVERABLES = 5        # Truncate to most recent if more
MAX_PLATFORMS = 5           # Unlikely to exceed, but cap it
MAX_RECENT_SESSIONS = 3     # Session summaries to include
MAX_USER_FACTS = 10         # User-stated facts from memory
SESSION_LOOKBACK_DAYS = 7   # Only include sessions from last N days
CONTEXT_TOKEN_BUDGET = 2000 # Approximate target


async def build_session_context(user_id: str, client: Any) -> dict:
    """
    Build the context object for TP system prompt injection.

    Args:
        user_id: The authenticated user's ID
        client: Supabase client instance

    Returns:
        Dict structured for JSON serialization into the prompt.
        Designed to stay under ~2,000 tokens.
    """
    context = {
        "user_profile": await _get_user_profile(user_id, client),
        "user_facts": await _get_user_facts(user_id, client),
        "active_deliverables": await _get_active_deliverables(user_id, client),
        "connected_platforms": await _get_connected_platforms(user_id, client),
        "recent_sessions": await _get_recent_sessions(user_id, client),
    }

    return context


async def _get_user_profile(user_id: str, client: Any) -> dict:
    """
    Fetch user profile for context injection.

    Equivalent to: the "author" section of CLAUDE.md

    Sources:
    - auth.users table (email)
    - user_memories with source_type='preference' (for learned preferences)
    """
    profile = {
        "name": None,
        "role": None,
        "preferences": {},
        "timezone": None,
    }

    try:
        # Get basic user info
        # Note: auth.users requires service role or specific RLS
        # For now, we'll get what we can from memories

        # Look for preference-type memories that encode user facts
        result = client.table("user_memories").select(
            "content, tags"
        ).eq(
            "user_id", user_id
        ).eq(
            "source_type", "preference"
        ).eq(
            "is_active", True
        ).limit(10).execute()

        if result.data:
            # Extract preferences from memory content
            for mem in result.data:
                content = mem.get("content", "")
                tags = mem.get("tags", [])

                # Simple heuristics to populate profile
                if "timezone" in tags or "timezone" in content.lower():
                    profile["preferences"]["timezone_note"] = content
                elif "role" in tags:
                    profile["role"] = content
                elif "name" in tags:
                    profile["name"] = content
                else:
                    # General preference
                    profile["preferences"][f"pref_{len(profile['preferences'])}"] = content

    except Exception:
        # Profile is best-effort; don't fail session start
        pass

    return profile


async def _get_user_facts(user_id: str, client: Any) -> list:
    """
    Fetch user-stated facts from memory for context injection.

    This is the narrow, justified use of the memory table (ADR-038).
    Only loads facts from source_type='user_stated' or 'chat' — things
    the user explicitly said that have no source file equivalent.

    Examples:
    - "Presenting to board next month"
    - "Prefers bullet-point format"
    - "Working on Q2 planning"

    These are NOT searched at runtime — they're preloaded here.
    """
    facts = []

    try:
        # Get recent user-stated facts
        # source_type IN ('user_stated', 'chat', 'conversation')
        result = client.table("user_memories").select(
            "content, created_at"
        ).eq(
            "user_id", user_id
        ).in_(
            "source_type", ["user_stated", "chat", "conversation"]
        ).eq(
            "is_active", True
        ).order(
            "created_at", desc=True
        ).limit(MAX_USER_FACTS).execute()

        if result.data:
            for mem in result.data:
                content = mem.get("content", "").strip()
                if content:
                    # Just the fact, no metadata needed
                    facts.append(content)

    except Exception:
        # Facts are best-effort
        pass

    return facts


async def _get_active_deliverables(user_id: str, client: Any) -> list:
    """
    Fetch active deliverables summary for context injection.

    Equivalent to: ls src/ — what build targets exist

    Returns condensed list: title, frequency, recipient, status.
    Capped at MAX_DELIVERABLES, ordered by updated_at desc.
    """
    deliverables = []
    total_count = 0

    try:
        # Get count first
        count_result = client.table("deliverables").select(
            "id", count="exact"
        ).eq(
            "user_id", user_id
        ).eq(
            "status", "active"
        ).execute()

        total_count = count_result.count or 0

        # Get details for display
        result = client.table("deliverables").select(
            "id, title, status, schedule, recipient_context, next_run_at, updated_at"
        ).eq(
            "user_id", user_id
        ).eq(
            "status", "active"
        ).order(
            "updated_at", desc=True
        ).limit(MAX_DELIVERABLES).execute()

        if result.data:
            for d in result.data:
                schedule = d.get("schedule", {}) or {}
                recipient = d.get("recipient_context", {}) or {}

                deliverables.append({
                    "id": d["id"],
                    "title": d.get("title", "Untitled"),
                    "frequency": schedule.get("frequency", "unknown"),
                    "recipient": recipient.get("name", "unspecified"),
                    "next_run": d.get("next_run_at"),
                })

        # Add overflow note if truncated
        if total_count > MAX_DELIVERABLES:
            deliverables.append({
                "_note": f"... and {total_count - MAX_DELIVERABLES} more active deliverables"
            })

    except Exception:
        # Deliverables are best-effort
        pass

    return deliverables


async def _get_connected_platforms(user_id: str, client: Any) -> list:
    """
    Fetch connected platform summary for context injection.

    Equivalent to: what source directories are mounted

    Returns: provider, status, last_synced (with freshness indicator).
    """
    platforms = []

    try:
        result = client.table("user_integrations").select(
            "id, provider, status, last_synced_at, settings"
        ).eq(
            "user_id", user_id
        ).order("provider").limit(MAX_PLATFORMS).execute()

        if result.data:
            now = datetime.now(timezone.utc)

            for p in result.data:
                last_synced = p.get("last_synced_at")
                freshness = _calculate_freshness(last_synced, now)

                platforms.append({
                    "provider": p.get("provider", "unknown"),
                    "status": p.get("status", "unknown"),
                    "last_synced": last_synced,
                    "freshness": freshness,
                })

    except Exception:
        # Platforms are best-effort
        pass

    return platforms


def _calculate_freshness(last_synced: Optional[str], now: datetime) -> str:
    """Calculate human-readable freshness indicator."""
    if not last_synced:
        return "never synced"

    try:
        synced_dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00"))
        delta = now - synced_dt

        if delta < timedelta(hours=1):
            return "fresh"
        elif delta < timedelta(hours=24):
            return f"{int(delta.total_seconds() // 3600)} hours ago"
        elif delta < timedelta(days=7):
            return f"{delta.days} days ago"
        else:
            return f"stale ({delta.days} days)"
    except Exception:
        return "unknown"


async def _get_recent_sessions(user_id: str, client: Any) -> list:
    """
    Fetch recent session summaries for context injection.

    Equivalent to: recent shell history — what did we discuss recently?

    Returns last N session summaries (not full message history).
    Only includes sessions from last 7 days with non-empty summaries.
    """
    sessions = []

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=SESSION_LOOKBACK_DAYS)).isoformat()

        result = client.table("chat_sessions").select(
            "id, created_at, summary"
        ).eq(
            "user_id", user_id
        ).not_.is_(
            "summary", "null"
        ).gte(
            "created_at", cutoff
        ).order(
            "created_at", desc=True
        ).limit(MAX_RECENT_SESSIONS).execute()

        if result.data:
            for s in result.data:
                summary = s.get("summary", "")
                if summary:
                    sessions.append({
                        "date": s.get("created_at", "")[:10],  # Just the date
                        "summary": summary[:300],  # Truncate long summaries
                    })

    except Exception:
        # Sessions are best-effort
        pass

    return sessions


# --- Utilities ---

def estimate_context_tokens(context: dict) -> int:
    """
    Rough token count estimation for context injection.
    Rule of thumb: 1 token ≈ 4 characters for JSON.
    """
    json_str = json.dumps(context, indent=2)
    return len(json_str) // 4


def format_context_for_prompt(context: dict) -> str:
    """
    Format context dict as a readable string for prompt injection.
    """
    lines = ["## Your Context\n"]

    # User profile
    profile = context.get("user_profile", {})
    if profile.get("name") or profile.get("role"):
        lines.append(f"**User:** {profile.get('name', 'Unknown')} ({profile.get('role', 'no role specified')})")

    # User facts (from memory - user-stated things with no source file)
    facts = context.get("user_facts", [])
    if facts:
        lines.append(f"\n**User Facts:**")
        for fact in facts:
            lines.append(f"  - {fact}")

    # Active deliverables
    deliverables = context.get("active_deliverables", [])
    if deliverables:
        lines.append(f"\n**Active Deliverables:** {len([d for d in deliverables if 'id' in d])}")
        for d in deliverables:
            if "_note" in d:
                lines.append(f"  {d['_note']}")
            else:
                lines.append(f"  - {d.get('title')} ({d.get('frequency')}) → {d.get('recipient')}")

    # Connected platforms
    platforms = context.get("connected_platforms", [])
    if platforms:
        lines.append(f"\n**Connected Platforms:**")
        for p in platforms:
            lines.append(f"  - {p.get('provider')}: {p.get('status')} ({p.get('freshness')})")

    # Recent sessions
    sessions = context.get("recent_sessions", [])
    if sessions:
        lines.append(f"\n**Recent Sessions:**")
        for s in sessions:
            lines.append(f"  - {s.get('date')}: {s.get('summary')}")

    return "\n".join(lines)
