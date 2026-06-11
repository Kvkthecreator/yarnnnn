"""One-shot soak-hygiene repair (Hat-B): restore alpha-trader-2's track-universe
schedule to bundle-default.

Context (docs/evaluations/longitudinal-soak-alpha-trader-2/TRACKING-LOG.md,
2026-06-11 TENURE-READ + kvk cross-check): on day 1 the alpha-trader-2 Reviewer
made an isolated single-wake judgment slip — it nulled track-universe's
ADR-268 three-snapshot RTH schedule (narrated as "advanced to 09:40", but the
substrate shows `schedule: null`), so the tracker stopped firing during RTH and
the operation read 11-hour-stale snapshots. kvk (same program/canon) is intact,
so this is n=1 fixture corruption, not a system flaw. This script restores the
soak workspace to the schedule the bundle shipped so future tenure reads aren't
confounded by self-inflicted stale data.

This is NOT a system change — it restores operator-shaped substrate to its
bundle-default state, written through the canonical attributed write path
(ADR-209 write_revision) with system:eval-cleanup attribution, matching the
prior stewardship-finding cleanup precedent.

Defensive: verifies the live block is EXACTLY the nulled state before writing;
aborts otherwise (so it can't corrupt a drifted file).

Run:  cd api && ../.venv/bin/python -m scripts.alpha_ops.restore_track_universe_schedule
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

USER_ID = "29a74c63-0c9c-4998-b8bb-56dd0d810a4e"  # alpha-trader-2
PATH = "/workspace/_recurrences.yaml"

# The exact nulled block the day-1 slip produced (must match live, or abort).
NULLED_BLOCK = (
    "- slug: track-universe\n"
    "  schedule: null\n"
    "  mode: mechanical\n"
    "  prompt: '@primitive: TrackUniverse()'\n"
    "  fire_on_activation: true\n"
    "  display_name: Universe Tracker\n"
)

# The restore target — the ADR-268 three-snapshot schedule the bundle ships,
# rendered in the live file's flat format (NOT the bundle's nested-comment
# format — we preserve the live serialization shape, only fix the schedule).
RESTORED_BLOCK = (
    "- slug: track-universe\n"
    "  schedule:\n"
    "  - '@market_open + 15min'\n"
    "  - '@market_open + 3h'\n"
    "  - '@market_close - 1h'\n"
    "  mode: mechanical\n"
    "  prompt: '@primitive: TrackUniverse()'\n"
    "  fire_on_activation: true\n"
    "  display_name: Universe Tracker\n"
)


def _service_client() -> Any:
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL") or "https://noxgqcwynkzqabljjyon.supabase.co"
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        raise SystemExit("SUPABASE_SERVICE_KEY required (load api/.env)")
    return create_client(url, key)


async def main() -> None:
    from services.authored_substrate import write_revision
    from services.scheduling import materialize_scheduling_index

    client = _service_client()

    # 1. Read live content.
    resp = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", USER_ID)
        .eq("path", PATH)
        .single()
        .execute()
    )
    content = resp.data["content"]

    # 2. Defensive: confirm the nulled block is present and the restored block
    #    is NOT already present (idempotency + drift guard).
    if RESTORED_BLOCK in content:
        print("ALREADY RESTORED — track-universe carries the three-snapshot "
              "schedule. No write. (idempotent no-op)")
        return
    if NULLED_BLOCK not in content:
        raise SystemExit(
            "ABORT: the expected nulled track-universe block was not found "
            "verbatim. Live state has drifted from the recorded finding — "
            "inspect manually before any write.\n\n"
            f"Expected block:\n{NULLED_BLOCK}"
        )

    # 3. Surgical replace — only the track-universe block changes.
    new_content = content.replace(NULLED_BLOCK, RESTORED_BLOCK)
    assert new_content != content, "replace produced no change"
    assert new_content.count("slug: track-universe") == 1, "duplicated block"

    # 4. Write through the canonical attributed path (ADR-209).
    rev_id = write_revision(
        client,
        user_id=USER_ID,
        path=PATH,
        content=new_content,
        authored_by="system:eval-cleanup",
        message=(
            "Restore track-universe ADR-268 three-snapshot RTH schedule "
            "(soak-hygiene: revert the isolated day-1 Reviewer schedule-null "
            "slip; TENURE-READ 2026-06-11 finding, kvk-cross-checked n=1)."
        ),
    )
    print(f"WROTE revision: {rev_id}")

    # 5. Re-materialize the scheduling index so tasks.next_run_at recomputes
    #    from the restored schedule (preserves last_run_at).
    rows = await materialize_scheduling_index(client, USER_ID)
    print(f"materialize_scheduling_index: {rows} rows synced")


if __name__ == "__main__":
    asyncio.run(main())
