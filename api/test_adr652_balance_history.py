"""ADR-652 gate — the balance history is legible, and honest about duplicates.

SCRIPT-SHAPED: run it and read the COUNT, not the exit code.

    cd api && python3 -B test_adr652_balance_history.py

What it holds, driving the REAL route body against fake ledger rows:

  ① the live Jul-2 retry cluster (workspace d5b9029b: 3 x $15 in 33s, one
     purchase) renders as ONE credit;
  ②–⑤ nothing else collapses — same amount days apart, just outside the window,
     a different kind, a different amount all survive as distinct credits;
  ⑥ a deeper cluster collapses to one, not to pairs;
  ⑦ an unparseable timestamp forgoes the comparison instead of collapsing blindly;
  ⑧ a $0 or negative row never renders (the ADR-490 marker row is $0.0000);
  ⑨ an unknown kind falls back to a neutral label, never the raw slug;
  ⑩ has_more trips past the page limit;
  ⑪ the route 403s a caller without billing authority, exactly as /status does
     (the ledger is not a new door into the workspace's money);
  ⑫ the served payload's keys match the `BalanceEntry` TS interface, driven over
     real HTTP through the real router.

⭐ PROVEN RED: with the pre-fix `_parse_ledger_ts` (bare py3.9 `fromisoformat`,
which rejects the 5-fractional-digit timestamps Postgres actually emits) check ①
renders 3 rows instead of 1. The first cut of this feature shipped exactly that
way — green on every structural read, collapsing nothing on live data. Check ⑦
is what keeps the fallback honest rather than silently permissive.
"""
import asyncio, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routes.subscription as sub

class FakeTable:
    def __init__(self, rows): self._rows = rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self):
        class R: data = self._rows
        return R()
class FakeClient:
    def __init__(self, rows): self._rows = rows
    def table(self, name): return FakeTable(self._rows)
class FakeAuth:
    def __init__(self, rows): self.client = FakeClient(rows); self.email = None

sub._resolve_billing_workspace = lambda auth: "ws"
loop = asyncio.new_event_loop()
def run(rows):
    return loop.run_until_complete(sub.get_balance_history(FakeAuth(rows))).entries

def row(at, kind, amt, order=None):
    return {"created_at": at, "kind": kind, "amount_usd": amt, "lemon_order_id": order}

