"""
ADR-143 Test Suite — Agent Playbook Layer + Feedback Consolidation

Tests:
  1. Playbook seeding at agent creation
  2. load_context() reads playbook + feedback files correctly
  3. feedback_distillation writes to feedback.md (not preferences.md)
  4. WriteAgentFeedback primitive works
  5. Import validation — no dangling references to deleted files
  6. _build_headless_system_prompt no longer accepts workspace_preferences
  7. build_task_execution_prompt no longer accepts workspace_preferences
  8. Frontend type alignment — AgentMemory shape matches backend

Strategy: Real DB writes with TEST_ADR143_ prefix. No live LLM calls.
Test user: kvkthecreator@gmail.com

Usage:
    cd api && python test_adr143_playbook_feedback.py
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any
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
TEST_PREFIX = "TEST_ADR143_"

# Results tracking
RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    logger.info(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def get_service_client():
    """Get a Supabase service client (bypasses RLS)."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


# =============================================================================
# Test 1: Agent Framework — Playbook in Registry
# =============================================================================

def test_playbook_in_registry():
    """Verify all 6 agent types have playbook entries."""
    logger.info("Test 1: Playbook in AGENT_TYPES registry")

    from services.agent_framework import AGENT_TYPES, get_type_playbook

    for type_key, type_def in AGENT_TYPES.items():
        playbook = type_def.get("methodology", {})
        record(
            f"  {type_key} has playbook",
            len(playbook) > 0,
            f"{len(playbook)} files: {list(playbook.keys())}"
        )

        # Every type must have at least playbook-outputs.md
        record(
            f"  {type_key} has playbook-outputs.md",
            "playbook-outputs.md" in playbook,
        )

    # Test helper function
    research_method = get_type_playbook("research")
    record(
        "  get_type_playbook('research') returns dict",
        isinstance(research_method, dict) and len(research_method) > 0,
        f"{len(research_method)} files"
    )

    # Test legacy mapping
    legacy_method = get_type_playbook("digest")  # legacy → research
    record(
        "  get_type_playbook('digest') resolves via legacy map",
        isinstance(legacy_method, dict) and len(legacy_method) > 0,
    )

    # Unknown type returns empty
    unknown_method = get_type_playbook("nonexistent_type_xyz")
    record(
        "  get_type_playbook('nonexistent') returns empty",
        isinstance(unknown_method, dict) and len(unknown_method) == 0,
    )


# =============================================================================
# Test 2: Agent Creation Seeds Playbook
# =============================================================================

async def test_playbook_seeding():
    """Verify agent creation seeds playbook files to workspace."""
    logger.info("Test 2: Agent creation seeds playbook files")

    client = get_service_client()

    # Create a test agent
    from services.agent_creation import create_agent_record as create_agent
    result = await create_agent(
        client=client,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}Research Test",
        role="research",
        agent_instructions="Test research agent for ADR-143",
        origin="user_configured",
    )

    record("  Agent created", result.get("success", False), str(result.get("error", "")))

    if not result.get("success"):
        return

    agent = result["agent"]
    agent_id = agent["id"]

    try:
        # Check workspace for playbook files
        from services.workspace import AgentWorkspace, get_agent_slug
        ws = AgentWorkspace(client, TEST_USER_ID, get_agent_slug(agent))

        playbook_outputs = await ws.read("memory/playbook-outputs.md")
        record(
            "  playbook-outputs.md seeded",
            playbook_outputs is not None and len(playbook_outputs) > 100,
            f"{len(playbook_outputs or '')} chars"
        )

        playbook_research = await ws.read("memory/playbook-research.md")
        record(
            "  playbook-research.md seeded (research type)",
            playbook_research is not None and len(playbook_research) > 100,
            f"{len(playbook_research or '')} chars"
        )

        # Also check self_assessment.md was seeded (existing ADR-128)
        self_assessment = await ws.read("memory/self_assessment.md")
        record(
            "  self_assessment.md seeded (ADR-128)",
            self_assessment is not None and "Self-Assessment" in self_assessment,
        )

        # Check AGENT.md was seeded
        agent_md = await ws.read("AGENT.md")
        record(
            "  AGENT.md seeded",
            agent_md is not None and "Test research agent" in agent_md,
        )

    finally:
        # Cleanup
        client.table("agents").delete().eq("id", agent_id).execute()
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).like(
            "path", f"%{get_agent_slug(agent)}%"
        ).execute()
        logger.info(f"  [CLEANUP] Deleted test agent {agent_id}")


