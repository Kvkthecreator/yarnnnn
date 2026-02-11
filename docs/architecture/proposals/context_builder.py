"""
Context Builder for TP Session Start

This module builds the context object injected into the TP system prompt
at the start of every session. It's YARNNN's equivalent of Claude Code
reading CLAUDE.md + scanning project structure.

The context gives TP immediate awareness of:
- Who the user is (profile, preferences, timezone)
- What they're working on (active deliverables)
- What's connected (platforms + sync status)
- Recent conversation history (session summaries)

This eliminates the need for runtime memory searches in ~90% of interactions.

Usage:
    context = await build_session_context(user_id)
    system_prompt = TP_PROMPT_TEMPLATE.format(context=json.dumps(context, indent=2))
"""

import json
from datetime import datetime, timedelta
from typing import Optional

# --- Configuration ---

MAX_DELIVERABLES = 5        # Truncate to most recent if more
MAX_PLATFORMS = 5            # Unlikely to exceed, but cap it
MAX_RECENT_SESSIONS = 3     # Session summaries to include
CONTEXT_TOKEN_BUDGET = 2000  # Approximate target


async def build_session_context(user_id: str, supabase_client=None) -> dict:
    """
    Build the context object for TP system prompt injection.
    
    Returns a dict structured for JSON serialization into the prompt.
    Designed to stay under ~2,000 tokens.
    """
    context = {
        "user_profile": await _get_user_profile(user_id, supabase_client),
        "active_deliverables": await _get_active_deliverables(user_id, supabase_client),
        "connected_platforms": await _get_connected_platforms(user_id, supabase_client),
        "recent_sessions": await _get_recent_sessions(user_id, supabase_client),
    }
    
    return context


async def _get_user_profile(user_id: str, supabase) -> dict:
    """
    Fetch user profile for context injection.
    
    Equivalent to: the "author" section of CLAUDE.md
    
    Sources:
    - users table (name, email)
    - user_preferences table or JSONB column (role, preferences, timezone)
    
    TODO: Wire to actual user/preferences tables
    """
    # Scaffold — replace with actual DB query
    # result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    
    return {
        "name": None,           # From users table
        "role": None,           # From preferences
        "preferences": {},      # Tone, defaults, etc.
        "timezone": None,       # For scheduling context
    }


async def _get_active_deliverables(user_id: str, supabase) -> list:
    """
    Fetch active deliverables summary for context injection.
    
    Equivalent to: ls src/ — what build targets exist
    
    Returns condensed list: title, frequency, recipient, last generated.
    Capped at MAX_DELIVERABLES, ordered by updated_at desc.
    If more exist, includes a count note.
    
    TODO: Wire to deliverables table
    """
    # Scaffold — replace with actual DB query
    # result = (supabase.table("deliverables")
    #     .select("id, title, status, schedule, recipient_context, updated_at")
    #     .eq("user_id", user_id)
    #     .eq("status", "active")
    #     .order("updated_at", desc=True)
    #     .limit(MAX_DELIVERABLES)
    #     .execute())
    
    # Transform to context-friendly format:
    # deliverables = []
    # for d in result.data:
    #     deliverables.append({
    #         "id": d["id"],
    #         "title": d["title"],
    #         "frequency": d.get("schedule", {}).get("frequency", "unknown"),
    #         "recipient": d.get("recipient_context", {}).get("name", "unspecified"),
    #         "last_generated": None,  # From work_tickets join
    #     })
    
    return []


async def _get_connected_platforms(user_id: str, supabase) -> list:
    """
    Fetch connected platform summary for context injection.
    
    Equivalent to: what source directories are mounted
    
    Returns: provider, status, last_synced, brief summary.
    
    TODO: Wire to user_integrations table
    """
    # Scaffold — replace with actual DB query
    # result = (supabase.table("user_integrations")
    #     .select("id, provider, status, last_synced_at, sync_summary")
    #     .eq("user_id", user_id)
    #     .order("provider")
    #     .limit(MAX_PLATFORMS)
    #     .execute())
    
    # Transform:
    # platforms = []
    # for p in result.data:
    #     platforms.append({
    #         "provider": p["provider"],
    #         "status": p["status"],
    #         "last_synced": p.get("last_synced_at"),
    #         "summary": p.get("sync_summary", {}).get("brief", ""),
    #     })
    
    return []


async def _get_recent_sessions(user_id: str, supabase) -> list:
    """
    Fetch recent session summaries for context injection.
    
    Equivalent to: recent shell history — what did we discuss recently?
    
    Returns last N session summaries (not full message history).
    Only includes sessions from last 7 days with non-empty summaries.
    
    TODO: Wire to chat_sessions table
    """
    # Scaffold — replace with actual DB query
    # cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    # result = (supabase.table("chat_sessions")
    #     .select("id, created_at, summary")
    #     .eq("user_id", user_id)
    #     .not_.is_("summary", "null")
    #     .gte("created_at", cutoff)
    #     .order("created_at", desc=True)
    #     .limit(MAX_RECENT_SESSIONS)
    #     .execute())
    
    # Transform:
    # sessions = []
    # for s in result.data:
    #     sessions.append({
    #         "date": s["created_at"][:10],  # Just the date
    #         "summary": s["summary"][:200],  # Truncate long summaries
    #     })
    
    return []


# --- Context Size Estimation ---

def estimate_context_tokens(context: dict) -> int:
    """
    Rough token count estimation for context injection.
    Rule of thumb: 1 token ≈ 4 characters for JSON.
    """
    json_str = json.dumps(context, indent=2)
    return len(json_str) // 4


# --- Integration Point ---

# In api/agents/thinking_partner.py:
#
# from services.context import build_session_context
#
# async def create_session(user_id: str):
#     context = await build_session_context(user_id, supabase_client)
#     system_prompt = TP_PROMPT_V5.format(context=json.dumps(context, indent=2))
#     # ... initialize Claude with system_prompt
