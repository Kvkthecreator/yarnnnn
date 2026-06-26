"""Per-tool presentation affordances — data, not code (ADR-372 D1).

A tool declares an OPTIONAL affordance here; a tool with no entry is text-only
(the default, valid on every host). This is the durable layer: the memory verbs
are subject to change (README §"Why these three verbs"), but the affordance
MECHANISM is stable. A new verb opts in with one dict entry; a removed verb drops
one. No tool body is rewired, and the vendor `_meta` shape is generated downstream
(registry + adapters), never authored here.

`trace` is the first and only affordance: the ADR-209 authored revision chain is
YARNNN's differentiator and a who-changed-what-when timeline is inherently visual.
`remember` is a fire-and-forget write (text confirmation is correct); `recall` is
text-first for now (a `recall-cards` widget is a future, additive entry).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Affordance:
    """A tool's optional rich-rendering declaration.

    Attributes:
        widget:      registry id (→ a `ui://` resource in registry.WIDGETS).
        fallback:    always "text" — the text path is never removed (ADR-372 D4).
        interactive: True if the widget may call back into tools over the MCP Apps
                     bridge (ADR-372 D6 — callbacks are the same gated tool).
    """

    widget: str
    fallback: str = "text"
    interactive: bool = False


#: tool name → affordance. A tool absent from this map is text-only.
AFFORDANCES: dict[str, Affordance] = {
    "trace": Affordance(widget="trace-timeline", fallback="text", interactive=True),
    "recall": Affordance(widget="recall-cards", fallback="text", interactive=False),
    "remember": Affordance(widget="remember-receipt", fallback="text", interactive=False),
}


def affordance_for(tool_name: str) -> Affordance | None:
    """Return the affordance for a tool, or None (text-only)."""
    return AFFORDANCES.get(tool_name)
