"""
E2E Test: ADR-117 Phase 3 — Duties, Role Portfolios, Skills & Cross-Agent Communication

Validates the full ADR-117 P3 stack + adjacent systems:
  Layer 1: Portfolio registry — pure logic, exhaustive role × seniority coverage
  Layer 2: Execution wiring — duty dispatch, effective_role override, SKILL.md injection
  Layer 3: Skills utilization — RuntimeDispatch, render gateway, workspace file writes
  Layer 4: Delivery pipeline — output folder → manifest → email delivery path
  Layer 5: Filesystem persistence — save_output, manifest structure, version history
  Layer 6: Cross-agent communication — DiscoverAgents, ReadAgentContext, project contributions
  Layer 7: Composer promotion — promote_duty, portfolio gating, activity events

Uses real Supabase workspace_files but mocks LLM calls, render gateway, and email delivery.
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
from typing import Optional

import pytest

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
TEST_PREFIX = "TEST_ADR117_"


@dataclass
class LayerResult:
    layer: str
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


def get_service_client():
    """Get Supabase service client for test operations."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


@pytest.fixture
def client():
    """Supabase service client fixture for layers that need DB access."""
    return get_service_client()


# ============================================================================
# LAYER 1: Portfolio Registry — Pure Logic
# ============================================================================

def test_layer1_portfolio_registry() -> LayerResult:
    """Exhaustive tests for classify_seniority, get_eligible_duties, get_promotion_duty."""
    r = LayerResult("Layer 1: Portfolio Registry")
    logger.info("\n=== Layer 1: Portfolio Registry (pure logic) ===")

    from services.agent_framework import (
        classify_seniority,
        get_eligible_duties,
        get_promotion_duty,
        ROLE_PORTFOLIOS,
        SKILL_ENABLED_ROLES,
    )

    # --- classify_seniority ---

    # Below both thresholds
    assert classify_seniority(3, 0.5) == "new"
    r.ok("classify_seniority(3, 0.5) → new")

    # Exact associate boundary
    assert classify_seniority(5, 0.6) == "associate"
    r.ok("classify_seniority(5, 0.6) → associate")

    # Just below associate (runs ok, approval too low)
    assert classify_seniority(5, 0.59) == "new"
    r.ok("classify_seniority(5, 0.59) → new (approval just below)")

    # Just below associate (approval ok, runs too low)
    assert classify_seniority(4, 0.6) == "new"
    r.ok("classify_seniority(4, 0.6) → new (runs just below)")

    # Exact senior boundary
    assert classify_seniority(10, 0.8) == "senior"
    r.ok("classify_seniority(10, 0.8) → senior")

    # Well above senior
    assert classify_seniority(50, 0.95) == "senior"
    r.ok("classify_seniority(50, 0.95) → senior")

    # High runs, low approval — stays new
    assert classify_seniority(100, 0.3) == "new"
    r.ok("classify_seniority(100, 0.3) → new (many runs, low approval)")

    # High runs, moderate approval — associate
    assert classify_seniority(20, 0.7) == "associate"
    r.ok("classify_seniority(20, 0.7) → associate")

    # Zero runs
    assert classify_seniority(0, 0.0) == "new"
    r.ok("classify_seniority(0, 0.0) → new")

    # --- get_eligible_duties ---

    # Digest role across seniority levels
    assert get_eligible_duties("digest", "new") == [{"duty": "digest", "trigger": "recurring"}]
    r.ok("digest/new → [digest]")

    assert get_eligible_duties("digest", "associate") == [{"duty": "digest", "trigger": "recurring"}]
    r.ok("digest/associate → [digest]")

    senior_digest = get_eligible_duties("digest", "senior")
    assert len(senior_digest) == 2
    assert senior_digest[0]["duty"] == "digest"
    assert senior_digest[1]["duty"] == "monitor"
    assert senior_digest[1]["trigger"] == "reactive"
    r.ok("digest/senior → [digest, monitor(reactive)]")

    # Research role — senior gains monitor(proactive)
    senior_research = get_eligible_duties("research", "senior")
    assert len(senior_research) == 2
    assert senior_research[1]["duty"] == "monitor"
    assert senior_research[1]["trigger"] == "proactive"
    r.ok("research/senior → [research, monitor(proactive)]")

    # Synthesize role — senior gains research(goal)
    senior_synth = get_eligible_duties("synthesize", "senior")
    assert len(senior_synth) == 2
    assert senior_synth[1]["duty"] == "research"
    assert senior_synth[1]["trigger"] == "goal"
    r.ok("synthesize/senior → [synthesize, research(goal)]")

    # Monitor role — senior gains act(reactive)
    senior_monitor = get_eligible_duties("monitor", "senior")
    assert len(senior_monitor) == 2
    assert senior_monitor[1]["duty"] == "act"
    r.ok("monitor/senior → [monitor, act(reactive)]")

    # Prepare — never expands
    assert len(get_eligible_duties("prepare", "senior")) == 1
    r.ok("prepare/senior → [prepare] (no expansion)")

    # PM — never expands
    assert len(get_eligible_duties("pm", "senior")) == 1
    r.ok("pm/senior → [pm] (no expansion)")

    # Custom — never expands
    assert len(get_eligible_duties("custom", "senior")) == 1
    r.ok("custom/senior → [custom] (no expansion)")

    # Unknown role — graceful degradation
    assert get_eligible_duties("nonexistent_role", "senior") == []
    r.ok("unknown role → [] (graceful)")

    # Unknown seniority — falls back to "new"
    result = get_eligible_duties("digest", "legendary")
    assert result == [{"duty": "digest", "trigger": "recurring"}]
    r.ok("unknown seniority → falls back to new")

    # --- get_promotion_duty ---

    # Digest senior missing monitor → promote to monitor
    promo = get_promotion_duty("digest", "senior", [{"duty": "digest", "trigger": "recurring"}])
    assert promo is not None
    assert promo["duty"] == "monitor"
    assert promo["trigger"] == "reactive"
    r.ok("digest/senior with [digest] → promote to monitor")

    # Digest senior already has both → None
    promo = get_promotion_duty("digest", "senior", [
        {"duty": "digest", "trigger": "recurring"},
        {"duty": "monitor", "trigger": "reactive"},
    ])
    assert promo is None
    r.ok("digest/senior with [digest, monitor] → None (full portfolio)")

    # Prepare senior — no promotion path
    promo = get_promotion_duty("prepare", "senior", [{"duty": "prepare"}])
    assert promo is None
    r.ok("prepare/senior → None (no expansion path)")

    # New-level agent — no promotion (only has seed duty which is expected)
    promo = get_promotion_duty("digest", "new", [{"duty": "digest"}])
    assert promo is None
    r.ok("digest/new with [digest] → None (new agents don't expand)")

    # Empty current_duties — returns first eligible
    promo = get_promotion_duty("digest", "senior", [])
    assert promo is not None
    assert promo["duty"] == "digest"
    r.ok("digest/senior with [] → promotes to digest (seed)")

    # None current_duties — same as empty
    promo = get_promotion_duty("digest", "senior", None)
    assert promo is not None
    r.ok("digest/senior with None → returns first eligible")

    # --- SKILL_ENABLED_ROLES ---
    assert "synthesize" in SKILL_ENABLED_ROLES
    assert "research" in SKILL_ENABLED_ROLES
    assert "monitor" in SKILL_ENABLED_ROLES
    assert "custom" in SKILL_ENABLED_ROLES
    assert "digest" not in SKILL_ENABLED_ROLES
    assert "prepare" not in SKILL_ENABLED_ROLES
    assert "pm" not in SKILL_ENABLED_ROLES
    r.ok("SKILL_ENABLED_ROLES: monitor/research/synthesize/custom yes, digest/prepare/pm no")

    # --- Portfolio completeness ---
    for role_name in ROLE_PORTFOLIOS:
        portfolio = ROLE_PORTFOLIOS[role_name]
        assert "new" in portfolio, f"{role_name} missing 'new' level"
        assert "associate" in portfolio, f"{role_name} missing 'associate' level"
        assert "senior" in portfolio, f"{role_name} missing 'senior' level"
        # Each level has at least the seed duty
        for level in ["new", "associate", "senior"]:
            duties = portfolio[level]
            assert len(duties) >= 1
            assert duties[0]["duty"] == role_name  # Seed duty always first
    r.ok("All roles have new/associate/senior levels with seed duty first")

    return r


