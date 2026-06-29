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

from services.workspace_paths import INBOUND_ROOT  # the raw intake lane (ADR-376/DP32)

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
# placement — foreign-LLM raw observations land in the inbound/ raw lane and the
# seat DERIVES into operation/ by judgment (ADR-376/DP32). The ADR-151 DOMAIN_KEYWORDS table +
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

    Values: the `id` of any registered HostProfile (ADR-379 — chatgpt, claude.ai,
    claude_desktop, claude_code, gemini, cursor, copilot, perplexity, …), or
    'unknown'. The canonical list lives in `mcp_server.presentation.hosts.HOSTS`.
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


# =============================================================================
# The honest-state vocabulary — ONE shared 4-value scale across recall + trace
# =============================================================================
# (2026-06-29, hardened after a live discrimination test surfaced two seams.)
# recall reports `confidence`, trace reports `resolution`; BOTH use this SAME
# vocabulary with the SAME meaning, and the field is ALWAYS PRESENT (never absent
# on a miss — the earlier recall-miss dropped the field entirely, an honest-state
# hole a `switch(confidence)` integrator hits as `undefined`). Documented in
# docs/features/mcp/honest-state-contract.md.
#
#   "high"      — confident hit (recall: dominant/exact; trace: exact name-match).
#                 Use it.
#   "ambiguous" — found multiple, none dominant. The host should surface the
#                 candidates and ASK / CONFIRM rather than crowning the top.
#   "weak"      — found SOMETHING but low-confidence (recall: below the dominant
#                 bar; trace: an FTS mention-match, not a name-match). Treat as a
#                 loose lead, not an answer.
#   "none"      — NOTHING recorded at all. The strongest "nothing here" signal;
#                 answer from own knowledge. (Distinct from "weak": weak = a real
#                 but shaky hit; none = a true miss. This split is why the two
#                 tools no longer overload one word for both.)
CONFIDENCE_HIGH = "high"
CONFIDENCE_AMBIGUOUS = "ambiguous"
CONFIDENCE_WEAK = "weak"
CONFIDENCE_NONE = "none"

# Recall confidence thresholds (derived from the similarity QueryKnowledge already
# returns — ZERO extra inference / DB cost). The connector's job is fidelity, not
# judgment: it reports the honest state so the HOST LLM (the one in the
# conversation) decides answer-vs-clarify. It never clarifies or guesses itself
# (ADR-368 D1 bright line: recall returns material, the host explains). The bug
# this fixes: a deterministic OR top-fuzzy hit was crowned as "the answer" even
# when other candidates scored nearly as high — laundering ambiguity into false
# certainty, so the host never learned it should clarify.
_RECALL_DOMINANT_MIN = 0.55   # a top score this high is a confident standalone hit
_RECALL_AMBIGUOUS_GAP = 0.08  # if #1 and #2 are within this, no clear winner


def _recall_confidence(chunks: list[dict]) -> str:
    """Derive an honest confidence label from chunks (pure; no inference).

    Returns a value from the shared honest-state vocabulary (see above):
      'high'      — exact deterministic hit, single chunk, or dominant top score.
      'ambiguous' — multiple candidates, close top scores, no dominant one.
      'weak'      — the best score is below the dominant bar (loose matches only).
      'none'      — no chunks at all (a true miss). The field is ALWAYS present.
    """
    if not chunks:
        return CONFIDENCE_NONE
    # An exact subject→path resolve is maximally confident regardless of fuzzy scores.
    if chunks[0].get("match") == "exact":
        return CONFIDENCE_HIGH
    sims = sorted((c["similarity"] for c in chunks if "similarity" in c), reverse=True)
    if not sims:
        # BM25/list path (no scores) — single hit is high; multiple is ambiguous.
        return CONFIDENCE_HIGH if len(chunks) == 1 else CONFIDENCE_AMBIGUOUS
    top = sims[0]
    second = sims[1] if len(sims) > 1 else 0.0
    if top >= _RECALL_DOMINANT_MIN and (top - second) >= _RECALL_AMBIGUOUS_GAP:
        return CONFIDENCE_HIGH
    if len(sims) > 1 and (top - second) < _RECALL_AMBIGUOUS_GAP:
        return CONFIDENCE_AMBIGUOUS
    if top < _RECALL_DOMINANT_MIN:
        return CONFIDENCE_WEAK
    return CONFIDENCE_HIGH


