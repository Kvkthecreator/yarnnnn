"""ADR-445 §7 P2 gate — seat drift is DETECTED and RECORDED.

WHY (the audit finding, 2026-07-21): nothing could ever detect seat drift.
`sync_seat_quantity` is doubly best-effort (a non-2xx only logs; the outer
`except` ate what the inner already swallowed) and the webhook read variant /
status / renewal / customer but NEVER `quantity`. So a failed LS PATCH meant:
the member lifecycle succeeded, LS kept billing the OLD quantity,
`/subscription/status` reported the NEW computed fee, and no row, flag, or retry
anywhere recorded the divergence — permanent silent under-billing on the axis
ADR-445 designates as the team-revenue path.

The fix is OBSERVE-ONLY by design: the webhook never PATCHes back (an owner may
legitimately set quantity in the LS customer portal, and a webhook fighting the
portal would loop). It records `seat_quantity_drift` / `seat_sync_failed` rows to
`subscription_events` — making the gap durable and queryable rather than correct
by force.

This gate CALLS the reconciler against a fake client and asserts what lands.

Usage:
    cd api
    python test_adr445_seat_reconciliation.py
"""

from __future__ import annotations

import sys
import types

PASSED = 0
FAILED = 0

WS = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


class _Q:
    def __init__(self, table, store):
        self.table_name, self.store = table, store
        self.filters = {}

    def select(self, *_a, **_k): return self
    def limit(self, *_a, **_k): return self
    def in_(self, *_a, **_k): return self

    def eq(self, c, v):
        self.filters[c] = v
        return self

    def insert(self, row):
        self.store.setdefault(self.table_name, []).append(row)
        return self

    def execute(self):
        if self.table_name == "principal_grants":
            # `humans` controls the roster size the reconciler will count.
            n = self.store.get("_humans", 1)
            return types.SimpleNamespace(
                data=[{"principal_id": f"h{i}", "role": "member"} for i in range(n)]
            )
        return types.SimpleNamespace(data=[])


class FakeClient:
    def __init__(self, humans=1):
        self.store = {"_humans": humans}

    def table(self, name):
        return _Q(name, self.store)

    def rows(self, table):
        return self.store.get(table, [])


def _attrs(quantity):
    return {"first_subscription_item": {"quantity": quantity}}


def test_quantity_is_read_from_the_payload() -> None:
    print("\n[read] the webhook parses LS's reported seat quantity")
    from routes.subscription import _ls_quantity
    check("reads first_subscription_item.quantity", _ls_quantity(_attrs(3)) == 3)
    check("tolerates a string quantity", _ls_quantity(_attrs("2")) == 2)
    check("absent item → None (not an error)", _ls_quantity({}) is None)
    check("absent quantity → None", _ls_quantity({"first_subscription_item": {}}) is None)


def test_drift_is_recorded() -> None:
    print("\n[drift] a mismatch lands a durable subscription_events row")
    from routes.subscription import _reconcile_seat_quantity
    # 3 humans on starter → expected billable = 2. LS says it bills 1.
    c = FakeClient(humans=3)
    _reconcile_seat_quantity(c, WS, "starter", _attrs(1), "subscription_updated")
    rows = c.rows("subscription_events")
    check("exactly one drift row written", len(rows) == 1, f"rows={rows}")
    if rows:
        r = rows[0]
        check("event_type is seat_quantity_drift", r["event_type"] == "seat_quantity_drift")
        check("source marks it as OURS, not LS", r["event_source"] == "yarnnn")
        check("payload carries billed vs expected",
              r["payload"]["billed_quantity"] == 1 and r["payload"]["expected_quantity"] == 2,
              f"payload={r['payload']}")
        check("payload names the observing event",
              r["payload"]["observed_on"] == "subscription_updated")