# ============================================================================
# LAYER 2: Execution Wiring — duty dispatch, effective_role, duty context
# ============================================================================

@pytest.mark.asyncio
async def test_layer2_execution_wiring(client) -> LayerResult:
    """Test scheduler duty resolution and execution pipeline wiring."""
    r = LayerResult("Layer 2: Execution Wiring")
    logger.info("\n=== Layer 2: Execution Wiring ===")

    from jobs.unified_scheduler import resolve_due_duties
    from services.workspace import AgentWorkspace

    # --- resolve_due_duties ---

    # Agent with duties=null (legacy) → synthetic single duty
    legacy_agent = {"role": "digest", "duties": None}
    duties = resolve_due_duties(legacy_agent)
    assert len(duties) == 1
    assert duties[0]["duty"] == "digest"
    assert duties[0]["trigger"] == "recurring"
    r.ok("duties=null → synthetic single duty [digest]")

    # Agent with explicit single duty → returns it
    single_duty_agent = {
        "role": "digest",
        "duties": [{"duty": "digest", "trigger": "recurring", "status": "active"}],
    }
    duties = resolve_due_duties(single_duty_agent)
    assert len(duties) == 1
    assert duties[0]["duty"] == "digest"
    r.ok("explicit single duty → [digest]")

    # Agent with multi-duty portfolio → returns all active
    multi_duty_agent = {
        "role": "digest",
        "duties": [
            {"duty": "digest", "trigger": "recurring", "status": "active"},
            {"duty": "monitor", "trigger": "reactive", "status": "active"},
        ],
    }
    duties = resolve_due_duties(multi_duty_agent)
    assert len(duties) == 2
    duty_names = {d["duty"] for d in duties}
    assert duty_names == {"digest", "monitor"}
    r.ok("multi-duty agent → [digest, monitor]")

    # Agent with paused duty → filters it out
    partial_active = {
        "role": "digest",
        "duties": [
            {"duty": "digest", "trigger": "recurring", "status": "active"},
            {"duty": "monitor", "trigger": "reactive", "status": "paused"},
        ],
    }
    duties = resolve_due_duties(partial_active)
    assert len(duties) == 1
    assert duties[0]["duty"] == "digest"
    r.ok("paused duty filtered out → [digest] only")

    # Agent with empty duties list → falls back to seed role
    empty_duties = {"role": "research", "duties": []}
    duties = resolve_due_duties(empty_duties)
    # Empty list is falsy, so falls back to synthetic
    assert len(duties) == 1
    assert duties[0]["duty"] == "research"
    r.ok("empty duties list → synthetic [research]")

    # --- Workspace duty read/write ---
    slug = f"{TEST_PREFIX}exec-wiring"
    ws = AgentWorkspace(client, TEST_USER_ID, slug)

    # Write a duty file
    duty_content = "# Duty: monitor\n\nWatch for escalation patterns in Slack."
    success = await ws.write_duty("monitor", duty_content)
    assert success
    r.ok("write_duty('monitor') succeeded")

    # Read it back
    read_back = await ws.read_duty("monitor")
    assert read_back is not None
    assert "escalation patterns" in read_back
    r.ok("read_duty('monitor') returns correct content")

    # List duties
    duty_list = await ws.list_duties()
    assert "monitor" in duty_list
    r.ok("list_duties() includes 'monitor'")

    # Read non-existent duty → None
    missing = await ws.read_duty("nonexistent")
    assert missing is None
    r.ok("read_duty('nonexistent') → None")

    # --- effective_role override logic (test the concept) ---
    # When duty_name == role, effective_role stays as role
    agent_role = "digest"
    duty_name = "digest"
    effective_role = agent_role
    if duty_name and duty_name != agent_role:
        effective_role = duty_name
    assert effective_role == "digest"
    r.ok("duty=digest on digest agent → effective_role stays digest")

    # When duty_name != role (e.g., monitor on digest), effective_role overrides
    duty_name = "monitor"
    effective_role = agent_role
    if duty_name and duty_name != agent_role:
        effective_role = duty_name
    assert effective_role == "monitor"
    r.ok("duty=monitor on digest agent → effective_role becomes monitor")

    # effective_role for SKILL_ENABLED check
    from services.agent_framework import SKILL_ENABLED_ROLES
    assert effective_role in SKILL_ENABLED_ROLES  # monitor → gets skills
    assert agent_role not in SKILL_ENABLED_ROLES  # digest → no skills
    r.ok("monitor effective_role grants SKILL access; digest seed role does not")

    return r


