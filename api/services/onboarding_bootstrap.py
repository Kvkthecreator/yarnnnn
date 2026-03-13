"""
Onboarding Bootstrap — ADR-110

Deterministic agent auto-creation on platform connection.
No LLM involved. Lookup table, not intelligence.

Trigger: platform sync completion (called from platform_worker.py)
Action: Create matching digest agent if conditions met

Template mapping:
  Slack → Slack Recap (platform/digest/recurring)
  Gmail → Gmail Digest (platform/digest/recurring)
  Notion → Notion Summary (platform/digest/recurring)
  Calendar → (none — low standalone value, deferred to Composer)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Deterministic template mapping: platform → agent config
BOOTSTRAP_TEMPLATES = {
    "slack": {
        "title": "Slack Recap",
        "skill": "digest",
        "frequency": "daily",
    },
    "gmail": {
        "title": "Gmail Digest",
        "skill": "digest",
        "frequency": "daily",
    },
    "notion": {
        "title": "Notion Summary",
        "skill": "digest",
        "frequency": "daily",
    },
    # Calendar excluded — Meeting Prep requires cross-platform context (ADR-110)
}


async def maybe_bootstrap_agent(
    client: Any,
    user_id: str,
    platform: str,
) -> Optional[str]:
    """
    Check conditions and create a bootstrap digest agent if appropriate.

    Called after a successful platform sync in platform_worker.py.

    Returns agent_id if created, None if skipped.

    Conditions checked:
    1. Platform has a bootstrap template (calendar excluded)
    2. No existing digest agent for this platform already exists
    3. User is under their tier agent limit
    4. Platform has at least one synced source with content
    """
    template = BOOTSTRAP_TEMPLATES.get(platform)
    if not template:
        logger.info(f"[BOOTSTRAP] No template for {platform}, skipping")
        return None

    # Check: existing digest agent for this platform?
    if await _has_existing_digest(client, user_id, platform):
        logger.info(f"[BOOTSTRAP] Digest agent already exists for {platform}, skipping")
        return None

    # Check: under tier agent limit?
    from services.platform_limits import check_agent_limit
    allowed, message = check_agent_limit(client, user_id)
    if not allowed:
        logger.info(f"[BOOTSTRAP] Agent limit reached for user {user_id}: {message}")
        return None

    # Check: platform has synced content?
    if not await _has_synced_content(client, user_id, platform):
        logger.info(f"[BOOTSTRAP] No synced content for {platform}, skipping")
        return None

    # Get synced sources for this platform
    sources = await _get_synced_sources(client, user_id, platform)

    # Create the agent via shared creation path
    from services.agent_creation import create_agent_record

    result = await create_agent_record(
        client=client,
        user_id=user_id,
        title=template["title"],
        skill=template["skill"],
        origin="system_bootstrap",
        frequency=template["frequency"],
        sources=sources,
        execute_now=True,  # Immediate first run
    )

    if not result.get("success"):
        logger.warning(f"[BOOTSTRAP] Agent creation failed for {platform}: {result.get('message')}")
        return None

    agent_id = result["agent_id"]
    logger.info(f"[BOOTSTRAP] Created {template['title']} ({agent_id}) for user {user_id}")

    # Activity log
    try:
        from services.activity_log import write_activity
        await write_activity(
            client=client,
            user_id=user_id,
            event_type="agent_bootstrapped",
            summary=f"Auto-created {template['title']} from {platform} connection",
            event_ref=agent_id,
            metadata={
                "platform": platform,
                "origin": "system_bootstrap",
                "skill": template["skill"],
            },
        )
    except Exception:
        pass  # Non-fatal

    return agent_id


async def _has_existing_digest(client: Any, user_id: str, platform: str) -> bool:
    """Check if a digest agent already exists for this platform.

    Two checks:
    1. Bootstrap-created agent with matching title (e.g. "Slack Recap")
    2. Any digest agent whose sources reference this platform
    """
    template = BOOTSTRAP_TEMPLATES.get(platform)
    if not template:
        return False

    try:
        # Check 1: exact bootstrap title match (most reliable for idempotency)
        title_match = (
            client.table("agents")
            .select("id")
            .eq("user_id", user_id)
            .eq("skill", "digest")
            .eq("title", template["title"])
            .execute()
        )
        if title_match.data:
            return True

        # Check 2: any digest agent with sources referencing this platform
        digest_agents = (
            client.table("agents")
            .select("id, sources")
            .eq("user_id", user_id)
            .eq("skill", "digest")
            .execute()
        )
        for agent in (digest_agents.data or []):
            sources = agent.get("sources", [])
            for source in sources:
                if isinstance(source, dict) and source.get("platform") == platform:
                    return True
                elif isinstance(source, str) and platform in source:
                    return True

        return False
    except Exception as e:
        logger.warning(f"[BOOTSTRAP] Digest check failed: {e}")
        return True  # Err on the side of not creating duplicates


async def _has_synced_content(client: Any, user_id: str, platform: str) -> bool:
    """Check if platform has at least one piece of synced content."""
    try:
        result = (
            client.table("platform_content")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        logger.warning(f"[BOOTSTRAP] Content check failed: {e}")
        return False


async def _get_synced_sources(client: Any, user_id: str, platform: str) -> list:
    """Get the user's selected sources for this platform."""
    try:
        result = (
            client.table("platform_connections")
            .select("selected_sources")
            .eq("user_id", user_id)
            .eq("platform", platform)
            .single()
            .execute()
        )
        if result.data and result.data.get("selected_sources"):
            return result.data["selected_sources"]
    except Exception:
        pass
    return []
