"""
YARNNN MCP Server — ADR-169 (tool surface) + ADR-075 (infrastructure)

Three intent-shaped tools expose YARNNN as a cross-LLM context hub:

    work_on_this    — curated start-of-session bundle for a subject
    pull_context    — ranked chunks of accumulated material (primary cross-LLM tool)
    remember_this   — write observations back to the workspace

Design invariants (ADR-169):
    1. Three tools, not nine — the old data-shaped surface is DELETED
    2. Zero YARNNN-internal LLM calls on the serving path
    3. MCP is the fifth caller of execute_primitive() — no direct service imports
    4. Every write carries ADR-162 provenance (source: mcp:<client>)
    5. Cross-LLM consistency is the load-bearing property — every LLM sees
       the same substrate via identical QueryKnowledge retrieval

Two-layer auth (ADR-075, unchanged):
    Transport: OAuth 2.1 (Claude.ai, ChatGPT) + static bearer (Claude Desktop)
    Data:      Service key + MCP_USER_ID (all queries scoped by user_id)

Canonical framing: docs/features/mcp/README.md
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

from mcp_server.auth import get_authenticated_client
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
    """Best-effort MCP → narrative emission. Never raises."""
    try:
        session_id = find_active_workspace_session(auth.client, auth.user_id)
        if not session_id:
            logger.debug(
                "[MCP NARRATIVE] no active session for user=%s; skipping %s emission",
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
    """Initialize auth context at server startup."""
    logger.info("[MCP Server] Initializing ADR-169 three-tool surface…")
    auth = get_authenticated_client()
    logger.info(f"[MCP Server] Ready — user: {auth.user_id}")
    yield {"auth": auth}
    logger.info("[MCP Server] Shutting down")


# Server URL for OAuth issuer
_server_url = os.environ.get(
    "MCP_SERVER_URL", "https://yarnnn-mcp-server.onrender.com"
)

mcp = FastMCP(
    "yarnnn",
    instructions=(
        "YARNNN is the context hub across the LLMs you already use. "
        "It is not a connector for static data — it is a living workspace "
        "grown by an autonomous agent workforce in the background.\n\n"
        "Three tools expose that workspace to whichever LLM the user is in:\n"
        "  • work_on_this — call at the START of a work session on a subject\n"
        "  • pull_context — call MID-SESSION when the user mentions something\n"
        "                    that might live in their accumulated context\n"
        "  • remember_this — call whenever the user shares an observation,\n"
        "                    decision, or insight worth keeping\n\n"
        "Whatever you write via remember_this is IMMEDIATELY visible to any "
        "other LLM the user switches to. This is how the user's thinking stays "
        "coherent across rooms.\n\n"
        "Use these proactively — YARNNN is supposed to be ambient. Do not wait "
        "for the user to ask you to consult it."
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
# Tool 1: work_on_this
# =============================================================================


@mcp.tool()
async def work_on_this(
    ctx: Context,
    context: str,
    subject_hint: Optional[str] = None,
) -> dict:
    """Prime yourself with a curated starting bundle from the user's YARNNN workspace for a subject they're about to work on.

    Call this when the user says "help me work on this," "let's think through
    this," "I'm drafting X," or otherwise indicates they're about to ENGAGE
    with a subject that might live in their YARNNN workspace (people,
    companies, markets, projects, deliverables, decisions).

    BEFORE CALLING, compress what you and the user have been discussing into
    one or two sentences and pass it as `context`. If you can identify a
    specific subject name (a person, company, project, or topic), pass it as
    `subject_hint`. DO NOT ask the user to clarify what they mean — infer
    from your conversation.

    If YARNNN cannot confidently resolve the subject, it will return a set of
    candidates from currently-active workspace state. Surface those to the
    user naturally ("You've got a few things in flight — which one?") and
    call again with a clearer subject.

    This tool returns a COMPACT curated bundle designed for starting a work
    session. If you need deeper or broader material about the subject later
    in the conversation, use `pull_context` instead — that tool returns
    ranked chunks rather than a curated bundle.

    Use this proactively when the user is starting work on something. YARNNN
    is supposed to be ambient — the user should not have to ask you to
    consult it.

    Args:
        context: 1-2 sentence compression of the current conversation and
                 what the user is trying to do. Required. Generated silently
                 by you at call time — never asked from the user.
        subject_hint: Optional specific subject name (company, person,
                 project) if the conversation named one clearly.
    """
    auth = ctx.request_context.lifespan_context["auth"]
    result = await mcp_composition.compose_subject_context(
        auth=auth,
        context=context or "",
        subject_hint=subject_hint,
    )

    # ADR-219 Commit 6: emit narrative entry for the external invocation.
    # work_on_this is a curated read (no substrate write) → routine weight.
    client_name = mcp_composition.derive_client_name(
        getattr(ctx.request_context, "request", None)
    )
    subject_label = subject_hint or "subject"
    _emit_mcp_narrative(
        auth,
        tool="work_on_this",
        weight="routine",
        summary=f"{client_name} pulled session bundle for {subject_label}",
        body=f"context: {context}\nsubject_hint: {subject_hint or '(none)'}",
        client_name=client_name,
        extra_metadata={"subject_hint": subject_hint},
    )
    return result


# =============================================================================
# Tool 2: pull_context
# =============================================================================


@mcp.tool()
async def pull_context(
    ctx: Context,
    subject: str,
    question: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Pull YARNNN's accumulated context about a subject.

    Call this whenever the user references something mid-conversation that
    might live in their YARNNN workspace — a person, company, market,
    project, topic, or domain they track — and you need the underlying
    material to reason about it.

    Pass the subject name as `subject`. Optionally pass a `question` to
    narrow the retrieval (YARNNN will rank chunks by relevance to the
    question). Optionally pass a `domain` filter (competitors, market,
    relationships, projects, content, signals, slack, notion, github) if
    you know which context domain the subject lives in.

    The tool returns RANKED CHUNKS from the user's accumulated workspace
    context, with paths and timestamps. YARNNN does not compose an answer
    for you — you are expected to reason over the chunks and synthesize in
    your own voice, using the surrounding conversation as context.

    THIS IS THE CROSS-LLM CONSISTENCY TOOL. The user may be in a different
    LLM tomorrow than they are today. Every LLM calling `pull_context` on
    the same subject sees the same chunks from the same Postgres-backed
    substrate. This is how the user's thinking stays coherent across
    whichever LLM they happen to be in.

    If no chunks match (empty results), tell the user YARNNN has no
    accumulated context for that subject and answer from your own
    knowledge if you can.

    Use this proactively. YARNNN is supposed to be ambient — if the user
    mentions something they might track, pull the context first and weave
    it into your response. Do not wait for the user to ask you to consult
    YARNNN.

    Args:
        subject: What to pull context about (entity, topic, keyword). Required.
        question: Optional specific question to narrow the retrieval.
        domain: Optional context domain filter. One of: competitors, market,
                relationships, projects, content, signals, slack, notion, github.
        limit: Max chunks to return (default 10, hard cap 30).
    """
    auth = ctx.request_context.lifespan_context["auth"]
    limit = max(1, min(int(limit or 10), 30))
    client_name = mcp_composition.derive_client_name(
        getattr(ctx.request_context, "request", None)
    )

    # Normalize domain alias → registry key
    normalized_domain = mcp_composition.DOMAIN_ALIASES.get(
        (domain or "").lower().strip(),
        domain,
    ) if domain else None

    # Dispatch through the primitive layer (ADR-164 runtime-agnostic)
    # ADR-168 Commit 4: file-layer primitives now named ReadFile/WriteFile/
    # SearchFiles/ListFiles. QueryKnowledge kept (distinct semantic-query layer).
    result = await execute_primitive(auth, "QueryKnowledge", {
        "query": question or subject,
        "domain": normalized_domain,
        "limit": limit,
    })

    if not result.get("success"):
        # ADR-219 Commit 6: emit narrative even on failure so the operator
        # sees the foreign-LLM call landed (Identity legibility per
        # FOUNDATIONS Derived Principle 12).
        _emit_mcp_narrative(
            auth,
            tool="pull_context",
            weight="routine",
            summary=f"{client_name} pull_context failed for {subject!r}",
            body=str(result.get("message") or "QueryKnowledge dispatch failed"),
            client_name=client_name,
            extra_metadata={"subject": subject, "outcome": "failed"},
        )
        return {
            "success": False,
            "error": result.get("error", "query_failed"),
            "message": result.get("message", "QueryKnowledge dispatch failed"),
            "subject": subject,
        }

    raw_results = result.get("results") or []

    chunks = []
    for r in raw_results:
        path = r.get("path", "")
        excerpt = (r.get("content_preview") or r.get("summary") or "")[:500]
        chunks.append({
            "path": path,
            "excerpt": excerpt,
            "relevance": None,  # QueryKnowledge doesn't currently expose a score
            "last_updated": r.get("updated_at"),
            "domain": r.get("domain") or mcp_composition.extract_domain_from_path(path),
            "source_tag": mcp_composition._extract_provenance_tag(r.get("content_preview")),
        })

    # ADR-219 Commit 6: routine weight (no substrate write) per D3.
    _emit_mcp_narrative(
        auth,
        tool="pull_context",
        weight="routine",
        summary=(
            f"{client_name} pulled {len(chunks)} chunks for {subject!r}"
            if chunks
            else f"{client_name} pulled context for {subject!r} (none found)"
        ),
        body=(
            f"subject: {subject}\n"
            f"question: {question or '(none)'}\n"
            f"domain: {normalized_domain or '(any)'}\n"
            f"returned: {len(chunks)}"
        ),
        client_name=client_name,
        extra_metadata={
            "subject": subject,
            "domain": normalized_domain,
            "returned": len(chunks),
        },
    )

    if not chunks:
        return {
            "success": True,
            "subject": subject,
            "chunks": [],
            "total_matches": 0,
            "returned": 0,
            "citations": [],
            "explanation": (
                f"YARNNN has no accumulated context about '{subject}'. "
                "The user has not tracked this in any context domain yet. "
                "Answer from your own knowledge if you can."
            ),
        }

    return {
        "success": True,
        "subject": subject,
        "chunks": chunks,
        "total_matches": result.get("count", len(chunks)),
        "returned": len(chunks),
        "citations": [c["path"] for c in chunks],
    }