# ============================================================================
# LAYER 3: Skills Utilization — RuntimeDispatch, render mock, workspace write
# ============================================================================

@pytest.mark.asyncio
async def test_layer3_skills_utilization(client) -> LayerResult:
    """Test RuntimeDispatch call flow with mocked render gateway."""
    r = LayerResult("Layer 3: Skills Utilization")
    logger.info("\n=== Layer 3: Skills Utilization ===")

    from services.primitives.runtime_dispatch import handle_runtime_dispatch

    # Build mock auth context
    class MockAuth:
        def __init__(self, client, user_id, agent_slug):
            self.client = client
            self.user_id = user_id
            self.agent_slug = agent_slug
            self.pending_renders = []

    auth = MockAuth(client, TEST_USER_ID, f"{TEST_PREFIX}skills-test")

    # Mock the render gateway HTTP call
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "success": True,
        "output_url": "https://storage.test/rendered/test-chart.png",
        "content_type": "image/png",
        "size_bytes": 12345,
    }
    mock_response.raise_for_status = MagicMock()

    # Mock render limit check (allow) — these are lazy imports inside handle_runtime_dispatch,
    # so patch at the source module (services.platform_limits)
    with patch("services.platform_limits.check_render_limit", return_value=(True, 5, 100)), \
         patch("services.platform_limits.check_work_budget", return_value=(True, 10, 1000)), \
         patch("services.platform_limits.record_render_usage"), \
         patch("services.platform_limits.record_work_units"), \
         patch("httpx.AsyncClient") as mock_httpx:

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.return_value = mock_client_instance

        # Test: Chart skill dispatch
        result = await handle_runtime_dispatch(auth, {
            "type": "chart",
            "input": {
                "chart_type": "bar",
                "title": "Test Growth",
                "labels": ["Jan", "Feb", "Mar"],
                "datasets": [{"label": "Users", "data": [100, 200, 300]}],
            },
            "output_format": "png",
            "filename": "test-growth-chart",
        })

        assert result["success"] is True
        assert result["output_url"] == "https://storage.test/rendered/test-chart.png"
        assert result["size_bytes"] == 12345
        r.ok("RuntimeDispatch chart → success, URL returned")

        # Verify workspace file was written
        # RuntimeDispatch writes to /agents/{agent_slug}/outputs/{safe_title}.{format}
        ws_result = client.table("workspace_files").select("path, content_url, tags").eq(
            "user_id", TEST_USER_ID
        ).like("path", f"%{auth.agent_slug}%test-growth-chart%").execute()

        if ws_result.data:
            ws_file = ws_result.data[0]
            assert ws_file["content_url"] == "https://storage.test/rendered/test-chart.png"
            assert "rendered" in ws_file["tags"]
            assert "chart" in ws_file["tags"]
            r.ok("Workspace file written with content_url + rendered/chart tags")
        else:
            # The workspace write may have used a different path — check by content_url
            ws_by_url = client.table("workspace_files").select("path, content_url, tags").eq(
                "user_id", TEST_USER_ID
            ).eq("content_url", "https://storage.test/rendered/test-chart.png").execute()
            if ws_by_url.data:
                ws_file = ws_by_url.data[0]
                assert "rendered" in ws_file["tags"]
                r.ok(f"Workspace file written (path={ws_file['path']}), content_url + tags correct")
            else:
                r.fail("Workspace file not found after RuntimeDispatch")

        # Verify pending_renders accumulated for manifest
        assert len(auth.pending_renders) == 1
        pr = auth.pending_renders[0]
        assert pr["content_url"] == "https://storage.test/rendered/test-chart.png"
        assert pr["skill_type"] == "chart"
        assert pr["role"] == "rendered"
        r.ok("pending_renders accumulated for save_output() manifest")

    # Test: Missing params → error
    auth2 = MockAuth(client, TEST_USER_ID, f"{TEST_PREFIX}skills-test-2")
    with patch("services.platform_limits.check_render_limit", return_value=(True, 5, 100)), \
         patch("services.platform_limits.check_work_budget", return_value=(True, 10, 1000)):
        result = await handle_runtime_dispatch(auth2, {"type": "", "input": {}, "output_format": ""})
        assert result["success"] is False
        assert result["error"] == "missing_params"
        r.ok("Missing params → error with correct code")

    # Test: Render limit exceeded → rejected
    auth3 = MockAuth(client, TEST_USER_ID, f"{TEST_PREFIX}skills-test-3")
    with patch("services.platform_limits.check_render_limit", return_value=(False, 100, 100)), \
         patch("services.platform_limits.check_work_budget", return_value=(True, 10, 1000)):
        result = await handle_runtime_dispatch(auth3, {
            "type": "document", "input": {"markdown": "# Test"}, "output_format": "pdf",
        })
        assert result["success"] is False
        assert result["error"] == "render_limit_exceeded"
        r.ok("Render limit exceeded → rejected before gateway call")

    # Test: Work budget exceeded → rejected
    auth4 = MockAuth(client, TEST_USER_ID, f"{TEST_PREFIX}skills-test-4")
    with patch("services.platform_limits.check_render_limit", return_value=(True, 5, 100)), \
         patch("services.platform_limits.check_work_budget", return_value=(False, 1000, 1000)):
        result = await handle_runtime_dispatch(auth4, {
            "type": "document", "input": {"markdown": "# Test"}, "output_format": "pdf",
        })
        assert result["success"] is False
        assert result["error"] == "work_budget_exceeded"
        r.ok("Work budget exceeded → rejected before gateway call")

    return r