# =============================================================================
# Test 3: load_context() Labels Playbook Correctly
# =============================================================================

async def test_load_context_labels():
    """Verify load_context() labels playbook and feedback files distinctly."""
    logger.info("Test 3: load_context() labeling")

    client = get_service_client()

    # Create agent and seed files manually
    from services.agent_creation import create_agent_record as create_agent
    result = await create_agent(
        client=client,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}Context Label Test",
        role="content",
        agent_instructions="Test content agent",
        origin="user_configured",
    )

    if not result.get("success"):
        record("  Agent created for context test", False, str(result.get("error")))
        return

    agent = result["agent"]
    agent_id = agent["id"]

    try:
        from services.workspace import AgentWorkspace, get_agent_slug
        ws = AgentWorkspace(client, TEST_USER_ID, get_agent_slug(agent))

        # Write a feedback entry
        await ws.write("memory/feedback.md",
                       "# Feedback History\n\n## Run 1 (2026-03-25)\n- Test feedback entry\n",
                       summary="test")

        # Load context
        context = await ws.load_context()

        record(
            "  Context contains '## Playbook: Outputs'",
            "## Playbook: Outputs" in context,
        )

        record(
            "  Context contains '## Playbook: Formats'",
            "## Playbook: Formats" in context,
            "content type should have playbook-formats.md"
        )

        record(
            "  Context contains '## Feedback History'",
            "## Feedback History" in context,
        )

        record(
            "  Context does NOT contain '## Memory: Preferences'",
            "## Memory: Preferences" not in context,
            "preferences.md should be gone"
        )

        record(
            "  Context does NOT contain '## Memory: Observations'",
            "## Memory: Observations" not in context,
            "observations.md should be gone"
        )

    finally:
        client.table("agents").delete().eq("id", agent_id).execute()
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).like(
            "path", f"%{get_agent_slug(agent)}%"
        ).execute()


# =============================================================================
# Test 4: Feedback Distillation → feedback.md
# =============================================================================

async def test_feedback_distillation():
    """Verify feedback distillation writes to feedback.md, not preferences.md."""
    logger.info("Test 4: Feedback distillation → feedback.md")

    client = get_service_client()

    from services.agent_creation import create_agent_record as create_agent
    result = await create_agent(
        client=client,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}Feedback Test",
        role="research",
        agent_instructions="Test feedback agent",
        origin="user_configured",
    )

    if not result.get("success"):
        record("  Agent created for feedback test", False, str(result.get("error")))
        return

    agent = result["agent"]
    agent_id = agent["id"]
    from services.workspace import AgentWorkspace, get_agent_slug
    _slug = get_agent_slug(agent)

    try:
        # Insert a fake agent_run with edit signals
        from datetime import datetime, timezone
        run_data = {
            "id": str(uuid4()),
            "agent_id": agent_id,
            "version_number": 1,
            "status": "approved",
            "edit_categories": {
                "additions": ["executive summary", "action items"],
                "deletions": ["detailed playbook"],
                "restructures": [],
                "rewrites": [],
            },
            "edit_distance_score": 0.35,
            "feedback_notes": "Keep it concise",
        }
        try:
            client.table("agent_runs").insert(run_data).execute()
        except Exception as e:
            record("  agent_runs insert", False, str(e))
            return

        # Run distillation
        from services.feedback_distillation import distill_feedback_to_workspace
        success = await distill_feedback_to_workspace(client, TEST_USER_ID, agent)
        record("  distill_feedback_to_workspace returned True", success)

        # Check feedback.md was written
        ws = AgentWorkspace(client, TEST_USER_ID, _slug)

        feedback = await ws.read("memory/feedback.md")
        record(
            "  feedback.md was written",
            feedback is not None and "Feedback History" in feedback,
        )

        record(
            "  feedback.md contains edit signals",
            feedback is not None and "executive summary" in feedback.lower(),
            f"Content: {(feedback or '')[:200]}"
        )

        record(
            "  feedback.md contains user feedback note",
            feedback is not None and "Keep it concise" in feedback,
        )

        # Verify preferences.md was NOT written
        preferences = await ws.read("memory/preferences.md")
        record(
            "  preferences.md was NOT written",
            preferences is None or "User Preferences" not in preferences,
            "Old file should not exist for new agents"
        )

    finally:
        client.table("agent_runs").delete().eq("agent_id", agent_id).execute()
        client.table("agents").delete().eq("id", agent_id).execute()
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).like(
            "path", f"%{_slug}%"
        ).execute()


