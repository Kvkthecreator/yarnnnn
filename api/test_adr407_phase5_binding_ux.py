"""Regression gate for ADR-407 Phase 5 — the binding UX.

Backend: GET /api/workspace/memberships (the caller's workspaces — owner +
active member grants, is_active marks the request's resolved binding).
Frontend: workspace switcher in the user menu (renders only at N>1) +
ADR-406 CAS threading (editors pass expected_head_version_id; 409 surfaces
who changed the file instead of silent last-writer-wins).

Run:
    cd api && python test_adr407_phase5_binding_ux.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
WEB = REPO_ROOT / "web"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name):
    _PASS.append(name); print(f"  ✓ {name}")


def _bad(name, reason):
    _FAIL.append((name, reason)); print(f"  ✗ {name}\n      {reason}")


def test_backend_endpoint() -> None:
    text = (ROOT / "routes/workspace.py").read_text()
    checks = [
        ("memberships endpoint exists", '@router.get("/workspace/memberships"' in text),
        ("owner labeled + member grants queried",
         '"My workspace"' in text and '.in_("role", ["member"])' in text),
        ("is_active reflects the request binding", "is_active=(own_ws == acting)" in text),
        ("response model declared", "class WorkspaceMembershipsResponse" in text),
    ]
    for name, cond in checks:
        _ok(f"backend: {name}") if cond else _bad(f"backend: {name}", "pattern missing")


def test_fe_switcher() -> None:
    client = (WEB / "lib/api/client.ts").read_text()
    if "memberships" in client and "clearActiveWorkspace" in client:
        _ok("fe: client has memberships + clearActiveWorkspace")
    else:
        _bad("fe: client has memberships + clearActiveWorkspace", "missing")
    menu = (WEB / "components/shell/UserMenu.tsx").read_text()
    if "memberships" in menu and ("clearActiveWorkspace" in menu or "setActiveWorkspace" in menu):
        _ok("fe: UserMenu renders the switcher")
    else:
        _bad("fe: UserMenu renders the switcher", "not wired")


def test_fe_409_wiring() -> None:
    hits = []
    for p in WEB.rglob("*.tsx"):
        if ".next" in str(p) or "node_modules" in str(p):
            continue
        t = p.read_text()
        if (
            "expected_head_version_id" in t
            or "expectedHeadVersionId" in t
            or ("editFile(" in t and "headId" in t and "conditional write" in t)
        ):
            hits.append(str(p.relative_to(WEB)))
    if hits:
        _ok(f"fe: CAS threaded in editors ({len(hits)} component(s))")
    else:
        _bad("fe: CAS threaded in editors", "no component passes expected_head_version_id")

    conflict = []
    for p in WEB.rglob("*.tsx"):
        if ".next" in str(p) or "node_modules" in str(p):
            continue
        t = p.read_text()
        if "409" in t and ("stale" in t.lower() or "conflict" in t.lower()):
            conflict.append(str(p.relative_to(WEB)))
    if conflict:
        _ok(f"fe: 409 conflict surfaced ({len(conflict)} component(s))")
    else:
        _bad("fe: 409 conflict surfaced", "no 409 handling found")


def main() -> int:
    print("ADR-407 Phase 5 — binding UX regression")
    print("=" * 60)
    test_backend_endpoint()
    test_fe_switcher()
    test_fe_409_wiring()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
