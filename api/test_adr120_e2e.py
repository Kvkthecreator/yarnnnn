"""
E2E Test: ADR-120 — Project Execution & Work Budget (Phases 1-4)

Validates the full ADR-120 stack end-to-end:
  Phase 1: Project creation → PM auto-creation → project heartbeat trigger
  Phase 2: Assembly composition (mocked LLM) → delivery orchestration
  Phase 3: Work budget — record, check, enforce
  Phase 4: Intentions parsing, work plan generation, graceful degradation

Uses real Supabase workspace_files but mocks LLM calls and external delivery.
"""

import asyncio
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
TEST_PROJECT_SLUG = "test-adr120-e2e"
TEST_PREFIX = "TEST_ADR120_"


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


def get_service_client():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


def cleanup(client):
    """Remove all test workspace files, work_units, and agents."""
    # Workspace files
    for prefix in [
        f"/projects/{TEST_PROJECT_SLUG}/",
        "/agents/test-analyst-120/memory/projects.json",
        "/agents/test-writer-120/memory/projects.json",
    ]:
        try:
            client.table("workspace_files").delete().eq(
                "user_id", TEST_USER_ID
            ).like("path", f"{prefix}%").execute()
        except Exception:
            pass

    # Work units with test metadata
    try:
        client.table("work_units").delete().eq(
            "user_id", TEST_USER_ID
        ).like("action_type", "test_%").execute()
    except Exception:
        pass

    # Test agents
    try:
        result = client.table("agents").select("id").eq(
            "user_id", TEST_USER_ID
        ).like("title", f"{TEST_PREFIX}%").execute()
        for a in (result.data or []):
            client.table("agent_runs").delete().eq("agent_id", a["id"]).execute()
            client.table("agents").delete().eq("id", a["id"]).execute()
    except Exception:
        pass

    logger.info("[CLEANUP] Test data removed")


# =============================================================================
# Phase 1: PROJECT.md Intentions + Backward Compat (ADR-120 P4)
# =============================================================================
async def phase1_intentions(client) -> PhaseResult:
    r = PhaseResult("P1: Intentions Schema")
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(client, TEST_USER_ID, TEST_PROJECT_SLUG)

    # 1a. Write project WITH intentions
    success = await pw.write_project(
        title="Test ADR-120 E2E Project",
        intent={
            "deliverable": "Executive deck",
            "audience": "Leadership",
            "format": "pptx",
            "purpose": "Quarterly review",
        },
        contributors=[
            {"agent_slug": "test-analyst-120", "expected_contribution": "Revenue data"},
            {"agent_slug": "test-writer-120", "expected_contribution": "Narrative"},
        ],
        assembly_spec="Combine analyst data with writer narrative into slide deck.",
        delivery={"channel": "email", "target": "test@example.com"},
        intentions=[
            {
                "type": "recurring",
                "description": "Produce Q2 review deck biweekly",
                "format": "pptx",
                "delivery": {"channel": "email", "target": "ceo@example.com"},
                "budget": "8 units/cycle",
            },
            {
                "type": "reactive",
                "description": "Alert on revenue drop >10% QoQ",
                "format": "chart",
                "delivery": {"channel": "slack", "target": "#leadership"},
                "budget": "3 units/trigger",
            },
            {
                "type": "goal",
                "description": "Final Q2 board deck",
                "format": "pptx",
                "delivery": {"channel": "email", "target": "board@example.com"},
                "budget": "15 units total",
                "deadline": "2026-07-01",
            },
        ],
    )
    if success:
        r.ok("write_project with intentions")
    else:
        r.fail("write_project with intentions")

    # 1b. Read and verify intentions
    project = await pw.read_project()
    if not project:
        r.fail("read_project returned None")
        return r

    r.ok("read_project returns dict") if project else r.fail("read_project")

    intentions = project.get("intentions", [])
    if len(intentions) == 3:
        r.ok(f"3 intentions parsed (got {len(intentions)})")
    else:
        r.fail(f"expected 3 intentions, got {len(intentions)}")

    # Verify first intention fields
    i0 = intentions[0] if intentions else {}
    if i0.get("type") == "recurring":
        r.ok("intention[0].type = recurring")
    else:
        r.fail("intention[0].type", f"expected 'recurring', got {i0.get('type')}")

    if "biweekly" in i0.get("description", ""):
        r.ok("intention[0].description contains 'biweekly'")
    else:
        r.fail("intention[0].description", f"got {i0.get('description')}")

    if i0.get("format") == "pptx":
        r.ok("intention[0].format = pptx")
    else:
        r.fail("intention[0].format", f"got {i0.get('format')}")

    # Verify delivery parsed as dict with channel/target
    d0 = i0.get("delivery", {})
    if isinstance(d0, dict) and d0.get("channel") == "email":
        r.ok("intention[0].delivery.channel = email")
    else:
        r.fail("intention[0].delivery", f"got {d0}")

    if i0.get("budget") == "8 units/cycle":
        r.ok("intention[0].budget parsed")
    else:
        r.fail("intention[0].budget", f"got {i0.get('budget')}")

    # Verify goal intention has deadline
    i2 = intentions[2] if len(intentions) > 2 else {}
    if i2.get("type") == "goal":
        r.ok("intention[2].type = goal")
    else:
        r.fail("intention[2].type", f"expected 'goal', got {i2.get('type')}")

    if i2.get("deadline") == "2026-07-01":
        r.ok("intention[2].deadline parsed")
    else:
        r.fail("intention[2].deadline", f"got {i2.get('deadline')}")

    return r


