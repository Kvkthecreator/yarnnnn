"""ADR-286 migration: purge kernel-default content at bundle-owned paths.

Pre-ADR-286 the kernel scaffold at `workspace_init` Phase 2 wrote default
content for 10 paths that the alpha-trader bundle ALSO ships. When the
bundle activated later via `fork_reference_workspace`, the fork's
`is_skeleton_content` check failed to recognize the kernel default as
"should-be-replaced" (the kernel default had substantive prose), so the
fork skipped to preserve "operator-customized content" — which was
actually kernel-default content masquerading as operator-customized.

Result observed on kvk's workspace 2026-05-17:
  - `review/IDENTITY.md` stuck on 2354-byte kernel default (bundle ships 5270)
  - `_shared/AUTONOMY.md` stuck on 3132-byte kernel default (bundle ships 5309)
  - `review/principles.md` stuck on pre-Phase-2 content (bundle ships 9467)

This migration walks each alpha workspace, reads each bundle-owned path,
checks if content matches the pre-ADR-286 kernel default (deterministic
constant comparison), and deletes the row if matched. Subsequent re-fork
populates fresh from bundle.

Per ADR-286 D8 — pre-users, one-shot. Run once, then archive.

Usage:
  python -m scripts.oneshot.adr286_purge_dual_write_kernel_defaults
    [--user-id <uuid>]        # purge specific workspace
    [--all-alpha-trader]      # walk all alpha-trader workspaces
    [--dry-run]               # report what would be deleted, don't write
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("adr286_purge")

# Bundle-owned paths per ADR-286 D3 (alpha-trader inventory).
# Future bundles add their own paths; this migration is alpha-trader-scoped
# because alpha-trader is the only program with pre-ADR-286 workspaces.
BUNDLE_OWNED_PATHS = [
    "/workspace/context/_shared/MANDATE.md",
    "/workspace/context/_shared/IDENTITY.md",
    "/workspace/context/_shared/BRAND.md",
    "/workspace/context/_shared/AUTONOMY.md",
    "/workspace/context/_shared/_autonomy.yaml",
    "/workspace/memory/awareness.md",
    "/workspace/review/IDENTITY.md",
    "/workspace/review/principles.md",
    "/workspace/_workspace_guide.md",
]


def _load_kernel_defaults() -> dict[str, str]:
    """Pre-ADR-286 kernel default text per path. Constants from orchestration.py."""
    from services.orchestration import (
        DEFAULT_IDENTITY_MD,
        DEFAULT_BRAND_MD,
        DEFAULT_AUTONOMY_MD,
        DEFAULT_AWARENESS_MD,
        DEFAULT_REVIEW_IDENTITY_MD,
        DEFAULT_REVIEW_PRINCIPLES_MD,
        DEFAULT_WORKSPACE_GUIDE_MD,
    )

    # Pre-ADR-286 _autonomy.yaml default — inline string from workspace_init
    DEFAULT_AUTONOMY_YAML = (
        "# _autonomy.yaml — delegation declaration (ADR-254 + Commit F 2026-05-11)\n"
        "# Machine-parsed by review_policy + working_memory. See AUTONOMY.md for prose docs.\n"
        "# Schema:\n"
        "#   default:\n"
        "#     delegation: manual | bounded | autonomous   (canonical 3-value enum)\n"
        "#     ceiling_cents: <int>  (required when delegation=bounded)\n"
        "#     never_auto: [<action_type>, ...]  (always route to operator)\n"
        "#   paused_until: <ISO timestamp>  (set by Reviewer / operator, ADR-248 D3)\n\n"
        "default:\n"
        "  delegation: manual\n"
        "  # ceiling_cents: 0       # uncomment + set when promoting to bounded\n"
        "  # never_auto: []         # action types that always require operator click\n"
    )

    # Pre-ADR-286 mandate skeleton (inline in workspace_init)
    DEFAULT_MANDATE_MD = (
        "# Mandate\n\n"
        "<!-- This file declares what this workspace is running.\n"
        "     Authored via YARNNN conversation at first use; revised when\n"
        "     the operator decides. No forced revision cadence. -->\n\n"
        "## Primary Action\n"
        "_<not yet declared — talk to YARNNN to author your mandate>_\n\n"
        "## Success Criteria\n\n"
        "## Boundary Conditions\n"
    )

    return {
        "/workspace/context/_shared/MANDATE.md": DEFAULT_MANDATE_MD,
        "/workspace/context/_shared/IDENTITY.md": DEFAULT_IDENTITY_MD,
        "/workspace/context/_shared/BRAND.md": DEFAULT_BRAND_MD,
        "/workspace/context/_shared/AUTONOMY.md": DEFAULT_AUTONOMY_MD,
        "/workspace/context/_shared/_autonomy.yaml": DEFAULT_AUTONOMY_YAML,
        "/workspace/memory/awareness.md": DEFAULT_AWARENESS_MD,
        "/workspace/review/IDENTITY.md": DEFAULT_REVIEW_IDENTITY_MD,
        "/workspace/review/principles.md": DEFAULT_REVIEW_PRINCIPLES_MD,
        "/workspace/_workspace_guide.md": DEFAULT_WORKSPACE_GUIDE_MD,
    }


async def purge_workspace(
    client, user_id: str, dry_run: bool = False, alpha_rewrite_all: bool = False
) -> dict:
    """Walk bundle-owned paths for one workspace; delete kernel-default content.

    When `alpha_rewrite_all=True`: deletes ALL bundle-owned paths regardless of
    kernel-default match — appropriate for alpha workspaces where there's no
    real operator content yet AND the bundle has evolved since last fork
    (e.g., Phase 2 amendments to principles.md, IDENTITY.md). Subsequent
    re-fork writes the current bundle content cleanly.
    """
    defaults = _load_kernel_defaults()
    deleted: list[str] = []
    preserved: list[str] = []
    absent: list[str] = []

    for path in BUNDLE_OWNED_PATHS:
        # Read live content
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
        if not res.data:
            absent.append(path)
            continue

        live = res.data[0]["content"] or ""
        default = defaults.get(path, "")

        # Compare against pre-ADR-286 kernel default.
        # Use rstrip to ignore trailing whitespace differences (DB may strip).
        matches_default = live.rstrip() == default.rstrip()

        should_delete = matches_default or alpha_rewrite_all
        reason = "kernel-default match" if matches_default else "alpha-rewrite-all (bundle evolved since last fork)"

        if should_delete:
            if dry_run:
                logger.info(f"  [DRY-RUN] would delete {path} ({len(live)} bytes, {reason})")
            else:
                # Delete the workspace_files row + cascade revisions per ADR-209.
                # Per ADR-286 D8 the bundle-fork will re-author cleanly.
                client.table("workspace_files").delete().eq("user_id", user_id).eq("path", path).execute()
                # Also delete revision rows for clean re-author attribution chain.
                client.table("workspace_file_versions").delete().eq("user_id", user_id).eq("path", path).execute()
                logger.info(f"  DELETED {path} ({len(live)} bytes, {reason})")
            deleted.append(path)
        else:
            preserved.append(path)
            logger.info(f"  PRESERVED {path} ({len(live)} bytes, operator-edited or post-ADR-286 bundle-shaped)")

    return {
        "user_id": user_id,
        "deleted": deleted,
        "preserved": preserved,
        "absent": absent,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="ADR-286 purge dual-write kernel defaults")
    parser.add_argument("--user-id", help="Specific workspace user_id")
    parser.add_argument("--all-alpha-trader", action="store_true", help="Walk all alpha-trader workspaces")
    parser.add_argument("--dry-run", action="store_true", help="Report only; don't write")
    parser.add_argument(
        "--alpha-rewrite-all",
        action="store_true",
        help="Delete all bundle-owned paths regardless of kernel-default match (alpha-stage; no real operator content to preserve)",
    )
    args = parser.parse_args()

    if not args.user_id and not args.all_alpha_trader:
        parser.error("Pass --user-id <uuid> or --all-alpha-trader")

    from services.supabase import get_service_client
    client = get_service_client()

    user_ids: list[str] = []
    if args.user_id:
        user_ids = [args.user_id]
    else:
        # Walk personas.yaml for alpha-trader workspace ids
        from scripts.alpha_ops._shared import load_registry
        reg = load_registry()
        user_ids = [p.user_id for p in reg.personas if p.program == "alpha-trader"]
        logger.info(f"Found {len(user_ids)} alpha-trader workspaces")

    summaries = []
    for uid in user_ids:
        logger.info(f"[{uid[:8]}] purging kernel defaults (alpha_rewrite_all={args.alpha_rewrite_all})")
        summary = await purge_workspace(
            client, uid, dry_run=args.dry_run, alpha_rewrite_all=args.alpha_rewrite_all
        )
        summaries.append(summary)

    print()
    print("=" * 60)
    print("ADR-286 purge summary")
    print("=" * 60)
    for s in summaries:
        print(f"  {s['user_id'][:8]}: deleted={len(s['deleted'])} preserved={len(s['preserved'])} absent={len(s['absent'])}")
        for p in s["deleted"]:
            print(f"    - {p}")


if __name__ == "__main__":
    asyncio.run(main())
