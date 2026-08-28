#!/usr/bin/env python3
"""ADR-617 gate — an external principal is taught the document it can write.

DRIVEN, not grepped. The defect this closes was an INCORRECT SUCCESS (a reader
seeing `found: true` over a document whose cited blocks are empty-and-correct,
with nothing saying so), and a source-text check cannot see one of those. Every
assertion below runs the real composer or the real guard.

Run: python3 test_adr617_the_cited_document_crosses.py   (from api/)

Asserts:
  1. D2 — the artifact citation rule is a KERNEL constant, distinct from the
     derived_from rule, and the connector composes it.
  2. D3 — `open` names an artifact's citations, marks the projected ones, and
     excludes the marked <style> edge.
  3. D4 — both write doors refuse citation damage, and allow legitimate edits.
  4. The parser is span-aware and carries no undeclared dependency.
"""

import asyncio
import sys

_results = []


def _check(label, ok, detail=""):
    _results.append((label, bool(ok)))
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


ISLAND = (
    '<div data-block="table" data-block-id="b5" data-ref="op/d.csv" '
    'data-ref-kind="table" data-ref-rev="r1"></div>'
)
STYLE_EDGE = (
    '<style data-skin="true" data-ref="design-system/x/_design.yaml">.a{color:red}</style>'
)
HEAD = (
    '<html data-template="deck"><head>' + STYLE_EDGE + "</head><body>"
    "<p>intro</p>" + ISLAND +
    '<img data-ref="op/logo.png" data-ref-rev="r9" alt="">'
    "<p>outro</p></body></html>"
)


class _Q:
    def __init__(self, rows):
        self._rows = rows

    def __getattr__(self, _n):
        return lambda *a, **k: self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class _Auth:
    user_id = "u"
    workspace_id = "w"

    def __init__(self, rows):
        self.client = type("C", (), {"table": lambda _s, _n: _Q(rows)})()


