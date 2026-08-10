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

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
