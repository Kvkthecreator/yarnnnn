"""ADR-383 amendment (2026-07-02): backfill the steward `_autonomy.yaml`.

Autonomy was pulled OUT of the kernel seed by ADR-286 D3 (a kernel-written
`_autonomy.yaml` blocked bundle-fork overwrite — the pre-marker dual-write bug),
and the ADR-286 purge script (`adr286_purge_dual_write_kernel_defaults.py`)
DELETED it from existing workspaces. It was never put back for no-program
(bare-Freddie) workspaces, so they 404 on
`GET /api/workspace/file?path=/workspace/governance/_autonomy.yaml`. The FE
top-bar Freddie chip issues that GET on every page load → repeated 404 noise.

ADR-383's STEWARD_DEFAULT_MARKER mechanism resolves the original dual-write
objection (a marked default is overwrite-eligible, so a later program-fork
cleanly replaces it). This ADR-383 amendment adds `_autonomy.yaml` to the
kernel steward-seed set at `workspace_init` Phase 2 — new no-program workspaces
now get it. This one-shot backfills the EXISTING no-program workspaces so they
match: it writes the steward-default `DEFAULT_AUTONOMY_YAML` to any workspace
that is (a) missing the file AND (b) not running a program.

WHY ONLY NO-PROGRAM WORKSPACES: a program-activated workspace's `_autonomy.yaml`
is bundle-owned (the fork writes the program's tuned delegation). We must NOT
overwrite a bundle's autonomy with the generic steward default. The gate is
`resolve_active_program_slug(MANDATE.md)` — if a program is active, we skip.

SAFETY: idempotent (skips workspaces that already have the file — never
overwrites existing content, program or operator-authored). The steward default
is `delegation: manual` — the same fail-closed posture the gate already applies
when the file is absent, so behavior does not change; the file just makes the
posture legible as substrate and stops the FE 404.

TOPOLOGY NOTE: `governance/` is a locked GRANT root (ADR-366) — no runtime
caller (Freddie/agent/MCP) may write it; only the operator or a kernel/init
writer. This backfill runs out-of-band with the service client + writes with
`authored_by="system:steward-seed"` (an init-class author, the same class the
kernel scaffold uses), which is the legal writer for a kernel-seeded default.

Per ADR-383 §7 — pre-users, one-shot. Run once, then archive.

Usage:
  python -m scripts.oneshot.adr383_backfill_steward_autonomy_yaml
    [--user-id <uuid>]   # backfill one workspace
    [--all]              # walk every workspace
    [--dry-run]          # report what would be written, don't write
"""
from __future__ import annotations

import argparse
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("adr383_backfill_autonomy")

AUTONOMY_PATH = "/workspace/governance/_autonomy.yaml"
MANDATE_PATH = "/workspace/constitution/MANDATE.md"
# The init-class author. governance/ is a locked GRANT root (ADR-366); a
# kernel-seeded steward default is written by the init/system writer, not a
# runtime caller. Mirrors the attribution the Phase-2 scaffold uses.
STEWARD_SEED_AUTHOR = "system:steward-seed"


def _read_content(client, user_id: str, path: str) -> str | None:
    res = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", user_id)
        .eq("path", path)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return res.data[0].get("content")


def backfill_workspace(client, user_id: str, dry_run: bool = False) -> dict:
    """Write the steward autonomy default IFF the workspace is no-program and
    is missing the file. Idempotent — never overwrites existing content."""
    from services.orchestration import DEFAULT_AUTONOMY_YAML
    from services.programs import resolve_hired_program_slug  # ADR-414 D5
    from services.authored_substrate import write_revision

    result = {"user_id": user_id, "action": None, "reason": None}

    # (b) skip program-activated workspaces — their _autonomy.yaml is bundle-owned.
    mandate = _read_content(client, user_id, MANDATE_PATH)
    program_slug = resolve_hired_program_slug(user_id)  # ADR-414 D5 (was: mandate)
    if program_slug:
        result["action"] = "skip"
        result["reason"] = f"program active ({program_slug}) — autonomy is bundle-owned"
        return result

    # (a) skip if the file already exists — never overwrite.
    existing = _read_content(client, user_id, AUTONOMY_PATH)
    if existing is not None:
        result["action"] = "skip"
        result["reason"] = f"already present ({len(existing)} bytes)"
        return result

    if dry_run:
        result["action"] = "would-write"
        result["reason"] = f"no-program + absent → would seed {len(DEFAULT_AUTONOMY_YAML)} bytes"
        return result

    write_revision(
        client,
        user_id=user_id,
        path=AUTONOMY_PATH,
        content=DEFAULT_AUTONOMY_YAML,
        authored_by=STEWARD_SEED_AUTHOR,
        message="ADR-383 amend backfill: steward autonomy default (delegation: manual)",
        summary="Steward autonomy — the system agent's delegation posture (ADR-383 amend)",
    )
    result["action"] = "written"
    result["reason"] = f"seeded {len(DEFAULT_AUTONOMY_YAML)} bytes (delegation: manual)"
    return result


async def main() -> None:
    parser = argparse.ArgumentParser(description="ADR-383 backfill steward _autonomy.yaml")
    parser.add_argument("--user-id", help="Specific workspace user_id")
    parser.add_argument("--all", action="store_true", help="Walk every workspace")
    parser.add_argument("--dry-run", action="store_true", help="Report only; don't write")
    args = parser.parse_args()

    if not args.user_id and not args.all:
        parser.error("Pass --user-id <uuid> or --all")

    from services.supabase import get_service_client
    client = get_service_client()

    if args.user_id:
        user_ids = [args.user_id]
    else:
        # Distinct user_ids that have any workspace_files row.
        res = client.table("workspace_files").select("user_id").execute()
        user_ids = sorted({r["user_id"] for r in (res.data or [])})
        logger.info(f"Found {len(user_ids)} workspaces")

    summaries = []
    for uid in user_ids:
        summary = backfill_workspace(client, uid, dry_run=args.dry_run)
        logger.info(f"[{uid[:8]}] {summary['action']}: {summary['reason']}")
        summaries.append(summary)

    print()
    print("=" * 60)
    print("ADR-383 autonomy backfill summary" + (" (DRY-RUN)" if args.dry_run else ""))
    print("=" * 60)
    counts: dict[str, int] = {}
    for s in summaries:
        counts[s["action"]] = counts.get(s["action"], 0) + 1
    for action, n in sorted(counts.items()):
        print(f"  {action}: {n}")


if __name__ == "__main__":
    asyncio.run(main())
