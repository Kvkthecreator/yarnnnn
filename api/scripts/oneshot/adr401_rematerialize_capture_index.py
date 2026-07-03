"""ADR-401 Phase 4 one-time repair: rematerialize the capture index.

The seeded connector cadence `@every 15min` was unresolvable before the
bare-interval schedule fix (commit bae3e33): `_is_semantic` classified any
@-prefixed string as semantic, so `compute_next_run_at` either raised (no
market_context) or failed the `during <session>` grammar — and the seeded
capture rows were materialized with `next_run_at = NULL`. `get_due_captures`
only selects `next_run_at <= now`, so those rows could NEVER become due:
this is why no connector capture ever fired live.

The grammar fix makes the schedules resolvable, but nothing in the scheduler
tick rematerializes an already-NULL row (materialization happens at
seed/teardown/cadence-edit time). This script re-runs
`materialize_capture_index` once for every workspace that has a
`_captures.yaml`, recomputing `next_run_at` under the fixed grammar.

Idempotent + re-runnable (materialize is an idempotent sync). Pure
deterministic Python — no LLM calls. Service client (RLS bypass).

Usage (run the file directly — the script self-inserts the api root on sys.path):
    cd api && python scripts/oneshot/adr401_rematerialize_capture_index.py          # dry-run
    cd api && python scripts/oneshot/adr401_rematerialize_capture_index.py --apply  # rematerialize
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_API_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("adr401-rematerialize")


async def main(apply: bool) -> int:
    from services.supabase import get_service_client
    from services.conventions import CAPTURES_PATH
    from services.capture.scheduling import materialize_capture_index

    client = get_service_client()

    # Every workspace with a _captures.yaml (the declaration truth).
    rows = (
        client.table("workspace_files")
        .select("user_id")
        .eq("path", CAPTURES_PATH)
        .execute()
    ).data or []
    user_ids = sorted({r["user_id"] for r in rows if r.get("user_id")})
    logger.info("workspaces with _captures.yaml: %d", len(user_ids))

    # Receipt: capture rows currently stuck at next_run_at NULL.
    stuck = (
        client.table("tasks")
        .select("user_id, slug, next_run_at, paused")
        .eq("kind", "capture")
        .is_("next_run_at", "null")
        .execute()
    ).data or []
    live_stuck = [r for r in stuck if not r.get("paused")]
    logger.info(
        "capture rows with next_run_at=NULL: %d (%d active/un-paused)",
        len(stuck), len(live_stuck),
    )
    for r in stuck:
        logger.info("  stuck: user=%s slug=%s paused=%s",
                    str(r.get("user_id"))[:8], r.get("slug"), r.get("paused"))

    if not apply:
        logger.info("DRY-RUN — pass --apply to rematerialize.")
        return 0

    touched_total = 0
    for uid in user_ids:
        try:
            touched = await materialize_capture_index(client, uid)
            touched_total += touched
            logger.info("rematerialized user=%s rows=%d", uid[:8], touched)
        except Exception as exc:  # noqa: BLE001 — per-user best-effort
            logger.warning("materialize failed user=%s: %s", uid[:8], exc)

    # Post-receipt: how many rows remain NULL (paused rows legitimately stay NULL).
    after = (
        client.table("tasks")
        .select("user_id, slug, next_run_at, paused")
        .eq("kind", "capture")
        .is_("next_run_at", "null")
        .execute()
    ).data or []
    live_after = [r for r in after if not r.get("paused")]
    logger.info(
        "done: %d rows touched; NULL next_run_at now %d (%d active/un-paused)",
        touched_total, len(after), len(live_after),
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(apply="--apply" in sys.argv)))
