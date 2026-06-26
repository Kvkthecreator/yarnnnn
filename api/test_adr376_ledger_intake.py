"""ADR-376 / FOUNDATIONS DP32 regression gate — the ledger-intake axiom (MCP slice).

Structural invariants for the raw-observation-vs-derived-substrate split on the
MCP intake path. Pure-Python (no DB, no `mcp` package); the live round-trip is
covered by probe_mcp_memory_surface.py.

The axiom (DP32): every contribution enters as an attributed RAW observation;
what the workspace makes of it is a SEPARATE attributed DERIVED act; the raw is
never rewritten and the derived always cites its source (`retain + attribute +
cite`). This gate proves the MCP slice obeys it.

Asserts:
  1. INBOUND_ROOT exists, is `inbound/`, and is OUTSIDE the topology cut
     (sibling to uploads/ — not a sixth semantic-class root).
  2. The mcp caller is NOT locked from inbound/ (it's the foreign caller's raw
     home) but IS still locked from governance/constitution/persona/system/.
  3. remember routing lands the RAW observation in inbound/mcp/{client}/{slug}.md
     — never operation/, never a locked root, for every adversarial subject.
  4. resolve_remember_path is per-CLIENT (the per-principal sublane convention).
  5. The placement wake is DERIVE-AND-CITE, not rewrite-in-place: the prompt
     instructs deriving into operation/ with `derived_from`, and explicitly says
     NOT to rewrite/move the raw.
  6. The derived_from walk EXISTS (_extract_derived_from) and compose_trace
     consults it (the raw→derived chain).
  7. resolve_memory_path reads DERIVED-FIRST, raw as the fallback receipt.
"""

import inspect
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def _perception_roundtrip(tws):
    """Mocked end-to-end: a TrackWebSources fire retains each fetched feed body
    in the raw lane and the distilled signal cites them via derived_from. No DB,
    no network — write_revision + _fetch are stubbed; the structural flow is the
    assertion (the live fire is the optional validation step)."""
    import asyncio
    import types
    from services.mcp_composition import _extract_derived_from_list

    class MockTable:
        def __init__(self, store):
            self.store = store
            self._eq = {}

        def select(self, *a, **k):
            return self

        def eq(self, c, v):
            self._eq[c] = v
            return self

        def limit(self, n):
            return self

        def execute(self):
            path = self._eq.get("path")
            for p, c in self.store.items():
                if p == path:
                    return types.SimpleNamespace(data=[{"content": c}])
            return types.SimpleNamespace(data=[])

    class MockClient:
        def __init__(self):
            self.store = {}

        def table(self, n):
            return MockTable(self.store)

    import services.authored_substrate as asub
    saved_write = asub.write_revision
    saved_fetch = tws._fetch
    writes = []

    def fake_write_revision(client, *, user_id, path, content, authored_by, message):
        writes.append({"path": path, "authored_by": authored_by, "content": content})

    RSS = (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>'
        "<item><title>A</title><link>https://ex.com/a</link><description>d</description></item>"
        "</channel></rss>"
    )

    async def fake_fetch(url):
        return RSS

    try:
        asub.write_revision = fake_write_revision
        tws._fetch = fake_fetch
        client = MockClient()
        decl = "/workspace/operation/watch/_sources.yaml"
        client.store[decl] = (
            "sources:\n  - id: feedone\n    url: https://ex.com/f1\n"
            "  - id: feedtwo\n    url: https://ex.com/f2\n"
        )
        auth = types.SimpleNamespace(user_id="u1", client=client)
        res = asyncio.run(tws.handle_track_web_sources(
            auth, {"declaration": decl, "distills_to": "/workspace/operation/watch/_watch_signal.yaml"}))
    finally:
        asub.write_revision = saved_write
        tws._fetch = saved_fetch

    raws = [w for w in writes if "/inbound/web/" in w["path"]]
    sig = next((w for w in writes if w["path"].endswith("_watch_signal.yaml")), None)
    if not (res.get("success") and len(raws) == 2 and sig):
        return False, f"raws={len(raws)} sig={'y' if sig else 'n'} res={res.get('success')}"
    # raws attributed system:track-web-sources, land in the inbound/ raw lane
    raw_attr = all(w["authored_by"] == "system:track-web-sources" for w in raws)
    raw_paths = {w["path"] for w in raws}
    # the signal's derived_from cites EXACTLY the retained raws (the fan-in)
    cited = set(_extract_derived_from_list(sig["content"]))
    cites_raws = cited == raw_paths
    return (raw_attr and cites_raws), f"raw_attr={raw_attr} cited={len(cited)}=={len(raw_paths)}"


