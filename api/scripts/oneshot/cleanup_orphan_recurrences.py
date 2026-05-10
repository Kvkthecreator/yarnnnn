"""
One-shot: archive YAML-only orphan recurrences in alpha-trader-2.

Post-Phase-B.2 cleanup. The Phase B.2 migration projected legacy
back-office.yaml entries with executor-name-derived slugs
('signal-evaluation', 'track-universe') because the operator-edited
YAML was unparseable. The operator persona's authored slugs were
always '-2'-suffixed, so the canonical-slug entries never matched
any scheduling-index row and the H.3a (Phase H stale-row sweep on
2026-05-10) deleted the index rows. The YAML entries persisted
as orphans.

This script archives those orphan entries via Schedule(action="archive")
using the same handler the operator uses through the chat surface,
authored_by="system:phaseI-cleanup".

Usage:
    cd api
    python -m scripts.oneshot.cleanup_orphan_recurrences --user-id <UUID>
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
logger = logging.getLogger("orphan_cleanup")


ORPHAN_SLUGS = {"signal-evaluation", "track-universe"}


class _Auth:
    """Minimal auth-shape compatible with handle_schedule."""
    def __init__(self, client, user_id: str):
        self.client = client
        self.user_id = user_id


async def archive_orphans(client, user_id: str, *, dry_run: bool) -> dict:
    from services.primitives.schedule import handle_schedule
    from services.recurrence import walk_workspace_recurrences

    recurrences = walk_workspace_recurrences(client, user_id)
    by_slug = {r.slug: r for r in recurrences}

    summary: dict = {"user_id": user_id, "archived": [], "not_found": [], "dry_run": dry_run}

    for slug in sorted(ORPHAN_SLUGS):
        if slug not in by_slug:
            summary["not_found"].append(slug)
            logger.info("[%s] %s not present in YAML — skipping", user_id[:8], slug)
            continue

        if dry_run:
            logger.info("[%s] DRY RUN — would archive %s", user_id[:8], slug)
            summary["archived"].append(slug)
            continue

        result = await handle_schedule(_Auth(client, user_id), {
            "action": "archive",
            "slug": slug,
            "authored_by": "system:phaseI-cleanup",
        })
        if result.get("success"):
            logger.info("[%s] archived %s", user_id[:8], slug)
            summary["archived"].append(slug)
        else:
            logger.warning("[%s] archive failed for %s: %s", user_id[:8], slug, result)
            summary.setdefault("failures", []).append({"slug": slug, "result": result})

    return summary


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, help="Workspace owner UUID")
    parser.add_argument("--dry-run", action="store_true", help="Compute but don't write")
    args = parser.parse_args()

    from services.supabase import get_service_client
    client = get_service_client()

    summary = await archive_orphans(client, args.user_id, dry_run=args.dry_run)

    print()
    print("=" * 60)
    print("Orphan-recurrence cleanup summary")
    print("=" * 60)
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