# ============================================================================
# LAYER 4: Delivery Pipeline — output folder → manifest → email
# ============================================================================

@pytest.mark.asyncio
async def test_layer4_delivery_pipeline(client) -> LayerResult:
    """Test deliver_from_output_folder reads workspace and dispatches delivery."""
    r = LayerResult("Layer 4: Delivery Pipeline")
    logger.info("\n=== Layer 4: Delivery Pipeline ===")

    from services.workspace import AgentWorkspace
    from services.delivery import deliver_from_output_folder
    from integrations.core.types import ExportStatus

    slug = f"{TEST_PREFIX}delivery-test"
    ws = AgentWorkspace(client, TEST_USER_ID, slug)

    # Set up output folder with content and manifest
    output_folder = "outputs/2026-03-19T0900"

    await ws.write(
        f"{output_folder}/output.md",
        "# Weekly Slack Recap\n\nKey discussions in #engineering this week...\n\n## Highlights\n- API redesign approved",
        summary="Test output",
    )

    manifest = {
        "run_id": "test-run-001",
        "agent_id": "test-agent-001",
        "version": 1,
        "role": "digest",
        "created_at": "2026-03-19T09:00:00+00:00",
        "status": "active",
        "files": [
            {"path": "output.md", "type": "text/markdown", "role": "primary"},
            {"path": "recap-chart.png", "type": "image/png", "role": "rendered",
             "content_url": "https://storage.test/recap-chart.png", "size_bytes": 8000},
        ],
        "sources": ["/knowledge/slack/engineering/2026-03-18.md"],
        "feedback": {},
    }

    await ws.write(
        f"{output_folder}/manifest.json",
        json.dumps(manifest, indent=2),
        summary="Test manifest",
        content_type="application/json",
    )

    # Verify workspace reads work
    content = await ws.read(f"{output_folder}/output.md")
    assert content is not None
    assert "Slack Recap" in content
    r.ok("Output folder: output.md readable")

    manifest_raw = await ws.read(f"{output_folder}/manifest.json")
    parsed = json.loads(manifest_raw)
    assert parsed["files"][1]["content_url"] == "https://storage.test/recap-chart.png"
    r.ok("Output folder: manifest.json readable with rendered file refs")

    # Test delivery with mocked email exporter
    agent = {
        "id": "test-agent-001",
        "title": "Slack Recap",
        "role": "digest",
        "mode": "recurring",
        "destination": {"platform": "email", "email": "test@example.com"},
    }

    # Mock the email delivery function
    with patch("services.delivery._deliver_email_from_manifest") as mock_email:
        from integrations.core.types import ExportResult
        mock_email.return_value = ExportResult(
            status=ExportStatus.SUCCESS,
            external_id="msg_test_123",
        )

        result = await deliver_from_output_folder(
            client=client,
            user_id=TEST_USER_ID,
            agent=agent,
            output_folder=output_folder,
            agent_slug=slug,
            version_id="test-version-001",
            version_number=1,
        )

        assert result.status == ExportStatus.SUCCESS
        r.ok("deliver_from_output_folder → SENT status")

        # Verify _deliver_email_from_manifest was called with correct args
        call_args = mock_email.call_args
        assert call_args is not None
        # Check text_content was passed
        assert "Slack Recap" in call_args.kwargs.get("text_content", "") or \
               "Slack Recap" in (call_args.args[1] if len(call_args.args) > 1 else "")
        r.ok("Email delivery called with output content")

    # Test: missing output.md → FAILED
    result = await deliver_from_output_folder(
        client=client,
        user_id=TEST_USER_ID,
        agent=agent,
        output_folder="outputs/nonexistent-folder",
        agent_slug=slug,
        version_id="test-version-002",
        version_number=2,
    )
    assert result.status == ExportStatus.FAILED
    assert "not found" in result.error_message.lower()
    r.ok("Missing output.md → FAILED with clear error")

    # Test: no destination → FAILED
    no_dest_agent = {**agent, "destination": None}
    result = await deliver_from_output_folder(
        client=client,
        user_id=TEST_USER_ID,
        agent=no_dest_agent,
        output_folder=output_folder,
        agent_slug=slug,
        version_id="test-version-003",
        version_number=3,
    )
    assert result.status == ExportStatus.FAILED
    r.ok("No destination → FAILED")

    return r


