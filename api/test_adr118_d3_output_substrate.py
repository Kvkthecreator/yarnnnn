"""
E2E Test — ADR-118 D.3 Unified Output Substrate

Validates the full pipeline: generation → save_output() → manifest → delivery from output folder.
Does NOT call the LLM — instead injects synthetic draft content and exercises the workspace/delivery layers.

Usage:
    cd api && python test_adr118_d3_output_substrate.py

Phases:
1. Setup: Create test agent + agent_run in DB
2. save_output: Write output.md + manifest.json to workspace_files
3. Manifest structure: Validate manifest schema (files[], sources, status)
4. Rendered files in manifest: Simulate RuntimeDispatch pending_renders → manifest files[]
5. deliver_from_output_folder (email): Read from output folder, deliver via mock
6. Manifest delivery tracking: Verify manifest updated with delivery status
7. Fallback path: When output folder write fails, legacy deliver_version activates
8. Non-email delivery: Output folder content flows to non-email exporters
9. Cleanup: Remove test data
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test user — same as other tests
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
TEST_PREFIX = "TEST_ADR118_D3_"


@dataclass
class PhaseResult:
    phase: str
    passed: bool
    details: list[str]


def assert_true(cond: bool, msg: str, details: list[str]) -> bool:
    if cond:
        details.append(f"  ✓ {msg}")
        return True
    else:
        details.append(f"  ✗ FAIL: {msg}")
        return False


def assert_eq(actual: Any, expected: Any, msg: str, details: list[str]) -> bool:
    if actual == expected:
        details.append(f"  ✓ {msg}")
        return True
    else:
        details.append(f"  ✗ FAIL: {msg} — expected {expected!r}, got {actual!r}")
        return False


# =============================================================================
# Phase 1: Setup — create test agent + agent_run
# =============================================================================

async def phase_setup(client) -> tuple[PhaseResult, dict]:
    """Create a test agent and agent_run record."""
    details = []
    test_data = {}
    ok = True

    agent_id = str(uuid4())
    agent_title = f"{TEST_PREFIX}Output Substrate Agent"
    run_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Create test agent
    try:
        client.table("agents").insert({
            "id": agent_id,
            "user_id": TEST_USER_ID,
            "title": agent_title,
            "scope": "cross_platform",
            "role": "digest",
            "mode": "recurring",
            "status": "active",
            "destination": {"platform": "email", "target": "test@example.com", "format": "send"},
            "created_at": now,
        }).execute()
        ok = assert_true(True, f"Created test agent: {agent_id}", details) and ok
    except Exception as e:
        ok = assert_true(False, f"Create agent failed: {e}", details)
        return PhaseResult("1. Setup", False, details), test_data

    # Create agent_run
    try:
        client.table("agent_runs").insert({
            "id": run_id,
            "agent_id": agent_id,
            "version_number": 1,
            "status": "generating",
            "created_at": now,
        }).execute()
        ok = assert_true(True, f"Created agent_run: {run_id}", details) and ok
    except Exception as e:
        ok = assert_true(False, f"Create agent_run failed: {e}", details)

    test_data = {
        "agent_id": agent_id,
        "agent_title": agent_title,
        "run_id": run_id,
        "agent": {
            "id": agent_id,
            "title": agent_title,
            "scope": "cross_platform",
            "role": "digest",
            "mode": "recurring",
            "destination": {"platform": "email", "target": "test@example.com", "format": "send"},
        },
    }

    return PhaseResult("1. Setup", ok, details), test_data


# =============================================================================
# Phase 2: save_output — write output.md + manifest.json
# =============================================================================

async def phase_save_output(client, test_data: dict) -> tuple[PhaseResult, str]:
    """Test AgentWorkspace.save_output() writes output folder correctly."""
    from services.workspace import AgentWorkspace, get_agent_slug

    details = []
    ok = True

    agent = test_data["agent"]
    slug = get_agent_slug(agent)
    ws = AgentWorkspace(client, TEST_USER_ID, slug)

    draft_content = f"""# {TEST_PREFIX}Weekly Digest