# =============================================================================
# Phase 2: Backward Compat — Intentions derived from Intent + Delivery
# =============================================================================
async def phase2_backward_compat(client) -> PhaseResult:
    r = PhaseResult("P2: Backward Compat (no intentions section)")
    from services.workspace import ProjectWorkspace

    slug = f"{TEST_PROJECT_SLUG}-compat"
    pw = ProjectWorkspace(client, TEST_USER_ID, slug)

    # Write project WITHOUT intentions
    await pw.write_project(
        title="Test Backward Compat",
        intent={
            "deliverable": "Weekly digest",
            "audience": "Team",
            "format": "pdf",
            "purpose": "Weekly summary",
        },
        contributors=[{"agent_slug": "test-analyst-120", "expected_contribution": "Data"}],
        delivery={"channel": "email", "target": "team@example.com"},
    )

    project = await pw.read_project()
    if not project:
        r.fail("read_project returned None")
        return r

    intentions = project.get("intentions", [])
    if len(intentions) == 1:
        r.ok("derived single intention from intent+delivery")
    else:
        r.fail(f"expected 1 derived intention, got {len(intentions)}")

    i0 = intentions[0] if intentions else {}
    if i0.get("type") == "recurring":
        r.ok("derived intention type = recurring")
    else:
        r.fail("derived intention type", f"got {i0.get('type')}")

    if i0.get("format") == "pdf":
        r.ok("derived intention format from intent.format")
    else:
        r.fail("derived intention format", f"got {i0.get('format')}")

    if isinstance(i0.get("delivery"), dict) and i0["delivery"].get("channel") == "email":
        r.ok("derived intention delivery from project delivery")
    else:
        r.fail("derived intention delivery", f"got {i0.get('delivery')}")

    # Cleanup
    try:
        client.table("workspace_files").delete().eq(
            "user_id", TEST_USER_ID
        ).like("path", f"/projects/{slug}/%").execute()
    except Exception:
        pass

    return r


