"""
ADR-588 — folders are first-class; the told-name is an accepted address.

Two defects, one root cause: FOLDERS DO NOT EXIST IN THE SUBSTRATE. A folder
exists iff a file exists under its path prefix, and the tree is derived from
paths. Two consequences followed, and this gate pins both fixes.

D1 — the FOLDER MARKER. An empty folder is now expressible as a real
`workspace_files` row at the folder's own trailing-slash path carrying
`content_type='inode/directory'`. It replaces the deleted README seed, which
wrote a document attributed to "operator" that the operator never authored.
A marker must never render as a document to an operator, an LLM participant,
or an export.

D2 — the home ALIAS. `PARTICIPANT_FILESYSTEM_MODEL` tells every LLM participant
that two homes are provided, BY THEIR DISPLAY NAMES: "Documents" and "Downloads".
The kernel paths are `operation/` and `inbound/`, and nothing translated between
them at the write door — so a participant writing the name it was told created a
REAL top-level root that `root_metadata` title-cases back into an exact visual
twin of the real home. The told-name now RESOLVES to the real home.

D3 — a TOP-LEVEL folder may not take a home's display name.

Pure-Python source/behaviour guard (no DB, no `mcp` package). Script-style AND
pytest-collectable — `test_adr588()` asserts `run() == 0`.
"""

