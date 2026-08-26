"""Turn reach — the member's own connections, inside their own turn (ADR-585).

The principal-presence rule, which is the existing scope taxonomy applied
(ADR-407: verbs are user-scoped; ADR-425: a platform credential is the
member's ACCOUNT object): a chat turn is the member present, driving — the
LLM is their instrument for that turn, so it may read through the
connections THEY hold. Agents, apps, and every headless path stay
workspace-disciplined: landed capture files only, never a credential
(ADR-577 — whose `is_agent_caller` refusal this composes with, not
replaces: a lane turn's `member:` caller identity is a human's hands).

TRANSIENT by disposition (intake-pipeline.md §5): fetched content lives and
dies in the turn's context; keeping something is an ordinary attributed
substrate write (the mcp-lane precedent — no derive step, no auto-landing).

The surface is READ-ONLY and derived from the capability registry's own
read rosters (`PLATFORM_TOOLS_BY_CAPABILITY["read_{platform}"]`) — never a
hand-kept list that could drift into a write tool. Dormant behind
``TURN_REACH_ENABLED`` (default OFF — the ADR-404 D2 pattern: built whole,
lit deliberately).
"""

from __future__ import annotations

import os
from typing import Optional

#: The content platforms a turn may read through — the connector trio.
#: (commerce/trading/email are api-key operational connectors, not content;
#: reddit/hackernews are publisher-lane perceive tools. Widening this tuple
#: is an ADR-585 amendment, not a tweak.)
TURN_REACH_PLATFORMS: tuple = ("slack", "notion", "github")


def is_turn_reach_enabled() -> bool:
    """Deploy-level gate (ADR-585 D2). Default OFF."""
    return os.getenv("TURN_REACH_ENABLED", "").strip().lower() in ("1", "true", "yes")


def turn_reach_tool_names(platforms: Optional[tuple] = None) -> tuple:
    """The read-only platform tool names a reach-bearing turn holds — derived
    from the capability registry's read rosters (Singular Implementation: the
    same rosters agent-capability resolution reads), so a write tool cannot
    drift in without editing the registry itself.

    ADR-612: `platforms` NARROWS to a being's opt-in. None = every reachable
    platform (no opt-in recorded — today's behaviour, and the load-bearing
    default). An empty tuple is a real state: the being reaches nothing, so it
    holds no platform tools at all.
    """
    from services.platform_tools import PLATFORM_TOOLS_BY_CAPABILITY

    allowed = TURN_REACH_PLATFORMS if platforms is None else tuple(platforms)
    names: list = []
    for plat in TURN_REACH_PLATFORMS:
        if plat not in allowed:
            continue
        names.extend(PLATFORM_TOOLS_BY_CAPABILITY.get(f"read_{plat}", []))
    return tuple(names)


def turn_reach_tool_defs(platforms: Optional[tuple] = None) -> list:
    """Anthropic-format definitions for the reach surface, from the provider
    rosters' own schemas (no parallel definitions). A reach name with no
    schema is an ERROR, never a silent drop (the ADR-467 D4 rule)."""
    from services.platform_tools import PLATFORM_TOOLS_BY_PROVIDER

    wanted = set(turn_reach_tool_names(platforms))
    defs = [
        t
        for plat in TURN_REACH_PLATFORMS
        for t in PLATFORM_TOOLS_BY_PROVIDER.get(plat, [])
        if t.get("name") in wanted
    ]
    missing = wanted - {t["name"] for t in defs}
    if missing:
        raise ValueError(
            f"turn-reach names {sorted(missing)} have no tool schema in "
            "PLATFORM_TOOLS_BY_PROVIDER — the registry rosters disagree"
        )
    return defs


__all__ = [
    "TURN_REACH_PLATFORMS",
    "is_turn_reach_enabled",
    "turn_reach_tool_defs",
    "turn_reach_tool_names",
]
