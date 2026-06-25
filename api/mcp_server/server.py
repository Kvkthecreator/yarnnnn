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
from pydantic import AnyHttpUrl

from mcp_server.auth import resolve_request_client
from mcp_server.oauth_provider import YarnnnOAuthProvider
from services import mcp_composition
from services.narrative import (
    find_active_workspace_session,
    write_narrative_entry,
)
from services.primitives.registry import execute_primitive

logger = logging.getLogger(__name__)


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
        "YARNNN is the user's memory across every LLM they use. Whatever they "
        "record in YARNNN follows them — from this conversation into ChatGPT, "
        "Claude, any LLM — attributed and intact. Three verbs:\n"
        "  • remember — save something worth keeping (a decision, insight, fact,\n"
        "               preference). Whatever you save is immediately visible to\n"
        "               any other LLM the user switches to.\n"
        "  • recall   — pull what the user already knows about a subject when\n"
        "               they reference something they might track. YARNNN returns\n"
        "               the material; YOU explain it in your own voice.\n"
        "  • trace    — show how a recorded fact changed over time (who changed\n"
        "               it, when, what the change was) — YARNNN's distinguishing\n"
        "               capability, which a plain storage connector cannot show.\n\n"
        "Use these proactively — YARNNN is supposed to be ambient. Don't wait for "
        "the user to ask: recall before reasoning about something they track, and "
        "remember when they share something worth keeping. You are reading and "
        "writing a shared memory — not asking YARNNN to do work for you."
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
)



# =============================================================================
# The memory-first interop surface — remember / recall / trace (ADR-368)
# =============================================================================
# Three verbs shaped on the user's memory mental model: put in, get out, trace
# history. Each composes kernel primitives SERVER-SIDE into a one-round result —
# the host LLM (claude.ai / ChatGPT / Gemini) never has to chain. The raw kernel
# primitives remain available defer-loaded for agentic hosts that do chain.


@mcp.tool()
async def remember(
    ctx: Context,
    content: str,
    about: Optional[str] = None,
) -> dict:
    """Save something into the user's YARNNN memory so it follows them across every LLM.

    Call this whenever the user shares something worth keeping — a decision, an
    insight, a fact, a preference, an observation about something they track.
    Don't wait for them to say "remember this": if they reach a conclusion or
    state something they'll want later, save it.

    Pass the thing to keep as `content` — their words, or a faithful summary of
    what you both concluded. Be concise but preserve the specific claim. If it's
    clearly about a subject (a company, person, project, topic), pass that as
    `about`.

    The write is synchronous and immediately visible to any other LLM the user
    switches to, attributed to this LLM. YARNNN's own judgment seat then files
    the memory where it belongs in the workspace and checks it against what it
    already knows (in the background — you don't wait for it). You are saving to
    a shared memory; you are not asking YARNNN to do work.

    Args:
        content: The thing to remember. Required.
        about: Optional subject hint (company, person, project, topic).
    """
    auth = resolve_request_client()
    content = (content or "").strip()
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
        return {"success": False, "error": "empty_content", "message": "content is required"}

    # ADR-368 D3: write to the operation/ commons only — the one root the mcp
    # caller may write. No enum, no governing-substrate target reachable.
    stamped = mcp_composition.stamp_provenance(content, client_name, user_context=about)
    result = await mcp_composition.dispatch_remember_this(
        auth=auth, stamped_text=stamped, about=about,
    )

    if not result.get("success"):
        _emit_mcp_narrative(
            auth, tool="remember", weight="routine",
            summary=f"{client_name} remember failed",
            body=str(result.get("message") or "remember dispatch failed"),
            client_name=client_name,
            extra_metadata={"outcome": "failed", "error": result.get("error")},
        )
        return {
            "success": False,
            "error": result.get("error", "write_failed"),
            "message": result.get("message", "remember dispatch failed"),
        }

    written_path = result.get("filename") or result.get("path") or "(unknown)"

    # ADR-368 D5: the dump landed in the memory inbox; this wake INVOKES the
    # Reviewer to reason about where it belongs and file it (placement is
    # judgment, not a deterministic route), and to check it against ground-truth.
    # Eventually-async; never blocks. The dump is captured instantly.
    if written_path and written_path != "(unknown)":
        await mcp_composition.submit_foreign_write_wake(
            auth, written_path=written_path, target="memory-inbox", client_name=client_name,
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
    return {
        "success": True,
        "written_to": written_path,
        "provenance": {
            "source": f"mcp:{client_name}",
            "date": _today_iso(),
            "original_context": (about or content[:80]),
        },
        # ADR-368 D5: the seat will file this where it belongs + validate it.
        "captured": True,
    }


@mcp.tool()
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
    return result


@mcp.tool()
async def trace(
    ctx: Context,
    subject: str,
    limit: int = 10,
) -> dict:
    """Show how the user's recorded thinking on a subject changed over time.

    Call this when the user asks about the HISTORY of something they track —
    "when did I decide that," "how has my view on X changed," "who added this,"
    "what did this used to say." This is YARNNN's distinguishing capability: it
    returns the authored revision chain of a fact — who changed it, when, and
    what the change was — which a plain storage connector cannot show.

    Pass the subject as `subject`. YARNNN resolves it to the most relevant
    recorded material and returns its revision history, newest first. Reason over
    the chain and narrate the evolution in your own voice.

    Args:
        subject: What to trace the history of. Required.
        limit: Max revisions (default 10, max 30).
    """
    auth = resolve_request_client()
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
    return result


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
