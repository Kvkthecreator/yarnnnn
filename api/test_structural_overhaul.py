"""
Structural Overhaul Test Suite — TP Context Visibility & Active Workspace Management

Tests the changes from [2026.03.05.1] and [2026.03.05.3]:
  Phase 1: Version entity in refs.py TABLE_MAP + search scope
  Phase 2: Latest version in scoped working memory
  Phase 3: Enriched headless prompt (user context + full memory)
  Phase 4: DEFAULT_INSTRUCTIONS + instruction seeding on Write
  Phase 5: Behavioral triggers in TP prompt (qualitative)
  Phase 6: Workspace primitives (append_observation, set_goal, agent_instructions)

Strategy: Real DB writes with TEST_OVERHAUL_ prefix. No live LLM calls.
Test user: kvkthecreator@gmail.com

Usage:
    cd api && python test_structural_overhaul.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

# Load .env
env_path = Path(__file__).parent / ".env"
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

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
TEST_PREFIX = "TEST_OVERHAUL_"


# =============================================================================
# Result tracking (same pattern as test_adr092_modes.py)
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


def assert_eq(r: PhaseResult, label: str, actual, expected) -> None:
    if actual == expected:
        r.ok(label)
    else:
        r.fail(label, f"expected {expected!r}, got {actual!r}")


def assert_true(r: PhaseResult, label: str, condition: bool, detail: str = "") -> None:
    if condition:
        r.ok(label)
    else:
        r.fail(label, detail)


def assert_in(r: PhaseResult, label: str, needle: str, haystack: str) -> None:
    if needle in haystack:
        r.ok(label)
    else:
        r.fail(label, f"'{needle}' not found in output ({len(haystack)} chars)")


def assert_not_in(r: PhaseResult, label: str, needle: str, haystack: str) -> None:
    if needle not in haystack:
        r.ok(label)
    else:
        r.fail(label, f"'{needle}' should NOT be in output but was found")


# =============================================================================
# Setup & teardown
# =============================================================================

def get_client():
    from supabase import create_client
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )


class MockAuth:
    def __init__(self, user_id: str, client: Any):
        self.user_id = user_id
        self.client = client


def cleanup(client):
    """Remove all test data."""
    # Get test agent IDs first (for cascading cleanup)
    dels = client.table("agents").select("id").eq(
        "user_id", TEST_USER_ID
    ).ilike("title", f"{TEST_PREFIX}%").execute()
    agent_ids = [d["id"] for d in (dels.data or [])]

    if agent_ids:
        # Delete versions for test agents
        for did in agent_ids:
            client.table("agent_runs").delete().eq(
                "agent_id", did
            ).execute()
        # Delete agents
        for did in agent_ids:
            client.table("agents").delete().eq("id", did).execute()

    logger.info(f"Cleanup: removed {len(agent_ids)} test agents + versions")


# =============================================================================
# Phase 1: Version Entity Access (refs.py + search.py)
# =============================================================================

async def phase_1_version_access(auth: MockAuth) -> PhaseResult:
    r = PhaseResult("Phase 1: Version Entity Access")
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 1: Version Entity Access")
    logger.info(f"{'='*60}")

    from services.primitives.refs import parse_ref, TABLE_MAP, ENTITY_TYPES, resolve_ref
    from services.primitives import execute_primitive

    # 1a: version in ENTITY_TYPES
    assert_in(r, "version in ENTITY_TYPES", "version", str(ENTITY_TYPES))

    # 1b: version in TABLE_MAP
    assert_eq(r, "TABLE_MAP[version] = agent_runs",
              TABLE_MAP.get("version"), "agent_runs")

    # 1c: parse_ref accepts version refs
    try:
        ref = parse_ref("version:latest?agent_id=abc123")
        assert_eq(r, "parse_ref version:latest type", ref.entity_type, "version")
        assert_eq(r, "parse_ref version:latest identifier", ref.identifier, "latest")
        assert_eq(r, "parse_ref version:latest query",
                  ref.query.get("agent_id"), "abc123")
    except Exception as e:
        r.fail("parse_ref version:latest", str(e))

    # 1d: Create a test agent + version, then resolve refs
    del_id = str(uuid4())
    ver_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    auth.client.table("agents").insert({
        "id": del_id,
        "user_id": TEST_USER_ID,
        "title": f"{TEST_PREFIX}Version Test",
        "scope": "cross_platform",
        "role": "synthesize",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }).execute()

    auth.client.table("agent_runs").insert({
        "id": ver_id,
        "agent_id": del_id,
        "version_number": 1,
        "status": "approved",
        "draft_content": "This is test version content for the structural overhaul test suite.",
        "final_content": "This is test version content for the structural overhaul test suite.",
        "created_at": now,
    }).execute()

    # 1e: Read(ref="version:latest?agent_id=X")
    result = await execute_primitive(auth, "LookupEntity", {
        "ref": f"version:latest?agent_id={del_id}"
    })
    assert_true(r, "Read version:latest success", result.get("success", False),
                f"Read failed: {result.get('message', '')}")
    if result.get("success"):
        data = result.get("data", {})
        assert_eq(r, "Read version:latest version_number", data.get("version_number"), 1)
        assert_eq(r, "Read version:latest status", data.get("status"), "approved")

    # 1f: Read(ref="version:<uuid>")
    result = await execute_primitive(auth, "LookupEntity", {
        "ref": f"version:{ver_id}"
    })
    assert_true(r, "Read version:uuid success", result.get("success", False),
                f"Read failed: {result.get('message', '')}")

    # 1g: Search(scope="version")
    result = await execute_primitive(auth, "SearchEntities", {
        "query": "structural overhaul",
        "scope": "version",
        "agent_id": del_id,
    })
    assert_true(r, "Search version scope success", result.get("success", False),
                f"Search failed: {result.get('message', '')}")
    results = result.get("results", [])
    assert_true(r, "Search version found result", len(results) > 0,
                f"Expected results, got {len(results)}")

    # 1h: Read(ref="version:*?agent_id=X") — list all versions
    result = await execute_primitive(auth, "LookupEntity", {
        "ref": f"version:*?agent_id={del_id}"
    })
    assert_true(r, "Read version:* returns list", isinstance(result.get("data"), list),
                f"Expected list, got {type(result.get('data'))}")

    # 1i: Security — version scoping through agent ownership
    # Create a fake auth with different user_id
    fake_auth = MockAuth("00000000-0000-0000-0000-000000000000", auth.client)
    result = await execute_primitive(fake_auth, "LookupEntity", {
        "ref": f"version:latest?agent_id={del_id}"
    })
    # Should return not_found (not_error) because fake user doesn't own the agent
    assert_true(r, "Version scoping blocks other users",
                not result.get("success") or result.get("data") is None,
                "Other user should not be able to read this version")

    return r


# =============================================================================
# Phase 2: Latest Version in Scoped Working Memory
# =============================================================================

async def phase_2_working_memory_version(auth: MockAuth) -> PhaseResult:
    r = PhaseResult("Phase 2: Latest Version in Scoped Working Memory")
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 2: Latest Version in Scoped Working Memory")
    logger.info(f"{'='*60}")

    from services.working_memory import _extract_agent_scope

    # Get test agent
    dels = auth.client.table("agents").select("*").eq(
        "user_id", TEST_USER_ID
    ).ilike("title", f"{TEST_PREFIX}Version Test").execute()
    assert_true(r, "Test agent exists", len(dels.data or []) > 0)
    if not dels.data:
        return r

    agent = dels.data[0]

    # 2a: _extract_agent_scope includes latest_version
    scope = await _extract_agent_scope(agent, auth.client)
    assert_true(r, "scope has latest_version key", "latest_version" in scope,
                f"Keys: {list(scope.keys())}")
    if "latest_version" in scope:
        lv = scope["latest_version"]
        assert_eq(r, "latest_version.version_number", lv.get("version_number"), 1)
        assert_eq(r, "latest_version.status", lv.get("status"), "approved")
        assert_true(r, "latest_version.content_preview populated",
                    len(lv.get("content_preview", "")) > 0)

    # 2b: Scope contains agent ref for Edit calls
    assert_true(r, "scope has agent id", "id" in scope and scope["id"])
    assert_true(r, "scope has title", "title" in scope and scope["title"])

    # 2c: Agent without versions should NOT crash
    no_ver_del = {
        "id": str(uuid4()),
        "title": "No versions",
        "role": "custom",
        "scope": "knowledge",
    }
    scope_empty = await _extract_agent_scope(no_ver_del, auth.client)
    assert_true(r, "No crash for agent without versions",
                "latest_version" not in scope_empty,
                "Should not have latest_version for nonexistent agent")

    return r


# =============================================================================
# Phase 3: Enriched Headless Prompt
# =============================================================================

async def phase_3_headless_prompt(auth: MockAuth) -> PhaseResult:
    r = PhaseResult("Phase 3: Enriched Headless Prompt")
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 3: Enriched Headless Prompt")
    logger.info(f"{'='*60}")

    from services.agent_execution import _build_headless_system_prompt

    # 3a: User context injection
    user_ctx = [
        {"key": "name", "value": "Kevin"},
        {"key": "role", "value": "CEO"},
        {"key": "company", "value": "YARNNN"},
        {"key": "timezone", "value": "Asia/Seoul"},
        {"key": "tone_formal", "value": "high"},
        {"key": "preference:brevity", "value": "Keep reports under 500 words"},
    ]
    prompt = _build_headless_system_prompt(
        role="synthesize",
        user_context=user_ctx,
    )
    assert_in(r, "User context section present", "## User Context", prompt)
    assert_in(r, "Name injected", "Kevin", prompt)
    assert_in(r, "Company injected", "YARNNN", prompt)
    assert_in(r, "Tone preference injected", "Tone Formal", prompt)
    assert_in(r, "Preference injected", "Prefers: Keep reports under 500 words", prompt)

    # 3b: Agent instructions injection
    agent = {
        "agent_instructions": "Focus on top 3 items. Use bullet points only.",
        "agent_memory": {
            "observations": [
                {"date": "2026-03-01", "note": "User prefers concise format"},
                {"date": "2026-03-03", "note": "Q4 data finalized"},
            ],
            "goal": {
                "description": "Ship quarterly report",
                "status": "in_progress",
            },
            "review_log": [
                {"date": "2026-03-02", "note": "Approved v1 with minor edits"},
                {"date": "2026-03-04", "note": "Requested more data points"},
            ],
        },
    }
    prompt = _build_headless_system_prompt(
        role="synthesize",
        agent=agent,
        user_context=user_ctx,
    )
    assert_in(r, "Instructions section present", "## Agent Instructions", prompt)
    assert_in(r, "Instructions content", "top 3 items", prompt)
    assert_in(r, "Goal present", "Ship quarterly report", prompt)
    assert_in(r, "Goal status present", "in_progress", prompt)
    assert_in(r, "Observations present", "User prefers concise format", prompt)
    assert_in(r, "Review log present", "Approved v1 with minor edits", prompt)

    # 3c: Empty user_context should not crash
    prompt_no_ctx = _build_headless_system_prompt(
        role="digest",
        user_context=None,
    )
    assert_not_in(r, "No User Context section when None", "## User Context", prompt_no_ctx)
    assert_in(r, "Base prompt still works", "You are", prompt_no_ctx)

    # 3d: Empty agent_memory should not crash
    prompt_no_mem = _build_headless_system_prompt(
        role="synthesize",
        agent={"agent_memory": {}},
    )
    assert_not_in(r, "No memory section when empty", "## Agent Memory", prompt_no_mem)

    return r


# =============================================================================
# Phase 4: DEFAULT_INSTRUCTIONS + Write Seeding
# =============================================================================

async def phase_4_default_instructions(auth: MockAuth) -> PhaseResult:
    r = PhaseResult("Phase 4: DEFAULT_INSTRUCTIONS + Write Seeding")
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 4: DEFAULT_INSTRUCTIONS + Write Seeding")
    logger.info(f"{'='*60}")

    from services.agent_pipeline import DEFAULT_INSTRUCTIONS
    from services.primitives import execute_primitive

    # 4a: All expected role types have instructions (ADR-109: keyed by role name)
    expected_types = ["digest", "prepare", "synthesize", "monitor", "research", "custom"]
    for dtype in expected_types:
        assert_true(r, f"DEFAULT_INSTRUCTIONS[{dtype}] exists",
                    dtype in DEFAULT_INSTRUCTIONS and len(DEFAULT_INSTRUCTIONS[dtype]) > 10,
                    f"Missing or empty for {dtype}")

    # 4b: Write seeds instructions when not provided
    result = await execute_primitive(auth, "Write", {
        "ref": "agent:new",
        "content": {
            "title": f"{TEST_PREFIX}Seeded Instructions",
            "role": "digest",
        },
    })
    assert_true(r, "Write success", result.get("success", False),
                f"Write failed: {result.get('message', '')}")

    if result.get("success"):
        data = result.get("data", {})
        instructions = data.get("agent_instructions", "")
        assert_true(r, "Instructions seeded on create",
                    len(instructions) > 10,
                    f"Instructions: '{instructions}'")
        assert_in(r, "Seeded instructions match digest type",
                  "Summarize key activity", instructions)

    # 4c: Write does NOT override explicit instructions
    result2 = await execute_primitive(auth, "Write", {
        "ref": "agent:new",
        "content": {
            "title": f"{TEST_PREFIX}Explicit Instructions",
            "role": "synthesize",
            "agent_instructions": "My custom instructions here",
        },
    })
    assert_true(r, "Write with explicit instructions success",
                result2.get("success", False))
    if result2.get("success"):
        data2 = result2.get("data", {})
        assert_eq(r, "Explicit instructions preserved",
                  data2.get("agent_instructions"), "My custom instructions here")

    return r


# =============================================================================
# Phase 5: Behavioral Triggers (Qualitative — Prompt Verification)
# =============================================================================

async def phase_5_behavioral_triggers(auth: MockAuth) -> PhaseResult:
    r = PhaseResult("Phase 5: Behavioral Triggers (Prompt Verification)")
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 5: Behavioral Triggers (Prompt Verification)")
    logger.info(f"{'='*60}")

    from agents.yarnnn_prompts.behaviors import BEHAVIORS_SECTION
    from agents.yarnnn_prompts.tools import TOOLS_SECTION
    from agents.yarnnn_prompts import build_system_prompt

    # 5a: Stale references removed
    assert_not_in(r, "No 'Work Boundary' in behaviors",
                  "Work Boundary", BEHAVIORS_SECTION)
    assert_not_in(r, "No 'ADR-061' in behaviors",
                  "ADR-061", BEHAVIORS_SECTION)
    assert_not_in(r, "No 'Path A' in behaviors",
                  "Path A", BEHAVIORS_SECTION)
    assert_not_in(r, "No 'Path B' in behaviors",
                  "Path B", BEHAVIORS_SECTION)

    # 5b: New sections present
    assert_in(r, "Conversation vs Generation Boundary present",
              "Conversation vs Generation Boundary", BEHAVIORS_SECTION)
    assert_in(r, "Agent Workspace Management section present",
              "Agent Workspace Management", BEHAVIORS_SECTION)

    # 5c: Dual posture explicitly documented
    assert_in(r, "User memory passive posture documented",
              "User memory", BEHAVIORS_SECTION)
    assert_in(r, "Agent workspace active posture documented",
              "active", BEHAVIORS_SECTION)
    assert_in(r, "Nightly cron mentioned for user memory",
              "Nightly cron", BEHAVIORS_SECTION)

    # 5d: Behavioral triggers present
    assert_in(r, "Update instructions trigger",
              "Update instructions", BEHAVIORS_SECTION)
    assert_in(r, "Append observations trigger",
              "Append observations", BEHAVIORS_SECTION)
    assert_in(r, "Update goals trigger",
              "Update goals", BEHAVIORS_SECTION)

    # 5e: When NOT to act documented
    assert_in(r, "One-off request guard",
              "one-off requests", BEHAVIORS_SECTION)
    assert_in(r, "Trivial observation guard",
              "trivial observations", BEHAVIORS_SECTION)

    # 5f: Scoped vs general session distinction
    assert_in(r, "Scoped session guidance",
              "agent-scoped session", BEHAVIORS_SECTION)
    assert_in(r, "General session hands-off",
              "hands-off", BEHAVIORS_SECTION)

    # 5g: Edit syntax in behaviors matches actual primitive
    assert_in(r, "append_observation syntax correct",
              "append_observation: {note:", BEHAVIORS_SECTION)
    assert_in(r, "set_goal syntax correct",
              "set_goal: {description:", BEHAVIORS_SECTION)
    assert_in(r, "agent_instructions syntax correct",
              "agent_instructions:", BEHAVIORS_SECTION)

    # 5g2: Ref usage guidance in behaviors
    assert_in(r, "Behaviors instructs TP to use Ref from working memory",
              "do NOT guess", BEHAVIORS_SECTION)

    # 5h: tools.py cross-references behaviors
    assert_in(r, "tools.py references behaviors section",
              "Agent Workspace Management", TOOLS_SECTION)

    # 5i: tools.py Edit syntax also correct
    assert_in(r, "tools.py append_observation syntax",
              "append_observation: {note:", TOOLS_SECTION)
    assert_in(r, "tools.py set_goal syntax",
              "set_goal: {description:", TOOLS_SECTION)

    # 5j: No stale "work" entity references in tools
    assert_not_in(r, "No 'work' entity type in tools Reference Syntax",
                  '"work"', TOOLS_SECTION)

    # 5k: Full system prompt builds without error
    try:
        full_prompt = build_system_prompt(
            with_tools=True,
            context="Test context block",
        )
        assert_true(r, "Full system prompt builds successfully",
                    len(full_prompt) > 500,
                    f"Prompt too short: {len(full_prompt)} chars")
        assert_in(r, "Full prompt includes behaviors",
                  "Agent Workspace Management", full_prompt)
        assert_in(r, "Full prompt includes tools",
                  "Agent Workspace", full_prompt)
    except Exception as e:
        r.fail("Full system prompt build", str(e))

    return r


# =============================================================================
# Phase 6: Workspace Primitives (append_observation, set_goal, instructions)
# =============================================================================

async def phase_6_workspace_primitives(auth: MockAuth) -> PhaseResult:
    r = PhaseResult("Phase 6: Workspace Primitives (E2E)")
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 6: Workspace Primitives (E2E)")
    logger.info(f"{'='*60}")

    from services.primitives import execute_primitive

    # Get a test agent
    dels = auth.client.table("agents").select("id").eq(
        "user_id", TEST_USER_ID
    ).ilike("title", f"{TEST_PREFIX}%").limit(1).execute()
    assert_true(r, "Test agent available", len(dels.data or []) > 0)
    if not dels.data:
        return r

    del_id = dels.data[0]["id"]

    # 6a: Update agent_instructions via Edit
    result = await execute_primitive(auth, "EditEntity", {
        "ref": f"agent:{del_id}",
        "changes": {
            "agent_instructions": "Keep it under 300 words. Use bullet points. Focus on blockers."
        },
    })
    assert_true(r, "Edit agent_instructions success",
                result.get("success", False),
                f"Edit failed: {result.get('message', '')}")

    # Verify persisted
    check = auth.client.table("agents").select(
        "agent_instructions"
    ).eq("id", del_id).execute()
    if check.data:
        assert_in(r, "Instructions persisted correctly",
                  "300 words", check.data[0].get("agent_instructions", ""))

    # 6b: Append observation via Edit
    result = await execute_primitive(auth, "EditEntity", {
        "ref": f"agent:{del_id}",
        "changes": {
            "append_observation": {
                "note": "User found v1 too verbose — prefers concise bullet format"
            }
        },
    })
    assert_true(r, "append_observation success", result.get("success", False),
                f"Failed: {result.get('message', '')}")
    assert_in(r, "append_observation in changes_applied",
              "append_observation", str(result.get("changes_applied", [])))

    # Verify observation persisted in JSONB
    check = auth.client.table("agents").select(
        "agent_memory"
    ).eq("id", del_id).execute()
    if check.data:
        memory = check.data[0].get("agent_memory") or {}
        observations = memory.get("observations", [])
        assert_true(r, "Observation persisted in JSONB",
                    len(observations) >= 1,
                    f"Observations: {observations}")
        if observations:
            assert_in(r, "Observation content correct",
                      "too verbose", observations[-1].get("note", ""))

    # 6c: Second observation appends (doesn't replace)
    result2 = await execute_primitive(auth, "EditEntity", {
        "ref": f"agent:{del_id}",
        "changes": {
            "append_observation": {
                "note": "Q4 financial data is now finalized"
            }
        },
    })
    assert_true(r, "Second append_observation success", result2.get("success", False))

    check2 = auth.client.table("agents").select(
        "agent_memory"
    ).eq("id", del_id).execute()
    if check2.data:
        memory2 = check2.data[0].get("agent_memory") or {}
        observations2 = memory2.get("observations", [])
        assert_eq(r, "Two observations accumulated", len(observations2), 2)

    # 6d: Set goal via Edit
    result = await execute_primitive(auth, "EditEntity", {
        "ref": f"agent:{del_id}",
        "changes": {
            "set_goal": {
                "description": "Ship quarterly board report",
                "status": "in_progress",
                "milestones": ["Draft", "Review", "Publish"],
            }
        },
    })
    assert_true(r, "set_goal success", result.get("success", False),
                f"Failed: {result.get('message', '')}")

    # Verify goal persisted without clobbering observations
    check3 = auth.client.table("agents").select(
        "agent_memory"
    ).eq("id", del_id).execute()
    if check3.data:
        memory3 = check3.data[0].get("agent_memory") or {}
        goal = memory3.get("goal", {})
        observations3 = memory3.get("observations", [])
        assert_eq(r, "Goal description persisted",
                  goal.get("description"), "Ship quarterly board report")
        assert_eq(r, "Goal milestones persisted",
                  len(goal.get("milestones", [])), 3)
        assert_eq(r, "Observations NOT clobbered by set_goal",
                  len(observations3), 2)

    # 6e: Invalid append_observation (missing note) returns error
    result = await execute_primitive(auth, "EditEntity", {
        "ref": f"agent:{del_id}",
        "changes": {
            "append_observation": {"source": "user"}  # Missing required 'note'
        },
    })
    assert_true(r, "Invalid observation returns error",
                not result.get("success"),
                "Should have failed without 'note'")
    assert_eq(r, "Error type is invalid_observation",
              result.get("error"), "invalid_observation")

    # 6f: Invalid set_goal (missing description) returns error
    result = await execute_primitive(auth, "EditEntity", {
        "ref": f"agent:{del_id}",
        "changes": {
            "set_goal": {"status": "done"}  # Missing required 'description'
        },
    })
    assert_true(r, "Invalid goal returns error",
                not result.get("success"),
                "Should have failed without 'description'")
    assert_eq(r, "Error type is invalid_goal",
              result.get("error"), "invalid_goal")

    # 6g: Raw agent_memory write blocked
    result = await execute_primitive(auth, "EditEntity", {
        "ref": f"agent:{del_id}",
        "changes": {
            "agent_memory": {"observations": []}  # Should be blocked
        },
    })
    assert_true(r, "Raw agent_memory write blocked",
                not result.get("success"),
                "Should have rejected raw agent_memory write")

    return r


# =============================================================================
# Phase 7: Integration — Full Scoped Working Memory Rendering
# =============================================================================

async def phase_7_integration(auth: MockAuth) -> PhaseResult:
    r = PhaseResult("Phase 7: Integration — Full Scoped Rendering")
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 7: Integration — Full Scoped Rendering")
    logger.info(f"{'='*60}")

    from services.working_memory import _extract_agent_scope

    # Get test agent (should have instructions, observations, goal, version)
    dels = auth.client.table("agents").select("*").eq(
        "user_id", TEST_USER_ID
    ).ilike("title", f"{TEST_PREFIX}Version Test").execute()
    if not dels.data:
        r.fail("Test agent not found", "Need Phase 1 agent")
        return r

    agent = dels.data[0]

    # 7a: Full scope extraction
    scope = await _extract_agent_scope(agent, auth.client)
    assert_true(r, "Scope has id", "id" in scope)
    assert_true(r, "Scope has title", "title" in scope)
    assert_true(r, "Scope has type", "type" in scope)

    # 7b: Scope extraction produces complete data for prompt rendering
    assert_true(r, "Scope has agent id for Edit calls", bool(scope.get("id")))
    assert_true(r, "Scope has title for display", bool(scope.get("title")))

    # 7c: Token budget check — scoped working memory should be under 3000 tokens (rough estimate: 4 chars/token)
    est_tokens = len(prompt_text) / 4
    assert_true(r, f"Token estimate reasonable ({int(est_tokens)} est. tokens)",
                est_tokens < 3000,
                f"Estimated {int(est_tokens)} tokens — may be too large")

    return r


# =============================================================================
# Main
# =============================================================================

async def main():
    client = get_client()
    auth = MockAuth(TEST_USER_ID, client)

    logger.info("=" * 60)
    logger.info("Structural Overhaul Test Suite")
    logger.info(f"Test user: {TEST_USER_ID}")
    logger.info("=" * 60)

    # Cleanup before
    cleanup(client)

    results: list[PhaseResult] = []

    try:
        results.append(await phase_1_version_access(auth))
        results.append(await phase_2_working_memory_version(auth))
        results.append(await phase_3_headless_prompt(auth))
        results.append(await phase_4_default_instructions(auth))
        results.append(await phase_5_behavioral_triggers(auth))
        results.append(await phase_6_workspace_primitives(auth))
        results.append(await phase_7_integration(auth))
    finally:
        # Cleanup after
        cleanup(client)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("RESULTS SUMMARY")
    logger.info(f"{'='*60}")

    total_passed = 0
    total_failed = 0
    for phase in results:
        status = "✓ PASS" if phase.success else "✗ FAIL"
        logger.info(f"  {status}  {phase.phase} ({phase.passed} passed, {phase.failed} failed)")
        if phase.errors:
            for err in phase.errors:
                logger.info(f"         → {err}")
        total_passed += phase.passed
        total_failed += phase.failed

    logger.info(f"\nTotal: {total_passed} passed, {total_failed} failed")

    all_passed = all(p.success for p in results)
    if all_passed:
        logger.info("\n✓ ALL PHASES PASSED")
    else:
        logger.error("\n✗ SOME PHASES FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