# =============================================================================
# Tool 3: remember_this
# =============================================================================


@mcp.tool()
async def remember_this(
    ctx: Context,
    content: str,
    about: Optional[str] = None,
) -> dict:
    """Write an observation, decision, or insight the user just shared back into their YARNNN workspace.

    Call this when the user says "remember this," "save that," "note that,"
    "YARNNN should know," or otherwise indicates something worth persisting.

    Pass the content as `content` — this can be the user's own words, a
    summary of a conclusion you and the user just reached together, or a
    paraphrase of an artifact you just drafted. Be concise but preserve
    the specific claim being made.

    If the content is clearly about a specific entity (a company, person,
    project, or topic), pass it as `about`. If not, leave `about` empty
    and YARNNN will classify from the content.

    YARNNN routes the content to the correct context target automatically:
        • identity — facts about the user's role, company, or work context
        • brand    — voice/tone/style preferences
        • memory   — general facts, preferences, standing instructions
        • agent    — feedback about a specific agent's work (slug-disambiguated)
        • task     — feedback about a specific task's output (slug-disambiguated)

    If it cannot classify confidently, it returns candidates — surface them
    and let the user choose.

    THIS IS THE CROSS-LLM CONTRIBUTION PATH. Whatever you write here is
    immediately visible to any other LLM the user might switch to. A user
    who tells you something at 3pm and then opens a different LLM at 4pm
    will find the material already there via pull_context. The write is
    synchronous — it commits before this tool returns.

    Use this proactively whenever the user shares something worth keeping.
    Do not wait for an explicit "remember this" — if the user shares a
    decision, an insight, a fact they want to act on, or an observation
    about something they track, call this tool.

    Args:
        content: The observation, decision, or fact to remember. Required.
        about: Optional scope hint — an entity, subject, or target name if
               clear from the conversation.
    """
    auth = ctx.request_context.lifespan_context["auth"]
    content = (content or "").strip()
    client_name = mcp_composition.derive_client_name(
        getattr(ctx.request_context, "request", None)
    )

    if not content:
        # No invocation work happened — but per ADR-219 universal coverage,
        # the call still lands a (housekeeping-weight) narrative breadcrumb
        # so the operator sees the foreign LLM tried.
        _emit_mcp_narrative(
            auth,
            tool="remember_this",
            weight="housekeeping",
            summary=f"{client_name} remember_this rejected (empty content)",
            body="empty content — nothing written",
            client_name=client_name,
            extra_metadata={"outcome": "rejected"},
        )
        return {"success": False, "error": "empty_content", "message": "content is required"}

    # --- Load slug pools for operational-feedback classification ---
    agents_by_slug = _load_active_agents(auth)
    tasks_by_slug = _load_active_tasks(auth)

    classification = mcp_composition.classify_memory_target(
        content=content,
        about=about,
        agents_by_slug=agents_by_slug,
        tasks_by_slug=tasks_by_slug,
    )

    # --- Ambiguous classification → return candidates for LLM to surface ---
    if classification.get("ambiguous"):
        # No substrate write happened yet; routine weight per D3 default.
        _emit_mcp_narrative(
            auth,
            tool="remember_this",
            weight="routine",
            summary=f"{client_name} remember_this — clarification needed",
            body=(
                f"about: {about or '(none)'}\n"
                f"content: {content[:240]}{'…' if len(content) > 240 else ''}\n"
                f"candidates: {classification.get('candidates') or []}"
            ),
            client_name=client_name,
            extra_metadata={
                "outcome": "ambiguous",
                "candidates": classification.get("candidates", []),
            },
        )
        return {
            "success": True,
            "ambiguous": {
                "candidates": classification.get("candidates", []),
                "clarification": (
                    "I can route this feedback to multiple targets. Which did you mean?"
                ),
            },
        }

    target = classification["target"]

    # --- Stamp ADR-162 provenance on the content before UpdateContext ---
    stamped_text = mcp_composition.stamp_provenance(
        content=content,
        client_name=client_name,
        user_context=about,
    )

    # --- Build UpdateContext input ---
    uc_input: dict = {"target": target, "text": stamped_text}
    if target == "agent":
        uc_input["agent_slug"] = classification.get("slug")
    elif target == "task":
        uc_input["task_slug"] = classification.get("slug")

    # --- Dispatch through the primitive layer (ADR-164 runtime-agnostic) ---
    result = await execute_primitive(auth, "UpdateContext", uc_input)

    if not result.get("success"):
        _emit_mcp_narrative(
            auth,
            tool="remember_this",
            weight="routine",
            summary=f"{client_name} remember_this failed → {target}",
            body=str(result.get("message") or "UpdateContext dispatch failed"),
            client_name=client_name,
            extra_metadata={
                "attempted_target": target,
                "outcome": "failed",
            },
        )
        return {
            "success": False,
            "error": result.get("error", "update_failed"),
            "message": result.get("message", "UpdateContext dispatch failed"),
            "attempted_target": target,
        }

    # ADR-219 D3: remember_this success is MATERIAL — substrate changed,
    # cross-LLM contribution committed. The morning briefing will surface
    # this attribution per ADR-169.
    written_path = result.get("filename") or result.get("path") or "(unknown)"
    _emit_mcp_narrative(
        auth,
        tool="remember_this",
        weight="material",
        summary=(
            f"{client_name} wrote to {target}"
            + (f":{classification.get('slug')}" if classification.get("slug") else "")
        ),
        body=(
            f"target: {target}\n"
            f"slug: {classification.get('slug') or '(none)'}\n"
            f"written_to: {written_path}\n"
            f"about: {about or '(none)'}\n"
            f"content: {content[:480]}{'…' if len(content) > 480 else ''}"
        ),
        client_name=client_name,
        extra_metadata={
            "target": target,
            "slug": classification.get("slug"),
            "written_to": written_path,
            "outcome": "success",
            "task_slug": classification.get("slug") if target == "task" else None,
        },
    )

    return {
        "success": True,
        "target": target,
        "slug": classification.get("slug"),
        "written_to": result.get("filename") or result.get("path"),
        "provenance": {
            "source": f"mcp:{client_name}",
            "date": _today_iso(),
            "original_context": (about or content[:80]),
        },
        "note": classification.get("note"),
    }


