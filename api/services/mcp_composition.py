"""
MCP Composition Layer — ADR-543 (the file-native interop surface)

Composition module for the interop verbs: open · list · search · save ·
history (share composes in server.py against the share machinery directly).
Each verb is a binding of a kernel verb (ADR-512 D3: read · write · list ·
search · revisions · share) and composes existing kernel primitives
(QueryKnowledge / WriteFile / ListRevisions / DiffRevisions) SERVER-SIDE into a
reason-ready result returned in one round. The chaining lives here (an agentic
context, no round limit), not in a round-limited consumer chat host (claude.ai /
ChatGPT / Gemini connectors) — ADR-368 Correction 1, the binding-channel
constraint ADR-512 and ADR-543 preserve.

ADR-543: the memory ontology (remember / recall / trace, the ADR-169→368
strata) is retired IN FULL. Every verb reads, writes, enumerates, searches, or
histories FILES AT PATHS; every receipt names the path it touched. No verb
presents an object the kernel contract does not have — which is why the phantom
object's bespoke resolution machinery (resolve_remember_path /
resolve_memory_path / resolve_trace_path, the store/fetch-by-key "FLOOR") is
deleted rather than renamed.

Design invariants:
    1. No new primitives — this module is composition over execute_primitive()
       plus direct workspace-scoped substrate reads (`_substrate_scope`).
    2. Zero YARNNN-internal LLM calls on the serving path.
    3. `search` RETURNS material; it does not synthesize — the host LLM explains
       (retrieval, not delegation — ADR-368 D1's bright line, kept by ADR-543).
    4. `open` / `history` are EXACT (a reference names one file; a miss is a
       miss); `list` enumerates; `search` is the only fuzzy verb. Keeping the
       guarantees distinct is the point of having four read verbs.

Canonical product framing:
    docs/features/mcp/README.md and sibling docs — this module is their impl.
    ADR-543 supersedes ADR-368's memory-first surface; ADR-310 two-faces holds.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

# ADR-448: the derived_from parser relocated to authored_substrate (the ledger
# owns its convention — the write door lifts with the SAME parser the history
# walk reads with). Imported, not duplicated.
from services.authored_substrate import (
    extract_derived_from_list as _extract_derived_from_list,
)

# Module-level, deliberately: `compose_open` reads these at module scope
# (2026-08-22 outage: this import block was swallowed into `_substrate_scope`'s
# body by a merge, making the names function-local — every `open` then died
# with NameError while the import-time surface stayed green).
from services.workspace_paths import display_home_alias
from services.workspace_context import (
    describe_if_trashed,
    live_files_filter,
    substrate_scope_filter,
)


def _substrate_scope(auth) -> tuple:
    """(column, value) scope for substrate reads — ADR-407 Phase 1.

    The workspace-keyed mirror of the write path: every read composition
    reaches the COMMONS (whatever workspace the caller's grant binds), not the
    caller's own row set. Closes the audit's 'reads still user-scoped'
    remainder — a foreign LLM or member reading under a grant sees the shared rows.
    """
    return substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None))

logger = logging.getLogger(__name__)


# =============================================================================
# Client identity + shared helpers
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


def _display_authors(auth: Any, rows: list[dict]) -> dict[int, str]:
    """Batched principal display for revision-shaped rows (2026-08-10 identity
    pass). The MCP surface NEVER emits a stored `authored_by` verbatim — raw
    member UUIDs and legacy `<email> via <model>` rows must not cross the
    boundary. One resolution point for every surface:
    `services/principal_display.py`."""
    from services.principal_display import display_author, display_for_rows
    try:
        # workspace_id enables the ADR-431 legacy fallback (whose connection an
        # unstamped external-llm revision acted under). Best-effort.
        try:
            from services.supabase import resolve_workspace_for_principal
            ws_id = resolve_workspace_for_principal(auth.user_id)
        except Exception:  # noqa: BLE001
            ws_id = None
        return display_for_rows(auth.client, rows, workspace_id=ws_id)
    except Exception as exc:  # noqa: BLE001 — display must never break a read
        logger.warning("[MCP] batched principal display failed (%s); degrading", exc)
        # Nameless fallback: pure string resolution (humans degrade to
        # "a workspace member"; every other species renders normally).
        return {
            i: display_author(
                r.get("authored_by"),
                author_identity_uuid=r.get("author_identity_uuid"),
            )
            for i, r in enumerate(rows)
        }


def _short_excerpt(text: str, limit: int = 400) -> str:
    """Trim text to a reasonable excerpt length."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


# =============================================================================
# whoami — where am I standing? (ADR-584 D1)
# =============================================================================


async def compose_whoami(
    auth: Any,
    client_name: Optional[str] = None,
    binding: str = "default",
    scopes: Optional[list] = None,
) -> dict:
    """Answer "where am I, and what may I do here?" in one round (ADR-584 D1).

    Until ADR-584 a connected principal could not learn which workspace it was
    bound to: the workspace lived as a bare UUID on the auth, was used purely as
    a query filter, and was discarded before every response. A model holding the
    wrong commons wrote to it correctly, attributed, and invisibly.

    THE NAME IS AN ADDRESS, NOT INTENT (ADR-584 D3). ADR-533 D6 refuses to port
    the workspace MANDATE — what this workspace is FOR — into a third-party
    context window. The workspace's NAME is the label distinguishing two commons
    a principal can reach, already disclosed to this exact client on the ADR-563
    consent screen the operator read before binding. D6's boundary is unchanged.

    `binding` is the observability half (ADR-584 D2) — it reports whether the
    operator's CHOSEN workspace was honoured, or whether an unreachable stamp
    degraded to the default. That degrade is deliberate and stays; being unable
    to SAY it had happened was the defect.
    """
    from services.supabase import display_workspace_name, get_service_client

    workspace_id = getattr(auth, "workspace_id", None)

    # The workspaces row is read HERE and nowhere else on the MCP path — one
    # lookup, on a verb the model calls once per session, rather than a constant
    # duplicated into every page of every listing (the envelope shape ADR-584 D1
    # rejected).
    raw_name = None
    if workspace_id:
        try:
            res = (
                get_service_client()
                .table("workspaces")
                .select("name")
                .eq("id", workspace_id)
                .limit(1)
                .execute()
            )
            if res.data:
                raw_name = res.data[0].get("name")
        except Exception as exc:  # noqa: BLE001 — identity must never fail a session
            logger.debug("[ADR-584] workspace name lookup failed: %s", exc)

    # None while the row still wears the mint default: an unnamed workspace is
    # described by its address, never by leaking "My Workspace" to a reader it
    # isn't "my" to (the rule display_workspace_name already enforces on invite
    # and share landings).
    name = display_workspace_name(raw_name)

    # What this token may actually DO (ADR-563 tiers). A model that knows it
    # cannot `share` stops offering to.
    from services.mcp_scopes import allowed_verbs, describe_scopes

    held = list(scopes or [])
    capabilities = allowed_verbs(held)

    who = getattr(auth, "caller_identity", None) or "yarnnn:mcp"

    where = f"the workspace named “{name}”" if name else "an unnamed workspace"
    if binding == "fallback":
        situation = (
            f"You are in {where} — the PRINCIPAL'S DEFAULT. The workspace this "
            "connection was bound to at consent is no longer reachable (the "
            "grant may have been revoked), so it degraded rather than failing. "
            "Writes here are correct and attributed, but they are NOT landing in "
            "the workspace the operator chose — say so before writing."
        )
    elif binding == "chosen":
        situation = f"You are in {where} — the workspace chosen for this connection at consent."
    elif binding == "unresolved":
        situation = (
            f"You are in {where}, resolved by fallback — the binding could not be "
            "resolved for this request. Treat the location as unconfirmed."
        )
    else:
        situation = (
            f"You are in {where} — this connection carries no explicit choice, so "
            "it resolves the operator's default workspace."
        )

    return {
        "success": True,
        "workspace": name,
        "workspace_id": workspace_id,
        "workspace_named": bool(name),
        "binding": binding,
        "you": who,
        "client": client_name,
        "scopes": held,
        "capabilities": capabilities,
        "explanation": (
            f"{situation} Your writes are signed as `{who}`. "
            f"You may use: {', '.join(capabilities) or '(none)'}. "
            # describe_scopes returns SENTENCES (a list), not a string — the
            # same copy the operator approved at consent, so what the model is
            # told matches what the human agreed to.
            + " ".join(describe_scopes(held))
        ),
    }


# =============================================================================
# The honest-state vocabulary — search's 4-value `confidence` scale
# =============================================================================
# (2026-06-29, hardened after a live discrimination test surfaced two seams;
# ADR-543 narrows it to `search` — the only fuzzy verb left. `open` / `history`
# are exact by contract, so they report `found`, never a confidence.) The field
# is ALWAYS PRESENT (never absent on a miss — the earlier miss-path dropped the
# field entirely, an honest-state hole a `switch(confidence)` integrator hits as
# `undefined`). Documented in docs/features/mcp/honest-state-contract.md.
#
#   "high"      — confident hit (dominant top score, or a single hit). Use it.
#   "ambiguous" — found multiple, none dominant. The host should surface the
#                 candidates and ASK / CONFIRM rather than crowning the top.
#   "weak"      — found SOMETHING but low-confidence (below the dominant bar).
#                 Treat as a loose lead, not an answer.
#   "none"      — NOTHING matched at all. The strongest "nothing here" signal;
#                 answer from own knowledge. (Distinct from "weak": weak = a real
#                 but shaky hit; none = a true miss.)
CONFIDENCE_HIGH = "high"
CONFIDENCE_AMBIGUOUS = "ambiguous"
CONFIDENCE_WEAK = "weak"
CONFIDENCE_NONE = "none"

# Search confidence thresholds (derived from the similarity QueryKnowledge
# already returns — ZERO extra inference / DB cost). The connector's job is
# fidelity, not judgment: it reports the honest state so the HOST LLM (the one
# in the conversation) decides answer-vs-clarify. It never clarifies or guesses
# itself (search returns material, the host explains). The bug this fixes: a
# top-fuzzy hit was crowned as "the answer" even when other candidates scored
# nearly as high — laundering ambiguity into false certainty, so the host never
# learned it should clarify.
_SEARCH_DOMINANT_MIN = 0.55   # a top score this high is a confident standalone hit
_SEARCH_AMBIGUOUS_GAP = 0.08  # if #1 and #2 are within this, no clear winner

# BM25 grading is MARGIN-based, never count-based (operator receipt 2026-08-23:
# a bullseye at rank-1 trailed by four raw feed dumps graded "ambiguous", so a
# contract-following host asked a clarifying question it already had the answer
# to — false ambiguity, the mirror of the false "none"). ts_rank is not on the
# cosine scale and varies with document length, so dominance is a RATIO.
# Calibrated on live production queries (workspace d5b9029b, 2026-08-23):
#   "market sizing figures"  → 0.99972 vs 0.00000  (∞×)  must grade HIGH
#   "definition of done"     → 0.99679 vs 0.35520  (2.8×) must grade HIGH
#   "downturn companies"     → 0.99706 vs 0.47396  (2.1×) fairly AMBIGUOUS
#     (the csv and the deck are both genuinely about it — worth the question)
_BM25_DOMINANT_RATIO = 2.5
# All-words-matched at negligible density (huge diffuse docs — feed dumps score
# 0.000x): a lead, not a hit.
_BM25_NOISE_RANK = 0.02


def _search_confidence(results: list[dict]) -> str:
    """Derive an honest confidence label from results (pure; no inference).

    Returns a value from the honest-state vocabulary (see above):
      'high'      — a single hit, or a dominant top score.
      'ambiguous' — multiple candidates, close top scores, no dominant one.
      'weak'      — the best score is below the dominant bar (loose matches only).
      'none'      — no results at all (a true miss). The field is ALWAYS present.
    """
    if not results:
        return CONFIDENCE_NONE
    sims = sorted((c["similarity"] for c in results if "similarity" in c), reverse=True)
    if not sims:
        # BM25 path: grade on the ts_rank margin the RPC already computed.
        ranks = sorted((c["rank"] for c in results if "rank" in c), reverse=True)
        if not ranks:
            # scoreless rows (the no-query list path) — count is all we have.
            return CONFIDENCE_HIGH if len(results) == 1 else CONFIDENCE_AMBIGUOUS
        top = ranks[0]
        if top < _BM25_NOISE_RANK:
            return CONFIDENCE_WEAK
        second = ranks[1] if len(ranks) > 1 else 0.0
        if second <= 0.0 or (top / second) >= _BM25_DOMINANT_RATIO:
            return CONFIDENCE_HIGH
        return CONFIDENCE_AMBIGUOUS
    top = sims[0]
    second = sims[1] if len(sims) > 1 else 0.0
    if top >= _SEARCH_DOMINANT_MIN and (top - second) >= _SEARCH_AMBIGUOUS_GAP:
        return CONFIDENCE_HIGH
    if len(sims) > 1 and (top - second) < _SEARCH_AMBIGUOUS_GAP:
        return CONFIDENCE_AMBIGUOUS
    if top < _SEARCH_DOMINANT_MIN:
        return CONFIDENCE_WEAK
    return CONFIDENCE_HIGH


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


def _naturalize_query(query: str) -> str:
    """Turn a slug-shaped query into natural words for full-text search.

    A host often passes a hyphenated or slug-shaped subject (e.g.
    "yarnnn-mcp-connector"). `search_workspace` builds a plainto_tsquery, which
    AND-matches every lexeme: the literal slug becomes `yarnnn & mcp &
    connector` and matches ZERO prose files even when a file is named exactly
    that and clearly relevant (live test 2026-06-26). Replacing separators with
    spaces lets the tokenizer rank on the individual words instead of requiring
    the joined slug, which content rarely contains verbatim.
    """
    return re.sub(r"[-_/]+", " ", query or "").strip()


# =============================================================================
# compose_search / compose_history — server-side read compositions (ADR-543)
# =============================================================================
# The read verbs are not a second vocabulary — they compose the existing kernel
# primitives (QueryKnowledge / ListRevisions / DiffRevisions) inside the MCP
# server, returning a reason-ready result in ONE round from the host's
# perspective. The chaining lives here (an agentic context, no round limit),
# not in a round-limited consumer chat host.


async def compose_search(
    auth: Any,
    query: str,
    limit: int = 10,
) -> dict:
    """Drive `search` — find files by meaning (ADR-543 D2, binds kernel search).

    Composes `QueryKnowledge` into a ranked, reason-ready result: paths +
    excerpts + an honest `confidence` signal. YARNNN RETURNS the material; it
    does NOT synthesize an answer — the host LLM holding the conversation
    explains it (retrieval, not delegation — ADR-368 D1's bright line, kept).
    Every result carries the path/reference to `open` for the exact content.
    """
    from services.primitives.registry import execute_primitive

    limit = max(1, min(int(limit or 10), 30))
    result = await execute_primitive(auth, "QueryKnowledge", {
        "query": _naturalize_query(query),
        "limit": limit,
    })
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "query_failed"),
                "message": result.get("message", "search failed"), "query": query}

    results = [
        {
            "path": r.get("path", ""),
            "reference": format_file_reference(r.get("path", "")),
            "excerpt": _short_excerpt(r.get("content_preview") or r.get("summary") or ""),
            "last_updated": r.get("updated_at"),
            # Carry the per-row score QueryKnowledge already computed —
            # similarity (semantic) or ts_rank (BM25). The host uses it to
            # decide answer-vs-clarify (see confidence below).
            **({"similarity": r["similarity"]} if "similarity" in r else {}),
            **({"rank": r["rank"]} if "rank" in r else {}),
        }
        for r in (result.get("results") or [])
    ]

    # Raw arrivals are not authored understanding (intake-pipeline canon: a
    # feed dump or transcript lands as an OBSERVATION; meaning lives at the
    # consumer layer). Long diffuse dumps match a little of everything, so
    # left in the candidate set they manufacture false ambiguity around an
    # authored bullseye — the operator receipt behind this partition
    # (2026-08-23: rank-1 exact file + four RSS dumps graded "ambiguous").
    # When ANY authored file matches, the inbound/ rows step aside into
    # `raw_arrivals` — still returned, labelled, never candidates and never
    # confidence inputs. When ONLY inbound matches, it IS the result set
    # (an arrival can be the only place an answer exists).
    raw_arrivals = [r for r in results if r["path"].startswith("/workspace/inbound/")]
    authored = [r for r in results if not r["path"].startswith("/workspace/inbound/")]
    if authored:
        results = authored
    else:
        raw_arrivals = []

    if not results:
        return {
            "success": True, "query": query, "results": [], "total_matches": 0,
            "returned": 0,
            # ALWAYS emit `confidence` — even on a true miss. The earlier
            # miss-path dropped the field, so a host's switch(confidence) hit
            # `undefined` on a clean miss (the honest-state hole the live test
            # surfaced). "none" is the strongest "nothing here" signal.
            "confidence": CONFIDENCE_NONE,
            "citations": [],
            "explanation": (
                f"No file in the workspace matches '{query}'. Nothing has been "
                "authored on this yet — answer from your own knowledge if you "
                "can, or `list` a folder to see what exists."
            ),
        }

    # Honest-state signal (zero inference): let the HOST decide answer-vs-clarify.
    confidence = _search_confidence(results)
    # Migration 246 degrade pass: every row matched SOME query words, none
    # matched ALL of them. That is a lead, not a hit — cap the grade at WEAK.
    # (The pre-246 shape reported this exact state as "none", and the calling
    # model believed nothing existed — 2026-08-22, operator receipt.)
    if result.get("search_method") == "bm25_loose":
        confidence = CONFIDENCE_WEAK
    explanation = None
    if confidence == "ambiguous":
        explanation = (
            f"Multiple files could match '{query}' and none clearly dominates. "
            f"Rather than assume the first, consider asking the user which they "
            f"mean — the candidates are in `results` (with `similarity`)."
        )
    elif confidence == "weak":
        explanation = (
            f"Nothing closely matches '{query}' — only loose matches below the "
            f"confidence bar. Treat these as weak leads; you may need to answer "
            f"from your own knowledge or ask the user to be more specific."
        )
    out = {
        "success": True, "query": query, "results": results,
        "total_matches": max(result.get("count", 0), len(results)),
        "returned": len(results),
        "confidence": confidence,
        "citations": [r["path"] for r in results],
    }
    if raw_arrivals:
        out["raw_arrivals"] = raw_arrivals
        note = (
            f"{len(raw_arrivals)} raw arrival(s) under Downloads also matched "
            "(unprocessed feed/transcript captures — see `raw_arrivals`); they "
            "are set aside from the candidates and the confidence grade."
        )
        explanation = f"{explanation} {note}" if explanation else note
    if explanation:
        out["explanation"] = explanation
    return out