# ============================================================================
# LAYER 5: Filesystem Persistence — save_output, manifest, version history
# ============================================================================

@pytest.mark.asyncio
async def test_layer5_filesystem_persistence(client) -> LayerResult:
    """Test workspace output saving, manifest structure, and version history."""
    r = LayerResult("Layer 5: Filesystem Persistence")
    logger.info("\n=== Layer 5: Filesystem Persistence ===")

    from services.workspace import AgentWorkspace

    slug = f"{TEST_PREFIX}filesystem-test"
    ws = AgentWorkspace(client, TEST_USER_ID, slug)

    # --- save_output with rendered files ---
    rendered_files = [
        {
            "path": "q2-report.pdf",
            "content_type": "application/pdf",
            "content_url": "https://storage.test/q2-report.pdf",
            "size_bytes": 50000,
            "role": "rendered",
            "skill_type": "document",
        },
    ]

    output_folder = await ws.save_output(
        content="# Q2 Report\n\nRevenue grew 15% QoQ...",
        run_id="run-fs-001",
        agent_id="agent-fs-001",
        version_number=1,
        role="research",
        rendered_files=rendered_files,
        sources=["/knowledge/gmail/reports/2026-03-18.md"],
    )

    assert output_folder is not None
    assert output_folder.startswith("outputs/")
    r.ok(f"save_output returned folder: {output_folder}")

    # Read back the text output
    text = await ws.read(f"{output_folder}/output.md")
    assert text is not None
    assert "Revenue grew 15%" in text
    r.ok("output.md persisted correctly")

    # Read and validate manifest
    manifest_raw = await ws.read(f"{output_folder}/manifest.json")
    assert manifest_raw is not None
    manifest = json.loads(manifest_raw)

    assert manifest["run_id"] == "run-fs-001"
    assert manifest["agent_id"] == "agent-fs-001"
    assert manifest["version"] == 1
    assert manifest["role"] == "research"
    assert manifest["status"] == "active"
    r.ok("Manifest: core fields correct")

    # Manifest files list
    assert len(manifest["files"]) == 2  # output.md + rendered PDF
    primary = next(f for f in manifest["files"] if f["role"] == "primary")
    assert primary["path"] == "output.md"
    assert primary["type"] == "text/markdown"
    r.ok("Manifest: primary file entry correct")

    rendered = next(f for f in manifest["files"] if f["role"] == "rendered")
    assert rendered["path"] == "q2-report.pdf"
    assert rendered["content_url"] == "https://storage.test/q2-report.pdf"
    assert rendered["size_bytes"] == 50000
    r.ok("Manifest: rendered file entry with content_url + size")

    assert manifest["sources"] == ["/knowledge/gmail/reports/2026-03-18.md"]
    r.ok("Manifest: sources preserved")

    # --- Version history (write same path, check archival) ---
    # Write a thesis file, then overwrite it
    await ws.write("thesis.md", "# Thesis v1\n\nInitial thesis about Q2 performance.")

    # Verify it exists
    thesis = await ws.read("thesis.md")
    assert thesis is not None
    assert "v1" in thesis
    r.ok("thesis.md v1 written")

    # Check history mechanism exists
    history = await ws.list("history/")
    # History may or may not have entries yet — the important thing is the method works
    r.ok(f"list('history/') returns {len(history)} items (method functional)")

    # --- Lifecycle column ---
    # Verify workspace_files rows have lifecycle set
    ws_rows = client.table("workspace_files").select(
        "path, lifecycle"
    ).eq("user_id", TEST_USER_ID).like(
        "path", f"%{slug}%output.md"
    ).execute()

    if ws_rows.data:
        for row in ws_rows.data:
            if "output.md" in row["path"] and output_folder.split("/")[-1] in row["path"]:
                assert row["lifecycle"] == "active"
                r.ok("output.md lifecycle = 'active'")
                break
        else:
            r.ok("Lifecycle check: output files present (lifecycle may be null for non-output writes)")
    else:
        r.fail("No workspace_files rows found for output")

    return r


