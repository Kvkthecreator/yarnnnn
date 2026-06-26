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


def derive_client_name_from_token(auth: Any) -> str:
    """Derive the MCP client name from the authenticated OAuth session.

    The reliable identity of a foreign LLM is its OAuth registration, NOT the
    raw HTTP request — claude.ai's User-Agent doesn't contain "claude", and a
    Starlette Request has no `client_id`, which is why the request-based
    `derive_client_name` returned "unknown" on real claude.ai calls (live test
    2026-06-25). This reads the access token's `client_id`, maps it to a known
    short id, and — when the client_id is opaque (a registration UUID) — looks
    up the registered `client_name` from `mcp_oauth_clients`.

    Best-effort: returns "unknown" only when nothing identifies the caller.
    """
    try:
        from mcp.server.auth.middleware.auth_context import get_access_token
        token = get_access_token()
    except Exception:  # noqa: BLE001
        token = None

    client_id = getattr(token, "client_id", None) if token else None
    if client_id:
        # direct map (some clients register a recognizable client_id)
        normalized = _normalize_client_id(client_id)
        if normalized:
            return normalized
        # opaque client_id → look up the human client_name we stored at register
        try:
            row = (
                auth.client.table("mcp_oauth_clients")
                .select("client_name")
                .eq("client_id", client_id)
                .limit(1)
                .execute()
            )
            name = (row.data or [{}])[0].get("client_name") if row.data else None
            if name:
                mapped = _normalize_client_id(name)
                if mapped:
                    return mapped
                return name  # surface the registered name even if unmapped
        except Exception as exc:  # noqa: BLE001
            logger.debug("[MCP] client_name lookup failed: %s", exc)
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


def _naturalize_subject(subject: str) -> str:
    """Turn a subject string into natural words for full-text search.

    `recall`/`trace` are most often called with the SAME string passed as
    `about` to `remember` — frequently a slug-shaped or hyphenated subject
    (e.g. "yarnnn-mcp-connector"). `search_workspace` builds a
    plainto_tsquery, which AND-matches every lexeme: the literal slug
    "yarnnn-mcp-connector" becomes `yarnnn & mcp & connector` and matches ZERO
    prose files even when the file is named exactly that and clearly relevant
    (live test 2026-06-26 — the exact save-then-recall round-trip returned
    nothing). Replacing separators with spaces lets the tokenizer rank on the
    individual words instead of requiring the joined slug, which the content
    rarely contains verbatim.
    """
    return re.sub(r"[-_/]+", " ", subject or "").strip()


