"""
MCP Composition Layer — ADR-368 (memory-first interop surface)

Composition module for the three memory verbs (remember / recall / trace).
Each verb composes existing kernel primitives (QueryKnowledge / WriteFile /
ListRevisions / DiffRevisions) SERVER-SIDE into a reason-ready result returned
in one round. This is the fix for ADR-311's "host must chain primitives" error:
the chaining lives here (an agentic context, no round limit), not in a
round-limited consumer chat host (claude.ai / ChatGPT / Gemini connectors).

The user's memory mental model is the surface (ADR-368 D1):
    remember  — put something in   → resolve_remember_path + dispatch_remember_this
    recall    — get something out  → compose_recall  (QueryKnowledge → rank)
    trace     — how did it change  → compose_trace   (resolve → ListRevisions)

Design invariants:
    1. No new primitives — this module is composition over execute_primitive().
    2. Zero YARNNN-internal LLM calls on the serving path.
    3. Writes route to the `operation/` commons ONLY (ADR-368 D3) — the one root
       CALLER_WRITE_POLICY["mcp"] grants the foreign caller. The pre-ADR-368
       five-target enum (memory/identity/brand/agent/task) is DELETED; three of
       its targets pointed at roots locked for the mcp caller.
    4. `recall` RETURNS material; it does not synthesize — the host LLM explains
       (ADR-368 D1: retrieval, not synthesis — the bright memory-vs-delegation line).
    5. Every write carries ADR-162 provenance (source: mcp:<client_name>) and
       fires the integrity wake (ADR-310 D2 / ADR-368 D5).

Canonical product framing:
    docs/features/mcp/README.md and sibling docs — this module is their impl.
    ADR-368 supersedes ADR-311's pure-primitive surface; ADR-310 two-faces holds.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Domain keyword hints for subject/content classification
# =============================================================================
# The directory_registry does not ship domain-level keyword metadata, so we
# maintain a minimal dict here for MCP classification. Keys match the canonical
# domain keys in api/services/directory_registry.py (context type only).
#
# This is intentionally small — the classifier's job is not exhaustive entity
# recognition, just a confident first-pass routing hint. When keywords miss,
# the tool returns the structured ambiguous shape and the LLM asks the user.
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "competitors": [
        "competitor", "competition", "rival", "compete", "market share",
        "positioning", "pricing model", "product roadmap",
    ],
    "market": [
        "market", "segment", "industry", "trend", "tam", "sam",
        "buyer", "adoption", "category",
    ],
    "relationships": [
        "contact", "relationship", "partner", "customer", "client",
        "introduction", "intro", "warm intro", "connection",
    ],
    "projects": [
        "project", "initiative", "milestone", "roadmap item", "sprint",
        "deliverable", "deadline",
    ],
    "content_research": [
        "draft", "outline", "research note", "article", "post",
        "blog", "essay", "content piece",
    ],
    "signals": [
        "signal", "observation", "heard that", "noticed", "flag",
        "incident", "event",
    ],
}

# User-facing domain aliases (what LLMs might pass) → registry keys
DOMAIN_ALIASES: dict[str, str] = {
    "content": "content_research",
    "competitor": "competitors",
    "contact": "relationships",
    "contacts": "relationships",
    "project": "projects",
    "market_research": "market",
}


# =============================================================================
# Provenance + helpers (shared by the memory-verb compositions below)
# =============================================================================


def derive_client_name(request_context: Any) -> str:
    """
    Derive the MCP client name for provenance stamping.

    Known clients map to short identifiers; unknown clients return 'unknown'.
    Sources in preference order:
        1. OAuth client_id if present on the request context
        2. User-Agent header substring match
        3. Fallback to 'unknown'

    Values: claude.ai, chatgpt, claude_desktop, gemini, cursor, unknown
    """
    if request_context is None:
        return "unknown"

    # Try OAuth client id
    client_id = getattr(request_context, "client_id", None)
    if client_id:
        normalized = _normalize_client_id(client_id)
        if normalized:
            return normalized

    # Try User-Agent from the request headers
    headers = getattr(request_context, "headers", None) or {}
    ua = headers.get("user-agent") or headers.get("User-Agent") or ""
    normalized = _normalize_client_id(ua)
    if normalized:
        return normalized

    return "unknown"


def stamp_provenance(
    content: str,
    client_name: str,
    user_context: Optional[str] = None,
) -> str:
    """
    Prepend an ADR-162 source-provenance HTML comment to content.

    Format:
        <!-- source: mcp:<client> | date: YYYY-MM-DD | user_context: "..." -->
        <original content>
    """
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    uc = (user_context or "")[:100].replace('"', "'")
    comment = f'<!-- source: mcp:{client_name} | date: {date} | user_context: "{uc}" -->'
    return f"{comment}\n{content}"


def extract_domain_from_path(path: str) -> Optional[str]:
    """
    Extract the domain key from a /workspace/operation/{domain}/... path.
    Returns None if the path is not under /workspace/operation/.

    Per ADR-320 + ADR-321, accumulation domains live under operation/, not
    the pre-migration context/ root.
    """
    if not path or not path.startswith("/workspace/operation/"):
        return None
    parts = path.split("/")
    if len(parts) >= 4:
        return parts[3]
    return None


def _extract_provenance_tag(content: Optional[str]) -> Optional[str]:
    """
    Extract the `source: <tag>` field from the first ADR-162 HTML comment
    at the start of a file's content. Returns None if no tag is found.
    """
    if not content:
        return None
    # Match an HTML comment on the first or second line
    lines = content.strip().split("\n", 2)
    for line in lines[:2]:
        m = re.search(r"source:\s*([^\s|]+)", line)
        if m:
            return m.group(1).strip()
    return None


def _classify_domain(text: str) -> Optional[str]:
    """
    Match text against DOMAIN_KEYWORDS and return the best-scoring domain key.
    Returns None if no domain scores > 0.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score
    if not scores:
        return None
    return max(scores.items(), key=lambda kv: kv[1])[0]


