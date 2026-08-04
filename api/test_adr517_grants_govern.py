"""ADR-517 regression gate — grants govern, share executes.

Run: python3 test_adr517_grants_govern.py  (from api/)

The authority logic is EXECUTED (fake service client), not grepped — a green
grep is not a run gate. Structural checks cover the wiring (routes, MCP verb,
migration shape, deletions).

Asserts:
  A. assert_may_mint_share (executed): owner passes · viewer refused ·
     write-deny-all member refused · owner-only dial refuses a member ·
     ordinary member passes.
  B. _canonical_artifact_path (executed): one absolute spelling at the write.
  C. revoke_share authority (executed): minter revokes own · stranger-member
     refused · owner revokes any.
  D. class_default_write_regions('viewer') == [] (executed).
  E. accept_share viewer branch mints role='viewer' (ADR-437 D4.3 amended).
  F. Migration 234 shape: role CHECK carries viewer · all four write policies
     exclude viewer · dial column + CHECK · backfill guarded by birthmark AND
     axes · no inner BEGIN/COMMIT (runner owns the transaction).
  G. Both origins call the gate (cockpit route + MCP verb); MCP gains the
     reach check.
  H. POST /api/share is deleted (ADR-515 D8 executed).
  I. HUMAN_SEAT_ROLES stays (owner, member) — a viewer is not a seat.
"""

import inspect
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


class _FakeQuery:
    def __init__(self, data):
        self._data = data

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return type("R", (), {"data": self._data})()


class _FakeSvc:
    """Routes table() calls to canned rows."""

    def __init__(self, workspaces_rows, grants_rows):
        self._ws = workspaces_rows
        self._grants = grants_rows

    def table(self, name):
        if name == "workspaces":
            return _FakeQuery(self._ws)
        if name == "principal_grants":
            return _FakeQuery(self._grants)
        raise AssertionError(f"unexpected table {name}")


