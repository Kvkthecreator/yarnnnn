"""
Working Memory Builder - ADR-058 Knowledge Base Architecture

Builds the working memory injected into the TP system prompt at session start.
This is YARNNN's equivalent of Claude Code reading CLAUDE.md + scanning project structure.

ADR-058 Terminology:
- Working Memory: What TP has in prompt for current request
- Knowledge: User profile, styles, domains, entries (inferred from filesystem)
- Filesystem: Raw synced data (platform content + documents)

The working memory gives TP immediate awareness of:
- WHO: User profile (name, role, timezone, company)
- HOW: User styles per platform (tone, verbosity, patterns)
- WHAT: Active domains and their sources
- KNOWN: Knowledge entries (facts, preferences, decisions)
- WORK: Active deliverables
- STATUS: Connected platforms + sync freshness
- HISTORY: Recent session summaries

This eliminates the need for runtime searches in ~90% of interactions.

Usage:
    working_memory = await build_working_memory(user_id, supabase_client)
    system_prompt = TP_PROMPT_TEMPLATE.format(working_memory=format_for_prompt(working_memory))
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# --- Configuration ---

MAX_DELIVERABLES = 5        # Truncate to most recent if more
MAX_PLATFORMS = 5           # Unlikely to exceed, but cap it
MAX_RECENT_SESSIONS = 3     # Session summaries to include
MAX_KNOWLEDGE_ENTRIES = 15  # Knowledge entries to include
MAX_STYLES = 3              # Platform styles to include
SESSION_LOOKBACK_DAYS = 7   # Only include sessions from last N days
WORKING_MEMORY_TOKEN_BUDGET = 2500  # Approximate target


async def build_working_memory(user_id: str, client: Any) -> dict:
    """
    Build the working memory object for TP system prompt injection.

    Args:
        user_id: The authenticated user's ID
        client: Supabase client instance

    Returns:
        Dict structured for JSON serialization into the prompt.
        Designed to stay under ~2,500 tokens.
    """
    working_memory = {
        "profile": await _get_knowledge_profile(user_id, client),
        "styles": await _get_knowledge_styles(user_id, client),
        "domains": await _get_knowledge_domains(user_id, client),
        "entries": await _get_knowledge_entries(user_id, client),
        "deliverables": await _get_active_deliverables(user_id, client),
        "platforms": await _get_connected_platforms(user_id, client),
        "recent_sessions": await _get_recent_sessions(user_id, client),
    }

    return working_memory


async def _get_knowledge_profile(user_id: str, client: Any) -> dict:
    """
    Fetch user's knowledge profile.

    ADR-058: Profile contains who the user is - name, role, company, timezone.
    Uses stated_* fields if set (user override), otherwise inferred_* fields.
    """
    profile = {
        "name": None,
        "role": None,
        "company": None,
        "timezone": None,
    }

    try:
        result = client.table("knowledge_profile").select(
            "stated_name, inferred_name, "
            "stated_role, inferred_role, "
            "stated_company, inferred_company, "
            "stated_timezone, inferred_timezone"
        ).eq("user_id", user_id).single().execute()

        if result.data:
            row = result.data
            # Stated values take precedence (user overrides)
            profile["name"] = row.get("stated_name") or row.get("inferred_name")
            profile["role"] = row.get("stated_role") or row.get("inferred_role")
            profile["company"] = row.get("stated_company") or row.get("inferred_company")
            profile["timezone"] = row.get("stated_timezone") or row.get("inferred_timezone")

    except Exception:
        # Profile is best-effort; don't fail session start
        pass

    return profile


async def _get_knowledge_styles(user_id: str, client: Any) -> list:
    """
    Fetch user's writing styles per platform.

    ADR-058: Styles are inferred from user-authored content in filesystem_items.
    Includes tone, verbosity, formatting patterns, and sample excerpts.
    """
    styles = []

    try:
        result = client.table("knowledge_styles").select(
            "platform, tone, verbosity, formatting, sample_excerpts"
        ).eq(
            "user_id", user_id
        ).limit(MAX_STYLES).execute()

        if result.data:
            for row in result.data:
                styles.append({
                    "platform": row.get("platform"),
                    "tone": row.get("tone"),
                    "verbosity": row.get("verbosity"),
                    "formatting": row.get("formatting"),
                    "samples": row.get("sample_excerpts", [])[:2],  # Just 2 samples
                })

    except Exception:
        # Styles are best-effort
        pass

    return styles


async def _get_knowledge_domains(user_id: str, client: Any) -> list:
    """
    Fetch user's knowledge domains.

    ADR-058: Domains are work contexts that group sources and entries.
    """
    domains = []

    try:
        result = client.table("knowledge_domains").select(
            "id, name, summary, sources, is_default"
        ).eq(
            "user_id", user_id
        ).eq(
            "is_active", True
        ).order(
            "is_default", desc=True  # Default domain first
        ).execute()

        if result.data:
            for row in result.data:
                sources = row.get("sources", [])
                domains.append({
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "summary": row.get("summary"),
                    "source_count": len(sources) if sources else 0,
                    "is_default": row.get("is_default", False),
                })

    except Exception:
        # Domains are best-effort
        pass

    return domains


async def _get_knowledge_entries(user_id: str, client: Any) -> list:
    """
    Fetch user's knowledge entries (facts, preferences, decisions).

    ADR-058: Entries are explicit knowledge - things the user stated,
    preferences inferred from conversations, decisions made.
    """
    entries = []

    try:
        result = client.table("knowledge_entries").select(
            "content, entry_type, source, importance, tags"
        ).eq(
            "user_id", user_id
        ).eq(
            "is_active", True
        ).order(
            "importance", desc=True
        ).order(
            "created_at", desc=True
        ).limit(MAX_KNOWLEDGE_ENTRIES).execute()

        if result.data:
            for row in result.data:
                entries.append({
                    "content": row.get("content"),
                    "type": row.get("entry_type"),
                    "source": row.get("source"),
                    "importance": row.get("importance"),
                })

    except Exception:
        # Entries are best-effort
        pass

    return entries


async def _get_active_deliverables(user_id: str, client: Any) -> list:
    """
    Fetch active deliverables summary for working memory.

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
    Fetch connected platform summary for working memory.

    ADR-058: Uses platform_connections table (was user_integrations).
    """
    platforms = []

    try:
        result = client.table("platform_connections").select(
            "id, platform, status, last_synced_at, settings"
        ).eq(
            "user_id", user_id
        ).order("platform").limit(MAX_PLATFORMS).execute()

        if result.data:
            now = datetime.now(timezone.utc)

            for p in result.data:
                last_synced = p.get("last_synced_at")
                freshness = _calculate_freshness(last_synced, now)

                platforms.append({
                    "platform": p.get("platform", "unknown"),
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
    Fetch recent session summaries for working memory.

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


# --- Formatting ---

def estimate_working_memory_tokens(working_memory: dict) -> int:
    """
    Rough token count estimation for working memory injection.
    Rule of thumb: 1 token ≈ 4 characters for JSON.
    """
    json_str = json.dumps(working_memory, indent=2)
    return len(json_str) // 4


def format_for_prompt(working_memory: dict) -> str:
    """
    Format working memory dict as a readable string for prompt injection.

    This is the actual text that goes into TP's system prompt.
    """
    lines = ["## Working Memory\n"]

    # Profile (WHO)
    profile = working_memory.get("profile", {})
    if any(profile.values()):
        lines.append("### Who You're Talking To")
        if profile.get("name"):
            role_str = f" ({profile.get('role')})" if profile.get("role") else ""
            company_str = f" at {profile.get('company')}" if profile.get("company") else ""
            lines.append(f"**{profile['name']}**{role_str}{company_str}")
        if profile.get("timezone"):
            lines.append(f"Timezone: {profile['timezone']}")

    # Styles (HOW)
    styles = working_memory.get("styles", [])
    if styles:
        lines.append("\n### Their Communication Style")
        for style in styles:
            platform = style.get("platform", "unknown").title()
            tone = style.get("tone", "")
            verbosity = style.get("verbosity", "")
            style_desc = ", ".join(filter(None, [tone, verbosity]))
            if style_desc:
                lines.append(f"- **{platform}**: {style_desc}")

    # Knowledge Entries (KNOWN)
    entries = working_memory.get("entries", [])
    if entries:
        lines.append("\n### What You Know About Them")
        for entry in entries:
            content = entry.get("content", "")
            entry_type = entry.get("type", "fact")
            type_marker = {"preference": "Prefers", "instruction": "Note", "decision": "Decided", "fact": ""}.get(entry_type, "")
            if type_marker:
                lines.append(f"- {type_marker}: {content}")
            else:
                lines.append(f"- {content}")

    # Domains (WHAT)
    domains = working_memory.get("domains", [])
    if domains:
        lines.append("\n### Their Work Domains")
        for domain in domains:
            name = domain.get("name", "Unknown")
            summary = domain.get("summary", "")
            source_count = domain.get("source_count", 0)
            default_marker = " (default)" if domain.get("is_default") else ""
            if summary:
                lines.append(f"- **{name}**{default_marker}: {summary}")
            else:
                lines.append(f"- **{name}**{default_marker} ({source_count} sources)")

    # Deliverables (WORK)
    deliverables = working_memory.get("deliverables", [])
    if deliverables:
        lines.append(f"\n### Active Deliverables")
        for d in deliverables:
            if "_note" in d:
                lines.append(f"  {d['_note']}")
            else:
                lines.append(f"- {d.get('title')} ({d.get('frequency')}) → {d.get('recipient')}")

    # Platforms (STATUS)
    platforms = working_memory.get("platforms", [])
    if platforms:
        lines.append(f"\n### Connected Platforms")
        for p in platforms:
            status = p.get("status", "unknown")
            freshness = p.get("freshness", "unknown")
            if status == "connected":
                lines.append(f"- {p.get('platform')}: {freshness}")
            else:
                lines.append(f"- {p.get('platform')}: {status}")

    # Recent Sessions (HISTORY)
    sessions = working_memory.get("recent_sessions", [])
    if sessions:
        lines.append(f"\n### Recent Conversations")
        for s in sessions:
            lines.append(f"- {s.get('date')}: {s.get('summary')}")

    return "\n".join(lines)


# =============================================================================
# Backwards Compatibility (TEMPORARY - will be removed)
# =============================================================================

# Alias for migration period. Remove after all callers are updated.

async def build_session_context(user_id: str, client: Any) -> dict:
    """DEPRECATED: Use build_working_memory instead."""
    import logging
    logging.getLogger(__name__).warning(
        "build_session_context is deprecated. Use build_working_memory."
    )
    return await build_working_memory(user_id, client)


def format_context_for_prompt(context: dict) -> str:
    """DEPRECATED: Use format_for_prompt instead."""
    import logging
    logging.getLogger(__name__).warning(
        "format_context_for_prompt is deprecated. Use format_for_prompt."
    )
    return format_for_prompt(context)


def estimate_context_tokens(context: dict) -> int:
    """DEPRECATED: Use estimate_working_memory_tokens instead."""
    import logging
    logging.getLogger(__name__).warning(
        "estimate_context_tokens is deprecated. Use estimate_working_memory_tokens."
    )
    return estimate_working_memory_tokens(context)