# =============================================================================
# Phase 3: Contributor Freshness + PM Primitives (ADR-120 P1)
# =============================================================================
async def phase3_freshness(client) -> PhaseResult:
    r = PhaseResult("P3: Contributor Freshness")
    from services.workspace import ProjectWorkspace

    pw = ProjectWorkspace(client, TEST_USER_ID, TEST_PROJECT_SLUG)

    # Write contributions
    await pw.contribute("test-analyst-120", "data.md", "# Revenue\n$2.4M Q2")
    await pw.contribute("test-writer-120", "summary.md", "# Summary\nStrong quarter.")

    # Check freshness via primitive
    from services.primitives.project_execution import handle_check_contributor_freshness

    class FakeAuth:
        def __init__(self, c, uid):
            self.client = c
            self.user_id = uid

    auth = FakeAuth(client, TEST_USER_ID)
    result = await handle_check_contributor_freshness(auth, {"project_slug": TEST_PROJECT_SLUG})

    if result.get("all_fresh") is True:
        r.ok("all_fresh = True (no prior assembly)")
    elif result.get("all_fresh") is False:
        # First time, no assembly date means all are fresh
        r.fail("all_fresh should be True on first check with contributions", str(result))
    else:
        r.fail("all_fresh missing from result", str(result))

    contribs = result.get("contributors", [])
    if len(contribs) == 2:
        r.ok(f"2 contributors in freshness result")
    else:
        r.fail(f"expected 2 contributors, got {len(contribs)}")

    # Check ReadProjectStatus
    from services.primitives.project_execution import handle_read_project_status
    status = await handle_read_project_status(auth, {"project_slug": TEST_PROJECT_SLUG})

    if status.get("success"):
        r.ok("ReadProjectStatus success")
    else:
        r.fail("ReadProjectStatus failed", str(status))

    if status.get("project", {}).get("title") == "Test ADR-120 E2E Project":
        r.ok("ReadProjectStatus returns project title")
    else:
        r.fail("ReadProjectStatus title", str(status.get("project", {}).get("title")))

    return r


# =============================================================================
# Phase 4: PM Decision Routing — update_work_plan (ADR-120 P4)
# =============================================================================
async def phase4_pm_work_plan(client) -> PhaseResult:
    r = PhaseResult("P4: PM update_work_plan Action")
    from services.agent_execution import _handle_pm_decision

    # Mock PM JSON output for update_work_plan
    pm_draft = json.dumps({
        "action": "update_work_plan",
        "reason": "Initial decomposition — first PM run",
        "work_plan": {
            "contributors": [
                {"slug": "test-analyst-120", "expected_cadence": "weekly", "skills": ["spreadsheet"]},
                {"slug": "test-writer-120", "expected_cadence": "weekly", "skills": ["document"]},
            ],
            "assembly_cadence": "biweekly",
            "budget_per_cycle": 8,
            "skill_sequence": ["spreadsheet", "document", "presentation"],
            "notes": "Analyst data feeds into writer narrative → combined into deck",
        },
    })

    agent = {"id": "mock-pm-id", "title": f"{TEST_PREFIX}PM", "user_id": TEST_USER_ID}
    type_config = {"project_slug": TEST_PROJECT_SLUG}

    result = await _handle_pm_decision(
        client, TEST_USER_ID, agent, pm_draft, type_config,
        version_id="mock-version-001", next_version=1, usage={},
    )

    if result.get("pm_action") == "update_work_plan":
        r.ok("PM action routed to update_work_plan")
    else:
        r.fail("PM action routing", f"got {result.get('pm_action')}")

    if result.get("success"):
        r.ok("update_work_plan success")
    else:
        r.fail("update_work_plan failed", str(result))

    # Verify work plan written to workspace
    from services.workspace import ProjectWorkspace
    pw = ProjectWorkspace(client, TEST_USER_ID, TEST_PROJECT_SLUG)
    work_plan = await pw.read("memory/work_plan.md")

    if work_plan and "biweekly" in work_plan:
        r.ok("work_plan.md written with assembly_cadence")
    else:
        r.fail("work_plan.md content", f"got: {(work_plan or '')[:100]}")

    if work_plan and "test-analyst-120" in work_plan:
        r.ok("work_plan.md contains contributor slugs")
    else:
        r.fail("work_plan.md missing contributors")

    if work_plan and "spreadsheet" in work_plan:
        r.ok("work_plan.md contains skill info")
    else:
        r.fail("work_plan.md missing skills")

    return r


