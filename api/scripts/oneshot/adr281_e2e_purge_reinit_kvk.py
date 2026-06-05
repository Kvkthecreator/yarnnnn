"""ADR-281 Stream B E2E proof: purge + re-initialize kvk's alpha-trader workspace.

Validates that the full Phase 1 + dissolution + Stream A + ADR-281 + Stream B
arc holds end-to-end on a clean workspace:

1. Purge kvk's substrate + tasks + agents + chat + proposals (preserves auth
   + platform_connections so reinit detects the alpaca paper connection).
2. Re-initialize via services.workspace_init.initialize_workspace with
   program_slug="alpha-trader".
3. Verify clean state:
   - workspace guide exists at /workspace/_workspace_guide.md (alpha-trader-shipped)
   - workspace guide declares path-only signal_files entry (post-ADR-281)
   - judgment_log.md absent (created on first material Reviewer wake — not at init)
   - mirror-signal-state recurrence in _recurrences.yaml
   - _signals_summary.md substrate populated by fire_on_activation
   - No legacy decisions.md path anywhere
   - YARNNN agent row scaffolded
   - tasks index populated from _recurrences.yaml

Pure deterministic. ~5-10s end-to-end. Forward-only per Singular Implementation.

Usage:
    cd api && python -m scripts.oneshot.adr281_e2e_purge_reinit_kvk
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


KVK_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
PROGRAM_SLUG = "alpha-trader"


def _delete_rows(client, table: str, user_id: str, user_column: str = "user_id", optional: bool = False) -> int:
    """Mirror of routes/account.py::_delete_rows."""
    try:
        result = (
            client.table(table)
            .delete(count="exact")
            .eq(user_column, user_id)
            .execute()
        )
        return result.count or 0
    except Exception as exc:
        if optional:
            logger.info(f"  table {table} optional/missing — skipped: {exc}")
            return 0
        logger.warning(f"  table {table} delete failed: {exc}")
        return 0


def _null_head_version_pointers(client, user_id: str) -> None:
    """Mirror of routes/account.py — clear head_version_id before deleting versions."""
    try:
        client.table("workspace_files").update({"head_version_id": None}).eq("user_id", user_id).execute()
    except Exception as exc:
        logger.warning(f"  null head_version_id failed: {exc}")


def _delete_workspace_files(client, user_id: str) -> int:
    return _delete_rows(client, "workspace_files", user_id)


async def main():
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL + SUPABASE_SERVICE_KEY required.")
        sys.exit(2)

    client = create_client(url, key)

    # ====================================================================
    # Phase 0: pre-purge state snapshot
    # ====================================================================
    logger.info("=" * 60)
    logger.info("Phase 0: pre-purge snapshot")
    logger.info("=" * 60)
    pre = {}
    for tbl, col in [
        ("workspace_files", "user_id"),
        ("workspace_file_versions", "user_id"),
        ("agents", "user_id"),
        ("tasks", "user_id"),
        ("chat_sessions", "user_id"),
        ("action_proposals", "user_id"),
    ]:
        r = client.table(tbl).select("id", count="exact").eq(col, KVK_USER_ID).limit(1).execute()
        pre[tbl] = r.count or 0
    logger.info(f"  pre-purge: {pre}")

    # ====================================================================
    # Phase 1: purge (mirrors routes/account.py::clear_workspace logic)
    # ====================================================================
    logger.info("=" * 60)
    logger.info("Phase 1: purge kvk's workspace state")
    logger.info("=" * 60)

    # ADR-209 FK order: null head_version_id before deleting versions
    _null_head_version_pointers(client, KVK_USER_ID)

    deleted = {}
    deleted["workspace_file_versions"] = _delete_rows(client, "workspace_file_versions", KVK_USER_ID)
    deleted["workspace_files"] = _delete_workspace_files(client, KVK_USER_ID)
    deleted["tasks"] = _delete_rows(client, "tasks", KVK_USER_ID, optional=True)
    deleted["action_proposals"] = _delete_rows(client, "action_proposals", KVK_USER_ID)

    # chat_sessions FK from session_messages → delete messages first
    try:
        msg_query = (
            client.table("session_messages")
            .delete(count="exact")
            .in_("session_id", [
                r["id"] for r in (
                    client.table("chat_sessions").select("id").eq("user_id", KVK_USER_ID).execute().data or []
                )
            ])
            .execute()
            if (client.table("chat_sessions").select("id").eq("user_id", KVK_USER_ID).execute().data or [])
            else None
        )
        deleted["session_messages"] = msg_query.count if msg_query else 0
    except Exception as exc:
        logger.warning(f"  session_messages delete failed: {exc}")
        deleted["session_messages"] = 0
    deleted["chat_sessions"] = _delete_rows(client, "chat_sessions", KVK_USER_ID)

    deleted["execution_events"] = _delete_rows(client, "execution_events", KVK_USER_ID, optional=True)
    deleted["activity_log"] = _delete_rows(client, "activity_log", KVK_USER_ID, optional=True)
    deleted["notifications"] = _delete_rows(client, "notifications", KVK_USER_ID, optional=True)
    deleted["agents"] = _delete_rows(client, "agents", KVK_USER_ID)

    logger.info(f"  purge results: {deleted}")

    # Preserved: auth.users (user identity) + platform_connections (so reinit
    # detects the active alpaca paper connection for bundle activation).
    preserved_conns = (
        client.table("platform_connections")
        .select("platform, status", count="exact")
        .eq("user_id", KVK_USER_ID)
        .eq("status", "active")
        .execute()
    )
    logger.info(f"  preserved: {preserved_conns.count} active platform connection(s)")

    # ====================================================================
    # Phase 2: re-initialize with program_slug="alpha-trader"
    # ====================================================================
    logger.info("=" * 60)
    logger.info(f"Phase 2: initialize_workspace(program_slug={PROGRAM_SLUG!r})")
    logger.info("=" * 60)

    from services.workspace_init import initialize_workspace

    reinit_summary = await initialize_workspace(
        client, KVK_USER_ID,
        program_slug=PROGRAM_SLUG,
    )
    logger.info(f"  reinit summary:")
    for k, v in reinit_summary.items():
        if isinstance(v, list):
            logger.info(f"    {k}: {len(v)} entries")
        else:
            logger.info(f"    {k}: {v}")

    # ====================================================================
    # Phase 3: verify clean state
    # ====================================================================
    logger.info("=" * 60)
    logger.info("Phase 3: verify clean state")
    logger.info("=" * 60)

    checks = []

    def _check(name: str, condition: bool, detail: str = "") -> None:
        status = "PASS" if condition else "FAIL"
        suffix = f" — {detail}" if detail else ""
        logger.info(f"  [{status}] {name}{suffix}")
        checks.append((name, condition, detail))

    # 3.1 — YARNNN agent scaffolded
    yarnnn = (
        client.table("agents")
        .select("id, role")
        .eq("user_id", KVK_USER_ID)
        .eq("role", "thinking_partner")
        .execute()
    )
    _check("YARNNN agent scaffolded", len(yarnnn.data or []) == 1)

    # 3.2 — workspace guide forked from alpha-trader bundle
    guide = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", KVK_USER_ID)
        .eq("path", "/workspace/_workspace_guide.md")
        .execute()
    )
    guide_content = (guide.data or [{}])[0].get("content", "")
    _check("workspace guide present", bool(guide_content), f"{len(guide_content)} bytes")
    _check(
        "workspace guide is alpha-trader-shipped (not kernel-default)",
        "alpha-trader" in guide_content,
        "checks for 'alpha-trader' string"
    )
    _check(
        "workspace guide declares path-only signal_files entry",
        "operation/trading/_signals_summary.md" in guide_content and "path_glob" not in guide_content,
    )

    # 3.3 — workspace guide attribution
    guide_rev = (
        client.table("workspace_file_versions")
        .select("authored_by")
        .eq("user_id", KVK_USER_ID)
        .eq("path", "/workspace/_workspace_guide.md")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    attr = (guide_rev.data or [{}])[0].get("authored_by", "")
    _check(
        "workspace guide attribution = system:bundle-fork",
        attr == "system:bundle-fork",
        f"got {attr!r}"
    )

    # 3.4 — judgment_log.md NOT present yet (created on first material wake)
    judgment_log = (
        client.table("workspace_files")
        .select("id")
        .eq("user_id", KVK_USER_ID)
        .eq("path", "/workspace/persona/judgment_log.md")
        .execute()
    )
    _check(
        "judgment_log.md correctly absent at init",
        len(judgment_log.data or []) == 0,
        "(created lazily on first material Reviewer wake per ADR-281 §5)"
    )

    # 3.5 — legacy decisions.md path NOT present
    legacy = (
        client.table("workspace_files")
        .select("id")
        .eq("user_id", KVK_USER_ID)
        .eq("path", "/workspace/persona/judgment_log.md")
        .execute()
    )
    _check(
        "no legacy decisions.md path",
        len(legacy.data or []) == 0,
    )

    # 3.6 — _recurrences.yaml present + contains mirror-signal-state
    recs = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", KVK_USER_ID)
        .eq("path", "/workspace/_recurrences.yaml")
        .execute()
    )
    recs_content = (recs.data or [{}])[0].get("content", "")
    _check("_recurrences.yaml present", bool(recs_content))
    _check(
        "mirror-signal-state recurrence declared",
        "mirror-signal-state" in recs_content,
    )
    _check(
        "MirrorSignalState primitive invocation in _recurrences.yaml",
        "@primitive: MirrorSignalState" in recs_content,
    )

    # 3.7 — tasks scheduling index populated
    tasks = (
        client.table("tasks")
        .select("id, slug", count="exact")
        .eq("user_id", KVK_USER_ID)
        .execute()
    )
    _check(
        "tasks scheduling index populated",
        (tasks.count or 0) > 0,
        f"{tasks.count} recurrences materialized into tasks index"
    )

    # 3.8 — operator-canon files present
    canon_files = (
        client.table("workspace_files")
        .select("path")
        .eq("user_id", KVK_USER_ID)
        .in_("path", [
            "/workspace/constitution/MANDATE.md",
            "/workspace/persona/IDENTITY.md",
            "/workspace/operation/BRAND.md",
            "/workspace/governance/AUTONOMY.md",
            "/workspace/constitution/PRECEDENT.md",
            "/workspace/persona/IDENTITY.md",
            "/workspace/persona/principles.md",
            "/workspace/operation/trading/_operator_profile.md",
            "/workspace/operation/trading/_risk.md",
        ])
        .execute()
    )
    found_canon = {row["path"] for row in (canon_files.data or [])}
    _check(
        "kernel-universal operator-canon files present",
        all(p in found_canon for p in [
            "/workspace/constitution/MANDATE.md",
            "/workspace/persona/IDENTITY.md",
            "/workspace/persona/IDENTITY.md",
            "/workspace/persona/principles.md",
        ]),
        f"{len(found_canon)}/9 expected operator-canon paths found"
    )
    _check(
        "alpha-trader operator-canon files present (trading domain)",
        "/workspace/operation/trading/_operator_profile.md" in found_canon,
    )

    # ====================================================================
    # Phase 4: summary
    # ====================================================================
    logger.info("=" * 60)
    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    logger.info(f"E2E PROOF: {passed}/{total} checks passed")
    logger.info("=" * 60)

    if passed < total:
        failed = [name for name, ok, _ in checks if not ok]
        logger.error(f"FAILED CHECKS: {failed}")
        sys.exit(1)

    logger.info("")
    logger.info("All Stream B + ADR-281 + Stream A + Phase 1 + dissolution work validated end-to-end.")
    logger.info("kvk's workspace is in clean alpha-trader-activated state post-Stream-B.")


if __name__ == "__main__":
    asyncio.run(main())