def main():
    results = []
    from services import workspace_shares as ws

    # ── A. the mint-authority gate, executed ─────────────────────────────────
    def run_gate(*, owner_id, caller, ws_rows, grant_rows):
        orig_svc, orig_owner = ws._svc, ws._workspace_owner_id
        ws._svc = lambda: _FakeSvc(ws_rows, grant_rows)
        ws._workspace_owner_id = lambda _wsid: owner_id
        try:
            ws.assert_may_mint_share(caller, "ws-1")
            return None
        except ws.ShareError as e:
            return e.code
        finally:
            ws._svc, ws._workspace_owner_id = orig_svc, orig_owner

    dial_default = [{"share_mint_policy": "write-holders"}]
    results.append(_check(
        "A1 owner always mints",
        run_gate(owner_id="alice", caller="alice", ws_rows=dial_default, grant_rows=[]) is None))
    results.append(_check(
        "A2 viewer-role grant refused (the §6.1 escalation door closes)",
        run_gate(owner_id="alice", caller="bob", ws_rows=dial_default,
                 grant_rows=[{"role": "viewer", "write_scopes": []}]) == "mint_forbidden"))
    results.append(_check(
        "A3 write-deny-all member refused (narrowed-to-nothing is a viewer in fact)",
        run_gate(owner_id="alice", caller="bob", ws_rows=dial_default,
                 grant_rows=[{"role": "member", "write_scopes": []}]) == "mint_forbidden"))
    results.append(_check(
        "A4 owner-only dial refuses a write-holding member",
        run_gate(owner_id="alice", caller="bob",
                 ws_rows=[{"share_mint_policy": "owner-only"}],
                 grant_rows=[{"role": "member", "write_scopes": None}]) == "mint_forbidden"))
    results.append(_check(
        "A5 ordinary member (class-default write) mints",
        run_gate(owner_id="alice", caller="bob", ws_rows=dial_default,
                 grant_rows=[{"role": "member", "write_scopes": None}]) is None))
    results.append(_check(
        "A6 grant-less caller refused",
        run_gate(owner_id="alice", caller="mallory", ws_rows=dial_default,
                 grant_rows=[]) == "mint_forbidden"))

    # ── B. one spelling at the write, executed ───────────────────────────────
    cap = ws._canonical_artifact_path
    results.append(_check(
        "B canonical spelling: relative→absolute, absolute unchanged, None passes",
        cap(None) is None
        and cap("operation/deck.html") == "/workspace/operation/deck.html"
        and cap("/operation/deck.html") == "/workspace/operation/deck.html"
        and cap("/workspace/operation/deck.html") == "/workspace/operation/deck.html"))

    # ── C. revoke authority, executed ────────────────────────────────────────
    def run_revoke(*, owner_id, caller, shared_by):
        orig_svc, orig_owner = ws._svc, ws._workspace_owner_id

        class _RevokeSvc(_FakeSvc):
            def table(self, name):
                if name == "workspace_shares":
                    q = _FakeQuery([{"id": "s-1", "shared_by": shared_by}])
                    q.update = lambda *_a, **_k: q
                    return q
                return super().table(name)

        ws._svc = lambda: _RevokeSvc([], [])
        ws._workspace_owner_id = lambda _wsid: owner_id
        try:
            return ws.revoke_share("ws-1", "s-1", revoked_by=caller)
        except ws.ShareError as e:
            return e.code
        finally:
            ws._svc, ws._workspace_owner_id = orig_svc, orig_owner

    results.append(_check(
        "C1 minter revokes their own link", run_revoke(owner_id="alice", caller="bob", shared_by="bob") is True))
    results.append(_check(
        "C2 a stranger member may NOT revoke someone else's link",
        run_revoke(owner_id="alice", caller="carol", shared_by="bob") == "revoke_forbidden"))
    results.append(_check(
        "C3 the owner revokes any link", run_revoke(owner_id="alice", caller="alice", shared_by="bob") is True))

    # ── D. viewer class default is deny-all, executed ────────────────────────
    from services.principals import class_default_write_regions
    results.append(_check(
        "D class_default_write_regions('viewer') == []",
        class_default_write_regions("viewer") == []))

    # ── E. the honest role on accept ─────────────────────────────────────────
    src_accept = inspect.getsource(ws.accept_share)
    results.append(_check(
        "E viewer branch mints role='viewer' (ADR-437 D4.3 amended by D1)",
        'role="viewer"' in src_accept and "granted_by=f\"share-view:" in src_accept))

    # ── F. migration 234 shape ───────────────────────────────────────────────
    with open("../supabase/migrations/234_adr517_role_honest_viewer_and_mint_authority.sql",
              encoding="utf-8") as f:
        mig = f.read()
    results.append(_check(
        "F1 role CHECK carries viewer",
        "'owner','member','viewer','own-agent','foreign-llm','platform','a2a'" in mig))
    results.append(_check(
        "F2 all four write policies exclude the viewer role",
        mig.count("role <> 'viewer'") == 4))
    results.append(_check(
        "F3 the dial column + its CHECK",
        "share_mint_policy" in mig and "('write-holders','owner-only')" in mig))
    results.append(_check(
        "F4 backfill guarded by birthmark AND axes (a widened grant is left alone)",
        "granted_by LIKE 'share-view:%'" in mig and "write_scopes = '{}'" in mig))
    results.append(_check(
        "F5 no inner BEGIN/COMMIT (the runner owns the transaction — 545f88b lesson)",
        "\nBEGIN;" not in mig and "\nCOMMIT;" not in mig))
    results.append(_check(
        "F6 artifact_path canonicalization backfill",
        "NOT LIKE '/workspace/%'" in mig))

    # ── G. both origins call the gate ────────────────────────────────────────
    with open("routes/shares.py", encoding="utf-8") as f:
        route_src = f.read()
    results.append(_check(
        "G1 cockpit route calls assert_may_mint_share before create_share",
        route_src.index("assert_may_mint_share(auth.user_id, workspace_id)")
        < route_src.index("share = create_share(")))
    results.append(_check(
        "G2 mint_forbidden maps to 403", 'e.code == "mint_forbidden"' in route_src))
    with open("mcp_server/server.py", encoding="utf-8") as f:
        server_src = f.read()
    results.append(_check(
        "G3 MCP verb: reach check + the same gate (species-blind parity)",
        "principal_reaches_workspace(auth.user_id, workspace_id)" in server_src
        and "assert_may_mint_share(auth.user_id, workspace_id)" in server_src))

    # ── H. the dead endpoint is dead ─────────────────────────────────────────
    with open("routes/documents.py", encoding="utf-8") as f:
        docs_src = f.read()
    results.append(_check(
        "H POST /api/share deleted (ADR-515 D8 executed by ADR-517 D7)",
        '@router.post("/share")' not in docs_src and "share_file_global" not in docs_src))

    # ── I. a viewer is not a seat ────────────────────────────────────────────
    from services.billing_tiers import HUMAN_SEAT_ROLES
    results.append(_check(
        "I HUMAN_SEAT_ROLES stays (owner, member) — viewer reach never bills",
        set(HUMAN_SEAT_ROLES) == {"owner", "member"}))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
