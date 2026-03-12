"""
ADR-109 E2E Test: Agent Skill Portfolio
=========================================

Creates one test agent per active skill type, triggers a run for each,
and verifies output is generated and delivered to kvkthecreator@gmail.com.

Skills tested:
  - digest:     Platform recap (Slack sources)
  - prepare:    Auto meeting prep (Calendar + cross-platform)
  - synthesize: Work summary (cross-platform)
  - monitor:    Watch (cross-platform, simulated)
  - research:   Research (no sources, web-driven)
  - custom:     Custom agent (cross-platform)

Not tested (require multi-agent orchestration):
  - orchestrate: Coordinator agent
  - act:         Action agent (future)

Usage:
  cd api
  python test_adr109_skills.py [create|run|status|cleanup]

  create  - Insert test agents into DB
  run     - Trigger ad-hoc runs for all test agents
  status  - Check run status and delivery
  cleanup - Delete test agents and their runs
"""

import asyncio
import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

# Setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SUPABASE_URL", "https://noxgqcwynkzqabljjyon.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "sb_secret_-8NWVKf09Cf56mO3JrjPqw_5FqL423G")

from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Constants
USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
DESTINATION = {"platform": "email", "target": "kvkthecreator@gmail.com", "format": "send"}
TEST_PREFIX = "[TEST-ADR109]"

# Test agent definitions — one per skill
TEST_AGENTS = [
    {
        "title": f"{TEST_PREFIX} Slack Recap (digest)",
        "skill": "digest",
        "mode": "recurring",
        "sources": [{"provider": "slack", "resource_id": "all", "resource_name": "All Slack"}],
        "type_config": {"primary_platform": "slack"},
        "agent_instructions": "Create a concise Slack recap highlighting key discussions from the past 24 hours.",
    },
    {
        "title": f"{TEST_PREFIX} Meeting Prep (prepare)",
        "skill": "prepare",
        "mode": "recurring",
        "sources": [
            {"provider": "calendar", "resource_id": "all", "resource_name": "All Calendar"},
            {"provider": "slack", "resource_id": "all", "resource_name": "All Slack"},
        ],
        "type_config": {},
        "agent_instructions": "Prepare a briefing for today's meetings with context from Slack conversations about attendees and topics.",
    },
    {
        "title": f"{TEST_PREFIX} Work Summary (synthesize)",
        "skill": "synthesize",
        "mode": "recurring",
        "sources": [
            {"provider": "slack", "resource_id": "all", "resource_name": "All Slack"},
            {"provider": "notion", "resource_id": "all", "resource_name": "All Notion"},
        ],
        "type_config": {},
        "recipient_context": {"name": "Kevin", "role": "Founder"},
        "agent_instructions": "Synthesize a weekly work summary across Slack and Notion for the founder, highlighting progress, blockers, and key decisions.",
    },
    {
        "title": f"{TEST_PREFIX} Platform Watch (monitor)",
        "skill": "monitor",
        "mode": "recurring",
        "sources": [
            {"provider": "slack", "resource_id": "all", "resource_name": "All Slack"},
        ],
        "type_config": {"watch_topics": ["AI agents", "platform architecture", "product launch"]},
        "agent_instructions": "Monitor Slack for mentions of AI agents, platform architecture, and product launch discussions. Surface emerging themes.",
    },
    {
        "title": f"{TEST_PREFIX} Market Research (research)",
        "skill": "research",
        "mode": "recurring",
        "sources": [],
        "type_config": {},
        "agent_instructions": "Research the current state of AI agent platforms and autonomous agent frameworks. Focus on recent developments in 2026.",
    },
    {
        "title": f"{TEST_PREFIX} Custom Report (custom)",
        "skill": "custom",
        "mode": "recurring",
        "sources": [
            {"provider": "slack", "resource_id": "all", "resource_name": "All Slack"},
        ],
        "type_config": {},
        "description": "A custom weekly report",
        "agent_instructions": "Generate a creative weekly roundup of what happened across connected platforms. Make it engaging and actionable.",
    },
]


def get_client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def infer_scope(sources, skill, mode="recurring"):
    """Mirror of routes/agents.py infer_scope()"""
    if skill == "orchestrate":
        return "autonomous"
    if mode in ("proactive", "coordinator") and skill in ("synthesize", "research"):
        return "autonomous"
    providers = set()
    for s in sources:
        provider = s.get("provider") if isinstance(s, dict) else None
        if provider:
            providers.add(provider)
    if not providers:
        if skill == "research":
            return "research"
        return "knowledge" if skill in ("monitor", "research") else "cross_platform"
    if len(providers) == 1:
        return "platform"
    return "cross_platform"