def main():
    results = []
    from services import mcp_composition as m
    from services import workspace_paths as wp
    from services.workspace_paths import CALLER_WRITE_POLICY

    # 1. INBOUND_ROOT exists, value, and is outside the cut (sibling to uploads/).
    cut_roots = (
        wp.GOVERNANCE_ROOT, wp.CONSTITUTION_ROOT, wp.PERSONA_ROOT,
        wp.OPERATION_ROOT, wp.SYSTEM_ROOT, wp.CONTRACT_ROOT,
    )
    results.append(_check(
        "1 INBOUND_ROOT is 'inbound/' and OUTSIDE the topology cut (sibling to uploads/)",
        getattr(wp, "INBOUND_ROOT", None) == "inbound/" and wp.INBOUND_ROOT not in cut_roots))

    # 2. mcp caller: NOT locked from inbound/, STILL locked from the governing roots.
    mcp_locks = CALLER_WRITE_POLICY["mcp"]
    inbound_open = not any("inbound/".startswith(p) for p in mcp_locks)
    governing_locked = all(r in mcp_locks for r in (
        wp.GOVERNANCE_ROOT, wp.CONSTITUTION_ROOT, wp.PERSONA_ROOT, wp.SYSTEM_ROOT))
    results.append(_check(
        "2 mcp caller may write inbound/ (raw home) but stays locked from governance/constitution/persona/system",
        inbound_open and governing_locked, f"mcp_locks={mcp_locks}"))

    # 3. remember routing lands RAW in inbound/mcp/, never operation/ or a locked root.
    probes = [None, "", "Acme Corp", "system", "identity", "governance",
              "persona", "constitution", "contract", "reports", "trading"]
    all_inbound = all(
        m.resolve_remember_path(a, client_name="claude.ai").startswith("inbound/mcp/")
        for a in probes)
    no_operation = not any(
        m.resolve_remember_path(a, client_name="claude.ai").startswith("operation/")
        for a in probes)
    no_locked = not any(
        any(m.resolve_remember_path(a, client_name="claude.ai").startswith(r) for r in mcp_locks)
        for a in probes)
    results.append(_check(
        "3 every remember RAW lands in inbound/mcp/ — never operation/, never a locked root",
        all_inbound and no_operation and no_locked))

    # 4. routing is per-CLIENT (the per-principal sublane convention, ADR-373-enforced later).
    p_claude = m.resolve_remember_path("Acme Corp", client_name="claude.ai")
    p_gpt = m.resolve_remember_path("Acme Corp", client_name="chatgpt")
    p_none = m.resolve_remember_path("Acme Corp", client_name=None)
    results.append(_check(
        "4 raw lane is per-client (inbound/mcp/{client}/...) — different clients, different sublanes",
        p_claude != p_gpt and "/claude" in p_claude and "/chatgpt" in p_gpt and "/unknown/" in p_none,
        f"claude={p_claude} gpt={p_gpt}"))

    # 5. placement wake is DERIVE-AND-CITE, not rewrite-in-place.
    wake_src = inspect.getsource(m.submit_foreign_write_wake)
    derive_and_cite = (
        "derived_from" in wake_src
        and "do NOT rewrite" in wake_src
        and "DERIVE" in wake_src
        and "operation/" in wake_src
    )
    no_old_move = "move or copy" not in wake_src  # the pre-ADR-376 rewrite-in-place phrasing
    results.append(_check(
        "5 placement wake is DERIVE-AND-CITE (derived_from + 'do NOT rewrite the raw'), not move/rewrite-in-place",
        derive_and_cite and no_old_move,
        f"derive_and_cite={derive_and_cite} no_old_move={no_old_move}"))

    # 6. the derived_from walk exists and compose_trace consults it (both
    #    directions: append the cited raw chain when on the derived file, AND
    #    forward-walk raw→derived when resolution lands on the raw lane — the
    #    real-run finding that the seat names the derived file by its own judgment,
    #    so name-match reaches the raw, and the citation is the only reliable link).
    has_extractor = hasattr(m, "_extract_derived_from")
    has_reverse = hasattr(m, "_find_derived_from_raw")
    trace_src = inspect.getsource(m.compose_trace)
    trace_walks = "_extract_derived_from" in trace_src and "derived_from" in trace_src
    forward_walk = "_find_derived_from_raw" in trace_src and "INBOUND_ROOT" in trace_src
    # the extractor resolves a bare ref to an absolute /workspace/ path
    extracted = m._extract_derived_from("derived_from: inbound/mcp/claude-ai/acme-corp.md\n# body") \
        if has_extractor else None
    results.append(_check(
        "6 derived_from walk BOTH ways: append raw chain on derived file + forward-walk raw→derived (real-run fix)",
        has_extractor and has_reverse and trace_walks and forward_walk
        and extracted == "/workspace/inbound/mcp/claude-ai/acme-corp.md",
        f"extracted={extracted} reverse={has_reverse} forward={forward_walk}"))

    # 7. resolve_memory_path reads DERIVED-FIRST, raw as fallback receipt. The
    #    derived query EXCLUDES the raw lane (not_.like INBOUND_ROOT) and runs
    #    BEFORE the raw-lane query (the `%/{INBOUND_ROOT}%/{slug}.md` match).
    #    Ordering is checked on the QUERY STATEMENTS, not docstring prose.
    rmp_src = inspect.getsource(m.resolve_memory_path)
    body = rmp_src.split('"""', 2)[-1]  # drop the docstring; reason over code only
    derived_query_pos = body.find("not_.like")            # the derived (excludes-raw) query
    raw_query_pos = body.find("INBOUND_ROOT}%/")          # the raw-lane query pattern
    derived_first = (
        derived_query_pos != -1 and raw_query_pos != -1
        and derived_query_pos < raw_query_pos
    )
    results.append(_check(
        "7 resolve_memory_path reads DERIVED-first (excludes raw lane) THEN raw as the fallback receipt",
        derived_first, f"derived@{derived_query_pos} raw@{raw_query_pos}"))

    # ----------------------------------------------------------------------
    # Perception slice (ADR-376 second conformance slice, 2026-06-26).
    # The web/RSS watch was the SOLE remaining DP32 violator, on the retain
    # clause only (it CITED via source_ref + ATTRIBUTED system:track-web-sources
    # but DISCARDED the fetched observation). TrackWebSources now RETAINS each
    # cited raw in inbound/web/{source}/{observed_at}.xml and the distilled
    # signal carries derived_from. This forced the §9 single-vs-list DECIDE.
    # ----------------------------------------------------------------------

    # 8. derived_from is a LIST (§9 DECIDED): the list reader handles all three
    #    on-wire shapes, the single-cite reader stays byte-identical to the MCP
    #    case (first element), and a multi-cite (perception) file walks N raws.
    single_mcp = m._extract_derived_from("derived_from: inbound/mcp/claude-ai/acme.md\n# body")
    list_inline = m._extract_derived_from_list("derived_from: [inbound/web/a/x.md, inbound/web/b/y.md]")
    list_block = m._extract_derived_from_list(
        "# header comment\nderived_from:\n  - /workspace/inbound/web/a/x.md\n"
        "  - /workspace/inbound/web/b/y.md\nwatch: foo")
    single_as_list = m._extract_derived_from_list("derived_from: inbound/mcp/claude-ai/acme.md")
    results.append(_check(
        "8 derived_from is a LIST (§9 DECIDED): list reader walks inline+block N cites; single-cite byte-identical",
        single_mcp == "/workspace/inbound/mcp/claude-ai/acme.md"
        and list_inline == ["/workspace/inbound/web/a/x.md", "/workspace/inbound/web/b/y.md"]
        and list_block == ["/workspace/inbound/web/a/x.md", "/workspace/inbound/web/b/y.md"]
        and single_as_list == ["/workspace/inbound/mcp/claude-ai/acme.md"],
        f"single={single_mcp} inline={len(list_inline)} block={len(list_block)}"))

    # 9. compose_trace walks ALL cited raws (not just the first) — the multi-cite
    #    fan-in shows every raw observation's chain (perception's N-source signal).
    trace_src2 = inspect.getsource(m.compose_trace)
    walks_all = (
        "_extract_derived_from_list" in trace_src2
        and "for cited in derived_froms" in trace_src2
    )
    results.append(_check(
        "9 compose_trace walks ALL cited raws (multi-cite fan-in), not just the first",
        walks_all))

    # 10. TrackWebSources RETAINS the cited raw + the signal carries derived_from
    #     (the retain-clause fix). Reasoned over the primitive's source: it writes
    #     to the inbound/web/ raw lane, attributed system:track-web-sources, and
    #     threads derived_from into the signal. Bounded to CITED observations
    #     (a successful fetch), never every fetched byte (DP32 D5).
    from services.primitives import track_web_sources as tws
    tws_src = inspect.getsource(tws)
    retains = (
        'INBOUND_WEB_PREFIX = "inbound/web/"' in tws_src
        and "_write_raw_observation" in tws_src
        and 'authored_by="system:track-web-sources"' in tws_src
        and "derived_from=raw_paths" in tws_src          # signal cites the retained raws
        and "raw_paths.append(raw_path)" in tws_src        # only on a successful fetch (cited)
    )
    # the raw lane is the inbound/ sibling, NOT operation/ or a program tree
    raw_in_inbound = "INBOUND_WEB_PREFIX}{_slug(source_id)}" in tws_src
    results.append(_check(
        "10 TrackWebSources RETAINS cited raw in inbound/web/ (attributed) + signal carries derived_from",
        retains and raw_in_inbound,
        f"retains={retains} raw_in_inbound={raw_in_inbound}"))

    # 11. End-to-end (mocked fetch + write): the fetched feed body lands in the
    #     raw lane immutably, and the distilled signal's derived_from cites it —
    #     a judgment can re-read the observation behind the signal (falsifiable).
    e2e_ok, e2e_detail = _perception_roundtrip(tws)
    results.append(_check(
        "11 e2e: raw feed body retained in inbound/web/ + signal derived_from cites it (round-trip)",
        e2e_ok, e2e_detail))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-376 assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
