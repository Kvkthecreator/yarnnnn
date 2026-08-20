"""
ADR-424 — the pure-OS filesystem model for all participants.

The anti-drift ratchet: ONE home-model (PARTICIPANT_FILESYSTEM_MODEL) is the
singular source of the filesystem's mental model for LLM participants; no
participant envelope re-authors a kernel-root enumeration (the pre-ADR-424
state had four disagreeing inline lists). Plus D2 (peers ratified, "never
invent" removed) and D3 (conventions.py home param, byte-identical default).

Pure-Python source-guard (no DB, no `mcp` package).
"""

import inspect
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    ok = True

    # ── D1: the singular home-model constant exists + is pure-OS ──────────────
    from services.workspace_paths import PARTICIPANT_FILESYSTEM_MODEL as M
    ok &= _check("D1 home-model constant exists + non-trivial", len(M) > 200)
    ok &= _check("D1 is pure-OS (home directory, write by meaning, grant)",
                 "home directory" in M and "meaning" in M and "grant" in M)
    ok &= _check("D1 names Documents + Downloads (the two system homes)",
                 "Documents" in M and "Downloads" in M)
    # It must NOT re-enumerate the kernel roots (that's the whole point).
    ok &= _check("D1 does NOT enumerate kernel roots",
                 "governance/" not in M and "constitution/" not in M
                 and "persona/" not in M)

    # ── D4: the four envelopes carry the model, not their own root lists ──────
    # lane_runner hands frame
    from services.lane_runner import _CONVENTIONS_FRAME, build_lane_conventions
    ok &= _check("D4 lane frame injects the D1 model (not its own list)",
                 "{filesystem_model}" in _CONVENTIONS_FRAME)
    lane_src = inspect.getsource(build_lane_conventions)
    ok &= _check("D4 lane frame imports PARTICIPANT_FILESYSTEM_MODEL",
                 "PARTICIPANT_FILESYSTEM_MODEL" in lane_src)
    # The old divergent list markers are gone from the lane frame.
    ok &= _check("D4 lane frame dropped its divergent root list",
                 "memory/ — accumulated" not in _CONVENTIONS_FRAME
                 and "The working regions" not in _CONVENTIONS_FRAME)

    # freddie_agent frame
    from agents.freddie_agent import _compute_minimal_frame
    frame = _compute_minimal_frame()
    ok &= _check("D4 freddie frame reframed to write-by-meaning",
                 "write into the workspace by meaning" in frame)
    ok &= _check("D4 freddie frame dropped the five-root recital",
                 "EXCEPT two roots" not in frame and "governance/" not in frame)

    # WriteFile tool description (the most-reused)
    from services.primitives.workspace import WRITE_FILE_TOOL
    wf = WRITE_FILE_TOOL["description"]
    ok &= _check("D4 WriteFile desc reframed to write-by-meaning",
                 "by MEANING" in wf or "by meaning" in wf)
    ok &= _check("D4 WriteFile desc dropped 'the five roots'",
                 "five roots" not in wf and "five-root" not in wf)
    # The param descriptions too.
    scope_desc = WRITE_FILE_TOOL["input_schema"]["properties"]["scope"]["description"]
    ok &= _check("D4 WriteFile scope param dropped 'five-root'",
                 "five-root" not in scope_desc and "five roots" not in scope_desc)

    # dispatch_specialist frame — the "never invent paths" absolute is softened
    from services.primitives.dispatch_specialist import _SPECIALIST_FRAME
    ok &= _check("D4 specialist frame no longer says 'never invent paths'",
                 "never invent paths" not in _SPECIALIST_FRAME)

    # ── D2: the 'never invent directories' rule is removed (it forbade peers) ──
    ok &= _check("D2 lane frame removed 'Never invent new top-level directories'",
                 "Never invent new top-level" not in _CONVENTIONS_FRAME)

    # ── D3: conventions.py home param — byte-identical default, peer re-root ──
    from services import conventions as c
    ok &= _check("D3 DEFAULT_WORK_HOME is 'operation'", c.DEFAULT_WORK_HOME == "operation")
    # byte-identical for every current caller (no home arg).
    defaults_ok = (
        c.report_root("x") == "/workspace/operation/reports/x"
        and c.report_feedback_path("x") == "/workspace/operation/reports/x/_feedback.md"
        and c.authored_root("x") == "/workspace/operation/authored/x"
        and c.domain_root("acme") == "/workspace/operation/acme"
        and c.operation_root("op") == "/workspace/operation/operations/op"
        and c.spec_path("s") == "/workspace/operation/specs/s.md"
    )
    ok &= _check("D3 default home is byte-identical (operation/)", defaults_ok)
    # a peer home re-roots.
    peer_ok = (
        c.report_root("x", home="the-acme-deal") == "/workspace/the-acme-deal/reports/x"
        and c.domain_root("acme", home="the-acme-deal") == "/workspace/the-acme-deal/acme"
    )
    ok &= _check("D3 peer home re-roots correctly", peer_ok)

    # ── D2 create-folder route: the operator makes a peer folder ──────────────
    from routes.documents import _sanitize_folder_segment, create_folder
    ok &= _check("create-folder sanitizer strips traversal + specials",
                 _sanitize_folder_segment("The Acme Deal!") == "the-acme-deal"
                 and _sanitize_folder_segment("../etc") == "etc")
    cf_src = inspect.getsource(create_folder)
    # The route must guard on operator_can_organize (so system/ + inbound/ refuse)
    # and write through the ADR-209 write path, not a raw insert.
    ok &= _check("create-folder guards on operator_can_organize",
                 "operator_can_organize" in cf_src)
    # ── ADR-588 D1: the README SEED IS DELETED, replaced by a folder marker ──
    # This assertion previously pinned the seed ("WriteFile" in cf_src and
    # "README.md" in cf_src), encoding the workaround as canon. The seed wrote a
    # document attributed to "operator" that the operator never authored — a
    # false signature in the attribution ledger. It is re-anchored here, not
    # routed around.
    # NOTE ON THIS GATE'S SHAPE: the assertions below pin MECHANISM (what the
    # route calls, what it returns), never a SPELLING. The prose above the code
    # names "README" and "seeded" precisely because it explains the deletion —
    # a naive `"README" not in cf_src` would go red against correct code by
    # matching its own comment. Strip comments/docstrings before any text test.
    cf_code = "\n".join(
        line for line in cf_src.splitlines()
        if not line.lstrip().startswith("#")
    )
    _body = cf_code.split('"""')
    cf_code = "".join(_body[0:1] + _body[2:])  # drop the docstring

    ok &= _check("create-folder does NOT seed a README document (ADR-588 D1)",
                 "README" not in cf_code)
    ok &= _check("create-folder writes a folder MARKER via write_revision",
                 "write_revision" in cf_code
                 and "FOLDER_MARKER_CONTENT_TYPE" in cf_code
                 and "folder_marker_path" in cf_code)
    ok &= _check("create-folder response carries no 'seeded' key",
                 "seeded" not in cf_code)
    # It must NOT route the marker through the WriteFile primitive — that
    # primitive's empty-content guard correctly refuses a 0-byte write.
    ok &= _check("create-folder does not call the WriteFile primitive",
                 "WriteFile" not in cf_code)

    # ── folder-node New Folder (2026-08-04): parent is ADDRESSING, not naming ──
    # The parent names an EXISTING folder, so it must NOT pass through the
    # segment sanitizer (which lowercases + rewrites `_` → `-`): sanitizing an
    # existing segment silently reroutes the new folder. Only the new leaf is
    # sanitized. The parent IS validated (no traversal), and the composed path
    # still hits the operator_can_organize guard downstream.
    from routes.documents import CreateFolderRequest
    ok &= _check("create-folder accepts an optional parent field",
                 "parent" in CreateFolderRequest.model_fields
                 and CreateFolderRequest.model_fields["parent"].default is None)
    parent_block = cf_src[cf_src.index("if body.parent"):] if "if body.parent" in cf_src else ""
    ok &= _check("parent segments are NOT re-sanitized (verbatim addressing)",
                 bool(parent_block)
                 and "_sanitize_folder_segment" not in parent_block.split("readme_path")[0])
    ok &= _check("parent rejects traversal segments",
                 '".."' in parent_block)
    # The sanitizer really is lossy on existing names — the reason verbatim
    # matters. If this ever stops holding, the verbatim lane can be dropped.
    ok &= _check("sanitizer is lossy on underscore-prefixed existing names",
                 _sanitize_folder_segment("_adr427-probe") != "_adr427-probe")

    return 0 if ok else 1


def test_adr424_pure_os_filesystem():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(run())
