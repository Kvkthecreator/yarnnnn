"""ADR-465 D3 regression gate — share-as-view (the second share shape).

Ratified 2026-08-02 (ADR-512 §7); this pass is Phase D. Pure-Python structural
checks (no DB): the service-layer branch logic, the birth-narrowing contract,
and the don't-downgrade guarantee.

Run: python3 test_adr465_share_as_view.py  (from api/)

Asserts:
  1. create_share validates the role enum (member|viewer) and writes it.
  2. accept_share's viewer branch mints a BIRTH-NARROWED member grant
     (write_scopes=[] deny-all; read_scopes=[artifact] or None for bare) —
     the grant row role stays 'member' (one grant model, ADR-437 D4.3).
  3. ensure_principal_grant applies the axes on the INSERT branch only — an
     existing active grant is returned untouched (don't-downgrade).
  4. Migration 231 widens the role CHECK to (member, viewer).
  5. The route passes the role through; the client sends it.
"""

import inspect
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []
    from services import workspace_shares as ws
    from services import principal_grants as pg

    # 1. create_share role validation + write
    src_create = inspect.getsource(ws.create_share)
    results.append(_check(
        "1a create_share validates role enum",
        '("member", "viewer")' in src_create and "invalid_role" in src_create))
    results.append(_check(
        "1b create_share writes the chosen role (no hardcoded 'member' row)",
        '"role": role,' in src_create and '"role": "member",' not in src_create))

    # 2. the viewer branch birth-narrows
    src_accept = inspect.getsource(ws.accept_share)
    results.append(_check(
        "2a viewer branch exists and deny-alls writes",
        'share_role == "viewer"' in src_accept and "write_scopes=[]" in src_accept))
    results.append(_check(
        "2b read axis scopes to the artifact (None for a bare share)",
        "read_scopes=[artifact] if artifact else None" in src_accept))
    results.append(_check(
        "2c one grant model — the grant row role stays 'member' in BOTH branches",
        src_accept.count('role="member"') == 2 and 'role="viewer"' not in src_accept))
    results.append(_check(
        "2d the response reports the SHARE's shape (honest accept copy)",
        '"role": share_role,' in src_accept))

    # 3. ensure_principal_grant: axes on INSERT only (don't-downgrade)
    src_ensure = inspect.getsource(pg.ensure_principal_grant)
    sig = inspect.signature(pg.ensure_principal_grant)
    results.append(_check(
        "3a ensure_principal_grant accepts write_scopes/read_scopes",
        "write_scopes" in sig.parameters and "read_scopes" in sig.parameters))
    existing_return = src_ensure.index("return existing.data[0]")
    axes_apply = src_ensure.index('row["write_scopes"]')
    results.append(_check(
        "3b existing-grant early return PRECEDES the axes (insert-only narrowing)",
        existing_return < axes_apply))
    results.append(_check(
        "3c legacy scopes mirror follows write_scopes (narrow_grant convention)",
        'row["scopes"] = write_scopes' in src_ensure))

    # 4. migration 231
    with open("../supabase/migrations/231_adr465_share_as_view.sql", encoding="utf-8") as f:
        mig = f.read()
    results.append(_check(
        "4 migration 231 widens the CHECK to (member, viewer)",
        "CHECK (role IN ('member', 'viewer'))" in mig
        and "DROP CONSTRAINT IF EXISTS workspace_shares_role_check" in mig))

    # 5. route + client pass-through
    with open("routes/shares.py", encoding="utf-8") as f:
        route_src = f.read()
    results.append(_check(
        "5a route model carries role and forwards it",
        'role: str = "member"' in route_src and "role=body.role," in route_src))
    with open("../web/lib/api/client.ts", encoding="utf-8") as f:
        client_src = f.read()
    results.append(_check(
        "5b client sends role on createShare",
        'role: "member" | "viewer" = "member"' in client_src
        and "ttl_days: ttlDays, role" in client_src))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
