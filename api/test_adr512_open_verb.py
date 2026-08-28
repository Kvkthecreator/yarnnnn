"""ADR-512 regression gate — the file is the unit of interop (`open` + the handle grammar).

Structural invariants for the fourth consumer verb and the D5 reference grammar.
Pure-Python (no `mcp` package locally — that ships only on the MCP Render
service), same pattern as test_adr543_file_native_surface.py: composition-layer
checks run live; server.py is checked at source-text level.

Run: python3 test_adr512_open_verb.py  (from api/)

Asserts:
  1. The D5 handle grammar parses all three spellings to one relative path,
     rejects foreign schemes and workspace escapes, and round-trips via
     format_file_reference.
  2. compose_open EXISTS and is exact-read shaped (no search fallback import).
  3. server.py registers the tool under the NAME `open` without shadowing the
     builtin (symbol is open_file), read-only annotated, with an output schema.
  4. The connector instructions dropped the memory-identity framing ("durable,
     attributed memory") for the workspace framing, and teach every verb.
  5. The ADR-543 file-native surface is registered in full
     (open/list/search/save/history/share) and the memory verbs are gone.
  6. (ADR-574 §2b, closed 2026-08-28) `open` REACHES THE BODY: the marked
     machine-composed stylesheets are elided, the unmarked layout style
     survives, and offset/next_offset page a large file to its end. DRIVEN
     against a real-shaped artifact — the defect was an incorrect success
     (`found: true` over a CSS-only payload), which no source-text check sees.
"""

import sys