## Highlights
- Product roadmap update shared in #product
- Customer escalation resolved by support team
- Engineering sprint review completed

## Key Discussions
Several cross-team threads about the upcoming launch.
"""

    output_folder = await ws.save_output(
        content=draft_content,
        run_id=test_data["run_id"],
        agent_id=test_data["agent_id"],
        version_number=1,
        role="digest",
    )

    ok = assert_true(output_folder is not None, "save_output returned a folder path", details) and ok
    ok = assert_true(
        output_folder and output_folder.startswith("outputs/"),
        f"Folder path starts with outputs/: {output_folder}",
        details,
    ) and ok

    # Verify output.md exists
    text = await ws.read(f"{output_folder}/output.md")
    ok = assert_true(text is not None and len(text) > 0, "output.md readable from workspace", details) and ok
    ok = assert_true(
        TEST_PREFIX in (text or ""),
        "output.md contains expected content",
        details,
    ) and ok

    # Verify manifest.json exists
    manifest_raw = await ws.read(f"{output_folder}/manifest.json")
    ok = assert_true(manifest_raw is not None, "manifest.json readable from workspace", details) and ok

    test_data["output_folder"] = output_folder
    test_data["slug"] = slug
    test_data["draft_content"] = draft_content

    return PhaseResult("2. save_output", ok, details), output_folder


# =============================================================================
# Phase 3: Manifest structure validation
# =============================================================================

async def phase_manifest_structure(client, test_data: dict) -> PhaseResult:
    """Validate manifest.json schema and content."""
    from services.workspace import AgentWorkspace

    details = []
    ok = True

    ws = AgentWorkspace(client, TEST_USER_ID, test_data["slug"])
    output_folder = test_data["output_folder"]

    manifest_raw = await ws.read(f"{output_folder}/manifest.json")
    try:
        manifest = json.loads(manifest_raw)
    except (json.JSONDecodeError, TypeError) as e:
        return PhaseResult("3. Manifest structure", False, [f"  ✗ Invalid JSON: {e}"])

    # Required fields
    ok = assert_eq(manifest.get("run_id"), test_data["run_id"], "manifest.run_id matches", details) and ok
    ok = assert_eq(manifest.get("agent_id"), test_data["agent_id"], "manifest.agent_id matches", details) and ok
    ok = assert_eq(manifest.get("version"), 1, "manifest.version is 1", details) and ok
    ok = assert_eq(manifest.get("role"), "digest", "manifest.role is digest", details) and ok
    ok = assert_eq(manifest.get("status"), "active", "manifest.status is active", details) and ok
    ok = assert_true("created_at" in manifest, "manifest.created_at present", details) and ok
    ok = assert_true(isinstance(manifest.get("files"), list), "manifest.files is a list", details) and ok
    ok = assert_true(isinstance(manifest.get("sources"), list), "manifest.sources is a list", details) and ok
    ok = assert_true(isinstance(manifest.get("feedback"), dict), "manifest.feedback is a dict", details) and ok

    # Primary file entry
    files = manifest.get("files", [])
    ok = assert_true(len(files) >= 1, f"manifest.files has >= 1 entry (got {len(files)})", details) and ok
    if files:
        primary = files[0]
        ok = assert_eq(primary.get("path"), "output.md", "Primary file is output.md", details) and ok
        ok = assert_eq(primary.get("type"), "text/markdown", "Primary file type is text/markdown", details) and ok
        ok = assert_eq(primary.get("role"), "primary", "Primary file role is 'primary'", details) and ok

    return PhaseResult("3. Manifest structure", ok, details)


# =============================================================================
# Phase 4: Rendered files in manifest
# =============================================================================

async def phase_rendered_files(client, test_data: dict) -> PhaseResult:
    """Test save_output with rendered_files from RuntimeDispatch."""
    from services.workspace import AgentWorkspace

    details = []
    ok = True

    ws = AgentWorkspace(client, TEST_USER_ID, test_data["slug"])

    # Simulate what RuntimeDispatch accumulates in pending_renders
    rendered_files = [
        {
            "path": "Q1-Report.pdf",
            "content_type": "application/pdf",
            "content_url": "https://storage.example.com/renders/q1-report.pdf",
            "size_bytes": 45056,
            "skill_type": "document",
            "role": "rendered",
        },
        {
            "path": "Growth-Chart.png",
            "content_type": "image/png",
            "content_url": "https://storage.example.com/renders/growth-chart.png",
            "size_bytes": 12800,
            "skill_type": "chart",
            "role": "rendered",
        },
    ]

    run_id_2 = str(uuid4())
    output_folder_2 = await ws.save_output(
        content="# Report with attachments\n\nSee attached PDF and chart.",
        run_id=run_id_2,
        agent_id=test_data["agent_id"],
        version_number=2,
        role="synthesize",
        rendered_files=rendered_files,
        sources=["platform:slack", "platform:gmail"],
    )

    ok = assert_true(output_folder_2 is not None, "save_output with renders succeeded", details) and ok

    # Read and parse manifest
    manifest_raw = await ws.read(f"{output_folder_2}/manifest.json")
    manifest = json.loads(manifest_raw) if manifest_raw else {}

    files = manifest.get("files", [])
    ok = assert_true(len(files) == 3, f"manifest.files has 3 entries (primary + 2 rendered), got {len(files)}", details) and ok

    # Check rendered file entries
    rendered = [f for f in files if f.get("role") == "rendered"]
    ok = assert_eq(len(rendered), 2, "2 rendered file entries in manifest", details) and ok
    if len(rendered) >= 1:
        ok = assert_true(
            rendered[0].get("content_url", "").startswith("https://"),
            "Rendered file has content_url",
            details,
        ) and ok
        ok = assert_true(rendered[0].get("size_bytes", 0) > 0, "Rendered file has size_bytes", details) and ok

    # Sources array
    sources = manifest.get("sources", [])
    ok = assert_eq(len(sources), 2, "manifest.sources has 2 entries", details) and ok

    test_data["output_folder_2"] = output_folder_2
    test_data["run_id_2"] = run_id_2

    return PhaseResult("4. Rendered files in manifest", ok, details)


# =============================================================================
# Phase 5: deliver_from_output_folder (email path)
# =============================================================================

async def phase_deliver_email(client, test_data: dict) -> PhaseResult:
    """Test deliver_from_output_folder reads from workspace and delivers."""
    details = []
    ok = True

    # We can't actually send email in tests. Instead, we verify the function:
    # 1. Reads output.md from workspace
    # 2. Reads manifest.json
    # 3. Reaches the email delivery path
    # We mock send_email to capture the call.

    from services.workspace import AgentWorkspace

    ws = AgentWorkspace(client, TEST_USER_ID, test_data["slug"])
    output_folder = test_data["output_folder"]

    # Verify the workspace data is readable (pre-condition for delivery)
    text = await ws.read(f"{output_folder}/output.md")
    ok = assert_true(text is not None and len(text) > 50, "output.md content is substantive", details) and ok

    manifest_raw = await ws.read(f"{output_folder}/manifest.json")
    manifest = json.loads(manifest_raw) if manifest_raw else {}
    # Note: Phase 4 may have overwritten this folder (same hour), so check run_id is present, not specific value
    ok = assert_true(manifest.get("run_id") is not None, "Manifest has a run_id for delivery", details) and ok

    # Test the delivery function with a mocked send_email
    import unittest.mock as mock

    mock_email_result = mock.AsyncMock()
    mock_email_result.return_value = mock.MagicMock(success=True, message_id="mock-msg-123", error=None)

    with mock.patch("jobs.email.send_email", mock_email_result):
        from services.delivery import deliver_from_output_folder
        from integrations.core.types import ExportStatus

        result = await deliver_from_output_folder(
            client=client,
            user_id=TEST_USER_ID,
            agent=test_data["agent"],
            output_folder=output_folder,
            agent_slug=test_data["slug"],
            version_id=test_data["run_id"],
            version_number=1,
        )

    ok = assert_true(result is not None, "deliver_from_output_folder returned a result", details) and ok
    ok = assert_eq(result.status, ExportStatus.SUCCESS, "Delivery status is SUCCESS", details) and ok
    ok = assert_eq(result.external_id, "mock-msg-123", "External ID matches mock", details) and ok

    # Verify send_email was called with correct args
    ok = assert_true(mock_email_result.called, "send_email was called", details) and ok
    if mock_email_result.called:
        call_kwargs = mock_email_result.call_args
        # send_email(to=..., subject=..., html=..., text=...)
        ok = assert_eq(call_kwargs.kwargs.get("to") or call_kwargs[1].get("to", call_kwargs[0][0] if call_kwargs[0] else None),
                       "test@example.com", "Email sent to correct recipient", details) and ok

    return PhaseResult("5. deliver_from_output_folder (email)", ok, details)


# =============================================================================
# Phase 6: Manifest delivery tracking
# =============================================================================

async def phase_manifest_delivery_tracking(client, test_data: dict) -> PhaseResult:
    """Verify manifest.json is updated with delivery status after send."""
    from services.workspace import AgentWorkspace

    details = []
    ok = True

    ws = AgentWorkspace(client, TEST_USER_ID, test_data["slug"])
    output_folder = test_data["output_folder"]

    # The delivery in Phase 5 should have updated the manifest
    manifest_raw = await ws.read(f"{output_folder}/manifest.json")
    manifest = json.loads(manifest_raw) if manifest_raw else {}

    delivery = manifest.get("delivery", {})
    ok = assert_true(len(delivery) > 0, "manifest.delivery is populated", details) and ok
    ok = assert_eq(delivery.get("channel"), "email", "delivery.channel is email", details) and ok
    ok = assert_eq(delivery.get("status"), "delivered", "delivery.status is delivered", details) and ok
    ok = assert_true("sent_at" in delivery, "delivery.sent_at present", details) and ok

    # Manifest status should be "delivered"
    ok = assert_eq(manifest.get("status"), "delivered", "manifest.status updated to delivered", details) and ok

    return PhaseResult("6. Manifest delivery tracking", ok, details)


# =============================================================================
# Phase 7: deliver_from_output_folder with rendered attachments
# =============================================================================

async def phase_deliver_with_attachments(client, test_data: dict) -> PhaseResult:
    """Test email delivery includes rendered file download links from manifest."""
    details = []
    ok = True

    import unittest.mock as mock

    captured_html = {}

    async def capture_send_email(**kwargs):
        captured_html["html"] = kwargs.get("html", "")
        captured_html["to"] = kwargs.get("to", "")
        captured_html["subject"] = kwargs.get("subject", "")
        result = mock.MagicMock(success=True, message_id="mock-msg-456", error=None)
        return result

    with mock.patch("jobs.email.send_email", side_effect=capture_send_email):
        from services.delivery import deliver_from_output_folder

        result = await deliver_from_output_folder(
            client=client,
            user_id=TEST_USER_ID,
            agent=test_data["agent"],
            output_folder=test_data["output_folder_2"],
            agent_slug=test_data["slug"],
            version_id=test_data["run_id_2"],
            version_number=2,
        )

    from integrations.core.types import ExportStatus

    ok = assert_eq(result.status, ExportStatus.SUCCESS, "Delivery with attachments succeeded", details) and ok
    ok = assert_true("html" in captured_html, "HTML was captured", details) and ok

    html = captured_html.get("html", "")
    # Check that rendered file links are in the HTML
    ok = assert_true("Q1-Report.pdf" in html, "PDF attachment link in email HTML", details) and ok
    ok = assert_true("Growth-Chart.png" in html, "Chart attachment link in email HTML", details) and ok
    ok = assert_true("Attachments" in html, "Attachments section header in HTML", details) and ok
    ok = assert_true("storage.example.com" in html, "Storage URL present in attachment links", details) and ok

    return PhaseResult("7. Email delivery with rendered attachments", ok, details)


# =============================================================================
# Phase 8: deliver_from_output_folder — missing output.md
# =============================================================================

async def phase_missing_output(client, test_data: dict) -> PhaseResult:
    """Verify graceful failure when output.md is missing from workspace."""
    details = []
    ok = True

    import unittest.mock as mock

    mock_send = mock.AsyncMock()
    with mock.patch("jobs.email.send_email", mock_send):
        from services.delivery import deliver_from_output_folder
        from integrations.core.types import ExportStatus

        result = await deliver_from_output_folder(
            client=client,
            user_id=TEST_USER_ID,
            agent=test_data["agent"],
            output_folder="outputs/nonexistent-folder",
            agent_slug=test_data["slug"],
            version_id=str(uuid4()),
            version_number=99,
        )

    ok = assert_eq(result.status, ExportStatus.FAILED, "Delivery fails when output.md missing", details) and ok
    ok = assert_true(
        "not found" in (result.error_message or "").lower(),
        f"Error message mentions 'not found': {result.error_message}",
        details,
    ) and ok
    ok = assert_true(not mock_send.called, "send_email was NOT called", details) and ok

    return PhaseResult("8. Missing output.md graceful failure", ok, details)


# =============================================================================
# Phase 9: HeadlessAuth pending_renders accumulation
# =============================================================================

async def phase_pending_renders_accumulation(client, test_data: dict) -> PhaseResult:
    """Verify HeadlessAuth.pending_renders accumulates rendered file metadata."""
    from services.primitives.registry import create_headless_executor

    details = []
    ok = True

    executor = create_headless_executor(client, TEST_USER_ID, agent=test_data["agent"])
    auth = getattr(executor, "auth", None)
    ok = assert_true(auth is not None, "executor.auth is accessible", details) and ok
    if not auth:
        return PhaseResult("9. HeadlessAuth pending_renders", False, details)

    ok = assert_true(hasattr(auth, "pending_renders"), "HeadlessAuth has pending_renders", details) and ok
    ok = assert_eq(auth.pending_renders, [], "pending_renders starts empty", details) and ok
    ok = assert_true(auth.agent_slug is not None, f"agent_slug derived: {auth.agent_slug}", details) and ok

    # Simulate RuntimeDispatch appending
    auth.pending_renders.append({
        "path": "test-doc.pdf",
        "content_type": "application/pdf",
        "content_url": "https://example.com/test.pdf",
        "size_bytes": 1024,
        "skill_type": "document",
        "role": "rendered",
    })
    ok = assert_eq(len(auth.pending_renders), 1, "pending_renders has 1 entry after append", details) and ok
    ok = assert_eq(auth.pending_renders[0]["path"], "test-doc.pdf", "Entry path correct", details) and ok

    return PhaseResult("9. HeadlessAuth pending_renders", ok, details)


# =============================================================================
# Phase 10: update_manifest_delivery
# =============================================================================

async def phase_update_manifest_delivery(client, test_data: dict) -> PhaseResult:
    """Test AgentWorkspace.update_manifest_delivery() directly."""
    from services.workspace import AgentWorkspace

    details = []
    ok = True

    ws = AgentWorkspace(client, TEST_USER_ID, test_data["slug"])
    output_folder_2 = test_data["output_folder_2"]

    # Update delivery status on the second output folder
    delivery_status = {
        "channel": "slack",
        "status": "delivered",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "external_id": "slack-ts-123",
    }
    result = await ws.update_manifest_delivery(output_folder_2, delivery_status)
    ok = assert_true(result, "update_manifest_delivery returned True", details) and ok

    # Re-read and verify
    manifest_raw = await ws.read(f"{output_folder_2}/manifest.json")
    manifest = json.loads(manifest_raw) if manifest_raw else {}

    delivery = manifest.get("delivery", {})
    ok = assert_eq(delivery.get("channel"), "slack", "delivery.channel updated to slack", details) and ok
    ok = assert_eq(delivery.get("external_id"), "slack-ts-123", "delivery.external_id set", details) and ok
    ok = assert_eq(manifest.get("status"), "delivered", "manifest.status is delivered", details) and ok

    # Verify the manifest workspace_files row has lifecycle=delivered
    row = (
        client.table("workspace_files")
        .select("lifecycle")
        .eq("user_id", TEST_USER_ID)
        .like("path", f"%{output_folder_2}/manifest.json")
        .single()
        .execute()
    )
    if row.data:
        ok = assert_eq(row.data.get("lifecycle"), "delivered", "workspace_files lifecycle is 'delivered'", details) and ok
    else:
        ok = assert_true(False, "manifest.json row found in workspace_files", details)

    return PhaseResult("10. update_manifest_delivery", ok, details)


# =============================================================================
# Phase 11: Cleanup
# =============================================================================

async def phase_cleanup(client, test_data: dict) -> PhaseResult:
    """Remove test data."""
    details = []

    agent_id = test_data.get("agent_id")
    if not agent_id:
        return PhaseResult("11. Cleanup", True, ["  ✓ No test data to clean"])

    try:
        # Delete agent_runs
        client.table("agent_runs").delete().eq("agent_id", agent_id).execute()
        details.append("  ✓ Deleted agent_runs")
    except Exception as e:
        details.append(f"  ⚠ agent_runs cleanup: {e}")

    try:
        # Delete workspace_files for this agent
        slug = test_data.get("slug", "")
        if slug:
            client.table("workspace_files").delete().eq(
                "user_id", TEST_USER_ID
            ).like("path", f"/agents/{slug}/%").execute()
            details.append(f"  ✓ Deleted workspace_files for /agents/{slug}/")
    except Exception as e:
        details.append(f"  ⚠ workspace_files cleanup: {e}")

    try:
        # Delete agent
        client.table("agents").delete().eq("id", agent_id).execute()
        details.append(f"  ✓ Deleted test agent {agent_id}")
    except Exception as e:
        details.append(f"  ⚠ agent cleanup: {e}")

    return PhaseResult("11. Cleanup", True, details)


# =============================================================================
# Main Runner
# =============================================================================

async def main():
    from services.supabase import get_service_client
    client = get_service_client()

    print("\n" + "=" * 72)
    print("ADR-118 D.3: Unified Output Substrate — E2E Test")
    print("=" * 72)

    results: list[PhaseResult] = []
    test_data = {}

    # Phase 1: Setup
    result, test_data = await phase_setup(client)
    results.append(result)
    if not result.passed:
        print(f"\n{'✗' if not result.passed else '✓'} {result.phase}")
        for d in result.details:
            print(d)
        print("\n⛔ Setup failed — aborting.")
        return

    # Phase 2: save_output
    result, output_folder = await phase_save_output(client, test_data)
    results.append(result)

    # Phase 3: Manifest structure
    if test_data.get("output_folder"):
        result = await phase_manifest_structure(client, test_data)
        results.append(result)

    # Phase 4: Rendered files
    result = await phase_rendered_files(client, test_data)
    results.append(result)

    # Phase 5: Email delivery
    if test_data.get("output_folder"):
        result = await phase_deliver_email(client, test_data)
        results.append(result)

    # Phase 6: Manifest delivery tracking
    if test_data.get("output_folder"):
        result = await phase_manifest_delivery_tracking(client, test_data)
        results.append(result)

    # Phase 7: Email delivery with rendered attachments
    if test_data.get("output_folder_2"):
        result = await phase_deliver_with_attachments(client, test_data)
        results.append(result)

    # Phase 8: Missing output.md
    result = await phase_missing_output(client, test_data)
    results.append(result)

    # Phase 9: HeadlessAuth pending_renders
    result = await phase_pending_renders_accumulation(client, test_data)
    results.append(result)

    # Phase 10: update_manifest_delivery
    if test_data.get("output_folder_2"):
        result = await phase_update_manifest_delivery(client, test_data)
        results.append(result)

    # Phase 11: Cleanup
    result = await phase_cleanup(client, test_data)
    results.append(result)

    # Print results
    print()
    total_pass = 0
    total_fail = 0
    for r in results:
        icon = "✓" if r.passed else "✗"
        print(f"\n{icon} {r.phase}")
        for d in r.details:
            print(d)
        if r.passed:
            total_pass += 1
        else:
            total_fail += 1

    print("\n" + "=" * 72)
    print(f"Results: {total_pass} passed, {total_fail} failed, {len(results)} total")
    print("=" * 72)

    if total_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
