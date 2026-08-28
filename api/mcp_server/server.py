"""
YARNNN MCP Server — ADR-543 (the file-native interop surface) over ADR-512
(the file is the unit of interop) + ADR-075 (infrastructure)

Six verbs expose the user's SHARED, ATTRIBUTED WORKSPACE to every LLM they
touch — one species-blind file contract (ADR-512 D2/D3), each verb a binding of
a kernel verb, served compound:

    open      — read an EXACT file by reference/path (content + attribution +
                recent revisions; the exact-version read, ADR-512 D4)
    list      — enumerate the files under a folder (paths + who last changed
                each; the tree's front door, ADR-543 D2)
    search    — find files by meaning (ranked paths + excerpts + confidence)
    save      — attributed write to a named file (CAS via base_revision)
    history   — the attributed revision chain of one exact file (the
                differentiator)
    share     — mint a member/viewer link (the grant act, ADR-465 D1)

Each verb composes kernel primitives SERVER-SIDE into a one-round result, so the
host LLM (claude.ai / ChatGPT / Gemini connectors, which chain only ~3-5 tool
rounds per turn) never has to compose by chaining (ADR-368 Correction 1 — the
binding channel constraint ADR-512 + ADR-543 preserve).

Design invariants:
    1. The FILE is the unit on every face (ADR-512 D1) and the ONLY ontology
       (ADR-543 D1 — the remember/recall/trace memory surface is retired IN
       FULL; no verb presents an object the kernel contract does not have).
       Verb ontology never varies by principal species (ADR-512 D2) — only the
       grant/lock-set does.
    2. Zero YARNNN-internal LLM calls on the serving path.
    3. Writes route through `save` under CALLER_WRITE_POLICY["mcp"];
       open/list/search/history are pure reads.
    4. search RETURNS material; the host LLM explains (retrieval, not
       synthesis). open/history are EXACT; they never fall back to search
       (the guarantees stay distinct — that is the point of having them).
    5. Every call emits a session-INDEPENDENT narrative entry (ADR-368 D4) so
       the cross-room operator sees what entered.

Deferred: delegation-from-foreign-LLM (ADR-368 §6).

Two-layer auth (ADR-075, unchanged):
    Transport: OAuth 2.1 (Claude.ai, ChatGPT) + static bearer (Claude Desktop)
    Data:      Service key + MCP_USER_ID (all queries scoped by user_id)

Canonical framing: docs/features/mcp/README.md + ADR-543 (supersedes ADR-368's
memory-first surface; ADR-310 one-moat-two-faces holds).
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

from mcp_server import auth as mcp_auth
from mcp_server.auth import (
    ScopeDenied,
    resolve_request_client,
    resolve_request_host_id,
)
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

    async def call_tool(self, name, arguments):  # type: ignore[override]
        """Compose a scope refusal instead of letting it escape as a fault.

        ⭐ ADR-563 put the scope CHECK at the one door every verb opens
        (`resolve_request_client(verb=…)` → `assert_scope`), for the stated
        reason that "a guard a call site can forget is not a guard". The
        REFUSAL was never given the same treatment: `ScopeDenied` was imported
        here and caught nowhere (one occurrence in this file, zero uses), so an
        under-scoped connection got a protocol-level exception rather than an
        answer — on the authorization surface, the one place a refusal most
        needs to read cleanly. It also rendered a raw Python list literal
        (`this connection holds ['(none)']`).

        The handler belongs HERE for the same reason the check does: this is the
        single funnel every tool call passes through, so a verb added tomorrow
        is covered without remembering anything. Ten try/excepts in ten bodies
        would be the shape ADR-563 already rejected.
        """
        try:
            return await super().call_tool(name, arguments)
        except ScopeDenied as exc:
            held = ", ".join(exc.held) if exc.held else "no file scopes"
            logger.info(
                "[MCP SCOPE] refused verb=%s required=%s held=%s",
                exc.verb, exc.required, exc.held,
            )
            return {
                "success": False,
                "error": "scope_denied",
                "message": (
                    f"This connection is not authorized to {exc.verb}. It holds "
                    f"{held}, and {exc.verb} needs the '{exc.required}' scope. "
                    "Tell the user to re-authorize the yarnnn connector and "
                    "grant it — you cannot widen your own access from here."
                ),
                "verb": exc.verb,
                "required_scope": exc.required,
                "held_scopes": list(exc.held),
            }

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
        "whoami",
        "name WHERE YOU ARE STANDING — which workspace this connection is bound "
        "to, whether that is the one the operator chose, who your writes will be "
        "signed as, and which of these verbs your token actually authorizes. "
        "Call it once at the start of real work, and ALWAYS before writing "
        "somewhere the user assumed: a shared workspace has more than one "
        "commons, and the reference grammar cannot tell them apart.",
    ),
    (
        "open",
        "read an EXACT file when you have its reference (a yarnnn://workspace/… "
        "handle or a workspace-relative path, e.g. one the user pasted). Returns "
        "the current content + who last changed it + recent attributed "
        "revisions. Exact means exact: open never guesses — use search or list.",
    ),
    (
        "list",
        "enumerate the files under a folder — every path with its size, who "
        "last changed it, and when. No reference lists the whole workspace; "
        "pass `since` (ISO timestamp) for the change feed — what moved since "
        "you were last here. Use it to see what exists before guessing.",
    ),
    (
        "search",
        "find files by meaning when you don't hold a path. Returns ranked "
        "paths + excerpts + a `confidence` signal; YOU explain the material in "
        "your own voice. On confidence='ambiguous' (several matches, none "
        "dominant) ASK which the user means. Then open the file for exact content.",
    ),
    (
        "save",
        "write a WHOLE document as an attributed revision, signed as you — "
        "creating, or rewriting wholesale. Read-before-write: pass "
        "base_revision from open; a stale_write means someone changed it since "
        "— re-open, merge, save again. Cite sources with derived_from. For a "
        "targeted change to an existing file, prefer edit.",
    ),
    (
        "edit",
        "change PART of a file: pass the exact text to replace and its "
        "replacement. Only the change travels — content you never read is "
        "never at risk, so this is the right verb for files open returned "
        "truncated, and for concurrent work (edits to different regions don't "
        "conflict). Fails loudly if the anchor is missing or ambiguous.",
    ),
    (
        "delete",
        "remove a file — or a WHOLE FOLDER — from the live workspace. Point it "
        "at a folder and everything under it goes, as one restorable unit: say "
        "so before you do. Nothing is lost either way: an attributed tombstone "
        "records who and why, the revision chain keeps the content, and history "
        "still walks it. Use it to tidy — superseded scratch, dead duplicates, "
        "stale artifacts that would mislead the next reader.",
    ),
    (
        "move",
        "move or rename a file — or a WHOLE FOLDER, with every file under it — "
        "to a new path as one attributed operation. Refuses to overwrite an "
        "existing destination (delete it first, by intent). The old path keeps "
        "a tombstone pointing at the new one.",
    ),
    (
        "history",
        "show how one EXACT file changed over time (who changed it, when, what "
        "the change was, with diffs and cited sources) — the attributed "
        "provenance a plain storage connector cannot show. Takes the same "
        "reference as open; when you only know the topic, search first.",
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
    requires. Also not ported: member/model interpolation.

    ADR-617 D2 AMENDS that list. "Lane posture overlays" was one item covering
    two different things, and the split matters: a posture's TURN STATE (the
    live outline, an inlined `_string.yaml`, the design-system roster) is
    workspace-specific and stays withheld — it is also turn-scoped and would
    cost a DB read per call. A posture's FORMAT GRAMMAR is not intent at all;
    it is the same class as PARTICIPANT_FILESYSTEM_MODEL, which always ported.
    The artifact citation rule crosses on that basis, as a kernel constant both
    surfaces compose — never by calling a lane posture builder from here.
    """
    from services.workspace_paths import (
        PARTICIPANT_ARTIFACT_CITATION_RULE,
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
        f"- {PARTICIPANT_READ_BEFORE_WRITE} Use open (exact), list (enumerate), "
        "or search (by meaning).\n"
        f"- Every write is signed as you, {PARTICIPANT_ATTRIBUTION_RULE}\n"
        f"- {PARTICIPANT_CITATION_RULE}\n"
        f"- {PARTICIPANT_FORMAT_DISCIPLINE}\n\n"
        f"{PARTICIPANT_FILESYSTEM_MODEL}\n\n"
        # ADR-617 D2 — amends ADR-533 D6. Withheld until 2026-08-28 as a "lane
        # posture overlay"; it is not intent, it is how an artifact works, and a
        # surface that can `save` one must be taught it.
        f"## Documents that cite other files\n{PARTICIPANT_ARTIFACT_CITATION_RULE}\n\n"
        "## Your verbs\n"
        f"{verbs}\n\n"
        "Use these proactively — the workspace is supposed to be ambient. When "
        "the user asks WHICH workspace they are connected to — or anything else "
        "about this connection — answer with whoami, not by listing files: a "
        "listing shows what is in a workspace, never which one it is, and the "
        "reference grammar is identical in all of them. If the "
        "user pastes a yarnnn reference or names a specific document, open it "
        "before reasoning about it; search before reasoning about something they "
        "track. When the user concludes something worth keeping and no document "
        "is in hand, save it — by meaning like any participant; a conversational "
        "observation with no better home goes under Downloads. You are reading "
        "and writing the user's shared workspace — not asking YARNNN to do work "
        "for you."
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
        # ADR-563: the scope field is no longer decorative. `valid_scopes` was
        # the single string "read" while the surface bound nine verbs including
        # delete and share — a token LABELLED read could delete a file and mint
        # a member grant. The tiers are additive (files:read ⊂ files:write ⊂
        # files:share); enforcement is per-verb in `auth.assert_scope`, reached
        # through the one chokepoint every handler already calls.
        #
        # `required_scopes` stays EMPTY on purpose: requiring a scope at the
        # transport would reject every pre-563 token (all carry legacy "read")
        # before a handler could apply the containment rule that keeps them
        # working. The authorization decision belongs at the verb, not the door.
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=mcp_auth.VALID_SCOPES,
            default_scopes=mcp_auth.DEFAULT_SCOPES,
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=[],
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
    "ui://yarnnn/history-timeline.html",
    mime_type=presentation_registry.RESOURCE_MIME,
    meta=presentation_registry.served_resource_meta("history-timeline"),
)
def history_timeline_widget() -> str:
    """Serve the history-timeline widget bundle (ADR-372 §7, renamed ADR-543)."""
    return presentation_registry.widget_for("history-timeline").read_bundle()


