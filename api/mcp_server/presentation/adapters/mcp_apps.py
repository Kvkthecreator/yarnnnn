"""PRIMARY adapter — the open MCP Apps spec shape (SEP-1865, ratified 2026-01-26).

The ratified linkage is `_meta.ui.resourceUri` pointing at a `ui://` resource; the
served resource carries `_meta.ui.domain` + a CSP block. This adapter speaks only
the open spec — no vendor names. ChatGPT-specific sugar lives in the openai overlay.

Typed loosely (dict) to avoid a hard import of the Widget dataclass into the
adapter layer; the registry passes a Widget and we read its public attributes.
"""

from __future__ import annotations

from typing import Any


def tool_definition_meta(widget: Any) -> dict:
    """`_meta` for a tool DEFINITION — registers the template with the host."""
    return {"ui": {"resourceUri": widget.uri}}


def tool_response_meta(widget: Any) -> dict:
    """`_meta` for a tool RESPONSE — links this result to its widget template."""
    return {"ui": {"resourceUri": widget.uri}}


def served_resource_meta(widget: Any) -> dict:
    """`_meta.ui` for the SERVED RESOURCE — domain + CSP (submission requires it)."""
    return {
        "ui": {
            "domain": widget.domain,
            "csp": {"connectDomains": list(widget.csp_connect)},
        }
    }
