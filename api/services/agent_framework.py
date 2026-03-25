"""
Agent Framework — ADR-140 Workforce Model (v3)

Pre-scaffolded agent roster. Three registries, three concerns:
  1. AGENT_TYPES  — workforce roster: agents + bots, capabilities each gets
  2. CAPABILITIES — implementation: what each capability resolves to
  3. RUNTIMES     — infrastructure: where compute happens

Three independent axes per agent (ADR-140):
  - Identity (AGENT.md): name, domain, evolves with use
  - Capabilities (AGENT_TYPES): tool access, fixed at creation
  - Tasks (TASK.md): work assignments, come and go

v3 (2026-03-25): 4 agents + 2 bots. Agents are domain-cognitive (multi-step
reasoning, deep expertise). Bots are platform-mechanical (read/write one platform).
All 6 pre-scaffolded at sign-up. Tasks assigned downstream.

Canonical reference: docs/adr/ADR-140-agent-workforce-model.md
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Union


# =============================================================================
# Registry 1: Agent Types — workforce roster (ADR-140)
# =============================================================================
# Pre-scaffolded at sign-up. Two classes:
#   agent — domain-cognitive, multi-step reasoning, deep expertise
#   bot   — platform-mechanical, scoped to one platform's API
#
# Type determines capabilities (axis 2). Identity (axis 1) and tasks (axis 3)
# are independent — see ADR-140 for the three-axis model.

AGENT_TYPES: dict[str, dict[str, Any]] = {

    # ── Agents (domain-cognitive) ──

    "research": {
        "class": "agent",
        "display_name": "Research Agent",
        "tagline": "Investigates and analyzes",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge", "read_platforms",
            "investigate", "produce_markdown", "chart", "mermaid", "image", "compose_html",
        ],
        "description": "Deep investigation across web and workspace. Produces structured "
                       "analysis with evidence. Competitor tracking, market research, due diligence.",
        "default_instructions": "Investigate assigned topics with depth. Use web search and "
                                "workspace context. Produce structured analysis with evidence. "
                                "Prioritize insights the user hasn't seen elsewhere.",
    },

    "content": {
        "class": "agent",
        "display_name": "Content Agent",
        "tagline": "Creates deliverables",
        "capabilities": [
            "read_workspace", "search_knowledge", "produce_markdown",
            "chart", "mermaid", "image", "video_render", "compose_html",
        ],
        "description": "Produces polished deliverables from workspace context. Reports, "
                       "presentations, blog posts, investor updates, documents.",
        "default_instructions": "Produce polished deliverables for the target audience. "
                                "Use charts and visuals where they add clarity. Structure for "
                                "readability. Focus on quality and completeness.",
    },

    "marketing": {
        "class": "agent",
        "display_name": "Marketing Agent",
        "tagline": "Handles go-to-market",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge", "read_platforms",
            "produce_markdown", "compose_html",
        ],
        "description": "GTM tracking, content distribution, competitive positioning, "
                       "campaign analysis. Monitors market signals, produces GTM insights.",
        "default_instructions": "Track go-to-market activities and competitive positioning. "
                                "Monitor market signals. Produce actionable GTM insights and content.",
    },

    "crm": {
        "class": "agent",
        "display_name": "CRM Agent",
        "tagline": "Manages relationships",
        "capabilities": [
            "read_platforms", "read_workspace", "search_knowledge",
            "produce_markdown", "compose_html",
        ],
        "description": "Client tracking, relationship management, follow-ups, meeting "
                       "preparation. Reads platform context for relationship signals.",
        "default_instructions": "Track client relationships and interactions. Prepare meeting "
                                "briefs. Flag follow-ups and action items. Summarize relationship health.",
    },

    # ── Bots (platform-mechanical) ──

    "slack_bot": {
        "class": "bot",
        "display_name": "Slack Bot",
        "tagline": "Reads and writes Slack",
        "capabilities": [
            "read_platforms", "write_slack", "summarize", "produce_markdown",
        ],
        "platform": "slack",
        "description": "Platform bot for Slack. Recaps, summaries, alerts, message posting.",
        "default_instructions": "Monitor Slack channels. Summarize key discussions. Post updates "
                                "when directed. Flag action items and decisions.",
    },

    "notion_bot": {
        "class": "bot",
        "display_name": "Notion Bot",
        "tagline": "Reads and writes Notion",
        "capabilities": [
            "read_platforms", "write_notion", "summarize", "produce_markdown",
        ],
        "platform": "notion",
        "description": "Platform bot for Notion. Knowledge base management, page syncing, "
                       "content updates.",
        "default_instructions": "Manage Notion workspace. Sync meeting notes. Update knowledge "
                                "base pages. Track document changes.",
    },
}

# Default roster created at sign-up (ADR-140)
DEFAULT_ROSTER = [
    {"title": "Research Agent", "role": "research"},
    {"title": "Content Agent", "role": "content"},
    {"title": "Marketing Agent", "role": "marketing"},
    {"title": "CRM Agent", "role": "crm"},
    {"title": "Slack Bot", "role": "slack_bot"},
    {"title": "Notion Bot", "role": "notion_bot"},
]

# PM_MODES — REMOVED (PM/project architecture dissolved)


# Legacy role → new type mapping (for DB migration / backward compat reads)
LEGACY_ROLE_MAP: dict[str, str] = {
    # v1 legacy
    "digest": "research",
    "synthesize": "research",
    "prepare": "content",
    "custom": "research",
    # v2 legacy (ADR-130)
    "briefer": "research",
    "monitor": "research",
    "scout": "research",
    "researcher": "research",
    "analyst": "research",
    "drafter": "content",
    "writer": "content",
    "planner": "content",
    # v3 current types pass through
    "research": "research",
    "content": "content",
    "marketing": "marketing",
    "crm": "crm",
    "slack_bot": "slack_bot",
    "notion_bot": "notion_bot",
}


def resolve_role(role: str) -> str:
    """Map legacy role names to current types. Passthrough for current types."""
    if role in AGENT_TYPES:
        return role
    return LEGACY_ROLE_MAP.get(role, role)


# =============================================================================
# Registry 2: Capabilities — what each capability resolves to
# =============================================================================

CAPABILITIES: dict[str, dict[str, Any]] = {
    # -- Cognitive (prompt-driven, no dedicated tool) --
    "read_platforms":    {"category": "cognitive", "runtime": "internal"},
    "summarize":         {"category": "cognitive", "runtime": "internal"},
    "detect_change":     {"category": "cognitive", "runtime": "internal"},
    "alert":             {"category": "cognitive", "runtime": "internal"},
    "cross_reference":   {"category": "cognitive", "runtime": "internal"},
    "data_analysis":     {"category": "cognitive", "runtime": "internal"},
    "investigate":       {"category": "cognitive", "runtime": "internal"},
    "produce_markdown":  {"category": "cognitive", "runtime": "internal"},

    # -- Tool-backed (internal primitives) --
    "web_search":        {"category": "tool", "runtime": "internal", "tool": "WebSearch"},
    "read_workspace":    {"category": "tool", "runtime": "internal", "tool": "ReadWorkspace"},
    "search_knowledge":  {"category": "tool", "runtime": "internal", "tool": "QueryKnowledge"},

    # -- Asset production (compute runtimes) --
    "chart":   {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "chart/SKILL.md",
        "output_type": "image/png",
    },
    "mermaid": {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "mermaid/SKILL.md",
        "output_type": "image/svg+xml",
    },
    "image":   {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "image/SKILL.md",
        "output_type": "image/png",
    },
    "video_render": {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "video/SKILL.md",
        "output_type": "video/mp4",
        "timeout": 180,  # extended timeout for video rendering
    },

    # -- Composition (post-generation pipeline step) --
    "compose_html": {
        "category": "composition", "runtime": "python_render",
        "post_generation": True,
    },

    # PM coordination capabilities removed — PM/project architecture dissolved
}


# =============================================================================
# Registry 3: Runtimes — where compute happens
# =============================================================================

RUNTIMES: dict[str, dict[str, Any]] = {
    "internal":       {"description": "In-process, no HTTP call"},
    "python_render":  {"description": "yarnnn-render service (Docker: Python + Node.js + Chromium + matplotlib + Remotion)"},
    "external:slack": {"description": "Slack API via user OAuth token"},
    "external:notion":{"description": "Notion API via user OAuth token"},
}


# =============================================================================
# Type Query Helpers
# =============================================================================

def get_type_capabilities(agent_type: str) -> list[str]:
    """Return the capability list for an agent type. Falls back to briefer for unknown."""
    resolved = resolve_role(agent_type)
    type_def = AGENT_TYPES.get(resolved)
    if not type_def:
        return AGENT_TYPES["research"]["capabilities"]
    return type_def["capabilities"]


def has_capability(agent_type: str, capability: str) -> bool:
    """Check if an agent type has a specific capability."""
    return capability in get_type_capabilities(agent_type)


def has_asset_capabilities(agent_type: str) -> bool:
    """Check if an agent type has any asset-producing capabilities (chart, mermaid, image).

    Determines whether an agent gets SKILL.md injection and RenderAsset access.
    """
    caps = get_type_capabilities(agent_type)
    return any(
        CAPABILITIES.get(c, {}).get("category") == "asset"
        for c in caps
    )


def get_type_skill_docs(agent_type: str) -> list[str]:
    """Return skill doc paths for capabilities that have them."""
    caps = get_type_capabilities(agent_type)
    docs = []
    for c in caps:
        cap_def = CAPABILITIES.get(c, {})
        if cap_def.get("skill_docs"):
            docs.append(cap_def["skill_docs"])
    return docs


def get_type_display(agent_type: str) -> dict[str, str]:
    """Return display_name and tagline for a type. Used by frontend + TP prompt."""
    resolved = resolve_role(agent_type)
    type_def = AGENT_TYPES.get(resolved, AGENT_TYPES.get("briefer", {}))
    return {
        "display_name": type_def.get("display_name", agent_type.title()),
        "tagline": type_def.get("tagline", ""),
    }


def list_agent_types(include_pm: bool = False) -> list[dict]:
    """List all agent types for system reference / TP prompt injection."""
    types = []
    for key, tdef in AGENT_TYPES.items():
        if key == "pm" and not include_pm:
            continue
        types.append({
            "type": key,
            "display_name": tdef["display_name"],
            "tagline": tdef["tagline"],
            "capabilities": tdef["capabilities"],
            "has_assets": has_asset_capabilities(key),
        })
    return types


# =============================================================================
# Pulse Cadence — how often each type senses (ADR-126)
# =============================================================================

ROLE_PULSE_CADENCE: dict[str, Union[timedelta, str]] = {
    # v3 types (ADR-140)
    "research":   "schedule",   # runs on task cadence
    "content":    "schedule",   # runs on task cadence
    "marketing":  "schedule",   # runs on task cadence
    "crm":        "schedule",   # runs on task cadence
    "slack_bot":  timedelta(hours=1),   # frequent platform monitoring
    "notion_bot": timedelta(hours=12),  # daily platform sync
}

_DEFAULT_PULSE_CADENCE = "schedule"


def get_pulse_cadence(role: str) -> Union[timedelta, str]:
    """Return the pulse cadence for a role/type."""
    return ROLE_PULSE_CADENCE.get(role, _DEFAULT_PULSE_CADENCE)
