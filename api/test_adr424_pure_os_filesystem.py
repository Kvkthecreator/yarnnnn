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

    return 0 if ok else 1


def test_adr424_pure_os_filesystem():
    assert run() == 0


if __name__ == "__main__":
    sys.exit(run())