# ADR-533 D2: the instructions are composed at import time (kernel constants +
# the derived verb table), so assertions about what the host is TAUGHT must read
# the rendered output. The extraction lives in the ADR-533 gate — one home.
from test_adr533_participant_contract import rendered_instructions as _rendered_instructions


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []
    from services import mcp_composition as m

    # 1. the handle grammar
    p = m.parse_file_reference
    results.append(_check(
        "1a all three spellings resolve to the same relative path",
        p("yarnnn://workspace/operation/reports/q3.md")
        == p("/workspace/operation/reports/q3.md")
        == p("operation/reports/q3.md")
        == "operation/reports/q3.md"))
    results.append(_check(
        "1b foreign schemes / empties / escapes rejected",
        p("https://example.com/x.md") is None
        and p("") is None and p(None) is None
        and p("yarnnn://workspace/../governance/x.yaml") is None
        and p("operation/../../etc/passwd") is None))
    results.append(_check(
        "1c format round-trips through parse",
        m.format_file_reference("operation/x.md") == "yarnnn://workspace/operation/x.md"
        and p(m.format_file_reference("/workspace/operation/x.md")) == "operation/x.md"))

    # 2. compose_open exists; open stays exact (no QueryKnowledge in its body)
    results.append(_check("2a compose_open EXISTS", hasattr(m, "compose_open")))
    import inspect
    src = inspect.getsource(m.compose_open)
    results.append(_check(
        "2b open never falls back to search (no QueryKnowledge/resolve_trace_path in compose_open)",
        "QueryKnowledge" not in src and "resolve_trace_path" not in src))

    # 3 + 4 + 5. server.py source-text (module not importable without `mcp`)
    with open("mcp_server/server.py", encoding="utf-8") as f:
        server_src = f.read()
    results.append(_check(
        "3a tool registered under NAME open via symbol open_file (builtin unshadowed)",
        'name="open"' in server_src and "async def open_file(" in server_src
        and "\nasync def open(" not in server_src))
    results.append(_check(
        "3b open is read-only annotated + schema'd",
        '"open": {' in server_src and server_src.count("readOnlyHint=True") >= 3))
    results.append(_check(
        "4a memory-identity framing GONE from instructions",
        "durable, attributed memory" not in server_src))
    # ADR-533 D2: the verb table is DERIVED from `_INTEROP_VERBS` at import time,
    # so the bullets no longer appear as literals in the source. The INVARIANT is
    # unchanged (every verb is taught) — assert it against the RENDERED
    # instructions instead of grepping source text for a bullet glyph.
    results.append(_check(
        "4b instructions teach every verb (rendered, ADR-533 D2)",
        all(f"• {v}" in _rendered_instructions()
            for v in ("open", "list", "search", "save", "history", "share"))))
    results.append(_check(
        "5 ADR-543 file-native surface registered; memory verbs gone",
        all(f"async def {v}(" in server_src
            for v in ("list_files", "search", "history"))
        and not any(f"async def {v}(" in server_src
                    for v in ("remember", "recall", "trace"))))

    # ── 6. The body is REACHABLE (ADR-574 §2b closed) ───────────────────
    # DRIVEN, not grepped. The defect was an incorrect success: `open` returned
    # `found: true` with a payload holding zero authored content, because a
    # Studio artifact inlines ~31KB of kernel CSS ahead of <body> and the cap
    # landed mid-stylesheet. A source-text check cannot see that; only running
    # the composer against an artifact shaped like the real one can.
    import asyncio

    # Imported DEFENSIVELY. A bare `from … import elide_presentation_css`
    # raises when the helper is absent, and an ImportError here would abort
    # main() and hide every assertion below it — the crashing-gate trap
    # (a gate that dies on the defect it guards reports nothing). Absent
    # helper → each §6 row fails on its own merits, which is the whole point.
    elide_presentation_css = getattr(
        __import__("services.machine_projection", fromlist=["x"]),
        "elide_presentation_css", None,
    ) or (lambda markup: (markup, 0))

    KERNEL = '<style data-kernel="true" data-kernel-v="19">' + ("/*k*/" * 6000) + "</style>"
    SKIN = '<style data-skin="true">' + ("/*s*/" * 500) + "</style>"
    LAYOUT = "<style>.layout{color:red}</style>"
    BODY = "<p>FIRST-AUTHORED-WORD</p>" + ("<p>filler</p>" * 3000) + "<p>LAST-AUTHORED-WORD</p>"
    ARTIFACT = ("<!doctype html><html><head>" + LAYOUT + KERNEL + SKIN
                + "</head><body>" + BODY + "</body></html>")

    class _Q:
        def __init__(self, rows): self._rows = rows
        def __getattr__(self, _n): return lambda *a, **k: self
        def execute(self):
            return type("R", (), {"data": self._rows})()

    class _Auth:
        user_id = "u"; workspace_id = "w"
        def __init__(self, rows):
            self.client = type("C", (), {"table": lambda _s, _n: _Q(rows)})()

    auth = _Auth([{"path": "/workspace/probe.html", "content": ARTIFACT,
                   "updated_at": "t", "content_type": "text/html"}])
    page1 = asyncio.get_event_loop().run_until_complete(
        m.compose_open(auth, "probe.html"))

    results.append(_check(
        "6a the FIRST authored word is in the FIRST page — the ADR-574 §2b "
        "incorrect success (CSS-only payload under found:true) is closed",
        "FIRST-AUTHORED-WORD" in (page1.get("content") or "")))
    results.append(_check(
        "6b the machine-composed sheets are elided from the read",
        "/*k*/" not in (page1.get("content") or "")
        and "/*s*/" not in (page1.get("content") or "")))
    results.append(_check(
        "6c the UNMARKED layout style SURVIVES — it is baked once and never "
        "retrofitted, so it is the one sheet that can hold an authored edit",
        ".layout{color:red}" in (page1.get("content") or "")))

    # The continuation `list` has carried since ADR-545 D3. Without it a file
    # past the cap has no path to its own tail: `search` returns an excerpt and
    # points back at `open`, and `history` carries messages, not body text.
    # Called through a shim for the same reason the import above is defensive:
    # pre-continuation, `offset` is an unexpected kwarg and the TypeError would
    # abort the run and hide every row below. A verb with no continuation must
    # FAIL these rows, not silence them.
    def _open(off=0):
        try:
            return asyncio.get_event_loop().run_until_complete(
                m.compose_open(auth, "probe.html", offset=off))
        except TypeError:
            return {"unsupported": True, "content": "", "truncated": False}

    seen, off, pages = "", 0, 0
    while True:
        r = _open(off)
        seen += r.get("content") or ""
        pages += 1
        if not r.get("truncated") or pages > 25:
            break
        off = r["next_offset"]
    results.append(_check(
        "6d paging REACHES THE END — offset/next_offset walk the whole file",
        "LAST-AUTHORED-WORD" in seen, f"({pages} pages)"))
    results.append(_check(
        "6e no character is lost or duplicated across page boundaries",
        len(seen) == page1.get("content_chars"),
        f"walked={len(seen)} total={page1.get('content_chars')}"))
    results.append(_check(
        "6f a truncated page ALWAYS carries next_offset (a dead-end "
        "`truncated: true` is what made the cap unescapable)",
        all(not _open(o).get("truncated") or "next_offset" in _open(o)
            for o in (0, 24000, 48000))
        and not _open(0).get("unsupported")))
    past = _open(10 ** 9)
    results.append(_check(
        "6g an offset past the end is an honest empty read, not a crash",
        past.get("found") and past.get("content") == ""
        and not past.get("truncated") and "past its end" in past.get("explanation", "")))

    # The elision is a READ-path act. If it ever reached a write door the
    # ADR-453 D2 retrofit contract would be silently undone on the next save.
    from services import authoring as _authoring
    results.append(_check(
        "6h the elision never reaches a write door (read path only)",
        "elide_presentation_css" not in _authoring.__dict__
        and elide_presentation_css(ARTIFACT)[1] > 0))

    # The cap's own comment used to promise an escape hatch that did not
    # exist ("history/search stay available for the rest"). That sentence is
    # what made the dead end look intentional.
    _cap_src = open("services/mcp_composition.py", encoding="utf-8").read()
    results.append(_check(
        "6i the cap no longer claims history/search reach the rest",
        "history/search stay\n#: available" not in _cap_src
        and "next_offset" in _cap_src))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
