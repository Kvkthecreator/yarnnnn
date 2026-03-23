"""
Agent Framework — ADR-130 Three-Registry Architecture (v2)

Canonical registry for agent capabilities. The agent type registry is the
product catalog — each type is a role a user "hires" for their project team.

Three registries, three concerns:
  1. AGENT_TYPES  — product catalog: types users hire, capabilities each gets
  2. CAPABILITIES — implementation: what each capability resolves to
  3. RUNTIMES     — infrastructure: where compute happens

v2 (2026-03-23): 8 user-facing types + PM. Expanded from v1's 5 implementation-
oriented types. Types are product offerings, not internal taxonomy.
Dissolves: synthesize (→ analyst/briefer), prepare (→ planner), custom (→ pick a type).
Adds: drafter, analyst, writer, planner, scout.

Multi-agent coordination model: projects are teams. Each project has 1 PM +
1..N contributor agents of various types. PM orchestrates via work plan.
Lean start (1 contributor at scaffold), team grows via Composer/TP/user.

Canonical reference: docs/architecture/output-substrate.md
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Union


# =============================================================================
# Registry 1: Agent Types — product catalog
# =============================================================================
# Each type is a "hire" — a role the user adds to their project team.
# Type determines: capabilities, prompt template, pulse cadence, description.
# Personification (title, scoping) comes from instructions + project context.
#
# v2 — 8 user-facing types + PM infrastructure type.

AGENT_TYPES: dict[str, dict[str, Any]] = {

    # ── User-facing types (the product catalog) ──

    "briefer": {
        "display_name": "Briefer",
        "tagline": "Keeps you briefed on what's happening",
        "capabilities": [
            "read_platforms", "summarize", "produce_markdown", "compose_html",
        ],
        "description": "Recurring summaries of platform activity scoped to a domain. "
                       "Reads Slack, Notion, workspace files. Produces daily/weekly briefings.",
        "default_trigger": "recurring",
        "default_frequency": "daily",
    },

    "monitor": {
        "display_name": "Monitor",
        "tagline": "Watches for what matters and alerts you",
        "capabilities": [
            "read_platforms", "detect_change", "alert",
            "produce_markdown", "compose_html",
        ],
        "description": "Continuous monitoring with threshold-based alerts. "
                       "Detects changes, escalations, anomalies. Always-on sensing.",
        "default_trigger": "recurring",
        "default_frequency": "daily",
    },

    "researcher": {
        "display_name": "Researcher",
        "tagline": "Investigates topics and produces analysis",
        "capabilities": [
            "read_platforms", "web_search", "investigate",
            "produce_markdown", "chart", "mermaid", "compose_html",
        ],
        "description": "Deep investigation on focused topics. Uses workspace context + web search. "
                       "Produces research reports, comparisons, due diligence.",
        "default_trigger": "recurring",
        "default_frequency": "weekly",
    },

    "drafter": {
        "display_name": "Drafter",
        "tagline": "Produces deliverables and documents for you",
        "capabilities": [
            "read_platforms", "produce_markdown",
            "chart", "mermaid", "compose_html",
        ],
        "description": "Creates specific work products: reports, decks, client updates, "
                       "quarterly reviews. Recurring or bounded (produce and done).",
        "default_trigger": "recurring",
        "default_frequency": "weekly",
    },

    "analyst": {
        "display_name": "Analyst",
        "tagline": "Tracks metrics and surfaces patterns",
        "capabilities": [
            "read_platforms", "data_analysis", "cross_reference",
            "chart", "mermaid", "produce_markdown", "compose_html",
        ],
        "description": "Tracks patterns over time. Data analysis, trend identification, "
                       "metric tracking. Produces data-rich reports with charts.",
        "default_trigger": "recurring",
        "default_frequency": "weekly",
    },

    "writer": {
        "display_name": "Writer",
        "tagline": "Crafts communications and content",
        "capabilities": [
            "read_platforms", "produce_markdown", "compose_html",
        ],
        "description": "Produces external-facing content: newsletters, investor updates, "
                       "client emails, social posts. Tone-aware, audience-scoped.",
        "default_trigger": "recurring",
        "default_frequency": "weekly",
    },

    "planner": {
        "display_name": "Planner",
        "tagline": "Prepares plans, agendas, and follow-ups",
        "capabilities": [
            "read_platforms", "produce_markdown", "compose_html",
        ],
        "description": "Event-driven or recurring planning: meeting prep, action item tracking, "
                       "project planning, follow-up reminders. Reads platform context for prep.",
        "default_trigger": "recurring",
        "default_frequency": "daily",
    },

    "scout": {
        "display_name": "Scout",
        "tagline": "Tracks competitors and market movements",
        "capabilities": [
            "read_platforms", "web_search",
            "produce_markdown", "chart", "compose_html",
        ],
        "description": "Continuous competitive and market monitoring. Tracks external sources, "
                       "flags changes, produces periodic intelligence reports.",
        "default_trigger": "recurring",
        "default_frequency": "weekly",
    },

    # ── Infrastructure type (not user-facing) ──

    "pm": {
        "display_name": "Project Manager",
        "tagline": "Coordinates your project team",
        "capabilities": [
            "read_workspace", "check_freshness", "steer_contributors",
            "trigger_assembly", "manage_work_plan",
        ],
        "description": "Coordinates project contributors. Manages work plan, steers via "
                       "contribution briefs, gates quality, assembles deliverables, delivers.",
        "default_trigger": "proactive",
        "default_frequency": "daily",
    },
}

# Legacy role → new type mapping (for DB migration / backward compat reads)
LEGACY_ROLE_MAP: dict[str, str] = {
    "digest": "briefer",
    "synthesize": "analyst",
    "research": "researcher",
    "prepare": "planner",
    "custom": "briefer",  # safe default
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

    # -- Asset production (compute runtimes) --
    "chart":   {
        "category": "asset", "runtime": "python_render",
        "tool": "RenderAsset", "skill_docs": "chart/SKILL.md",
        "output_type": "image/png",
    },
    "mermaid": {
        "category": "asset", "runtime": "python_render",
        "tool": "RenderAsset", "skill_docs": "mermaid/SKILL.md",
        "output_type": "image/svg+xml",
    },
    "image":   {
        "category": "asset", "runtime": "python_render",
        "tool": "RenderAsset", "skill_docs": "image/SKILL.md",
        "output_type": "image/png",
    },

    # -- Composition (post-generation pipeline step) --
    "compose_html": {
        "category": "composition", "runtime": "python_render",
        "post_generation": True,
    },

    # -- PM coordination --
    "check_freshness":    {"category": "pm", "runtime": "internal", "tool": "CheckContributorFreshness"},
    "steer_contributors": {"category": "pm", "runtime": "internal", "tool": "WriteWorkspace"},
    "trigger_assembly":   {"category": "pm", "runtime": "internal"},
    "manage_work_plan":   {"category": "pm", "runtime": "internal", "tool": "UpdateWorkPlan"},
}


# =============================================================================
# Registry 3: Runtimes — where compute happens
# =============================================================================

RUNTIMES: dict[str, dict[str, Any]] = {
    "internal":       {"description": "In-process, no HTTP call"},
    "python_render":  {"description": "yarnnn-render service (Docker: Python + matplotlib + pandoc + pillow + mermaid-cli)"},
    "node_remotion":  {"description": "yarnnn-video service (Docker: Node.js + Remotion + Chrome) [future]"},
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
        return AGENT_TYPES["briefer"]["capabilities"]
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
    "monitor":    timedelta(hours=1),
    "pm":         timedelta(hours=2),
    "briefer":    timedelta(hours=12),
    "analyst":    "schedule",
    "researcher": "schedule",
    "drafter":    "schedule",
    "writer":     "schedule",
    "planner":    timedelta(hours=12),
    "scout":      "schedule",
    # Legacy mappings
    "digest":     timedelta(hours=12),
    "synthesize": "schedule",
    "research":   "schedule",
    "prepare":    timedelta(hours=12),
    "custom":     "schedule",
}

_DEFAULT_PULSE_CADENCE = "schedule"


def get_pulse_cadence(role: str) -> Union[timedelta, str]:
    """Return the pulse cadence for a role/type."""
    return ROLE_PULSE_CADENCE.get(role, _DEFAULT_PULSE_CADENCE)
