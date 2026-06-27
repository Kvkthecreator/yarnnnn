"""Host rendering capability — which connected hosts can render a widget.

ADR-372 (amended 2026-06-27): widget `_meta` is attached per-request to hosts
that can RENDER it, not unconditionally. The original D4 ("attach `_meta`
unconditionally; a text-only host ignores it harmlessly") was falsified live:
claude.ai's connector does NOT ignore a widget pointer — it tries to render the
resource (served `text/html+skybridge` with `openai/*` keys) and fails with
"Unsupported UI resource content format". The text channel stays unconditional
(that is the real ADR-368 invariant); the WIDGET pointer is now gated.

This module is the single, data-shaped seam for that decision. It expresses host
capability as an allow-set keyed on the SAME short client id the rest of the MCP
layer already derives (`mcp_composition.derive_client_name*`). Two design rules
keep it future-proof:

  1. Capability, not vendor branching. The gate asks "can this host render an
     MCP-Apps widget?", expressed as membership in WIDGET_RENDERING_HOSTS. A new
     rendering host opts in with one entry — no tool body changes, no `if
     host == ...` scattered through the server.

  2. Safe default = text. The set is an ALLOW-list. Any host not in it — the
     opaque-client_id claude.ai case, an unidentified UA, a brand-new connector —
     falls back to the universally-safe text path. An unknown host never receives
     a widget pointer it might choke on. This is the inverse of a deny-list and is
     what makes the failure mode "no widget" (always safe) rather than "broken UI".

Why an id and not a live host handshake: MCP has no per-request "I render
widgets" capability bit today. The reliable signal we DO have is the resolved
client id (UA / OAuth-registered client_name → `chatgpt`/`claude.ai`/…). When the
protocol grows a real capability negotiation, this is the one function to swap.
"""

from __future__ import annotations

#: Short client ids (as produced by mcp_composition._normalize_client_id) whose
#: host renders MCP-Apps / OpenAI-Apps widgets today. Membership = "send the
#: widget `_meta`". Everything else gets the text path.
#:
#: ONLY ChatGPT is in here. The ADR-372 widget was validated live on ChatGPT and
#: uses the OpenAI Apps SDK render path (skybridge MIME + openai/* keys). claude.ai
#: is deliberately ABSENT — its connector cannot render that resource (the live
#: failure that motivated this gate). Add a host here only after its widget render
#: is verified end-to-end on that host.
WIDGET_RENDERING_HOSTS: frozenset[str] = frozenset({"chatgpt"})


def renders_widgets(client_name: str | None) -> bool:
    """True if this host should receive widget `_meta` (else: text-only path).

    Allow-list semantics with a text-safe default: an unknown / unidentified
    client (including the opaque-client_id claude.ai case that resolves late or
    not at all) returns False and gets the text path, which every host renders.
    """
    return bool(client_name) and client_name in WIDGET_RENDERING_HOSTS