def test_agreement_is_silent() -> None:
    print("\n[quiet] when LS agrees with the roster, nothing is written")
    from routes.subscription import _reconcile_seat_quantity
    c = FakeClient(humans=3)          # expected billable = 2
    _reconcile_seat_quantity(c, WS, "starter", _attrs(2), "subscription_updated")
    check("no row on agreement", not c.rows("subscription_events"),
          f"rows={c.rows('subscription_events')}")


def test_solo_floor_is_not_reported_as_drift() -> None:
    print("\n[floor] a solo workspace billing 1 is NOT drift (the ratified floor)")
    from routes.subscription import _reconcile_seat_quantity
    c = FakeClient(humans=1)  # billable_seats = 0, floored to 1 at checkout
    _reconcile_seat_quantity(c, WS, "starter", _attrs(1), "subscription_created")
    check("solo at quantity 1 is quiet", not c.rows("subscription_events"),
          "max(1, billable_seats) is the ratified charge, not a defect")


def test_missing_quantity_is_not_drift() -> None:
    print("\n[tolerance] an event without a quantity says nothing about drift")
    from routes.subscription import _reconcile_seat_quantity
    c = FakeClient(humans=5)
    _reconcile_seat_quantity(c, WS, "starter", {}, "subscription_resumed")
    check("no row when LS reports no quantity", not c.rows("subscription_events"))


def test_sync_failure_is_recorded() -> None:
    print("\n[sync] a swallowed PATCH failure still leaves a record")
    from routes.subscription import _record_seat_sync_failure
    c = FakeClient()
    _record_seat_sync_failure(c, WS, "sub_1", 3, 4, "http_422", "unprocessable")
    rows = c.rows("subscription_events")
    check("a seat_sync_failed row is written", len(rows) == 1, f"rows={rows}")
    if rows:
        check("it carries the intended quantity + reason",
              rows[0]["payload"]["intended_quantity"] == 3
              and rows[0]["payload"]["reason"] == "http_422",
              f"payload={rows[0]['payload']}")


def test_reconciler_never_raises() -> None:
    print("\n[safety] reconciliation can never break webhook handling")
    from routes.subscription import _reconcile_seat_quantity, _record_seat_sync_failure

    class Exploding:
        def table(self, *_a, **_k):
            raise RuntimeError("db down")

    try:
        _reconcile_seat_quantity(Exploding(), WS, "starter", _attrs(9), "subscription_updated")
        _record_seat_sync_failure(Exploding(), WS, "s", 1, 1, "x")
        check("both swallow a DB failure", True)
    except Exception as exc:  # noqa: BLE001
        check("both swallow a DB failure", False, f"raised {exc!r}")


def test_webhook_invokes_the_reconciler() -> None:
    print("\n[wiring] the lifecycle handler actually calls it")
    import inspect
    import routes.subscription as sub
    src = inspect.getsource(sub)
    check("_reconcile_seat_quantity is called in the webhook body",
          "_reconcile_seat_quantity(client, workspace_id, tier, attrs, event_name)" in src,
          "a reconciler nothing calls is not reconciliation")


def test_status_uses_the_exempt_aware_count() -> None:
    print("\n[status] a comped workspace does not report phantom billable seats")
    import inspect
    import routes.subscription as sub
    src = inspect.getsource(sub)
    check("billable_seats field uses n_billable (exempt-aware)",
          "billable_seats=n_billable" in src,
          "re-calling _billable_seats here drops the exempt override")


def main() -> int:
    print("=" * 74)
    print("ADR-445 §7 P2 — seat-drift detection + the reconciliation record")
    print("=" * 74)
    test_quantity_is_read_from_the_payload()
    test_drift_is_recorded()
    test_agreement_is_silent()
    test_solo_floor_is_not_reported_as_drift()
    test_missing_quantity_is_not_drift()
    test_sync_failure_is_recorded()
    test_reconciler_never_raises()
    test_webhook_invokes_the_reconciler()
    test_status_uses_the_exempt_aware_count()
    print("\n" + "=" * 74)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 74)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
