"""Gate: a paid top-up that never arrives is VISIBLE (2026-09-02).

THE INCIDENT THIS GATES
-----------------------
The Lemon Squeezy store had two webhooks registered for the same events — a
stale `https://api.ep-0.com/webhooks/lemonsqueezy` beside the live yarnnn one.
Order 2216529 ($25.00) was routed to the stale host, which answered an HTML 503.

Nothing reached the API: no request in the access log, no row in any table, no
error anywhere in the system. The member's money left their account, the balance
did not move, and the ONLY reason it was ever noticed is that the operator
happened to look at the number and find it unchanged.

A webhook that never arrives is invisible by construction — you cannot detect it
from the events it failed to write. So the detector reads the GAP between two
things we do record: a checkout we minted, and the credit it should have made.

WHAT IS ASSERTED
----------------
  1. minting a top-up checkout leaves a durable row (the promise)
  2. a checkout with no credit after the grace window is REPORTED
  3. a checkout with a credit after it is SILENT          (no false alarm)
  4. a checkout still inside the grace window is SILENT   (no premature alarm)
  5. a credit landing INSIDE the grace window still resolves it
  6. the detector never raises — a read failure returns None, not a broken pane
  7. the signal is on the status payload, and the surface renders it

Every positive is paired with its negative: a detector that only ever fires, or
only ever stays quiet, would pass a one-sided gate while being useless.

    cd api && python3 test_undelivered_topup_is_visible.py
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0


def check(label, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {label}")
    else:
        failed += 1
        print(f"  [FAIL] {label}" + (f" -- {detail}" if detail else ""))


# ── Fake Supabase, shaped like the real client's fluent chain ────────────────

class FakeQuery:
    def __init__(self, rows, sink=None):
        self._rows = list(rows)
        self._sink = sink
        self._filters = []

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def lt(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) < val]
        return self

    def gte(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) >= val]
        return self

    def order(self, col, desc=False):
        self._rows.sort(key=lambda r: r.get(col) or "", reverse=desc)
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    def insert(self, row):
        if self._sink is not None:
            self._sink.append(row)
        return self

    def execute(self):
        return type("R", (), {"data": self._rows})()


class FakeClient:
    def __init__(self, events=(), txs=()):
        self.events = list(events)
        self.txs = list(txs)
        self.inserted = []

    def table(self, name):
        if name == "subscription_events":
            return FakeQuery(self.events, sink=self.inserted)
        if name == "balance_transactions":
            return FakeQuery(self.txs)
        return FakeQuery([])


class ExplodingClient:
    def table(self, _name):
        raise RuntimeError("supabase is down")


def iso(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


WS = "ws-1"


def with_client(client, fn):
    """Run fn with services.supabase.get_service_client patched."""
    import services.supabase as sb
    original = sb.get_service_client
    sb.get_service_client = lambda: client
    try:
        return fn()
    finally:
        sb.get_service_client = original


print("=" * 62)
print("undelivered top-up gate")
print("=" * 62)

import routes.subscription as subs  # noqa: E402

GRACE = subs.TOPUP_DELIVERY_GRACE_MINUTES


# ── 1. the promise is recorded ───────────────────────────────────────────────
print("\n[1] minting a checkout leaves a durable row")
c = FakeClient()
with_client(c, lambda: subs._record_topup_checkout(WS, "user-1", 25.0))
check("one row written", len(c.inserted) == 1, f"rows={c.inserted}")
if c.inserted:
    row = c.inserted[0]
    check("event_type is topup_checkout_created",
          row.get("event_type") == "topup_checkout_created", str(row))
    check("event_source is 'yarnnn' (our act, not LS-reported)",
          row.get("event_source") == "yarnnn", str(row))
    check("amount is carried on the payload",
          (row.get("payload") or {}).get("amount_usd") == 25.0, str(row))

print("    a bookkeeping failure must not break the checkout")
try:
    with_client(ExplodingClient(), lambda: subs._record_topup_checkout(WS, "u", 25.0))
    check("writer swallows a DB failure", True)
except Exception as exc:  # noqa: BLE001
    check("writer swallows a DB failure", False, f"raised {exc!r}")


# ── 2/3. fires when undelivered, silent when delivered ───────────────────────
print("\n[2] a checkout with no credit after it is REPORTED")
stale = {"workspace_id": WS, "event_type": "topup_checkout_created",
         "created_at": iso(GRACE + 10), "payload": {"amount_usd": 25.0}}
c = FakeClient(events=[stale])
got = with_client(c, lambda: subs._undelivered_topup(WS))
check("signal returned", got is not None, f"got={got}")
check("carries the amount", (got or {}).get("amount_usd") == 25.0, f"got={got}")
check("carries the timestamp", (got or {}).get("at") == stale["created_at"], f"got={got}")

print("\n[3] a checkout WITH a credit after it is SILENT (no false alarm)")
credited = {"workspace_id": WS, "kind": "topup", "created_at": iso(GRACE + 5)}
c = FakeClient(events=[stale], txs=[credited])
check("no signal", with_client(c, lambda: subs._undelivered_topup(WS)) is None)

print("    a credit for a DIFFERENT workspace must not resolve ours")
other = {"workspace_id": "ws-2", "kind": "topup", "created_at": iso(GRACE + 5)}
c = FakeClient(events=[stale], txs=[other])
check("still reported", with_client(c, lambda: subs._undelivered_topup(WS)) is not None)

print("    a non-topup credit must not resolve it")
allowance = {"workspace_id": WS, "kind": "allowance_grant", "created_at": iso(GRACE + 5)}
c = FakeClient(events=[stale], txs=[allowance])
check("still reported", with_client(c, lambda: subs._undelivered_topup(WS)) is not None)

print("    a credit from BEFORE the checkout must not resolve it")
old = {"workspace_id": WS, "kind": "topup", "created_at": iso(GRACE + 999)}
c = FakeClient(events=[stale], txs=[old])
check("still reported", with_client(c, lambda: subs._undelivered_topup(WS)) is not None)


# ── 4/5. the grace window ────────────────────────────────────────────────────
print("\n[4] a checkout inside the grace window is SILENT (not premature)")
fresh = {"workspace_id": WS, "event_type": "topup_checkout_created",
         "created_at": iso(max(GRACE - 10, 1)), "payload": {"amount_usd": 25.0}}
c = FakeClient(events=[fresh])
check("no signal yet", with_client(c, lambda: subs._undelivered_topup(WS)) is None)

print("\n[5] a credit inside the grace window still resolves it")
inside = {"workspace_id": WS, "kind": "topup", "created_at": iso(GRACE + 9)}
c = FakeClient(events=[stale], txs=[inside])
check("resolved", with_client(c, lambda: subs._undelivered_topup(WS)) is None)

print("\n    no checkouts at all -> silent")
check("no signal", with_client(FakeClient(), lambda: subs._undelivered_topup(WS)) is None)

print("    the grace window is a real duration, not zero")
check(f"grace = {GRACE}min, within a sane range", 5 <= GRACE <= 240, f"grace={GRACE}")


# ── 6. never breaks the pane ─────────────────────────────────────────────────
print("\n[6] a read failure returns None, never an exception")
try:
    got = with_client(ExplodingClient(), lambda: subs._undelivered_topup(WS))
    check("returns None on failure", got is None, f"got={got}")
except Exception as exc:  # noqa: BLE001
    check("returns None on failure", False, f"raised {exc!r}")


# ── 7. it reaches the surface ────────────────────────────────────────────────
print("\n[7] the signal is on the payload and rendered")
check("SubscriptionStatus declares undelivered_topup",
      "undelivered_topup" in subs.SubscriptionStatus.model_fields)

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "routes", "subscription.py"), encoding="utf-8").read()
check("status endpoint populates it",
      re.search(r"undelivered_topup=_undelivered_topup\(workspace_id\)", src) is not None)
check("checkout records the promise",
      re.search(r"_record_topup_checkout\(workspace_id,", src) is not None)
check("only top-ups are recorded (a subscription order is not a top-up)",
      re.search(r'if request\.checkout_type == "topup":\s*\n\s*_record_topup_checkout', src)
      is not None)

web = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")
card = open(os.path.join(web, "components", "subscription", "SubscriptionCard.tsx"),
            encoding="utf-8").read()
check("the card reads the field", "undelivered_topup" in card)
check("the card renders a banner", "undeliveredTopup && (" in card)
check("copy hedges on completion (an abandoned checkout trips the same signal)",
      "If you completed" in card or "if you completed" in card)
types = open(os.path.join(web, "types", "index.ts"), encoding="utf-8").read()
check("the FE type declares it", "undelivered_topup: UndeliveredTopup | null" in types)


print("\n" + "=" * 62)
print(f"undelivered-topup gate: {passed} passed, {failed} failed")
print("=" * 62)
sys.exit(1 if failed else 0)
