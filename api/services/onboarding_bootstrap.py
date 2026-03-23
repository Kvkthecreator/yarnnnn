"""
Onboarding Bootstrap — ADR-110, rewritten ADR-122, updated ADR-132

Deterministic project scaffolding on platform connection.
No LLM involved. Registry lookup, not intelligence.

Trigger: platform sync completion (called from platform_worker.py)

ADR-132: If user completed onboarding (has any projects), skip generic
platform digest. Users who skipped onboarding still get platform digests.
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
    Check conditions and scaffold a platform digest project if appropriate.

    Called after a successful platform sync in platform_worker.py.
    Returns project_slug if created, None if skipped.

    Conditions:
    1. User has NOT completed onboarding (no projects yet)
    2. Platform has a project type in the registry
    3. Uniqueness (1 per platform per user)
    4. Under tier agent limit
    5. Platform has synced content
    """
    from services.project_registry import (
        get_platform_project_type, scaffold_project, _has_synced_content,
    )

    # Skip generic digest if user already has projects from onboarding
    if await _has_onboarded_projects(client, user_id):
        logger.info(f"[BOOTSTRAP] User has projects, skipping generic {platform} digest")
        return None

    type_info = get_platform_project_type(platform)
    if not type_info:
        logger.info(f"[BOOTSTRAP] No project type for {platform}, skipping")
        return None

    type_key, ptype = type_info

    from services.platform_limits import check_agent_limit
    allowed, message = check_agent_limit(client, user_id)
    if not allowed:
        logger.info(f"[BOOTSTRAP] Agent limit reached for user {user_id}: {message}")
        return None

    if not await _has_synced_content(client, user_id, platform):
        logger.info(f"[BOOTSTRAP] No synced content for {platform}, skipping")
        return None

    result = await scaffold_project(
        client, user_id, type_key,
        execute_now=True,
    )

    if not result.get("success"):
        reason = result.get("reason", "unknown")
        if reason == "duplicate":
            logger.info(f"[BOOTSTRAP] Project already exists for {platform}: {result.get('existing_slug')}")
        else:
            logger.warning(f"[BOOTSTRAP] Scaffold failed for {platform}: {result.get('message')}")
        return None

    project_slug = result["project_slug"]
    agents = result.get("contributors_created", [])
    logger.info(
        f"[BOOTSTRAP] Scaffolded {type_key} project ({project_slug}) "
        f"with {len(agents)} agent(s) for user {user_id}"
    )

    return project_slug
