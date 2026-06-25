"""ADR-366 — migrate the operating-CONTRACT files governance/ -> contract/.

ADR-366 split the `governance/` root into the GRANT (_autonomy + _budget, locked)
and the operating CONTRACT (_preferences + _expected_output), moving the latter to
a new `contract/` root (mode-governed, not locked). The READERS now query the
`contract/` paths, so any live workspace that still has these two files at the old
`governance/` path would have them go SILENTLY INVISIBLE to the wake envelope (the
ADR-320 'reads-empty' failure mode). substrate_reapply does NOT do path moves (it
updates content at known paths only), so this is a one-time data migration — the
same class as the ADR-320 re-rooting migration.

What it does, per workspace, per file:
  - read the OLD-path head row's content,
  - write that exact content to the NEW contract/ path via write_revision (a fresh
    revision chain at the new home; the OLD path's history stays in
    workspace_file_versions per ADR-209 — nothing is destroyed),
  - delete the OLD-path head row (so the file no longer resolves at governance/).

Properties:
  - IDEMPOTENT — skips a file already absent at the old path (re-runnable safely).
  - CONTENT-EXACT — byte-for-byte; no transform.
  - REVISION-PRESERVING — ADR-209: the old path's version chain is retained; the
    new path gets a migration-attributed first revision.
  - ATTRIBUTED — authored_by="system:adr366-migration" (a deterministic actor).
  - AUDITABLE — prints every move; a dry-run mode (default) shows the plan first.

Usage:
  # dry-run (default — shows what WOULD move, no writes):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.oneshot.adr366_migrate_governance_to_contract
  # apply:
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.oneshot.adr366_migrate_governance_to_contract --apply
  # single workspace:
  ... --apply --user <uuid>
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[2]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(_API_ROOT.parent / ".env")

# The two operating-contract files that move. (The GRANT files — _autonomy,
# AUTONOMY.md, _budget — stay in governance/ and are NOT touched here.)
MOVES = [
    ("/workspace/governance/_preferences.yaml", "/workspace/contract/_preferences.yaml"),
    ("/workspace/governance/_expected_output.yaml", "/workspace/contract/_expected_output.yaml"),
]

AUTHOR = "system:adr366-migration"


def _affected_user_ids(client) -> list[str]:
    """Every user_id with at least one file still at an old governance/ contract path."""
    users: set[str] = set()
    for old, _new in MOVES:
        res = client.table("workspace_files").select("user_id").eq("path", old).execute()
        for row in (res.data or []):
            users.add(row["user_id"])
    return sorted(users)


def _migrate_user(client, user_id: str, apply: bool) -> dict:
    from services.authored_substrate import write_revision

    moved, skipped = [], []
    for old, new in MOVES:
        old_row = (
            client.table("workspace_files").select("content")
            .eq("user_id", user_id).eq("path", old).limit(1).execute()
        )
        if not (old_row.data):
            skipped.append((old, "absent at old path"))
            continue
        content = old_row.data[0].get("content") or ""
        # Guard: if the NEW path already has content, don't clobber it — just
        # remove the stale old row (idempotent re-run / partial prior migration).
        new_row = (
            client.table("workspace_files").select("path")
            .eq("user_id", user_id).eq("path", new).limit(1).execute()
        )
        new_exists = bool(new_row.data)
        if apply:
            if not new_exists:
                write_revision(
                    client, user_id=user_id, path=new, content=content,
                    authored_by=AUTHOR,
                    message="ADR-366: move operating-contract file governance/ -> contract/ (grant/contract split)",
                )
            client.table("workspace_files").delete().eq("user_id", user_id).eq("path", old).execute()
        moved.append((old, new, "new-existed→drop-old" if new_exists else "moved"))
    return {"user_id": user_id, "moved": moved, "skipped": skipped}


def main() -> int:
    from services.supabase import get_service_client
    client = get_service_client()

    apply = "--apply" in sys.argv
    only_user = None
    if "--user" in sys.argv:
        only_user = sys.argv[sys.argv.index("--user") + 1]

    users = [only_user] if only_user else _affected_user_ids(client)
    print(f"[adr366-migrate] {'APPLY' if apply else 'DRY-RUN'} — "
          f"{len(users)} workspace(s) with files still at old governance/ paths\n")

    if not users:
        print("[adr366-migrate] nothing to migrate — all workspaces already on contract/.")
        return 0

    for uid in users:
        res = _migrate_user(client, uid, apply)
        print(f"  user {uid[:8]}:")
        for old, new, how in res["moved"]:
            print(f"    {'MOVED ' if apply else 'WOULD MOVE '}{old} -> {new}  [{how}]")
        for old, why in res["skipped"]:
            print(f"    skip   {old}  ({why})")

    if not apply:
        print("\n[adr366-migrate] DRY-RUN only. Re-run with --apply to perform the migration.")
    else:
        # Verify: zero rows remain at the old paths.
        remaining = 0
        for old, _new in MOVES:
            r = client.table("workspace_files").select("user_id").eq("path", old).execute()
            remaining += len(r.data or [])
        print(f"\n[adr366-migrate] APPLIED. Rows remaining at old governance/ contract paths: {remaining} "
              f"({'CLEAN' if remaining == 0 else 'INVESTIGATE'}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
