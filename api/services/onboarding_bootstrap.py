"""
Onboarding Bootstrap — ADR-110/122/133

Fallback project scaffolding on platform connection (for users who skipped onboarding).
No LLM involved. Creates a workspace project with a briefer agent.

Trigger: platform sync completion (called from platform_worker.py)

ADR-133: Platform-specific project types deleted. Bootstrap creates a
generic workspace project with a briefer agent that reads the connected platform.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def _has_onboarded_projects(client: Any, user_id: str) -> bool:
    """Check if user has any projects (completed onboarding)."""
    try:
        result = (
            client.table("workspace_files")
            .select("path")
            .eq("user_id", user_id)
            .like("path", "/projects/%/PROJECT.md")
            .limit(1)
            .execute()
        )
        return len(result.data or []) > 0
    except Exception:
        return False


async def maybe_bootstrap_project(
    client: Any,
    user_id: str,
    platform: str,
) -> Optional[str]:
    """
    Scaffold a briefer project for a newly connected platform (fallback path).

    Only fires when user has no projects (skipped onboarding) and platform has content.
    Creates a workspace project with a briefer agent reading the connected platform.
    """
    from services.project_registry import scaffold_project, _has_synced_content

    # Skip if user already has projects from onboarding
    if await _has_onboarded_projects(client, user_id):
        logger.info(f"[BOOTSTRAP] User has projects, skipping bootstrap for {platform}")
        return None

    # Check platform has synced content
    if not await _has_synced_content(client, user_id, platform):
        logger.info(f"[BOOTSTRAP] No synced content for {platform}, skipping")
        return None

    from services.platform_limits import check_agent_limit
    allowed, message = check_agent_limit(client, user_id)
    if not allowed:
        logger.info(f"[BOOTSTRAP] Agent limit reached: {message}")
        return None

    # Scaffold workspace project with briefer (platform is perception, not a project type)
    platform_title = platform.capitalize()
    result = await scaffold_project(
        client, user_id,
        type_key="workspace",
        scope_name=f"{platform_title} Updates",
        execute_now=True,
    )

    if not result.get("success"):
        reason = result.get("reason", "unknown")
        if reason == "duplicate":
            logger.info(f"[BOOTSTRAP] Project already exists for {platform}")
        else:
            logger.warning(f"[BOOTSTRAP] Scaffold failed: {result.get('message')}")
        return None

    project_slug = result["project_slug"]
    logger.info(f"[BOOTSTRAP] Scaffolded '{project_slug}' for {platform}")
    return project_slug
