#!/usr/bin/env python3
"""ADR-267 P&L Unification — Live Workspace Migration (2026-05-12)

Commit 6 of 6 in the P/L unification refactor. Migrates already-forked
live workspaces (alpha-trader, alpha-trader-2, kvk) to the post-Commit-3
`_recurrences.yaml` content that re-grounds Reviewer recurrence prompts
to `_money_truth.md` + `by_signal` block.

Why this script (instead of `activate_persona.py --skip-connect`):

  `_fork_reference_workspace` treats existing files as "operator-customized"
  when they differ from the current bundle, preserving operator content
  (the right default per ADR-209). But that means bundle-source updates
  to non-canon-tier files (like `_recurrences.yaml`, which carries the
  recurrence prompts) don't propagate to live workspaces. Same pattern
  as the A1/A2 drift fixes earlier this session.

The fix: write the bundle's current `_recurrences.yaml` directly via
`write_revision(authored_by="system:bundle-drift-fix")`, then re-
materialize the `tasks` scheduling index so the scheduler picks up the
new content.

Run once after deploying Commits 1-5 to production:

    .venv/bin/python api/scripts/oneshot/adr267_pnl_unification_migration.py

Idempotent: re-running is safe (write_revision is no-op when content
matches; materialize_scheduling_index is idempotent).

Verified outcome: all 3 personas reach 32/32 on verify.py --all after
this script + Alpaca connect.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
sys.path.insert(0, str(_API_ROOT))

REPO_ROOT = _THIS_DIR.parents[2]
BUNDLE_FILE = REPO_ROOT / "docs" / "programs" / "alpha-trader" / "reference-workspace" / "_recurrences.yaml"

# Persona registry — single source of truth in personas.yaml, hardcoded here
# for a one-shot migration so we don't pull in the registry loader.
USER_IDS = [
    ("alpha-trader",   "2be30ac5-b3cf-46b1-aeb8-af39cd351af4"),
    ("alpha-trader-2", "29a74c63-0c9c-4998-b8bb-56dd0d810a4e"),
    ("kvk",            "2abf3f96-118b-4987-9d95-40f2d9be9a18"),
]


async def main() -> int:
    if not BUNDLE_FILE.exists():
        print(f"ERROR: bundle file not found: {BUNDLE_FILE}", file=sys.stderr)
        return 1

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        print(
            "ERROR: SUPABASE_URL + SUPABASE_SERVICE_KEY required in env "
            "(source .env first).",
            file=sys.stderr,
        )
        return 1

    from supabase import create_client
    from services.scheduling import materialize_scheduling_index
    from services.workspace import UserMemory

    client = create_client(supabase_url, supabase_key)
    new_body = BUNDLE_FILE.read_text()

    print(f"Bundle source: {BUNDLE_FILE.relative_to(REPO_ROOT)} ({len(new_body)} chars)")
    print()

    for label, user_id in USER_IDS:
        um = UserMemory(client, user_id)
        existing = await um.read("_recurrences.yaml")
        if existing == new_body:
            print(f"NO-OP   {label}: already at bundle content")
        else:
            await um.write(
                "_recurrences.yaml",
                new_body,
                authored_by="system:bundle-drift-fix",
                message=(
                    "ADR-267 P&L unification — re-ground recurrence prompts "
                    "to _money_truth.md + by_signal"
                ),
            )
            old_len = len(existing or "")
            print(f"WROTE   {label}: _recurrences.yaml ({old_len} -> {len(new_body)} chars)")

        # Always re-materialize: the write may have inserted/dropped/paused
        # recurrences; the index must reflect the YAML truth.
        count = await materialize_scheduling_index(client, user_id)
        print(f"        index materialized: {count} recurrences")
        print()

    print("Migration complete. Run verify.py --all to confirm 32/32 per persona.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
