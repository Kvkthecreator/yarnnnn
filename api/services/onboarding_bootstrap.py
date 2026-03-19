"""
Onboarding Bootstrap — ADR-110, rewritten ADR-122

Deterministic project scaffolding on platform connection.
No LLM involved. Registry lookup, not intelligence.

Trigger: platform sync completion (called from platform_worker.py)
Action: Scaffold matching platform project if conditions met

ADR-122 rewrites the bootstrap path to create projects (not standalone agents)
via the unified scaffold_project() function from project_registry.py.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def maybe_bootstrap_project(
    client: Any,
    user_id: str,
    platform: str,
) -> Optional[str]:
    """
    Check conditions and scaffold a platform digest project if appropriate.

    Called after a successful platform sync in platform_worker.py.

    Returns project_slug if created, None if skipped.

    Conditions checked:
    1. Platform has a project type in the registry (calendar excluded)
    2. No existing project of this type for this user (uniqueness via type_key)
    3. User is under their tier agent limit
    4. Platform has at least one synced source with content
    """
    from services.project_registry import (
        get_platform_project_type, scaffold_project, _has_synced_content,
    )

    type_info = get_platform_project_type(platform)
    if not type_info:
        logger.info(f"[BOOTSTRAP] No project type for {platform}, skipping")
        return None

    type_key, ptype = type_info

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

    # Scaffold project (uniqueness check is inside scaffold_project)
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
    agents = result.get("agents_created", [])
    logger.info(
        f"[BOOTSTRAP] Scaffolded {type_key} project ({project_slug}) "
        f"with {len(agents)} agent(s) for user {user_id}"
    )

    return project_slug
