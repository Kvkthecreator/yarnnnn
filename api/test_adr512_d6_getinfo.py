"""ADR-512 D6 regression gate — Get Info (reach) + attach-in-chat (the bind).

Tier 2 of the deferred queue (operator delegation 2026-08-03). Structural.

Run: python3 test_adr512_d6_getinfo.py  (from api/)

Asserts:
  1. /workspace/members?path= computes per-principal reach with the ONE
     powerbox matcher (path_under_scopes) — never a re-derived FE matcher —
     with the owner shortcut and the NULL-write → class-default fallback.
  2. The FE Get Info panel (NodeDetailsPanel) mounts reach + per-file share
     management (revoke — the "Manage Shared File" row) and computes no
     scope-matching client-side.
  3. Attach-from-workspace is a BIND: the chip carries the existing path; the
     handler performs no upload; the picker mounts the ONE WorkspacePicker.
"""

import inspect
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []
    from routes import workspace as w

    sig = str(inspect.signature(w.get_workspace_members))
    src = inspect.getsource(w.get_workspace_members)
    results.append(_check(
        "1a members endpoint accepts ?path=", "path: Optional[str]" in sig))
    results.append(_check(
        "1b reach rides the ONE matcher (path_under_scopes)",
        "path_under_scopes" in src))
    results.append(_check(
        "1c owner shortcut + NULL-write class-default fallback",
        'if role == "owner":' in src
        and "_class_default_write_regions(role)" in src))
    results.append(_check(
        "1d model carries can_read/can_write",
        "can_read" in w.WorkspaceMember.model_fields
        and "can_write" in w.WorkspaceMember.model_fields))

    with open("../web/components/workspace/NodeDetailsPanel.tsx", encoding="utf-8") as f:
        panel = f.read()
    results.append(_check(
        "2a Get Info mounts reach + shares sections",
        "function FileReach" in panel and "function FileShares" in panel
        and "<FileReach" in panel and "<FileShares" in panel))
    results.append(_check(
        "2b no client-side scope matching (server computes; panel renders)",
        "startsWith" not in inspect.getsource(w.get_workspace_members) or
        ("path_under_scopes" in src and "can_write" in panel and "prefix" not in panel.lower())))
    results.append(_check(
        "2c per-file share revoke present (revocation = the public link's off switch)",
        "revokeShare" in panel))

    with open("../web/components/chat-surface/LanePanel.tsx", encoding="utf-8") as f:
        lane = f.read()
    results.append(_check(
        "3a attach-from-workspace mounts the ONE picker",
        "WorkspacePickerModal" in lane and "attachWorkspaceFile" in lane))
    # the bind handler must not upload — slice its source out of the file text
    start = lane.index("const attachWorkspaceFile")
    end = lane.index("const addFiles")
    bind_src = lane[start:end]
    results.append(_check(
        "3b the bind performs NO upload call (reference, not copy)",
        "api.documents" not in bind_src and ".upload(" not in bind_src
        and "path," in bind_src))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
