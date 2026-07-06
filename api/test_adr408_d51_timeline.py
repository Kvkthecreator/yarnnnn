"""Regression gate for ADR-408 D5.1 — the workspace timeline.

GET /api/workspace/timeline: derived at read time from the three attributed
ledgers (revisions, invocations, proposals), workspace-scoped, actor-carrying,
no dollar fields (ADR-396 display discipline). Never stored (DP29).

Run:
    cd api && python test_adr408_d51_timeline.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT.parent / "web"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name):
    _PASS.append(name); print(f"  ✓ {name}")


def _bad(name, reason):
    _FAIL.append((name, reason)); print(f"  ✗ {name}\n      {reason}")


WS = "00000000-0000-0000-0000-00000000aaaa"
USER = "00000000-0000-0000-0000-000000000001"


class _FakeQuery:
    def __init__(self, sink, table, rows):
        self._sink, self._table, self._rows = sink, table, rows
    def select(self, cols):
        self._sink.setdefault("selects", []).append((self._table, cols)); return self
    def eq(self, col, val):
        self._sink.setdefault("filters", []).append((self._table, col, val)); return self
    def lt(self, *a): return self
    def order(self, *a, **k): return self
    def limit(self, *a): return self
    def execute(self):
        class R: pass
        r = R(); r.data = self._rows
        return r


class _FakeClient:
    def __init__(self, tables):
        self.sink = {}; self._tables = tables
    def table(self, name):
        return _FakeQuery(self.sink, name, self._tables.get(name, []))


class _FakeAuth:
    def __init__(self, client):
        self.client = client; self.user_id = USER; self.workspace_id = WS


def test_endpoint() -> None:
    from routes.workspace import get_workspace_timeline
    from services import workspace_context as wc

    tables = {
        "workspace_file_versions": [
            {"path": "/workspace/operation/notes.md", "authored_by": "operator",
             "message": "edit", "created_at": "2026-07-06T03:00:00Z"},
        ],
        "execution_events": [
            {"slug": "addressed", "mode": "judgment", "status": "success",
             "trigger_type": "addressed", "principal_id": USER,
             "created_at": "2026-07-06T02:00:00Z"},
        ],
        "action_proposals": [
            {"id": "p-1", "primitive": "WriteFile", "family": "substrate",
             "status": "approved", "source": "freddie:ai",
             "approved_by": "human:member-2", "created_at": "2026-07-06T01:00:00Z",
             "approved_at": "2026-07-06T04:00:00Z"},
        ],
    }
    client = _FakeClient(tables)
    token = wc.set_request_workspace(WS)
    try:
        out = asyncio.get_event_loop().run_until_complete(
            get_workspace_timeline(_FakeAuth(client), limit=40)
        )
    finally:
        wc.reset_request_workspace(token)

    # Workspace scoping on all three ledgers
    f = client.sink.get("filters", [])
    scoped = all(
        (t, "workspace_id", WS) in f
        for t in ("workspace_file_versions", "execution_events", "action_proposals")
    )
    _ok("timeline: all three ledgers workspace-scoped") if scoped else _bad(
        "timeline: all three ledgers workspace-scoped", f"filters={f}")

    kinds = [e.kind for e in out.entries]
    if kinds == ["proposal", "revision", "invocation"]:
        _ok("timeline: merged + sorted desc (proposal decided-at wins)")
    else:
        _bad("timeline: merged + sorted desc (proposal decided-at wins)", str(kinds))

    prop = out.entries[0]
    if prop.decided_by == "human:member-2" and prop.actor == "freddie:ai":
        _ok("timeline: proposal carries proposer + witness")
    else:
        _bad("timeline: proposal carries proposer + witness", f"{prop}")

    # No dollar fields anywhere (display discipline)
    selects = dict(
        (t, cols) for t, cols in client.sink.get("selects", [])
    )
    if "cost" not in (selects.get("execution_events") or ""):
        _ok("timeline: no cost fields selected (dollars stay internal)")
    else:
        _bad("timeline: no cost fields selected (dollars stay internal)",
             selects.get("execution_events"))


def test_fe_mounted() -> None:
    comp = WEB / "components/library/kernel-home/WorkspaceTimeline.tsx"
    front = WEB / "components/library/kernel-home/HomeFrontPage.tsx"
    if comp.exists():
        _ok("fe: WorkspaceTimeline component exists")
        text = comp.read_text()
        if "attribution" in text or "formatAuthor" in text:
            _ok("fe: timeline uses the shared attribution module")
        else:
            _bad("fe: timeline uses the shared attribution module", "no attribution import")
    else:
        _bad("fe: WorkspaceTimeline component exists", "missing")
    if front.exists() and "WorkspaceTimeline" in front.read_text():
        _ok("fe: mounted on HomeFrontPage")
    else:
        _bad("fe: mounted on HomeFrontPage", "not mounted")


def main() -> int:
    print("ADR-408 D5.1 — workspace timeline regression")
    print("=" * 60)
    test_endpoint()
    test_fe_mounted()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
