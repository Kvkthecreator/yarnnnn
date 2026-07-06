"""ADR-410 D2 hygiene one-shot — expire the stale pre-D3 substrate proposals.

ADR-408 D3 (2026-07-06) flipped the steward's substrate-family delegation to
autonomous: post-D3, a reversible substrate act applies directly and never
queues. Substrate-family proposals still `pending` from before the flip are
ZOMBIES — they misrepresent the witness queue (the operator's bell showed
four of them, ADR-410 §1). Per D2: expired-with-reason, auditable, never
deleted.

Scope: status='pending' AND family='substrate' only. Capital-family pending
proposals are REAL queue entries (the dial still gates capital) and are not
touched. `expired` is a first-class status (migration 149's check constraint);
the reason lands in rejection_reason (the lifecycle's reason field).

Run:  .venv/bin/python api/scripts/oneshot/adr410_d2_expire_stale_substrate_proposals.py [--apply]
      (dry-run by default; --apply mutates)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

REASON = (
    "Expired by the ADR-410 D2 hygiene sweep (2026-07-06): substrate-family "
    "delegation went autonomous (ADR-408 D3) — post-D3 this act applies "
    "directly and never queues; the pending row predates the flip."
)


def main(apply: bool) -> int:
    from services.supabase import get_service_client

    client = get_service_client()
    rows = (
        client.table("action_proposals")
        .select("id, workspace_id, user_id, primitive, source, created_at")
        .eq("status", "pending")
        .eq("family", "substrate")
        .order("created_at")
        .execute()
        .data
        or []
    )
    print(f"pending substrate-family proposals: {len(rows)}")
    for r in rows:
        print(
            f"  {r['id']}  ws={str(r.get('workspace_id'))[:8]}  "
            f"{r.get('primitive')}  src={r.get('source')}  at={r.get('created_at')}"
        )

    if not rows:
        print("nothing to expire — queue already clean.")
        return 0
    if not apply:
        print("\nDRY RUN — re-run with --apply to expire the rows above.")
        return 0

    ids = [r["id"] for r in rows]
    client.table("action_proposals").update(
        {"status": "expired", "rejection_reason": REASON}
    ).in_("id", ids).execute()
    # Receipt: re-read and report.
    check = (
        client.table("action_proposals")
        .select("id, status")
        .in_("id", ids)
        .execute()
        .data
        or []
    )
    expired = sum(1 for r in check if r.get("status") == "expired")
    print(f"\nexpired {expired}/{len(ids)} rows (receipt ids above).")
    return 0 if expired == len(ids) else 1


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
