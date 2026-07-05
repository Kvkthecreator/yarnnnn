"""Regression gate for ADR-407 Phase 0 — the money gate re-keys to the workspace.

Migration 200: execution_events.workspace_id + get_effective_balance(p_workspace_id).
Code: telemetry stamps workspace_id on every ledger row; platform_limits gates and
rolls up spend by the ACTING workspace (contextvar → owner resolution); a member
acting under a grant draws — and debits — the shared pool.

Run:
    cd api && python test_adr407_phase0_money_gate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
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


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeQuery:
    def __init__(self, sink: dict, table: str, rows=None):
        self._sink = sink
        self._table = table
        self._rows = rows if rows is not None else []
        self._filters: list[tuple] = []

    def select(self, *_a, **_k):
        return self

    def insert(self, row):
        self._sink.setdefault("inserts", []).append((self._table, row))
        return self

    def update(self, row):
        self._sink.setdefault("updates", []).append((self._table, row))
        return self

    def eq(self, col, val):
        self._filters.append(("eq", col, val))
        self._sink.setdefault("filters", []).append((self._table, "eq", col, val))
        return self

    def gt(self, col, val):
        self._filters.append(("gt", col, val))
        return self

    def gte(self, col, val):
        self._filters.append(("gte", col, val))
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        class R:
            pass
        r = R()
        r.data = self._rows
        return r


class _FakeClient:
    def __init__(self, table_rows: dict | None = None, rpc_result=None):
        self.sink: dict = {}
        self._table_rows = table_rows or {}
        self._rpc_result = rpc_result

    def table(self, name):
        return _FakeQuery(self.sink, name, self._table_rows.get(name, []))

    def rpc(self, fn, params):
        self.sink.setdefault("rpcs", []).append((fn, params))
        q = _FakeQuery(self.sink, f"rpc:{fn}", [])

        def _execute():
            class R:
                pass
            r = R()
            r.data = self._rpc_result
            return r

        q.execute = _execute  # type: ignore[method-assign]
        return q


WS = "00000000-0000-0000-0000-00000000aaaa"
GRANTED_WS = "00000000-0000-0000-0000-00000000bbbb"
USER = "00000000-0000-0000-0000-000000000001"


# ---------------------------------------------------------------------------
# 1. Migration 200 shape
# ---------------------------------------------------------------------------

def test_migration_shape() -> None:
    path = REPO_ROOT / "supabase/migrations/200_adr407_phase0_money_gate.sql"
    if not path.exists():
        _bad("migration 200 exists", str(path))
        return
    sql = path.read_text()
    checks = [
        ("adds workspace_id column", "ADD COLUMN IF NOT EXISTS workspace_id uuid REFERENCES workspaces(id)" in sql),
        ("backfills via owner mapping", "w.owner_id = ee.user_id" in sql and "SET workspace_id = w.id" in sql),
        ("drops the p_user_id RPC", "DROP FUNCTION IF EXISTS public.get_effective_balance(uuid)" in sql),
        ("recreates keyed p_workspace_id", "get_effective_balance(p_workspace_id uuid)" in sql),
        ("spend sums by workspace", "ee.workspace_id = w.id" in sql),
        ("workspace looked up by id", "WHERE w.id = p_workspace_id" in sql),
        ("anchor precedence unchanged", all(a in sql for a in ("allowance_granted_at", "subscription_refill_at", "w.created_at"))),
        ("rollup index present", "idx_execution_events_workspace_created" in sql),
        ("no owner_id resolution remains in RPC", "w.owner_id = p_user_id" not in sql),
    ]
    for name, cond in checks:
        _ok(f"migration: {name}") if cond else _bad(f"migration: {name}", "pattern missing")


# ---------------------------------------------------------------------------
# 2. telemetry.record_execution_event stamps workspace_id
# ---------------------------------------------------------------------------

def test_telemetry_stamps_workspace() -> None:
    from services import telemetry
    from services import workspace_context

    # (a) explicit kwarg wins
    client = _FakeClient()
    telemetry.record_execution_event(
        client, user_id=USER, slug="t", mode="mechanical",
        trigger_type="manual", status="success", workspace_id=WS,
    )
    inserts = client.sink.get("inserts", [])
    row = inserts[0][1] if inserts else {}
    if row.get("workspace_id") == WS:
        _ok("telemetry: explicit workspace_id stamped")
    else:
        _bad("telemetry: explicit workspace_id stamped", f"row={row}")

    # (b) request contextvar resolves (the member-under-grant path)
    client = _FakeClient()
    token = workspace_context.set_request_workspace(GRANTED_WS)
    try:
        telemetry.record_execution_event(
            client, user_id=USER, slug="t", mode="mechanical",
            trigger_type="manual", status="success",
        )
    finally:
        workspace_context.reset_request_workspace(token)
    row = client.sink.get("inserts", [[None, {}]])[0][1]
    if row.get("workspace_id") == GRANTED_WS:
        _ok("telemetry: contextvar workspace stamped (member path)")
    else:
        _bad("telemetry: contextvar workspace stamped (member path)", f"row={row}")

    # (c) resolution failure is fail-open — row still lands, unscoped
    client = _FakeClient()
    orig = workspace_context.effective_workspace_id
    workspace_context.effective_workspace_id = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore
    try:
        rid_err = None
        try:
            telemetry.record_execution_event(
                client, user_id=USER, slug="t", mode="mechanical",
                trigger_type="manual", status="success",
            )
        except Exception as e:  # pragma: no cover
            rid_err = e
    finally:
        workspace_context.effective_workspace_id = orig  # type: ignore
    inserts = client.sink.get("inserts", [])
    if rid_err is None and inserts and "workspace_id" not in inserts[0][1]:
        _ok("telemetry: scoping failure fail-open (row lands unscoped)")
    else:
        _bad("telemetry: scoping failure fail-open (row lands unscoped)",
             f"err={rid_err} inserts={inserts}")


# ---------------------------------------------------------------------------
# 3. platform_limits gate keys on the acting workspace
# ---------------------------------------------------------------------------

def test_gate_workspace_keyed() -> None:
    from services import platform_limits, workspace_context

    # (a) RPC called with p_workspace_id from the contextvar
    client = _FakeClient(rpc_result=12.5)
    token = workspace_context.set_request_workspace(GRANTED_WS)
    try:
        bal = platform_limits.get_effective_balance(client, USER)
    finally:
        workspace_context.reset_request_workspace(token)
    rpcs = client.sink.get("rpcs", [])
    if rpcs == [("get_effective_balance", {"p_workspace_id": GRANTED_WS})] and bal == 12.5:
        _ok("gate: RPC keyed p_workspace_id via contextvar (member draws shared pool)")
    else:
        _bad("gate: RPC keyed p_workspace_id via contextvar (member draws shared pool)",
             f"rpcs={rpcs} bal={bal}")

    # (b) no workspace resolvable → fail-safe 0.0, no RPC
    client = _FakeClient(rpc_result=99.0)
    orig = workspace_context.effective_workspace_id
    workspace_context.effective_workspace_id = lambda *a, **k: None  # type: ignore
    try:
        bal = platform_limits.get_effective_balance(client, USER)
    finally:
        workspace_context.effective_workspace_id = orig  # type: ignore
    if bal == 0.0 and not client.sink.get("rpcs"):
        _ok("gate: unresolvable workspace → fail-safe 0.0")
    else:
        _bad("gate: unresolvable workspace → fail-safe 0.0", f"bal={bal} rpcs={client.sink.get('rpcs')}")

    # (c) check_balance still the single hard-stop wrapper
    client = _FakeClient(rpc_result=0)
    token = workspace_context.set_request_workspace(WS)
    try:
        allowed, bal = platform_limits.check_balance(client, USER)
    finally:
        workspace_context.reset_request_workspace(token)
    if allowed is False and bal == 0.0:
        _ok("gate: hard-stop at zero preserved")
    else:
        _bad("gate: hard-stop at zero preserved", f"allowed={allowed} bal={bal}")

    # (d) grant_allowance passes the explicit workspace to the balance read
    client = _FakeClient(
        table_rows={"workspaces": [{"balance_usd": 5, "allowance_usd": 0, "allowance_period": None}]},
        rpc_result=5.0,
    )
    ok = platform_limits.grant_allowance(client, WS, USER, 15.0)
    rpcs = client.sink.get("rpcs", [])
    if ok and rpcs and rpcs[0][1] == {"p_workspace_id": WS}:
        _ok("gate: grant_allowance reads pool via explicit workspace")
    else:
        _bad("gate: grant_allowance reads pool via explicit workspace", f"ok={ok} rpcs={rpcs}")


# ---------------------------------------------------------------------------
# 4. Spend windows keyed by workspace
# ---------------------------------------------------------------------------

def test_spend_windows_workspace_keyed() -> None:
    from services import telemetry, platform_limits, workspace_context

    # get_daily_spend
    client = _FakeClient(table_rows={"execution_events": [{"cost_usd": 1.0}]})
    token = workspace_context.set_request_workspace(GRANTED_WS)
    try:
        spend = telemetry.get_daily_spend(client, USER)
    finally:
        workspace_context.reset_request_workspace(token)
    filters = client.sink.get("filters", [])
    if ("execution_events", "eq", "workspace_id", GRANTED_WS) in filters and spend == 1.0:
        _ok("spend: get_daily_spend keyed workspace_id")
    else:
        _bad("spend: get_daily_spend keyed workspace_id", f"filters={filters}")

    # get_lifetime_spend_usd
    client = _FakeClient(table_rows={
        "workspaces": [{"allowance_granted_at": None, "subscription_refill_at": None,
                        "created_at": "2026-01-01T00:00:00+00:00"}],
        "execution_events": [{"cost_usd": 2.5}],
    })
    token = workspace_context.set_request_workspace(GRANTED_WS)
    try:
        spend = platform_limits.get_lifetime_spend_usd(client, USER)
    finally:
        workspace_context.reset_request_workspace(token)
    filters = client.sink.get("filters", [])
    ws_by_id = ("workspaces", "eq", "id", GRANTED_WS) in filters
    ee_by_ws = ("execution_events", "eq", "workspace_id", GRANTED_WS) in filters
    no_owner_key = ("workspaces", "eq", "owner_id", USER) not in filters
    if ws_by_id and ee_by_ws and no_owner_key and spend == 2.5:
        _ok("spend: get_lifetime_spend_usd keyed workspace (no owner_id path)")
    else:
        _bad("spend: get_lifetime_spend_usd keyed workspace (no owner_id path)",
             f"filters={filters} spend={spend}")

    # billing tier follows the acting workspace
    from services import billing_tiers
    client = _FakeClient(table_rows={"workspaces": [{"subscription_tier": "pro"}]})
    token = workspace_context.set_request_workspace(GRANTED_WS)
    try:
        tier = billing_tiers.get_tier(client, USER)
    finally:
        workspace_context.reset_request_workspace(token)
    filters = client.sink.get("filters", [])
    if tier == "pro" and ("workspaces", "eq", "id", GRANTED_WS) in filters:
        _ok("tier: get_tier follows the acting workspace")
    else:
        _bad("tier: get_tier follows the acting workspace", f"tier={tier} filters={filters}")


# ---------------------------------------------------------------------------
# 5. No stray p_user_id call into the balance RPC remains
# ---------------------------------------------------------------------------

def test_no_stray_p_user_id_balance_calls() -> None:
    import re
    offenders = []
    for py in (ROOT / "services").rglob("*.py"):
        text = py.read_text()
        for m in re.finditer(r"get_effective_balance\"\s*,\s*\{\s*\"p_user_id\"", text):
            offenders.append(f"{py.name}:{text[:m.start()].count(chr(10)) + 1}")
    for py in (ROOT / "routes").rglob("*.py"):
        text = py.read_text()
        for m in re.finditer(r"get_effective_balance\"\s*,\s*\{\s*\"p_user_id\"", text):
            offenders.append(f"{py.name}:{text[:m.start()].count(chr(10)) + 1}")
    if not offenders:
        _ok("sweep: no p_user_id balance RPC call in services/ or routes/")
    else:
        _bad("sweep: no p_user_id balance RPC call in services/ or routes/", str(offenders))


# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-407 Phase 0 — money gate regression")
    print("=" * 60)
    test_migration_shape()
    test_telemetry_stamps_workspace()
    test_gate_workspace_keyed()
    test_spend_windows_workspace_keyed()
    test_no_stray_p_user_id_balance_calls()
    print("=" * 60)
    print(f"{len(_PASS)} passed, {len(_FAIL)} failed")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
