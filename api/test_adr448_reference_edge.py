"""
ADR-448 — the reference edge: derived_from on the ledger.

Structural gate for the column + the lift + the derive step's first writers.
Pure-Python (no DB); the live round-trip is an upload → projection → dependents
probe. Run directly: `python test_adr448_reference_edge.py` (the checks print
✗ but pytest would PASS them — ADR-415 lesson).

Asserts:
  1. write_revision + _insert_revision accept derived_from (default None);
     _insert_revision writes the column only when non-empty (byte-identical
     for ordinary writes + safe against a not-yet-migrated DB).
  2. The parser lives in authored_substrate (relocated) and mcp_composition
     imports it — no duplicate definition (Singular Implementation).
  3. extract_derived_from_list handles the three on-wire shapes; the
     data-ref extractor normalizes + dedupes.
  4. _resolve_derived_from rules: explicit param → derivation; frontmatter
     lift → derivation; artifact data-ref lift → edges only (kind stays
     authored); junk prose never becomes an edge; self-cites drop; an
     explicit revision_kind always wins.
  5. The intake writers complete: the upload raw tags 'observation'
     (the ADR-423 D3 gap); the projection writer passes derived_from +
     'derivation' (the first live derivation writer).
  6. The write-path wrappers (UserMemory.write, AgentWorkspace.write) +
     the WriteFile primitive thread derived_from; the tool schema documents it.
  7. Readers: Revision carries derived_from; list/read revision select it;
     ReadRevision forwards it; trace reads the column first; list_dependents
     exists; the dependents route is registered; migration 215 exists.
"""

