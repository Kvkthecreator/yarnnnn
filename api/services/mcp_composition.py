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
# DOMAIN_ALIASES normalizes the OPTIONAL `domain` filter a host LLM may pass to
# `recall` (e.g. domain="competitor" → "competitors"). It is NOT used for
# placement — foreign-LLM dumps land in the memory inbox and the Reviewer does
# placement by judgment (ADR-368 D3/D5). The ADR-151 DOMAIN_KEYWORDS table +
# _classify_domain were deleted with the deterministic-routing model: live
# workspaces are program-shaped (reports/, trading/, specs/, …), not the
# competitors/market/relationships fiction that table encoded.
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


MEMORY_INBOX_PREFIX = "operation/memory/"
MEMORY_INBOX_DEFAULT = "operation/memory/inbox.md"


def resolve_remember_path(about: Optional[str]) -> str:
    """Resolve where a foreign-LLM `remember` DUMP lands (ADR-368 D3, revised).

    Placement is a JUDGMENT, not a deterministic route. The MCP layer does NOT
    decide where operator-contributed content belongs in the workspace — it
    CAPTURES it honestly in a memory inbox, attributed `yarnnn:mcp`, and the
    integrity wake invokes the Reviewer to REASON about placement against the
    actual workspace structure and file it into its real home (D5).

    Two prior mistakes this fixes: (1) routing to `system/notes.md` (locked for
    the mcp caller — the original `governance_locked` bug); (2) routing into
    invented `operation/{domain}/` folders (ADR-151 `competitors`/`market`
    fiction that live workspaces don't use) or into a program's structured
    output tree (`reports/`/`trading/`/`specs/` — which the foreign LLM doesn't
    understand and must not corrupt). The dump goes to a dedicated memory inbox;
    the judgment seat does placement.

    `about` only organizes the inbox so the Reviewer (and `trace`) can see dumps
    grouped by subject — it is NOT final placement:
        about="Acme Corp"  → operation/memory/acme-corp.md
        about=None         → operation/memory/inbox.md
    """
    hint = (about or "").strip()
    if hint:
        slug = _slugify(hint)
        if slug:
            return f"{MEMORY_INBOX_PREFIX}{slug}.md"
    return MEMORY_INBOX_DEFAULT


async def dispatch_remember_this(
    auth: Any,
    stamped_text: str,
    about: Optional[str] = None,
) -> dict:
    """Commit a `remember` DUMP to the memory inbox (ADR-368 D3, revised).

    A foreign LLM's `remember` is captured, not placed: it appends to the memory
    inbox under `operation/memory/` (writable by the `yarnnn:mcp` caller — the
    one commons root the topology grants it). Placement into the dump's real home
    is the Reviewer's job, invoked by the integrity wake the caller fires on
    success (ADR-368 D5 — placement is judgment, not a deterministic route). The
    ADR-307 gate at `execute_primitive` is still the authority; this function
    never constructs a locked path.

    ADR-288: `authored_by` defaults to `auth.caller_identity` ("yarnnn:mcp").
    Returns the WriteFile primitive result unchanged.
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
            "message": "remember → memory inbox (awaiting Reviewer placement)",
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
# ADR-310 D2 / ADR-368 D5 — the moat seam: foreign DUMP → Reviewer PLACEMENT
# =============================================================================
#
# This is the SINGLE site in the MCP path that touches the wake contract
# (services.wake.submit_wake_proposal). It is deliberately isolated in one
# best-effort adapter so that if the wake contract is ever reshaped, the blast
# radius is exactly this function. Everything else in the MCP tools stays
# wake-agnostic.
#
# Placement-is-judgment model (ADR-368 D5, revised): a foreign LLM's `remember`
# is a DUMP — it commits to the memory inbox (operation/memory/…) attributed
# `yarnnn:mcp`, with NO deterministic placement. This adapter then INVOKES the
# Reviewer to reason about where the dump belongs against the actual workspace
# structure and FILE it into its real home (or leave it in the inbox if memory
# is genuinely where it belongs). Placement lives with the judgment seat — which
# understands the workspace and can write everywhere the foreign caller can't —
# not with the least-context foreign caller. The foreign tool never blocks on
# it; the dump is captured instantly, the Reviewer files it shortly after.
#
# The two-step is git-legible: the dump's `yarnnn:mcp` origin survives on its
# revision; the Reviewer's placement is a SEPARATE `reviewer:<id>` revision; the
# `trace` verb shows the whole chain ("contributed via claude.ai → filed to X by
# the Reviewer"). The instruction reaches the Reviewer in the wake's hook.prompt
# (ADR-310 D3) — not a new payload field — so the substrate_event contract stays
# frozen.

async def submit_foreign_write_wake(
    auth: Any,
    *,
    written_path: str,
    target: str,
    client_name: str,
) -> None:
    """Best-effort: invoke the Reviewer to place a foreign-LLM memory dump.

    Resolves the head revision_id for the just-written inbox path and submits a
    substrate_event wake whose hook.prompt invokes the Reviewer to reason about
    placement (file the dump into its real home) AND validate it against
    ground-truth. Never raises — a wake failure must not affect the `remember`
    result (the dump already committed to the inbox and is attributed).

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
            f"The operator contributed a memory from outside YARNNN (via MCP, "
            f"client: {client_name}). It landed UNPLACED in the memory inbox at "
            f"`{abs_path}` — a holding area, not its home. Read it, then decide "
            f"where it belongs in this workspace and FILE it there: move or copy "
            f"it into the right substrate (a domain under operation/, an entity "
            f"file, agent feedback, or wherever its subject lives), preserving "
            f"the content and its `yarnnn:mcp` origin. If the memory genuinely "
            f"belongs as free memory, leave it in the inbox. While you place it, "
            f"also judge it against authored ground-truth and the mandate — if it "
            f"conflicts, surface that. You understand this workspace's structure; "
            f"the contributing LLM did not, which is why placement is yours."
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
                "field_change": {"source": "mcp", "target": "memory-inbox"},
                "revision_id": revision_id,
            },
        )
        logger.info(
            "[MCP WAKE] submitted Reviewer wake for foreign write to %s", abs_path
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MCP WAKE] submit failed (non-fatal): %s", exc)