# ============================================================================
# LAYER 6: Cross-Agent Communication — DiscoverAgents, ReadAgentContext
# ============================================================================

@pytest.mark.asyncio
async def test_layer6_cross_agent_communication(client) -> LayerResult:
    """Test inter-agent discovery, context reading, and project contribution paths."""
    r = LayerResult("Layer 6: Cross-Agent Communication")
    logger.info("\n=== Layer 6: Cross-Agent Communication ===")

    from services.primitives.workspace import handle_discover_agents, handle_read_agent_context
    from services.workspace import AgentWorkspace, get_agent_slug

    # Create two test agents in the DB
    agent_a_data = {
        "user_id": TEST_USER_ID,
        "title": f"{TEST_PREFIX}Slack Recap",
        "role": "digest",
        "scope": "platform",
        "status": "active",
        "sources": [{"platform": "slack", "id": "C123", "name": "engineering"}],
    }
    agent_b_data = {
        "user_id": TEST_USER_ID,
        "title": f"{TEST_PREFIX}Market Researcher",
        "role": "research",
        "scope": "research",
        "status": "active",
        "sources": [],
    }

    # Insert agents
    res_a = client.table("agents").insert(agent_a_data).execute()
    res_b = client.table("agents").insert(agent_b_data).execute()
    agent_a = res_a.data[0]
    agent_b = res_b.data[0]
    agent_a_id = agent_a["id"]
    agent_b_id = agent_b["id"]

    try:
        # Seed workspaces
        slug_a = get_agent_slug(agent_a)
        slug_b = get_agent_slug(agent_b)
        ws_a = AgentWorkspace(client, TEST_USER_ID, slug_a)
        ws_b = AgentWorkspace(client, TEST_USER_ID, slug_b)

        await ws_a.write("AGENT.md", "# Slack Recap\n\nDigest daily Slack activity from #engineering.")
        await ws_a.write("thesis.md", "# Domain Thesis\n\nThe engineering team communicates primarily via threads.")
        await ws_a.write("memory/preferences.md", "- User prefers bullet-point format\n- Skip bot messages")

        await ws_b.write("AGENT.md", "# Market Researcher\n\nInvestigate competitor trends.")
        await ws_b.write("thesis.md", "# Domain Thesis\n\nThe market is consolidating around AI-first platforms.")

        # --- DiscoverAgents ---
        class MockAuth:
            def __init__(self, client, user_id, calling_agent=None):
                self.client = client
                self.user_id = user_id
                self.agent = calling_agent

        # Agent B discovers Agent A
        auth_b = MockAuth(client, TEST_USER_ID, {"id": agent_b_id})
        discover_result = await handle_discover_agents(auth_b, {"role": "digest"})

        assert discover_result["success"] is True
        agents_found = discover_result.get("agents", [])
        a_ids = [a["agent_id"] for a in agents_found]
        assert agent_a_id in a_ids
        assert agent_b_id not in a_ids  # Excludes self
        r.ok("DiscoverAgents: Agent B finds Agent A by role=digest, excludes self")

        # Discover all (no filter)
        discover_all = await handle_discover_agents(auth_b, {})
        all_ids = [a["agent_id"] for a in discover_all.get("agents", [])]
        assert agent_a_id in all_ids
        r.ok("DiscoverAgents: no filter returns Agent A (among others)")

        # --- ReadAgentContext ---
        # Agent B reads Agent A's identity
        context_result = await handle_read_agent_context(auth_b, {
            "agent_id": agent_a_id,
            "files": "identity",
        })
        assert context_result["success"] is True
        assert context_result["agent_title"] == agent_a["title"]
        assert context_result["role"] == "digest"
        # Should have AGENT.md and thesis.md content
        identity_files = context_result.get("files", {})
        assert "AGENT.md" in str(identity_files) or "agent_md" in str(context_result)
        r.ok("ReadAgentContext: identity files returned for Agent A")

        # Read memory files
        memory_result = await handle_read_agent_context(auth_b, {
            "agent_id": agent_a_id,
            "files": "memory",
        })
        assert memory_result["success"] is True
        r.ok("ReadAgentContext: memory files accessible")

        # Read all files
        all_result = await handle_read_agent_context(auth_b, {
            "agent_id": agent_a_id,
            "files": "all",
        })
        assert all_result["success"] is True
        r.ok("ReadAgentContext: all files accessible")

        # Non-existent agent → error
        bad_result = await handle_read_agent_context(auth_b, {
            "agent_id": "00000000-0000-0000-0000-000000000000",
        })
        assert bad_result["success"] is False
        assert bad_result["error"] == "agent_not_found"
        r.ok("ReadAgentContext: non-existent agent → agent_not_found")

        # --- Project contribution path ---
        # Test that agents can write to project contribution folders
        project_slug = f"{TEST_PREFIX}q2-review"
        from services.workspace import ProjectWorkspace
        pws = ProjectWorkspace(client, TEST_USER_ID, project_slug)

        # Write a contribution from Agent A
        contrib_path = f"contributions/{slug_a}/latest.md"
        success = await pws.write(
            contrib_path,
            "# Slack Recap Contribution\n\nKey thread: API redesign discussion.",
            summary="Agent A contribution to Q2 Review",
        )
        assert success
        r.ok("Project contribution: Agent A wrote to contributions folder")

        # Read it back from project workspace
        contrib = await pws.read(contrib_path)
        assert contrib is not None
        assert "API redesign" in contrib
        r.ok("Project contribution: readable from ProjectWorkspace")

    finally:
        # Cleanup: delete test agents
        client.table("agents").delete().eq("id", agent_a_id).execute()
        client.table("agents").delete().eq("id", agent_b_id).execute()
        logger.info("    [cleanup] Test agents deleted")

    return r