@mcp.resource(
    "ui://yarnnn/search-results.html",
    mime_type=presentation_registry.RESOURCE_MIME,
    meta=presentation_registry.served_resource_meta("search-results"),
)
def search_results_widget() -> str:
    """Serve the search-results widget bundle (ADR-372, renamed ADR-543)."""
    return presentation_registry.widget_for("search-results").read_bundle()


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
# The file-native interop surface — open / list / search / save / history /
# share (ADR-543)
# =============================================================================
# Six verbs, each a binding of a kernel verb (ADR-512 D3). Each composes kernel
# primitives SERVER-SIDE into a one-round result — the host LLM (claude.ai /
# ChatGPT / Gemini) never has to chain.


@mcp.tool(
    # ADR-584 D1 — the tenth verb, and the only one whose subject is the
    # CONNECTION rather than a file. Before it, a connected principal could not
    # learn which workspace it was bound to: the workspace lived as a bare UUID
    # on the auth, was used purely as a query filter, and was discarded before
    # every response. Chosen over a `workspace` key on every envelope (which
    # would tax all eight file verbs forever to answer a question asked once per
    # session) and over a per-verb `workspace` argument (rejected in ADR-573 §2:
    # the MODEL becomes the chooser, and a wrong guess writes to the wrong
    # commons with full attribution).
    name="whoami",
    annotations=ToolAnnotations(
        title="Who am I",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def whoami(ctx: Context) -> dict:
    """Name WHERE THIS CONNECTION IS STANDING in the user's yarnnn workspace.

    Call this at the start of real work, and ALWAYS before writing somewhere the
    user assumed — a person can reach more than one workspace, and the
    `yarnnn://workspace/…` grammar is the same in all of them, so no path or
    handle can tell you which commons you are in.

    Returns the workspace's name (the operator chose it at consent), whether that
    is the workspace this connection was BOUND to or a fallback, the attribution
    your writes will carry, and exactly which verbs your token authorizes.

    Read `binding` before writing:
      • "chosen"   — you are where the operator chose. Proceed.
      • "default"  — no explicit choice on this connection; you are in their
                     default workspace.
      • "fallback" — the bound workspace is UNREACHABLE and this is NOT where the
                     operator chose. Writes still succeed and are attributed —
                     SAY SO before writing, rather than filing into the wrong
                     commons silently.
      • "unresolved" — resolution FAILED and `workspace_id` is null. Do not
                     write: say the connection could not name its workspace and
                     ask the user to re-check it.

    An unnamed workspace returns `workspace: null` with `workspace_named: false`
    — describe it by its address, and don't invent a name for it.
    """
    auth = resolve_request_client(verb="whoami")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_whoami(
        auth=auth,
        client_name=client_name,
        binding=mcp_auth.request_binding(auth.user_id),
        scopes=mcp_auth.token_scopes(),
    )
    # No narrative entry: `whoami` reads no substrate and changes nothing —
    # logging an orientation call as workspace activity would fill the operator's
    # timeline with noise that carries no attribution story.
    return _present("whoami", result, client_name=client_name)


@mcp.tool(
    # ADR-543 D2 — the kernel `list` verb, bound at last (ADR-512 D3 named it;
    # the surface never shipped it, so external principals reconstructed the
    # tree from search hits — the 2026-08-10 external-audit finding).
    # list is a pure READ — enumeration with attribution, writes nothing.
    name="list",
    annotations=ToolAnnotations(
        title="List",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def list_files(
    ctx: Context,
    reference: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> dict:
    """List the files under a folder in the user's yarnnn workspace.

    Call this to see what exists — before guessing a path, when the user asks
    "what's in my workspace / in that folder", or to orient yourself at the
    start of real work. Pass a folder reference (a workspace-relative path like
    `Documents/reports`, or a yarnnn://workspace/… handle); omit it to list the
    entire workspace tree.

    THE CHANGE FEED: pass `since` (ISO timestamp) to get only the files whose
    last change landed after that moment — "what moved since I was last here"
    in one call. Returning to a workspace after time away? list(since=…) first.

    Returns every matching file — path, size, who last changed it, and when.
    The listing is real enumeration, not inference: what it returns is what
    exists. When `truncated` is true, continue from `next_offset`. Use `open`
    on any returned path for exact content, and `search` when you're after
    meaning rather than structure.

    Args:
        reference: Optional folder — workspace-relative path or
            yarnnn://workspace/{path}. Omit to list the whole workspace.
        since: Optional ISO timestamp — only files changed after this moment.
        limit: Max files per page (default and cap 500).
        offset: Page start in path order (use next_offset from a truncated call).
    """
    auth = resolve_request_client(verb="list")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_list(
        auth=auth, reference=reference, since=since, limit=limit, offset=offset,
    )
    n = result.get("count", 0)
    where = result.get("path") or "(workspace)"
    _emit_mcp_narrative(
        auth, tool="list", weight="routine",
        summary=f"{client_name} listed {n} file(s) under {where}"
        + (f" since {since}" if since else ""),
        body=f"reference: {reference or '(workspace root)'}\nsince: {since or '(none)'}\ncount: {n}",
        client_name=client_name,
        extra_metadata={"reference": reference, "count": n, "since": since},
    )
    return _present("list", result, client_name=client_name)


@mcp.tool(
    meta=presentation_registry.tool_definition_meta("search-results"),
    # search is a pure READ — it returns ranked paths + excerpts, writes
    # nothing. openWorld because the substrate evolves between calls.
    annotations=ToolAnnotations(
        title="Search",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def search(
    ctx: Context,
    query: str,
    limit: int = 10,
) -> dict:
    """Search the user's yarnnn workspace by meaning.

    Call this when you're after a file you don't hold a path for — the user
    references a topic, project, person, or decision that may live in the
    workspace. Don't wait to be asked: if they mention something the workspace
    might hold, search it first and weave what you find into your answer.

    YARNNN RETURNS the material — ranked results with paths, excerpts,
    timestamps, and a `confidence` signal. It does NOT write an answer for
    you, and it does NOT decide whether to clarify: YOU reason over what it
    returns and explain in your own voice. Every result's path is `open`-able
    for the exact current content; `search` returns leads, `open` returns truth.

    The `confidence` field is ALWAYS present (even on a miss) — use it to
    decide how to respond:
      • "high"      — a clear, dominant match. Use it.
      • "ambiguous" — several files match and none dominates. Do NOT silently
                      pick the first; surface the candidates (in `results`) and
                      ASK the user which they mean. This is the clarify case.
      • "weak"      — only loose matches below the confidence bar. A lead, not
                      an answer; answer from your own knowledge or ask the user
                      to be specific.
      • "none"      — NOTHING matched (a true miss; `results` empty). The
                      strongest "nothing here" signal — answer from your own
                      knowledge, or `list` to see what exists.

    Args:
        query: What to find (topic, entity, keywords). Required.
        limit: Max results (default 10, max 30).
    """
    auth = resolve_request_client(verb="search")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_search(auth=auth, query=query, limit=limit)
    n = result.get("returned", 0)
    _emit_mcp_narrative(
        auth, tool="search", weight="routine",
        summary=(
            f"{client_name} searched {query!r} — {n} result(s)"
            if n else f"{client_name} searched {query!r} (nothing found)"
        ),
        body=f"query: {query}\nreturned: {n}",
        client_name=client_name,
        extra_metadata={"query": query, "returned": n},
    )
    # ADR-372 D4: only a widget host gets the search-results `_meta`; text path intact.
    return _present("search", result, client_name=client_name)


@mcp.tool(
    meta=presentation_registry.tool_definition_meta("history-timeline"),
    # history is a pure READ — it returns the authored revision chain, writes
    # nothing.
    annotations=ToolAnnotations(
        title="History",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def history(
    ctx: Context,
    reference: str,
    limit: int = 10,
):
    """Show how one EXACT file in the user's yarnnn workspace changed over time.

    Call this when the user asks about a file's history — "when did I decide
    that," "how has this document changed," "who added this," "what did this
    used to say." This is YARNNN's distinguishing capability: the authored
    revision chain — who changed the file, when, and what the change was (with
    per-revision diffs, and the chains of any cited sources it was made from)
    — which a plain storage connector cannot show.

    Pass the same reference `open` takes (yarnnn://workspace/… handle,
    /workspace/… absolute, or a workspace-relative path). `history` is exact:
    an unknown path returns `found: false` — when you only know the topic,
    `search` first, then history the path you found. Reason over the chain and
    narrate the evolution in your own voice.

    On a rich-render host (ChatGPT / MCP Apps) the revision chain ALSO renders
    as an interactive timeline widget (ADR-372) — but you STILL narrate the
    evolution in prose: the widget is additive, not a replacement for your
    explanation. On a text-only host you get the full chain as text.

    Args:
        reference: The file — yarnnn://workspace/{path}, /workspace/{path},
            or a bare workspace-relative path. Required.
        limit: Max revisions (default 10, max 30).
    """
    auth = resolve_request_client(verb="history")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_history(auth=auth, reference=reference, limit=limit)
    n = result.get("returned", 0)
    _emit_mcp_narrative(
        auth, tool="history", weight="routine",
        summary=(
            f"{client_name} read {n} revision(s) of {result.get('path') or reference!r}"
            if n else f"{client_name} read history of {reference!r} (no revisions)"
        ),
        body=f"reference: {reference}\npath: {result.get('path') or '(none)'}\nreturned: {n}",
        client_name=client_name,
        extra_metadata={"reference": reference, "returned": n},
    )
    # ADR-372 D4: attach the widget `_meta` only for a widget host (renders the
    # timeline); the full result stays in the text channel for every host.
    return _present("history", result, client_name=client_name)


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
    offset: int = 0,
) -> dict:
    """Open an EXACT file from the user's yarnnn workspace by its reference.

    Call this when you hold a reference to a specific file — a
    `yarnnn://workspace/…` handle (the user may paste one, e.g. from Studio's
    "Copy AI reference"), a workspace-relative path like `Documents/reports/q3.md`,
    or a `/workspace/…` absolute path. This is the exact-version read: you get
    THIS file's current content, who last changed it, and its recent attributed
    revisions — so you and the user are looking at the same version, not a copy.

    `open` never searches or guesses: an unknown path returns `found: false`.
    When you only know the topic (not the path), use `search`; to see what
    exists, use `list`; for the full revision chain with diffs, use `history`.

    A large file is PAGED, not lost: `truncated: true` comes with `next_offset`
    — call again with `offset=next_offset` to read on. `content_chars` is the
    length of the READABLE VIEW, so you always know how much remains to read.
    Read to the end before summarizing a long file.

    ⚠️ Reading to the end is NOT the same as holding the file. A Studio
    artifact's machine-composed stylesheets are elided from the view, so
    `stored_chars` exceeds `content_chars` and no amount of paging closes the
    gap. **`complete_for_write` is the only field that answers "may I `save`
    this back".** When it is false, use `edit` — its anchors match the stored
    bytes and are unaffected by elision.

    `citations` lists the workspace files an artifact CITES. Their content is
    projected from the source when the document renders, so a cited element is
    usually EMPTY in what you read here — that is a working citation, not
    missing content. Open a cited file to learn what it shows, and never write
    content inside a citation: it is overwritten on the next render.

    Args:
        reference: The file reference — yarnnn://workspace/{path}, /workspace/{path},
            or a bare workspace-relative path. Required.
        revisions: How many recent revisions to summarize (default 5, max 10).
        offset: Character offset to read from (default 0). Pass `next_offset`
            from a truncated call to continue.
    """
    auth = resolve_request_client(verb="open")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_open(
        auth=auth, reference=reference, revisions=revisions, offset=offset,
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
    confirm_full_replace: bool = False,
) -> dict:
    """Save content to an EXACT file in the user's yarnnn workspace, as an attributed revision.

    Call this to CREATE a file or REWRITE one wholesale. Pass the same
    reference `open` takes (yarnnn://workspace/… or a workspace-relative path)
    and the FULL new content (this is an overwrite, not a patch). For a
    targeted change to an existing file — especially one `open` returned
    truncated — use `edit` instead: it sends only the change, so content you
    never read is never at risk. A save over a file larger than open's cap is
    refused unless you pass confirm_full_replace=true (stated intent).

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
    their team see exactly what you changed, beside every human change. `save`
    also captures conversational conclusions worth keeping: write them by
    meaning like any participant — an observation with no better home goes
    under Downloads.

    Args:
        reference: The file — yarnnn://workspace/{path} or workspace-relative path.
        content: The full new content. Required, non-empty.
        base_revision: The head revision id from open (required for existing files).
        message: Optional one-line description of the change.
        derived_from: Optional references of the source file(s) this was made
            from (same grammar as `reference`). Pass whenever you author from
            sources you read.
        confirm_full_replace: Required true to wholesale-overwrite a file
            larger than open's content cap (stated intent; prefer `edit`).
    """
    auth = resolve_request_client(verb="save")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_save(
        auth=auth, reference=reference, content=content,
        base_revision=base_revision, message=message,
        derived_from=derived_from,
        confirm_full_replace=confirm_full_replace,
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
    # ADR-545 D1 — the anchored write (binds ADR-337 EditFile). Only the change
    # travels; the anchor is the precondition (no base_revision — a stale view
    # fails loudly as no-match, and the kernel's head-read CAS closes the
    # apply-window race per ADR-406 D4). Non-destructive in the ledger sense:
    # one attributed revision, prior content on the chain.
    annotations=ToolAnnotations(
        title="Edit",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def edit(
    ctx: Context,
    reference: str,
    old: str,
    new: str,
    replace_all: bool = False,
    message: Optional[str] = None,
) -> dict:
    """Change PART of a file in the user's yarnnn workspace — an anchored edit.

    Call this for any targeted change to an existing file: fixing a line,
    updating a section, appending an entry. Pass the exact current text as
    `old` (verbatim, including whitespace — include surrounding context to
    make it unique) and the replacement as `new`. Only the change travels:
    content you never read is never at risk, which makes this the REQUIRED
    verb for files `open` returned truncated, and the right one when several
    principals work the same file (edits to different regions don't conflict).

    Fails loudly, never guesses: `old_string_not_found` means your view is
    stale or the anchor isn't verbatim — re-open and re-anchor;
    `old_string_not_unique` means add more context or pass replace_all=true.
    The edit lands as one attributed revision signed as you; use `save` only
    to create a file or rewrite one wholesale.

    Args:
        reference: The file — same grammar as open. Required.
        old: Exact text to replace (verbatim; unique unless replace_all).
        new: Replacement text.
        replace_all: Replace every occurrence (default false).
        message: Optional one-line description of the change.
    """
    auth = resolve_request_client(verb="edit")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_edit(
        auth=auth, reference=reference, old=old, new=new,
        replace_all=replace_all, message=message,
    )
    outcome = "edited" if result.get("success") else (result.get("error") or "failed")
    _emit_mcp_narrative(
        auth, tool="edit", weight="material" if result.get("success") else "routine",
        summary=f"{client_name} {outcome}: {result.get('path') or reference}",
        body=(
            f"reference: {reference}\noutcome: {outcome}\n"
            f"replacements: {result.get('replacements') or 0}\n"
            f"message: {message or '(none)'}"
        ),
        client_name=client_name,
        extra_metadata={"outcome": outcome, "replacements": result.get("replacements")},
    )
    return _present("edit", result, client_name=client_name)


@mcp.tool(
    # ADR-545 D2 — binds ADR-337 DeleteFile. A VIEW change, not information
    # loss (attributed tombstone; chain retained; restore is revert-as-write,
    # ADR-209 D7). destructiveHint=True is the honest annotation for a host's
    # permission surface: the file leaves the live tree, even though the
    # ledger keeps everything.
    annotations=ToolAnnotations(
        title="Delete",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def delete(
    ctx: Context,
    reference: str,
    message: Optional[str] = None,
) -> dict:
    """Remove a file — or a whole folder — from the live yarnnn workspace.

    The file goes to Trash: it is a PLACE, not an erasure — the revision chain
    is retained and the user can put it back.

    ONE VERB, TWO GRAINS. `reference` may name a file or a FOLDER, and the
    workspace resolves which — you don't have to know. Naming a folder deletes
    its whole subtree, every file under it, as one restorable unit. That is a
    much larger act than deleting a file: say what you are about to sweep, and
    for anything beyond obvious scratch, confirm with the user first. If only
    some of it should go, `list` the folder and delete the files by name.

    Call this when something would mislead the next reader: superseded scratch,
    a dead duplicate after a move, a stale artifact. Nothing is lost — an
    attributed tombstone records who removed it and why, the revision chain
    keeps the content, and `history` still walks it; the user can restore
    from the workspace. Governance-protected paths refuse, same as save — on a
    folder they are reported in `locked` rather than silently skipped, so say
    "19 moved to Trash · 2 are managed by the system and stayed" rather than
    claiming a clean sweep. A folder larger than one gesture should move (500
    items) is refused outright rather than half-performed.

    Say why in `message` — the tombstone is the next reader's explanation.

    Args:
        reference: The file OR folder — same grammar as open. Required.
        message: Why this is being removed (recorded on the tombstone).
    """
    auth = resolve_request_client(verb="delete")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_delete(
        auth=auth, reference=reference, message=message,
    )
    outcome = "deleted" if result.get("success") else (result.get("error") or "failed")
    _emit_mcp_narrative(
        auth, tool="delete", weight="material" if result.get("success") else "routine",
        summary=f"{client_name} {outcome}: {result.get('path') or reference}",
        body=(
            f"reference: {reference}\noutcome: {outcome}\n"
            f"message: {message or '(none)'}\n"
            f"tombstone: {result.get('tombstone_revision_id') or '(n/a)'}"
        ),
        client_name=client_name,
        extra_metadata={"outcome": outcome,
                        "tombstone_revision_id": result.get("tombstone_revision_id")},
    )
    return _present("delete", result, client_name=client_name)


@mcp.tool(
    # ADR-545 D2 — binds ADR-337 MoveFile. One attributed operation: content
    # revision at the destination + tombstone at the origin pointing there.
    # Refuses to overwrite an existing destination (delete first, by intent).
    annotations=ToolAnnotations(
        title="Move",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def move(
    ctx: Context,
    reference: str,
    new_reference: str,
    message: Optional[str] = None,
) -> dict:
    """Move or rename a file — or a whole folder — in the user's yarnnn workspace.

    Call this to put work where it belongs — a better home, a clearer name.
    One attributed operation: the content lands at the new path, the old path
    keeps a tombstone pointing there, and both revision chains are retained.
    Refuses to overwrite an existing destination — if the destination must be
    replaced, `delete` it first (explicit intent).

    ONE VERB, TWO GRAINS. `reference` may name a file or a FOLDER, and the
    workspace resolves which — you don't have to know. Naming a folder moves
    every file under it, keeping their relative layout; a rename is the same
    act with a new leaf. Locked children are reported in `locked` and a
    partially-landed fan in `failed`, never hidden — report what actually
    moved rather than assuming the whole tree did.

    Args:
        reference: The current path of the file OR folder — same grammar as
            open. Required.
        new_reference: The destination path (must not already exist). Required.
        message: Why this is moving (recorded on both revisions).
    """
    auth = resolve_request_client(verb="move")
    client_name = mcp_composition.derive_client_name_from_token(auth)
    if client_name == "unknown":
        client_name = mcp_composition.derive_client_name(
            getattr(ctx.request_context, "request", None)
        )
    result = await mcp_composition.compose_move(
        auth=auth, reference=reference, new_reference=new_reference, message=message,
    )
    outcome = "moved" if result.get("success") else (result.get("error") or "failed")
    _emit_mcp_narrative(
        auth, tool="move", weight="material" if result.get("success") else "routine",
        summary=f"{client_name} {outcome}: {reference} → {new_reference}",
        body=(
            f"from: {reference}\nto: {new_reference}\noutcome: {outcome}\n"
            f"message: {message or '(none)'}"
        ),
        client_name=client_name,
        extra_metadata={"outcome": outcome, "to": new_reference},
    )
    return _present("move", result, client_name=client_name)


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
    auth = resolve_request_client(verb="share")
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
        # `ShareError` above is OURS — typed, member-language, and keeps its
        # message. This branch is anything else (transport, PostgREST), whose
        # str() carries our internals to an external client.
        logger.warning("[MCP] share mint failed: %s", exc)
        return _present("share", {
            "success": False, "error": "share_failed",
            "message": mcp_composition.INTERNAL_FAILURE_MESSAGE,
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
            + "; joining requires sign-in. The user can revoke it in their yarnnn workspace."
        ),
    }, client_name=client_name)


# =============================================================================
# ADR-372 submission-readiness — explicit output schemas
# =============================================================================
# The App-review surface flags "OUTPUT SCHEMA RECOMMENDED" on tools without one;
# a declared outputSchema lets the host validate structuredContent and (for
# history) makes the widget's render contract explicit. We declare them as data
# and attach post-registration: FastMCP derives a schema from the return
# annotation only with structured_output=True, which (a) fails on history's
# nested TypedDict in this Pydantic and (b) is bypassed entirely because history
# returns a CallToolResult. Setting `output_schema` directly is the uniform,
# low-risk path.

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
    # ADR-584 — the one verb whose subject is the CONNECTION. It was the only
    # verb of ten with no declared schema, which ChatGPT's connector panel
    # surfaces verbatim as "OUTPUT SCHEMA RECOMMENDED" (observed 2026-08-20).
    # It matters MORE here than on the file verbs, not less: whoami's entire
    # audience is the model, and `binding` is a three-value field the model is
    # asked to branch on before writing. A described enum is how that branch
    # becomes legible rather than guessed.
    "whoami": {
        "type": "object",
        "properties": {
            "workspace": {"type": ["string", "null"], "description": "the workspace's name, or null when it still wears the mint default (describe it by address; do not invent a name)"},
            "workspace_id": {"type": ["string", "null"], "description": "the workspace's stable id — the receipt to quote when the operator asks WHICH commons this is"},
            "workspace_named": {"type": "boolean", "description": "false when the workspace has no operator-chosen name yet"},
            # The enum carries ALL FOUR BINDING_* constants, including
            # `unresolved`. It is reachable (resolve_mcp_workspace_detail's
            # except branch) and was missing from the tool docstring — an enum
            # that omitted it would make a host reject a legitimate response,
            # in exactly the failure state where the model most needs to be
            # able to say what happened.
            "binding": {
                "type": "string",
                "enum": ["chosen", "default", "fallback", "unresolved"],
                "description": "how this connection arrived at that workspace. 'chosen' = the operator picked it at consent. 'default' = no explicit choice on this connection. 'fallback' = the bound workspace is UNREACHABLE and this is NOT where the operator chose — writes still succeed and are attributed, so SAY SO before writing rather than filing into the wrong commons silently. 'unresolved' = workspace resolution FAILED; workspace_id is null and no write should be attempted until the user re-checks the connection.",
            },
            "you": {"type": "string", "description": "the attribution every write from this connection will carry (yarnnn:mcp:<client>)"},
            "client": {"type": ["string", "null"], "description": "the connecting host as yarnnn resolved it (chatgpt | claude.ai | …)"},
            "scopes": {"type": "array", "items": {"type": "string"}, "description": "the ADR-563 scope tiers this token holds; 'read' is the legacy full-access grant"},
            "capabilities": {"type": "array", "items": {"type": "string"}, "description": "exactly which verbs this token authorizes — derived from the same check that enforces them, so it cannot overstate what a call will be allowed to do"},
            "explanation": {"type": "string"},
        },
        "required": ["workspace_id", "binding", "you", "capabilities"],
    },
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
            "found": {"type": "boolean", "description": "false = no file at that exact reference (open never searches — use search or list)"},
            "reference": {"type": "string", "description": "the canonical yarnnn://workspace/… handle for this file (ADR-512 D5)"},
            "path": {"type": ["string", "null"], "description": "the ledger's absolute path (/workspace/…)"},
            "content": {"type": ["string", "null"], "description": "the file's content from `offset` (one page; see truncated). Machine-composed stylesheets are elided — authored content is never removed"},
            "truncated": {"type": "boolean", "description": "true when content remains — continue from next_offset"},
            "next_offset": {"type": "integer", "description": "pass as offset to read the next page (present when truncated)"},
            "offset": {"type": "integer", "description": "the character offset this page started at"},
            "content_chars": {"type": "integer", "description": "length of the READABLE VIEW in characters — what offset/next_offset paginate over. Not the file's size when stylesheets were elided; compare stored_chars"},
            "stored_chars": {"type": "integer", "description": "the file's actual stored length in characters. Greater than content_chars when machine-composed stylesheets were elided from the view"},
            "complete_for_write": {"type": "boolean", "description": "TRUE only when this content IS the file — nothing truncated and nothing elided. FALSE means you hold a VIEW: safe to read and to `edit` against, never safe to `save` back as a whole file"},
            "citations": {"type": "array", "items": {"type": "object"}, "description": "workspace files this document CITES (path, kind, pinned, projected). A projected citation renders EMPTY here — its content comes from the cited file, so open that file to read it; never write content into a citation"},
            "authored_by": {"type": ["string", "null"], "description": "who made the most recent revision"},
            "last_updated": {"type": ["string", "null"]},
            "history": {"type": "array", "items": _REVISION_SCHEMA, "description": "recent revisions, newest first (no diffs — history has those)"},
            "explanation": {"type": "string"},
        },
    },
    "list": {
        "type": "object",
        "properties": {
            "reference": {"type": "string", "description": "the canonical handle of the listed folder (yarnnn://workspace/… — the workspace root when no reference was passed)"},
            "path": {"type": ["string", "null"], "description": "the ledger's absolute folder prefix (/workspace/…)"},
            "files": {"type": "array", "items": {"type": "object"}, "description": "every matching file (path, reference, bytes, last_updated, authored_by, author_class), ordered by path"},
            "count": {"type": "integer"},
            "since": {"type": "string", "description": "echoed when the call was a change-feed query (only files changed after this moment)"},
            "truncated": {"type": "boolean", "description": "true when more files remain — continue from next_offset"},
            "next_offset": {"type": "integer", "description": "pass as offset to fetch the next page (present when truncated)"},
            "explanation": {"type": "string"},
        },
    },
    "edit": {
        "type": "object",
        "properties": {
            "reference": {"type": "string", "description": "the canonical handle of the edited file"},
            "path": {"type": ["string", "null"]},
            "replacements": {"type": "integer", "description": "how many occurrences were replaced"},
            "explanation": {"type": "string"},
        },
    },
    "delete": {
        "type": "object",
        "properties": {
            "reference": {"type": "string", "description": "the canonical handle of the removed file"},
            "path": {"type": ["string", "null"]},
            "tombstone_revision_id": {"type": ["string", "null"], "description": "the attributed tombstone — the chain is retained; restore is possible"},
            "explanation": {"type": "string"},
        },
    },
    "move": {
        "type": "object",
        "properties": {
            "reference": {"type": "string", "description": "the canonical handle of the file at its NEW path"},
            "from_path": {"type": ["string", "null"], "description": "the old absolute path (now a tombstone pointing at path)"},
            "path": {"type": ["string", "null"], "description": "the new absolute path"},
            "explanation": {"type": "string"},
        },
    },
    "search": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "results": {"type": "array", "items": {"type": "object"}, "description": "ranked matches (path, reference, excerpt, last_updated, similarity) — open any path for exact content"},
            "total_matches": {"type": "integer"},
            "returned": {"type": "integer"},
            "confidence": {"type": "string", "enum": ["high", "ambiguous", "weak", "none"], "description": "ALWAYS present (even on a miss): high=use it; ambiguous=ask which the user means; weak=loose lead only; none=nothing matched (true miss)"},
            "explanation": {"type": "string"},
        },
    },
    "history": {
        "type": "object",
        "properties": {
            "found": {"type": "boolean", "description": "false = no file at that exact reference (history never searches — use search or list)"},
            "reference": {"type": "string", "description": "the canonical yarnnn://workspace/… handle for this file (ADR-512 D5)"},
            "path": {"type": ["string", "null"], "description": "the ledger's absolute path (/workspace/…)"},
            "derived_from": {"type": ["string", "null"], "description": "the first cited source (ADR-448 edge), if any"},
            "history": {"type": "array", "items": _REVISION_SCHEMA, "description": "revision chain, newest first; cited sources' chains follow with cited_source: true"},
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
