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
from services.agent_registry import AGENT_TYPES, LEGACY_ROLE_MAP
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
    # ADR-164: YARNNN as meta-cognitive agent — orchestration is autonomous scope
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
    - user_configured (YARNNN chat, UI form)
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
                from services.agent_registry import has_asset_capabilities
                if has_asset_capabilities(role):
                    agent_md += "\n\n## Available Capabilities\nThis agent can produce rich outputs via RuntimeDispatch: PNG/SVG charts, diagrams, and images. Use these when visual data or formatted reports would serve the recipient better than plain text."
                # ADR-154: Coherence protocol removed from agent level — reflections
                # are now per-task via awareness.md, not per-agent.
                await ws.write("AGENT.md", agent_md,
                               summary="Agent identity and behavioral instructions")

                # ADR-143: Seed playbook files from type registry
                from services.agent_registry import get_type_playbook
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


# =============================================================================
# ADR-205: Infrastructure Agent Classification + Lazy Ensure
# (amended by ADR-207 P4a: Platform Bots dissolved into capability gates)
# =============================================================================
# ADR-205 collapses signup-time scaffolding to a single workspace identity:
# YARNNN (role=thinking_partner). Specialists are lazy-created — a row
# materializes the first time dispatch resolves to that role.
#
# ADR-207 P4a (2026-04-22) dissolves Platform Bots as an agent class. Slack,
# Notion, GitHub, Commerce, and Trading are now accessed via CAPABILITIES
# (read_slack, write_notion, write_trading, ...) gated by
# `platform_connection_requirement` (ADR-207 P3). No agent row — any
# specialist can invoke a platform capability if the connection is active.
# The `platform_bot` classification is removed; `delete_platform_bot`
# deleted; `ensure_infrastructure_agents_for_type` deleted (callers derive
# ensure list from TASK.md process steps).

SPECIALIST_ROLES: frozenset[str] = frozenset({
    # ADR-176 universal specialists
    "researcher", "analyst", "writer", "tracker", "designer",
    # ADR-176 synthesizer
    "executive",
})

# Infrastructure slug → role. Slugs are derived from AGENT_TEMPLATES display
# names via _slugify_agent; this map is the inverse. Dispatch sites that resolve
# by slug use it to find the underlying infrastructure role for lazy-ensure.
_INFRA_SLUG_TO_ROLE: dict[str, str] = {
    # Specialists (ADR-176 display names → slugs)
    "researcher": "researcher",
    "analyst": "analyst",
    "writer": "writer",
    "tracker": "tracker",
    "designer": "designer",
    "reporting": "executive",  # title "Reporting" → slug "reporting", role "executive"
    # YARNNN
    "thinking-partner": "thinking_partner",
    # ADR-207 P4a: Platform Bot slugs (slack-bot / notion-bot / github-bot /
    # commerce-bot / trading-bot) removed — bots no longer exist as agent rows.
}


def resolve_infra_role_from_ref(agent_ref: str) -> Optional[str]:
    """Return the infrastructure role for a ref that may be a role or a slug.

    ADR-205: dispatch sites may see either a slug (e.g. "reporting") or a role
    (e.g. "executive") in TASK.md's agent_ref. This returns the canonical role
    for lazy-ensure if the ref is an infrastructure identifier, else None.
    """
    if classify_role(agent_ref) != "user_authored":
        return agent_ref
    return _INFRA_SLUG_TO_ROLE.get(agent_ref)


def classify_role(role: str) -> str:
    """Classify a role for ADR-205 dispatch routing.

    Returns one of:
      - "yarnnn"        → role == thinking_partner (one per workspace, scaffolded at signup)
      - "specialist"    → one of SPECIALIST_ROLES (lazy-ensured on first dispatch)
      - "user_authored" → everything else (queried from agents table normally)

    ADR-207 P4a: `platform_bot` classification removed. Platform access runs
    through CAPABILITIES + capability_available() at dispatch, not through
    a dedicated agent class.
    """
    if role == "thinking_partner":
        return "yarnnn"
    if role in SPECIALIST_ROLES:
        return "specialist"
    return "user_authored"


async def ensure_infrastructure_agent(
    client: Any,
    user_id: str,
    role: str,
) -> Optional[dict]:
    """Ensure a row exists in `agents` for this (user_id, role) infrastructure agent.

    ADR-205: YARNNN and Specialists are lazy-scaffolded. The dispatch layer
    calls this helper before resolving a role-based agent_ref; if the row
    doesn't exist yet, it is created from AGENT_TEMPLATES[role].

    Returns:
      - The agent dict (existing or newly created) on success.
      - None if the role is user_authored (caller should query agents
        table directly).
      - None if the role is unknown or creation failed.

    ADR-207 P4a: platform_bot classification + per-platform connection check
    removed. Platform capability gating now happens in the task pipeline via
    `capability_available()`; no pre-dispatch "bot requires connection"
    check is needed at the agent-ensure layer.
    """
    classification = classify_role(role)

    # User-authored agents are resolved by the caller via direct query.
    if classification == "user_authored":
        return None

    # Try to find existing infrastructure row (idempotent).
    existing = (
        client.table("agents")
        .select("*")
        .eq("user_id", user_id)
        .eq("role", role)
        .eq("origin", "system_bootstrap")
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    # Lazy-create from AGENT_TEMPLATES.
    from services.agent_registry import AGENT_TEMPLATES
    template = AGENT_TEMPLATES.get(role)
    if not template:
        logger.warning(f"[ensure_infrastructure_agent] No template for role: {role}")
        return None

    title = template.get("display_name") or role.replace("_", " ").title()
    result = await create_agent_record(
        client=client,
        user_id=user_id,
        title=title,
        role=role,
        origin="system_bootstrap",
        agent_instructions=template.get("default_instructions", ""),
    )
    if not result.get("success"):
        logger.warning(
            f"[ensure_infrastructure_agent] Create failed for {role}: "
            f"{result.get('message')}"
        )
        return None
    logger.info(f"[ensure_infrastructure_agent] Lazy-created {role} for {user_id[:8]}")
    return result.get("agent")


async def ensure_infrastructure_agents_for_type(
    client: Any,
    user_id: str,
    type_key: str,
) -> None:
    """Ensure all infrastructure agents declared by a task type's process steps exist.

    ADR-205: called before task creation / type change so `resolve_process_agents`
    can find Specialist rows (which are lazy-scaffolded). ADR-207 P4a removed
    the bot branch — only Specialists are ensured.
    """
    from services.task_types import TASK_TYPES
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return
    seen: set[str] = set()
    for step in task_type.get("process", []):
        role = step.get("agent_type")
        if not role or role in seen:
            continue
        seen.add(role)
        if classify_role(role) == "user_authored":
            continue
        await ensure_infrastructure_agent(client, user_id, role)


# ADR-207 P4a: delete_platform_bot() DELETED. Platform Bots no longer exist
# as agent rows; OAuth disconnect no longer needs to cascade-delete a bot
# row. Migration 157 drops any stale bot rows once.