# =============================================================================
# Phase 5: PM Decision Routing — assemble (ADR-120 P2, mocked LLM)
# =============================================================================
async def phase5_pm_assemble(client) -> PhaseResult:
    r = PhaseResult("P5: PM assemble Action (mocked LLM)")
    from services.agent_execution import _handle_pm_decision
    from services.workspace import ProjectWorkspace

    pm_draft = json.dumps({
        "action": "assemble",
        "reason": "All contributors fresh — ready to assemble",
    })

    agent = {"id": "mock-pm-id", "title": f"{TEST_PREFIX}PM", "user_id": TEST_USER_ID}
    type_config = {"project_slug": TEST_PROJECT_SLUG}

    # Mock _compose_assembly to avoid real LLM call
    mock_compose = AsyncMock(return_value=(
        "# Assembled Output\n\nQ2 revenue was $2.4M. Strong quarter across all segments.",
        {"input_tokens": 100, "output_tokens": 200},
        [],  # no pending renders
    ))

    # Mock record_work_units to avoid needing the table
    mock_record_wu = MagicMock()

    with patch("services.agent_execution._compose_assembly", mock_compose), \
         patch("services.platform_limits.record_work_units", mock_record_wu):
        result = await _handle_pm_decision(
            client, TEST_USER_ID, agent, pm_draft, type_config,
            version_id="mock-version-002", next_version=2, usage={},
        )

    if result.get("pm_action") == "assemble":
        r.ok("PM action routed to assemble")
    else:
        r.fail("PM action routing", f"got {result.get('pm_action')}")

    if result.get("success"):
        r.ok("assembly success")
    else:
        r.fail("assembly failed", str(result))

    if result.get("assembly_folder"):
        r.ok(f"assembly_folder returned: {result['assembly_folder']}")
    else:
        r.fail("no assembly_folder in result")

    # Verify assembly written to workspace
    pw = ProjectWorkspace(client, TEST_USER_ID, TEST_PROJECT_SLUG)
    assemblies = await pw.list_assemblies()
    if assemblies:
        r.ok(f"assemblies listed: {assemblies}")
    else:
        r.fail("no assemblies found after assembly action")

    # Verify composition was called
    if mock_compose.called:
        r.ok("_compose_assembly was called")
    else:
        r.fail("_compose_assembly was NOT called")

    # Verify work units recorded (assembly = 2 units)
    if mock_record_wu.called:
        call_args = mock_record_wu.call_args
        if call_args and call_args[0][2] == "assembly":
            r.ok("record_work_units called with action_type='assembly'")
        else:
            r.fail("record_work_units wrong action_type", str(call_args))

        if call_args and call_args[0][3] == 2:
            r.ok("record_work_units called with units=2")
        else:
            r.fail("record_work_units wrong units", str(call_args))
    else:
        r.fail("record_work_units was NOT called")

    return r


# =============================================================================
# Phase 6: PM Decision Routing — advance_contributor (ADR-120 P1)
# =============================================================================
async def phase6_pm_advance(client) -> PhaseResult:
    r = PhaseResult("P6: PM advance_contributor Action")
    from services.agent_execution import _handle_pm_decision

    pm_draft = json.dumps({
        "action": "advance_contributor",
        "reason": "Writer hasn't produced in 5 days",
        "target_agent": "test-writer-120",
    })

    agent = {"id": "mock-pm-id", "title": f"{TEST_PREFIX}PM", "user_id": TEST_USER_ID}
    type_config = {"project_slug": TEST_PROJECT_SLUG}

    # advance_contributor looks up real agent by slug — mock the DB lookup
    mock_advance = AsyncMock(return_value={
        "success": True,
        "agent_slug": "test-writer-120",
        "message": "Advanced test-writer-120's schedule to now",
    })

    with patch("services.primitives.project_execution.handle_request_contributor_advance", mock_advance):
        result = await _handle_pm_decision(
            client, TEST_USER_ID, agent, pm_draft, type_config,
            version_id="mock-version-003", next_version=3, usage={},
        )

    if result.get("pm_action") == "advance_contributor":
        r.ok("PM action routed to advance_contributor")
    else:
        r.fail("PM action routing", f"got {result.get('pm_action')}")

    if result.get("success"):
        r.ok("advance_contributor success")
    else:
        r.fail("advance_contributor failed", str(result))

    if result.get("target_agent") == "test-writer-120":
        r.ok("target_agent = test-writer-120")
    else:
        r.fail("target_agent", f"got {result.get('target_agent')}")

    return r