def main():
    from services import mcp_composition as m

    # Imported DEFENSIVELY, and the guards likewise below. A bare import (or a
    # bare attribute call) raises when the thing is absent, and that aborts
    # main() and hides every assertion after it — the crashing-gate trap. A
    # missing piece must make its OWN rows red, which is the only way this
    # gate can be falsified against the pre-fix tree.
    _subs = __import__("services.authored_substrate", fromlist=["x"])
    citation_islands = getattr(_subs, "citation_islands", None) or (lambda c: [])
    _edit_guard = getattr(m, "_refuse_citation_damage", None) or (lambda *a: None)

    async def _save_guard(*a):
        fn = getattr(m, "_refuse_citation_loss_on_save", None)
        return await fn(*a) if fn else None

    # ── 1. D2 — the rule is a kernel constant, and it is NOT the other one ──
    from services import workspace_paths as wp

    rule = getattr(wp, "PARTICIPANT_ARTIFACT_CITATION_RULE", "")
    _check(
        "1a the artifact citation rule is a KERNEL constant (composed by both "
        "surfaces, never owned by the MCP package)",
        bool(rule) and "data-ref" in rule,
    )
    # The two rules answer different questions and the ADR turns on not merging
    # them: derived_from is provenance BETWEEN files; data-ref is a projection
    # INSIDE one. A gate that accepted either would let a future edit collapse
    # them back together.
    _check(
        "1b it is DISTINCT from the derived_from rule (provenance between "
        "files vs a live projection inside one)",
        rule.strip() != (wp.PARTICIPANT_CITATION_RULE or "").strip()
        and "derived_from" in wp.PARTICIPANT_CITATION_RULE
        and "derived_from" not in rule,
    )
    _check(
        "1c it teaches the three load-bearing consequences: empty is correct, "
        "the source is authoritative, keep the citation whole",
        "empty" in rule.lower()
        and ("never" in rule.lower() and "inside" in rule.lower())
        and "data-ref-rev" in rule,
    )
    server_src = open("mcp_server/server.py", encoding="utf-8").read()
    _check(
        "1d the connector COMPOSES it (not restated inline — the ADR-533 D1 rule)",
        "PARTICIPANT_ARTIFACT_CITATION_RULE" in server_src
        and rule.split("\n")[0] not in server_src,
    )

    # ── 2. D3 — open names the citations ────────────────────────────────
    auth = _Auth([{  # noqa: F841
        "path": "/workspace/op/deck.html", "content": HEAD,
        "updated_at": "t", "content_type": "text/html",
    }])
    loop = asyncio.get_event_loop()
    r = loop.run_until_complete(m.compose_open(auth, "op/deck.html"))
    cites = {c["path"]: c for c in (r.get("citations") or [])}

    _check(
        "2a open NAMES what the document cites (the rider exists and is populated)",
        "op/d.csv" in cites and "op/logo.png" in cites,
        f"({len(cites)} cited)",
    )
    _check(
        "2b a PROJECTED citation is marked — the empty element that read as an "
        "empty slide is now legible as a working citation",
        cites.get("op/d.csv", {}).get("projected") is True,
    )
    _check(
        "2c the pin is reported (a floating citation can only ever dangle)",
        cites.get("op/logo.png", {}).get("pinned") is True,
    )
    # A marked <style> wears data-ref as a trace EDGE, not a projection. Listing
    # it would send the reader to a stylesheet manifest to understand a deck.
    _check(
        "2d the marked <style> EDGE is excluded from citations",
        not any("_design.yaml" in p for p in cites),
    )
    _check(
        "2e the explanation SAYS it — a host rendering only prose still learns "
        "the document has projected holes",
        "CITES" in (r.get("explanation") or "")
        and "EMPTY" in (r.get("explanation") or ""),
    )
    # A plain prose file must not grow a citations story it has no use for.
    auth_md = _Auth([{"path": "/workspace/op/n.md", "content": "# hi\n\nplain",
                      "updated_at": "t", "content_type": "text/markdown"}])
    r_md = loop.run_until_complete(m.compose_open(auth_md, "op/n.md"))
    _check(
        "2f a non-citing file reports no citations and says nothing about them",
        r_md.get("citations") == []
        and "CITES" not in (r_md.get("explanation") or ""),
    )

    # ── 3. D4 — the write doors ─────────────────────────────────────────
    _check(
        "3a edit REFUSES an anchor that removes a citation ('a data-ref can't "
        "be halved', ported from the canvas)",
        (_edit_guard(ISLAND, "<p>a table</p>", "op/deck.html") or {})
        .get("error") == "citation_damage",
    )
    _check(
        "3b edit ALLOWS an edit that keeps the citation whole",
        _edit_guard(
            f"<p>intro</p>{ISLAND}", f"<p>INTRO</p>{ISLAND}", "op/deck.html") is None,
    )
    _check(
        "3c edit ALLOWS ordinary prose (the guard is not a tax on every edit)",
        _edit_guard("<p>intro</p>", "<p>INTRO</p>", "op/deck.html") is None,
    )

    dropped = '<html data-template="deck"><body><p>intro</p></body></html>'
    filled = HEAD.replace(
        'data-ref-rev="r1"></div>',
        'data-ref-rev="r1"><table><tr><td>1994</td></tr></table></div>')
    _check(
        "3d save REFUSES dropping a citation the head carried",
        (loop.run_until_complete(
            _save_guard(auth, "/workspace/op/deck.html",
                                            "op/deck.html", dropped)) or {}
         ).get("error") == "citation_damage",
    )
    _check(
        "3e save REFUSES filling an empty island — THE helpful-paste, whose "
        "bytes are dead on arrival (overwritten at the next render)",
        (loop.run_until_complete(
            _save_guard(auth, "/workspace/op/deck.html",
                                            "op/deck.html", filled)) or {}
         ).get("error") == "citation_damage",
    )
    _check(
        "3f save ALLOWS a legitimate rewrite that leaves citations intact",
        loop.run_until_complete(
            _save_guard(
                auth, "/workspace/op/deck.html", "op/deck.html",
                HEAD.replace("<p>intro</p>", "<p>REWRITTEN</p>"))) is None,
    )
    # A guard that cannot read must not block a legitimate save.
    class _Boom:
        user_id = "u"; workspace_id = "w"
        class client:  # noqa: D106
            @staticmethod
            def table(_n):
                raise RuntimeError("postgrest down")
    _check(
        "3g the save guard degrades OPEN when it cannot read the head",
        loop.run_until_complete(
            _save_guard(
                _Boom(), "/workspace/op/deck.html", "op/deck.html", dropped)) is None,
    )

    # ── 4. the parser ───────────────────────────────────────────────────
    isl = {i["ref"]: i for i in citation_islands(HEAD)}
    _check(
        "4a the parser is SPAN-aware (inner bounds, not just the attribute — "
        "extract_data_ref_paths gives paths and cannot answer 'where does it end')",
        isl["op/d.csv"]["inner_end"] >= isl["op/d.csv"]["inner_start"]
        and isl["op/d.csv"]["inner"] == "",
    )
    _check(
        "4b a void element reports an empty body, never an unclosed island",
        isl["op/logo.png"]["inner_start"] == isl["op/logo.png"]["inner_end"],
    )
    nested = '<div data-ref="a/b.html" data-ref-kind="component"><div>x</div></div>'
    _check(
        "4c a nested same-tag child does not end the island early",
        citation_islands(nested)[0]["inner"] == "<div>x</div>",
    )
    _check(
        "4d an UNCLOSED island degrades conservatively (span to the end — the "
        "guard gets stricter, never looser)",
        citation_islands('<div data-ref="a/b.csv">tail')[0]["inner_end"]
        == len('<div data-ref="a/b.csv">tail'),
    )
    # lxml is importable in the dev venv and ABSENT from requirements.txt —
    # exactly how a serving path acquires an undeclared dependency.
    # Test the IMPORT, not the word: the module's own docstring names lxml to
    # say why it is NOT used, and a substring check reads that prose as a
    # dependency (it did, on the first run of this gate).
    import re as _re
    subs = open("services/authored_substrate.py", encoding="utf-8").read()
    reqs = open("requirements.txt", encoding="utf-8").read().lower()
    imports_lxml = bool(_re.search(r"^\s*(?:import|from)\s+lxml\b", subs, _re.M))
    _check(
        "4e the parser carries no undeclared dependency (no lxml IMPORT on the "
        "serving path while it is absent from requirements.txt)",
        not imports_lxml or "lxml" in reqs,
    )

    ok = all(v for _, v in _results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — "
          f"{sum(1 for _, v in _results if v)}/{len(_results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
