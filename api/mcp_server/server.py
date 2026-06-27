"""
YARNNN MCP Server — ADR-368 (memory-first surface) + ADR-075 (infrastructure)

Three memory verbs expose YARNNN as a portable memory across every LLM the user
touches. Shaped on the user's own mental model — put in, get out, trace history:

    remember  — save something into memory (writes the operation/ commons)
    recall    — pull what the user already knows about a subject (ranked read)
    trace     — show how a recorded fact changed over time (the revision chain)

Each verb composes kernel primitives SERVER-SIDE into a one-round result, so the
host LLM (claude.ai / ChatGPT / Gemini connectors, which chain only ~3-5 tool
rounds per turn) never has to compose by chaining. The raw kernel primitives
remain available defer-loaded for agentic hosts (Claude Code/Desktop) that do.

Design invariants (ADR-368):
    1. Memory mental model is the surface — not the kernel's verb taxonomy.
    2. Zero YARNNN-internal LLM calls on the serving path.
    3. Writes route to the operation/ commons ONLY (the one root the mcp caller
       may write per CALLER_WRITE_POLICY); the pre-368 five-target enum is gone.
    4. recall RETURNS material; the host LLM explains (retrieval, not synthesis).
    5. Every write carries ADR-162 provenance + fires the integrity wake
       (ADR-310 D2: the seat validates foreign writes against ground-truth).
    6. Operator-visibility: every call emits a session-INDEPENDENT narrative
       entry (ADR-368 D4) so the cross-room operator sees what entered.

Deferred (ADR-368 §6): delegation-from-foreign-LLM (work_on_this as an addressed
wake) — additive when demand + the sync-vs-stream hinge are resolved.

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

from mcp_server.auth import resolve_request_client
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

    A tool with no affordance returns the bare dict (FastMCP serializes it;
    those tools advertise no outputSchema). An affordance-bearing tool ALWAYS
    returns a CallToolResult with both channels populated; the widget `_meta` is
    attached only when the calling host renders widgets (ADR-372 D4 gate, ADR-379
    Host Profile registry). The widget dialect (ADR-379 D3b) is the host's
    declared `widget_dialect` — only "openai" is wired today. Non-widget hosts get
    the same full result, minus the pointer they cannot render.
    """
    affordance = presentation_affordances.affordance_for(tool_name)
    if affordance is None:
        return result
    meta = None
    if presentation_hosts.renders_widgets(client_name):
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
        write_narrative_entry(
            auth.client,
            session_id,
            role="external",
            summary=summary,
            body=body or summary,
            pulse="addressed",
            weight=weight,  # type: ignore[arg-type]
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


# Server URL for OAuth issuer
_server_url = os.environ.get(
    "MCP_SERVER_URL", "https://yarnnn-mcp-server.onrender.com"
)

mcp = FastMCP(
    "yarnnn",
    instructions=(
        "YARNNN is the user's durable, attributed memory — the knowledge they "
        "record persists across sessions, intact and with full provenance. "
        "Three verbs:\n"
        "  • remember — save something worth keeping (a decision, insight, fact,\n"
        "               preference). The write is durable and immediately\n"
        "               available on the next recall.\n"
        "  • recall   — pull what the user already knows about a subject when\n"
        "               they reference something they might track. YARNNN returns\n"
        "               the material; YOU explain it in your own voice.\n"
        "  • trace    — show how a recorded fact changed over time (who changed\n"
        "               it, when, what the change was) — YARNNN's distinguishing\n"
        "               capability, which a plain storage connector cannot show.\n\n"
        "Use these proactively — YARNNN is supposed to be ambient. Don't wait for "
        "the user to ask: recall before reasoning about something they track, and "
        "remember when they share something worth keeping. You are reading and "
        "writing the user's durable memory — not asking YARNNN to do work for you."
    ),
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

    The write is synchronous and durable — immediately available on the next
    recall, attributed to its source. YARNNN's own judgment seat then files the
    memory where it belongs in the workspace and checks it against what it already
    knows (in the background — you don't wait for it). You are saving to the
    user's durable memory; you are not asking YARNNN to do work.

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

    # ADR-376/DP32: the raw observation landed immutably in the inbound/ lane;
    # this wake INVOKES the seat to DERIVE-AND-CITE the understanding into
    # operation/ (a separate citing act, never a rewrite of the raw), and to
    # judge it against ground-truth. Eventually-async; never blocks.
    if written_path and written_path != "(unknown)":
        await mcp_composition.submit_foreign_write_wake(
            auth, written_path=written_path, target="inbound-raw-lane", client_name=client_name,
        )

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

    YARNNN RETURNS the material — ranked excerpts with paths, timestamps, and the
    LLM that originally contributed each. It does NOT write an answer for you:
    you reason over what it returns and explain in your own voice, using the
    conversation as context. Every LLM the user touches sees the same memory, so
    their thinking stays coherent across rooms. If nothing matches, tell them
    YARNNN has nothing recorded yet and answer from your own knowledge.

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
    "remember": {
        "type": "object",
        "properties": {
            "captured": {"type": "boolean", "description": "true when the observation was committed"},
            "written_to": {"type": "string", "description": "the raw-capture path the observation landed at"},
        },
    },
    "recall": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "chunks": {"type": "array", "items": {"type": "object"}, "description": "ranked excerpts of recorded material (path, excerpt, last_updated, domain, source_tag)"},
            "total_matches": {"type": "integer"},
            "returned": {"type": "integer"},
            "explanation": {"type": "string"},
        },
    },
    "trace": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "path": {"type": ["string", "null"]},
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
