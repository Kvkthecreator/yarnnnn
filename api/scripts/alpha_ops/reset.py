#!/usr/bin/env python3
"""
Reset a persona workspace to cold-start state.

Usage:
    python -m api.scripts.alpha_ops.reset alpha-trader --confirm
    python -m api.scripts.alpha_ops.reset alpha-commerce --confirm

What it does:
    Calls DELETE /api/account/reset on the production API as the persona user.
    This is the same endpoint the UI's "Reset account" action uses. Routes/account.py
    wipes agents, tasks, workspace_files, platform_connections, chat history, etc.,
    then synchronously calls initialize_workspace() to rescaffold the full alpha
    roster (12 agents + 5 essential tasks + identity files).

    After reset you still need to re-run connect.py to re-attach platform creds.

Safety:
    --confirm is required. Refuses to proceed without it.

Typical session:
    python -m api.scripts.alpha_ops.reset alpha-trader --confirm
    python -m api.scripts.alpha_ops.alpha_ops.connect alpha-trader
    python -m api.scripts.alpha_ops.verify alpha-trader
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared import ProdClient, load_registry  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Reset a persona workspace to cold start.")
    ap.add_argument("persona", help="Persona slug (e.g. alpha-trader, alpha-commerce)")
    ap.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Proves you meant to destroy this workspace's state.",
    )
    args = ap.parse_args()

    if not args.confirm:
        print("refusing to proceed without --confirm. This is destructive.", file=sys.stderr)
        return 2

    registry = load_registry()
    persona = registry.require(args.persona)

    print(f"resetting {persona.slug} ({persona.email}) ... workspace {persona.workspace_id}")
    with ProdClient(persona, registry=registry) as client:
        r = client.delete("/api/account/reset")

    if r.status_code >= 300:
        print(f"reset failed [{r.status_code}]: {r.text}", file=sys.stderr)
        return 1

    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)
    print(f"\n[next] run: python -m api.scripts.alpha_ops.connect {persona.slug}")
    print(f"[then] run: python -m api.scripts.alpha_ops.verify  {persona.slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