fails = []
def check(name, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: got {got}, want {want}")
    if not ok: fails.append(name)

print("① the real Jul-2 retry cluster collapses to one")
check("3 identical within 33s", len(run([
    row("2026-07-02T01:42:19.710613+00:00","allowance_grant",15.0),
    row("2026-07-02T01:42:18.19472+00:00","allowance_grant",15.0),
    row("2026-07-02T01:41:46.826223+00:00","allowance_grant",15.0),
])), 1)

print("② two REAL top-ups of the same amount, days apart, both survive")
check("same amount 2 days apart", len(run([
    row("2026-09-04T10:00:00+00:00","topup",25.0,"A"),
    row("2026-09-02T10:00:00+00:00","topup",25.0,"B"),
])), 2)

print("③ two real top-ups same amount just OUTSIDE the window (301s)")
check("301s apart", len(run([
    row("2026-09-02T10:05:01+00:00","topup",25.0,"A"),
    row("2026-09-02T10:00:00+00:00","topup",25.0,"B"),
])), 2)

print("④ same amount, DIFFERENT kind, seconds apart — both survive")
check("different kind", len(run([
    row("2026-09-02T10:00:05+00:00","topup",15.0),
    row("2026-09-02T10:00:00+00:00","admin_grant",15.0),
])), 2)

print("⑤ different amount, same kind, seconds apart — both survive")
check("different amount", len(run([
    row("2026-09-02T10:00:05+00:00","topup",25.0),
    row("2026-09-02T10:00:00+00:00","topup",30.0),
])), 2)

print("⑥ a 4-deep retry cluster collapses to one, not two")
check("4 identical within window", len(run([
    row("2026-09-02T10:00:30+00:00","topup",25.0),
    row("2026-09-02T10:00:20+00:00","topup",25.0),
    row("2026-09-02T10:00:10+00:00","topup",25.0),
    row("2026-09-02T10:00:00+00:00","topup",25.0),
])), 1)

print("⑦ unparseable timestamps forgo dedupe rather than collapsing blindly")
check("both garbage survive", len(run([
    row("garbage","topup",25.0), row("garbage","topup",25.0),
])), 2)

print("⑧ $0 and negative rows never render")
check("zero + negative dropped", len(run([
    row("2026-09-02T10:00:00+00:00","allowance_grant",0.0),
    row("2026-09-01T10:00:00+00:00","topup",-5.0),
])), 0)

print("⑨ unknown kind falls back to a neutral label, never the slug")
e = run([row("2026-09-02T10:00:00+00:00","some_future_kind",5.0)])
check("neutral label", e[0].label, "Credit")

print("⑩ has_more trips past the page limit")
many = [row(f"2026-09-02T10:{i//60:02d}:{i%60:02d}+00:00","admin_grant",float(i+1)) for i in range(sub.BALANCE_HISTORY_LIMIT+5)]
many.sort(key=lambda r: r["created_at"], reverse=True)
res = loop.run_until_complete(sub.get_balance_history(FakeAuth(many)))
check("has_more true", res.has_more, True)

print("⑪ the route is gated identically to /status — no new door")
import typing
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

_app = FastAPI()
_app.include_router(sub.router, prefix="/api")
_args = typing.get_args(sub.UserClient)
_app.dependency_overrides[_args[1].dependency] = lambda: FakeAuth([])

def _deny(auth):
    raise HTTPException(status_code=403, detail="Billing is managed by the workspace owner")

_saved = sub._resolve_billing_workspace
sub._resolve_billing_workspace = _deny
_c = TestClient(_app)
for _path in ("/api/subscription/status", "/api/subscription/transactions"):
    check(f"403 on {_path.split('/')[-1]}", _c.get(_path).status_code, 403)
sub._resolve_billing_workspace = _saved

print("⑫ the payload shape matches the BalanceEntry TS interface over real HTTP")
sub._resolve_billing_workspace = lambda auth: "ws"
_app2 = FastAPI()
_app2.include_router(sub.router, prefix="/api")
_app2.dependency_overrides[_args[1].dependency] = lambda: FakeAuth([
    row("2026-09-02T07:45:39.872586+00:00", "topup", 25.0, "2216529"),
])
_r = TestClient(_app2).get("/api/subscription/transactions")
check("HTTP 200", _r.status_code, 200)
_body = _r.json()
check("top-level keys", sorted(_body), ["entries", "has_more"])
check(
    "entry keys",
    sorted(_body["entries"][0]),
    ["amount_usd", "at", "kind", "label", "order_id"],
)

print()
total = 15
passed = total - len(fails)
print(f"ADR-652: {passed}/{total} checks passed")
print()
print(
    "NOTE — one condition this gate CANNOT assert: `balance_transactions` had RLS\n"
    "ENABLED WITH ZERO POLICIES on live, which denies every row to a non-service\n"
    "role. The endpoint returned HTTP 200 / entries:0 to the workspace's own owner\n"
    "against 6 real rows, and every check above stayed green (they fake the client;\n"
    "RLS lives in the database). Migration 255 restores migration 144's owner-only\n"
    "SELECT policy. To verify the LIVE object, not this file:\n"
    "    SELECT count(*) FROM pg_policy WHERE polrelid='balance_transactions'::regclass;\n"
    "  -- must be >= 1; it was 0 on 2026-09-16\n"
    "Only an authenticated read against a real deploy proves this path."
)
if fails:
    print("FAILED:", ", ".join(fails))
    sys.exit(1)
