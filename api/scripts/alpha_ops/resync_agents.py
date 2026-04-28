#!/usr/bin/env python3
"""
Re-sync system_bootstrap agents' AGENT.md + playbook files when the kernel
template (orchestration.AGENT_TEMPLATES.default_instructions / methodology)
has drifted from what was seeded at agent-creation time.

Why this exists
---------------
ADR-106 Phase 2 made workspace AGENT.md the sole authority for agent identity,
seeded once from `default_instructions` at agent-creation time
(api/services/agent_creation.py:175). When the kernel template is updated
(e.g., ADR-227 added a "Source Priority" section to the Tracker prompt),
existing agent rows continue to read their old AGENT.md content. The kernel
update applies only to NEW agents.

This is a one-shot reconciliation. It walks the agents table for one persona,
compares each agent's current AGENT.md against the live template's
default_instructions, and re-writes AGENT.md (via authored substrate per
ADR-209) when they differ. Memory playbook files are similarly compared and
re-written.

Usage
-----
    python -m api.scripts.alpha_ops.resync_agents alpha-trader
    python -m api.scripts.alpha_ops.resync_agents alpha-trader --dry-run
    python -m api.scripts.alpha_ops.resync_agents alpha-trader --role tracker
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Make `services.*` importable. api/scripts/alpha_ops -> api -> sys.path
_API_ROOT = Path(__file__).resolve().parents[2]  # api/
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared import load_registry  # noqa: E402


async def resync_persona(slug: str, role_filter: str | None, dry_run: bool) -> int:
    registry = load_registry()
    persona = registry.require(slug)

    from supabase import create_client  # type: ignore[import-untyped]

    supabase_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_KEY"]
    client = create_client(supabase_url, service_key)

    from services.orchestration import ALL_ROLES, has_asset_capabilities, get_type_playbook
    from services.workspace import AgentWorkspace, get_agent_slug

    agents_q = (
        client.table("agents")
        .select("id, role, title, origin")
        .eq("user_id", persona.user_id)
        .eq("origin", "system_bootstrap")
    )
    if role_filter:
        agents_q = agents_q.eq("role", role_filter)
    result = agents_q.execute()
    agents = result.data or []

    if not agents:
        print(f"No system_bootstrap agents found for {slug}" + (f" (role={role_filter})" if role_filter else ""))
        return 0

    drift_count = 0
    write_count = 0

    for agent in agents:
        role = agent["role"]
        template = ALL_ROLES.get(role)
        if not template:
            print(f"  [skip] {role}: no template in AGENT_TEMPLATES")
            continue

        # Build the canonical AGENT.md content the same way agent_creation.py does.
        canonical = template.get("default_instructions", "")
        if has_asset_capabilities(role):
            canonical += (
                "\n\n## Available Capabilities\nThis agent can produce rich outputs "
                "via RuntimeDispatch: PNG/SVG charts, diagrams, and images. "
                "Use these when visual data or formatted reports would serve the "
                "recipient better than plain text."
            )

        slug_str = get_agent_slug(agent)
        ws = AgentWorkspace(client, persona.user_id, slug_str)
        current = await ws.read("AGENT.md") or ""

        if current.strip() == canonical.strip():
            print(f"  [ok] {role} AGENT.md ({len(current)} chars) matches template")
        else:
            drift_count += 1
            print(
                f"  [DRIFT] {role} AGENT.md "
                f"current={len(current)} chars, template={len(canonical)} chars"
            )
            if not dry_run:
                await ws.write(
                    "AGENT.md",
                    canonical,
                    summary="Agent identity and behavioral instructions",
                    authored_by="system:agent-resync",
                    message=f"resync AGENT.md to current AGENT_TEMPLATES.{role}.default_instructions",
                )
                write_count += 1
                print(f"        → re-written via authored substrate")

        # Playbook files (memory/_playbook-*.md)
        playbook = get_type_playbook(role)
        for filename, content in playbook.items():
            mem_path = f"memory/{filename}"
            current_pb = await ws.read(mem_path) or ""
            if current_pb.strip() == content.strip():
                continue
            drift_count += 1
            print(f"  [DRIFT] {role} {mem_path} current={len(current_pb)}, template={len(content)}")
            if not dry_run:
                await ws.write(
                    mem_path,
                    content,
                    summary=f"ADR-143 playbook re-sync ({filename})",
                    authored_by="system:agent-resync",
                    message=f"resync {filename} to current PLAYBOOK_METADATA.{role}",
                )
                write_count += 1
                print(f"        → re-written via authored substrate")

    print()
    print(f"Summary: {drift_count} drift(s) detected, {write_count} write(s) applied" + (" [DRY RUN]" if dry_run else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    ap.add_argument("persona", help="Persona slug (e.g. alpha-trader)")
    ap.add_argument("--role", help="Limit to a single role (e.g. tracker)")
    ap.add_argument("--dry-run", action="store_true", help="Report drift without writing")
    args = ap.parse_args()
    return asyncio.run(resync_persona(args.persona, args.role, args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