def _slugify(text: str) -> str:
    """Simple slug derivation for entity path matching."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _normalize_client_id(raw: str) -> Optional[str]:
    """
    Map an OAuth client id / User-Agent / registered name to a canonical host id.

    ADR-379: the substring chain that used to live here moved to the single Host
    Profile registry (`mcp_server.presentation.hosts`) — one resolver, one place a
    host name appears. A new host is a registry entry, not a new `if` here. The
    import is lazy to keep the dependency direction clean (services/ does not
    import the interop-face presentation layer at module load).
    """
    if not raw:
        return None
    from mcp_server.presentation.hosts import resolve_host_id
    return resolve_host_id(raw)


# =============================================================================
# dispatch_remember_this — ADR-235 routing for the MCP write path
# =============================================================================


# The RAW intake lane (ADR-376 / FOUNDATIONS DP32). A foreign-LLM `remember` is
# an attributed RAW observation; it lands here IMMUTABLY, and the seat DERIVES
# the workspace's understanding from it into operation/ (citing this raw via
# `derived_from`). Per-{client} sublane is single-writer by construction.
INBOUND_MCP_PREFIX = "inbound/mcp/"
INBOUND_MCP_DEFAULT_SLUG = "inbox"


def resolve_remember_path(about: Optional[str], client_name: Optional[str] = None) -> str:
    """Resolve where a foreign-LLM `remember` RAW observation lands (ADR-376/DP32).

    The ledger-intake axiom: a contribution enters as an ATTRIBUTED RAW
    observation, kept distinct from what the workspace makes of it. The MCP layer
    CAPTURES the dump immutably in the raw lane — `inbound/mcp/{client}/{slug}.md`
    — attributed `yarnnn:mcp:{client}`; the integrity wake then invokes the seat
    to DERIVE the understanding into operation/ (citing this raw), rather than
    rewriting the dump in place (the pre-ADR-376 conflation — one namespace doing
    two jobs, which is why `operation/memory/` had to be overwritten).

    The raw lane is OUTSIDE the topology cut (no semantic-class authority) and is
    the foreign caller's writable home (CALLER_WRITE_POLICY["mcp"] does not lock
    inbound/). It is never a locked root, never a program's structured output
    tree (`reports/`/`trading/`/`specs/`), never an invented domain folder.

    `about` only names the raw observation so the seat (and `trace`) can see it;
    `client_name` segregates the per-principal sublane (single-writer by
    construction; ADR-373's per-principal grant later enforces it):
        about="Acme Corp", client="claude.ai" → inbound/mcp/claude.ai/acme-corp.md
        about=None,        client="claude.ai" → inbound/mcp/claude.ai/inbox.md
        about=None,        client=None        → inbound/mcp/unknown/inbox.md
    """
    client = _slugify(client_name or "") or "unknown"
    hint = (about or "").strip()
    slug = _slugify(hint) if hint else ""
    if not slug:
        slug = INBOUND_MCP_DEFAULT_SLUG
    return f"{INBOUND_MCP_PREFIX}{client}/{slug}.md"


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


def _normalize_inbound_ref(ref: str) -> Optional[str]:
    """Normalize one raw-citation token to an absolute /workspace/ path."""
    ref = (ref or "").strip().strip("`").strip("'\"").rstrip(",")
    if not ref or ref in ("[", "]", "-"):
        return None
    return ref if ref.startswith("/workspace/") else "/workspace/" + ref.lstrip("/")


def _extract_derived_from_list(content: Optional[str]) -> list[str]:
    """Read ALL `derived_from:` citations from a derived file (ADR-376/DP32 D3).

    A derived object cites the raw observation(s) it was built from. The MCP
    `remember` derivation cites ONE raw dump; a PERCEPTION distillation cites N
    raw web observations (one signal from several feeds — the first multi-cite
    case, ADR-376 §9 DECIDED 2026-06-26: `derived_from` is a list, the single
    case is the one-element list). This reader is tolerant of all three on-wire
    shapes so a derived file authored by the seat (free-form `.md`) or written
    mechanically (`.yaml` block list) both walk cleanly:

        derived_from: /workspace/inbound/mcp/claude.ai/acme.md        # bare scalar
        derived_from: [a.md, b.md]                                    # inline list
        derived_from:                                                 # block list
          - /workspace/inbound/web/stereogum/2026-06-26T10:00:00Z.md
          - /workspace/inbound/web/pitchfork/2026-06-26T10:00:00Z.md

    Returns absolute /workspace/ paths (deduped, order-preserved). Scans the
    header region (first ~20 lines — a block list can run several lines).
    """
    if not content:
        return []
    lines = content.split("\n")
    refs: list[str] = []
    # Find the `derived_from:` key in the header region (first ~20 lines); once
    # found, a block list may run as many lines as it has cites (perception can
    # distill N feeds), so consume the WHOLE following block, not a fixed window.
    for i, line in enumerate(lines[:20]):
        m = re.match(r"\s*derived_from:\s*(.*)$", line)
        if not m:
            continue
        rest = m.group(1).strip()
        if rest.startswith("["):
            # inline list — strip brackets, split on commas
            for tok in rest.strip("[]").split(","):
                norm = _normalize_inbound_ref(tok)
                if norm:
                    refs.append(norm)
        elif rest and not rest.startswith("#"):
            # bare scalar on the same line
            norm = _normalize_inbound_ref(re.split(r"[\s|<>\"']", rest, 1)[0])
            if norm:
                refs.append(norm)
        else:
            # block list — consume ALL following `- item` lines (unbounded by the
            # header window; stops at the first non-`- ` line, e.g. the next key)
            for nxt in lines[i + 1:]:
                bm = re.match(r"\s*-\s+(.+)$", nxt)
                if not bm:
                    break
                norm = _normalize_inbound_ref(bm.group(1))
                if norm:
                    refs.append(norm)
        break  # only the first derived_from: key in the header region
    # dedupe, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def _extract_derived_from(content: Optional[str]) -> Optional[str]:
    """Read the FIRST `derived_from:` citation (ADR-376/DP32 D3).

    The single-cite reader (the MCP `remember` derivation cites one raw dump).
    Returns the first cited absolute path or None. For the multi-cite case
    (perception distilling N observations), use `_extract_derived_from_list`.
    Tolerant of YAML frontmatter, an early bare line, an inline/block list.
    """
    refs = _extract_derived_from_list(content)
    return refs[0] if refs else None


async def _find_derived_from_raw(auth: Any, raw_abs_path: str) -> Optional[str]:
    """Reverse-walk the citation: find the DERIVED file that cites `raw_abs_path`.

    The seat derives a raw observation into operation/ and names that file by its
    own judgment (not the subject slug), citing the raw via `derived_from`. So the
    only reliable way to reach the derived understanding FROM the raw is the
    citation itself. Returns the newest active operation/ file whose content cites
    the raw path, or None (no derivation yet). Best-effort; raw-path may be bare or
    absolute (both are matched against the stored `derived_from` text).
    """
    bare = raw_abs_path[len("/workspace/"):] if raw_abs_path.startswith("/workspace/") else raw_abs_path
    try:
        hits = (
            auth.client.table("workspace_files")
            .select("path, content, updated_at")
            .eq("user_id", auth.user_id)
            .like("path", "/workspace/operation/%")
            .ilike("content", "%derived_from%")
            .order("updated_at", desc=True)
            .limit(25)
            .execute()
        ).data or []
        for h in hits:
            cited = _extract_derived_from(h.get("content"))
            if cited and (cited == raw_abs_path or cited.endswith(bare) or bare.endswith(cited.lstrip("/workspace/"))):
                return h["path"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] reverse derived_from walk failed: %s", exc)
    return None


async def resolve_memory_path(auth: Any, subject: str) -> Optional[str]:
    """Resolve a `recall`/`trace` subject to its authored path DETERMINISTICALLY.

    The save→read round-trip is deterministic, not fuzzy. Under the ledger-intake
    axiom (ADR-376/DP32) a `remember(about=X)` lands a RAW observation at
    `inbound/mcp/{client}/{slug(X)}.md`; the seat then DERIVES the understanding
    into operation/ (a file it typically names after the subject, citing the raw
    via `derived_from`). `recall` wants the **understanding first, raw as the
    receipt behind it** (ADR-376 §4): so this resolves DERIVED-FIRST.

    Resolution order (first hit wins), all scoped to the caller's substrate:
        1. DERIVED — an active operation/ (or other non-inbound) file whose
           basename is {slug}.md (the seat's filed understanding; if none yet,
           there is simply no derived object — legible, not ambiguous);
        2. RAW — the raw observation at inbound/mcp/{*}/{slug}.md (the source of
           record, before any fuzzy search — so the round-trip never depends on
           embeddings or FTS even before the seat has derived);
        3. None → caller falls back to fuzzy QueryKnowledge.

    Returns the absolute /workspace/ path or None.
    """
    slug = _slugify(subject or "")
    if not slug:
        return None

    try:
        # 1. DERIVED — same basename, NOT in the raw lane (the seat's filed
        #    understanding). Prefer it: recall returns understanding, raw is the
        #    receipt. Newest wins if several.
        derived = (
            auth.client.table("workspace_files")
            .select("path, updated_at")
            .eq("user_id", auth.user_id)
            .like("path", f"%/{slug}.md")
            .not_.like("path", f"%/{INBOUND_ROOT}%")
            .in_("lifecycle", ["active", "delivered"])
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if derived.data:
            return derived.data[0]["path"]

        # 2. RAW — the inbound/ source of record (deterministic, pre-derive).
        raw = (
            auth.client.table("workspace_files")
            .select("path, updated_at")
            .eq("user_id", auth.user_id)
            .like("path", f"%/{INBOUND_ROOT}%/{slug}.md")
            .in_("lifecycle", ["active", "delivered"])
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if raw.data:
            return raw.data[0]["path"]
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] deterministic memory-path resolve failed: %s", exc)

    return None


async def resolve_trace_path(auth: Any, subject: str) -> tuple[Optional[str], str]:
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

    Returns `(path, resolution)` on the SHARED honest-state vocabulary (the lower
    three values mean exactly what they mean in recall, so one host handler works):
      "exact"     — a SINGLE file's basename IS the subject (confident; trace's
                    name for recall's "high"). Narrate.
      "ambiguous" — several name-matches competed (we picked one) OR FTS returned
                    several candidates. Host should confirm/surface before narrating.
      "weak"      — only a single FTS MENTION-match (a loose lead, never a
                    name-match — "exact" is reserved for name-matches). Narrate
                    cautiously / confirm.
      "none"      — nothing matched at all (a true miss). `(None, "none")`.
    Zero added inference — derived from the resolve branch already taken.
    """
    from services.primitives.registry import execute_primitive

    raw = (subject or "").strip()
    if not raw:
        return None, CONFIDENCE_NONE
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
            # A SINGLE name-match is the file that IS the subject → "exact" (trace's
            # name for the confident value, ≡ recall's "high"). Multiple competing
            # name-matches means we PICKED one → "ambiguous" (same meaning as recall).
            return best, ("exact" if len(name_hits) == 1 else CONFIDENCE_AMBIGUOUS)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] trace name-match resolve failed: %s", exc)

    # 2. HISTORY-WEIGHTED FTS fallback.
    try:
        qk = await execute_primitive(
            auth, "QueryKnowledge", {"query": _naturalize_subject(raw), "limit": 8}
        )
        results = (qk.get("results") or []) if qk.get("success") else []
        if not results:
            return None, CONFIDENCE_NONE
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
            return None, CONFIDENCE_NONE
        scored.sort(key=lambda x: x[0], reverse=True)  # path-match then revs
        # FTS fallback = mention-ranking, inherently looser than a name-match — so
        # it NEVER returns "exact" ("exact" is reserved for the name-match branch
        # above, where the file's basename IS the subject). Honest mapping onto the
        # shared vocabulary: a SINGLE loose candidate → "weak" (a lead, not an
        # answer — narrate cautiously / confirm); SEVERAL candidates → "ambiguous"
        # (the host should surface the choice). Either way the host should confirm
        # before narrating "how your thinking evolved".
        _top_score, top_path = scored[0]
        resolution = CONFIDENCE_WEAK if len(scored) == 1 else CONFIDENCE_AMBIGUOUS
        return top_path, resolution
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] trace FTS resolve failed: %s", exc)
        return None, CONFIDENCE_NONE


