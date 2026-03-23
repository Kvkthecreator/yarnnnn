"""
Onboarding Bootstrap — ADR-110, rewritten ADR-122, updated ADR-132

Deterministic project scaffolding on platform connection.
No LLM involved. Registry lookup, not intelligence.

Trigger: platform sync completion (called from platform_worker.py)

ADR-132 update: If user has a work index (/memory/WORK.md), skip generic
platform digest creation — the user already has work-scoped projects.
Fallback to platform digest only when no work index exists.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def _has_work_index(client: Any, user_id: str) -> bool:
    """Check if user has a work index (ADR-132 onboarding completed)."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", "/memory/WORK.md")
            .limit(1)
            .execute()
        )
        rows = result.data or []
        return bool(rows and rows[0].get("content", "").strip())
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

    ADR-132: If user has a work index, skip generic platform digest creation.
    The user's work-scoped projects already exist — platform sources will be
    mapped to those projects in a future phase. Creating a generic "Slack Digest"
    alongside work-scoped projects would be redundant.

    Conditions checked:
    1. User does NOT have a work index (ADR-132 — if they do, skip generic digest)
    2. Platform has a project type in the registry
    3. No existing project of this type for this user (uniqueness via type_key)
    4. User is under their tier agent limit
    5. Platform has at least one synced source with content
    """
    from services.project_registry import (
        get_platform_project_type, scaffold_project, _has_synced_content,
    )

    # ADR-132: Skip generic digest if user already has work-scoped projects
    if await _has_work_index(client, user_id):
        logger.info(f"[BOOTSTRAP] User has work index, skipping generic {platform} digest")
        return None

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
    agents = result.get("contributors_created", [])
    logger.info(
        f"[BOOTSTRAP] Scaffolded {type_key} project ({project_slug}) "
        f"with {len(agents)} agent(s) for user {user_id}"
    )

    return project_slug
