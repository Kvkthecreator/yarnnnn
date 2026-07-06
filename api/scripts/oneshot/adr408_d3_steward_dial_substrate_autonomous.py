"""One-shot: ADR-408 D3 — flip live steward-default _autonomy.yaml to the
substrate-autonomous posture.

Scope: ONLY workspaces whose governance/_autonomy.yaml still carries the
`# yarnnn:steward-default` marker (kernel-seeded, never operator- or
program-authored). Program-tuned or operator-edited files are untouched.
Write path: authored_substrate.write_revision (the single mutation path),
authored_by="system:adr408-d3" — attributed + revertible like everything.

Idempotent: a file already containing the `substrate:` block is skipped.

Run:  cd api && python scripts/oneshot/adr408_d3_steward_dial_substrate_autonomous.py [--dry-run]
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

STEWARD_MARKER = "# yarnnn:steward-default"
AUTONOMY_PATH = "/workspace/governance/_autonomy.yaml"


async def main(dry_run: bool) -> int:
    from services.supabase import get_service_client
    from services.orchestration import DEFAULT_AUTONOMY_YAML
    from services.authored_substrate import write_revision

    client = get_service_client()

    rows = (
        client.table("workspace_files")
        .select("id, user_id, workspace_id, path, content")
        .eq("path", AUTONOMY_PATH)
        .execute()
    ).data or []

    print(f"{len(rows)} _autonomy.yaml rows found")
    flipped = skipped_tuned = skipped_done = 0

    for row in rows:
        content = row.get("content") or ""
        label = f"ws={str(row.get('workspace_id'))[:8]} user={str(row.get('user_id'))[:8]}"
        if STEWARD_MARKER not in content:
            skipped_tuned += 1
            print(f"  SKIP (program/operator-authored): {label}")
            continue
        if "substrate:" in content:
            skipped_done += 1
            print(f"  SKIP (already has substrate block): {label}")
            continue
        if dry_run:
            flipped += 1
            print(f"  WOULD FLIP: {label}")
            continue
        revision_id = write_revision(
            client,
            user_id=row["user_id"],
            path=AUTONOMY_PATH,
            content=DEFAULT_AUTONOMY_YAML,
            authored_by="system:adr408-d3",
            message=(
                "ADR-408 D3: steward dial — substrate family goes autonomous "
                "(hands, not gatekeeper); capital default stays manual"
            ),
            workspace_id=row.get("workspace_id"),
        )
        flipped += 1
        print(f"  FLIPPED: {label} revision={str(revision_id)[:8]}")

    print(
        f"\nDone. flipped={flipped} skipped_program_or_operator={skipped_tuned} "
        f"skipped_already_done={skipped_done} dry_run={dry_run}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main("--dry-run" in sys.argv)))