# =============================================================================
# Slug pool loaders (for remember_this classification)
# =============================================================================


def _load_active_agents(auth) -> dict[str, dict]:
    """Load active agents keyed by slug for classifier slug matching."""
    try:
        result = (
            auth.client.table("agents")
            .select("id, title, role, scope, status")
            .eq("user_id", auth.user_id)
            .eq("status", "active")
            .limit(50)
            .execute()
        )
        pool: dict[str, dict] = {}
        for a in (result.data or []):
            # Derive slug from title (mirrors services.workspace.get_agent_slug)
            title = a.get("title") or ""
            slug = _simple_slug(title)
            if slug:
                pool[slug] = a
        return pool
    except Exception as e:
        logger.warning(f"[MCP] _load_active_agents failed: {e}")
        return {}


def _load_active_tasks(auth) -> dict[str, dict]:
    """Load active tasks keyed by slug for classifier slug matching.

    Note: the `tasks` table has no `title` column — slug is the only
    identifier we need for substring-based slug matching.
    """
    try:
        result = (
            auth.client.table("tasks")
            .select("slug, status")
            .eq("user_id", auth.user_id)
            .eq("status", "active")
            .limit(50)
            .execute()
        )
        return {
            t["slug"]: t
            for t in (result.data or [])
            if t.get("slug")
        }
    except Exception as e:
        logger.warning(f"[MCP] _load_active_tasks failed: {e}")
        return {}


def _simple_slug(text: str) -> str:
    """Simple slug derivation — lowercase, hyphenate. Matches get_agent_slug shape."""
    import re
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def _today_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
