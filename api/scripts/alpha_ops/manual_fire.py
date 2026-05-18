"""Manually fire a recurrence for a persona — test harness.

Usage:
    python scripts/alpha_ops/manual_fire.py --persona kvk --slug signal-evaluation

Reads `/workspace/_recurrences.yaml`, finds the named slug, and calls
`services.invocation_dispatcher.dispatch(client, user_id, recurrence)`
synchronously. Output streams to stdout. Used for ADR-290 fresh-fork
behavioral validation — bypasses the scheduler so we don't have to wait
for the natural cron.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Repo path discipline
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env.alpha-ops")
load_dotenv()


def _load_persona(slug: str) -> tuple[str, str]:
    """Resolve persona slug → (user_id, email) via personas.yaml."""
    from scripts.alpha_ops._shared import load_registry
    registry = load_registry()
    persona = registry.require(slug)
    return persona.user_id, persona.email


async def fire(persona_slug: str, recurrence_slug: str) -> int:
    from services.supabase import get_service_client
    from services.recurrence import walk_workspace_recurrences
    from services.invocation_dispatcher import dispatch

    user_id, email = _load_persona(persona_slug)
    print(f"\n--- Manual fire: persona={persona_slug} ({email}) slug={recurrence_slug} ---\n")

    client = get_service_client()
    recurrences = walk_workspace_recurrences(client, user_id)
    target = next((r for r in recurrences if r.slug == recurrence_slug), None)
    if target is None:
        print(f"ERROR: recurrence slug={recurrence_slug!r} not found in /workspace/_recurrences.yaml")
        print(f"Available: {[r.slug for r in recurrences]}")
        return 1

    print(f"Found: slug={target.slug} mode={target.mode} paused={target.paused}")
    print(f"Firing dispatch(trigger='reactive', context=None)...\n")

    result = await dispatch(client, user_id, target, trigger="reactive", context=None)

    print("\n--- Result ---")
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("success") else 2


def main() -> int:
    ap = argparse.ArgumentParser(description="Manually fire a recurrence (test harness).")
    ap.add_argument("--persona", required=True, help="Persona slug from personas.yaml")
    ap.add_argument("--slug", required=True, help="Recurrence slug to fire")
    args = ap.parse_args()

    return asyncio.run(fire(args.persona, args.slug))


if __name__ == "__main__":
    sys.exit(main())