# =============================================================================
# Test 5: WriteAgentFeedback Primitive
# =============================================================================

async def test_write_agent_feedback_primitive():
    """Verify WriteAgentFeedback primitive writes to feedback.md."""
    logger.info("Test 5: WriteAgentFeedback primitive")

    client = get_service_client()

    from services.agent_creation import create_agent_record as create_agent
    result = await create_agent(
        client=client,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}Primitive Test",
        role="content",
        agent_instructions="Test agent for primitive",
        origin="user_configured",
    )

    if not result.get("success"):
        record("  Agent created for primitive test", False, str(result.get("error")))
        return

    agent = result["agent"]
    agent_id = agent["id"]

    try:
        from services.workspace import get_agent_slug
        slug = get_agent_slug(agent)

        from services.primitives.workspace import handle_write_agent_feedback
        auth = {"client": client, "user_id": TEST_USER_ID}
        result = await handle_write_agent_feedback(auth, {
            "agent_slug": slug,
            "feedback": "Reports are too long. Keep to 2 pages max."
        })

        record(
            "  Primitive returned ok",
            result.get("status") == "ok",
            str(result)
        )

        # Verify feedback.md was written
        from services.workspace import AgentWorkspace
        ws = AgentWorkspace(client, TEST_USER_ID, slug)
        feedback = await ws.read("memory/feedback.md")

        record(
            "  feedback.md contains conversational feedback",
            feedback is not None and "Reports are too long" in feedback,
        )

        record(
            "  feedback entry has 'conversation' source",
            feedback is not None and "conversation" in feedback,
        )

        # Test with invalid slug
        error_result = await handle_write_agent_feedback(auth, {
            "agent_slug": "nonexistent-agent-xyz",
            "feedback": "This should fail"
        })
        record(
            "  Invalid slug returns error",
            "error" in error_result,
            str(error_result)
        )

    finally:
        client.table("agents").delete().eq("id", agent_id).execute()
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).like(
            "path", f"%{slug}%"
        ).execute()


# =============================================================================
# Test 6: Import Validation — No Dangling References
# =============================================================================

def test_import_validation():
    """Verify critical imports still work after refactor."""
    logger.info("Test 6: Import validation")

    # feedback_distillation imports
    try:
        from services.feedback_distillation import distill_feedback_to_workspace
        from services.feedback_distillation import write_feedback_entry
        record("  feedback_distillation imports ok", True)
    except ImportError as e:
        record("  feedback_distillation imports ok", False, str(e))

    # write_supervisor_notes should NOT exist anymore
    try:
        from services.feedback_distillation import write_supervisor_notes
        record("  write_supervisor_notes deleted", False, "Still importable!")
    except ImportError:
        record("  write_supervisor_notes deleted", True)

    # agent_framework imports
    try:
        from services.agent_framework import get_type_playbook
        record("  get_type_playbook importable", True)
    except ImportError as e:
        record("  get_type_playbook importable", False, str(e))

    # Registry has WriteAgentFeedback
    try:
        from services.primitives.registry import HANDLERS, PRIMITIVE_MODES
        record(
            "  WriteAgentFeedback in registry",
            "WriteAgentFeedback" in HANDLERS,
        )
        record(
            "  WriteAgentFeedback is chat-mode only",
            PRIMITIVE_MODES.get("WriteAgentFeedback") == ["chat"],
        )
    except Exception as e:
        record("  Registry check", False, str(e))

    # _build_headless_system_prompt should NOT accept workspace_preferences
    try:
        from services.agent_execution import _build_headless_system_prompt
        sig = inspect.signature(_build_headless_system_prompt)
        has_wp = "workspace_preferences" in sig.parameters
        record(
            "  _build_headless_system_prompt: no workspace_preferences param",
            not has_wp,
            f"Params: {list(sig.parameters.keys())}"
        )
    except Exception as e:
        record("  _build_headless_system_prompt signature check", False, str(e))

    # build_task_execution_prompt should NOT accept workspace_preferences
    try:
        from services.task_pipeline import build_task_execution_prompt
        sig = inspect.signature(build_task_execution_prompt)
        has_wp = "workspace_preferences" in sig.parameters
        record(
            "  build_task_execution_prompt: no workspace_preferences param",
            not has_wp,
            f"Params: {list(sig.parameters.keys())}"
        )
    except Exception as e:
        record("  build_task_execution_prompt signature check", False, str(e))


