"""
ADR-092 Mode Test Suite — Agent Intelligence & Mode Taxonomy

Tests the three new scheduler paths introduced in ADR-092 Phases 2–5:
  - Reactive mode: observation accumulation + threshold-triggered generation
  - Proactive mode: apply_review_decision() memory writes
  - Coordinator mode: CreateAgent + AdvanceAgentSchedule primitives

Also tests _parse_review_response() edge cases (pure unit, no DB) and
verifies scheduler query filters correctly separate recurring/goal from
proactive/coordinator paths.

Strategy: No live LLM calls. Real DB writes using service client.
Test agents use prefix TEST_ADR092_ for cleanup isolation.

Usage:
    cd api && python test_adr092_modes.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def parse_dt(s: str) -> datetime:
    """Parse ISO timestamp from Supabase, tolerant of non-standard microsecond precision."""
    s = s.replace("Z", "+00:00")
    # Normalize microseconds to exactly 6 digits (Python 3.9 fromisoformat requires this)
    s = re.sub(r"(\.\d+)(?=\+|-|$)", lambda m: m.group(1).ljust(7, "0")[:7], s)
    return datetime.fromisoformat(s)


# Test user (kvkthecreator@gmail.com)
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
TEST_PREFIX = "TEST_ADR092_"


# =============================================================================
# Result tracking
# =============================================================================

@dataclass
class PhaseResult:
    phase: str
    passed: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def ok(self, label: str) -> None:
        logger.info(f"    ✓ {label}")
        self.passed += 1

    def fail(self, label: str, detail: str = "") -> None:
        msg = f"{label}: {detail}" if detail else label
        logger.error(f"    ✗ {msg}")
        self.failed += 1
        self.errors.append(msg)

    @property
    def success(self) -> bool:
        return self.failed == 0


def assert_eq(result: PhaseResult, label: str, actual, expected) -> None:
    if actual == expected:
        result.ok(label)
    else:
        result.fail(label, f"expected {expected!r}, got {actual!r}")


def assert_true(result: PhaseResult, label: str, condition: bool, detail: str = "") -> None:
    if condition:
        result.ok(label)
    else:
        result.fail(label, detail)


# =============================================================================
# Phase 1: Setup
# =============================================================================

async def phase1_setup(supabase) -> dict:
    """
    Create 3 test agents + synthetic platform_content.
    Returns dict of created IDs for use in subsequent phases.
    """
    logger.info("\n[Phase 1] Setup")
    now = datetime.now(timezone.utc)

    ids = {}

    # Reactive agent
    reactive = (
        supabase.table("agents").insert({
            "user_id": TEST_USER_ID,
            "title": f"{TEST_PREFIX}Reactive",
            "scope": "knowledge",
            "role": "custom",
            "mode": "reactive",
            "trigger_type": "event",
            "trigger_config": {"observation_threshold": 3},
            "origin": "user_configured",
            "status": "active",
            "sources": [],
            "schedule": {"frequency": "once"},
            "agent_memory": {"observations": []},
        }).execute()
    )
    ids["reactive"] = reactive.data[0]["id"]
    logger.info(f"  Created reactive agent: {ids['reactive']}")

    # Proactive agent (next_review overdue by 1h)
    proactive = (
        supabase.table("agents").insert({
            "user_id": TEST_USER_ID,
            "title": f"{TEST_PREFIX}Proactive",
            "scope": "knowledge",
            "role": "custom",
            "mode": "proactive",
            "trigger_type": "schedule",
            "origin": "user_configured",
            "status": "active",
            "sources": [],
            "schedule": {"frequency": "daily"},
            "agent_memory": {"review_log": [], "observations": []},
            "proactive_next_review_at": (now - timedelta(hours=1)).isoformat(),
        }).execute()
    )
    ids["proactive"] = proactive.data[0]["id"]
    logger.info(f"  Created proactive agent: {ids['proactive']}")

    # Coordinator agent (next_review overdue by 1h)
    coordinator = (
        supabase.table("agents").insert({
            "user_id": TEST_USER_ID,
            "title": f"{TEST_PREFIX}Coordinator",
            "scope": "autonomous",
            "role": "orchestrate",
            "mode": "coordinator",
            "trigger_type": "schedule",
            "origin": "user_configured",
            "status": "active",
            "sources": [],
            "schedule": {"frequency": "daily"},
            "agent_memory": {"review_log": [], "created_agents": []},
            "proactive_next_review_at": (now - timedelta(hours=1)).isoformat(),
        }).execute()
    )
    ids["coordinator"] = coordinator.data[0]["id"]
    logger.info(f"  Created coordinator agent: {ids['coordinator']}")

    # Synthetic platform_content for reactive trigger context
    content_ids = []
    for i in range(3):
        c = supabase.table("platform_content").insert({
            "user_id": TEST_USER_ID,
            "platform": "slack",
            "resource_id": "C_TEST_ADR092",
            "resource_name": "test-general",
            "content_type": "message",
            "item_id": f"test-adr092-msg-{i}",
            "content": f"Test message {i} for reactive trigger",
            "metadata": {"channel": "general"},
            "retained": False,
        }).execute()
        content_ids.append(c.data[0]["id"])

    ids["content_ids"] = content_ids
    logger.info(f"  Created {len(content_ids)} synthetic platform_content items")
    logger.info("  [Phase 1] Setup complete")
    return ids


# =============================================================================
# Phase 2: Reactive dispatch — _dispatch_medium_reactive
# =============================================================================

async def phase2_reactive(supabase, ids: dict) -> PhaseResult:
    """Test reactive observation accumulation and threshold-triggered generation."""
    result = PhaseResult("Phase 2: Reactive dispatch")
    logger.info("\n[Phase 2] Reactive dispatch")

    from services.trigger_dispatch import _dispatch_medium_reactive

    reactive_id = ids["reactive"]

    # Fetch the agent dict (as scheduler would)
    d = supabase.table("agents").select("*").eq("id", reactive_id).single().execute().data

    trigger_context = {
        "type": "event",
        "platform": "slack",
        "event_type": "message",
        "resource_id": "general",
        "event_ts": datetime.now(timezone.utc).isoformat(),
        "content_preview": "Test message for reactive trigger",
    }

    # --- Call 1: below threshold (1/3) ---
    r1 = await _dispatch_medium_reactive(supabase, d, "event", trigger_context)
    assert_eq(result, "call 1 action=memory_updated", r1.get("action"), "memory_updated")
    assert_eq(result, "call 1 success=True", r1.get("success"), True)
    assert_eq(result, "call 1 observation_count=1", r1.get("observation_count"), 1)

    # Verify DB state
    fresh1 = supabase.table("agents").select("agent_memory").eq("id", reactive_id).single().execute().data
    obs1 = (fresh1.get("agent_memory") or {}).get("observations", [])
    assert_eq(result, "DB has 1 observation after call 1", len(obs1), 1)
    assert_true(result, "observation has source=event", obs1[0].get("source") == "event")

    # Re-fetch for accurate memory state
    d = supabase.table("agents").select("*").eq("id", reactive_id).single().execute().data

    # --- Call 2: below threshold (2/3) ---
    r2 = await _dispatch_medium_reactive(supabase, d, "event", trigger_context)
    assert_eq(result, "call 2 observation_count=2", r2.get("observation_count"), 2)

    d = supabase.table("agents").select("*").eq("id", reactive_id).single().execute().data

    # --- Call 3: threshold met (3/3) → should trigger generation ---
    # Patch execute_agent_generation to avoid real LLM call
    import services.trigger_dispatch as td_module
    import services.agent_execution as exec_module
    original_generate = exec_module.execute_agent_generation

    async def mock_generate(**kwargs):
        return {"success": True, "run_id": "mock-version-id-001", "action": "generated"}

    exec_module.execute_agent_generation = mock_generate
    try:
        r3 = await _dispatch_medium_reactive(supabase, d, "event", trigger_context)
    finally:
        exec_module.execute_agent_generation = original_generate

    assert_eq(result, "call 3 action=generated", r3.get("action"), "generated")
    assert_eq(result, "call 3 success=True", r3.get("success"), True)
    assert_true(result, "call 3 reactive_threshold_met=True", r3.get("reactive_threshold_met") is True)
    assert_eq(result, "call 3 observations_cleared=3", r3.get("observations_cleared"), 3)

    # Verify DB: observations cleared
    fresh3 = supabase.table("agents").select("agent_memory").eq("id", reactive_id).single().execute().data
    obs3 = (fresh3.get("agent_memory") or {}).get("observations", [])
    assert_eq(result, "observations cleared after threshold generation", len(obs3), 0)

    last_gen = (fresh3.get("agent_memory") or {}).get("last_generated_at")
    assert_true(result, "last_generated_at set after threshold generation", last_gen is not None)

    return result


# =============================================================================
# Phase 3: Proactive review — apply_review_decision
# =============================================================================

async def phase3_proactive(supabase, ids: dict) -> PhaseResult:
    """Test apply_review_decision() for observe, sleep, and generate actions."""
    result = PhaseResult("Phase 3: Proactive review decision")
    logger.info("\n[Phase 3] Proactive review — apply_review_decision")

    from services.proactive_review import apply_review_decision

    proactive_id = ids["proactive"]
    now = datetime.now(timezone.utc)

    def fetch_memory():
        return (
            supabase.table("agents")
            .select("agent_memory, proactive_next_review_at")
            .eq("id", proactive_id)
            .single()
            .execute()
            .data
        )

    d = supabase.table("agents").select("*").eq("id", proactive_id).single().execute().data

    # --- observe action ---
    apply_review_decision(supabase, d, {"action": "observe", "note": "Test observation note"})
    s1 = fetch_memory()
    review_log = (s1.get("agent_memory") or {}).get("review_log", [])
    assert_eq(result, "observe: review_log has 1 entry", len(review_log), 1)
    assert_eq(result, "observe: log action=observe", review_log[0].get("action"), "observe")
    assert_eq(result, "observe: log note set", review_log[0].get("note"), "Test observation note")
    next_review1 = s1.get("proactive_next_review_at")
    assert_true(result, "observe: proactive_next_review_at set", next_review1 is not None)
    nr1_dt = parse_dt(next_review1)
    hours_ahead = (nr1_dt - now).total_seconds() / 3600
    assert_true(result, "observe: next_review ~24h ahead", 20 <= hours_ahead <= 28,
                f"hours_ahead={hours_ahead:.1f}")

    # --- sleep action with explicit until ---
    until_dt = (now + timedelta(hours=48)).replace(microsecond=0)
    until_str = until_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    d = supabase.table("agents").select("*").eq("id", proactive_id).single().execute().data
    apply_review_decision(supabase, d, {"action": "sleep", "until": until_str, "note": "Quiet domain"})
    s2 = fetch_memory()
    review_log2 = (s2.get("agent_memory") or {}).get("review_log", [])
    assert_eq(result, "sleep: review_log has 2 entries", len(review_log2), 2)
    assert_eq(result, "sleep: latest action=sleep", review_log2[-1].get("action"), "sleep")
    next_review2 = s2.get("proactive_next_review_at")
    nr2_dt = parse_dt(next_review2)
    hours_ahead2 = (nr2_dt - now).total_seconds() / 3600
    assert_true(result, "sleep: next_review ~48h ahead", 44 <= hours_ahead2 <= 52,
                f"hours_ahead={hours_ahead2:.1f}")

    # --- generate action ---
    d = supabase.table("agents").select("*").eq("id", proactive_id).single().execute().data
    apply_review_decision(supabase, d, {"action": "generate"})
    s3 = fetch_memory()
    review_log3 = (s3.get("agent_memory") or {}).get("review_log", [])
    assert_eq(result, "generate: review_log has 3 entries", len(review_log3), 3)
    assert_eq(result, "generate: latest action=generate", review_log3[-1].get("action"), "generate")
    last_gen = (s3.get("agent_memory") or {}).get("last_generated_at")
    assert_true(result, "generate: last_generated_at set", last_gen is not None)
    next_review3 = s3.get("proactive_next_review_at")
    nr3_dt = parse_dt(next_review3)
    hours_ahead3 = (nr3_dt - now).total_seconds() / 3600
    assert_true(result, "generate: next_review ~24h ahead", 20 <= hours_ahead3 <= 28,
                f"hours_ahead={hours_ahead3:.1f}")

    return result


# =============================================================================
# Phase 4: Coordinator primitives
# =============================================================================

async def phase4_coordinator(supabase, ids: dict) -> PhaseResult:
    """Test CreateAgent and AdvanceAgentSchedule primitives."""
    result = PhaseResult("Phase 4: Coordinator primitives")
    logger.info("\n[Phase 4] Coordinator primitives")

    from services.primitives.coordinator import (
        handle_create_agent,
        handle_advance_agent_schedule,
    )

    coordinator_id = ids["coordinator"]
    created_child_ids: list[str] = []

    class FakeAuth:
        client = supabase
        user_id = TEST_USER_ID
        headless = True
        agent_sources = []
        coordinator_agent_id = coordinator_id

    auth = FakeAuth()

    # --- CreateAgent: success case ---
    r1 = await handle_create_agent(auth, {
        "title": f"{TEST_PREFIX}Child Meeting Prep",
        "role": "prepare",
        "agent_instructions": "Prepare briefing for external meeting",
        "dedup_key": "meeting:test-event-abc123",
    })
    assert_eq(result, "CreateAgent success=True", r1.get("success"), True)
    assert_true(result, "CreateAgent returns agent_id", r1.get("agent_id") is not None)
    assert_eq(result, "CreateAgent dedup_key echoed", r1.get("dedup_key"), "meeting:test-event-abc123")

    child_id = r1.get("agent_id")
    created_child_ids.append(child_id)
    ids["child_id"] = child_id

    # Verify child in DB
    child = supabase.table("agents").select("*").eq("id", child_id).single().execute().data
    assert_eq(result, "child origin=coordinator_created", child.get("origin"), "coordinator_created")
    assert_eq(result, "child trigger_type=manual", child.get("trigger_type"), "manual")
    assert_eq(result, "child status=active", child.get("status"), "active")
    assert_true(result, "child next_run_at is set", child.get("next_run_at") is not None)
    now = datetime.now(timezone.utc)
    next_run = parse_dt(child["next_run_at"])
    secs_ago = (now - next_run).total_seconds()
    assert_true(result, "child next_run_at is recent (within 60s)", -5 <= secs_ago <= 60,
                f"secs_ago={secs_ago:.1f}")

    # Verify created_agents dedup log on coordinator
    coord = supabase.table("agents").select("agent_memory").eq("id", coordinator_id).single().execute().data
    created_log = (coord.get("agent_memory") or {}).get("created_agents", [])
    assert_true(result, "created_agents log has 1 entry", len(created_log) >= 1)
    dedup_keys = [e.get("dedup_key") for e in created_log]
    assert_true(result, "dedup_key in created_agents log", "meeting:test-event-abc123" in dedup_keys)

    # --- CreateAgent: missing title ---
    r_no_title = await handle_create_agent(auth, {"role": "prepare"})
    assert_eq(result, "CreateAgent missing title → success=False", r_no_title.get("success"), False)
    assert_eq(result, "CreateAgent missing title → error=missing_title", r_no_title.get("error"), "missing_title")

    # --- AdvanceAgentSchedule: success case ---
    r_adv = await handle_advance_agent_schedule(auth, {
        "agent_id": child_id,
        "reason": "test advance",
    })
    assert_eq(result, "AdvanceAgentSchedule success=True", r_adv.get("success"), True)

    # Verify next_run_at updated to within 5s of now
    child_adv = supabase.table("agents").select("next_run_at").eq("id", child_id).single().execute().data
    adv_run = parse_dt(child_adv["next_run_at"])
    now2 = datetime.now(timezone.utc)
    secs = abs((now2 - adv_run).total_seconds())
    assert_true(result, "advanced next_run_at within 5s of now", secs <= 5, f"secs={secs:.1f}")

    # --- AdvanceAgentSchedule: non-existent agent ---
    r_notfound = await handle_advance_agent_schedule(auth, {
        "agent_id": "00000000-0000-0000-0000-000000000000",
        "reason": "test",
    })
    assert_eq(result, "AdvanceAgentSchedule non-existent → success=False", r_notfound.get("success"), False)
    assert_eq(result, "AdvanceAgentSchedule non-existent → error=not_found", r_notfound.get("error"), "not_found")

    # --- AdvanceAgentSchedule: paused agent ---
    paused = supabase.table("agents").insert({
        "user_id": TEST_USER_ID,
        "title": f"{TEST_PREFIX}Paused",
        "scope": "knowledge",
        "role": "custom",
        "mode": "recurring",
        "trigger_type": "schedule",
        "origin": "user_configured",
        "status": "paused",
        "sources": [],
        "schedule": {"frequency": "daily"},
    }).execute()
    paused_id = paused.data[0]["id"]
    created_child_ids.append(paused_id)
    ids.setdefault("cleanup_extra", []).append(paused_id)

    r_paused = await handle_advance_agent_schedule(auth, {
        "agent_id": paused_id,
        "reason": "test",
    })
    assert_eq(result, "AdvanceAgentSchedule paused → success=False", r_paused.get("success"), False)
    assert_eq(result, "AdvanceAgentSchedule paused → error=not_active", r_paused.get("error"), "not_active")

    return result


# =============================================================================
# Phase 5: _parse_review_response — pure unit tests
# =============================================================================

async def phase5_parse_response() -> PhaseResult:
    """Test _parse_review_response() edge cases. No DB calls."""
    result = PhaseResult("Phase 5: _parse_review_response")
    logger.info("\n[Phase 5] _parse_review_response edge cases")

    from services.proactive_review import _parse_review_response

    # Valid generate
    r = _parse_review_response('{"action": "generate"}')
    assert_eq(result, "valid generate → action=generate", r.get("action"), "generate")

    # Valid observe with note
    r = _parse_review_response('{"action": "observe", "note": "Something interesting"}')
    assert_eq(result, "valid observe → action=observe", r.get("action"), "observe")
    assert_eq(result, "valid observe → note set", r.get("note"), "Something interesting")

    # Valid sleep with until
    r = _parse_review_response('{"action": "sleep", "until": "2026-03-10T09:00:00Z"}')
    assert_eq(result, "valid sleep → action=sleep", r.get("action"), "sleep")
    assert_eq(result, "valid sleep → until set", r.get("until"), "2026-03-10T09:00:00Z")

    # Wrapped in markdown fences
    fenced = '```json\n{"action": "generate"}\n```'
    r = _parse_review_response(fenced)
    assert_eq(result, "fenced JSON → action=generate", r.get("action"), "generate")

    # Malformed JSON
    r = _parse_review_response('{"action": "generate"')
    assert_eq(result, "malformed JSON → action=observe", r.get("action"), "observe")
    assert_true(result, "malformed JSON → note contains error",
                bool(r.get("note")))

    # Unknown action
    r = _parse_review_response('{"action": "do_something_weird"}')
    assert_eq(result, "unknown action → action=observe", r.get("action"), "observe")
    assert_true(result, "unknown action → note mentions action", "do_something_weird" in r.get("note", ""))

    # Empty string
    r = _parse_review_response("")
    assert_eq(result, "empty string → action=observe", r.get("action"), "observe")
    assert_true(result, "empty string → note set", bool(r.get("note")))

    return result


# =============================================================================
# Phase 6: Scheduler query verification
# =============================================================================

async def phase6_scheduler_queries(supabase, ids: dict) -> PhaseResult:
    """Verify scheduler DB queries correctly partition agents by mode."""
    result = PhaseResult("Phase 6: Scheduler query filters")
    logger.info("\n[Phase 6] Scheduler query filters")

    reactive_id = ids["reactive"]
    proactive_id = ids["proactive"]
    coordinator_id = ids["coordinator"]

    now = datetime.now(timezone.utc).isoformat()

    # --- get_due_agents() query: mode IN ('recurring', 'goal') ---
    # Reactive/proactive/coordinator should NOT appear
    due_recurring = (
        supabase.table("agents")
        .select("id, mode")
        .eq("user_id", TEST_USER_ID)
        .in_("mode", ["recurring", "goal"])
        .in_("status", ["active"])
        .lte("next_run_at", now)
        .execute()
    )
    due_ids = {r["id"] for r in (due_recurring.data or [])}

    assert_true(result, "reactive NOT in recurring query", reactive_id not in due_ids,
                f"reactive_id found in recurring query")
    assert_true(result, "proactive NOT in recurring query", proactive_id not in due_ids,
                f"proactive_id found in recurring query")
    assert_true(result, "coordinator NOT in recurring query", coordinator_id not in due_ids,
                f"coordinator_id found in recurring query")

    # --- get_due_proactive_agents() query: mode IN ('proactive', 'coordinator') ---
    # with proactive_next_review_at <= now
    due_proactive = (
        supabase.table("agents")
        .select("id, mode")
        .eq("user_id", TEST_USER_ID)
        .in_("mode", ["proactive", "coordinator"])
        .in_("status", ["active"])
        .lte("proactive_next_review_at", now)
        .execute()
    )
    due_proactive_ids = {r["id"] for r in (due_proactive.data or [])}

    # Proactive's proactive_next_review_at was set to now-1h in setup,
    # but Phase 3 updated it to now+24h — so it should NOT be in results now.
    # Coordinator's proactive_next_review_at was set to now-1h in setup
    # and was not changed in Phase 4, so it SHOULD still be in results.
    assert_true(result, "coordinator IS in proactive query (review overdue)", coordinator_id in due_proactive_ids,
                f"coordinator_id not found in proactive query")
    assert_true(result, "reactive NOT in proactive query", reactive_id not in due_proactive_ids,
                f"reactive_id found in proactive query")

    return result


# =============================================================================
# Phase 7: Cleanup
# =============================================================================

async def phase7_cleanup(supabase, ids: dict) -> None:
    """Delete all test agents and synthetic platform_content."""
    logger.info("\n[Phase 7] Cleanup")

    deleted = 0

    # Delete all TEST_ADR092_ agents (cascade handles versions)
    test_agents = (
        supabase.table("agents")
        .select("id")
        .eq("user_id", TEST_USER_ID)
        .like("title", f"{TEST_PREFIX}%")
        .execute()
    )
    for row in (test_agents.data or []):
        # Delete versions first (no cascade in PostgREST RLS context)
        supabase.table("agent_runs").delete().eq("agent_id", row["id"]).execute()
        supabase.table("agents").delete().eq("id", row["id"]).execute()
        deleted += 1

    logger.info(f"  Deleted {deleted} test agent(s)")

    # Delete synthetic platform_content
    for cid in ids.get("content_ids", []):
        supabase.table("platform_content").delete().eq("id", cid).execute()
    logger.info(f"  Deleted {len(ids.get('content_ids', []))} synthetic platform_content item(s)")

    logger.info("  [Phase 7] Cleanup complete")


# =============================================================================
# Main runner
# =============================================================================

async def main() -> None:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        sys.exit(1)

    from supabase import create_client
    supabase = create_client(supabase_url, supabase_key)

    ids = {}
    results: list[PhaseResult] = []

    try:
        # Phase 1: Setup (no result tracking — if this fails, abort)
        ids = await phase1_setup(supabase)

        # Phase 2–6: Test phases
        results.append(await phase2_reactive(supabase, ids))
        results.append(await phase3_proactive(supabase, ids))
        results.append(await phase4_coordinator(supabase, ids))
        results.append(await phase5_parse_response())
        results.append(await phase6_scheduler_queries(supabase, ids))

    except Exception as e:
        import traceback
        logger.error(f"\nFatal error during test run: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Phase 7: Always clean up
        if ids:
            await phase7_cleanup(supabase, ids)

    # ==========================================================================
    # Report
    # ==========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("ADR-092 TEST RESULTS")
    logger.info("=" * 60)

    total_passed = 0
    total_failed = 0

    for r in results:
        status = "PASS" if r.success else "FAIL"
        logger.info(f"  [{status}] {r.phase}: {r.passed} passed, {r.failed} failed")
        if r.errors:
            for e in r.errors:
                logger.info(f"         → {e}")
        total_passed += r.passed
        total_failed += r.failed

    logger.info("=" * 60)
    logger.info(f"  Total: {total_passed} passed, {total_failed} failed")
    logger.info("=" * 60)

    if total_failed > 0:
        sys.exit(1)
    else:
        logger.info("  All phases passed ✓")


if __name__ == "__main__":
    asyncio.run(main())
