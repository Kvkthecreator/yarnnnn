"""
One-shot: tombstone the orphan /agents/system-agent/AGENT.md rows (ADR-457 P3).

These rows were seeded by the pre-ADR-414 era's agent-row creation path
(a "system-agent" agents-row whose workspace seed wrote AGENT.md at the
/agents/{slug}/ prefix). ADR-414 D3 retired the row concept and pure genesis
(D4) stopped all seeding; the files have had no live writer since 2026-07-04
(verified: max(created_at) predates the ADR-414 landing). They are the only
substrate rows stored OUTSIDE the /workspace/ prefix, where the Files tree
cannot legibly present them (the 2026-07-14 stress-test finding).

Deletion is attributed and reversible: delete_live_file writes a tombstone
revision carrying the content, so the chain records who/when/why and
revert-as-write can restore.

Usage:
    cd api
    python -m scripts.oneshot.adr457_tombstone_orphan_agent_files            # dry run
    python -m scripts.oneshot.adr457_tombstone_orphan_agent_files --execute  # apply
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("adr457_orphan_cleanup")

ORPHAN_PATH = "/agents/system-agent/AGENT.md"
AUTHORED_BY = "system:adr457-hygiene"
MESSAGE = (
    "ADR-457 P3 hygiene: tombstone the pre-ADR-414 system-agent AGENT.md orphan "
    "(no live writer since pure genesis; stored outside the /workspace/ prefix)."
)


async def run(execute: bool) -> int:
    from services.supabase import get_service_client
    from services.authored_substrate import delete_live_file

    client = get_service_client()

    rows = (
        client.table("workspace_files")
        .select("id, user_id, workspace_id, path")
        .eq("path", ORPHAN_PATH)
        .execute()
    ).data or []

    print(f"found {len(rows)} live row(s) at {ORPHAN_PATH}")
    if not rows:
        return 0

    tombstoned = 0
    for row in rows:
        uid = row["user_id"]
        ws = row.get("workspace_id")
        if not execute:
            print(f"  DRY RUN would tombstone user={uid[:8]} ws={str(ws)[:8]}")
            continue
        rev_id = delete_live_file(
            client,
            user_id=uid,
            path=ORPHAN_PATH,
            authored_by=AUTHORED_BY,
            message=MESSAGE,
            workspace_id=ws,
        )
        if rev_id:
            tombstoned += 1
            print(f"  tombstoned user={uid[:8]} ws={str(ws)[:8]} rev={rev_id}")
        else:
            print(f"  no live row (raced?) user={uid[:8]}")

    print(f"done: {tombstoned}/{len(rows)} tombstoned" if execute else "dry run complete")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="apply (default: dry run)")
    args = parser.parse_args()
    return asyncio.run(run(execute=args.execute))


if __name__ == "__main__":
    sys.exit(main())
