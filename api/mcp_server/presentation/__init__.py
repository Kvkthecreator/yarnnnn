"""MCP presentation layer — host-negotiated rich rendering on the interop face.

Governed by ADR-372. The interop face (MCP) returns text by default; a host that
can render a widget (ChatGPT via the OpenAI Apps SDK, or any MCP Apps host) gets
an interactive view of the SAME returned substrate. This package is the entire
presentation dimension:

    affordances.py   — per-tool affordance DECLARATIONS (data, not code; ADR-372 D1)
    registry.py      — widget id → ui:// resource (uri, mime, csp/domain; ADR-372 D3-served)
    adapters/        — neutral affordance → vendor `_meta` shape (ADR-372 D2/D5)

Invariants this package must never erode (ADR-372):
    D3  a widget renders RETURNED substrate; the model still narrates — additive,
        never a replacement, never host-composed judgment.
    D4  the server attaches `_meta` UNCONDITIONALLY; the full result is ALWAYS in
        the text channel (content/structuredContent). The text channel — not any
        host handshake — is what keeps the ADR-368 invariant true.
    D5  all presentation code lives here, inside `api/mcp_server/`. The kernel and
        `api/services/*` never learn a host exists. A host name appears in code in
        exactly one place: its adapter file.

This package imports NOTHING from `api/services/*` (the kernel). It is pure
presentation: declarations + `_meta` shaping over results the tools already return.
"""

from mcp_server.presentation.affordances import AFFORDANCES, Affordance
from mcp_server.presentation.registry import RESOURCE_MIME, WIDGETS, Widget, tool_response_meta, tool_definition_meta

__all__ = [
    "AFFORDANCES",
    "Affordance",
    "RESOURCE_MIME",
    "WIDGETS",
    "Widget",
    "tool_response_meta",
    "tool_definition_meta",
]