import inspect
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    ok = True

    from services.workspace_paths import (
        FOLDER_MARKER_CONTENT_TYPE,
        folder_marker_path,
        is_folder_marker,
        reserved_top_level_folder_reason,
        WORKSPACE_ROOTS,
    )

    # ── D1: the marker's shape ───────────────────────────────────────────────
    ok &= _check("D1 marker content type is the real directory MIME",
                 FOLDER_MARKER_CONTENT_TYPE == "inode/directory")

    # The trailing slash is load-bearing: it is what makes a marker
    # unambiguously not-a-file at every path-shaped consumer (git export's
    # `_repo_rel`, UserMemory.list, the unique (workspace_id, path) index).
    ok &= _check("D1 marker path is absolute + trailing-slash, from any spelling",
                 folder_marker_path("deals/acme")
                 == folder_marker_path("/workspace/deals/acme")
                 == folder_marker_path("workspace/deals/acme/")
                 == "/workspace/deals/acme/")

    ok &= _check("D1 a trailing-slash path IS a marker (path shape alone)",
                 is_folder_marker("/workspace/deals/acme/"))
    ok &= _check("D1 the content_type alone also answers",
                 is_folder_marker("/workspace/deals/acme", "inode/directory"))
    ok &= _check("D1 an ordinary document is NOT a marker",
                 not is_folder_marker("/workspace/deals/acme.md")
                 and not is_folder_marker("/workspace/operation/reports/q3/output.md"))

    # ── D1: _build_tree renders a marker as a FOLDER, never a file ───────────
    from routes.workspace import _build_tree

    rows = [
        {"path": "/workspace/operation/empty-folder/",
         "content_type": "inode/directory", "updated_at": "2026-08-20T00:00:00Z"},
        {"path": "/workspace/operation/notes.md",
         "content_type": "text/markdown", "updated_at": "2026-08-20T00:00:00Z"},
    ]
    tree = _build_tree(rows, "/workspace/operation")
    by_name = {n["name"]: n for n in tree}

    ok &= _check("D1 an EMPTY marked folder appears in the tree at all",
                 "empty-folder" in by_name)
    ok &= _check("D1 the marker is typed 'folder', not 'file'",
                 by_name.get("empty-folder", {}).get("type") == "folder")
    ok &= _check("D1 the empty folder has no children",
                 by_name.get("empty-folder", {}).get("children") == [])
    def _walk(nodes):
        for n in nodes:
            yield n
            yield from _walk(n.get("children") or [])

    all_nodes = list(_walk(tree))
    # The pre-588 failure shape, exactly: a marker row falling through to the
    # file branch produces an EMPTY-NAMED file node nested inside the folder
    # its own path synthesized. Walk the whole tree — a top-level-only check
    # misses it, because the leak is one level down.
    ok &= _check("D1 no node is named by the raw marker path",
                 not any(n["path"].endswith("/") for n in all_nodes))
    ok &= _check("D1 no empty-named node leaks anywhere in the tree",
                 all(n["name"] for n in all_nodes))
    ok &= _check("D1 no marker is typed 'file' anywhere in the tree",
                 not any(n["type"] == "file" and not n["name"].count(".")
                         for n in all_nodes if n["path"].rstrip("/").endswith("empty-folder")))
    ok &= _check("D1 an ordinary file still renders as a file",
                 by_name.get("notes.md", {}).get("type") == "file")

    # A marker and a document under the SAME folder converge on ONE node.
    rows2 = [
        {"path": "/workspace/operation/deals/", "content_type": "inode/directory",
         "updated_at": "2026-08-20T00:00:00Z"},
        {"path": "/workspace/operation/deals/acme.md", "content_type": "text/markdown",
         "updated_at": "2026-08-20T00:00:00Z"},
    ]
    tree2 = _build_tree(rows2, "/workspace/operation")
    deals = [n for n in tree2 if n["name"] == "deals"]
    ok &= _check("D1 marker + document converge on ONE folder node",
                 len(deals) == 1 and deals[0]["type"] == "folder"
                 and [c["name"] for c in deals[0]["children"]] == ["acme.md"])

    # ── D1: a marker never reaches a participant / export / search ───────────
    from services.export.git_export import _repo_rel
    ok &= _check("D1 git export excludes markers (no colliding zero-byte blob)",
                 _repo_rel("/workspace/deals/acme/") is None
                 and _repo_rel("/workspace/deals/acme.md") == "deals/acme.md")

    from services.primitives.embed import is_embed_eligible, is_searchable_root
    ok &= _check("D1 a marker is never embedded",
                 is_embed_eligible("/workspace/operation/deals/")[0] is False)
    ok &= _check("D1 a marker is never a search target",
                 is_searchable_root("/workspace/operation/deals/") is False
                 and is_searchable_root("/workspace/operation/deals/acme.md") is True)

    # The listing surfaces filter on the singular predicate.
    import services.mcp_composition as mcpc
    list_src = inspect.getsource(mcpc.compose_list)
    ok &= _check("D1 MCP `list` filters folder markers",
                 "is_folder_marker" in list_src)
    open_src = inspect.getsource(mcpc.compose_open)
    ok &= _check("D1 MCP `open` names a folder instead of returning empty content",
                 "is_folder_marker" in open_src)

    import services.primitives.workspace as pw
    ok &= _check("D1 ListFiles filters folder markers",
                 "is_folder_marker" in inspect.getsource(pw._list_tree))
    ok &= _check("D1 QueryKnowledge filters folder markers",
                 "is_folder_marker" in inspect.getsource(pw.handle_query_knowledge))

    from services.workspace import UserMemory
    ok &= _check("D1 UserMemory.list filters folder markers",
                 "is_folder_marker" in inspect.getsource(UserMemory.list))

    import routes.workspace as rw
    ok &= _check("D1 Recents excludes folder markers",
                 "is_folder_marker" in inspect.getsource(rw._is_authored_substrate_path))
    ok &= _check("D1 roots counts markers as EXISTENCE, not as files",
                 "marker_segs" in inspect.getsource(rw.get_workspace_roots))

    # ── D3: a top-level folder may not wear a home's display name ────────────
    ok &= _check("D3 'Documents' is refused at the top level",
                 bool(reserved_top_level_folder_reason("Documents")))
    ok &= _check("D3 the refusal is HONEST (names what holds it + a way forward)",
                 "already exists" in (reserved_top_level_folder_reason("Documents") or ""))
    ok &= _check("D3 the check is case/format-insensitive",
                 bool(reserved_top_level_folder_reason("downloads"))
                 and bool(reserved_top_level_folder_reason("DOCUMENTS")))
    ok &= _check("D3 the KERNEL root name is reserved too (silent merge)",
                 bool(reserved_top_level_folder_reason("operation"))
                 and bool(reserved_top_level_folder_reason("inbound")))
    ok &= _check("D3 an ordinary meaning-folder is NOT refused",
                 reserved_top_level_folder_reason("the-acme-deal") is None
                 and reserved_top_level_folder_reason("q3-planning") is None)
    # Derived from WORKSPACE_ROOTS, never hand-listed — a new home is reserved
    # automatically the day it is added.
    ok &= _check("D3 every WORKSPACE_ROOTS display name is reserved",
                 all(reserved_top_level_folder_reason(m["display_name"])
                     for m in WORKSPACE_ROOTS.values()))

    # D3 is wired into the create door, scoped to depth 1.
    from routes.documents import create_folder
    # Strip comments + the docstring before any text test: the prose above the
    # code NAMES the check it describes, so a naive substring test would match
    # its own comment and pass against a route that no longer calls it. (This
    # bit once — the same trap as the ADR-424 README assertion.)
    cf_lines = [l for l in inspect.getsource(create_folder).splitlines()
                if not l.lstrip().startswith("#")]
    _parts = "\n".join(cf_lines).split('"""')
    cf_code = "".join(_parts[0:1] + _parts[2:])

    ok &= _check("D3 create_folder CALLS the reserved-name check (code, not prose)",
                 "reserved_top_level_folder_reason(" in cf_code)
    ok &= _check("D3 the check is scoped to TOP-LEVEL (nested Documents is fine)",
                 "len(segments) == 1" in cf_code)
    ok &= _check("D3 the refusal is a 409 the operator can read",
                 "status_code=409" in cf_code)

    return 0 if ok else 1


def test_adr588_folder_markers_and_home_aliases():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(run())
