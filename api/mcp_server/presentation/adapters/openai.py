"""OVERLAY adapter — additive ChatGPT-only `_meta` sugar over the open spec.

This is the ONE file where the name "openai" appears in the presentation layer
(ADR-372 D5). Everything here is additive on top of the mcp_apps primary shape and
is ignored by non-OpenAI hosts (ADR-372 D4 — `_meta` keys a host doesn't read are
non-semantic), so it is safe to attach unconditionally. The widget itself
feature-detects `window.openai` at runtime for graceful degradation (ADR-372 D2);
the server never gates on host identity.

Keep this thin. As the open MCP Apps spec absorbs keys OpenAI currently does its
own way, prefer moving them into mcp_apps and shrinking this overlay.
"""

from __future__ import annotations

from typing import Any


def overlay_definition(meta: dict, widget: Any) -> dict:
    """Add ChatGPT tool-definition sugar (additive, non-destructive)."""
    meta = {**meta}
    ui = {**meta.get("ui", {})}
    # `visibility` lets the host know the tool is callable by both the model and
    # the rendered app (the widget's callback path, ADR-372 D6).
    ui.setdefault("visibility", ["model", "app"])
    meta["ui"] = ui
    return meta


def overlay_response(meta: dict, widget: Any) -> dict:
    """Add ChatGPT tool-response sugar (additive, non-destructive).

    Currently a no-op beyond the open shape — the response linkage is fully
    expressed by `_meta.ui.resourceUri`. Kept as the seam for future ChatGPT
    response-only keys (e.g. widget session/state) without touching server.py.
    """
    return {**meta}