# =============================================================================
# Test 7: Observation Redirect → feedback.md
# =============================================================================

async def test_observation_redirect():
    """Verify append_observation and record_observation redirect to feedback.md."""
    logger.info("Test 7: Observation redirect to feedback.md")

    client = get_service_client()

    from services.agent_creation import create_agent_record as create_agent
    result = await create_agent(
        client=client,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}Observation Redirect",
        role="research",
        agent_instructions="Test observation redirect",
        origin="user_configured",
    )

    if not result.get("success"):
        record("  Agent created", False, str(result.get("error")))
        return

    agent = result["agent"]
    agent_id = agent["id"]

    try:
        from services.workspace import AgentWorkspace, get_agent_slug
        ws = AgentWorkspace(client, TEST_USER_ID, get_agent_slug(agent))

        # Call append_observation (legacy API)
        count = await ws.append_observation("Test observation from trigger", source="trigger")
        record("  append_observation returned 0 (deprecated count)", count == 0)

        # Check feedback.md was written
        feedback = await ws.read("memory/feedback.md")
        record(
            "  Observation landed in feedback.md",
            feedback is not None and "Test observation from trigger" in feedback,
        )

        # Check observations.md was NOT written
        observations = await ws.read("memory/observations.md")
        record(
            "  observations.md was NOT written",
            observations is None,
        )

        # Call record_observation (other legacy API)
        success = await ws.record_observation("Test record observation", source="self")
        record("  record_observation returned True", success)

        # Verify both entries in feedback.md
        feedback = await ws.read("memory/feedback.md")
        record(
            "  Both observations in feedback.md",
            feedback is not None
            and "Test observation from trigger" in feedback
            and "Test record observation" in feedback,
        )

    finally:
        client.table("agents").delete().eq("id", agent_id).execute()
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).like(
            "path", f"%{get_agent_slug(agent)}%"
        ).execute()


# =============================================================================
# Test 8: get_agent_full_context Returns New Shape
# =============================================================================

async def test_full_context_shape():
    """Verify get_agent_full_context returns feedback/self_assessment, not old fields."""
    logger.info("Test 8: get_agent_full_context shape")

    client = get_service_client()

    from services.agent_creation import create_agent_record as create_agent
    result = await create_agent(
        client=client,
        user_id=TEST_USER_ID,
        title=f"{TEST_PREFIX}Context Shape",
        role="research",
        agent_instructions="Test context shape",
        origin="user_configured",
    )

    if not result.get("success"):
        record("  Agent created", False, str(result.get("error")))
        return

    agent = result["agent"]
    agent_id = agent["id"]

    try:
        from services.workspace import get_agent_intelligence as get_agent_full_context
        context = await get_agent_full_context(client, TEST_USER_ID, agent)

        memory = context.get("agent_memory") or {}

        # New fields should be present (self_assessment seeded at creation)
        record(
            "  self_assessment in memory",
            "self_assessment" in memory,
        )

        # Old fields should NOT be present
        for old_field in ["observations", "review_log", "preferences", "supervisor_notes"]:
            record(
                f"  '{old_field}' NOT in memory",
                old_field not in memory,
            )

    finally:
        client.table("agents").delete().eq("id", agent_id).execute()
        from services.workspace import get_agent_slug
        client.table("workspace_files").delete().eq("user_id", TEST_USER_ID).like(
            "path", f"%{get_agent_slug(agent)}%"
        ).execute()


# =============================================================================
# Runner
# =============================================================================

async def run_all():
    logger.info("=" * 70)
    logger.info("ADR-143 Test Suite — Playbook + Feedback Consolidation")
    logger.info("=" * 70)

    # Sync tests
    test_playbook_in_registry()
    test_import_validation()

    # Async tests
    await test_playbook_seeding()
    await test_load_context_labels()
    await test_feedback_distillation()
    await test_write_agent_feedback_primitive()
    await test_observation_redirect()
    await test_full_context_shape()

    # Summary
    logger.info("")
    logger.info("=" * 70)
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = sum(1 for _, p, _ in RESULTS if not p)
    logger.info(f"RESULTS: {passed} passed, {failed} failed, {len(RESULTS)} total")

    if failed:
        logger.info("\nFAILURES:")
        for name, p, detail in RESULTS:
            if not p:
                logger.info(f"  FAIL: {name} — {detail}")

    logger.info("=" * 70)
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
