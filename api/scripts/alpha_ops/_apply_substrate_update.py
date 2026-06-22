"""One-shot harness: invoke apply_substrate_update for a persona.

Used to push bundle-level updates (e.g., refreshed principles.md from a
post-fork bundle commit) into a live persona workspace per ADR-292.
Equivalent to the cockpit Settings → Workspace "Update bundle" button
that Phase 2 will ship.

Usage:
    .venv/bin/python -m api.scripts.alpha_ops._apply_substrate_update \\
        --persona yarnnn-author --scope bundle
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")

sys.path.insert(0, str(_THIS_DIR))
from _shared import load_registry  # noqa: E402


async def main_async(persona_slug: str, scope: str) -> int:
    from services.supabase import get_service_client
    from services.substrate_reapply import apply_substrate_update

    reg = load_registry()
    persona = reg.require(persona_slug)
    client = get_service_client()
    report = await apply_substrate_update(
        client,
        persona.user_id,
        scope=scope,  # type: ignore[arg-type]
        source="harness",
    )
    print(f"persona={persona_slug} scope={scope}")
    print(f"bundle: {report.bundle_from} -> {report.bundle_to}  "
          f"kernel: {report.kernel_from} -> {report.kernel_to}")
    print(f"actions: {len(report.actions)}  "
          f"skipped_operator_authored: {report.skipped_operator_authored}  "
          f"skipped_aligned: {report.skipped_aligned}")
    for action in report.actions:
        print(f"  {action.layer} {action.path}: {action.change_summary}")
    if report.config_conflicts:
        print(f"config_conflicts: {len(report.config_conflicts)}")
        for c in report.config_conflicts:
            print(f"  {c.path} (prior at {c.backup_path})")
    if report.error:
        print(f"error: {report.error}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--scope", default="bundle", choices=["kernel", "bundle", "both"])
    args = ap.parse_args()
    return asyncio.run(main_async(args.persona, args.scope))


if __name__ == "__main__":
    raise SystemExit(main())