async def compose_history(
    auth: Any,
    reference: str,
    limit: int = 10,
) -> dict:
    """Drive `history` — the attributed revision chain of one EXACT file
    (ADR-543 D2, binds the kernel revisions verbs — ADR-209's chain).

    Same reference grammar as `open` (ADR-512 D5), same exactness contract:
    `history` never resolves a topic to a file — that is `search`'s job. The
    pre-ADR-543 subject-resolution machinery (the fuzzy trace-side resolver and
    the raw-lane forward-walk) is deleted with the phantom object it served.

    Composes `ListRevisions` + per-revision `DiffRevisions` + the `derived_from`
    provenance walk (ADR-448 — cited sources' chains ride along) in one round:
    who authored each version, when, what changed, and what it was made from.
    This is the revision-archaeology differentiator (ADR-311 §3) — "when did I
    decide that / how has this evolved / who added this".
    """
    from services.primitives.registry import execute_primitive

    rel = parse_file_reference(reference)
    if rel is None:
        return {
            "success": False, "error": "invalid_reference",
            "message": (
                "Not a yarnnn file reference. Pass a workspace-relative path "
                "(e.g. Documents/reports/q3.md) or a yarnnn://workspace/… handle."
            ),
            "reference": reference,
        }

    # ListRevisions queries `workspace_file_versions` by the CANONICAL stored
    # path, which carries the `/workspace/` prefix (the authored-substrate
    # revision rows are absolute). Do NOT strip it — a bare path matches zero
    # rows and the chain comes back empty on every call (live test 2026-06-25).
    abs_path = "/workspace/" + rel
    lr = await execute_primitive(auth, "ListRevisions", {"path": abs_path, "limit": max(1, min(int(limit or 10), 30))})
    if not lr.get("success"):
        return {"success": False, "error": lr.get("error", "history_failed"),
                "message": lr.get("message", "history failed"),
                "reference": reference, "path": abs_path}

    revisions = lr.get("revisions") or []
    if not revisions:
        return {
            "success": True, "found": False,
            "reference": format_file_reference(rel), "path": abs_path,
            "history": [], "returned": 0,
            "explanation": (
                f"No file exists at `{rel}` in this workspace (or it has no "
                "revisions yet). `history` is exact — if you're not sure of the "
                "path, use `search` to find it or `list` to enumerate a folder."
            ),
        }

    # Principal display (2026-08-10 identity pass): the stored `authored_by`
    # taxonomy + `author_identity_uuid` stay on the LEDGER; what crosses the
    # boundary is the resolved display ("Kevin", "Kevin via Claude Sonnet",
    # "Claude (via MCP)", "system:radar") + the machine-legible species — never
    # a raw member UUID or a legacy email. ADR-460's hands-vs-principal
    # distinction survives in both channels.
    from services.principal_display import classify_author
    author_display = _display_authors(auth, revisions)
    history = [
        {
            "authored_by": author_display[i],
            "author_class": classify_author(rev.get("authored_by")),
            "when": rev.get("created_at"),
            "change": rev.get("message"),
            "revision_id": rev.get("id"),
            # ADR-423: the provenance-kind rides the ledger column (observation
            # | derivation | authored). ListRevisions surfaces it; history
            # carries it so a consumer can mark an outside arrival without a
            # path/content proxy. Legacy rows read 'authored'.
            "revision_kind": rev.get("revision_kind") or "authored",
        }
        for i, rev in enumerate(revisions)
    ]

    # ADR-372: embed each revision's diff-against-its-PREDECESSOR inline, so the
    # rich-render timeline widget can show click-to-expand diffs with ZERO
    # callback. Composed server-side via the existing DiffRevisions primitive.
    # `revisions` is newest-first, so a revision's predecessor is the NEXT item;
    # the oldest revision has no predecessor and carries `diff: None`.
    # Best-effort: a diff failure leaves that entry's `diff: None` and never
    # breaks history. Bounded by `limit`.
    await _embed_revision_diffs(auth, abs_path, revisions, history)

    # ADR-448: if this file CITES sources (`derived_from`), walk the citations
    # and APPEND each cited file's chain — so history shows the full provenance:
    # this file's revisions AND the sources it was made from (the structurally
    # legible "made from X" edge, not approximate in-place edit history).
    # Best-effort; column-first (the newest revision carries the edge on the
    # ledger), with the content-convention fallback for legacy revisions
    # (read-both IS the migration; no backfill).
    first_cited = None
    citations = [abs_path]
    try:
        derived_froms = list((revisions[0].get("derived_from") or [])) if revisions else []
        if not derived_froms:
            head = (
                auth.client.table("workspace_files")
                .select("content")
                .eq(*_substrate_scope(auth))
                .eq("path", abs_path)
                .limit(1)
                .execute()
            )
            # derived_from is a LIST (ADR-376 §9) — one file may cite N sources.
            # Walk ALL cited files and append each chain: the complete fan-in.
            derived_froms = _extract_derived_from_list((head.data or [{}])[0].get("content")) if head.data else []
        for cited in derived_froms:
            if not cited or cited == abs_path:
                continue
            cited_lr = await execute_primitive(
                auth, "ListRevisions", {"path": cited, "limit": max(1, min(int(limit or 10), 30))}
            )
            cited_revs = cited_lr.get("revisions") or []
            cited_display = _display_authors(auth, cited_revs)
            for j, rev in enumerate(cited_revs):
                history.append({
                    "authored_by": cited_display[j],
                    "author_class": classify_author(rev.get("authored_by")),
                    "when": rev.get("created_at"),
                    "change": rev.get("message"),
                    "revision_id": rev.get("id"),
                    "cited_source": True,       # marks this as a cited source's revision
                    "source_path": cited,
                })
            if cited_revs:
                if first_cited is None:
                    first_cited = cited
                citations.append(cited)
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] derived_from walk failed (non-fatal): %s", exc)

    n_cited = len(citations) - 1
    chain_note = (
        (f" — including the cited source at `{first_cited}`"
         if n_cited == 1 else
         f" — including {n_cited} cited sources (e.g. `{first_cited}`)")
        + " (what this file was made from, per its derived_from edge)"
        if first_cited else ""
    )
    return {
        "success": True, "found": True,
        "reference": format_file_reference(rel),
        "path": abs_path,
        "derived_from": first_cited,   # the first cited source, if any (ADR-448)
        "history": history,            # newest first; this file's chain then cited sources'
        "returned": len(history),
        "citations": citations,
        "explanation": (
            f"The authored history of `{rel}` — {len(history)} revision(s), "
            f"each attributed to who changed it and when{chain_note}. This is "
            "the cross-LLM provenance no plain storage connector can show."
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
    the whole chain.
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
        except Exception as exc:  # noqa: BLE001 — a diff must never break the chain
            logger.debug("[MCP] history diff embed failed for %s: %s", to_id, exc)


# =============================================================================
# ADR-512 — `open`: the deterministic file read, and the D5 handle grammar
# =============================================================================
# The record's unit is the attributed file (ADR-512 D1); `open` is the verb that
# names one. Where `search` is fuzzy (rank-and-hope), `open` is the
# exact-version read: a caller holding a reference gets THIS file — content +
# attribution + the recent revision summary — composed server-side in one round
# (the ADR-368 Correction-1 constraint holds; the host chains nothing).

#: ADR-512 D5 — the canonical cross-boundary file reference. Transport-neutral
#: text; Studio's "Copy AI reference" emits it, `open` accepts it, and future
#: bindings (A2A / direct-API) resolve the same form. Names a FILE, never a
#: revision; carries no authorization (reach is always the caller's grant).
YARNNN_REF_SCHEME = "yarnnn://workspace/"

#: `open` returns at most this much content PER CALL; a larger file is paged
#: with an honest flag and a `next_offset` to continue from (a consumer host's
#: context is finite — but finite per call, not per file).
#:
#: ⚠️ The cap used to say "history/search stay available for the rest". They
#: are NOT: `search` returns a short excerpt and tells the caller to `open` for
#: the content, and `history` carries revision messages, not body text. The
#: promised escape hatch pointed back at the verb that could not reach the
#: content, so a file past the cap had NO path to its own tail. `offset` is
#: that path, and it is the same continuation `list` has carried since ADR-545
#: D3 — `open` was simply the verb that never got it.
OPEN_CONTENT_CAP = 24_000

#: What an EXTERNAL client reads when something inside yarnnn broke.
#:
#: ⚠️ NEVER `str(exc)` on this surface. These composers sit behind PostgREST and
#: httpx, whose exceptions stringify to their own internals — a failed read
#: rendered `{'message': 'relation "workspace_files" does not exist', 'code':
#: '42P01', …}` and handed an external client (Claude Desktop, ChatGPT) our
#: table names and Postgres error codes. That is disclosure, not diction: the
#: caller is outside the trust boundary, and no phrasing of an internal fault is
#: actionable to them.
#:
#: The real detail is LOGGED at each site — operators keep everything, clients
#: get a stable sentence and a retry that is honest about what they can do.
INTERNAL_FAILURE_MESSAGE = (
    "Something went wrong inside yarnnn while reading the workspace — this is "
    "not a problem with your request. Try again; if it persists, tell the user "
    "so they can check the workspace."
)


def parse_file_reference(reference: Optional[str]) -> Optional[str]:
    """Normalize a cross-boundary file reference to a workspace-relative path.

    Accepts the three honest spellings of the same name (ADR-512 D5):
      · `yarnnn://workspace/operation/x.md`  (the canonical handle)
      · `/workspace/operation/x.md`          (the ledger's absolute form)
      · `operation/x.md`                     (bare workspace-relative)

    Returns the workspace-relative path (no leading slash), or None when the
    reference is empty, another scheme, or escapes the workspace (`..`).

    ADR-588 D2 — THE TOLD-NAME IS AN ACCEPTED ADDRESS. This is the one
    chokepoint every interop verb resolves a path through (read and write
    alike), so the home-alias resolution belongs HERE and nowhere else — the
    same guard-at-the-chokepoint discipline as ADR-563's `resolve_request_client`.
    `PARTICIPANT_FILESYSTEM_MODEL` tells the participant its homes are called
    "Documents" and "Downloads"; those names now land in `operation/` and
    `inbound/` instead of minting a top-level twin of the real home. Applying it
    here (rather than at the save door only) is what makes the round-trip hold:
    a participant that wrote `Documents/x.md` can `open`, `edit`, `move` and
    `history` it back by the same name it used.
    """
    ref = (reference or "").strip().strip("\"'")
    if not ref:
        return None
    lowered = ref.lower()
    if lowered.startswith(YARNNN_REF_SCHEME):
        ref = ref[len(YARNNN_REF_SCHEME):]
    elif "://" in ref:
        return None  # some other scheme — not a yarnnn reference
    elif ref.startswith("/workspace/"):
        ref = ref[len("/workspace/"):]
    ref = ref.lstrip("/").strip()
    if not ref or ".." in ref.split("/"):
        return None
    # ADR-588 D2: resolve the told-name home to the real kernel home. Applied
    # last, after normalization, so every accepted spelling of the reference
    # (bare / absolute / yarnnn:// handle) resolves identically.
    from services.workspace_paths import resolve_home_alias
    return resolve_home_alias(ref)


def format_file_reference(path: str) -> str:
    """The canonical handle for a workspace path (ADR-512 D5) — the emit half."""
    rel = parse_file_reference(path) or (path or "").lstrip("/")
    return f"{YARNNN_REF_SCHEME}{rel}"


async def _refuse_citation_loss_on_save(
    auth: Any, abs_path: str, rel: str, incoming: str
) -> Optional[dict]:
    """Refuse a whole-file save that drops or fills a citation (ADR-617 D4).

    Two failures, both invisible to the caller and both permanent in the ledger:
      · a citation the head carried is GONE from the new content — the document
        loses a live projection and keeps rendering as if nothing happened;
      · a citation is kept but its body has been FILLED IN — the classic
        helpful-paste. Those bytes are dead on arrival: the renderer overwrites
        the island from its source on the next read, so the file and every
        screen disagree, silently and forever.

    Only for `.html` (the artifact form). Degrades OPEN on any read failure —
    a guard that cannot read must not block a legitimate save.
    """
    from services.authored_substrate import citation_islands

    try:
        row = (
            live_files_filter(auth.client.table("workspace_files").select("content"))
            .eq(*_substrate_scope(auth)).eq("path", abs_path).limit(1).execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] citation guard read failed (non-fatal): %s", exc)
        return None
    if not row:
        return None
    head_islands = [i for i in citation_islands(row[0].get("content") or "")
                    if i["tag"] != "style"]
    if not head_islands:
        return None

    new_islands = {i["ref"]: i for i in citation_islands(incoming or "")
                   if i["tag"] != "style"}
    dropped = [i["ref"] for i in head_islands if i["ref"] not in new_islands]
    # "Was empty in the head, has a body now" — the paste. A citation the head
    # already carried content for is left alone: this door refuses NEW damage,
    # it does not demand the caller repair pre-existing state.
    filled = [
        i["ref"] for i in head_islands
        if not i["inner"].strip()
        and i["ref"] in new_islands
        and new_islands[i["ref"]]["inner"].strip()
    ]
    if not dropped and not filled:
        return None

    parts = []
    if dropped:
        parts.append(
            "removes " + ", ".join(f"`{p}`" for p in dropped[:5])
        )
    if filled:
        parts.append(
            "writes content inside " + ", ".join(f"`{p}`" for p in filled[:5])
        )
    return {
        "success": False, "error": "citation_damage",
        "message": (
            f"This save {' and '.join(parts)} in `{rel}`. A cited file's content "
            "is projected from its source when the document renders — writing it "
            "into the document produces bytes that are overwritten on the next "
            "render, and dropping the citation silently ends a live projection. "
            "Keep each citation element as it stands (its data-ref, data-ref-kind "
            "and data-ref-rev, with an empty body); to change what one SHOWS, "
            "save the cited file instead."
        ),
        "reference": format_file_reference(rel),
        "citations": sorted(set(dropped + filled)),
    }


def _refuse_citation_damage(old: str, new: str, rel: str) -> Optional[dict]:
    """Refuse an edit that would damage a citation (ADR-617 D4). None = allow.

    The rule ported: *a cited object's content is projected from its source; it
    is never authored inside the artifact* (ADR-440 D5). Two shapes are caught
    without reading the file, so this stays free and honest on a verb whose
    whole contract is that it never carries content the caller did not read:

      · a citation present in `old` and absent from `new` — the edit deletes or
        un-cites it (the "a data-ref can't be halved" refusal the canvas makes);
      · an OPENING citation tag in `old` whose element is not whole — the
        anchor starts or ends inside an island's body.

    What it deliberately cannot catch: an `old` that lies entirely INSIDE an
    island's inner content and mentions no `data-ref` at all. That needs the
    file, which this verb never fetches — and it is the case `compose_save`
    covers span-aware. Stated so the gap is known rather than assumed absent.
    """
    if "data-ref" not in (old or ""):
        return None
    from services.authored_substrate import citation_islands

    before = {i["ref"] for i in citation_islands(old) if i["tag"] != "style"}
    after = {i["ref"] for i in citation_islands(new or "") if i["tag"] != "style"}
    lost = sorted(before - after)
    if not lost:
        return None
    return {
        "success": False, "error": "citation_damage",
        "message": (
            f"This edit would remove or alter a citation in `{rel}`: "
            + ", ".join(f"`{p}`" for p in lost[:5])
            + ". A cited file's content is projected from its source when the "
            "document renders — it is not authored inside the document, and "
            "anything written in its place is overwritten on the next render. "
            "To change what a citation SHOWS, edit the cited file itself. To "
            "keep the citation and edit around it, include the whole citation "
            "element unchanged in both `old` and `new`."
        ),
        "reference": format_file_reference(rel),
        "citations": lost,
    }


def _describe_citations(citations: list[dict]) -> str:
    """The citation rider, as a sentence (ADR-617 D3).

    Named separately from the field because a host that renders only
    `explanation` would otherwise show a document with holes in it and no
    account of them — the incorrect-success shape this ADR exists to close.
    """
    n = len(citations)
    projected = [c for c in citations if c["projected"]]
    unpinned = [c for c in citations if not c["pinned"]]
    out = (
        f" This document CITES {n} workspace file(s) — their content is "
        "projected from the source when it renders, so it is not in the markup "
        "above: " + ", ".join(f"`{c['path']}`" for c in citations[:8])
        + ("…" if n > 8 else "") + "."
    )
    if projected:
        out += (
            f" {len(projected)} of them render as EMPTY elements here; open the "
            "cited file(s) to read what they show."
        )
    if unpinned:
        out += f" {len(unpinned)} carry no revision pin."
    return out


async def compose_open(
    auth: Any,
    reference: str,
    revisions: int = 5,
    offset: int = 0,
) -> dict:
    """Drive `open` — the deterministic path/handle read (ADR-512 D4).

    Resolves the reference (D5 grammar) to the exact stored file and returns
    content + head attribution + the recent revision summary in one round. A
    miss is a miss: `open` never falls back to search (that is `search`'s
    contract — keeping the two verbs' guarantees distinct is the point).

    Content is paged: `offset` continues a read past `OPEN_CONTENT_CAP`, and a
    truncated result carries `next_offset` — the ADR-545 D3 continuation `list`
    already had. Offsets index the content AS RETURNED (after the ADR-574 §4
    elision below), so `next_offset` is always a valid cursor for the next call.
    """
    from services.primitives.registry import execute_primitive

    rel = parse_file_reference(reference)
    if rel is None:
        return {
            "success": False, "error": "invalid_reference",
            "message": (
                "Not a yarnnn file reference. Pass a workspace-relative path "
                "(e.g. Documents/reports/q3.md) or a yarnnn://workspace/… handle."
            ),
            "reference": reference,
        }

    # The ledger stores canonical absolute paths (`/workspace/…`) — same key
    # compose_history reads with (the 2026-06-25 bare-path zero-rows lesson).
    abs_path = "/workspace/" + rel
    try:
        rows = (
            live_files_filter(
                auth.client.table("workspace_files")
                .select("path, content, updated_at, content_type")
            )
            .eq(*_substrate_scope(auth))
            .eq("path", abs_path)
            .limit(1)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MCP] open read failed for %s: %s", abs_path, exc)
        return {"success": False, "error": "read_failed", "reference": reference,
                # NEVER str(exc) — see INTERNAL_FAILURE_MESSAGE.
                "message": INTERNAL_FAILURE_MESSAGE}

    if not rows:
        # TRASHED is not ABSENT (2026-08-21). The filter above stops a deleted
        # file leaking its content to a foreign caller; without this branch it
        # would also make the caller tell the operator the file never existed,
        # while it sits in Trash intact and restorable. Name the state — the
        # ADR-588 D1 shape used for folders, one row down.
        trashed = describe_if_trashed(
            auth.client,
            user_id=auth.user_id,
            workspace_id=getattr(auth, "workspace_id", None),
            abs_path=abs_path,
            # The MCP roster has `history`, not the kernel revision primitives.
            interop=True,
        )
        if trashed:
            return {
                "success": True, "found": False, "trashed": True,
                "reference": format_file_reference(rel), "path": abs_path,
                "trashed_at": trashed["trashed_at"],
                "trashed_with": trashed["trashed_with"],
                "explanation": trashed["message"],
            }
        return {
            "success": True, "found": False,
            "reference": format_file_reference(rel), "path": abs_path,
            "explanation": (
                f"No file exists at `{rel}` in this workspace. `open` is exact — "
                "if you're not sure of the path, use `search` to find it by "
                "meaning or `list` to enumerate a folder."
            ),
        }

    # ADR-588 D1: `open` reads a FILE. A folder marker has no body, so returning
    # `found: true` with empty content would be an incorrect success — the
    # ADR-373 D6 class. Name what it is and route to the verb that answers it.
    from services.workspace_paths import is_folder_marker
    if is_folder_marker(rows[0].get("path") or abs_path, rows[0].get("content_type")):
        return {
            "success": True, "found": False,
            "reference": format_file_reference(rel), "path": abs_path,
            "explanation": (
                f"`{rel.rstrip('/')}` is a folder, not a file — it has no content to "
                "open. Use `list` to enumerate what's inside it."
            ),
        }

    content = rows[0].get("content") or ""

    # ADR-574 §4 — THE CHEAPEST REPAIR, TAKEN. A Studio artifact inlines its
    # kernel stylesheet (~20-31KB) and its skin ahead of <body>, so the cap
    # landed mid-CSS and an external caller received a presentation layer and
    # ZERO authored content, under `success: true, found: true` — the ADR-373
    # D6 incorrect-success class the ADR recorded as a standing defect. Both
    # elided sheets are machine-composed and re-stamped on every write, so no
    # authored byte is lost. Read path only — never a write door (ADR-453 D2).
    from services.machine_projection import elide_presentation_css
    stored_chars = len(content)
    content, elided = elide_presentation_css(content)

    # ADR-617 D3 — THE CITATIONS ARE NAMED. An artifact's cited blocks are
    # usually EMPTY in storage (their content is projected from the source at
    # render), so a reader that sees only the markup reads a working citation
    # as an empty block — and cannot tell that from a genuinely empty one. The
    # rider says what this document cites and whether each is pinned, so the
    # caller knows what it has NOT seen. Paths only: resolving them here would
    # re-copy the bytes the citation form exists to avoid.
    citations: list[dict] = []
    if "data-ref" in content:
        from services.authored_substrate import citation_islands
        seen_refs: set[str] = set()
        for isl in citation_islands(content):
            # A marked <style> wears data-ref as an EDGE (trace/dependents), not
            # a projection — its CSS is already composed in place, and the
            # renderer refuses to resolve "into" one (projection.ts, ADR-456 W3).
            # Listing it as a citation would tell the caller to go read a
            # stylesheet manifest to understand the document.
            if isl["tag"] == "style" or isl["ref"] in seen_refs:
                continue
            seen_refs.add(isl["ref"])
            citations.append({
                "path": isl["ref"],
                "kind": isl["kind"] or None,
                "pinned": bool(isl["rev"]),
                "projected": not isl["inner"].strip(),
            })

    total = len(content)
    start = max(0, int(offset or 0))
    window = content[start:start + OPEN_CONTENT_CAP]
    truncated = (start + len(window)) < total
    next_offset = start + len(window) if truncated else None
    content = window

    # The recent revision summary — attribution riding the read (ADR-311 D3:
    # riders are the fields the substrate already carries). Best-effort: a
    # history failure never breaks the read.
    history: list[dict] = []
    try:
        lr = await execute_primitive(
            auth, "ListRevisions",
            {"path": abs_path, "limit": max(1, min(int(revisions or 5), 10))},
        )
        revs = lr.get("revisions") or []
        # Principal display (2026-08-10): resolved names cross the boundary,
        # never raw member UUIDs — see services/principal_display.py.
        from services.principal_display import classify_author
        author_display = _display_authors(auth, revs)
        history = [
            {
                "authored_by": author_display[i],
                "author_class": classify_author(rev.get("authored_by")),
                "when": rev.get("created_at"),
                "change": rev.get("message"),
                "revision_id": rev.get("id"),
            }
            for i, rev in enumerate(revs)
        ]
    except Exception as exc:  # noqa: BLE001
        logger.debug("[MCP] open revision summary failed (non-fatal): %s", exc)

    head_author = history[0].get("authored_by") if history else None

    # Name the window, not just the fact of a cut. "truncated: true" alone told
    # a caller that SOMETHING was missing but never how much or how to reach it
    # — which is how a read returning zero authored content still read as a
    # success. The sentence states the span, the total, and the next call.
    past_end = bool(total) and start >= total
    if past_end:
        span = (
            f"`{rel}` has {total:,} characters — offset {start:,} is past its end, "
            "so no content is returned."
        )
    else:
        span = (
            f"Characters {start:,}–{start + len(content):,} of {total:,} from `{rel}`"
            + (f", last revised by {head_author}" if head_author else "")
            + "."
        )
    out = {
        "success": True, "found": True,
        "reference": format_file_reference(rel),
        "path": abs_path,
        "content": content,
        "truncated": truncated,
        "offset": start,
        # ⭐⭐⭐ THE VIEW IS NOT THE FILE, AND THE PAYLOAD MUST SAY WHICH IS WHICH.
        # `content_chars` paginates the VIEW (it is the bound `truncated` and
        # `next_offset` are computed against), so it must keep meaning that or
        # paging breaks. `stored_chars` is the FILE. When they differ, this
        # read is not a whole-file read no matter how many pages the caller
        # takes — which is exactly what `complete_for_write` says.
        #
        # Why this is not a cosmetic rename: `truncated: false` +
        # `content_chars == len(content)` is the signature every caller uses
        # for "I now hold the whole file", and after elision that signature
        # was TRUE while 33,855 characters were missing. The honest description
        # lived in `explanation` — prose, for a human — while every
        # machine-readable field said the content was whole. A save built on
        # that read deletes the kernel sheet and the skin, no error, and the
        # revision log records the edit the caller meant to make.
        "content_chars": total,
        "stored_chars": stored_chars,
        "complete_for_write": (not truncated) and elided == 0,
        "citations": citations,
        "authored_by": head_author,
        "last_updated": rows[0].get("updated_at"),
        "history": history,
        "returned": len(history),
        "explanation": (
            span
            + (f" Continue with offset={next_offset} to read on."
               if truncated else
               " This is the end of the file."
               if not past_end and (start or total > OPEN_CONTENT_CAP) else "")
            # Only on the first page — repeating it every page would read as a
            # fresh elision each time.
            + (f" ({elided:,} characters of machine-composed stylesheet were "
               "elided — presentation, not authored content.)"
               if elided and not start else "")
            # ADR-617 D3 — an unresolved citation is invisible in the markup.
            # Say so in the sentence, not only in a field a host may not render.
            + (_describe_citations(citations) if citations and not start else "")
            + f" With its {len(history)} most recent attributed revision(s); "
            "use `history` for the full chain with diffs."
        ),
    }
    if truncated:
        out["next_offset"] = next_offset
    return out


#: `list` returns at most this many entries; larger subtrees are truncated with
#: an honest flag. Mirrors the internal ListFiles ceiling posture (ADR-339 D1).
LIST_ENTRIES_CAP = 500


async def compose_list(
    auth: Any,
    reference: Optional[str] = None,
    since: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> dict:
    """Drive `list` — enumerate the files under a folder (ADR-543 D2, binds the
    kernel `list` verb ADR-512 D3 named but the MCP surface never bound).

    One call returns the subtree under `reference` — every file's path, size,
    last author, and last-updated (the ADR-339 D1 recursive-with-metadata
    shape). No reference (or the workspace root) enumerates the whole
    workspace: the tree's front door. Attribution rides the listing — who last
    touched each file is what a plain storage connector cannot show.

    Reads are workspace-scoped (`_substrate_scope`), the same scope every other
    read composition uses — a member or foreign LLM listing under a grant sees
    the shared commons, not its own row set (the ADR-407/501 read-path lesson).
    """
    ref = (reference or "").strip()
    # The workspace root in any of its honest spellings → list everything.
    if ref in ("", "/", "/workspace", "/workspace/", "workspace", "workspace/",
               "yarnnn://workspace", "yarnnn://workspace/"):
        rel = ""
    else:
        rel = parse_file_reference(ref)
        if rel is None:
            return {
                "success": False, "error": "invalid_reference",
                "message": (
                    "Not a yarnnn folder reference. Pass a workspace-relative "
                    "folder path (e.g. Documents/reports), a yarnnn://workspace/… "
                    "handle, or omit it to list the whole workspace."
                ),
                "reference": reference,
            }
        if rel and not rel.endswith("/"):
            rel += "/"

    # ADR-545 D3: page size + offset (path order), and the change feed —
    # `since` filters to files whose last change landed after the mark
    # (workspace_files.updated_at tracks the head revision).
    page = max(1, min(int(limit or LIST_ENTRIES_CAP), LIST_ENTRIES_CAP))
    offset = max(0, int(offset or 0))

    abs_prefix = f"/workspace/{rel}"
    try:
        q = (
            auth.client.table("workspace_files")
            .select(
                "path, content_bytes, updated_at, content_type, "
                "workspace_file_versions!head_version_id(authored_by, author_identity_uuid, created_at)"
            )
            .eq(*_substrate_scope(auth))
            .like("path", f"{abs_prefix}%")
            .in_("lifecycle", ["active", "delivered"])
        )
        if since and since.strip():
            q = q.gte("updated_at", since.strip())
        rows = (
            q.order("path")
            .range(offset, offset + page)  # inclusive → page+1 rows probes "more"
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MCP] list read failed for %s: %s", abs_prefix, exc)
        return {"success": False, "error": "list_failed", "reference": reference,
                "message": INTERNAL_FAILURE_MESSAGE}

    # ADR-588 D1: folder markers are directories, not documents — `list`
    # enumerates FILES, so a marker never appears here. (An empty folder is
    # simply an empty listing to a participant, which is the honest answer;
    # the operator's tree is where directories are the subject.)
    from services.workspace_paths import is_folder_marker
    rows = [r for r in rows if not is_folder_marker(r.get("path") or "", r.get("content_type"))]

    truncated = len(rows) > page
    kept = rows[:page]
    # Principal display (2026-08-10): the head author crosses the boundary as a
    # resolved name + species, never a raw member UUID or legacy email.
    from services.principal_display import classify_author
    heads = [r.get("workspace_file_versions") or {} for r in kept]
    author_display = _display_authors(auth, heads)
    files = []
    for i, r in enumerate(kept):
        head = heads[i]
        p = r.get("path") or ""
        rel_path = p[len("/workspace/"):] if p.startswith("/workspace/") else p
        files.append({
            "path": rel_path,
            "reference": format_file_reference(rel_path),
            "bytes": r.get("content_bytes"),
            "last_updated": head.get("created_at") or r.get("updated_at"),
            "authored_by": author_display[i] if head else None,
            "author_class": classify_author(head.get("authored_by")) if head else None,
        })

    # ADR-588 D2, display half: the participant was TOLD "Documents"/"Downloads"
    # — answer in the vocabulary we taught, not the kernel root. Prose only; the
    # `path`/`reference` fields above stay canonical addresses.
    where = (
        f"`{display_home_alias(rel.rstrip('/'))}`" if rel else "the workspace"
    )
    if not files:
        explanation = (
            (f"No files under {where} changed since {since}. Quiet is a clean "
             "signal — nothing moved." )
            if since else
            (f"No files under {where}. In a path-addressed store a folder exists "
             "only through its files — check the spelling, `list` a parent, or "
             "`search` by meaning.")
        )
    else:
        explanation = (
            f"{len(files)} file(s) under {where}"
            + (f" changed since {since}" if since else "")
            + ", each with who last changed it and when"
            + (f" (more remain — continue with offset={offset + page})" if truncated else "")
            + ". Use `open` on any path for its exact content."
        )
    out = {
        "success": True,
        "reference": f"{YARNNN_REF_SCHEME}{rel}",
        "path": abs_prefix,
        "files": files,
        "count": len(files),
        "truncated": truncated,
        "explanation": explanation,
    }
    if since:
        out["since"] = since
    if truncated:
        out["next_offset"] = offset + page
    return out


async def compose_edit(
    auth: Any,
    reference: str,
    old: str,
    new: str,
    replace_all: bool = False,
    message: Optional[str] = None,
) -> dict:
    """Drive `edit` — the anchored write (ADR-545 D1, binds ADR-337 EditFile).

    The ANCHOR is the precondition: `old` must match the current content
    exactly (and uniquely, unless replace_all), so the verb carries no
    base_revision — a stale view fails loudly (`old_string_not_found` /
    `old_string_not_unique`), never guesses, and the kernel's internal
    head-read CAS closes the apply-window race (ADR-406 D4). Content the
    client never read is never in the payload — the truncated-read data-loss
    class does not exist on this verb.
    """
    from services.primitives.registry import execute_primitive

    rel = parse_file_reference(reference)
    if rel is None:
        return {
            "success": False, "error": "invalid_reference",
            "message": (
                "Not a yarnnn file reference. Pass a workspace-relative path "
                "or a yarnnn://workspace/… handle."
            ),
        }
    # ADR-617 D4 — THE CITATION RULING REACHES THIS DOOR. The Studio UI
    # enforces it in three client-side layers (islands are contenteditable
    # =false, the caret is fenced out, and the commit serializer restores them
    # from data-src-html); MCP is the door built after that ruling and had
    # none of them. Content-free, matching this verb's contract that content
    # the client never read is never in the payload: a citation appearing in
    # `old` but not `new` is the anchor cutting through an island.
    refused = _refuse_citation_damage(old, new, rel)
    if refused:
        return refused

    result = await execute_primitive(auth, "EditFile", {
        "scope": "workspace",
        "path": rel,
        "old_string": old,
        "new_string": new,
        "replace_all": bool(replace_all),
        "message": message or f"edit via interop: {rel}",
    })
    if not result.get("success"):
        # Reshape the kernel's anchor failures onto host-actionable guidance.
        err = result.get("error")
        if err == "old_string_not_found":
            result["message"] = (
                (result.get("message") or "The anchor text was not found.")
                + " Your view of the file may be stale or truncated — re-open "
                "it and anchor on text you can see verbatim."
            )
        elif err == "old_string_not_unique":
            result["message"] = (
                (result.get("message") or "The anchor text is not unique.")
                + " Include more surrounding context in `old`, or pass "
                "replace_all=true to change every occurrence."
            )
        result.setdefault("reference", format_file_reference(rel))
        return result
    return {
        "success": True,
        "reference": format_file_reference(rel),
        "path": result.get("path") or f"/workspace/{rel}",
        "replacements": result.get("replacements", 1),
        "explanation": (
            f"Applied {result.get('replacements', 1)} replacement(s) to `{rel}` "
            "as one attributed revision. Only the anchored change was sent — "
            "content you did not read was never at risk."
        ),
    }


def _names_a_folder(auth: Any, rel: str) -> bool:
    """Whether this reference addresses a FOLDER rather than a file.

    ADR-588: a folder exists iff a marker row or a prefixed file exists, so the
    check is "is there a marker at this path, or anything beneath it". Used by
    `delete` and `move` to pick the grain — the interop roster keeps ONE delete
    and ONE move (a foreign caller should not have to know our two grains), and
    the verb resolves which fan-out answers.

    ⚠️ THE LIFECYCLE FILTER IS LOAD-BEARING (2026-08-26). This asks about the
    LIVE tree, because that is the only tree the fan-outs act on:
    `folder_organize.enumerate_subtree` excludes archived rows by contract ("a
    subtree walk answers about the LIVE folder"). Without the filter the two
    disagreed, and `delete` on an already-trashed folder resolved as a folder,
    fanned out over nothing, and answered `success: True · "0 moved to Trash"`
    — the ADR-373 D6 incorrect-success class. `DeleteFile` on a dead path
    returns `file_not_found`; declining the folder grain here is what lets the
    trashed case fall through to that honest refusal. The filter set is the
    SAME one `compose_list` reads with — one definition of "what is live".
    """
    from services.workspace_context import substrate_scope_filter
    from services.workspace_paths import folder_marker_path

    abs_folder = ("/" + rel.strip("/")) if not rel.startswith("/") else rel.rstrip("/")
    if abs_folder in ("", "/"):
        return False
    marker = folder_marker_path(abs_folder)
    client = auth.client
    workspace_id = getattr(auth, "workspace_id", None)
    try:
        rows = (
            client.table("workspace_files")
            .select("path")
            .eq(*substrate_scope_filter(auth.user_id, workspace_id))
            .or_(f"path.eq.{marker},path.like.{abs_folder}/%")
            .in_("lifecycle", ["active", "delivered"])
            .limit(1)
            .execute()
        ).data or []
    except Exception:
        return False
    return bool(rows)


async def compose_delete(
    auth: Any,
    reference: str,
    message: Optional[str] = None,
) -> dict:
    """Drive `delete` — remove from the live view (ADR-545 D2, binds DeleteFile).

    A VIEW change, not information loss (ADR-337 D2 / ADR-209 D7): an
    attributed tombstone records who and why; the chain retains the content;
    restore is revert-as-write. Governance locks + the ADR-307 gate apply
    exactly as for save.
    """
    from services.primitives.registry import execute_primitive

    rel = parse_file_reference(reference)
    if rel is None:
        return {
            "success": False, "error": "invalid_reference",
            "message": (
                "Not a yarnnn file reference. Pass a workspace-relative path "
                "or a yarnnn://workspace/… handle."
            ),
        }
    # ADR-337 amended (2026-08-21) — ONE delete verb, two grains. A foreign
    # caller addresses a name; the kernel knows whether that name is a file or
    # a folder, so it picks the fan-out rather than making the caller learn our
    # taxonomy. A folder delete is the same attributed archive-per-file the
    # operator's click performs — restorable as one unit.
    if _names_a_folder(auth, rel):
        folder_result = await execute_primitive(auth, "DeleteFolder", {
            "path": rel,
            "message": message or f"delete via interop: {rel}",
        })
        folder_result.setdefault("reference", format_file_reference(rel))
        return folder_result
    result = await execute_primitive(auth, "DeleteFile", {
        "scope": "workspace",
        "path": rel,
        "message": message or f"delete via interop: {rel}",
    })
    if not result.get("success"):
        result.setdefault("reference", format_file_reference(rel))
        return result
    return {
        "success": True,
        "reference": format_file_reference(rel),
        "path": result.get("path") or f"/workspace/{rel}",
        "tombstone_revision_id": result.get("tombstone_revision_id"),
        "explanation": (
            f"Removed `{rel}` from the live workspace as an attributed "
            "tombstone. Nothing is lost: the revision chain (including the "
            "content at deletion) is retained, and `history` still walks it."
        ),
    }


async def compose_move(
    auth: Any,
    reference: str,
    new_reference: str,
    message: Optional[str] = None,
) -> dict:
    """Drive `move` — move/rename as one attributed operation (ADR-545 D2,
    binds MoveFile). Refuses to overwrite an existing destination — replacing
    a file is `delete` first, by explicit intent."""
    from services.primitives.registry import execute_primitive

    rel = parse_file_reference(reference)
    new_rel = parse_file_reference(new_reference)
    if rel is None or new_rel is None:
        return {
            "success": False, "error": "invalid_reference",
            "message": (
                "Both references must be yarnnn file references — a "
                "workspace-relative path or a yarnnn://workspace/… handle."
            ),
        }
    # ADR-337 amended (2026-08-21) — ONE move verb, two grains (see `delete`).
    # Rename is the same act with a new leaf, at either grain.
    if _names_a_folder(auth, rel):
        folder_result = await execute_primitive(auth, "MoveFolder", {
            "path": rel,
            "new_path": new_rel,
            "message": message or f"move via interop: {rel} → {new_rel}",
        })
        folder_result.setdefault("reference", format_file_reference(new_rel))
        return folder_result
    result = await execute_primitive(auth, "MoveFile", {
        "scope": "workspace",
        "path": rel,
        "new_path": new_rel,
        "message": message or f"move via interop: {rel} → {new_rel}",
    })
    if not result.get("success"):
        result.setdefault("reference", format_file_reference(rel))
        return result
    return {
        "success": True,
        "reference": format_file_reference(new_rel),
        "from_path": f"/workspace/{rel}",
        "path": f"/workspace/{new_rel}",
        "explanation": (
            f"Moved `{rel}` → `{new_rel}` as one attributed operation. The "
            "old path carries a tombstone pointing here; both chains are "
            "retained."
        ),
    }


async def compose_save(
    auth: Any,
    reference: str,
    content: str,
    base_revision: Optional[str] = None,
    message: Optional[str] = None,
    derived_from: Optional[list] = None,
    confirm_full_replace: bool = False,
) -> dict:
    """Drive `save` — the attributed write to a named file (ADR-512 §8a).

    Read-before-write is the contract: an EXISTING file requires
    `base_revision` (the head id `open` returned); the ledger's ADR-406
    linearity guard makes the compare-and-set atomic, and a lost race returns
    the intervening head's attribution. A NEW file is created with no base.
    All consequence stays at the gate — this dispatches WriteFile through
    execute_primitive under the mcp caller identity; the caller's lock-set
    (CALLER_WRITE_POLICY['mcp']) and the empty-content guard apply unchanged.

    ADR-533 D3: `derived_from` (the ADR-448 reference edge) is threaded to the
    primitive, which has always accepted it. Before this, interop could READ the
    edge (history walks it) but never AUTHOR one — leaving the single surface
    where foreign material arrives as the only writing surface unable to record
    where its content came from. References are normalized at the write door;
    an unresolvable path is dropped there, not here.
    """
    from services.primitives.registry import execute_primitive

    rel = parse_file_reference(reference)
    if rel is None:
        return {
            "success": False, "error": "invalid_reference",
            "message": (
                "Not a yarnnn file reference. Pass a workspace-relative path "
                "or a yarnnn://workspace/… handle."
            ),
        }
    abs_path = "/workspace/" + rel

    # Head lookup — the read-before-write enforcement (never trust the host's
    # memory of whether the file exists; the ledger answers).
    try:
        head_rows = (
            auth.client.table("workspace_file_versions")
            .select("id, authored_by, author_identity_uuid, created_at, message")
            .eq(*_substrate_scope(auth))
            .eq("path", abs_path)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("[MCP] save head lookup failed for %s: %s", rel, exc)
        return {"success": False, "error": "head_lookup_failed",
                "message": INTERNAL_FAILURE_MESSAGE}

    head = head_rows[0] if head_rows else None

    # ⭐⭐⭐ A READ VIEW IS NOT A FILE, AND MUST NOT BE SAVED AS ONE.
    #
    # `open` elides the machine-composed stylesheets so an artifact's authored
    # content fits the first page. That made reading correct and writing
    # hazardous: the elided view carries a marker comment where ~31KB of
    # kernel sheet used to be, and a whole-file save of that view DELETES the
    # kernel and the skin — silently, with the revision log recording whatever
    # small change the caller actually intended.
    #
    # This is checked BEFORE the size guard below because it is the stricter
    # fact. The size guard asks "did you read enough?" and can be answered by
    # paging; this one asks "is what you hold even the file?" and paging
    # cannot fix it — every page of an elided read is elided.
    #
    # ⚠️ NOT overridable by `confirm_full_replace`. That flag means "I mean to
    # replace the whole file", which is a statement about INTENT. This is a
    # statement about the CONTENT: it is missing bytes the caller never saw
    # and cannot have meant to delete. Letting intent override it would make
    # the flag a way to confirm a mistake.
    from services.machine_projection import carries_elision_marker
    if head and carries_elision_marker(content):
        return {
            "success": False, "error": "elided_content_save",
            "message": (
                f"This content came from a READ of `{rel}` with its machine-"
                "composed stylesheets elided (the marker comment is still in "
                "it), so saving it would delete the artifact's styling. Use "
                "`edit` to change part of the file — its anchors match the "
                "stored bytes, so it is unaffected by elision. If you must "
                "replace the whole file, author the replacement rather than "
                "editing a read view."
            ),
            "reference": format_file_reference(rel),
        }

    # ADR-545 D4 — the honest save (truncation guard). A whole-file save over a
    # file larger than one `open` page is the read-truncated/save-back data-loss
    # shape. The guard STAYS now that `open` pages: paging makes a full read
    # POSSIBLE, not certain — a caller that read one page and saved would lose
    # the rest exactly as before, and the server cannot tell the two apart.
    # What changed is the remedy the refusal names: the caller can now actually
    # finish the read (offset), rather than only being told to use `edit`.
    if head and not confirm_full_replace:
        try:
            size_row = (
                auth.client.table("workspace_files")
                .select("content_bytes")
                .eq(*_substrate_scope(auth))
                .eq("path", abs_path)
                .limit(1)
                .execute()
            ).data or []
            existing_bytes = (size_row[0].get("content_bytes") or 0) if size_row else 0
        except Exception:  # noqa: BLE001 — the guard degrades open, never breaks save
            existing_bytes = 0
        if existing_bytes > OPEN_CONTENT_CAP:
            return {
                "success": False, "error": "large_file_overwrite",
                "message": (
                    f"`{rel}` is {existing_bytes} bytes — more than one "
                    f"{OPEN_CONTENT_CAP}-character `open` page, so a whole-file "
                    "save risks silently deleting a part you may not have read. "
                    "Either page through it first (`open` with offset=next_offset "
                    "until complete_for_write is true), or use `edit` for "
                    "targeted changes. To replace the whole file deliberately, "
                    "pass confirm_full_replace=true."
                ),
                "reference": format_file_reference(rel),
            }

    # ADR-617 D4 — the same ruling, span-aware, on the whole-file door. `edit`
    # checks its anchors without the file; `save` REPLACES the file, so the
    # honest question is whether the head's citations survive the new content.
    # Reads the head only when the head actually cites something.
    if head and "html" in (rel.rsplit(".", 1)[-1] or "").lower():
        refused = await _refuse_citation_loss_on_save(auth, abs_path, rel, content)
        if refused:
            return refused

    if head and not base_revision:
        return {
            "success": False, "error": "base_required",
            "message": (
                f"`{rel}` already exists — open it first and pass the head "
                "revision id as base_revision. save never overwrites blind "
                "(the exact-version guarantee runs both ways)."
            ),
            "current_head": {
                "revision_id": head.get("id"),
                # Principal display (2026-08-10): the conflict names WHO holds
                # the head as a resolved name, never a raw member UUID.
                "authored_by": _display_authors(auth, [head])[0],
                "when": head.get("created_at"),
            },
        }
    if base_revision and not head:
        return {
            "success": False, "error": "not_found",
            "message": f"No file exists at `{rel}` — omit base_revision to create it.",
        }

    # ADR-533 D3: the host cites sources in the SAME handle grammar it uses for
    # `reference` (yarnnn://workspace/… | /workspace/… | bare relative), so run
    # each citation through the interop parser — `normalize_workspace_ref` at the
    # write door owns the /workspace/ prefixing but does NOT speak the yarnnn://
    # handle. Parse the handle here, let the ledger normalize; two parsers, each
    # owning its own grammar, neither duplicating the other.
    #
    # A citation that doesn't parse is DROPPED, never fatal: a malformed
    # reference must not cost the user their write. The edge is provenance, not
    # a gate.
    write_input = {
        "scope": "workspace",
        "path": rel,
        "content": content,
        "mode": "overwrite",
        "message": message or f"save via interop: {rel}",
        "expected_parent_version_id": base_revision,
    }
    cited: list[str] = []
    if derived_from:
        cited = [p for p in (parse_file_reference(r) for r in derived_from) if p]
        if cited:
            write_input["derived_from"] = cited

    result = await execute_primitive(auth, "WriteFile", write_input)
    if result.get("error") == "stale_write":
        # Re-shape onto the open/save vocabulary; the host re-opens and merges.
        result["message"] = (
            (result.get("message") or "The file moved since you opened it.")
            + " Re-open the file, merge your change over the current version, "
            "and save again with the new base_revision."
        )
        return result
    if not result.get("success"):
        return result

    # Return the new head so a follow-up save can chain without re-opening.
    try:
        new_head = (
            auth.client.table("workspace_file_versions")
            .select("id")
            .eq(*_substrate_scope(auth))
            .eq("path", abs_path)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        ).data or []
        new_rev = new_head[0]["id"] if new_head else None
    except Exception:  # noqa: BLE001
        new_rev = None
    out = {
        "success": True,
        "reference": format_file_reference(rel),
        "path": abs_path,
        "created": head is None,
        "revision_id": new_rev,
        "explanation": (
            f"Saved `{rel}` as an attributed revision"
            + (" (new file)" if head is None else "")
            + ". Your write is signed as you in the workspace ledger; "
            "history shows it beside every other change."
        ),
    }
    # Echo the citations that were ACTUALLY RECORDED — the post-parse set, after
    # malformed references were dropped above. The caller passed intent; this is
    # the edge the ledger holds. Echoing the raw input would report a provenance
    # edge that may not exist (a citation that failed to parse is silently
    # dropped, deliberately, so a bad reference never costs the user their
    # write). Absent when nothing was cited — never an empty key.
    if cited:
        out["derived_from"] = cited
    return out


# =============================================================================
# What deliberately does NOT live here anymore
# =============================================================================
# · The memory verbs' machinery (ADR-543): resolve_remember_path /
#   resolve_memory_path / resolve_trace_path / dispatch_remember_this and the
#   store/fetch-by-key "FLOOR" — deleted with the phantom "memory" object.
#   Observations arrive as ordinary attributed `save` writes now; ADR-376's
#   capture/understanding split survives as convention + grant, not a verb.
# · The eager per-write derive wake (retired 2026-07-09, ADR-423 §7 + the
#   Files-model note §5): no wake fires on a foreign write. When a REAL derive
#   step ships it re-attaches as its own mechanism, writing
#   `revision_kind='derivation'` + `derived_from`; compose_history's
#   derived_from walk already reads that chain the day a producer exists.
