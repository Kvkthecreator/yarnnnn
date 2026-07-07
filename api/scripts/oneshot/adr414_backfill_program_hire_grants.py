"""One-shot — ADR-414 D5: backfill hire grants for live program workspaces.

The activation record moves from the MANDATE.md prose marker
(`# Mandate — {slug} (template)`) to a `principal_grants` row
(role='own-agent', principal_id='program:{slug}'). This one-shot walks
every workspace's MANDATE.md, parses the OLD marker one last time (the
regex lives here now — deleted from services/programs.py), validates the
slug against the bundle registry, and ensures the grant row.

MUST run against prod BEFORE the D+E-1 code deploy — the deployed code
still reads the marker; the new code reads only grants; the backfill
closes the window where activation would read as none.

Idempotent: ensure_principal_grant no-ops on an existing active grant.

Run:  cd api && venv/bin/python scripts/oneshot/adr414_backfill_program_hire_grants.py
"""

import re
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_API_ROOT / ".env")

_TEMPLATE_HEADING_RE = re.compile(
    r"^#\s+\S+\s+—\s+(?P<slug>[a-z0-9][a-z0-9\-]*)\b",
    re.IGNORECASE,
)


def _parse_marker(content):
    if not content:
        return None
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("# "):
            continue
        match = _TEMPLATE_HEADING_RE.match(stripped)
        return match.group("slug") if match else None
    return None


def main() -> int:
    from services.supabase import get_service_client
    from services.bundle_reader import _all_slugs
    from services.principal_grants import ensure_principal_grant
    from services.programs import HIRE_GRANT_ROLE, hire_grant_principal_id

    client = get_service_client()
    slugs = _all_slugs()

    workspaces = client.table("workspaces").select("id, owner_id").execute()
    minted, skipped, already = 0, 0, 0
    for ws in workspaces.data or []:
        ws_id, owner = ws["id"], ws["owner_id"]
        mandate = (
            client.table("workspace_files")
            .select("content")
            .eq("workspace_id", ws_id)
            .eq("path", "/workspace/constitution/MANDATE.md")
            .limit(1)
            .execute()
        )
        content = (mandate.data or [{}])[0].get("content") or ""
        candidate = _parse_marker(content)
        if not candidate or candidate not in slugs:
            skipped += 1
            print(f"  skip ws={ws_id[:8]} (marker={candidate!r})")
            continue
        existing = (
            client.table("principal_grants")
            .select("id")
            .eq("workspace_id", ws_id)
            .eq("principal_id", hire_grant_principal_id(candidate))
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if existing.data:
            already += 1
            print(f"  already ws={ws_id[:8]} program={candidate}")
            continue
        ensure_principal_grant(
            principal_id=hire_grant_principal_id(candidate),
            workspace_id=ws_id,
            role=HIRE_GRANT_ROLE,
            granted_by="system:adr414-backfill",
        )
        minted += 1
        print(f"  MINTED ws={ws_id[:8]} owner={owner[:8]} program={candidate}")

    print(f"\nReceipt: {minted} minted, {already} already-present, {skipped} no-program")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
