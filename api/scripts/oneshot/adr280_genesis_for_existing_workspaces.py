"""ADR-280 Phase 1 migration: trigger genesis-by-Reviewer for existing workspaces.

Per ADR-280 §8 Phase 1 acceptance: "One-shot migration script triggers
genesis wake for kvk's existing workspace; workspace guide successfully
authored; lock policy correctly enforces `context/trading/*` paths via
workspace-guide route."

Existing workspaces (kvk + seulkim88) were created before ADR-280's
genesis-by-Reviewer flow shipped, so they have no `_workspace_guide.md`.
Today the lock policy gracefully degrades to kernel-defaults +
bundle-substrate_abi fallback (the transitional safety net per ADR-280
§4.1 Phase 1), but the canonical state requires the guide. This script
runs the genesis wake against each existing workspace once.

Idempotent — `services.workspace_guide.read_frontmatter` returns
non-empty for any workspace whose guide already exists; the script
skips and reports.

Usage:
    cd api && python -m scripts.oneshot.adr280_genesis_for_existing_workspaces

Forward-only per the operator's singular-implementation directive — no
dry-run flag, no rollback (Authored Substrate per ADR-209 retains every
revision in-substrate; if the genesis wake authors a guide we don't like,
we revise it via WriteFile; the prior revision remains queryable).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

# Bootstrap: when run as a module the api/ root is on sys.path; when run
# as a script ensure it is.
_API_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

# Load .env if present so SUPABASE_URL / SUPABASE_SERVICE_KEY pick up
try:
    from dotenv import load_dotenv
    load_dotenv(_API_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # Lazy imports — supabase client + workspace machinery come in here so
    # the module file can be inspected for documentation without booting
    # the full kernel.
    from supabase import create_client
    from services import workspace_guide
    from services import bundle_reader
    from services.workspace_init import initialize_workspace

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        logger.error(
            "SUPABASE_URL + SUPABASE_SERVICE_KEY required. "
            "Source .env or export them before running."
        )
        sys.exit(2)

    client = create_client(url, key)

    # Discover all workspaces with at least one Reviewer-substrate file —
    # safer than enumerating auth.users (which we don't need to touch).
    # The presence of /workspace/review/IDENTITY.md indicates a workspace
    # that has been initialized (ADR-194 Phase 4 scaffolds it for every
    # workspace).
    rows = (
        client.table("workspace_files")
        .select("user_id")
        .eq("path", "/workspace/review/IDENTITY.md")
        .execute()
    )
    user_ids = sorted({r["user_id"] for r in (rows.data or [])})
    logger.info(f"Discovered {len(user_ids)} existing workspaces")

    skipped = 0
    succeeded = 0
    failed = 0

    for user_id in user_ids:
        existing = workspace_guide.read_frontmatter(client, user_id)
        if existing:
            logger.info(
                f"  [{user_id[:8]}] already has workspace guide "
                f"(path_zones={len(existing.get('path_zones', []))}) — skipping"
            )
            skipped += 1
            continue

        # Determine if a program is active for this workspace.
        bundles = bundle_reader.bundles_active_for_workspace(user_id, client)
        program_slug = bundles[0]["slug"] if bundles else None
        logger.info(
            f"  [{user_id[:8]}] no guide yet — running genesis "
            f"(program={program_slug or 'none'}, active_bundles={len(bundles)})"
        )

        try:
            # initialize_workspace is idempotent on the deterministic
            # scaffold portion; the genesis wake (Phase 6) is also
            # idempotent (skips if guide exists). Calling the full
            # function ensures we use the singular initialization path
            # rather than re-implementing the genesis call here.
            result = await initialize_workspace(
                client=client,
                user_id=user_id,
                program_slug=program_slug,
            )
            if result.get("workspace_guide_authored"):
                logger.info(
                    f"  [{user_id[:8]}] genesis SUCCEEDED "
                    f"(guide_authored=True)"
                )
                succeeded += 1
            else:
                err = result.get("workspace_guide_error", "unknown reason")
                logger.warning(
                    f"  [{user_id[:8]}] genesis returned but no guide authored: {err}"
                )
                failed += 1
        except Exception as exc:
            logger.error(f"  [{user_id[:8]}] genesis FAILED: {exc}", exc_info=True)
            failed += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info(
        f"Migration summary: {len(user_ids)} workspaces, "
        f"skipped={skipped}, succeeded={succeeded}, failed={failed}"
    )
    logger.info("=" * 60)
    if failed:
        logger.warning(
            "Some workspaces failed — re-run the script (idempotent). "
            "Failed workspaces continue to function via the lock-policy "
            "transitional fallback (kernel-defaults + bundle substrate_abi)."
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
