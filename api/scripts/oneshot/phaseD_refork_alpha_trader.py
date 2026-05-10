"""
Phase D.3 — Live re-fork of the updated alpha-trader bundle.

Per ADR-261 D6 + ADR-262 D6 the bundle now ships:
  - /workspace/_recurrences.yaml (canonical, replaces 6 per-shape files)
  - /workspace/specs/{ticker-snapshot, performance-rollup,
    pre-market-brief, weekly-performance-review,
    quarterly-signal-audit}.md (operator-authored output specs cited by
    recurrence prompts)
  - 10 stripped-frontmatter authored substrate files (MANDATE, IDENTITY,
    BRAND, AUTONOMY, principles, _operator_profile, _risk, etc.)

The fork rule (per services.programs.fork_reference_workspace):
  - File missing in operator's workspace → write bundle copy
  - File exists but skeleton (operator hasn't customized) → write bundle
    copy
  - File exists and operator-customized → skip

Usage:
    cd api
    python -m scripts.oneshot.phaseD_refork_alpha_trader --user-id <UUID>
    python -m scripts.oneshot.phaseD_refork_alpha_trader --all-alpha-trader
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
logger = logging.getLogger("phaseD_refork")


async def refork_user(client, user_id: str) -> dict:
    from services.programs import fork_reference_workspace

    logger.info("[%s] starting alpha-trader re-fork", user_id[:8])
    summary = await fork_reference_workspace(client, user_id, "alpha-trader")
    logger.info(
        "[%s] re-fork complete: wrote %d files, skipped %d",
        user_id[:8],
        len(summary.get("files_written", [])),
        len(summary.get("files_skipped", [])),
    )
    return summary


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", help="Re-fork one user (UUID)")
    parser.add_argument(
        "--all-alpha-trader",
        action="store_true",
        help="Re-fork every workspace that has the alpha-trader marker on MANDATE.md",
    )
    args = parser.parse_args()

    if not args.user_id and not args.all_alpha_trader:
        parser.error("provide either --user-id or --all-alpha-trader")

    from services.supabase import get_service_client
    client = get_service_client()

    user_ids: list[str] = []
    if args.user_id:
        user_ids = [args.user_id]
    else:
        rows = (
            client.table("workspace_files")
            .select("user_id,content")
            .eq("path", "/workspace/_shared/MANDATE.md")
            .execute()
        ).data or []
        for r in rows:
            content = r.get("content") or ""
            if "alpha-trader" in content.lower():
                user_ids.append(r["user_id"])
        user_ids = sorted(set(user_ids))
        logger.info("Found %d alpha-trader workspaces", len(user_ids))

    summaries = []
    for uid in user_ids:
        try:
            s = await refork_user(client, uid)
            summaries.append({"user_id": uid, **s})
        except Exception as e:
            logger.exception("[%s] re-fork FAILED: %s", uid[:8], e)
            summaries.append({"user_id": uid, "error": str(e)})

    print()
    print("=" * 60)
    print("Re-fork summary")
    print("=" * 60)
    for s in summaries:
        uid = s.get("user_id", "?")[:8]
        if "error" in s:
            print(f"  {uid}: FAILED — {s['error']}")
        else:
            print(
                f"  {uid}: wrote={len(s.get('files_written', []))} "
                f"skipped={len(s.get('files_skipped', []))}"
            )
            for f in s.get("files_written", []):
                print(f"    + {f}")


if __name__ == "__main__":
    asyncio.run(main())
