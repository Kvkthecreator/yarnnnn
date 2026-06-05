"""ADR-280 Phase 1 (revised §D4) migration: seed workspace guides for existing workspaces.

Per the revised §D4 (workspace guide is bundle-shipped operator-canon, not
Reviewer-authored at first wake), existing workspaces (kvk + seulkim88 +
others) need their `_workspace_guide.md` populated. New workspaces created
post-ADR-280 get this automatically via `workspace_init.py` Phase 2 (kernel
default) + `services.programs.fork_reference_workspace` (bundle override
when a program is activated). Existing workspaces predate this and need a
one-shot backfill.

For each existing workspace:
  - If a program is active (alpha-trader connection, alpha-commerce, etc.),
    seed the bundle's `reference-workspace/_workspace_guide.md` content.
  - If no program is active, seed `DEFAULT_WORKSPACE_GUIDE_MD` from
    `services.orchestration`.

Writes go through `services.authored_substrate.write_revision` with
`authored_by="system:bundle-fork"` (bundle case) or `system:workspace-init`
(no-program case) — same attribution every other forked / kernel-seeded
file uses. Idempotent: skipped if the workspace already has a guide.

Pure deterministic Python — no LLM calls. ~10s end-to-end for 5 workspaces.

Usage:
    cd api && python -m scripts.oneshot.adr280_seed_workspace_guides
"""

from __future__ import annotations

import asyncio
import logging
import os
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


_REPO_ROOT = _API_ROOT.parent


def _read_bundle_guide(slug: str) -> str | None:
    """Read a bundle's reference-workspace/_workspace_guide.md from disk."""
    p = _REPO_ROOT / "docs" / "programs" / slug / "reference-workspace" / "_workspace_guide.md"
    if not p.exists():
        return None
    return p.read_text()


async def main():
    from supabase import create_client
    from services import workspace_guide
    from services import bundle_reader
    from services.authored_substrate import write_revision
    from services.orchestration import DEFAULT_WORKSPACE_GUIDE_MD

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        logger.error(
            "SUPABASE_URL + SUPABASE_SERVICE_KEY required. Source .env or export."
        )
        sys.exit(2)

    client = create_client(url, key)

    # Discover workspaces with a Reviewer IDENTITY (signal of initialized workspace).
    rows = (
        client.table("workspace_files")
        .select("user_id")
        .eq("path", "/workspace/persona/IDENTITY.md")
        .execute()
    )
    user_ids = sorted({r["user_id"] for r in (rows.data or [])})
    logger.info(f"Discovered {len(user_ids)} existing workspaces")

    skipped = 0
    seeded_bundle = 0
    seeded_default = 0
    failed = 0

    for user_id in user_ids:
        existing = workspace_guide.read_frontmatter(client, user_id)
        if existing:
            logger.info(
                f"  [{user_id[:8]}] already has workspace guide — skipping"
            )
            skipped += 1
            continue

        # Determine active program (if any).
        bundles = bundle_reader.bundles_active_for_workspace(user_id, client)
        program_slug = bundles[0]["slug"] if bundles else None

        try:
            if program_slug:
                content = _read_bundle_guide(program_slug)
                if content is None:
                    logger.warning(
                        f"  [{user_id[:8]}] active program '{program_slug}' "
                        f"but bundle ships no _workspace_guide.md — falling back to kernel default"
                    )
                    content = DEFAULT_WORKSPACE_GUIDE_MD
                    authored_by = "system:workspace-init"
                    message = "Workspace guide — kernel default (bundle ships no guide)"
                else:
                    authored_by = "system:bundle-fork"
                    message = f"Workspace guide — forked from {program_slug} bundle"
            else:
                content = DEFAULT_WORKSPACE_GUIDE_MD
                authored_by = "system:workspace-init"
                message = "Workspace guide — kernel default (no program activated)"

            # Use the canonical authored-substrate write path per ADR-209.
            write_revision(
                client,
                user_id=user_id,
                path="/workspace/_workspace_guide.md",
                content=content,
                authored_by=authored_by,
                message=message,
                summary="Workspace guide (ADR-280 §D4 revised)",
                tags=["workspace_guide", "operator-canon", "adr-280"],
                lifecycle="active",
                content_type="text/markdown",
            )

            # Verify.
            check = workspace_guide.read_frontmatter(client, user_id)
            if check.get("schema_version") == 1:
                if program_slug:
                    seeded_bundle += 1
                    logger.info(
                        f"  [{user_id[:8]}] SEEDED ({program_slug} bundle, "
                        f"{len(check.get('path_zones', []))} path zones)"
                    )
                else:
                    seeded_default += 1
                    logger.info(
                        f"  [{user_id[:8]}] SEEDED (kernel default, "
                        f"{len(check.get('path_zones', []))} path zones)"
                    )
            else:
                failed += 1
                logger.error(
                    f"  [{user_id[:8]}] WRITE SUCCEEDED but frontmatter parse failed"
                )

        except Exception as exc:
            logger.error(f"  [{user_id[:8]}] FAILED: {exc}", exc_info=True)
            failed += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info(
        f"Migration summary: {len(user_ids)} workspaces — "
        f"skipped={skipped}, seeded_bundle={seeded_bundle}, "
        f"seeded_default={seeded_default}, failed={failed}"
    )
    logger.info("=" * 60)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
