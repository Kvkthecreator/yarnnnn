"""ADR-292 v3 propagation re-fork — Checkpoint 2 bundle content to live workspaces.

One-shot script to invoke apply_substrate_update(scope='bundle', source='harness')
against the two live demo personas (kvk + yarnnn-author) so the ADR-296 v2
Checkpoint 2 bundle content (deleted trade-proposal recurrence in alpha-trader;
migrated pre-ship-audit to substrate-event hook in alpha-author) reaches the
live workspaces.

Per ADR-292 v3 D10, the re-fork uses the new config-vs-prose taxonomy:
  - _recurrences.yaml + _hooks.yaml → auto-overwrite with operator backup
    to /workspace/_shared/conflict-backups/{ran_at}/{path}
  - All prose files (IDENTITY, BRAND, MANDATE body, principles, etc.) →
    preserve operator content as before

Expected outcomes:
  - kvk: trade-proposal recurrence removed from _recurrences.yaml; signal-
    evaluation prompt now teaches inline ProposeAction; _hooks.yaml created
    with hooks: []; (operator-edited _operator_profile.md from probe NOT
    touched — handled separately by kvk-cleanup hygiene pass)
  - yarnnn-author: pre-ship-audit recurrence removed from _recurrences.yaml;
    _hooks.yaml created with pre-ship-audit substrate-event hook (operator-
    or-Reviewer-edited entries for weekly-corpus-review/quarterly-voice-
    audit are operator-substrate-update authored, also handled by re-fork
    as config conflicts auto-resolved)

Usage:
    cd /Users/macbook/yarnnn
    .venv/bin/python -m api.scripts.oneshot.adr292_v3_refork_checkpoint2_propagation

Requires SUPABASE_URL + SUPABASE_SERVICE_KEY in env (loaded from api/.env).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Repo-root path bootstrap (so `from services...` imports resolve)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
API_ROOT = REPO_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


# Personas in scope (matches docs/alpha/personas.yaml entries).
PERSONAS = [
    {
        "slug": "kvk",
        "email": "kvkthecreator@gmail.com",
        "user_id": "2abf3f96-118b-4987-9d95-40f2d9be9a18",
        "program": "alpha-trader",
    },
    {
        "slug": "yarnnn-author",
        "email": "yarnnn-author@yarnnn.com",
        "user_id": "0b7a852d-4a67-447d-91d9-2ba1145a60d7",
        "program": "alpha-author",
    },
]


async def run() -> int:
    # Late imports to ensure path bootstrap takes effect.
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    load_dotenv(API_ROOT / ".env")

    import os
    from supabase import create_client  # type: ignore[import-not-found]
    from services.substrate_reapply import apply_substrate_update

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print(
            "error: SUPABASE_URL + SUPABASE_SERVICE_KEY must be set "
            "(load from api/.env or shell)",
            file=sys.stderr,
        )
        return 2

    client = create_client(url, key)

    print(f"ADR-292 v3 propagation re-fork against {len(PERSONAS)} live workspaces\n")

    for persona in PERSONAS:
        slug = persona["slug"]
        user_id = persona["user_id"]
        program = persona["program"]

        print(f"--- {slug} ({program}, user_id={user_id[:8]}…) ---")
        try:
            report = await apply_substrate_update(
                client,
                user_id,
                scope="bundle",
                source="harness",
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ apply_substrate_update raised: {exc}")
            continue

        print(f"  source: {report.source}")
        print(f"  bundle: {report.bundle_from!r} → {report.bundle_to!r}")
        print(f"  actions taken: {len(report.actions)}")
        print(f"  config conflicts auto-resolved: {len(report.config_conflicts)}")
        print(f"  skipped (operator-authored prose): {report.skipped_operator_authored}")
        print(f"  skipped (aligned): {report.skipped_aligned}")
        if report.error:
            print(f"  ERROR: {report.error}")

        if report.config_conflicts:
            print("  config conflicts:")
            for c in report.config_conflicts:
                print(f"    • {c.path} → backup at {c.backup_path} (bundle v{c.bundle_version})")
        if report.actions:
            print("  actions:")
            for a in report.actions[:20]:
                print(f"    • {a.path} ({a.layer}) — {a.change_summary}")
            if len(report.actions) > 20:
                print(f"    ... and {len(report.actions) - 20} more")
        print()

    print("done. Per ADR-292 v3 D10, each workspace's substrate-update-log.md")
    print("now carries the propagation event; conflict backups (if any) live")
    print("at /workspace/_shared/conflict-backups/{ran_at}/{relative_path}.")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())
