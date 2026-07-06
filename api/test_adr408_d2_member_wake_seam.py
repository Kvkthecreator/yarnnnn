"""Regression gate for ADR-408 D2 — member-addressed wakes run FOR the commons.

The two-account walk found Freddie, addressed from a member's seat, resolving
the MEMBER's own singleton (empty ListFiles, wrong governance) instead of the
granted commons. The wake stack's contract is "user_id = Workspace owner
UUID"; the request-layer seams now resolve acting-workspace → owner via the
shared `acting_workspace_owner` helper: addressed chat (feed.py),
FireInvocation, and the MCP-write wake. The member stays the attributed
principal; the reply stays in the member's thread.

Run:
    cd api && python test_adr408_d2_member_wake_seam.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name):
    _PASS.append(name); print(f"  ✓ {name}")


def _bad(name, reason):
    _FAIL.append((name, reason)); print(f"  ✗ {name}\n      {reason}")


OWNER = "00000000-0000-0000-0000-000000000001"
MEMBER = "00000000-0000-0000-0000-000000000002"
COMMONS = "00000000-0000-0000-0000-00000000aaaa"


class _FakeQuery:
    def __init__(self, rows): self._rows = rows
    def select(self, *a): return self
    def eq(self, *a): return self
    def limit(self, *a): return self
    def execute(self):
        class R: pass
        r = R(); r.data = self._rows
        return r


class _FakeClient:
    def __init__(self, owner_id=OWNER):
        self._owner_id = owner_id
    def table(self, name):
        return _FakeQuery([{"owner_id": self._owner_id}])


def test_helper() -> None:
    from services import workspace_context as wc

    # Member acting in the commons (contextvar set) → resolves the OWNER.
    token = wc.set_request_workspace(COMMONS)
    try:
        got = wc.acting_workspace_owner(_FakeClient(), MEMBER)
    finally:
        wc.reset_request_workspace(token)
    if got == OWNER:
        _ok("helper: member-in-commons → workspace owner")
    else:
        _bad("helper: member-in-commons → workspace owner", got)

    # No workspace resolvable → the caller themselves (their own lane).
    orig = wc.effective_workspace_id
    wc.effective_workspace_id = lambda *a, **k: None  # type: ignore
    try:
        got = wc.acting_workspace_owner(_FakeClient(), MEMBER)
    finally:
        wc.effective_workspace_id = orig  # type: ignore
    if got == MEMBER:
        _ok("helper: unresolvable → caller fallback")
    else:
        _bad("helper: unresolvable → caller fallback", got)

    # DB failure → caller fallback, never raises.
    class _Boom:
        def table(self, name): raise RuntimeError("db down")
    token = wc.set_request_workspace(COMMONS)
    try:
        got = wc.acting_workspace_owner(_Boom(), MEMBER)
    finally:
        wc.reset_request_workspace(token)
    if got == MEMBER:
        _ok("helper: DB failure → caller fallback (never raises)")
    else:
        _bad("helper: DB failure → caller fallback (never raises)", got)


def test_seams_wired() -> None:
    feed = (ROOT / "routes/feed.py").read_text()
    if "acting_workspace_owner(wake_client, auth.user_id)" in feed \
            and "wake_client, wake_user_id," in feed:
        _ok("seam: addressed chat enters the wake as the workspace owner")
    else:
        _bad("seam: addressed chat enters the wake as the workspace owner", "not wired")
    # Attribution + thread stay the member's
    if '"p_workspace_id": acting_ws' in feed and "addressed_principal = resolve_principal_id(auth)" in feed:
        _ok("seam: member stays the attributed principal + keeps their thread")
    else:
        _bad("seam: member stays the attributed principal + keeps their thread", "changed")

    fire = (ROOT / "services/primitives/fire_invocation.py").read_text()
    if "acting_workspace_owner(db_client, user_id)" in fire:
        _ok("seam: FireInvocation fires the commons' recurrence")
    else:
        _bad("seam: FireInvocation fires the commons' recurrence", "not wired")

    mcp = (ROOT / "services/mcp_composition.py").read_text()
    if "acting_workspace_owner(auth.client, auth.user_id)" in mcp \
            and 'select("owner_id")' not in mcp:
        _ok("seam: MCP wake uses the shared helper (inline lookup deleted)")
    else:
        _bad("seam: MCP wake uses the shared helper (inline lookup deleted)", "not refactored")


def main() -> int:
    print("ADR-408 D2 — member wake seam regression")
    print("=" * 60)
    test_helper()
    test_seams_wired()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