async def dispatch_remember_this(
    auth: Any,
    stamped_text: str,
    about: Optional[str] = None,
    client_name: Optional[str] = None,
) -> dict:
    """Commit a `remember` RAW observation to the inbound/ lane (ADR-376/DP32).

    A foreign LLM's `remember` is an attributed RAW observation: it appends to
    `inbound/mcp/{client}/{slug}.md` (the raw lane — writable by the `yarnnn:mcp`
    caller, outside the topology cut, never rewritten). The seat then DERIVES the
    workspace's understanding from it into operation/ (citing this raw), invoked
    by the integrity wake the caller fires on success — placement is JUDGMENT and
    a separate, citing act, not a rewrite of the raw (ADR-376 §5 — `operation/
    memory/` conflated capture and understanding in one file; the split fixes it).
    The ADR-307 gate at `execute_primitive` is still the authority; this function
    never constructs a locked path.

    ADR-288: `authored_by` defaults to `auth.caller_identity` (`yarnnn:mcp:{client}`).
    Returns the WriteFile primitive result unchanged.
    """
    from services.primitives.registry import execute_primitive

    path = resolve_remember_path(about, client_name=client_name)
    return await execute_primitive(
        auth,
        "WriteFile",
        {
            "scope": "workspace",
            "path": path,
            "content": stamped_text,
            "mode": "append",
            "message": "remember → inbound/ raw lane (awaiting seat derive-and-cite)",
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
            # Carry the per-row similarity QueryKnowledge already computed (semantic
            # path only; absent on BM25/list). Zero extra cost — it was being
            # discarded. The host uses it to decide answer-vs-clarify (see below).
            **({"similarity": r["similarity"]} if "similarity" in r else {}),
        }
        for r in raw
    ]

    # Deterministic chunk leads; dedupe fuzzy chunks by path. The deterministic hit
    # is an EXACT subject→path resolve, so it is maximally confident — mark it.
    if det_chunk is not None:
        det_chunk = {**det_chunk, "match": "exact"}
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
            "returned": 0,
            # ALWAYS emit `confidence` — even on a true miss. The earlier branch
            # dropped the field, so a host's switch(confidence) hit `undefined` on a
            # clean miss (the honest-state hole the live test surfaced). "none" is
            # the strongest "nothing here" signal — distinct from "weak" (a real
            # but shaky hit). The field is now never absent.
            "confidence": CONFIDENCE_NONE,
            "citations": [],
            "explanation": (
                f"YARNNN has no accumulated memory about '{subject}'. The user "
                "hasn't recorded this yet. Answer from your own knowledge if you can."
            ),
        }
    # total_matches must be >= returned: it counts everything that matched, and we
    # are handing back `chunks` (which may include the DETERMINISTIC path-resolved
    # chunk that the fuzzy QueryKnowledge `count` does not see). Sourcing
    # total_matches from the fuzzy count alone produced the {total_matches:0,
    # returned:1} inconsistency (2026-06-29) — the deterministic hit is a real
    # match the ranked counter missed. Reconcile to the max so the counter can
    # never report fewer matches than rows actually returned.
    fuzzy_count = result.get("count", 0) if result.get("success") else 0

    # Honest-state signal (zero inference): let the HOST decide answer-vs-clarify.
    confidence = _recall_confidence(chunks)
    explanation = None
    if confidence == "ambiguous":
        explanation = (
            f"Multiple recorded items could match '{subject}' and none clearly "
            f"dominates. Rather than assume the first, consider asking the user "
            f"which they mean — the candidates are in `chunks` (with `similarity`)."
        )
    elif confidence == "weak":
        explanation = (
            f"YARNNN has nothing that closely matches '{subject}' — only loose "
            f"matches below the confidence bar. Treat these as weak; you may need "
            f"to answer from your own knowledge or ask the user to be more specific."
        )
    out = {
        "success": True, "subject": subject, "chunks": chunks,
        "total_matches": max(fuzzy_count, len(chunks)),
        "returned": len(chunks),
        "confidence": confidence,
        "citations": [c["path"] for c in chunks],
    }
    if explanation:
        out["explanation"] = explanation
    return out


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
    path, resolution = await resolve_trace_path(auth, subject)
    if not path:
        return {
            "success": True, "subject": subject, "path": None, "history": [],
            # "none" = nothing recorded at all (a true miss) — the SAME meaning as
            # recall's "none". Was "weak", which overloaded the word: trace's empty
            # case is a true miss, not a low-confidence hit. Shared vocabulary now.
            "resolution": CONFIDENCE_NONE,
            "explanation": (
                f"YARNNN has no recorded material about '{subject}' to trace. "
                "Nothing has been authored on this subject yet."
            ),
        }

    # ADR-376/DP32 forward-walk: if resolution landed on a RAW observation
    # (inbound/), prefer the DERIVED understanding the seat authored from it — the
    # file whose `derived_from` cites this raw. The seat names the derived file by
    # its own judgment (e.g. nvda-2026-06-27.md from subject "NVDA earnings setup"),
    # so name-match can't reach it from the subject; the citation can. `trace` is
    # about the evolution of the UNDERSTANDING; the raw is appended as its origin
    # (the derived-file branch below adds it via _extract_derived_from). If no
    # derived file cites the raw yet, trace the raw as-is (a clean pre-derive state).
    if f"/{INBOUND_ROOT}" in path:
        derived_path = await _find_derived_from_raw(auth, path)
        if derived_path:
            path = derived_path
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

    # ADR-376/DP32: if this derived file CITES a raw observation (`derived_from`),
    # walk back and APPEND the raw's chain — so trace shows the full provenance:
    # the seat's derived understanding AND the foreign contributor's raw source
    # it was built from (the structurally-legible "contributed via X → derived by
    # the seat" chain, not approximate in-place edit history). Best-effort.
    raw_path = None
    citations = [abs_path]
    try:
        head = (
            auth.client.table("workspace_files")
            .select("content")
            .eq("user_id", auth.user_id)
            .eq("path", abs_path)
            .limit(1)
            .execute()
        )
        # ADR-376 §9 DECIDED (2026-06-26): derived_from is a LIST — one derived
        # object may cite N raw observations (the MCP `remember` derivation cites
        # one; a PERCEPTION distillation cites several feeds). Walk ALL cited raws
        # and append each chain, so trace shows the complete provenance fan-in.
        derived_froms = _extract_derived_from_list((head.data or [{}])[0].get("content")) if head.data else []
        for cited in derived_froms:
            if not cited or cited == abs_path:
                continue
            raw_lr = await execute_primitive(
                auth, "ListRevisions", {"path": cited, "limit": max(1, min(int(limit or 10), 30))}
            )
            cited_revs = raw_lr.get("revisions") or []
            for rev in cited_revs:
                history.append({
                    "authored_by": rev.get("authored_by"),
                    "when": rev.get("created_at"),
                    "change": rev.get("message"),
                    "revision_id": rev.get("id"),
                    "raw_source": True,         # marks this as a cited raw observation
                    "source_path": cited,
                })
            if cited_revs:
                if raw_path is None:
                    raw_path = cited       # the first cited raw (response field, back-compat)
                citations.append(cited)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] derived_from walk failed (non-fatal): %s", exc)

    n_raw = len(citations) - 1
    chain_note = (
        (f" — including the cited raw observation at `{raw_path}`"
         if n_raw == 1 else
         f" — including {n_raw} cited raw observations (e.g. `{raw_path}`)")
        + " (the source(s) of record this understanding was derived from)"
        if raw_path else ""
    )
    # Honest-state: if resolution was NOT confident ("exact"), tell the host so it
    # can CONFIRM it traced the right thing before narrating "how your thinking on X
    # evolved" — a wrong trace reads as authoritative, the failure mode this guards
    # (parallel to recall's ambiguous/weak). "ambiguous" = several candidates;
    # "weak" = a single loose FTS lead. Both warrant a confirm.
    if resolution in (CONFIDENCE_AMBIGUOUS, CONFIDENCE_WEAK):
        explanation = (
            f"Traced `{abs_path}` for '{subject}', but the subject didn't resolve "
            f"to a single unambiguous file — this is the closest match, not a "
            f"certain one. Before narrating its history as '{subject}', consider "
            f"confirming with the user that this is the thing they meant."
        )
    else:
        explanation = (
            f"The authored history of '{subject}' — {len(history)} revision(s), "
            f"each attributed to who changed it and when{chain_note}. This is the "
            "cross-LLM provenance no plain storage connector can show."
        )
    return {
        "success": True,
        "subject": subject,
        "path": abs_path,
        "resolution": resolution,      # exact | ambiguous (honest-state, 2026-06-29)
        "derived_from": raw_path,      # the cited raw observation, if any (ADR-376)
        "history": history,            # newest first; derived chain then raw chain
        "returned": len(history),
        "citations": citations,
        "explanation": explanation,
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
# Derive-and-cite model (ADR-376/DP32 — the ledger-intake axiom): a foreign LLM's
# `remember` is a RAW observation — it commits IMMUTABLY to the inbound/ raw lane
# (`inbound/mcp/{client}/…`) attributed `yarnnn:mcp:{client}`. This adapter then
# INVOKES the seat to DERIVE the workspace's understanding from it — a SEPARATE,
# CITING act authored into operation/ (carrying `derived_from`) — NOT a rewrite or
# move of the raw (the raw is never rewritten; it stays as the source of record).
# Derivation lives with the judgment seat — which understands the workspace and
# can write everywhere the foreign caller can't — not with the least-context
# foreign caller. The foreign tool never blocks on it; the raw is captured
# instantly, the seat derives shortly after (or derives nothing — a clean state).
#
# The two-object split is git-legible: the raw's `yarnnn:mcp:{client}` origin
# survives forever on its inbound/ revision; the seat's understanding is a SEPARATE
# `reviewer:<id>` revision on a DIFFERENT operation/ file that CITES the raw via
# `derived_from`; the `trace` verb walks the citation to show the whole chain
# ("contributed via claude.ai → derived by the seat"). The instruction reaches the
# seat in the wake's hook.prompt (ADR-310 D3) — not a new payload field — so the
# substrate_event contract stays frozen.

async def submit_foreign_write_wake(
    auth: Any,
    *,
    written_path: str,
    target: str,
    client_name: str,
) -> None:
    """Best-effort: invoke the seat to DERIVE-AND-CITE from a raw observation.

    Resolves the head revision_id for the just-written raw path and submits a
    substrate_event wake whose hook.prompt invokes the seat to DERIVE the
    workspace's understanding from the raw observation into operation/ — a NEW,
    separate, citing act (carrying `derived_from`), NOT a rewrite of the raw
    (ADR-376/DP32: the raw is never rewritten; understanding is a distinct
    attributed object that cites its source). Never raises — a wake failure must
    not affect the `remember` result (the raw already committed and is attributed).

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
            f"The operator contributed a RAW observation from outside YARNNN (via "
            f"MCP, client: {client_name}). It is captured immutably in the raw "
            f"intake lane at `{abs_path}` — a source of record, NOT its understood "
            f"home. Your job is to DERIVE the workspace's understanding from it, as "
            f"a SEPARATE act — do NOT rewrite or move the raw file (it stays as the "
            f"attributed source of record).\n\n"
            f"Read the raw observation, then AUTHOR (or update) the understanding "
            f"into its real home under `operation/` — a domain file, an entity "
            f"file, agent feedback, or wherever its subject lives — and on that "
            f"derived file include a citation back to the raw source:\n"
            f"    a frontmatter line  `derived_from: {abs_path}`\n"
            f"so the provenance chain (raw contributor → your derived understanding) "
            f"is walkable. Judge the observation against authored ground-truth and "
            f"the mandate while you derive — if it conflicts, surface that. If the "
            f"observation carries no understanding worth deriving yet (pure free "
            f"memory, or nothing actionable), it is legitimate to derive nothing and "
            f"leave it in the raw lane — that is a clean state, not an omission. You "
            f"understand this workspace's structure; the contributing LLM did not, "
            f"which is why the derivation is yours."
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
                "field_change": {"source": "mcp", "target": "inbound-raw-lane"},
                "revision_id": revision_id,
            },
        )
        logger.info(
            "[MCP WAKE] submitted Reviewer wake for foreign write to %s", abs_path
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MCP WAKE] submit failed (non-fatal): %s", exc)
