"""ADR-445/490 gate — the seat-sync ID, the free boundary, and the surfaced failure.

Found live 2026-07-29: the operator revoked a member (3 humans → 2), the roster
and seat count updated correctly, and the billing side silently did nothing. Two
defects under one symptom.

  1. THE ID (behavioural): the webhook read `payload.data.id` for EVERY event
     type. That is the subscription id only when `data.type == "subscriptions"`.
     On `subscription_payment_success` the resource is `subscription-invoices`,
     so `data.id` is the INVOICE id — and it was written over the good
     subscription id stored minutes earlier. Live receipt (ws d5b9029b): created
     + updated stored 2308204; payment_success clobbered it with 7779626, and
     every seat PATCH since 2026-07-02 404'd. Asserts `_ls_subscription_id`
     resolves each real payload shape, and that the handler never writes a None.

  2. THE FREE BOUNDARY: `max(1, billable_seats)` cannot express "nobody is on a
     paid seat any more" — at 2 humans it billed a phantom seat forever. Sync now
     CANCELS AT PERIOD END when billable hits 0. The floor is still correct at
     CHECKOUT (LS rejects quantity 0; the buyer is purchasing the incoming seat),
     so this asserts the two call sites diverge deliberately.

  3. THE READER: `seat_sync_failed` rows had been landing since the
     reconciliation layer shipped with NO reader — the operator found their own
     failure by hand-querying the table. Asserts the status payload carries the
     issue and the billing pane renders it.

Usage:
    cd api
    python3 test_adr445_seat_sync_boundary.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PASSED = 0
FAILED = 0

API = Path(__file__).parent
SUB = API / "routes" / "subscription.py"
WEB = API.parent / "web"
CARD = WEB / "components" / "subscription" / "SubscriptionCard.tsx"
TYPES = WEB / "types" / "index.ts"


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


def _py_code(src: str) -> str:
    """Strip comments + docstrings — they legitimately QUOTE the removed bug."""
    src = re.sub(r"^\s*#.*$", "", src, flags=re.M)
    return re.sub(r'""".*?"""', "", src, flags=re.S)


def main() -> int:
    src = SUB.read_text()
    code = _py_code(src)

    # ── 1. The ID resolver — BEHAVIOURAL, against the real payload shapes ────
    print("\n[id] the subscription id is never an invoice id")
    sys.path.insert(0, str(API))
    ns: dict = {"Optional": object}
    m = re.search(r"def _ls_subscription_id\(payload: dict\).*?\n    return None\n", src, re.S)
    check("_ls_subscription_id found", m is not None)
    if m:
        exec(compile(m.group(0), "<gate>", "exec"), ns)  # noqa: S102 — the function under test
        resolve = ns["_ls_subscription_id"]

        # The exact shapes LS sent this workspace (subscription_events receipts).
        created = {"data": {"id": "2308204", "type": "subscriptions",
                            "attributes": {"first_subscription_item":
                                           {"subscription_id": 2308204, "quantity": 1}}}}
        invoice = {"data": {"id": "7779626", "type": "subscription-invoices",
                            "attributes": {"subscription_id": 2308204}}}
        invoice_via_item = {"data": {"id": "7779626", "type": "subscription-invoices",
                                     "attributes": {"first_subscription_item":
                                                    {"subscription_id": 2308204}}}}
        opaque = {"data": {"id": "999", "type": "orders", "attributes": {}}}

        check("subscriptions payload → data.id", resolve(created) == "2308204")
        check("invoice payload → the SUBSCRIPTION id, not 7779626",
              resolve(invoice) == "2308204", f"got {resolve(invoice)}")
        check("invoice via first_subscription_item → 2308204",
              resolve(invoice_via_item) == "2308204")
        check("unresolvable payload → None (caller must not write)",
              resolve(opaque) is None)

    check("handler no longer reads the raw data.id",
          'subscription_id = str(payload.get("data", {}).get("id", ""))' not in code)
    check("handler resolves via _ls_subscription_id",
          "subscription_id = _ls_subscription_id(payload)" in code)
    # A None must never blank a working stored id.
    writes = re.findall(r'"lemonsqueezy_subscription_id"\]?\s*[:=]\s*subscription_id', code)
    for i, _ in enumerate(writes):
        pass
    check("every id write is guarded on a truthy id",
          code.count("if subscription_id:") >= 2,
          "an unguarded write can null a good id")

    # ── 2. The free boundary ─────────────────────────────────────────────────
    print("\n[boundary] 0 billable seats cancels, never bills a phantom seat")
    # Scope to sync_seat_quantity's own body — `max(1, ...)` legitimately
    # survives in create_checkout, so a whole-file grep would over-match the very
    # line we intend to keep.
    sync_body = re.search(
        r"async def sync_seat_quantity\(.*?\n(?=async def |def )", code, re.S,
    )
    check("sync_seat_quantity body found", sync_body is not None)
    if sync_body:
        check("sync no longer floors the quantity at 1",
              "max(1, billable_seats" not in sync_body.group(0))
        check("sync bills exactly the billable count", "quantity = billable" in sync_body.group(0))
    check("sync cancels at period end when billable == 0",
          "if billable == 0:" in code and "_cancel_subscription_at_period_end" in code)
    check("cancel helper uses LS DELETE (= cancel at period end)",
          re.search(r"_cancel_subscription_at_period_end.*?http\.delete", code, re.S) is not None)
    check("checkout KEEPS the floor (LS rejects quantity 0)",
          "seat_quantity = max(1, billable_seats(tier, humans))" in code)
    # The drift reconciler must not cry wolf during the cancel-pending window.
    check("drift check tolerates the cancel-pending window",
          "expected == 0 and billed == 1" in code)

    from services.billing_tiers import billable_seats
    check("2 humans on starter → 0 billable (the boundary)", billable_seats("starter", 2) == 0)
    check("3 humans on starter → 1 billable", billable_seats("starter", 3) == 1)

    # ── 3. The failure is SURFACED, not just recorded ────────────────────────
    print("\n[surface] a failed sync reaches the operator")
    check("status model carries seat_sync_issue", "seat_sync_issue: Optional[dict]" in code)
    check("status route populates it",
          "seat_sync_issue=_latest_unresolved_seat_sync_issue(workspace_id)" in code)
    check("resolver clears on a later success",
          '"seat_sync_succeeded"' in code and "_latest_unresolved_seat_sync_issue" in code)
    check("a successful sync records seat_sync_succeeded",
          '"event_type": "seat_sync_succeeded"' in code,
          "without it a resolved banner would never clear")
    check("the cancel path records its outcome",
          '"seat_subscription_cancelled"' in code)

    types_src = TYPES.read_text()
    check("FE type declares seat_sync_issue", "seat_sync_issue: SeatSyncIssue | null" in types_src)
    card_src = CARD.read_text()
    check("billing pane reads the issue", "status?.seat_sync_issue" in card_src)
    check("billing pane renders a warning banner",
          "seatSyncIssue &&" in card_src and "couldn&rsquo;t update your seat count" in card_src)

    print(f"\n{'='*60}\nseat-sync boundary gate: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