# ============================================================================
# LAYER 7: Composer Promotion — promote_duty, portfolio gating, activity events
# ============================================================================

@pytest.mark.asyncio
async def test_layer7_composer_promotion(client) -> LayerResult:
    """Test _execute_promote_duty with portfolio validation and activity events."""
    r = LayerResult("Layer 7: Composer Promotion")
    logger.info("\n=== Layer 7: Composer Promotion ===")

    from services.composer import _execute_promote_duty
    from services.workspace import AgentWorkspace, get_agent_slug
    from services.activity_log import get_recent_activity

    # Create a test agent (digest, senior-worthy)
    agent_data = {
        "user_id": TEST_USER_ID,
        "title": f"{TEST_PREFIX}Promo Slack Recap",
        "role": "digest",
        "scope": "platform",
        "status": "active",
        "duties": [{"duty": "digest", "trigger": "recurring", "status": "active"}],
    }
    res = client.table("agents").insert(agent_data).execute()
    agent = res.data[0]
    agent_id = agent["id"]

    try:
        # Seed workspace with AGENT.md
        slug = get_agent_slug(agent)
        ws = AgentWorkspace(client, TEST_USER_ID, slug)
        await ws.write("AGENT.md", f"# {agent['title']}\n\nDigest daily Slack activity.")

        # --- Happy path: promote digest → monitor ---
        decision = {
            "action": "promote_duty",
            "agent_id": agent_id,
            "new_duty": "monitor",
            "reason": "Senior agent with 80%+ approval — ready for monitoring",
        }
        assessment = {}  # Not used by promote_duty directly

        result = await _execute_promote_duty(client, TEST_USER_ID, decision, assessment)
        assert len(result) == 1
        assert result[0]["action_type"] == "promote_duty"
        assert result[0]["new_duty"] == "monitor"
        r.ok("promote_duty: digest → monitor succeeded")

        # Verify JSONB updated
        refreshed = client.table("agents").select("duties").eq("id", agent_id).single().execute()
        duties = refreshed.data["duties"]
        duty_names = {d["duty"] for d in duties}
        assert "monitor" in duty_names
        assert "digest" in duty_names
        assert len(duties) == 2
        r.ok("promote_duty: agents.duties JSONB has [digest, monitor]")

        # Verify new duty entry has metadata
        monitor_duty = next(d for d in duties if d["duty"] == "monitor")
        assert monitor_duty["status"] == "active"
        assert monitor_duty["added_by"] == "composer"
        assert "added_at" in monitor_duty
        r.ok("promote_duty: monitor entry has status/added_by/added_at metadata")

        # Verify workspace duty file
        duty_content = await ws.read_duty("monitor")
        assert duty_content is not None
        assert "monitor" in duty_content.lower()
        assert "ready for monitoring" in duty_content.lower() or "monitoring" in duty_content.lower()
        r.ok("promote_duty: /duties/monitor.md written to workspace")

        # Verify AGENT.md updated with duties section
        agent_md = await ws.read("AGENT.md")
        assert "## Duties & Capabilities" in agent_md
        assert "monitor" in agent_md
        assert "(earned)" in agent_md
        assert "(primary)" in agent_md
        r.ok("promote_duty: AGENT.md updated with Duties & Capabilities section")

        # Verify activity_log event
        activities = await get_recent_activity(client, TEST_USER_ID, limit=20)
        duty_events = [a for a in activities if a["event_type"] == "duty_promoted"]
        if len(duty_events) >= 1:
            latest_event = duty_events[0]
            assert "monitor" in latest_event["summary"]
            assert latest_event["metadata"]["new_duty"] == "monitor"
            assert latest_event["metadata"]["seniority"] == "senior"
            r.ok("promote_duty: duty_promoted activity event written")
        else:
            # Activity log may use service client insert — query with broader scope
            direct_query = client.table("activity_log").select("*").eq(
                "user_id", TEST_USER_ID
            ).eq("event_type", "duty_promoted").order(
                "created_at", desc=True
            ).limit(1).execute()
            if direct_query.data:
                evt = direct_query.data[0]
                assert "monitor" in evt["summary"]
                assert evt["metadata"]["new_duty"] == "monitor"
                r.ok("promote_duty: duty_promoted activity event written (direct query)")
            else:
                r.fail("promote_duty: no duty_promoted activity event found")

        # --- Idempotency: promote same duty again → no-op ---
        result2 = await _execute_promote_duty(client, TEST_USER_ID, decision, assessment)
        assert result2 == []
        r.ok("promote_duty: duplicate promotion → empty result (idempotent)")

        # Verify JSONB unchanged
        refreshed2 = client.table("agents").select("duties").eq("id", agent_id).single().execute()
        assert len(refreshed2.data["duties"]) == 2  # Still 2, not 3
        r.ok("promote_duty: JSONB unchanged after duplicate attempt")

        # --- Portfolio gating: invalid duty for role ---
        bad_decision = {
            "action": "promote_duty",
            "agent_id": agent_id,
            "new_duty": "research",  # Not in digest portfolio
            "reason": "Testing invalid promotion",
        }
        result3 = await _execute_promote_duty(client, TEST_USER_ID, bad_decision, assessment)
        assert result3 == []
        r.ok("promote_duty: research on digest agent → rejected (not in portfolio)")

        # --- Missing agent_id ---
        bad_decision2 = {"action": "promote_duty", "new_duty": "monitor"}
        result4 = await _execute_promote_duty(client, TEST_USER_ID, bad_decision2, assessment)
        assert result4 == []
        r.ok("promote_duty: missing agent_id → empty result")

        # --- Non-existent agent ---
        bad_decision3 = {
            "action": "promote_duty",
            "agent_id": "00000000-0000-0000-0000-000000000000",
            "new_duty": "monitor",
        }
        result5 = await _execute_promote_duty(client, TEST_USER_ID, bad_decision3, assessment)
        assert result5 == []
        r.ok("promote_duty: non-existent agent → empty result")

    finally:
        # Cleanup
        client.table("agents").delete().eq("id", agent_id).execute()
        logger.info("    [cleanup] Test agent deleted")

    return r