import inspect
import os
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    passed = True

    # ── 1. signatures + insert discipline ────────────────────────────────
    from services.authored_substrate import (
        Revision,
        _insert_revision,
        _resolve_derived_from,
        extract_data_ref_paths,
        extract_derived_from_list,
        list_dependents,
        write_revision,
    )

    wr = inspect.signature(write_revision).parameters
    ins = inspect.signature(_insert_revision).parameters
    passed &= _check(
        "write_revision has derived_from default None",
        "derived_from" in wr and wr["derived_from"].default is None,
    )
    passed &= _check(
        "_insert_revision has derived_from default None",
        "derived_from" in ins and ins["derived_from"].default is None,
    )

    captured = {}

    class _Result:
        data = [{"id": "rev-1"}]

    class _Table:
        def insert(self, row):
            captured["row"] = row
            return self

        def execute(self):
            return _Result()

    class _Client:
        def table(self, name):
            return _Table()

    _insert_revision(
        _Client(),
        user_id="u1",
        path="/workspace/a.md",
        blob_sha="sha",
        parent_version_id=None,
        authored_by="operator",
        author_identity_uuid=None,
        message="m",
    )
    passed &= _check(
        "default insert omits derived_from (byte-identical / pre-migration safe)",
        "derived_from" not in captured["row"] and "revision_kind" not in captured["row"],
    )
    _insert_revision(
        _Client(),
        user_id="u1",
        path="/workspace/a.md",
        blob_sha="sha",
        parent_version_id=None,
        authored_by="operator",
        author_identity_uuid=None,
        message="m",
        revision_kind="derivation",
        derived_from=["/workspace/inbound/uploads/operator/x.pdf"],
    )
    passed &= _check(
        "non-empty edge + kind land on the row",
        captured["row"].get("derived_from") == ["/workspace/inbound/uploads/operator/x.pdf"]
        and captured["row"].get("revision_kind") == "derivation",
    )

    # ── 2. one parser, relocated ──────────────────────────────────────────
    import services.mcp_composition as mcp

    passed &= _check(
        "mcp_composition imports the parser from authored_substrate",
        mcp._extract_derived_from_list is extract_derived_from_list,
    )
    mcp_src = inspect.getsource(mcp)
    passed &= _check(
        "no duplicate parser body in mcp_composition",
        "def _extract_derived_from_list" not in mcp_src
        and "def _normalize_inbound_ref" not in mcp_src,
    )

    # ── 3. the parser's three shapes + the data-ref extractor ────────────
    scalar = "derived_from: /workspace/inbound/mcp/claude.ai/acme.md\n\n# T\nbody"
    inline = "derived_from: [a.md, b.md]\n\nbody"
    block = "derived_from:\n  - /workspace/inbound/web/x/1.md\n  - /workspace/inbound/web/y/2.md\n\nbody"
    passed &= _check(
        "bare scalar",
        extract_derived_from_list(scalar) == ["/workspace/inbound/mcp/claude.ai/acme.md"],
    )
    passed &= _check(
        "inline list",
        extract_derived_from_list(inline) == ["/workspace/a.md", "/workspace/b.md"],
    )
    passed &= _check(
        "block list",
        extract_derived_from_list(block)
        == ["/workspace/inbound/web/x/1.md", "/workspace/inbound/web/y/2.md"],
    )
    html = (
        '<div data-ref="operation/reports/q3.md" data-ref-rev="r1"></div>'
        '<span data-ref="/workspace/operation/reports/q3.md"></span>'
        '<img data-ref="assets/logo.svg">'
    )
    passed &= _check(
        "data-ref extraction normalizes + dedupes",
        extract_data_ref_paths(html)
        == ["/workspace/operation/reports/q3.md", "/workspace/assets/logo.svg"],
    )

    # ── 4. the resolve rules ──────────────────────────────────────────────
    edges, kind = _resolve_derived_from("/workspace/d.md", "plain body", ["inbound/uploads/operator/x.pdf"], "authored")
    passed &= _check(
        "explicit param → normalized edge + kind flips to derivation",
        edges == ["/workspace/inbound/uploads/operator/x.pdf"] and kind == "derivation",
    )
    edges, kind = _resolve_derived_from("/workspace/d.md", "plain body", ["x.pdf"], "observation")
    passed &= _check("explicit revision_kind always wins", kind == "observation")
    edges, kind = _resolve_derived_from("/workspace/d.md", scalar, None, "authored")
    passed &= _check(
        "frontmatter lift → edge + derivation",
        edges == ["/workspace/inbound/mcp/claude.ai/acme.md"] and kind == "derivation",
    )
    edges, kind = _resolve_derived_from("/workspace/d.md", "derived_from: the meeting\n\nbody", None, "authored")
    passed &= _check("junk prose never becomes an edge", edges is None and kind == "authored")
    edges, kind = _resolve_derived_from("/workspace/art.html", html, None, "authored")
    passed &= _check(
        "artifact data-ref lift → edges only, kind stays authored",
        edges == ["/workspace/operation/reports/q3.md", "/workspace/assets/logo.svg"]
        and kind == "authored",
    )
    edges, kind = _resolve_derived_from("/workspace/plain.md", "no conventions here", None, "authored")
    passed &= _check("no conventions → no edge", edges is None and kind == "authored")
    edges, kind = _resolve_derived_from(
        "/workspace/self.md", "x", ["/workspace/self.md"], "authored"
    )
    passed &= _check("self-cite drops", edges is None)

    # ── 5. the intake writers complete ────────────────────────────────────
    import services.documents as documents

    doc_src = inspect.getsource(documents.process_document)
    passed &= _check(
        "upload raw tags 'observation' (ADR-423 D3 gap closed)",
        'revision_kind="observation"' in doc_src,
    )
    from services.primitives import extract_text_from_blob as etb

    etb_src = inspect.getsource(etb.handle_extract_text_from_blob)
    passed &= _check(
        "projection is the first live derivation writer",
        'revision_kind="derivation"' in etb_src and "derived_from=[raw_path]" in etb_src,
    )

    # ── 6. the wrappers + the primitive thread the edge ──────────────────
    from services.workspace import AgentWorkspace, UserMemory

    passed &= _check(
        "UserMemory.write accepts derived_from",
        "derived_from" in inspect.signature(UserMemory.write).parameters,
    )
    passed &= _check(
        "AgentWorkspace.write accepts derived_from",
        "derived_from" in inspect.signature(AgentWorkspace.write).parameters,
    )
    from services.primitives import workspace as prim_ws

    hw_src = inspect.getsource(prim_ws.handle_write_file)
    passed &= _check(
        "handle_write_file threads derived_from",
        'input.get("derived_from")' in hw_src and "derived_from=derived_from" in hw_src,
    )
    passed &= _check(
        "WriteFile tool schema documents derived_from",
        "derived_from" in prim_ws.WRITE_FILE_TOOL["input_schema"]["properties"],
    )

    # ── 7. the readers ────────────────────────────────────────────────────
    passed &= _check(
        "Revision dataclass carries derived_from",
        "derived_from" in {f.name for f in Revision.__dataclass_fields__.values()},
    )
    from services import authored_substrate as asub

    lr_src = inspect.getsource(asub.list_revisions)
    rr_src = inspect.getsource(asub.read_revision)
    passed &= _check("list_revisions selects derived_from", "derived_from" in lr_src)
    passed &= _check("read_revision selects derived_from", "derived_from" in rr_src)
    from services.primitives import revisions as prim_rev

    rrh_src = inspect.getsource(prim_rev.handle_read_revision)
    passed &= _check("ReadRevision forwards derived_from", "derived_from" in rrh_src)
    trace_src = inspect.getsource(mcp.compose_trace)
    passed &= _check(
        "trace reads the column first (read-both)",
        'revisions[0].get("derived_from")' in trace_src
        and "_extract_derived_from_list" in trace_src,
    )
    walk_src = inspect.getsource(mcp._find_derived_from_raw)
    passed &= _check(
        "reverse walk is the dependents query",
        "list_dependents" in walk_src,
    )
    ld = inspect.signature(list_dependents).parameters
    passed &= _check(
        "list_dependents(client, *, user_id, path, limit)",
        {"user_id", "path", "limit"} <= set(ld.keys()),
    )
    routes_src = open(os.path.join(os.path.dirname(__file__), "routes", "workspace.py")).read()
    passed &= _check(
        "dependents route registered",
        '"/workspace/file/dependents"' in routes_src and "list_dependents" in routes_src,
    )
    mig = os.path.join(
        os.path.dirname(__file__), "..", "supabase", "migrations", "215_adr448_derived_from.sql"
    )
    mig_src = open(mig).read() if os.path.exists(mig) else ""
    passed &= _check(
        "migration 215 adds the column + GIN index",
        "ADD COLUMN IF NOT EXISTS derived_from JSONB" in mig_src and "GIN" in mig_src,
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