def _short_excerpt(text: str, limit: int = 400) -> str:
    """Trim text to a reasonable excerpt length."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _slugify(text: str) -> str:
    """Simple slug derivation for entity path matching."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _normalize_client_id(raw: str) -> Optional[str]:
    """
    Map an OAuth client id or User-Agent string to one of the known
    short identifiers for provenance stamps.
    """
    if not raw:
        return None
    low = raw.lower()
    if "claude.ai" in low or "claude-ai" in low or "anthropic" in low and "desktop" not in low:
        return "claude.ai"
    if "claude" in low and "desktop" in low:
        return "claude_desktop"
    if "claude" in low and "code" in low:
        return "claude_code"
    if "chatgpt" in low or "openai" in low:
        return "chatgpt"
    if "gemini" in low or "google" in low:
        return "gemini"
    if "cursor" in low:
        return "cursor"
    return None


# =============================================================================
# dispatch_remember_this — ADR-235 routing for the MCP write path
# =============================================================================


def resolve_remember_path(about: Optional[str]) -> str:
    """Resolve where a `remember` write lands in the commons.

    ADR-368 D3: a foreign LLM writes ONLY the `operation/` commons (the one
    root `CALLER_WRITE_POLICY["mcp"]` grants it). The five-target enum
    (memory/identity/brand/agent/task) is DELETED — three of its targets
    (memory→system/, identity→persona+constitution) were locked for the mcp
    caller, making the default happy-path dead. There is no routing cleverness
    here and no governing-substrate target: subject-scoped content lands at
    `operation/{domain}/notes.md`; unscoped general memory lands at the commons
    notes file. The gate refuses anything else and the surface never offers it.

    `about` is the optional scope hint. When it names a recognizable domain we
    nest under it; otherwise the content joins the general commons notes.
    """
    hint = (about or "").strip().lower()
    if hint:
        # alias → registry domain, then a light keyword pass
        domain = DOMAIN_ALIASES.get(hint, None) or _classify_domain(hint)
        if domain:
            return f"operation/{domain}/notes.md"
        # named-but-unrecognized subject → its own commons folder, slugified
        slug = _slugify(hint)
        if slug:
            return f"operation/{slug}/notes.md"
    return "operation/notes.md"


async def dispatch_remember_this(
    auth: Any,
    stamped_text: str,
    about: Optional[str] = None,
) -> dict:
    """Commit a `remember` write to the `operation/` commons (ADR-368 D3).

    Topology-coherent: the only root a foreign (`yarnnn:mcp`) caller may write
    is `operation/`. This routes there unconditionally — no enum, no governing
    target, no locked-root reachable. The ADR-307 gate at `execute_primitive`
    is still the authority (a non-`operation/` path would `governance_locked`);
    this function simply never constructs such a path.

    ADR-288: `authored_by` defaults to `auth.caller_identity` ("yarnnn:mcp").
    Returns the WriteFile primitive result unchanged. The caller fires the
    integrity wake (ADR-368 D5) on success.
    """
    from services.primitives.registry import execute_primitive

    path = resolve_remember_path(about)
    return await execute_primitive(
        auth,
        "WriteFile",
        {
            "scope": "workspace",
            "path": path,
            "content": stamped_text,
            "mode": "append",
            "message": "remember → operation commons",
        },
    )