# =============================================================================
# Phase 7: PM Decision Routing — escalate (ADR-120 P1)
# =============================================================================
async def phase7_pm_escalate(client) -> PhaseResult:
    r = PhaseResult("P7: PM escalate Action")
    from services.agent_execution import _handle_pm_decision
    from services.workspace import ProjectWorkspace

    pm_draft = json.dumps({
        "action": "escalate",
        "reason": "Writer advanced twice with no result",
        "details": "Contributor test-writer-120 unresponsive for 10 days.",
    })

    agent = {"id": "mock-pm-id", "title": f"{TEST_PREFIX}PM", "user_id": TEST_USER_ID}
    type_config = {"project_slug": TEST_PROJECT_SLUG}

    result = await _handle_pm_decision(
        client, TEST_USER_ID, agent, pm_draft, type_config,
        version_id="mock-version-004", next_version=4, usage={},
    )

    if result.get("pm_action") == "escalate":
        r.ok("PM action routed to escalate")
    else:
        r.fail("PM action routing", f"got {result.get('pm_action')}")

    if result.get("success"):
        r.ok("escalate success")
    else:
        r.fail("escalate failed", str(result))

    # Verify escalation note written
    pw = ProjectWorkspace(client, TEST_USER_ID, TEST_PROJECT_SLUG)
    escalation = await pw.read("memory/escalation.md")
    if escalation and "advanced twice" in escalation:
        r.ok("escalation note written to workspace")
    else:
        r.fail("escalation note", f"got: {(escalation or '')[:100]}")

    return r


# =============================================================================
# Phase 8: Work Budget — Check + Record (ADR-120 P3)
# =============================================================================
async def phase8_work_budget(client) -> PhaseResult:
    r = PhaseResult("P8: Work Budget Functions")
    from services.platform_limits import (
        check_work_budget,
        record_work_units,
        get_monthly_work_units,
    )

    # Get baseline
    baseline = get_monthly_work_units(client, TEST_USER_ID)
    r.ok(f"baseline work units: {baseline}") if baseline >= 0 else r.fail("baseline negative")

    # Record test units
    record_work_units(client, TEST_USER_ID, "test_agent_run", 1, metadata={"test": True})
    record_work_units(client, TEST_USER_ID, "test_assembly", 2, metadata={"test": True})
    record_work_units(client, TEST_USER_ID, "test_render", 1, metadata={"test": True})

    # Check units increased by 4
    after = get_monthly_work_units(client, TEST_USER_ID)
    delta = after - baseline
    if delta == 4:
        r.ok(f"work units increased by 4 (was {baseline}, now {after})")
    else:
        r.fail(f"expected +4, got +{delta} (was {baseline}, now {after})")

    # Check budget
    allowed, used, limit = check_work_budget(client, TEST_USER_ID)
    if allowed:
        r.ok(f"budget check: allowed ({used}/{limit})")
    else:
        r.fail(f"budget check unexpectedly denied ({used}/{limit})")

    if limit > 0:
        r.ok(f"budget limit is positive: {limit}")
    else:
        r.fail(f"budget limit unexpected: {limit}")

    return r


