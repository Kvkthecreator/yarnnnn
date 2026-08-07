"""
YARNNN MCP Server — ADR-512 (the file is the unit of interop) over ADR-368
(server-side composition) + ADR-075 (infrastructure)

Four verbs expose the user's SHARED, ATTRIBUTED WORKSPACE to every LLM they
touch — one species-blind file contract (ADR-512 D2/D3), served compound:

    open      — read an EXACT file by reference/path (content + attribution +
                recent revisions; the exact-version read, ADR-512 D4)
    remember  — attributed write into the memory region (the inbound/ raw lane)
    recall    — ranked search over the accumulated commons
    trace     — the attributed revision chain of a fact (the differentiator)

Each verb composes kernel primitives SERVER-SIDE into a one-round result, so the
host LLM (claude.ai / ChatGPT / Gemini connectors, which chain only ~3-5 tool
rounds per turn) never has to compose by chaining (ADR-368 Correction 1 — the
binding channel constraint ADR-512 preserves). The raw kernel primitives remain
the stated direction for agentic hosts (defer-loaded; still unbuilt).

Design invariants:
    1. The FILE is the unit on every face (ADR-512 D1); "memory" is a region of
       the file plane, not the surface's identity. Verb ontology never varies by
       principal species (ADR-512 D2) — only the grant/lock-set does.
    2. Zero YARNNN-internal LLM calls on the serving path.
    3. Writes route to the roots CALLER_WRITE_POLICY["mcp"] grants — the
       pre-368 five-target enum is gone; open/recall/trace are pure reads.
    4. recall RETURNS material; the host LLM explains (retrieval, not synthesis).
       open is EXACT; it never falls back to search (the two guarantees stay
       distinct — that is the point of having both).
    5. Every write carries ADR-162 provenance; every call emits a
       session-INDEPENDENT narrative entry (ADR-368 D4) so the cross-room
       operator sees what entered.

Deferred: delegation-from-foreign-LLM (ADR-368 §6); the `share` membership verb
(ADR-465 D5 — ratified as direction, held on the Phase B/C genesis decisions);
rename/removal of remember/recall (ADR-512 §9 — evidence-gated).

Two-layer auth (ADR-075, unchanged):
    Transport: OAuth 2.1 (Claude.ai, ChatGPT) + static bearer (Claude Desktop)
    Data:      Service key + MCP_USER_ID (all queries scoped by user_id)

Canonical framing: docs/features/mcp/README.md + ADR-368 (supersedes ADR-311's
pure-primitive surface; ADR-310 one-moat-two-faces holds).
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import AnyHttpUrl

from mcp_server.auth import resolve_request_client, resolve_request_host_id
from mcp_server.oauth_provider import YarnnnOAuthProvider
from mcp_server.presentation import affordances as presentation_affordances
from mcp_server.presentation import hosts as presentation_hosts
from mcp_server.presentation import registry as presentation_registry
from services import mcp_composition
from services.narrative import (
    find_active_workspace_session,
    write_narrative_entry,
)
from services.primitives.registry import execute_primitive

logger = logging.getLogger(__name__)


# =============================================================================
# ADR-372 — presentation: ONE result envelope; gate only the widget pointer
# =============================================================================
#
# Every affordance-bearing tool returns a CallToolResult carrying BOTH channels:
#   * content           = the full result as JSON text (every host reads it);
#   * structuredContent = the full result dict (model-readable; ALSO what the
#                         advertised outputSchema validates against — see below);
#   * _meta             = the widget linkage, attached ONLY when the calling host
#                         renders widgets (presentation.hosts.renders_widgets).
#
# Why a CallToolResult on BOTH paths (not a bare dict for the text path): the
# tools advertise an outputSchema (_attach_output_schemas). The vendored mcp's
# lowlevel handler validates a tool return against that schema and ERRORS with
# "outputSchema defined but no structured output returned" unless the return is a
# CallToolResult (which short-circuits the check, lowlevel server.py:546) OR a
# bare dict that FastMCP's convert_result turns into structuredContent — but
# convert_result only does that when fn_metadata.output_schema is set, and our
# schemas are attached as an instance attr (the only override path that takes),
# NOT on fn_metadata. So a bare-dict text return reaches the handler as
# unstructured-only → structuredContent=None → the validation error. Returning a
# CallToolResult on every path sidesteps that entirely AND gives every host valid
# structuredContent. (This latent break was masked pre-2026-06-27 because EVERY
# tool always returned a CallToolResult — the unconditional-`_meta` path.)
#
# ADR-372 D4 (AMENDED 2026-06-27) — the widget pointer is no longer unconditional.
# The original D4 ("a text-only host ignores `_meta` harmlessly") was falsified
# live: claude.ai's connector does NOT ignore a widget pointer; it fetches+renders
# the resource (skybridge MIME + openai/* keys, an OpenAI-Apps shape) and fails
# with "Unsupported UI resource content format". So we gate ONLY the widget
# pointer on host capability; the result envelope (both channels) stays
# unconditional — that, not host negotiation, is what keeps the ADR-368 invariant
# true. A non-widget host (claude.ai, any unidentified host) gets the full result
# with NO widget pointer to choke on. See presentation/hosts.py.

def _present(tool_name: str, result: dict, *, client_name: str | None = None):
    """Wrap a tool's result in the standard envelope (ADR-372 D4).

    EVERY tool that advertises an outputSchema returns a CallToolResult with both
    channels populated — affordance or not. The widget `_meta` is attached only
    when the calling host renders widgets (ADR-372 D4 gate, ADR-379 Host Profile
    registry). The widget dialect (ADR-379 D3b) is the host's declared
    `widget_dialect` — only "openai" is wired today. Non-widget hosts get the same
    full result, minus the pointer they cannot render.

    A tool with NEITHER an affordance NOR a declared schema returns the bare dict
    (FastMCP serializes it).

    The affordance check alone is NOT the right gate — that was the 2026-08-03
    live break. The block above explains why a bare dict + a declared schema is a
    hard error ("outputSchema defined but no structured output returned"); the
    original code keyed the envelope on `affordance_for(...)` under the assumption,
    true when written, that affordance-less tools advertise no schema. ADR-512
    then added schemas for `open` / `save` / `share` without affordances, arming
    the documented latent break: all three verbs failed at EVERY MCP host, and
    `save` failed AFTER committing its revision — the caller saw an error for a
    write that landed. The schema is what the protocol validates, so the schema is
    what the envelope must key on.
    """
    affordance = presentation_affordances.affordance_for(tool_name)
    if affordance is None and tool_name not in _OUTPUT_SCHEMAS:
        return result
    meta = None
    if affordance is not None and presentation_hosts.renders_widgets(client_name):
        try:
            dialect = presentation_hosts.widget_dialect(client_name)
            meta = presentation_registry.tool_response_meta(affordance.widget, dialect=dialect)
        except Exception as exc:  # noqa: BLE001 — presentation must never break a tool
            logger.warning("[MCP PRESENT] %s: _meta build failed (%s); text-only", tool_name, exc)
            meta = None
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, indent=2, default=str))],
        structuredContent=result,
        _meta=meta,
    )


# =============================================================================
# ADR-219 Commit 6 — narrative emission for external (MCP) invocations
# =============================================================================
#
# Every foreign LLM tool call against the YARNNN MCP server is an
# invocation per FOUNDATIONS Axiom 9 — Identity = `external:<client>`,
# Trigger = addressed. Per the universal-coverage commitment, each call
# emits exactly one narrative entry into the operator's most-recently-
# active workspace session.
#
# Best-effort: if the operator has no active chat session yet, or the
# helper fails for any reason, the MCP tool result is unaffected. The
# canonical record of MCP work is still in mcp_oauth_* + the substrate
# writes themselves; narrative emission is a second read path.

def _emit_mcp_narrative(
    auth,
    *,
    tool: str,
    weight: str,  # routine | material
    summary: str,
    body: str,
    client_name: str,
    extra_metadata: Optional[dict] = None,
) -> None:
    """Best-effort MCP → narrative emission. Never raises.

    ADR-368 D4 (operator-visibility, Hole A): the trace must be
    SESSION-INDEPENDENT. The whole point of the interop face is the cross-room
    user — who writes to YARNNN from claude.ai/ChatGPT with NO YARNNN tab open.
    The pre-ADR-368 emitter returned early when no session was active, leaving
    the modal foreign write silent in the feed. We now fall back to the
    operator's DAILY session (get-or-create), so the entry is waiting whenever
    they return. The durable record (authored_by on the revision) was always
    correct; this closes the in-the-moment awareness gap so the operator has
    parity with the seat on what entered from outside.
    """
    try:
        session_id = find_active_workspace_session(auth.client, auth.user_id)
        if not session_id:
            session_id = _ensure_daily_session(auth)
        if not session_id:
            logger.debug(
                "[MCP NARRATIVE] no session resolvable for user=%s; skipping %s emission",
                auth.user_id[:8] if auth.user_id else "?",
                tool,
            )
            return
        meta = {"mcp_tool": tool, "mcp_client": client_name}
        if extra_metadata:
            meta.update(extra_metadata)
        # Actor identity (2026-06-30): stamp the ADR-209 `authored_by` so the
        # feed/notifications/chat rows show WHICH external LLM acted by name —
        # "ChatGPT (via MCP)" / "Claude (via MCP)" — instead of a flat "system".
        # `client_name` is the canonical lowercase host slug (chatgpt | claude.ai
        # | gemini | …) the FE attribution map keys on; matches the durable
        # `authored_by` already written on the revision (one identity, both
        # layers). "unknown" degrades to "Unknown (via MCP)" — still honest.
        write_narrative_entry(
            auth.client,
            session_id,
            role="external",
            summary=summary,
            body=body or summary,
            pulse="addressed",
            weight=weight,  # type: ignore[arg-type]
            authored_by=f"yarnnn:mcp:{client_name}",
            extra_metadata=meta,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[MCP NARRATIVE] emission failed (tool=%s): %s",
            tool,
            exc,
        )


@asynccontextmanager
async def lifespan(server: FastMCP):
    """Server startup/shutdown.

    ADR-310 D4: identity is resolved PER REQUEST from the OAuth token
    (resolve_request_client), not built once at boot. There is no longer a
    boot-time auth singleton — that pinned every request to one user.
    """
    logger.info("[MCP Server] Ready — per-request identity (ADR-310)")
    yield {}
    logger.info("[MCP Server] Shutting down")


# =============================================================================
# ADR-379 — the DISCOVERY + RESOURCE-READ host gate (the second leak)
# =============================================================================
#
# The ADR-372 response gate (_present) withholds the widget pointer from the tool
# RESPONSE for a non-widget host. But a host also discovers widgets BEFORE any
# response runs — at `tools/list` (the tool def's `openai/outputTemplate`) and at
# `resources/list` / `resources/read` (the served widget resource itself,
# skybridge MIME + openai/* keys). claude.ai followed the tool-def template to the
# resource, fetched it, and failed with "Unsupported UI resource content format"
# (live, 2026-06-27) — the leak this subclass closes.
#
# We subclass FastMCP and host-gate the two discovery surfaces + the read surface:
#   * list_tools     → strip widget `_meta` from tool defs for a non-widget host.
#   * read_resource  → for a non-widget host, never serve a widget bundle as a
#                      renderable resource (downgrade MIME to text/html, strip
#                      openai/* + ui.resourceUri so nothing tries to render).
# The host is resolved per-request (auth.resolve_request_host_id); an unidentified
# host is text-safe by default — the same fail-closed posture as the response gate.
# A widget host (chatgpt) is unaffected: full openai/* metadata flows through.

class HostGatedFastMCP(FastMCP):
    """FastMCP that strips widget advertisement for hosts that can't render it.

    Closes the discovery/read leak ADR-372's response gate didn't cover (ADR-379).
    A host name appears nowhere here — the gate is `hosts.renders_widgets`, applied
    to the resolved request host; the presentation layer owns what "strip" means
    (`registry.strip_widget_meta`). Kernel boundary preserved (ADR-222/372 D5).
    """

    async def list_tools(self):  # type: ignore[override]
        tools = await super().list_tools()
        try:
            host = resolve_request_host_id()
            if presentation_hosts.renders_widgets(host):
                return tools  # widget host (chatgpt) — leave the openai/* binding
            for t in tools:
                if getattr(t, "meta", None):
                    t.meta = presentation_registry.strip_widget_meta(t.meta)
        except Exception as exc:  # noqa: BLE001 — the gate must never break discovery
            logger.warning("[MCP GATE] list_tools host-gate failed (%s); serving as-is", exc)
        return tools

    async def read_resource(self, uri):  # type: ignore[override]
        contents = await super().read_resource(uri)
        try:
            if str(uri) not in presentation_registry.WIDGET_URIS:
                return contents  # not a widget resource — untouched
            host = resolve_request_host_id()
            if presentation_hosts.renders_widgets(host):
                return contents  # widget host — serve skybridge + openai/* as-is
            # non-widget host: hand back a plain, non-renderable text/html resource
            # so the host shows nothing instead of erroring on an unrenderable widget.
            from mcp.server.lowlevel.helper_types import ReadResourceContents
            gated = []
            for c in contents:
                gated.append(ReadResourceContents(
                    content=c.content,
                    mime_type=presentation_registry.TEXT_RESOURCE_MIME,
                    meta=presentation_registry.strip_widget_meta(getattr(c, "meta", None)),
                ))
            return gated
        except Exception as exc:  # noqa: BLE001 — the gate must never break a read
            logger.warning("[MCP GATE] read_resource host-gate failed (%s); serving as-is", exc)
            return contents


# Server URL for OAuth issuer
_server_url = os.environ.get(
    "MCP_SERVER_URL", "https://yarnnn-mcp-server.onrender.com"
)

# =============================================================================
# The interop verb roster (ADR-533 D2) — the SINGLE source of the verb table
# =============================================================================
# The connector self-description used to hand-write both the verb COUNT and the
# verb LIST. It said "Four verbs:" and then listed SIX — drift that shipped to
# every connected host from the moment ADR-512 added `save` + `share`.
#
# The lane already solved this class and said why: its tool line is
# `" · ".join(lane_tool_names())` — "so the prose can never claim a surface the
# model wasn't handed (the Scout bug's prose half)" (lane_runner.py).
#
# So: the roster is DATA, the prose is DERIVED. A new verb is a row here plus its
# @mcp.tool — never an edit to a sentence that counts things. There is no count
# in the prose at all; a count is a hand-maintained duplicate of len().
#
# `test_adr533_participant_contract.py` asserts this roster and the registered
# @mcp.tool set are the same set — so a verb can never ship announced-but-absent
# (or absent-but-announced), which is the drift this roster replaces.
_INTEROP_VERBS: tuple[tuple[str, str], ...] = (
    (
        "open",
        "read an EXACT file when you have its reference (a yarnnn://workspace/… "
        "handle or a workspace-relative path, e.g. one the user pasted). Returns "
        "the current content + who last changed it + recent attributed "
        "revisions. Exact means exact: open never guesses — use recall to search.",
    ),
    (
        "remember",
        "save something worth keeping (a decision, insight, fact, preference). "
        "The write is durable, signed as yours, and immediately available on the "
        "next recall — from ANY AI the user works with, not just you.",
    ),
    (
        "recall",
        "pull what the workspace already holds about a subject when the user "
        "references something they track. YARNNN returns the material + a "
        "`confidence` signal; YOU explain it in your own voice. On "
        "confidence='ambiguous' (several matches, none dominant) ASK which they mean.",
    ),
    (
        "trace",
        "show how a file or recorded fact changed over time (who changed it, "
        "when, what the change was) — the attributed provenance a plain storage "
        "connector cannot show.",
    ),
    (
        "save",
        "write a document back as an attributed revision, signed as you. "
        "Read-before-write: pass base_revision from open; a stale_write means "
        "someone changed it since — re-open, merge, save again. Omit "
        "base_revision only to create. Cite what you built on with derived_from.",
    ),
    (
        "share",
        "mint a link for a file (or the workspace) when the user wants someone "
        "else in: 'member' grants full access, 'viewer' is read-only. You relay "
        "the link; whoever opens it sees the work and who made it, no account needed.",
    ),
)


def _build_interop_instructions() -> str:
    """Compose the connector self-description (ADR-533 D1 + D2 + D6).

    The commons-contract clauses are the SAME kernel constants the lane frame
    composes (`services/workspace_paths.py`) — a participant is taught one
    contract whether it is a lane in the webapp or ChatGPT across an OAuth
    token. This function never restates a clause inline; it composes them.

    D6 — what deliberately does NOT port: the workspace MANDATE head (the lane
    injects 40 lines of it). The commons contract is HOW THE WORKSPACE WORKS —
    kernel-universal, therefore shared. The mandate is WHAT THIS WORKSPACE IS
    FOR — workspace-specific intent that would leave the system into a
    third-party host's context window on every connection, for a benefit no verb
    requires. Also not ported: lane posture overlays, member/model interpolation.
    """
    from services.workspace_paths import (
        PARTICIPANT_ATTRIBUTION_RULE,
        PARTICIPANT_CITATION_RULE,
        PARTICIPANT_COMMONS_CONTRACT,
        PARTICIPANT_FILESYSTEM_MODEL,
        PARTICIPANT_FORMAT_DISCIPLINE,
        PARTICIPANT_READ_BEFORE_WRITE,
    )

    # D2: the verb table is derived from the roster — no count, no hand-written list.
    verbs = "\n".join(
        f"  • {name:<9}— {desc}" for name, desc in _INTEROP_VERBS
    )

    return (
        "YARNNN is the user's shared, attributed workspace — the files they and "
        "their team work on with AI, where every change is signed by whoever "
        "made it (human or AI) and nothing is lost. You are a principal in that "
        "workspace, acting under your own grant.\n\n"
        f"{PARTICIPANT_COMMONS_CONTRACT}\n\n"
        f"- {PARTICIPANT_READ_BEFORE_WRITE} Use open (exact) or recall (search).\n"
        f"- Every write is signed as you, {PARTICIPANT_ATTRIBUTION_RULE}\n"
        f"- {PARTICIPANT_CITATION_RULE}\n"
        f"- {PARTICIPANT_FORMAT_DISCIPLINE}\n\n"
        f"{PARTICIPANT_FILESYSTEM_MODEL}\n\n"
        "## Your verbs\n"
        f"{verbs}\n\n"
        "Use these proactively — the workspace is supposed to be ambient. If the "
        "user pastes a yarnnn reference or names a specific document, open it "
        "before reasoning about it; recall before reasoning about something they "
        "track; remember when they conclude something worth keeping. You are "
        "reading and writing the user's shared workspace — not asking YARNNN to "
        "do work for you."
    )


mcp = HostGatedFastMCP(
    "yarnnn",
    # ADR-512: the connector's identity is the user's SHARED, ATTRIBUTED
    # WORKSPACE — files that humans and AIs work on together, every change
    # signed by whoever made it — not "a memory feature".
    # ADR-533: the etiquette half is composed from the SAME kernel constants the
    # lane frame uses, and the verb table is derived from `_INTEROP_VERBS`.
    instructions=_build_interop_instructions(),
    lifespan=lifespan,
    # OAuth 2.1 provider — Claude.ai connectors + ChatGPT developer mode
    auth_server_provider=YarnnnOAuthProvider(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(_server_url),
        resource_server_url=AnyHttpUrl(_server_url),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["read"],
            default_scopes=["read"],
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=["read"],
    ),
    # Render/Cloudflare reverse proxy changes Host; security handled by OAuth + edge
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
    # ADR-370 Slice 2: serve the MCP protocol at ROOT, not the SDK default
    # `/mcp`, so the connector URL is the clean, compact `https://mcp.yarnnn.com`
    # (no path). Eliminates the bare-domain-404 failure mode at the source — a
    # user who types the domain without a path now connects, instead of getting
    # "no MCP server found at the provided URL".
    #
    # No OAuth collision (verified against mcp 1.28.0 streamable_http_app, the
    # vendored SDK): create_auth_routes() registers /authorize, /token,
    # /register, /.well-known/* as explicit Routes FIRST, and the streamable
    # endpoint is appended AFTER as an EXACT-match `Route(streamable_http_path)`
    # (not a prefix Mount). Starlette matches first/exact, so the OAuth routes
    # always win their paths and only the bare `/` JSON-RPC POST hits the
    # protocol. Default was `/mcp`; this makes it `/`.
    streamable_http_path="/",
)


# =============================================================================
# ADR-533 §13 — declare the tool list VOLATILE (`capabilities.tools.listChanged`)
# =============================================================================
# THE DEFECT THIS FIXES: we were telling every host our tool surface never
# changes, so every host cached it forever — correctly.
#
# The chain, read from the pinned mcp 1.28.0 wheel:
#   1. `lowlevel/server.py` NotificationOptions.__init__ defaults
#      `tools_changed: bool = False`.
#   2. `tools_capability = ToolsCapability(listChanged=notification_options.tools_changed)`.
#   3. FastMCP calls `self._mcp_server.create_initialization_options()` with NO
#      arguments (fastmcp/server.py:759,848; streamable_http_manager.py:200,302),
#      so it always got the all-False default.
# ⇒ every `initialize` advertised `capabilities.tools.listChanged: false`.
#
# Measured consequence (2026-08-07): claude.ai held a manifest from after Aug 3
# (six verbs, but no `derived_from` on `save`); ChatGPT held one from on/before
# Aug 2 (three verbs — pre-`open`/`save`/`share`). Same server, same deploy, two
# frozen vintages. Neither host was misbehaving: a host told the list is
# immutable is ENTITLED to cache it forever.
#
# WHY OVERRIDE HERE: all four SDK call sites (both transports) invoke this method
# arg-less on the LOWLEVEL server, so this single override covers every path —
# stdio, SSE, and the two streamable-HTTP paths we actually serve. Patching a
# transport instead would leave the others lying.
#
# ⚠ WHAT THIS DOES *NOT* DO (ADR-533 §13 D2 — do not oversell it): it cannot
# refresh a host that has ALREADY cached. Our surface changes only on DEPLOY, and
# a deploy replaces the process and drops every live session — there is no
# session alive to notify about the change that just happened. `listChanged` is
# built for servers whose tools change mid-session (runtime registration); ours
# do not. This makes us HONEST going forward and lets a compliant host re-check
# on its next connect. Getting a stuck host unstuck is a human step — see
# `docs/features/mcp/CONNECTING.md` §"The surface changed".
#
# Deliberately NOT paired with an emit-on-startup `send_tool_list_changed()`: a
# host that just ran `initialize` has the current list already, so firing at
# startup would re-deliver what it just fetched — motion that looks like a fix
# and changes nothing.
_base_create_initialization_options = mcp._mcp_server.create_initialization_options


def _create_initialization_options_with_volatile_tools(
    notification_options=None, experimental_capabilities=None, **kwargs
):
    """Declare `tools.listChanged: true` unless a caller states otherwise."""
    from mcp.server.lowlevel.server import NotificationOptions

    if notification_options is None:
        notification_options = NotificationOptions(tools_changed=True)
    return _base_create_initialization_options(
        notification_options, experimental_capabilities, **kwargs
    )


mcp._mcp_server.create_initialization_options = (
    _create_initialization_options_with_volatile_tools
)


# =============================================================================
# ADR-372 — widget resources (the `ui://` rendering surface)
# =============================================================================
# Each presentation widget is served as an MCP resource at its `ui://` URI. A
# rendering host (ChatGPT / MCP Apps) fetches the bundle named by a tool result's
# `_meta.ui.resourceUri` and renders it in a sandboxed iframe. The served
# resource carries `_meta.ui` (domain + CSP) that host submission requires. The
# bundle is read from disk at serve time — a missing build is a deploy error, not
# a silent empty resource.

@mcp.resource(
    "ui://yarnnn/trace-timeline.html",
    mime_type=presentation_registry.RESOURCE_MIME,
    meta=presentation_registry.served_resource_meta("trace-timeline"),
)
def trace_timeline_widget() -> str:
    """Serve the trace-timeline widget bundle (ADR-372 §7)."""
    return presentation_registry.widget_for("trace-timeline").read_bundle()


@mcp.resource(
    "ui://yarnnn/recall-cards.html",
    mime_type=presentation_registry.RESOURCE_MIME,
    meta=presentation_registry.served_resource_meta("recall-cards"),
)
def recall_cards_widget() -> str:
    """Serve the recall-cards widget bundle (ADR-372)."""
    return presentation_registry.widget_for("recall-cards").read_bundle()


@mcp.resource(
    "ui://yarnnn/remember-receipt.html",
    mime_type=presentation_registry.RESOURCE_MIME,
    meta=presentation_registry.served_resource_meta("remember-receipt"),
)
def remember_receipt_widget() -> str:
    """Serve the remember-receipt widget bundle (ADR-372)."""
    return presentation_registry.widget_for("remember-receipt").read_bundle()


@mcp.resource(
    "ui://yarnnn/save-receipt.html",
    mime_type=presentation_registry.RESOURCE_MIME,
    meta=presentation_registry.served_resource_meta("save-receipt"),
)
def save_receipt_widget() -> str:
    """Serve the save-receipt widget bundle (ADR-533 D4)."""
    return presentation_registry.widget_for("save-receipt").read_bundle()


@mcp.resource(
    "ui://yarnnn/file-header.html",
    mime_type=presentation_registry.RESOURCE_MIME,
    meta=presentation_registry.served_resource_meta("file-header"),
)
def file_header_widget() -> str:
    """Serve the file-header widget bundle (ADR-533 D4)."""
    return presentation_registry.widget_for("file-header").read_bundle()


# =============================================================================
# The memory-first interop surface — remember / recall / trace (ADR-368)
# =============================================================================
# Three verbs shaped on the user's memory mental model: put in, get out, trace
# history. Each composes kernel primitives SERVER-SIDE into a one-round result —
# the host LLM (claude.ai / ChatGPT / Gemini) never has to chain. The raw kernel
# primitives remain available defer-loaded for agentic hosts that do chain.


@mcp.tool(
    meta=presentation_registry.tool_definition_meta("remember-receipt"),
    # ADR-372 submission-readiness: action annotations are an App-review
    # requirement (and incorrect ones are a named rejection reason). remember is a
    # WRITE but NON-destructive — it CAPTURES an attributed raw observation
    # (append/new file), never deletes or overwrites destructively. openWorld
    # because it reaches the user's evolving substrate.
    annotations=ToolAnnotations(
        title="Remember",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def remember(
    ctx: Context,
    content: str,
    about: Optional[str] = None,
) -> dict:
    """Save something into the user's durable YARNNN memory so it persists for later.

    Call this whenever the user shares something worth keeping — a decision, an
    insight, a fact, a preference, an observation about something they track.
    Don't wait for them to say "remember this": if they reach a conclusion or
    state something they'll want later, save it.

    Pass the thing to keep as `content` — their words, or a faithful summary of
    what you both concluded. Be concise but preserve the specific claim. If it's
    clearly about a subject (a company, person, project, topic), pass that as
    `about`.

    The write is synchronous and durable — the moment this returns the memory is
    stored, attributed, and ALREADY RETRIEVABLE (`status: "remembered"`): a
    `recall` (or `trace`) on the same subject will return THIS exact memory
    immediately, by key, with no waiting. That retrievable-now guarantee is the
    floor and it never depends on anything async. YARNNN's judgment seat THEN does
    a separate pass — files the memory alongside related understanding and checks
    it against what it already knows — and that ENRICHMENT is asynchronous (a short
    moment later). So you can tell the user it's saved and they can recall it now;
    just don't promise it's already been organized-with or validated by the seat
    ("saved and recallable — it'll be filed and checked against the rest in a
    moment"). You are saving to the user's durable memory; you are not asking
    YARNNN to do work.

    Args:
        content: The thing to remember. Required.
        about: Optional subject hint (company, person, project, topic).
    """
    auth = resolve_request_client()
    content = (content or "").strip()
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )

    if not content:
        _emit_mcp_narrative(
            auth, tool="remember", weight="housekeeping",
            summary=f"{client_name} remember rejected (empty content)",
            body="empty content — nothing written",
            client_name=client_name, extra_metadata={"outcome": "rejected"},
        )
        return _present("remember", {"success": False, "error": "empty_content", "message": "content is required"}, client_name=client_name)

    # ADR-376 / DP32: the dump is an attributed RAW observation — it lands in the
    # inbound/mcp/{client}/ raw lane (outside the topology cut, never rewritten);
    # the seat derives the understanding into operation/ via the placement wake.
    stamped = mcp_composition.stamp_provenance(content, client_name, user_context=about)
    result = await mcp_composition.dispatch_remember_this(
        auth=auth, stamped_text=stamped, about=about, client_name=client_name,
    )

    if not result.get("success"):
        _emit_mcp_narrative(
            auth, tool="remember", weight="routine",
            summary=f"{client_name} remember failed",
            body=str(result.get("message") or "remember dispatch failed"),
            client_name=client_name,
            extra_metadata={"outcome": "failed", "error": result.get("error")},
        )
        return _present("remember", {
            "success": False,
            "error": result.get("error", "write_failed"),
            "message": result.get("message", "remember dispatch failed"),
        }, client_name=client_name)

    written_path = result.get("filename") or result.get("path") or "(unknown)"

    # ADR-376/DP32 (retire the eager derive wake, 2026-07-09): the raw observation
    # landed immutably in the inbound/ lane, attributed, and tagged
    # revision_kind='observation' (mcp_composition.dispatch_remember_this) — the
    # `retain + attribute` half of the invariant, carried by the column per
    # ADR-423/384, not by a wake. The `cite` half — a derived-and-cited act into
    # operation/ — is NOT eager code: ADR-423 §7 / the Files-model note §5 demote
    # the derive step to "reserved, not the justification" (no live code produced
    # a derivation deterministically; the wake was a prompt-only contract that
    # mostly logged "nothing to derive" at ~$0.22/fire). We do NOT fire a
    # per-write seat wake here. A real derive step, when it ships, re-attaches
    # deliberately as its own mechanism.

    _emit_mcp_narrative(
        auth, tool="remember", weight="material",
        summary=f"{client_name} saved to memory",
        body=(
            f"written_to: {written_path}\n"
            f"about: {about or '(none)'}\n"
            f"content: {content[:480]}{'…' if len(content) > 480 else ''}"
        ),
        client_name=client_name,
        extra_metadata={"written_to": written_path, "outcome": "success"},
    )
    # ADR-372 D4: rich hosts render the remember-receipt widget; text path intact.
    return _present("remember", {
        "success": True,
        "written_to": written_path,
        "provenance": {
            "source": f"mcp:{client_name}",
            "date": _today_iso(),
            "original_context": (about or content[:80]),
        },
        # ADR-368 D5: the seat will file this where it belongs + validate it.
        "captured": True,
        # Honest-state (2026-06-30): "remembered" — not "captured". THE FLOOR
        # (mcp_composition: store-by-key/fetch-by-key) guarantees the memory is
        # durable AND retrievable by subject the instant this returns — a recall on
        # the same subject hits THIS exact file deterministically, no seat/embedding.
        # "captured" undersold that (it reads as "received, awaiting processing");
        # "remembered" states the retrievable-now floor honestly. The seat's
        # derive/place/judge pass is still ASYNC and additive — the host should set
        # "saved and recallable now; filed-and-checked in a moment", and must NOT
        # promise the seat has already judged/organized it. ("placed" would be the
        # false over-promise; "remembered" is the true floor.)
        "status": "remembered",
    }, client_name=client_name)


@mcp.tool(
    meta=presentation_registry.tool_definition_meta("recall-cards"),
    # recall is a pure READ — it returns ranked excerpts, writes nothing. The
    # DESTRUCTIVE label seen in dev mode was a MISSING annotation defaulting
    # conservatively; readOnlyHint corrects it (and removes the permission
    # friction). openWorld because the substrate evolves between calls.
    annotations=ToolAnnotations(
        title="Recall",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def recall(
    ctx: Context,
    subject: str,
    question: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Pull what the user already knows about a subject from their YARNNN memory.

    Call this whenever the user references something that might live in their
    accumulated YARNNN memory — a person, company, market, project, or topic
    they track — and you need the underlying material to reason well. Don't wait
    to be asked: if they mention something they might have recorded, recall it
    first and weave it into your answer.

    Pass the subject as `subject`. Optionally pass a `question` to focus the
    retrieval, or a `domain` to narrow it.

    YARNNN RETURNS the material — ranked excerpts with paths, timestamps, the LLM
    that originally contributed each, and a `confidence` signal. It does NOT write
    an answer for you, and it does NOT decide whether to clarify: YOU reason over
    what it returns and explain in your own voice, using the conversation as
    context. Every LLM the user touches sees the same memory, so their thinking
    stays coherent across rooms.

    The `confidence` field is ALWAYS present (even on a miss) and uses the same
    4-value scale as `trace`'s `resolution` — use it to decide how to respond:
      • "high"      — a clear, dominant match (or an exact subject hit). Use it.
      • "ambiguous" — several recorded items match and none dominates. Do NOT
                      silently pick the first; surface the candidates (in `chunks`)
                      and ASK the user which they mean. This is the clarify case.
      • "weak"      — only loose matches below the confidence bar. A lead, not an
                      answer; answer from your own knowledge or ask the user to be
                      specific.
      • "none"      — NOTHING recorded on this subject (a true miss; `chunks` empty).
                      The strongest "nothing here" signal — answer from your own
                      knowledge. (Distinct from "weak", which is a real but shaky hit.)
    (YARNNN never clarifies or guesses itself — it's the memory; you're the one in
    the conversation.)

    Args:
        subject: What to recall (entity, topic, keyword). Required.
        question: Optional focusing question.
        domain: Optional domain filter.
        limit: Max excerpts (default 10, max 30).
    """
    auth = resolve_request_client()
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_recall(
        auth=auth, subject=subject, question=question, domain=domain, limit=limit,
    )
    n = result.get("returned", 0)
    _emit_mcp_narrative(
        auth, tool="recall", weight="routine",
        summary=(
            f"{client_name} recalled {n} excerpt(s) for {subject!r}"
            if n else f"{client_name} recalled {subject!r} (nothing found)"
        ),
        body=f"subject: {subject}\nquestion: {question or '(none)'}\nreturned: {n}",
        client_name=client_name,
        extra_metadata={"subject": subject, "returned": n},
    )
    # ADR-372 D4: only a widget host gets the recall-cards `_meta`; text path intact.
    return _present("recall", result, client_name=client_name)


@mcp.tool(
    meta=presentation_registry.tool_definition_meta("trace-timeline"),
    # trace is a pure READ — it returns the authored revision chain, writes
    # nothing. Same correction as recall.
    annotations=ToolAnnotations(
        title="Trace",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def trace(
    ctx: Context,
    subject: str,
    limit: int = 10,
):
    """Show how the user's recorded thinking on a subject changed over time.

    Call this when the user asks about the HISTORY of something they track —
    "when did I decide that," "how has my view on X changed," "who added this,"
    "what did this used to say." This is YARNNN's distinguishing capability: it
    returns the authored revision chain of a fact — who changed it, when, and
    what the change was — which a plain storage connector cannot show.

    Pass the subject as `subject`. YARNNN resolves it to the most relevant
    recorded material and returns its revision history, newest first. Reason over
    the chain and narrate the evolution in your own voice.

    Check the `resolution` field before narrating — ALWAYS present, same 4-value
    scale as `recall`'s `confidence` (the lower three mean the same thing). A wrong
    trace reads as authoritative, so don't narrate a confident "here's how your
    thinking evolved" over the wrong file:
      • "exact"     — the subject named a single file; this IS its history. Narrate.
                      (trace's name for the confident value, ≡ recall's "high".)
      • "ambiguous" — the subject matched several files; this is the closest, not a
                      certain one. CONFIRM with the user before narrating.
      • "weak"      — only a single loose mention-match (not a name-match). A lead;
                      confirm before narrating it as the subject's history.
      • "none"      — NOTHING recorded on this subject (path is null, history empty).
                      Say so; don't narrate.

    On a rich-render host (ChatGPT / MCP Apps) the revision chain ALSO renders as
    an interactive timeline widget (ADR-372) — but you STILL narrate the evolution
    in prose: the widget is additive, not a replacement for your explanation. On a
    text-only host you get the full chain as text, exactly as before.

    Args:
        subject: What to trace the history of. Required.
        limit: Max revisions (default 10, max 30).
    """
    auth = resolve_request_client()
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_trace(auth=auth, subject=subject, limit=limit)
    n = result.get("returned", 0)
    _emit_mcp_narrative(
        auth, tool="trace", weight="routine",
        summary=(
            f"{client_name} traced {n} revision(s) for {subject!r}"
            if n else f"{client_name} traced {subject!r} (no history)"
        ),
        body=f"subject: {subject}\npath: {result.get('path') or '(none)'}\nreturned: {n}",
        client_name=client_name,
        extra_metadata={"subject": subject, "returned": n},
    )
    # ADR-372 D4: attach the widget `_meta` only for a widget host (renders the
    # timeline); the full result stays in the text channel for every host.
    return _present("trace", result, client_name=client_name)


@mcp.tool(
    # The registered tool NAME is `open` (the member-facing verb, ADR-512 D4);
    # the Python symbol is `open_file` so the module never shadows the builtin.
    name="open",
    # open is a pure READ of one exact file — content + attribution + recent
    # revisions, composed server-side in one round (ADR-512 D4).
    # ADR-533 D4: the file-header widget renders the file's IDENTITY (whose
    # version, when, how many revisions) — never its content, which is the
    # host's to render.
    meta=presentation_registry.tool_definition_meta("file-header"),
    annotations=ToolAnnotations(
        title="Open",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def open_file(
    ctx: Context,
    reference: str,
    revisions: int = 5,
) -> dict:
    """Open an EXACT file from the user's yarnnn workspace by its reference.

    Call this when you hold a reference to a specific file — a
    `yarnnn://workspace/…` handle (the user may paste one, e.g. from Studio's
    "Copy AI reference"), a workspace-relative path like `operation/reports/q3.md`,
    or a `/workspace/…` absolute path. This is the exact-version read: you get
    THIS file's current content, who last changed it, and its recent attributed
    revisions — so you and the user are looking at the same version, not a copy.

    `open` never searches or guesses: an unknown path returns `found: false`.
    When you only know the subject (not the path), use `recall`; for the full
    revision chain with diffs, use `trace`. Large files return truncated with
    `truncated: true`.

    Args:
        reference: The file reference — yarnnn://workspace/{path}, /workspace/{path},
            or a bare workspace-relative path. Required.
        revisions: How many recent revisions to summarize (default 5, max 10).
    """
    auth = resolve_request_client()
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_open(
        auth=auth, reference=reference, revisions=revisions,
    )
    found = bool(result.get("found"))
    _emit_mcp_narrative(
        auth, tool="open", weight="routine",
        summary=(
            f"{client_name} opened {result.get('path') or reference!r}"
            if found else f"{client_name} tried to open {reference!r} (not found)"
        ),
        body=(
            f"reference: {reference}\npath: {result.get('path') or '(unresolved)'}\n"
            f"found: {found}"
        ),
        client_name=client_name,
        extra_metadata={"reference": reference, "found": found},
    )
    return _present("open", result, client_name=client_name)


@mcp.tool(
    # ADR-512 §8a — the write half of the exact-version guarantee. Overwrites
    # are never destructive in the ledger sense (every prior version stays on
    # the attributed chain, ADR-209) and blind overwrites are refused by the
    # base_revision contract, so destructiveHint stays False honestly.
    # ADR-533 D4: the save-receipt widget exists for the CONFLICT state —
    # stale_write/base_required carry who holds the head and what to do next,
    # which a chat host renders as a paragraph the user skims past.
    meta=presentation_registry.tool_definition_meta("save-receipt"),
    annotations=ToolAnnotations(
        title="Save",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def save(
    ctx: Context,
    reference: str,
    content: str,
    base_revision: Optional[str] = None,
    message: Optional[str] = None,
    derived_from: Optional[list[str]] = None,
) -> dict:
    """Save content to an EXACT file in the user's yarnnn workspace, as an attributed revision.

    Call this when the user asks you to update a specific document — "apply
    that edit to the proposal", "save this version back". Pass the same
    reference `open` takes (yarnnn://workspace/… or a workspace-relative path)
    and the FULL new content (this is an overwrite, not a patch).

    THE CONTRACT — read before write: for an existing file you MUST pass
    `base_revision` = the head revision id you got from `open` (history[0].
    revision_id). If someone changed the file since, you get `stale_write`
    with WHO changed it — re-open, merge their change with yours in your own
    reasoning, and save again with the new base. Never retry a stale save
    with the same content unexamined. Omit `base_revision` only to CREATE a
    new file.

    CITE WHAT YOU BUILT ON: if this content was made FROM other workspace files
    — a document you opened and rewrote, sources you synthesized, a reference
    you worked from — pass their references as `derived_from`. The workspace
    uses that edge to show what was made from what, and to warn someone before
    they delete a file yours depends on. An uncited derivation arrives as an
    orphan; cite it and it joins the record.

    Your write lands signed as you in the workspace ledger — the user and
    their team see exactly what you changed, beside every human change. Use
    `remember` for notes/observations; `save` is for named documents.

    Args:
        reference: The file — yarnnn://workspace/{path} or workspace-relative path.
        content: The full new content. Required, non-empty.
        base_revision: The head revision id from open (required for existing files).
        message: Optional one-line description of the change.
        derived_from: Optional references of the source file(s) this was made
            from (same grammar as `reference`). Pass whenever you author from
            sources you read.
    """
    auth = resolve_request_client()
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_save(
        auth=auth, reference=reference, content=content,
        base_revision=base_revision, message=message,
        derived_from=derived_from,
    )
    outcome = "saved" if result.get("success") else (result.get("error") or "failed")
    _emit_mcp_narrative(
        auth, tool="save", weight="material" if result.get("success") else "routine",
        summary=f"{client_name} {outcome}: {result.get('path') or reference}",
        body=(
            f"reference: {reference}\noutcome: {outcome}\n"
            f"message: {message or '(none)'}\nrevision: {result.get('revision_id') or '(n/a)'}"
        ),
        client_name=client_name,
        extra_metadata={"outcome": outcome, "revision_id": result.get("revision_id")},
    )
    return _present("save", result, client_name=client_name)


@mcp.tool(
    # ADR-465 D5 (ratified via ADR-512 §7; built with ADR-513) — the membership
    # verb beside the content verbs: the commons ABI's access half. Mints a
    # share row and returns the link for the host to RELAY (yarnnn sends
    # nothing outbound — ADR-404 honesty line: models come IN).
    annotations=ToolAnnotations(
        title="Share",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def share(
    ctx: Context,
    reference: Optional[str] = None,
    access: str = "member",
) -> dict:
    """Create a share link for the user's yarnnn workspace (or one exact file in it).

    Call this when the user asks to share their work — "share this with my
    team", "send this doc to Alex", "make a link for this". Pass the file's
    reference (a yarnnn://workspace/… handle or workspace-relative path) to
    share that artifact; omit it to share the workspace itself.

    Returns a link. YOU relay it — in this conversation, for the user to send.
    Whoever opens the link SEES the artifact and who changed it (no account
    needed); joining the workspace requires signing in.

    `access` picks what accepting grants (the user's choice, not yours — ask if
    unclear): "member" = full access to work in the workspace (the default);
    "viewer" = read-only (they see the document and its history, and can
    change nothing).

    Args:
        reference: Optional file to share — yarnnn://workspace/{path},
            /workspace/{path}, or a bare workspace-relative path.
        access: "member" (full access, default) | "viewer" (read-only).
    """
    auth = resolve_request_client()
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )

    if access not in ("member", "viewer"):
        return _present("share", {
            "success": False, "error": "invalid_access",
            "message": "access must be 'member' (full) or 'viewer' (read-only)",
        }, client_name=client_name)

    artifact_rel = None
    if reference:
        artifact_rel = mcp_composition.parse_file_reference(reference)
        if artifact_rel is None:
            return _present("share", {
                "success": False, "error": "invalid_reference",
                "message": (
                    "Not a yarnnn file reference. Pass a workspace-relative path "
                    "or a yarnnn://workspace/… handle, or omit it to share the workspace."
                ),
            }, client_name=client_name)

    try:
        from services.deep_links import app_url
        from services.supabase import principal_reaches_workspace, resolve_workspace_for_principal
        from services.workspace_shares import ShareError, assert_may_mint_share, create_share

        workspace_id = resolve_workspace_for_principal(auth.user_id)
        if not workspace_id:
            return _present("share", {
                "success": False, "error": "no_workspace",
                "message": "No workspace resolved for this user.",
            }, client_name=client_name)
        # ADR-517 D3 — gate parity with the cockpit origin (species-blind):
        # the reach check this origin always should have had, then the same
        # mint-authority gate (write-holders mint; viewers never; the
        # workspace dial can tighten to owner-only).
        if not principal_reaches_workspace(auth.user_id, workspace_id):
            return _present("share", {
                "success": False, "error": "no_grant",
                "message": "You do not have a grant to this workspace.",
            }, client_name=client_name)
        assert_may_mint_share(auth.user_id, workspace_id)
        row = create_share(
            workspace_id=workspace_id,
            shared_by=auth.user_id,
            artifact_path=artifact_rel,
            role=access,
        )
        link = f"{app_url()}/s/{row['token']}"
    except ShareError as exc:
        return _present("share", {
            "success": False, "error": exc.code, "message": str(exc),
        }, client_name=client_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MCP] share mint failed: %s", exc)
        return _present("share", {
            "success": False, "error": "share_failed", "message": str(exc),
        }, client_name=client_name)

    # A membership act is material to the operator (ADR-368 D4 visibility).
    _emit_mcp_narrative(
        auth, tool="share", weight="material",
        summary=f"{client_name} minted a {access} share link"
        + (f" for {artifact_rel}" if artifact_rel else " for the workspace"),
        body=f"artifact: {artifact_rel or '(workspace)'}\naccess: {access}\nshare_id: {row.get('id')}",
        client_name=client_name,
        extra_metadata={"artifact": artifact_rel, "access": access, "share_id": row.get("id")},
    )
    return _present("share", {
        "success": True,
        "share_link": link,
        "access": access,
        "artifact": artifact_rel,
        "explanation": (
            f"A {('read-only' if access == 'viewer' else 'full-access')} share link. "
            "Relay it to the user — anyone who opens it sees the "
            + ("document and who changed it" if artifact_rel else "workspace invitation")
            + "; joining requires sign-in. The user can revoke it from Files."
        ),
    }, client_name=client_name)


# =============================================================================
# ADR-372 submission-readiness — explicit output schemas
# =============================================================================
# The App-review surface flags "OUTPUT SCHEMA RECOMMENDED" on tools without one;
# a declared outputSchema lets the host validate structuredContent and (for
# trace) makes the widget's render contract explicit. We declare them as data and
# attach post-registration: FastMCP derives a schema from the return annotation
# only with structured_output=True, which (a) fails on trace's nested history
# TypedDict in this Pydantic and (b) is bypassed entirely because trace returns a
# CallToolResult. Setting `output_schema` directly is the uniform, low-risk path.

_REVISION_SCHEMA = {
    "type": "object",
    "properties": {
        "authored_by": {"type": ["string", "null"], "description": "who authored this revision (operator | reviewer:<id> | yarnnn:mcp:<client> | agent:<slug> | system:<actor>)"},
        "when": {"type": ["string", "null"], "description": "ISO timestamp of the revision"},
        "change": {"type": ["string", "null"], "description": "the revision's change message"},
        "revision_id": {"type": ["string", "null"]},
        "diff": {"type": ["string", "null"], "description": "unified-diff vs the predecessor revision; null for the oldest"},
    },
}

_OUTPUT_SCHEMAS = {
    "save": {
        "type": "object",
        "properties": {
            "reference": {"type": "string", "description": "the canonical handle of the saved file"},
            "path": {"type": ["string", "null"]},
            "created": {"type": "boolean", "description": "true when this save created a new file"},
            "revision_id": {"type": ["string", "null"], "description": "the NEW head — pass as base_revision on a follow-up save"},
            "current_head": {"type": "object", "description": "on stale_write/base_required: who holds the head you must read first (revision_id, authored_by, when)"},
            "explanation": {"type": "string"},
        },
    },
    "share": {
        "type": "object",
        "properties": {
            "share_link": {"type": "string", "description": "the /s/{token} capability link — relay it to the user; reading needs no account, joining does"},
            "access": {"type": "string", "enum": ["member", "viewer"], "description": "what accepting grants: member = full access; viewer = read-only"},
            "artifact": {"type": ["string", "null"], "description": "the shared file (workspace-relative), or null for a workspace share"},
            "explanation": {"type": "string"},
        },
    },
    "open": {
        "type": "object",
        "properties": {
            "found": {"type": "boolean", "description": "false = no file at that exact reference (open never searches — use recall)"},
            "reference": {"type": "string", "description": "the canonical yarnnn://workspace/… handle for this file (ADR-512 D5)"},
            "path": {"type": ["string", "null"], "description": "the ledger's absolute path (/workspace/…)"},
            "content": {"type": ["string", "null"], "description": "the file's exact current content (capped; see truncated)"},
            "truncated": {"type": "boolean", "description": "true when content was cut at the cap"},
            "authored_by": {"type": ["string", "null"], "description": "who made the most recent revision"},
            "last_updated": {"type": ["string", "null"]},
            "history": {"type": "array", "items": _REVISION_SCHEMA, "description": "recent revisions, newest first (no diffs — trace has those)"},
            "explanation": {"type": "string"},
        },
    },
    "remember": {
        "type": "object",
        "properties": {
            "captured": {"type": "boolean", "description": "true when the observation was committed"},
            "status": {"type": "string", "enum": ["remembered"], "description": "remembered = stored + durable + retrievable-by-subject NOW (a recall on the same subject hits this memory deterministically); the seat's derive/place/judge enrichment is async (a moment later)"},
            "written_to": {"type": "string", "description": "the raw-capture path the observation landed at"},
        },
    },
    "recall": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "chunks": {"type": "array", "items": {"type": "object"}, "description": "ranked excerpts of recorded material (path, excerpt, last_updated, domain, source_tag, similarity)"},
            "total_matches": {"type": "integer"},
            "returned": {"type": "integer"},
            "confidence": {"type": "string", "enum": ["high", "ambiguous", "weak", "none"], "description": "ALWAYS present (even on a miss). Shared scale with trace.resolution: high=use it; ambiguous=ask which the user means; weak=loose lead only; none=nothing recorded (true miss)"},
            "explanation": {"type": "string"},
        },
    },
    "trace": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "path": {"type": ["string", "null"]},
            "resolution": {"type": "string", "enum": ["exact", "ambiguous", "weak", "none"], "description": "ALWAYS present. Shared scale with recall.confidence: exact=narrate (≡high); ambiguous=confirm first; weak=loose lead, confirm; none=nothing recorded (true miss)"},
            "history": {"type": "array", "items": _REVISION_SCHEMA, "description": "revision chain, newest first"},
            "returned": {"type": "integer"},
            "explanation": {"type": "string"},
        },
    },
}


def _attach_output_schemas() -> None:
    """Attach explicit output schemas to the registered tools (best-effort)."""
    for name, schema in _OUTPUT_SCHEMAS.items():
        try:
            tool = mcp._tool_manager.get_tool(name)
            if tool is not None:
                tool.output_schema = schema
        except Exception as exc:  # noqa: BLE001 — a schema attach must never break boot
            logger.debug("[MCP] output-schema attach failed for %s: %s", name, exc)


_attach_output_schemas()


def _ensure_daily_session(auth) -> Optional[str]:
    """Find-or-create the operator's workspace session (ADR-368 D4).

    A foreign-LLM narrative entry must land in a session the operator sees on
    /chat open even when none was active at write time. We do this with plain
    table ops against the CURRENT chat_sessions schema rather than the
    `get_or_create_chat_session` RPC: that RPC's body still references the
    dropped `project_id`/`deliverable_id` columns and errors on any call (a
    pre-existing latent drift, out of scope here). Keeping this helper
    RPC-independent means the visibility fix doesn't inherit that breakage.

    Resolution: most-recent thinking_partner session for the user (any status),
    else create a fresh active one. Mirrors the daily-scope intent (one rolling
    session the operator returns to) without the broken RPC.
    """
    try:
        existing = (
            auth.client.table("chat_sessions")
            .select("id")
            .eq("user_id", auth.user_id)
            .eq("session_type", "thinking_partner")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]["id"]
        created = (
            auth.client.table("chat_sessions")
            .insert({
                "user_id": auth.user_id,
                "session_type": "thinking_partner",
                "status": "active",
            })
            .execute()
        )
        if created.data:
            return created.data[0]["id"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MCP NARRATIVE] daily-session ensure failed: %s", exc)
    return None


def _today_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
