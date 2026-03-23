"""
Agent Framework — ADR-130 Three-Registry Architecture + ADR-126 Pulse Cadence

Canonical registry for agent capabilities. Determines what an agent can do
(capabilities), what tools it gets, what skill docs enter its prompt,
and how often it senses (pulse cadence).

Three registries, three concerns:
  1. AGENT_TYPES  — deterministic capability bundles per type (fixed at creation)
  2. CAPABILITIES — each capability → runtime, tool, skill docs, output type
  3. RUNTIMES     — where compute happens (internal, python_render, etc.)

Agent development is knowledge depth (accumulated memory, preferences, domain
expertise), not capability breadth. No seniority gating.

Type definitions are v1 — expect revision as ADR-132 and downstream work
stabilizes. The registry *structure* is the durable part; the entries inside
are the volatile part.

Canonical reference: docs/architecture/output-substrate.md
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Union


# =============================================================================
# Registry 1: Agent Types — deterministic capability bundles
# =============================================================================
# Each type is a fixed set of capabilities, determined at creation.
# Type = what this agent can do. Personification comes from instructions.
#
# v1 — expect revision after ADR-132 stabilizes type definitions.

AGENT_TYPES: dict[str, dict[str, Any]] = {
    "digest": {
        "capabilities": [
            "read_platforms", "synthesize", "produce_markdown", "compose_html",
        ],
        "description": "Summarizes platform activity into recurring digests",
        "default_trigger": "recurring",
    },
    "monitor": {
        "capabilities": [
            "read_platforms", "detect_change", "alert",
            "produce_markdown", "compose_html",
        ],
        "description": "Watches for changes and alerts on significant events",
        "default_trigger": "recurring",
    },
    "research": {
        "capabilities": [
            "read_platforms", "web_search", "investigate",
            "produce_markdown", "chart", "mermaid", "compose_html",
        ],
        "description": "Investigates topics using workspace and web sources",
        "default_trigger": "goal",
    },
    "synthesize": {
        "capabilities": [
            "read_platforms", "cross_reference", "data_analysis",
            "chart", "mermaid", "produce_markdown", "compose_html",
        ],
        "description": "Finds patterns across sources and produces analysis",
        "default_trigger": "recurring",
    },
    "prepare": {
        "capabilities": [
            "read_platforms", "produce_markdown", "compose_html",
        ],
        "description": "Prepares briefings and materials ahead of events",
        "default_trigger": "recurring",
    },
    "pm": {
        "capabilities": [
            "read_workspace", "check_freshness", "steer_contributors",
            "trigger_assembly", "manage_work_plan",
        ],
        "description": "Coordinates project contributors and manages delivery",
        "default_trigger": "proactive",
    },
    "custom": {
        "capabilities": [
            "read_platforms", "produce_markdown", "compose_html",
        ],
        "description": "User-defined agent with base capabilities",
        "default_trigger": "recurring",
    },
}


# =============================================================================
# Registry 2: Capabilities — what each capability resolves to
# =============================================================================
# Each capability maps to: runtime, tool (if any), skill_docs (if any),
# output_type, and whether it's a post-generation step.
#
# Categories:
#   - cognitive: prompt-driven, no tool call needed
#   - tool: backed by a headless primitive
#   - asset: produces binary output via compute runtime
#   - composition: post-generation pipeline step
#   - pm: project coordination primitives

CAPABILITIES: dict[str, dict[str, Any]] = {
    # -- Cognitive (prompt-driven, no dedicated tool) --
    "read_platforms":    {"category": "cognitive", "runtime": "internal"},
    "synthesize":        {"category": "cognitive", "runtime": "internal"},
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
    """Return the capability list for an agent type. Empty for unknown types."""
    type_def = AGENT_TYPES.get(agent_type)
    if not type_def:
        return AGENT_TYPES["custom"]["capabilities"]
    return type_def["capabilities"]


def has_capability(agent_type: str, capability: str) -> bool:
    """Check if an agent type has a specific capability."""
    return capability in get_type_capabilities(agent_type)


def has_asset_capabilities(agent_type: str) -> bool:
    """Check if an agent type has any asset-producing capabilities (chart, mermaid, image).

    This replaces the old SKILL_ENABLED_ROLES check — determines whether an
    agent gets SKILL.md injection and RenderAsset/RuntimeDispatch access.
    """
    caps = get_type_capabilities(agent_type)
    return any(
        CAPABILITIES.get(c, {}).get("category") == "asset"
        for c in caps
    )


def get_type_skill_docs(agent_type: str) -> list[str]:
    """Return skill doc paths for capabilities that have them.

    Used during headless prompt assembly to inject SKILL.md content.
    """
    caps = get_type_capabilities(agent_type)
    docs = []
    for c in caps:
        cap_def = CAPABILITIES.get(c, {})
        if cap_def.get("skill_docs"):
            docs.append(cap_def["skill_docs"])
    return docs


# =============================================================================
# Role Pulse Cadence — how often each role type senses (ADR-126 Phase 5)
# =============================================================================
# The role defines the natural sensing pace.
# pulse_cadence is the MAXIMUM interval between pulses.
# "schedule" = use the agent's configured schedule as pulse cadence.

ROLE_PULSE_CADENCE: dict[str, Union[timedelta, str]] = {
    "monitor":    timedelta(hours=1),
    "pm":         timedelta(hours=2),
    "digest":     timedelta(hours=12),
    "synthesize": "schedule",
    "research":   "schedule",
    "prepare":    timedelta(hours=12),
    "custom":     "schedule",
}

_DEFAULT_PULSE_CADENCE = "schedule"


def get_pulse_cadence(role: str) -> Union[timedelta, str]:
    """Return the pulse cadence for a role.

    Returns a timedelta for fixed-interval roles, or "schedule" for
    roles that pulse on their delivery rhythm.
    """
    return ROLE_PULSE_CADENCE.get(role, _DEFAULT_PULSE_CADENCE)
