"""Widget registry + `_meta` assembly (ADR-372 §3/§4).

Maps a widget id (from affordances.AFFORDANCES) to its served `ui://` resource —
uri, MIME, bundle path, and the served-resource `_meta.ui` fields (domain + CSP
that ChatGPT submission requires). Also assembles the tool-definition and
tool-response `_meta` by delegating the vendor-specific shape to one adapter
(ADR-372 D2/D5: a host name appears in code in exactly one place — its adapter).

The bundle is read from disk at serve time (a built HTML/JS artifact under
`widgets/`). This module imports nothing from `api/services/*` (the kernel).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from mcp_server.presentation.adapters import mcp_apps, openai

logger = logging.getLogger(__name__)

#: MIME for the served widget resource.
#: LIVE FINDING (2026-06-26): ChatGPT's renderer requires "text/html+skybridge"
#: (verified against OpenAI's example server). The generic MCP-Apps MIME
#: ("text/html;profile=mcp-app") registered the template but ChatGPT would not
#: render it. A resource carries one MIME; since ChatGPT is the host we render on
#: today, we serve skybridge. (If a strict open-spec-only host later needs the
#: profile MIME, expose a second resource URI rather than changing this one.)
RESOURCE_MIME = "text/html+skybridge"

#: Server origin used for the widget's required `domain` + CSP connect entry.
#: Mirrors server.py's `_server_url` resolution so the two never diverge.
_SERVER_URL = os.environ.get("MCP_SERVER_URL", "https://yarnnn-mcp-server.onrender.com")

#: Bundles live under api/mcp_server/widgets/dist/ (a mini-web build; see §3).
_WIDGETS_DIR = Path(__file__).resolve().parent.parent / "widgets" / "dist"


@dataclass(frozen=True)
class Widget:
    """A registered, servable UI resource."""

    uri: str
    bundle_filename: str
    invoking: str = "Working…"   # ChatGPT status while the tool runs
    invoked: str = "Done"        # ChatGPT status when it completes
    domain: str = _SERVER_URL
    csp_connect: tuple[str, ...] = field(default_factory=lambda: (_SERVER_URL,))

    @property
    def bundle_path(self) -> Path:
        return _WIDGETS_DIR / self.bundle_filename

    def read_bundle(self) -> str:
        """Read the built HTML/JS bundle. Raises if the build is missing — a
        missing bundle is a deploy error, not a silently-empty resource."""
        return self.bundle_path.read_text(encoding="utf-8")


#: widget id → Widget. Keyed by affordances.Affordance.widget.
WIDGETS: dict[str, Widget] = {
    "trace-timeline": Widget(
        uri="ui://yarnnn/trace-timeline.html",
        bundle_filename="trace-timeline.html",
        invoking="Tracing the revision history…",
        invoked="Traced the revision history",
    ),
    "recall-cards": Widget(
        uri="ui://yarnnn/recall-cards.html",
        bundle_filename="recall-cards.html",
        invoking="Recalling from your memory…",
        invoked="Recalled from your memory",
    ),
    "remember-receipt": Widget(
        uri="ui://yarnnn/remember-receipt.html",
        bundle_filename="remember-receipt.html",
        invoking="Saving to your memory…",
        invoked="Saved to your memory",
    ),
}


def widget_for(widget_id: str) -> Widget | None:
    return WIDGETS.get(widget_id)


def tool_definition_meta(widget_id: str, *, openai_overlay: bool = True) -> dict:
    """`_meta` for a tool DEFINITION (registers the template with the host).

    Always includes the open MCP Apps shape; overlays the additive OpenAI sugar
    by default (it is ignored by non-OpenAI hosts — ADR-372 D2/D4).
    """
    w = WIDGETS[widget_id]
    meta = mcp_apps.tool_definition_meta(w)
    if openai_overlay:
        meta = openai.overlay_definition(meta, w)
    return meta


def tool_response_meta(widget_id: str, *, dialect: str | None = "openai") -> dict:
    """`_meta` for a tool RESPONSE (links this result to its rendered widget).

    Attached only to a widget-rendering host (ADR-372 D4 gate; the caller decides
    via hosts.renders_widgets). `dialect` selects the resource shape (ADR-379 D3b):
        "openai"   → open MCP-Apps shape + the OpenAI overlay (the only wired
                     dialect today; what ChatGPT renders).
        "mcp-apps" → open MCP-Apps shape only (DEFERRED — §4 multi-dialect serving;
                     no rendering host needs it yet).
        None       → open shape only.
    Until a second rendering host exists, callers pass "openai" (the default) and
    the behavior is identical to before — the param is the pre-cut seam, not a
    second code path.
    """
    w = WIDGETS[widget_id]
    meta = mcp_apps.tool_response_meta(w)
    if dialect == "openai":
        meta = openai.overlay_response(meta, w)
    return meta


def served_resource_meta(widget_id: str, *, openai_overlay: bool = True) -> dict:
    """`_meta` for the SERVED RESOURCE.

    LIVE FINDING (2026-06-26): OpenAI's example server attaches the FULL tool
    `_meta` (openai/outputTemplate + widgetAccessible + invocation keys) to the
    served resource's `_meta` — not just domain/CSP. ChatGPT's skybridge appears
    to need these on the RESOURCE to recognize it as a renderable widget and wire
    `window.openai` (the trace widget registered + had data in structuredContent
    but stayed on "Waiting for trace data…" with only domain/csp on the resource).
    So we attach the same overlay here as on the tool definition, PLUS the
    open-spec ui.domain/csp block.
    """
    w = WIDGETS[widget_id]
    meta = mcp_apps.served_resource_meta(w)  # {ui: {domain, csp}}
    if openai_overlay:
        # add openai/outputTemplate + widgetAccessible + invocation keys
        meta = openai.overlay_definition(meta, w)
    return meta
