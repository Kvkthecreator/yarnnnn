"""
Agent Creation — Shared logic for all agent creation paths (ADR-111).

Single source of truth for creating agents. Called by:
- ManageAgent primitive (chat + headless, action="create")
- Onboarding bootstrap service (ADR-110)
- POST /agents route (agents.py)

Replaces the duplicated logic that was in:
- primitives/write.py (_process_agent)
- primitives/coordinator.py (handle_create_agent)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Valid values (ADR-109)
# =============================================================================

VALID_SCOPES = {"platform", "cross_platform", "knowledge", "research", "autonomous"}
# ADR-130 v2: Valid roles derived from AGENT_TYPES registry + legacy names for DB compat
from services.agent_framework import AGENT_TYPES, LEGACY_ROLE_MAP
VALID_ROLES = set(AGENT_TYPES.keys()) | set(LEGACY_ROLE_MAP.keys()) | {"act"}

# Fallback scope from role (used when infer_scope can't reason about sources)
ROLE_TO_SCOPE = {
    # v2 types
    "briefer": "platform",
    "monitor": "platform",
    "researcher": "research",
    "drafter": "cross_platform",
    "analyst": "cross_platform",
    "writer": "cross_platform",
    "planner": "platform",
    "scout": "research",
    # ADR-164: TP as meta-cognitive agent — orchestration is autonomous scope
    "thinking_partner": "autonomous",
    # Legacy mappings (DB may still have old values)
    "digest": "platform",
    "prepare": "platform",
    "research": "research",
    "synthesize": "cross_platform",
    "act": "autonomous",
    "custom": "knowledge",
}


def infer_scope(role: str) -> str:
    """
    ADR-109: Auto-infer scope from role.

    Scope is never user-configured — it's derived from the agent's role.
    ADR-138: mode removed from agents (proactive/coordinator modes deleted).
    """
    return ROLE_TO_SCOPE.get(role, "knowledge")

# Columns allowed in agents table INSERT (prevents Supabase 400)
# NOTE: agent_instructions and agent_memory EXCLUDED — deprecated by ADR-106.
# Workspace AGENT.md and memory/*.md are the sole authority for new agents.
# DB columns kept in schema for lazy migration of pre-workspace agents.
AGENT_COLUMNS = {
    "id", "user_id", "title", "slug",
    "status", "created_at", "updated_at",
    "type_config", "origin",
    "agent_instructions", "agent_memory",
    "scope", "role",
    "avatar_url",
}


def _slugify_agent(title: str) -> str:
    """Generate a filesystem-safe slug from agent title."""
    import re
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:50] or "agent"


# =============================================================================
# Core creation function
# =============================================================================

async def create_agent_record(
    client: Any,
    user_id: str,
    title: str,
    role: str = "custom",
    origin: str = "user_configured",
    *,
    agent_instructions: Optional[str] = None,
    type_config: Optional[dict] = None,
    avatar_url: Optional[str] = None,
) -> dict:
    """
    Create an agent record in the database with workspace seeding.

    This is the single creation path for all agent origins:
    - user_configured (TP chat, UI form)
    - coordinator_created (coordinator agents)
    - system_bootstrap (onboarding bootstrap, ADR-110)
    - composer (composer service, ADR-111 future)

    Returns:
        {"success": True, "agent_id": str, "agent": dict, "message": str}
        or {"success": False, "error": str, "message": str}
    """
    if not title or not title.strip():
        return {"success": False, "error": "missing_title", "message": "title is required"}

    # Validate and default role
    if role not in VALID_ROLES:
        role = "custom"

    # Infer scope from role (ADR-138: mode removed from agents)
    scope = infer_scope(role)

    # Resolve instructions
    instructions_text = agent_instructions
    if not instructions_text:
        from services.agent_pipeline import DEFAULT_INSTRUCTIONS
        instructions_text = DEFAULT_INSTRUCTIONS.get(role, DEFAULT_INSTRUCTIONS.get("custom", ""))

    now = datetime.now(timezone.utc)
    entity_id = str(uuid4())

    agent_data = {
        "id": entity_id,
        "user_id": user_id,
        "title": title.strip(),
        "slug": _slugify_agent(title.strip()),
        "role": role,
        "scope": scope,
        "origin": origin,
        "status": "active",
        "type_config": type_config or {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    if avatar_url:
        agent_data["avatar_url"] = avatar_url

    # Strip to valid columns only
    agent_data = {k: v for k, v in agent_data.items() if k in AGENT_COLUMNS}

    try:
        result = client.table("agents").insert(agent_data).execute()

        if not result.data:
            return {"success": False, "error": "insert_failed", "message": "Failed to create agent"}

        agent = result.data[0]

        # ADR-106: Seed workspace AGENT.md
        if instructions_text:
            try:
                from services.workspace import AgentWorkspace, get_agent_slug
                ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
                # ADR-118: Append capability reference for agents that may produce rich outputs
                agent_md = instructions_text
                from services.agent_framework import has_asset_capabilities
                if has_asset_capabilities(role):
                    agent_md += "\n\n## Available Capabilities\nThis agent can produce rich outputs via RuntimeDispatch: PNG/SVG charts, diagrams, and images. Use these when visual data or formatted reports would serve the recipient better than plain text."
                # ADR-154: Coherence protocol removed from agent level — reflections
                # are now per-task via awareness.md, not per-agent.
                await ws.write("AGENT.md", agent_md,
                               summary="Agent identity and behavioral instructions")

                # ADR-143: Seed playbook files from type registry
                from services.agent_framework import get_type_playbook
                playbook = get_type_playbook(role)
                for filename, content in playbook.items():
                    await ws.write(
                        f"memory/{filename}",
                        content,
                        summary=f"ADR-143: seed playbook ({filename})",
                    )
            except Exception as e:
                logger.error(f"[AGENT_CREATION] Workspace seed FAILED for {entity_id} — agent exists in DB but has no AGENT.md: {e}")

        logger.info(f"[AGENT_CREATION] Created: {title} ({entity_id}), origin={origin}, role={role}")

        return {
            "success": True,
            "agent_id": entity_id,
            "agent": agent,
            "message": f"Created agent '{title}'.",
        }

    except Exception as e:
        logger.error(f"[AGENT_CREATION] Failed: {e}")
        return {"success": False, "error": "creation_failed", "message": str(e)}