def cmd_create():
    """Create test agents in the database."""
    client = get_client()

    # Clean up any existing test agents first
    existing = client.table("agents").select("id, title").eq("user_id", USER_ID).like("title", f"{TEST_PREFIX}%").execute()
    if existing.data:
        logger.info(f"Cleaning up {len(existing.data)} existing test agents...")
        for agent in existing.data:
            # Delete runs first
            client.table("agent_runs").delete().eq("agent_id", agent["id"]).execute()
            client.table("agents").delete().eq("id", agent["id"]).execute()
            logger.info(f"  Deleted: {agent['title']}")

    # Create test agents
    created = []
    for defn in TEST_AGENTS:
        scope = infer_scope(defn["sources"], defn["skill"], defn.get("mode", "recurring"))
        agent_data = {
            "user_id": USER_ID,
            "title": defn["title"],
            "scope": scope,
            "skill": defn["skill"],
            "mode": defn.get("mode", "recurring"),
            "sources": defn["sources"],
            "type_config": defn.get("type_config", {}),
            "recipient_context": defn.get("recipient_context", {}),
            "schedule": {"frequency": "weekly", "day": "monday", "time": "09:00"},
            "destination": DESTINATION,
            "status": "active",
            "agent_instructions": defn.get("agent_instructions", ""),
            "description": defn.get("description", ""),
            "next_run_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        }
        result = client.table("agents").insert(agent_data).execute()
        agent = result.data[0]
        created.append(agent)
        logger.info(f"  Created: {agent['title']} (scope={scope}, skill={defn['skill']}, id={agent['id'][:8]}...)")

    print(f"\n{len(created)} test agents created. Run with 'run' to trigger execution.")
    return created


async def cmd_run():
    """Trigger ad-hoc runs for all test agents."""
    client = get_client()
    from services.agent_execution import execute_agent_generation

    agents = client.table("agents").select("*").eq("user_id", USER_ID).like("title", f"{TEST_PREFIX}%").order("skill").execute()

    if not agents.data:
        print("No test agents found. Run 'create' first.")
        return

    print(f"Triggering runs for {len(agents.data)} test agents...\n")

    for agent in agents.data:
        print(f"{'='*60}")
        print(f"Agent: {agent['title']}")
        print(f"  scope={agent['scope']}, skill={agent['skill']}, mode={agent['mode']}")
        print(f"  sources: {len(agent.get('sources', []))} configured")
        print(f"  destination: {agent.get('destination', {}).get('target', 'none')}")
        print(f"  Running...")

        try:
            result = await execute_agent_generation(
                client=client,
                user_id=USER_ID,
                agent=agent,
            )
            status = result.get("status", "unknown")
            draft_len = len(result.get("draft_content", "") or "")
            run_id = result.get("run_id", "n/a")
            print(f"  Result: status={status}, draft_length={draft_len}, run_id={run_id[:8] if run_id != 'n/a' else 'n/a'}")
        except Exception as e:
            print(f"  ERROR: {e}")

        print()

    print("All runs triggered. Run with 'status' to check delivery.")


def cmd_status():
    """Check status of test agent runs."""
    client = get_client()

    agents = client.table("agents").select("id, title, scope, skill").eq("user_id", USER_ID).like("title", f"{TEST_PREFIX}%").order("skill").execute()

    if not agents.data:
        print("No test agents found.")
        return

    print(f"{'Skill':<12} {'Scope':<16} {'Status':<10} {'Delivery':<12} {'Length':>7} {'Title'}")
    print("-" * 90)

    for agent in agents.data:
        # Get latest run
        run = client.table("agent_runs").select("*").eq("agent_id", agent["id"]).order("version_number", desc=True).limit(1).execute()

        if run.data:
            r = run.data[0]
            status = r.get("status") or "?"
            delivery = r.get("delivery_status") or "—"
            content_len = len(r.get("final_content", "") or r.get("draft_content", "") or "")
            print(f"{agent['skill']:<12} {agent['scope']:<16} {status:<10} {delivery:<12} {content_len:>7} {agent['title']}")
        else:
            print(f"{agent['skill']:<12} {agent['scope']:<16} {'no run':<10} {'—':<12} {'—':>7} {agent['title']}")


def cmd_cleanup():
    """Delete all test agents and their runs."""
    client = get_client()

    agents = client.table("agents").select("id, title").eq("user_id", USER_ID).like("title", f"{TEST_PREFIX}%").execute()

    if not agents.data:
        print("No test agents to clean up.")
        return

    for agent in agents.data:
        # Delete runs first (FK constraint)
        runs = client.table("agent_runs").delete().eq("agent_id", agent["id"]).execute()
        run_count = len(runs.data) if runs.data else 0
        client.table("agents").delete().eq("id", agent["id"]).execute()
        logger.info(f"  Deleted: {agent['title']} ({run_count} runs)")

    print(f"\n{len(agents.data)} test agents cleaned up.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "create":
        cmd_create()
    elif cmd == "run":
        asyncio.run(cmd_run())
    elif cmd == "status":
        cmd_status()
    elif cmd == "cleanup":
        cmd_cleanup()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python test_adr109_skills.py [create|run|status|cleanup]")
        sys.exit(1)