# =============================================================================
# compose_recall / compose_trace — server-side read compositions (ADR-368 D2)
# =============================================================================
# The memory verbs are NOT a second vocabulary — they compose the existing
# kernel primitives (QueryKnowledge / ListRevisions / DiffRevisions) inside the
# MCP server, returning a reason-ready result in ONE round from the host's
# perspective. This is the fix for ADR-311's "host must chain" error: the
# chaining lives here (an agentic context, no round limit), not in a
# round-limited consumer chat host.


async def compose_recall(
    auth: Any,
    subject: str,
    question: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Drive `recall` — the get-out-of-memory read.

    Composes `QueryKnowledge` into a ranked, reason-ready bundle. YARNNN
    RETURNS the material; it does NOT synthesize an answer — the host LLM
    holding the conversation explains it. (ADR-368 D1: `recall` connotes
    retrieval, not synthesis — the bright line that keeps memory-first from
    leaking into delegation.)
    """
    from services.primitives.registry import execute_primitive

    limit = max(1, min(int(limit or 10), 30))
    normalized_domain = DOMAIN_ALIASES.get((domain or "").lower().strip(), domain) if domain else None

    result = await execute_primitive(auth, "QueryKnowledge", {
        "query": question or subject,
        "domain": normalized_domain,
        "limit": limit,
    })
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "query_failed"),
                "message": result.get("message", "recall failed"), "subject": subject}

    raw = result.get("results") or []
    chunks = [
        {
            "path": r.get("path", ""),
            "excerpt": _short_excerpt(r.get("content_preview") or r.get("summary") or ""),
            "last_updated": r.get("updated_at"),
            "domain": r.get("domain") or extract_domain_from_path(r.get("path", "")),
            "source_tag": _extract_provenance_tag(r.get("content_preview")),
        }
        for r in raw
    ]
    if not chunks:
        return {
            "success": True, "subject": subject, "chunks": [], "total_matches": 0,
            "returned": 0, "citations": [],
            "explanation": (
                f"YARNNN has no accumulated memory about '{subject}'. The user "
                "hasn't recorded this yet. Answer from your own knowledge if you can."
            ),
        }
    return {
        "success": True, "subject": subject, "chunks": chunks,
        "total_matches": result.get("count", len(chunks)), "returned": len(chunks),
        "citations": [c["path"] for c in chunks],
    }


async def compose_trace(
    auth: Any,
    subject: str,
    limit: int = 10,
) -> dict:
    """Drive `trace` — the how-did-this-change read (the ADR-209 revision chain).

    Resolves the subject to its most-relevant authored path (via QueryKnowledge),
    then composes `ListRevisions` over it: who authored each version, when, and
    the change message. This is the revision-archaeology differentiator (ADR-311
    §3) surfaced in the user's words — "when did I decide that / how has this
    evolved / who added this" — composed server-side in one round.
    """
    from services.primitives.registry import execute_primitive

    # Resolve subject → the best-matching authored path.
    qk = await execute_primitive(auth, "QueryKnowledge", {"query": subject, "limit": 1})
    results = (qk.get("results") or []) if qk.get("success") else []
    if not results:
        return {
            "success": True, "subject": subject, "path": None, "history": [],
            "explanation": (
                f"YARNNN has no recorded material about '{subject}' to trace. "
                "Nothing has been authored on this subject yet."
            ),
        }

    path = results[0].get("path", "")
    # ListRevisions takes a workspace-relative path (strip the /workspace/ prefix).
    rel = path[len("/workspace/"):] if path.startswith("/workspace/") else path
    lr = await execute_primitive(auth, "ListRevisions", {"path": rel, "limit": max(1, min(int(limit or 10), 30))})
    if not lr.get("success"):
        return {"success": False, "error": lr.get("error", "trace_failed"),
                "message": lr.get("message", "trace failed"), "subject": subject, "path": path}

    revisions = lr.get("revisions") or []
    history = [
        {
            "authored_by": rev.get("authored_by"),   # operator | yarnnn:mcp | reviewer:<id> | agent:<slug> | system:<actor>
            "when": rev.get("created_at"),
            "change": rev.get("message"),
            "revision_id": rev.get("id"),
        }
        for rev in revisions
    ]
    return {
        "success": True,
        "subject": subject,
        "path": path,
        "history": history,            # newest first
        "returned": len(history),
        "citations": [path],
        "explanation": (
            f"The authored history of '{subject}' — {len(history)} revision(s), "
            "each attributed to who changed it and when. This is the cross-LLM "
            "provenance no plain storage connector can show."
        ),
    }


# =============================================================================
# ADR-310 D2/D3 — the moat seam: foreign write → Reviewer judgment (async)
# =============================================================================
#
# This is the SINGLE site in the MCP path that touches the wake contract
# (services.wake.submit_wake_proposal). It is deliberately isolated in one
# best-effort adapter so that if the wake contract is ever reshaped, the blast
# radius is exactly this function. Everything else in the MCP tools stays
# wake-agnostic.
#
# Eventually-judged model (ADR-310 D2 write side): the foreign LLM's write has
# already committed via dispatch_remember_this; this adapter then asks the
# Reviewer to evaluate it AFTER the fact. The foreign tool never blocks on it.
#
# Foreignness reaches the Reviewer in the wake's hook.prompt (ADR-310 D3) —
# NOT a new payload field — so the substrate_event contract stays frozen. The
# author is also structurally present on the revision (authored_by="yarnnn:mcp"
# per ADR-288), so the Reviewer can verify by reading it.

async def submit_foreign_write_wake(
    auth: Any,
    *,
    written_path: str,
    target: str,
    client_name: str,
) -> None:
    """Best-effort: wake the Reviewer to judge a foreign-LLM substrate write.

    Resolves the head revision_id for the just-written path and submits a
    substrate_event wake whose hook.prompt names the write as a foreign (MCP)
    contribution to evaluate against authored ground-truth. Never raises — a
    wake failure must not affect the remember_this result (the write already
    committed and is attributed).

    Shared-workspace seam (Phase 3, deferred): the Reviewer is a WORKSPACE-level
    seat (one per workspace), not per-user. The wake must fire for the WORKSPACE
    that owns this substrate, independent of which member's LLM wrote it. Today
    user_id == workspace owner (1:1), so `wake_scope` below equals auth.user_id
    and is accidentally correct. When workspaces become shared (user_id →
    workspace_id re-key), `wake_scope` becomes the resolved workspace_id — a
    one-line change confined to this function, which is the sole MCP→wake seam.
    The writing human's identity is preserved separately via authored_by on the
    revision (ADR-288), so multi-author attribution survives the re-key.
    """
    try:
        # workspace-relative path → absolute workspace path for revision lookup.
        abs_path = written_path
        if abs_path and not abs_path.startswith("/workspace/"):
            abs_path = "/workspace/" + abs_path.lstrip("/")

        # TODO(shared-workspace / Phase 3): resolve workspace_id here instead of
        # reusing the writing user's id. Today 1:1, so this is correct.
        wake_scope = auth.user_id

        from services.authored_substrate import _read_head_revision_id

        # Revision lookup is scoped to the writer's data (auth.user_id) — correct
        # in both worlds: the revision was written under the writer's scope.
        revision_id = _read_head_revision_id(auth.client, auth.user_id, abs_path)
        if not revision_id:
            logger.info(
                "[MCP WAKE] no revision for %s — skipping Reviewer wake", abs_path
            )
            return

        prompt = (
            f"A foreign LLM (via MCP, client: {client_name}) just wrote to "
            f"`{abs_path}` (target: {target}). Evaluate whether this "
            f"contribution is consistent with authored ground-truth and the "
            f"operator's mandate before it becomes load-bearing. If it "
            f"conflicts or warrants attention, surface it; otherwise stand down."
        )

        from services.wake import submit_wake_proposal

        await submit_wake_proposal(
            auth.client,
            wake_scope,  # workspace-scoped seam (Phase 3) — == auth.user_id today
            source="substrate_event",
            payload={
                "hook": {
                    "slug": "mcp-foreign-write-review",
                    "event": "substrate_change",
                    "prompt": prompt,
                },
                "path": abs_path,
                "field_change": {"source": "mcp", "target": target},
                "revision_id": revision_id,
            },
        )
        logger.info(
            "[MCP WAKE] submitted Reviewer wake for foreign write to %s", abs_path
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MCP WAKE] submit failed (non-fatal): %s", exc)
