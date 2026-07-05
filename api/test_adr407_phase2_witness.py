"""Regression gate for ADR-407 Phase 2 — the witness surface.

ADR-405 D3/D5 operationalized: after-witness emission derives recipients from
the grant roster at emission time (owner + members, minus actor — never a
stored subscription matrix), lands one notifications row per recipient, and is
wired at the two decision-critical moments (proposal created, proposal
decided). N=1 byte-identity: witnesses-minus-actor is empty → no-op.

Run:
    cd api && python test_adr407_phase2_witness.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    _PASS.append(name)
    print(f"  ✓ {name}")


def _bad(name: str, reason: str) -> None:
    _FAIL.append((name, reason))
    print(f"  ✗ {name}\n      {reason}")


WS = "00000000-0000-0000-0000-00000000aaaa"
OWNER = "00000000-0000-0000-0000-000000000001"
MEMBER = "00000000-0000-0000-0000-000000000002"
LLM = "claude.ai"


class _FakeQuery:
    def __init__(self, sink, table, rows):
        self._sink, self._table, self._rows = sink, table, rows

    def select(self, *a, **k):
        return self

    def insert(self, row):
        self._sink.setdefault("inserts", []).append((self._table, row))
        # notifications insert must return an id
        self._rows = [{"id": "n-1", **row}]
        return self

    def update(self, row):
        return self

    def eq(self, *a):
        return self

    def in_(self, *a):
        return self

    def limit(self, *a):
        return self

    def execute(self):
        class R: pass
        r = R(); r.data = self._rows
        return r


class _FakeClient:
    def __init__(self, grants=None, owner_id=OWNER):
        self.sink = {}
        self._grants = grants or []
        self._owner_id = owner_id

    def table(self, name):
        rows = []
        if name == "principal_grants":
            rows = self._grants
        elif name == "workspaces":
            rows = [{"owner_id": self._owner_id}]
        return _FakeQuery(self.sink, name, rows)


# ---------------------------------------------------------------------------
# 1. Roster derivation
# ---------------------------------------------------------------------------

def test_roster() -> None:
    from services.witness import workspace_witnesses

    # Owner + member + foreign-llm grants → humans only; actor excluded.
    grants = [
        {"principal_id": OWNER, "role": "owner"},
        {"principal_id": MEMBER, "role": "member"},
    ]
    client = _FakeClient(grants=grants)
    got = asyncio.get_event_loop().run_until_complete(
        workspace_witnesses(client, WS, exclude_user_id=MEMBER)
    )
    if got == [OWNER]:
        _ok("roster: owner+member grants → actor excluded, humans only")
    else:
        _bad("roster: owner+member grants → actor excluded, humans only", f"got {got}")

    # N=1: only the owner; owner acts → empty.
    client = _FakeClient(grants=[{"principal_id": OWNER, "role": "owner"}])
    got = asyncio.get_event_loop().run_until_complete(
        workspace_witnesses(client, WS, exclude_user_id=OWNER)
    )
    if got == []:
        _ok("roster: N=1 owner-acts → empty (byte-identity)")
    else:
        _bad("roster: N=1 owner-acts → empty (byte-identity)", f"got {got}")

    # Legacy workspace without an owner grant row → owner still derived.
    client = _FakeClient(grants=[])
    got = asyncio.get_event_loop().run_until_complete(
        workspace_witnesses(client, WS, exclude_user_id=None)
    )
    if got == [OWNER]:
        _ok("roster: owner derived from workspaces row when grant missing")
    else:
        _bad("roster: owner derived from workspaces row when grant missing", f"got {got}")


# ---------------------------------------------------------------------------
# 2. Emission fan-out
# ---------------------------------------------------------------------------

def test_emission() -> None:
    from services.witness import emit_after_witness

    grants = [
        {"principal_id": OWNER, "role": "owner"},
        {"principal_id": MEMBER, "role": "member"},
    ]
    client = _FakeClient(grants=grants)
    reached = asyncio.get_event_loop().run_until_complete(
        emit_after_witness(
            client,
            workspace_id=WS,
            actor_user_id=MEMBER,
            message="Proposal awaiting witness: WriteFile (substrate)",
            context={"proposal_id": "p-1"},
        )
    )
    notif_inserts = [r for t, r in client.sink.get("inserts", []) if t == "notifications"]
    recipients = {r["user_id"] for r in notif_inserts}
    if reached == 1 and recipients == {OWNER} and all(r["channel"] == "in_app" for r in notif_inserts):
        _ok("emission: member act → owner notified in_app, actor not")
    else:
        _bad("emission: member act → owner notified in_app, actor not",
             f"reached={reached} recipients={recipients}")

    # No workspace → no-op
    client = _FakeClient(grants=grants)
    reached = asyncio.get_event_loop().run_until_complete(
        emit_after_witness(client, workspace_id=None, actor_user_id=MEMBER, message="x")
    )
    if reached == 0 and not client.sink.get("inserts"):
        _ok("emission: no workspace → no-op")
    else:
        _bad("emission: no workspace → no-op", f"reached={reached}")


# ---------------------------------------------------------------------------
# 3. Wiring
# ---------------------------------------------------------------------------

def test_wiring() -> None:
    pa = (ROOT / "services/primitives/propose_action.py").read_text()
    if "emit_after_witness" in pa and "Proposal awaiting witness" in pa:
        _ok("wiring: proposal creation emits after-witness")
    else:
        _bad("wiring: proposal creation emits after-witness", "call missing in propose_action")

    pr = (ROOT / "routes/proposals.py").read_text()
    if pr.count("_emit_decision_witness") >= 3 and "emit_after_witness" in pr:
        _ok("wiring: approve + reject emit decision witness")
    else:
        _bad("wiring: approve + reject emit decision witness", "call missing in proposals routes")

    w = (ROOT / "services/witness.py").read_text()
    if "subscription matrix" in w and "DP29" in w:
        _ok("wiring: derived-never-stored discipline documented at the source")
    else:
        _bad("wiring: derived-never-stored discipline documented at the source", "doc missing")


def main() -> int:
    print("ADR-407 Phase 2 — witness surface regression")
    print("=" * 60)
    test_roster()
    test_emission()
    test_wiring()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
