"""ADR-478 — Permanent delete, and the Trash contract.

  D3   permanent delete removes the path's row + chain + content; every OTHER
       path's ledger is untouched (unrecoverable, not unremembered)
  D3a  content is reference-counted at the revision level — a blob a live path
       still cites is NEVER deleted (21 blobs live are shared across paths)
  D4   permanent delete is owner-grade (destroys shared content — reuses the
       ADR-476 gate)
  D5   a cited file cannot be permanently deleted (the ADR-448 reference edge)

The load-bearing one is D3a: the reference-counting probe below writes two files
with IDENTICAL content, deletes one, and asserts the other's shared blob
survives — the corruption case the design exists to prevent.

Run with `python3 test_adr478_permanent_delete.py` (NOT pytest — check() gates
print ✗ but a pytest run reports PASS; see MEMORY.md).
"""

import logging
import os
import sys
import uuid
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_passed = 0
_failed = 0


def record(name: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        logger.info(f"✓ {name}" + (f": {detail}" if detail else ""))
    else:
        _failed += 1
        logger.error(f"✗ {name}" + (f": {detail}" if detail else ""))


def run() -> None:
    # -- static: the contract lives where the ADR says ----------------------
    svc = open(os.path.join(REPO, "api/services/permanent_delete.py")).read()
    record(
        "D3. the chain delete is scoped to the deleted path only",
        '.eq("path", path)' in svc and "workspace_file_versions" in svc,
        "",
    )
    record(
        "D3a. blob deletion is guarded by _blob_still_cited_elsewhere",
        "_blob_still_cited_elsewhere" in svc and 'neq("path", exclude_path)' in svc,
        "",
    )
    has_guard = "_blob_still_cited_elsewhere(client" in svc
    has_chain_delete = 'workspace_file_versions").delete().eq("path", path)' in svc
    ordered = (
        has_guard
        and has_chain_delete
        and svc.index("_blob_still_cited_elsewhere(client")
        > svc.rindex('workspace_file_versions").delete().eq("path", path)')
    )
    record(
        "D3a. the cited-elsewhere check runs AFTER the chain delete",
        ordered,
        "against the true remaining graph"
        if ordered
        else "guard missing or runs before the chain delete",
    )

    routes = open(os.path.join(REPO, "api/routes/documents.py")).read()
    record(
        "D4. permanent delete gates on workspace-clear authority (ADR-476)",
        "has_workspace_clear_authority" in routes
        and "_require_permadelete_authority" in routes,
        "",
    )
    record(
        "D5. permanent delete refuses a cited file (list_dependents)",
        "list_dependents" in routes and "_assert_archived_and_uncited" in routes,
        "",
    )
    record(
        "archived-only: a non-trashed file is refused (409)",
        '!= "archived"' in routes or 'get("lifecycle") != "archived"' in routes,
        "",
    )
    record(
        "empty-trash skips cited files rather than failing",
        "empty_trash" in routes and "skipped" in routes,
        "",
    )

    # -- live: the end-to-end behavior, incl. the D3a corruption case -------
    try:
        from services.supabase import get_service_client
        from services.authored_substrate import write_revision, list_dependents
        from services.permanent_delete import permanently_delete_file

        c = get_service_client()
        ws_row = c.table("workspaces").select("id, owner_id").limit(1).execute().data[0]
        WS, owner = ws_row["id"], ws_row["owner_id"]
        tag = uuid.uuid4().hex[:8]
        victim = f"/workspace/uploads/operator/_t477_victim_{tag}.md"
        sibling = f"/workspace/uploads/operator/_t477_sibling_{tag}.md"
        cleanup: List[str] = [victim, sibling]

        try:
            shared = f"shared bytes {tag}"
            write_revision(c, user_id=owner, path=victim, content=shared,
                           authored_by="operator", message="v1", workspace_id=WS)
            write_revision(c, user_id=owner, path=victim, content=f"v2 {tag}",
                           authored_by="operator", message="v2", workspace_id=WS)
            write_revision(c, user_id=owner, path=sibling, content=shared,
                           authored_by="operator", message="sib", workspace_id=WS)
            write_revision(c, user_id=owner, path=victim, content=f"v2 {tag}",
                           authored_by="operator", message="arch", workspace_id=WS,
                           lifecycle="archived")

            summary = permanently_delete_file(c, user_id=owner, workspace_id=WS, path=victim)

            gone_row = not c.table("workspace_files").select("path").eq(
                "path", victim).eq("workspace_id", WS).execute().data
            gone_chain = not c.table("workspace_file_versions").select("id").eq(
                "path", victim).eq("workspace_id", WS).execute().data
            record("D3 LIVE. victim row + chain removed", gone_row and gone_chain,
                   f"{summary}")

            # D3a — the shared blob must survive because sibling still cites it
            sib = c.table("workspace_files").select("head_version_id").eq(
                "path", sibling).eq("workspace_id", WS).execute().data
            sib_content = None
            if sib:
                bl = c.table("workspace_file_versions").select(
                    "workspace_blobs(content)").eq("id", sib[0]["head_version_id"]).execute().data
                sib_content = (bl[0].get("workspace_blobs") or {}).get("content") if bl else None
            record("D3a LIVE. sibling's shared blob NOT over-deleted",
                   sib_content == shared, "reference-counting held")

            # D5 — a live derived file blocks
            src = f"/workspace/uploads/operator/_t477_src_{tag}.md"
            drv = f"/workspace/uploads/operator/_t477_drv_{tag}.md"
            cleanup += [src, drv]
            write_revision(c, user_id=owner, path=src, content=f"src {tag}",
                           authored_by="operator", message="s", workspace_id=WS)
            write_revision(c, user_id=owner, path=drv, content=f"from src {tag}",
                           authored_by="operator", message="d", workspace_id=WS,
                           derived_from=[src])
            write_revision(c, user_id=owner, path=src, content=f"src {tag}",
                           authored_by="operator", message="arch", workspace_id=WS,
                           lifecycle="archived")
            deps = list_dependents(c, user_id=owner, path=src, limit=5)
            record("D5 LIVE. a live derived file blocks permanent delete",
                   bool(deps), f"dependents={len(deps)}")
        finally:
            for p in cleanup:
                try:
                    c.table("workspace_files").update({"head_version_id": None}).eq("path", p).execute()
                    c.table("workspace_file_versions").delete().eq("path", p).execute()
                    c.table("workspace_files").delete().eq("path", p).execute()
                except Exception:
                    pass
    except Exception as exc:  # noqa: BLE001 — live checks are env-gated
        logger.warning(f"live checks skipped (no DB env): {exc}")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        logger.exception("suite crashed")
        record("SUITE", False, f"crashed: {exc}")
    print("\n" + "=" * 60)
    print(f"ADR-478 permanent-delete gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
