#!/usr/bin/env python3
"""
One-shot backfill: insert **Required Capabilities:** field into existing
TASK.md files for a persona, where the field is missing.

Why this exists
---------------
Tasks created before the fix to TaskCreate (api/routes/tasks.py) had their
`required_capabilities` payload field silently dropped by Pydantic — the
field was not declared on the model, so it was stripped before reaching
ManageTask._handle_create. Result: TASK.md files exist without the field,
and the ADR-227 dispatcher never merges platform tools into the agent's
tool surface for those tasks.

This script reads the canonical capability declarations from
docs/programs/alpha-trader/tasks.yaml (the program-default task instances
per ADR-230 D2; the previous scaffold_trader.py:TASKS source was deleted
by ADR-230 D5) and writes them into the existing TASK.md files via the
authored substrate (ADR-209) with attribution.

Usage
-----
    python -m api.scripts.alpha_ops.backfill_required_capabilities alpha-trader
    python -m api.scripts.alpha_ops.backfill_required_capabilities alpha-trader --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import re
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parents[2]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared import load_registry  # noqa: E402


# Canonical declarations from scaffold_trader.py:TASKS
ALPHA_TRADER_CAPABILITIES = {
    "track-universe": ["read_trading"],
    "signal-evaluation": ["read_trading"],
    "pre-market-brief": ["read_trading"],
    "trade-proposal": ["read_trading", "write_trading"],
    "weekly-performance-review": ["read_trading"],
    "quarterly-signal-audit": ["read_trading"],
    # back-office-* tasks are TP-class and have no platform capability needs
}


def insert_required_capabilities_field(task_md: str, capabilities: list[str]) -> str:
    """Insert **Required Capabilities:** line after **Context Writes:** (or
    after the final ** field line if Context Writes is absent).

    Idempotent: if the field already exists, returns content unchanged.
    """
    if "**Required Capabilities:**" in task_md:
        return task_md

    caps_line = f"**Required Capabilities:** {', '.join(capabilities)}"
    lines = task_md.split("\n")

    # Find the last consecutive **Field:** header line and insert after it.
    field_pattern = re.compile(r"^\*\*[A-Z][A-Za-z ]+:\*\*")
    last_field_idx = -1
    for i, line in enumerate(lines):
        if field_pattern.match(line):
            last_field_idx = i

    if last_field_idx == -1:
        return task_md  # no header fields; do not guess

    lines.insert(last_field_idx + 1, caps_line)
    return "\n".join(lines)


async def backfill_persona(slug: str, dry_run: bool) -> int:
    if slug != "alpha-trader":
        print(f"Persona {slug!r} has no canonical capability map. Add to ALPHA_TRADER_CAPABILITIES dict.")
        return 1

    registry = load_registry()
    persona = registry.require(slug)

    from supabase import create_client  # type: ignore[import-untyped]

    supabase_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(supabase_url, service_key)

    from services.task_workspace import TaskWorkspace
    from services.authored_substrate import write_revision

    backfill_count = 0
    skip_count = 0

    for task_slug, capabilities in ALPHA_TRADER_CAPABILITIES.items():
        ws = TaskWorkspace(client, persona.user_id, task_slug)
        current = await ws.read_task() or ""
        if not current:
            print(f"  [skip] {task_slug}: TASK.md missing")
            skip_count += 1
            continue

        if "**Required Capabilities:**" in current:
            print(f"  [ok] {task_slug}: already has Required Capabilities field")
            continue

        new_content = insert_required_capabilities_field(current, capabilities)
        if new_content == current:
            print(f"  [skip] {task_slug}: could not find insertion point")
            skip_count += 1
            continue

        print(f"  [BACKFILL] {task_slug}: adding **Required Capabilities:** {', '.join(capabilities)}")

        if not dry_run:
            path = f"/tasks/{task_slug}/TASK.md"
            write_revision(
                client,
                user_id=persona.user_id,
                path=path,
                content=new_content,
                authored_by="system:taskmd-backfill",
                message=f"backfill **Required Capabilities:** field (Pydantic-drop fix on /api/tasks)",
                summary="task charter",
            )
            backfill_count += 1

    print()
    print(f"Summary: {backfill_count} backfill(s) applied, {skip_count} skipped" + (" [DRY RUN]" if dry_run else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("persona", help="Persona slug (alpha-trader)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return asyncio.run(backfill_persona(args.persona, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
