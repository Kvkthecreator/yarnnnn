"""MCP presentation layer — host-negotiated rich rendering on the interop face.

Governed by ADR-372. The interop face (MCP) returns text by default; a host that
can render a widget (ChatGPT via the OpenAI Apps SDK, or any MCP Apps host) gets
an interactive view of the SAME returned substrate. This package is the entire
presentation dimension:

    affordances.py   — per-tool affordance DECLARATIONS (data, not code; ADR-372 D1)
    registry.py      — widget id → ui:// resource (uri, mime, csp/domain; ADR-372 D3-served)
    adapters/        — neutral affordance → vendor `_meta` shape (ADR-372 D2/D5)
    hosts.py         — the Host Profile registry: identity + render gate + dialect
                       per connecting LLM host (ADR-379; absorbs the ADR-372 D4 gate)

Invariants this package must never erode (ADR-372):
    D3  a widget renders RETURNED substrate; the model still narrates — additive,
        never a replacement, never host-composed judgment.
    D4  (amended 2026-06-27) the full RESULT is ALWAYS in the text channel
        (content/structuredContent) for every host — that, not any host
        handshake, is what keeps the ADR-368 invariant true. The widget `_meta`
        pointer, by contrast, is attached ONLY to a host that renders widgets
        (hosts.renders_widgets). The original "attach `_meta` unconditionally"
        was falsified live: claude.ai tries to render the pointed-at resource
        (skybridge MIME + openai/* keys) and fails. Allow-list semantics with a
        text-safe default: an unidentified host gets text, never a broken widget.
    D5  all presentation code lives here, inside `api/mcp_server/`. The kernel and
        `api/services/*` never learn a host exists. A host name appears in code in
        exactly one place: its adapter file (vendor `_meta` shape) or hosts.py
        (which hosts can render).

This package imports NOTHING from `api/services/*` (the kernel). It is pure
presentation: declarations + `_meta` shaping over results the tools already return.
"""

from mcp_server.presentation.affordances import AFFORDANCES, Affordance
from mcp_server.presentation.hosts import (
    HOSTS,
    HostProfile,
    WIDGET_RENDERING_HOSTS,
    renders_widgets,
    resolve_host_id,
    widget_dialect,
)
from mcp_server.presentation.registry import RESOURCE_MIME, WIDGETS, Widget, tool_response_meta, tool_definition_meta

__all__ = [
    "AFFORDANCES",
    "Affordance",
    "HOSTS",
    "HostProfile",
    "RESOURCE_MIME",
    "WIDGETS",
    "Widget",
    "WIDGET_RENDERING_HOSTS",
    "renders_widgets",
    "resolve_host_id",
    "widget_dialect",
    "tool_response_meta",
    "tool_definition_meta",
]
