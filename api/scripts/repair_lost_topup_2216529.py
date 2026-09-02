"""One-shot repair: credit LS order 2216529 ($25.00), lost to a stale webhook.

WHAT HAPPENED (2026-09-02)
--------------------------
The Lemon Squeezy store had TWO webhooks registered for the same events:

    https://api.ep-0.com/webhooks/lemonsqueezy            <- stale, not ours
    https://yarnnn-api.onrender.com/api/webhooks/lemonsqueezy   <- live

Order 2216529 ("yarnnn - Usage Top Up", $25.00, 05:00 UTC) was delivered to the
stale host, which answered an HTML 503. Our API therefore logged NO request at
all -- the Render access log for /api/webhooks/lemonsqueezy is empty across the
whole window, and balance_transactions has never held a single kind='topup' row.
The dashboard's Resend replays a delivery to the endpoint that delivery belongs
to, so resending only hit the dead host again. The stale webhook has since been
deleted, but that cannot retroactively route an order already dispatched.

The payment is real: LS emailed the receipt (order #2216529, $25.00, KIM SEUL KI,
kvkthecreator@gmail.com). This script credits it by hand.

WHY grant_balance AND NOT A RAW UPDATE
--------------------------------------
It calls the SAME function routes/subscription.py::handle_lemonsqueezy_webhook
calls on order_created, with the same kind and the same lemon_order_id. The
resulting row is indistinguishable from a normally-delivered top-up, so the
ledger reconciles and the audit trail names the real order. A raw balance_usd
UPDATE would move the money while leaving no attributable transaction row.

SAFE TO RUN TWICE. grant_balance is idempotent on lemon_order_id (added in the
same commit as this script). That guard is also what makes this repair safe
against LS later retrying order 2216529 into the now-healthy webhook.

    cd api && python3 scripts/repair_lost_topup_2216529.py

Delete this script once run -- it is a record of a one-time incident, not a tool.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services.platform_limits import grant_balance  # noqa: E402
from services.supabase import get_service_client  # noqa: E402

WORKSPACE_ID = "d5b9029b-bd4e-4757-9fcb-e2b139fd4913"  # "yarnnn workspace"
ORDER_ID = "2216529"
AMOUNT_USD = 25.00
TOTAL_CENTS = 2500


def balance(client) -> float:
    row = (
        client.table("workspaces")
        .select("balance_usd")
        .eq("id", WORKSPACE_ID)
        .limit(1)
        .execute()
    )
    return float(row.data[0]["balance_usd"])


def tx_rows(client):
    return (
        client.table("balance_transactions")
        .select("created_at,kind,amount_usd,lemon_order_id,metadata")
        .eq("lemon_order_id", ORDER_ID)
        .execute()
        .data
        or []
    )


def main() -> int:
    client = get_service_client()

    before = balance(client)
    print(f"before : balance_usd = {before}")
    print(f"         tx rows for order {ORDER_ID} = {len(tx_rows(client))}")

    grant_balance(
        client,
        workspace_id=WORKSPACE_ID,
        amount_usd=AMOUNT_USD,
        kind="topup",
        lemon_order_id=ORDER_ID,
        metadata={
            "order_id": ORDER_ID,
            "total_cents": TOTAL_CENTS,
            "manual_repair": (
                "delivered to stale api.ep-0.com webhook -> HTTP 503; never reached "
                "the API. Credited by hand from the LS email receipt (2026-09-02)."
            ),
        },
    )

    after = balance(client)
    rows = tx_rows(client)
    print(f"after  : balance_usd = {after}  (+{round(after - before, 4)})")
    print(f"         tx rows for order {ORDER_ID} = {len(rows)}")
    for r in rows:
        print("   ", r)

    # Prove the guard on the REAL row: a replay must move nothing.
    grant_balance(
        client,
        workspace_id=WORKSPACE_ID,
        amount_usd=AMOUNT_USD,
        kind="topup",
        lemon_order_id=ORDER_ID,
    )
    replayed = balance(client)
    print(f"replay : balance_usd = {replayed}  (must equal {after})")

    if replayed != after:
        print("FAIL: replay double-credited")
        return 1
    if len(tx_rows(client)) != 1:
        print("FAIL: replay wrote a second transaction row")
        return 1

    print("\nOK - credited once; a retry of this order is now a no-op.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
