"""In-app plan + seat management verbs (2026-07-22).

The Billing card's two management buttons were misleading: "Manage seats"
opened the Members permissions roster (no price on it) and "Manage" bounced to
the Lemon Squeezy customer portal (a differently-branded store page). Both are
now in-app. This gate covers the backend half — the `/subscription/cancel`
verb — by EXECUTING the handler against a fake LS + fake DB, not by grepping it.

The invariants that matter, and why each is load-bearing:

  1. Cancel does NOT write `subscription_tier` locally. LS cancellation is
     cancel-at-PERIOD-END; the tier flips on the `subscription_expired` webhook.
     Writing it here would strip a paid workspace of the allowance it already
     paid for, the instant it cancelled. The webhook stays the single writer.
  2. A comped (billing_exempt) workspace refuses — there is no subscription to
     cancel, and a silent success would imply a bill stopped that never ran.
  3. A workspace with no subscription id refuses rather than calling LS.
  4. An LS failure surfaces as an error, never a false "cancelled".
  5. `ends_at` is read back so the surface can say WHEN access stops.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Optional

FAIL: list[str] = []


def _check(cond: bool, label: str) -> None:
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        FAIL.append(label)


# ── Fakes ────────────────────────────────────────────────────────────────────


class _Resp:
    def __init__(self, status_code: int, payload: Optional[dict] = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class _Table:
    """Records every write so the gate can assert what was NOT written."""

    def __init__(self, rows: list[dict], writes: list[tuple[str, dict]], name: str):
        self._rows, self._writes, self._name = rows, writes, name

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return type("R", (), {"data": list(self._rows)})()

    def update(self, payload: dict):
        self._writes.append((self._name, payload))
        return self

    def insert(self, payload: dict):
        self._writes.append((self._name, payload))
        return self


class _Client:
    def __init__(self, ws_row: dict):
        self.writes: list[tuple[str, dict]] = []
        self._ws = [ws_row] if ws_row else []

    def table(self, name: str):
        return _Table(self._ws if name == "workspaces" else [], self.writes, name)


class _Auth:
    def __init__(self, client): self.client, self.user_id, self.email = client, "u-1", "kvk@example.com"


def _run(ws_row: dict, ls: _Resp):
    """Execute the real handler with LS + billing-workspace resolution stubbed."""
    import routes.subscription as S

    client = _Client(ws_row)
    orig_key, orig_resolve, orig_http = (
        S.LEMONSQUEEZY_API_KEY, S._resolve_billing_workspace, S.httpx.AsyncClient,
    )
    S.LEMONSQUEEZY_API_KEY = "test-key"
    S._resolve_billing_workspace = lambda auth: "ws-1"

    class _HTTP:
        async def __aenter__(self): return self
        async def __aexit__(self, *_): return False
        async def delete(self, *_a, **_k): return ls

    S.httpx.AsyncClient = lambda *a, **k: _HTTP()
    try:
        out = asyncio.run(S.cancel_subscription(_Auth(client)))
        return {"ok": True, "result": out, "writes": client.writes}
    except Exception as e:  # noqa: BLE001 — the gate inspects the raised error
        return {"ok": False, "error": e, "writes": client.writes}
    finally:
        S.LEMONSQUEEZY_API_KEY = orig_key
        S._resolve_billing_workspace = orig_resolve
        S.httpx.AsyncClient = orig_http


PAID = {
    "id": "ws-1", "subscription_tier": "starter", "billing_exempt": False,
    "lemonsqueezy_subscription_id": "sub-9",
}


def main() -> None:
    print("\n[1] Cancel succeeds and reports the period-end boundary")
    r = _run(PAID, _Resp(200, {"data": {"attributes": {"ends_at": "2026-08-22T00:00:00Z"}}}))
    _check(r["ok"], "handler returns without raising")
    if r["ok"]:
        _check(r["result"].cancelled is True, "cancelled is True")
        _check(r["result"].ends_at == "2026-08-22T00:00:00Z", "ends_at is read back from LS")

    print("\n[2] Cancel does NOT downgrade the tier locally (the webhook owns it)")
    tier_writes = [w for w in r["writes"] if "subscription_tier" in (w[1] or {})]
    _check(not tier_writes, f"no local subscription_tier write (found {tier_writes})")
    _check(not r["writes"], f"no DB write at all on cancel (found {r['writes']})")

    print("\n[3] A comped workspace refuses (no subscription to cancel)")
    r2 = _run({**PAID, "billing_exempt": True}, _Resp(200, {}))
    _check(not r2["ok"], "raises rather than silently succeeding")
    _check(getattr(r2.get("error"), "status_code", None) == 400, "400, not 500")
    _check("comped" in str(getattr(r2.get("error"), "detail", "")).lower(), "detail names the comp")

    print("\n[4] A workspace with no subscription refuses before calling LS")
    r3 = _run({**PAID, "lemonsqueezy_subscription_id": None}, _Resp(500, None, "should not be called"))
    _check(not r3["ok"], "raises")
    _check(getattr(r3.get("error"), "status_code", None) == 400, "400 (bad request, not gateway)")

    print("\n[5] An LS failure surfaces — never a false 'cancelled'")
    r4 = _run(PAID, _Resp(422, None, "unprocessable"))
    _check(not r4["ok"], "raises on LS non-2xx")
    _check(getattr(r4.get("error"), "status_code", None) == 502, "502 bad gateway")
    _check(not r4["writes"], "a failed cancel writes nothing")

    print("\n[6] A 204 (no body) still succeeds — ends_at simply unknown")
    r5 = _run(PAID, _Resp(204))
    _check(r5["ok"] and r5["result"].cancelled is True, "204 counts as cancelled")
    _check(r5["ok"] and r5["result"].ends_at is None, "ends_at None, not a crash")

    print("\n" + "=" * 60)
    print(f"billing manage-verbs gate: {'FAILED ' + str(len(FAIL)) if FAIL else 'ALL PASS'}")
    print("=" * 60)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