# =============================================================================
# Phase 9: Graceful Degradation — Budget Override (ADR-120 P4)
# =============================================================================
async def phase9_graceful_degradation(client) -> PhaseResult:
    r = PhaseResult("P9: Graceful Degradation (budget exhausted → escalate)")
    from services.agent_execution import _handle_pm_decision

    pm_draft = json.dumps({
        "action": "assemble",
        "reason": "All contributions fresh",
    })

    agent = {"id": "mock-pm-id", "title": f"{TEST_PREFIX}PM", "user_id": TEST_USER_ID}
    type_config = {"project_slug": TEST_PROJECT_SLUG}

    # Mock budget as exhausted — patch at the source module where it's imported from
    mock_budget = MagicMock(return_value=(False, 1000, 1000))

    with patch("services.platform_limits.check_work_budget", mock_budget):
        result = await _handle_pm_decision(
            client, TEST_USER_ID, agent, pm_draft, type_config,
            version_id="mock-version-005", next_version=5, usage={},
        )

    # Should override assemble → escalate
    if result.get("pm_action") == "escalate":
        r.ok("assemble overridden to escalate when budget exhausted")
    else:
        r.fail("expected escalate override", f"got {result.get('pm_action')}")

    if result.get("success"):
        r.ok("escalation success")
    else:
        r.fail("escalation failed", str(result))

    if "budget" in result.get("reason", "").lower():
        r.ok("escalation reason mentions budget")
    else:
        r.fail("escalation reason", f"got {result.get('reason')}")

    # Also test: advance_contributor should be overridden too
    pm_draft2 = json.dumps({
        "action": "advance_contributor",
        "reason": "Writer is stale",
        "target_agent": "test-writer-120",
    })

    with patch("services.platform_limits.check_work_budget", mock_budget):
        result2 = await _handle_pm_decision(
            client, TEST_USER_ID, agent, pm_draft2, type_config,
            version_id="mock-version-006", next_version=6, usage={},
        )

    if result2.get("pm_action") == "escalate":
        r.ok("advance_contributor overridden to escalate when budget exhausted")
    else:
        r.fail("advance_contributor override", f"got {result2.get('pm_action')}")

    # wait and escalate should NOT be overridden
    pm_draft3 = json.dumps({"action": "wait", "reason": "Not ready"})

    with patch("services.platform_limits.check_work_budget", mock_budget):
        result3 = await _handle_pm_decision(
            client, TEST_USER_ID, agent, pm_draft3, type_config,
            version_id="mock-version-007", next_version=7, usage={},
        )

    if result3.get("pm_action") == "wait":
        r.ok("wait action NOT overridden (correct — wait is free)")
    else:
        r.fail("wait should not be overridden", f"got {result3.get('pm_action')}")

    return r


# =============================================================================
# Phase 10: UpdateProjectIntent Primitive (ADR-120 P4)
# =============================================================================
async def phase10_update_intent(client) -> PhaseResult:
    r = PhaseResult("P10: UpdateProjectIntent Primitive")
    from services.primitives.project_execution import handle_update_project_intent
    from services.workspace import ProjectWorkspace

    class FakeAuth:
        def __init__(self, c, uid):
            self.client = c
            self.user_id = uid

    auth = FakeAuth(client, TEST_USER_ID)

    # Update assembly_spec only
    result = await handle_update_project_intent(auth, {
        "project_slug": TEST_PROJECT_SLUG,
        "assembly_spec": "Updated: Analyst chart on slide 1, writer narrative on slides 2-3.",
    })

    if result.get("success"):
        r.ok("UpdateProjectIntent success (assembly_spec)")
    else:
        r.fail("UpdateProjectIntent failed", str(result))

    if "assembly_spec" in result.get("updated_fields", []):
        r.ok("assembly_spec in updated_fields")
    else:
        r.fail("updated_fields", str(result.get("updated_fields")))

    # Verify assembly_spec persisted
    pw = ProjectWorkspace(client, TEST_USER_ID, TEST_PROJECT_SLUG)
    project = await pw.read_project()
    if project and "slide 1" in project.get("assembly_spec", ""):
        r.ok("assembly_spec persisted correctly")
    else:
        r.fail("assembly_spec not persisted", f"got: {project.get('assembly_spec', '')[:80]}")

    # Verify title was NOT changed (Composer's domain)
    if project.get("title") == "Test ADR-120 E2E Project":
        r.ok("title preserved (not modified by UpdateProjectIntent)")
    else:
        r.fail("title changed unexpectedly", f"got {project.get('title')}")

    # Verify intentions still present
    if len(project.get("intentions", [])) == 3:
        r.ok("intentions preserved after assembly_spec update")
    else:
        r.fail("intentions lost", f"got {len(project.get('intentions', []))}")

    # Update intentions
    result2 = await handle_update_project_intent(auth, {
        "project_slug": TEST_PROJECT_SLUG,
        "intentions": [
            {"type": "recurring", "description": "Weekly deck now", "format": "pptx",
             "delivery": {"channel": "email", "target": "ceo@example.com"}, "budget": "6 units/cycle"},
        ],
    })

    if result2.get("success"):
        r.ok("UpdateProjectIntent success (intentions)")
    else:
        r.fail("UpdateProjectIntent intentions failed", str(result2))

    # Verify intentions updated
    project2 = await pw.read_project()
    intentions = project2.get("intentions", [])
    if len(intentions) == 1:
        r.ok("intentions updated to 1 item")
    else:
        r.fail("intentions count", f"got {len(intentions)}")

    if intentions and intentions[0].get("description", "").startswith("Weekly deck"):
        r.ok("intention description updated")
    else:
        r.fail("intention description", str(intentions[0] if intentions else "empty"))

    return r


