"""
Onboarding Bootstrap — stub (project scaffolding removed).

Previously scaffolded platform digest projects on first sync.
Now a no-op stub — callers retain their try/except wrappers so no breakage.
Will be rewritten in Phase 3 for direct agent creation without projects.
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
    Stub — previously scaffolded a project for a newly connected platform.

    Returns None (no-op). Will be rewritten in Phase 3.
    """
    logger.debug(f"[BOOTSTRAP] Stub — bootstrap disabled (platform={platform})")
    return None