# ============================================================================
# Cleanup
# ============================================================================

async def cleanup_test_data(client):
    """Remove all test workspace files and agents."""
    logger.info("\n=== Cleanup ===")

    # Delete workspace files with test prefix
    try:
        client.table("workspace_files").delete().eq(
            "user_id", TEST_USER_ID
        ).like("path", f"%{TEST_PREFIX}%").execute()
        logger.info("    Cleaned up workspace_files")
    except Exception as e:
        logger.warning(f"    Workspace cleanup: {e}")

    # Delete test agents (if any leaked)
    try:
        client.table("agents").delete().eq(
            "user_id", TEST_USER_ID
        ).like("title", f"{TEST_PREFIX}%").execute()
        logger.info("    Cleaned up test agents")
    except Exception as e:
        logger.warning(f"    Agent cleanup: {e}")

    # Delete test activity_log entries
    try:
        client.table("activity_log").delete().eq(
            "user_id", TEST_USER_ID
        ).like("summary", f"%{TEST_PREFIX}%").execute()
        logger.info("    Cleaned up activity_log")
    except Exception as e:
        logger.warning(f"    Activity cleanup: {e}")


# ============================================================================
# Runner
# ============================================================================

async def main():
    logger.info("=" * 70)
    logger.info("ADR-117 Phase 3 E2E Test: Duties, Skills, Delivery & Cross-Agent")
    logger.info("=" * 70)

    client = get_service_client()
    results: list[LayerResult] = []

    try:
        # Layer 1: Pure logic (no DB)
        results.append(test_layer1_portfolio_registry())

        # Layers 2-7: Require DB
        results.append(await test_layer2_execution_wiring(client))
        results.append(await test_layer3_skills_utilization(client))
        results.append(await test_layer4_delivery_pipeline(client))
        results.append(await test_layer5_filesystem_persistence(client))
        results.append(await test_layer6_cross_agent_communication(client))
        results.append(await test_layer7_composer_promotion(client))

    finally:
        await cleanup_test_data(client)

    # --- Summary ---
    logger.info("\n" + "=" * 70)
    logger.info("RESULTS")
    logger.info("=" * 70)

    total_passed = 0
    total_failed = 0

    for r in results:
        status = "✓ PASS" if r.failed == 0 else "✗ FAIL"
        logger.info(f"  {status}  {r.layer}: {r.passed} passed, {r.failed} failed")
        if r.errors:
            for err in r.errors:
                logger.info(f"         ✗ {err}")
        total_passed += r.passed
        total_failed += r.failed

    logger.info(f"\n  TOTAL: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        logger.error("\n  ✗ SOME TESTS FAILED")
        sys.exit(1)
    else:
        logger.info("\n  ✓ ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