# =============================================================================
# Phase 11: PM Prompt Context Loading (ADR-120 P4)
# =============================================================================
async def phase11_pm_context(client) -> PhaseResult:
    r = PhaseResult("P11: PM Context Loading")
    from services.agent_execution import _load_pm_project_context

    # Mock check_work_budget — patch at source module
    mock_budget = MagicMock(return_value=(True, 50, 1000))

    with patch("services.platform_limits.check_work_budget", mock_budget):
        ctx = await _load_pm_project_context(client, TEST_USER_ID, TEST_PROJECT_SLUG)

    # Verify project_context
    if "Test ADR-120 E2E Project" in ctx.get("project_context", ""):
        r.ok("project_context contains title")
    else:
        r.fail("project_context missing title", ctx.get("project_context", "")[:100])

    # Verify contributor_status
    cs = ctx.get("contributor_status", "")
    if "test-analyst-120" in cs:
        r.ok("contributor_status contains analyst")
    else:
        r.fail("contributor_status missing analyst", cs[:100])

    # Verify intentions field (ADR-120 P4)
    intentions = ctx.get("intentions", "")
    if "recurring" in intentions:
        r.ok("intentions field contains 'recurring'")
    else:
        r.fail("intentions missing 'recurring'", intentions[:100])

    # Verify work_plan field
    wp = ctx.get("work_plan", "")
    if "biweekly" in wp:
        r.ok("work_plan contains assembly_cadence from Phase 4")
    else:
        r.fail("work_plan missing content", wp[:100])

    # Verify budget_status (ADR-120 P4)
    bs = ctx.get("budget_status", "")
    if "OK" in bs or "LOW" in bs or "EXHAUSTED" in bs:
        r.ok(f"budget_status present: {bs}")
    else:
        r.fail("budget_status missing or malformed", bs)

    return r


# =============================================================================
# Phase 12: PM Pipeline Validation (prompt + validation)
# =============================================================================
async def phase12_pm_pipeline_validation(client) -> PhaseResult:
    r = PhaseResult("P12: PM Pipeline Validation")
    from services.agent_pipeline import validate_output, ROLE_PROMPTS

    # PM prompt exists and has new P4 fields
    pm_prompt = ROLE_PROMPTS.get("pm", "")
    if "{intentions}" in pm_prompt:
        r.ok("PM prompt has {intentions} field")
    else:
        r.fail("PM prompt missing {intentions}")

    if "{budget_status}" in pm_prompt:
        r.ok("PM prompt has {budget_status} field")
    else:
        r.fail("PM prompt missing {budget_status}")

    if "update_work_plan" in pm_prompt:
        r.ok("PM prompt mentions update_work_plan action")
    else:
        r.fail("PM prompt missing update_work_plan")

    if "budget is low" in pm_prompt.lower() or "budget is exhausted" in pm_prompt.lower():
        r.ok("PM prompt has budget-aware rules")
    else:
        r.fail("PM prompt missing budget-aware rules")

    # Validate PM outputs
    valid_actions = [
        '{"action": "assemble", "reason": "ready"}',
        '{"action": "wait", "reason": "not ready"}',
        '{"action": "escalate", "reason": "stuck"}',
        '{"action": "advance_contributor", "reason": "stale", "target_agent": "test-agent"}',
        '{"action": "update_work_plan", "reason": "first run", "work_plan": {"assembly_cadence": "weekly"}}',
    ]
    for valid in valid_actions:
        result = validate_output("pm", valid, {})
        issues = result.get("issues", []) if isinstance(result, dict) else result
        if not issues:
            action = json.loads(valid)["action"]
            r.ok(f"validate_output accepts '{action}'")
        else:
            r.fail(f"validate_output rejected valid PM output", str(issues))

    # Invalid: unknown action
    result = validate_output("pm", '{"action": "destroy"}', {})
    issues = result.get("issues", []) if isinstance(result, dict) else result
    if issues:
        r.ok("validate_output rejects unknown action")
    else:
        r.fail("validate_output should reject 'destroy'")

    # Invalid: update_work_plan without work_plan
    result = validate_output("pm", '{"action": "update_work_plan", "reason": "test"}', {})
    issues = result.get("issues", []) if isinstance(result, dict) else result
    if issues:
        r.ok("validate_output rejects update_work_plan without work_plan object")
    else:
        r.fail("validate_output should require work_plan for update_work_plan")

    return r


