"""Search covers the NAME, and a partial match degrades — never concludes "none".

Run: `python3 test_search_covers_the_name.py` from `api/`.

WHY THIS EXISTS (2026-08-22)

`search("downturn companies deck")` returned confidence "none" — the tool's own
documented "strongest 'nothing here' signal" — over a deck titled "Build in the
Downturn" sitting beside a CSV literally named downturn-companies.csv. The
calling model believed it, told the operator the material didn't exist, and the
operator repeated the claim on the tool's authority. Measured live: every file
matched 'downturn' and 'compani'; NONE matched 'deck', because the tsvector
covered content only (the path never participated, and deck.html's only "deck"
sits inside an HTML tag, which ts_parse drops) — and plainto's AND semantics
turned one absent lexeme into a categorical "nothing exists".

A read that fails loudly gets retried. A search that confidently says nothing
exists gets believed. So the fix is honesty-shaped, three layers:

  - migration 246: path (weight A) + summary (B) join the tsvector; an
    all-words miss re-answers with the any-word pass, rows labelled
    match_mode='loose' — one call, no second round trip;
  - QueryKnowledge carries the label out as search_method='bm25_loose', and
    stops discarding sub-bar semantic rows (a weak lead is not an absence);
  - compose_search grades a loose result WEAK — never "high", never "none".
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

_API = Path(__file__).parent
_ROOT = _API.parent

PASSED = 0
FAILED: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        print(f"  ok   {label}")
        PASSED += 1
    else:
        print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")
        FAILED.append(label)


# =============================================================================
# [1] the migration carries all four load-bearing properties
# =============================================================================

print("\n[1] migration 246 — the RPC recut")

_mig = _ROOT / "supabase" / "migrations" / "246_search_covers_the_name_and_degrades.sql"
_sql = _mig.read_text() if _mig.exists() else ""
check("the migration exists", bool(_sql))
check("the return type changes, so it must DROP first (OR REPLACE would overload)",
      "DROP FUNCTION IF EXISTS public.search_workspace" in _sql)
check("the path joins the tsvector (a file can match its own name)",
      "translate(coalesce(wf.path" in _sql)
check("an all-words miss degrades to the any-word pass, labelled",
      "'loose'::text AS match_mode" in _sql and "NOT EXISTS (SELECT 1 FROM strict)" in _sql)
check("the trash filter survives the recut (218 regression guard)",
      "lifecycle" in _sql)
check("PostgREST is told to reload (PGRST205 guard)",
      "NOTIFY pgrst" in _sql)


# =============================================================================
# [2]+[3] QueryKnowledge EXECUTED — label carried, weak semantic not discarded
# =============================================================================

print("\n[2] QueryKnowledge carries the match label out")

import services.primitives.workspace as _ws_mod  # noqa: E402
import services.embeddings as _emb_mod  # noqa: E402


class _Result(SimpleNamespace):
    pass


class _RpcClient:
    """Records rpc calls; serves canned rows per RPC name."""

    def __init__(self, by_rpc):
        self.by_rpc = by_rpc
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        rows = self.by_rpc.get(name, [])
        return SimpleNamespace(execute=lambda: _Result(data=list(rows)))

    def table(self, name):  # the no-query branch — unused in these probes
        raise AssertionError("query probes must take the RPC path")


def _auth(client):
    return SimpleNamespace(
        user_id="00000000-0000-0000-0000-000000000001",
        workspace_id="00000000-0000-0000-0000-000000000002",
        client=client,
    )


def _row(path, mode=None, sim=None):
    r = {
        "path": path,
        "content": "body " * 60,
        "summary": "a probe file",
        "updated_at": "2026-08-22T00:00:00Z",
    }
    if mode is not None:
        r["match_mode"] = mode
    if sim is not None:
        r["similarity"] = sim
    return r


# The one DB-touching seam outside the client: the powerbox grant lookup.
# None → owner read-all (both helpers pass rows through untouched).
_orig_axes = _ws_mod._lookup_grant_axes
_ws_mod._lookup_grant_axes = lambda auth: None

# get_embedding reaches OpenAI — the semantic probe must never leave process.
_orig_embed = _emb_mod.get_embedding


async def _fake_embed(text):
    return [0.0] * 8

_emb_mod.get_embedding = _fake_embed

try:
    strict_rows = [_row("/workspace/operation/a.md", mode="strict")]
    res = asyncio.run(_ws_mod.handle_query_knowledge(
        _auth(_RpcClient({"search_workspace": strict_rows})), {"query": "alpha"}))
    check("strict rows report search_method='bm25'",
          res.get("success") and res.get("search_method") == "bm25",
          f"got {res.get('search_method')!r}")

    loose_rows = [
        _row("/workspace/operation/a.md", mode="loose"),
        _row("/workspace/operation/b.md", mode="loose"),
    ]
    res = asyncio.run(_ws_mod.handle_query_knowledge(
        _auth(_RpcClient({"search_workspace": loose_rows})), {"query": "alpha beta"}))
    check("loose rows report search_method='bm25_loose' (the honesty carrier)",
          res.get("search_method") == "bm25_loose",
          f"got {res.get('search_method')!r} — without the label the composition "
          "grades an any-word match as if every word had hit")
    check("…and the rows themselves come through",
          res.get("count") == 2)

    print("\n[3] a sub-bar semantic match is a weak lead, not an absence")
    sem_rows = [_row("/workspace/operation/c.md", sim=0.21)]
    res = asyncio.run(_ws_mod.handle_query_knowledge(
        _auth(_RpcClient({"search_workspace": [], "search_workspace_semantic": sem_rows})),
        {"query": "wholly nonlexical intent"}))
    check("similarity 0.21 rows pass through (the old >0.3 floor dropped them)",
          res.get("search_method") == "semantic" and res.get("count") == 1,
          f"got method={res.get('search_method')!r} count={res.get('count')} — "
          "'loose matches only' must never be reported as 'nothing exists'")
    check("…with similarity carried so the composition can grade it weak",
          (res.get("results") or [{}])[0].get("similarity") == 0.21)
finally:
    _ws_mod._lookup_grant_axes = _orig_axes
    _emb_mod.get_embedding = _orig_embed


# =============================================================================
# [4] compose_search grades: loose → weak; strict single → high; empty → none
# =============================================================================

print("\n[4] compose_search grades the label honestly")

import services.primitives.registry as _reg_mod  # noqa: E402
from services.mcp_composition import compose_search  # noqa: E402

_orig_exec = _reg_mod.execute_primitive


def _with_primitive_result(payload):
    async def _fake(auth, name, inp):
        assert name == "QueryKnowledge"
        return payload
    return _fake


def _qk(results, method):
    return {"success": True, "search_method": method,
            "count": len(results), "results": results, "query": "q"}


try:
    _reg_mod.execute_primitive = _with_primitive_result(_qk(
        [{"path": "/workspace/operation/a.md", "content_preview": "x", "updated_at": "t"}],
        "bm25_loose"))
    out = asyncio.run(compose_search(_auth(None), "downturn companies deck"))
    check("a single LOOSE hit grades WEAK, never high",
          out.get("confidence") == "weak",
          f"got {out.get('confidence')!r} — an any-word match presented as a "
          "confident hit is the mirror image of the false 'none'")
    check("…and the weak explanation tells the host it holds leads, not answers",
          "loose" in (out.get("explanation") or "").lower()
          or "weak" in (out.get("explanation") or "").lower())

    _reg_mod.execute_primitive = _with_primitive_result(_qk(
        [{"path": "/workspace/operation/a.md", "content_preview": "x", "updated_at": "t"}],
        "bm25"))
    out = asyncio.run(compose_search(_auth(None), "q"))
    check("control: a single STRICT hit still grades high",
          out.get("confidence") == "high", f"got {out.get('confidence')!r}")

    _reg_mod.execute_primitive = _with_primitive_result(_qk([], "none"))
    out = asyncio.run(compose_search(_auth(None), "q"))
    check("control: an actually-empty result still grades none",
          out.get("confidence") == "none" and out.get("results") == [])

    # =========================================================================
    # [5] confidence is MARGIN, not count (operator receipt 2026-08-23)
    # =========================================================================
    # The three calibration points are LIVE production measurements — a check
    # that grades them wrongly reproduces the exact complaint: a
    # contract-following host asked a clarifying question over a bullseye.

    print("\n[5] BM25 confidence comes from the rank margin, never the count")

    def _r(path, rank):
        return {"path": path, "content_preview": "x", "updated_at": "t", "rank": rank}

    dumps = [_r(f"/workspace/inbound/slack/c1/2026-07-03T0{i}.md", 0.3552) for i in range(4)]
    _reg_mod.execute_primitive = _with_primitive_result(_qk(
        [_r("/workspace/operation/definition-of-done.md", 0.99679)] + dumps, "bm25"))
    out = asyncio.run(compose_search(_auth(None), "definition of done"))
    check("a 2.8x dominant rank-1 grades HIGH despite four trailing rows",
          out.get("confidence") == "high",
          f"got {out.get('confidence')!r} — count-based grading manufactured "
          "'ambiguous' over a bullseye and the host hedged on a nailed answer")

    _reg_mod.execute_primitive = _with_primitive_result(_qk([
        _r("/workspace/operation/yarrnnnn-decl/assets/downturn-companies.csv", 0.99706),
        _r("/workspace/operation/yarrnnnn-decl/deck.html", 0.47396),
        _r("/workspace/operation/yarrnnnn-decl/assets/downturn-outcomes.csv", 0.30156),
    ], "bm25"))
    out = asyncio.run(compose_search(_auth(None), "downturn companies"))
    check("control: a 2.1x margin over close authored candidates stays AMBIGUOUS",
          out.get("confidence") == "ambiguous",
          f"got {out.get('confidence')!r} — margin grading must not crown every "
          "rank-1; two files genuinely about the topic deserve the question")

    # =========================================================================
    # [6] raw arrivals step aside — authored understanding is the candidate set
    # =========================================================================

    print("\n[6] inbound/ rows are set aside when authored files match")

    _reg_mod.execute_primitive = _with_primitive_result(_qk(
        [_r("/workspace/operation/fundraising/market-sizing-reference.md", 0.99972)]
        + [_r(f"/workspace/inbound/web/simonwillison/2026-07-2{i}.xml", 0.0) for i in range(4)],
        "bm25"))
    out = asyncio.run(compose_search(_auth(None), "market sizing figures"))
    check("the authored bullseye is the ONLY candidate, graded high",
          out.get("confidence") == "high"
          and [r["path"] for r in out.get("results", [])]
          == ["/workspace/operation/fundraising/market-sizing-reference.md"],
          f"got {out.get('confidence')!r} over {len(out.get('results', []))} candidates")
    check("…citations carry no inbound path",
          all("/inbound/" not in p for p in out.get("citations", [])))
    # Re-anchored 2026-08-25: this asserted the arrivals are LABELLED AND
    # COUNTED, but pinned the kernel SPELLING `inbound/`. The interop surface
    # now answers in the told-name the participant was taught ("Downloads",
    # ADR-588 D2 display half) — the intent holds, the spelling moved. Assert
    # the intent: a count, and a note that NAMES the home in whatever
    # vocabulary this surface speaks.
    from services.workspace_paths import HOME_ALIASES, INBOUND_ROOT

    _arrivals_home = HOME_ALIASES_INVERSE = {
        v.rstrip("/"): k for k, v in HOME_ALIASES.items()
    }[INBOUND_ROOT.strip("/")]
    check("…and the arrivals are SET ASIDE, not hidden (labelled, counted)",
          len(out.get("raw_arrivals", [])) == 4
          and _arrivals_home in (out.get("explanation") or ""),
          "dropping them silently would be the third honesty defect this file exists to end")

    _reg_mod.execute_primitive = _with_primitive_result(_qk(
        [_r(f"/workspace/inbound/web/simonwillison/2026-07-2{i}.xml", 0.0001) for i in range(3)],
        "bm25"))
    out = asyncio.run(compose_search(_auth(None), "slack conversation about pricing"))
    check("when ONLY arrivals match, they ARE the result set",
          len(out.get("results", [])) == 3 and "raw_arrivals" not in out,
          "an arrival can be the only place an answer exists")
    check("…graded WEAK (all-words at negligible density is a lead, not a hit)",
          out.get("confidence") == "weak", f"got {out.get('confidence')!r}")
finally:
    _reg_mod.execute_primitive = _orig_exec


print(f"\n{'=' * 60}")
if FAILED:
    print(f"FAILED {len(FAILED)}/{PASSED + len(FAILED)}: {FAILED}")
    sys.exit(1)
print(f"ALL PASS — {PASSED}/{PASSED}")