async def resolve_memory_path(auth: Any, subject: str) -> Optional[str]:
    """Resolve a `recall`/`trace` subject to its authored path DETERMINISTICALLY.

    The save→read round-trip is deterministic, not fuzzy: `remember(about=X)`
    writes the dump to `operation/memory/{slug(X)}.md`, so a later
    `recall(subject=X)` / `trace(subject=X)` with the same subject should find
    that exact file by PATH, before any full-text search. This closes the
    round-trip hole where QueryKnowledge's slug-AND-match (Finding 1) missed a
    file literally named after the subject.

    Resolution order (first hit wins), all scoped to the caller's substrate:
        1. the exact inbox path operation/memory/{slug}.md (the dump's home);
        2. a placed copy — any active file whose basename is {slug}.md (the
           Reviewer may have FILED the dump elsewhere under the same name);
        3. None → caller falls back to fuzzy QueryKnowledge.

    Returns the absolute /workspace/ path or None.
    """
    slug = _slugify(subject or "")
    if not slug:
        return None

    inbox_abs = f"/workspace/{MEMORY_INBOX_PREFIX}{slug}.md"
    try:
        # 1. exact inbox path
        hit = (
            auth.client.table("workspace_files")
            .select("path")
            .eq("user_id", auth.user_id)
            .eq("path", inbox_abs)
            .in_("lifecycle", ["active", "delivered"])
            .limit(1)
            .execute()
        )
        if hit.data:
            return hit.data[0]["path"]

        # 2. placed copy — same basename, anywhere the Reviewer filed it
        placed = (
            auth.client.table("workspace_files")
            .select("path, updated_at")
            .eq("user_id", auth.user_id)
            .like("path", f"%/{slug}.md")
            .in_("lifecycle", ["active", "delivered"])
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if placed.data:
            return placed.data[0]["path"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] deterministic memory-path resolve failed: %s", exc)

    return None


async def resolve_trace_path(auth: Any, subject: str) -> Optional[str]:
    """Resolve a `trace` subject to the file that IS the subject (ADR-372 fix).

    `trace` is about the HISTORY of a specific thing, so it must resolve to the
    file the subject NAMES — not a file that merely mentions it. The prior path
    (QueryKnowledge FTS top-hit) ranks by relevance, which systematically prefers
    prose files that *talk about* a subject over the terse state file that *is*
    it — and those mention-files tend to be single-revision, so the timeline came
    back empty/trivial on every real subject (live finding 2026-06-26: `SPY` →
    regime-state.md (1 rev) not SPY.yaml (14); `standing_intent`/`calibration`/
    `mandate` all → principles.md (1 rev)).

    Resolution order (first hit wins), all scoped to the caller's substrate:
      1. NAME MATCH — a file whose basename is the subject, ANY extension
         (`SPY` → SPY.yaml, `standing_intent` → standing_intent.md). Tries the
         raw subject, the slug, and the slug with `_`/`-` separators. Among
         name-matches, the one with the MOST revisions wins (the historied one).
      2. HISTORY-WEIGHTED FTS — fall back to full-text candidates, but re-rank
         them: prefer a candidate whose PATH contains the subject token, then
         break ties toward more revisions. A 20-revision file the subject names
         beats a 1-revision file that merely mentions it.
      3. None → caller reports "nothing recorded".

    Returns the absolute /workspace/ path or None.
    """
    from services.primitives.registry import execute_primitive

    raw = (subject or "").strip()
    if not raw:
        return None
    slug = _slugify(raw)
    # Candidate basenames to match against (no extension assumed).
    stems = {raw, slug, slug.replace("-", "_"), slug.replace("_", "-")}
    stems = {s for s in stems if s}

    async def _rev_count(path: str) -> int:
        try:
            r = (
                auth.client.table("workspace_file_versions")
                .select("id", count="exact")
                .eq("user_id", auth.user_id)
                .eq("path", path)
                .execute()
            )
            return r.count or 0
        except Exception:  # noqa: BLE001
            return 0

    try:
        # 1. NAME MATCH — basename == stem.<ext>, any extension. ilike is
        #    case-insensitive so `spy`/`SPY` both hit SPY.yaml.
        name_hits: list[str] = []
        for stem in stems:
            res = (
                auth.client.table("workspace_files")
                .select("path")
                .eq("user_id", auth.user_id)
                .in_("lifecycle", ["active", "delivered"])
                .ilike("path", f"%/{stem}.%")
                .limit(20)
                .execute()
            )
            name_hits.extend(row["path"] for row in (res.data or []))
        name_hits = list(dict.fromkeys(name_hits))  # dedupe, preserve order
        if name_hits:
            # the historied one wins among name-matches
            best, best_revs = name_hits[0], -1
            for p in name_hits:
                n = await _rev_count(p)
                if n > best_revs:
                    best, best_revs = p, n
            return best
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] trace name-match resolve failed: %s", exc)

    # 2. HISTORY-WEIGHTED FTS fallback.
    try:
        qk = await execute_primitive(
            auth, "QueryKnowledge", {"query": _naturalize_subject(raw), "limit": 8}
        )
        results = (qk.get("results") or []) if qk.get("success") else []
        if not results:
            return None
        subj_token = slug.replace("-", "").replace("_", "")

        async def _score(path: str) -> tuple:
            path_match = 1 if subj_token and subj_token in path.lower().replace("-", "").replace("_", "") else 0
            revs = await _rev_count(path)
            return (path_match, revs)

        scored = []
        for r in results:
            p = r.get("path", "")
            if p:
                scored.append((await _score(p), p))
        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)  # path-match then revs
        return scored[0][1]
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] trace FTS resolve failed: %s", exc)
        return None


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

    # Deterministic round-trip first (Finding 1): if the subject was saved via
    # `remember(about=subject)`, it lives at a known path — find it by path
    # before any fuzzy search. This guarantees save-then-recall-same-subject
    # works regardless of embeddings or tsquery slug-AND-matching. We still run
    # QueryKnowledge afterward for additional related material, then dedupe.
    det_path = None if (question and question.strip()) else await resolve_memory_path(auth, subject)
    det_chunk = None
    if det_path:
        try:
            row = (
                auth.client.table("workspace_files")
                .select("path, content, summary, updated_at")
                .eq("user_id", auth.user_id)
                .eq("path", det_path)
                .limit(1)
                .execute()
            )
            if row.data:
                r0 = row.data[0]
                det_chunk = {
                    "path": r0.get("path", det_path),
                    "excerpt": _short_excerpt(r0.get("content") or r0.get("summary") or ""),
                    "last_updated": r0.get("updated_at"),
                    "domain": extract_domain_from_path(r0.get("path", det_path)),
                    "source_tag": _extract_provenance_tag(r0.get("content")),
                }
        except Exception as exc:  # noqa: BLE001
            logger.debug("[MCP] recall deterministic read failed: %s", exc)

    # Fuzzy fallback / augmentation — naturalize the subject so a slug doesn't
    # AND-match prose (Finding 1b).
    result = await execute_primitive(auth, "QueryKnowledge", {
        "query": question or _naturalize_subject(subject),
        "domain": normalized_domain,
        "limit": limit,
    })
    # A QueryKnowledge failure is non-fatal when the deterministic hit already
    # found the material — the round-trip must not break on the fuzzy path.
    raw = (result.get("results") or []) if result.get("success") else []
    if not result.get("success") and not det_chunk:
        return {"success": False, "error": result.get("error", "query_failed"),
                "message": result.get("message", "recall failed"), "subject": subject}

    fuzzy_chunks = [
        {
            "path": r.get("path", ""),
            "excerpt": _short_excerpt(r.get("content_preview") or r.get("summary") or ""),
            "last_updated": r.get("updated_at"),
            "domain": r.get("domain") or extract_domain_from_path(r.get("path", "")),
            "source_tag": _extract_provenance_tag(r.get("content_preview")),
        }
        for r in raw
    ]

    # Deterministic chunk leads; dedupe fuzzy chunks by path.
    chunks: list[dict] = []
    seen: set[str] = set()
    for c in ([det_chunk] if det_chunk else []) + fuzzy_chunks:
        p = c.get("path", "")
        if p in seen:
            continue
        seen.add(p)
        chunks.append(c)

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
        "total_matches": result.get("count", len(chunks)) if result.get("success") else len(chunks),
        "returned": len(chunks),
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

    # Resolve subject → the file that IS the subject (ADR-372 fix). trace is about
    # the HISTORY of a specific thing, so resolution must prefer the file the
    # subject NAMES (name-match first), then history-weighted FTS — NOT the raw
    # FTS top-hit, which ranks files that merely MENTION the subject over the
    # state file that is it (live finding 2026-06-26: every real subject resolved
    # to a 1-revision prose/report file, so the timeline was always empty). The
    # memory-round-trip case (remember(about=X) → operation/memory/{slug}.md) is
    # subsumed: resolve_trace_path's name-match catches {slug}.md too.
    path = await resolve_trace_path(auth, subject)
    if not path:
        return {
            "success": True, "subject": subject, "path": None, "history": [],
            "explanation": (
                f"YARNNN has no recorded material about '{subject}' to trace. "
                "Nothing has been authored on this subject yet."
            ),
        }
    # ListRevisions queries `workspace_file_versions` by the CANONICAL stored
    # path, which carries the `/workspace/` prefix (the authored-substrate
    # revision rows are absolute). Do NOT strip it — a bare path matches zero
    # rows and `trace` (the differentiator) returns an empty chain on every
    # call. Verified: bare `operation/…` → 0 revisions; `/workspace/operation/…`
    # → the real chain. (Live test 2026-06-25 surfaced this; the Reviewer had
    # placed the dump — 2 revisions existed — but trace read the wrong key.)
    abs_path = path if path.startswith("/workspace/") else "/workspace/" + path.lstrip("/")
    lr = await execute_primitive(auth, "ListRevisions", {"path": abs_path, "limit": max(1, min(int(limit or 10), 30))})
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

    # ADR-372: embed each revision's diff-against-its-PREDECESSOR inline, so the
    # rich-render timeline widget can show click-to-expand diffs with ZERO
    # callback (preserves the ADR-368 three-verb surface). Composed server-side
    # via the existing DiffRevisions primitive — the same one-round composition
    # pattern recall/trace already use. `revisions` is newest-first, so a
    # revision's predecessor is the NEXT item; the oldest revision has no
    # predecessor and carries `diff: None`. Best-effort: a diff failure leaves
    # that entry's `diff: None` and never breaks trace. Bounded by `limit`.
    await _embed_revision_diffs(auth, abs_path, revisions, history)

    return {
        "success": True,
        "subject": subject,
        "path": abs_path,
        "history": history,            # newest first; each entry carries optional `diff`
        "returned": len(history),
        "citations": [abs_path],
        "explanation": (
            f"The authored history of '{subject}' — {len(history)} revision(s), "
            "each attributed to who changed it and when. This is the cross-LLM "
            "provenance no plain storage connector can show."
        ),
    }


async def _embed_revision_diffs(
    auth: Any,
    abs_path: str,
    revisions: list,
    history: list,
) -> None:
    """Attach a `diff` (unified-diff text vs the predecessor) to each history
    entry, in place (ADR-372). Newest-first ordering: entry i's predecessor is
    revision i+1. The oldest entry has no predecessor → `diff: None`. Each diff
    is one DiffRevisions call; best-effort per pair so one failure never breaks
    the whole trace.
    """
    from services.primitives.registry import execute_primitive

    for i, entry in enumerate(history):
        entry["diff"] = None  # default — overwritten on success
        predecessor_idx = i + 1
        if predecessor_idx >= len(revisions):
            continue  # oldest revision: nothing to diff against
        from_id = revisions[predecessor_idx].get("id")
        to_id = entry.get("revision_id")
        if not from_id or not to_id:
            continue
        try:
            dr = await execute_primitive(
                auth, "DiffRevisions",
                {"path": abs_path, "from_rev": from_id, "to_rev": to_id},
            )
            if dr.get("success"):
                entry["diff"] = dr.get("diff") or ""
        except Exception as exc:  # noqa: BLE001 — a diff must never break trace
            logger.debug("[MCP] trace diff embed failed for %s: %s", to_id, exc)


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