# =============================================================================
# Phase 13: Registry Verification
# =============================================================================
async def phase13_registry(client) -> PhaseResult:
    r = PhaseResult("P13: Primitives Registry")
    from services.primitives.registry import HANDLERS, PRIMITIVES, PRIMITIVE_MODES

    # UpdateProjectIntent registered
    if "UpdateProjectIntent" in HANDLERS:
        r.ok("UpdateProjectIntent in HANDLERS")
    else:
        r.fail("UpdateProjectIntent missing from HANDLERS")

    # In PRIMITIVES list
    tool_names = [t["name"] for t in PRIMITIVES]
    if "UpdateProjectIntent" in tool_names:
        r.ok("UpdateProjectIntent in PRIMITIVES list")
    else:
        r.fail("UpdateProjectIntent missing from PRIMITIVES list")

    # Mode-gated as headless-only
    modes = PRIMITIVE_MODES.get("UpdateProjectIntent", [])
    if modes == ["headless"]:
        r.ok("UpdateProjectIntent mode = headless-only")
    else:
        r.fail("UpdateProjectIntent modes", f"got {modes}")

    # All P1 primitives still registered
    for name in ["CheckContributorFreshness", "ReadProjectStatus", "RequestContributorAdvance"]:
        if name in HANDLERS:
            r.ok(f"{name} still in HANDLERS")
        else:
            r.fail(f"{name} missing from HANDLERS")

    return r


# =============================================================================
# Main
# =============================================================================
async def run_tests():
    client = get_service_client()

    # Pre-clean
    cleanup(client)

    phases = [
        phase1_intentions,
        phase2_backward_compat,
        phase3_freshness,
        phase4_pm_work_plan,
        phase5_pm_assemble,
        phase6_pm_advance,
        phase7_pm_escalate,
        phase8_work_budget,
        phase9_graceful_degradation,
        phase10_update_intent,
        phase11_pm_context,
        phase12_pm_pipeline_validation,
        phase13_registry,
    ]

    results = []
    for phase_fn in phases:
        logger.info(f"\n{'='*60}")
        logger.info(f"  {phase_fn.__name__}")
        logger.info(f"{'='*60}")
        try:
            result = await phase_fn(client)
            results.append(result)
        except Exception as e:
            logger.error(f"  EXCEPTION in {phase_fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
            err_result = PhaseResult(phase_fn.__name__)
            err_result.fail("phase crashed", str(e))
            results.append(err_result)

    # Post-clean
    cleanup(client)

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("  SUMMARY — ADR-120 E2E (Phases 1-4)")
    logger.info(f"{'='*60}")

    total_passed = 0
    total_failed = 0
    for result in results:
        status = "✓ PASS" if result.success else "✗ FAIL"
        logger.info(f"  {status}  {result.phase}  ({result.passed}p/{result.failed}f)")
        if result.errors:
            for err in result.errors:
                logger.info(f"         → {err}")
        total_passed += result.passed
        total_failed += result.failed

    logger.info(f"\n  Total: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        logger.error("  RESULT: FAILED")
        sys.exit(1)
    else:
        logger.info("  RESULT: ALL PASSED")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_tests())
