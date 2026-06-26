"""OVERLAY adapter — ChatGPT (OpenAI Apps SDK) `_meta` keys.

This is the ONE file where the name "openai" appears in the presentation layer
(ADR-372 D5). It overlays the open mcp_apps shape with the keys ChatGPT's
renderer actually reads.

LIVE FINDING (2026-06-26): the open-spec `_meta.ui.resourceUri` alone registered
the template (it appeared in ChatGPT's Templates list) but ChatGPT rendered
TEXT, never the widget — because ChatGPT's renderer binds a tool to its template
via `openai/outputTemplate` on the tool DEFINITION, not `ui.resourceUri`.
Verified against OpenAI's own example server (openai-apps-sdk-examples,
pizzaz_server_python): tool-definition `_meta` is

    {
        "openai/outputTemplate": "<ui:// template uri>",
        "openai/toolInvocation/invoking": "<status text>",
        "openai/toolInvocation/invoked": "<status text>",
        "openai/widgetAccessible": True,
    }

and the served resource uses mimeType "text/html+skybridge". So for ChatGPT
these keys are NOT optional sugar — they are the load-bearing binding. We keep
the open `ui.resourceUri` too (additive, ignored by ChatGPT, used by any future
open-spec host), so the adapter stays portable per ADR-372 D2 while actually
rendering on ChatGPT today. As the open MCP Apps spec converges with these keys,
prefer moving them into mcp_apps and shrinking this overlay.
"""

from __future__ import annotations

from typing import Any


def overlay_definition(meta: dict, widget: Any) -> dict:
    """Add the ChatGPT tool-definition binding keys (load-bearing for render).

    Additive over the open `ui.resourceUri` shape: ChatGPT reads
    `openai/outputTemplate`; an open-spec host reads `ui.resourceUri`.
    """
    meta = {**meta}
    meta["openai/outputTemplate"] = widget.uri
    meta["openai/widgetAccessible"] = True
    meta["openai/toolInvocation/invoking"] = widget.invoking
    meta["openai/toolInvocation/invoked"] = widget.invoked
    return meta


def overlay_response(meta: dict, widget: Any) -> dict:
    """Add ChatGPT tool-response sugar (additive, non-destructive).

    OpenAI's example repeats only the invocation-status keys on the response;
    the template binding lives on the definition. Kept thin.
    """
    meta = {**meta}
    meta["openai/toolInvocation/invoking"] = widget.invoking
    meta["openai/toolInvocation/invoked"] = widget.invoked
    return meta
