"""
ADR-042 Integration Tests

Tests the simplified deliverable execution against real database.

Requirements:
- .env file with SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY
- At least one user with a deliverable in the database

Run: cd api && python -m tests.test_adr042_integration
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value


def check_env():
    """Verify required environment variables."""
    required = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"Missing env vars: {missing}")
        print("Create api/.env with required variables")
        return False
    return True


async def test_database_connection():
    """Verify database connection works."""
    print("\n1. Testing database connection...")

    from supabase import create_client

    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )

    # Simple query
    result = client.table("deliverables").select("id").limit(1).execute()

    print(f"   Connected to Supabase")
    print(f"   Found {len(result.data)} deliverable(s)")
    print("   PASSED")
    return client


async def test_find_test_deliverable(client):
    """Find a deliverable to test with."""
    print("\n2. Finding test deliverable...")

    result = (
        client.table("deliverables")
        .select("id, user_id, title, deliverable_type, status")
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    if not result.data:
        print("   No active deliverables found")
        print("   SKIPPED (create a deliverable first)")
        return None

    deliverable = result.data[0]
    print(f"   Found: {deliverable['title']} ({deliverable['id'][:8]}...)")
    print(f"   Type: {deliverable['deliverable_type']}")
    print("   PASSED")
    return deliverable


async def test_get_full_deliverable(client, deliverable_id: str):
    """Get full deliverable record."""
    print("\n3. Loading full deliverable...")

    result = (
        client.table("deliverables")
        .select("*")
        .eq("id", deliverable_id)
        .single()
        .execute()
    )

    deliverable = result.data
    print(f"   Loaded: {deliverable['title']}")
    print(f"   Sources: {len(deliverable.get('sources', []))}")
    print("   PASSED")
    return deliverable


async def test_execute_generation(client, deliverable: dict):
    """Test the simplified execution flow."""
    print("\n4. Testing execute_deliverable_generation...")

    # Check if ANTHROPIC_API_KEY is set (needed for actual generation)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("   ANTHROPIC_API_KEY not set")
        print("   SKIPPED (would need API key for full test)")
        return None

    from services.deliverable_execution import execute_deliverable_generation

    user_id = deliverable["user_id"]

    print(f"   Executing for user: {user_id[:8]}...")

    result = await execute_deliverable_generation(
        client=client,
        user_id=user_id,
        deliverable=deliverable,
        trigger_context={"type": "integration_test"},
    )

    if result.get("success"):
        print(f"   Version created: {result.get('version_number')}")
        print(f"   Status: {result.get('status')}")
        print(f"   Version ID: {result.get('version_id')[:8]}...")
        print("   PASSED")
    else:
        print(f"   Failed: {result.get('message')}")
        print("   FAILED")

    return result


async def test_verify_work_ticket(client, version_id: str):
    """Verify the work_ticket was created correctly."""
    print("\n5. Verifying work_ticket shape...")

    result = (
        client.table("work_tickets")
        .select("*")
        .eq("deliverable_version_id", version_id)
        .execute()
    )

    if not result.data:
        print("   No work_ticket found")
        print("   FAILED")
        return False

    ticket = result.data[0]

    # ADR-042 checks
    checks = {
        "depends_on_work_id is NULL": ticket.get("depends_on_work_id") is None,
        "pipeline_step is NULL": ticket.get("pipeline_step") is None,
        "chain_output_as_memory is FALSE": ticket.get("chain_output_as_memory") is False,
        "status is completed": ticket.get("status") == "completed",
    }

    all_passed = True
    for check, passed in checks.items():
        status = "OK" if passed else "FAILED"
        print(f"   {check}: {status}")
        if not passed:
            all_passed = False

    # Count tickets for this version (should be exactly 1)
    ticket_count = len(result.data)
    if ticket_count != 1:
        print(f"   Expected 1 ticket, got {ticket_count}: FAILED")
        all_passed = False
    else:
        print(f"   Single ticket created: OK")

    if all_passed:
        print("   PASSED")
    else:
        print("   FAILED")

    return all_passed


async def test_verify_version_shape(client, version_id: str):
    """Verify the version was created with minimal columns."""
    print("\n6. Verifying version shape...")

    result = (
        client.table("deliverable_versions")
        .select("*")
        .eq("id", version_id)
        .single()
        .execute()
    )

    version = result.data

    # ADR-042 checks - these should be NULL
    null_checks = {
        "edit_diff": version.get("edit_diff"),
        "edit_categories": version.get("edit_categories"),
        "edit_distance_score": version.get("edit_distance_score"),
        "context_snapshot_id": version.get("context_snapshot_id"),
        "pipeline_run_id": version.get("pipeline_run_id"),
    }

    all_passed = True
    for field, value in null_checks.items():
        if value is None:
            print(f"   {field} is NULL: OK")
        else:
            print(f"   {field} is NOT NULL ({value}): FAILED")
            all_passed = False

    # These should be set
    set_checks = {
        "status": version.get("status"),
        "draft_content": version.get("draft_content"),
        "staged_at": version.get("staged_at"),
    }

    for field, value in set_checks.items():
        if value:
            print(f"   {field} is set: OK")
        else:
            print(f"   {field} is NOT set: FAILED")
            all_passed = False

    if all_passed:
        print("   PASSED")
    else:
        print("   FAILED")

    return all_passed


async def test_verify_execution_log(client, version_id: str):
    """Verify execution was logged."""
    print("\n7. Verifying execution log...")

    # Get ticket first
    ticket_result = (
        client.table("work_tickets")
        .select("id")
        .eq("deliverable_version_id", version_id)
        .single()
        .execute()
    )

    if not ticket_result.data:
        print("   No ticket found")
        print("   SKIPPED")
        return True

    ticket_id = ticket_result.data["id"]

    # Check execution log
    log_result = (
        client.table("work_execution_log")
        .select("*")
        .eq("ticket_id", ticket_id)
        .order("timestamp", desc=False)
        .execute()
    )

    if not log_result.data:
        print("   No execution log entries")
        print("   FAILED")
        return False

    logs = log_result.data
    stages = [log["stage"] for log in logs]

    print(f"   Found {len(logs)} log entries")
    print(f"   Stages: {stages}")

    # Should have at least 'started' and 'completed'
    if "started" in stages and "completed" in stages:
        print("   Has started + completed: OK")
        print("   PASSED")
        return True
    else:
        print("   Missing expected stages")
        print("   FAILED")
        return False


async def cleanup_test_version(client, version_id: str):
    """Clean up test-created version."""
    print("\n8. Cleaning up test data...")

    try:
        # Delete version (cascades to work_tickets via FK)
        client.table("deliverable_versions").delete().eq("id", version_id).execute()
        print(f"   Deleted version {version_id[:8]}...")
        print("   PASSED")
    except Exception as e:
        print(f"   Cleanup failed: {e}")
        print("   FAILED (manual cleanup may be needed)")


async def run_integration_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("ADR-042 Integration Tests")
    print("=" * 60)

    if not check_env():
        return False

    # 1. Database connection
    client = await test_database_connection()
    if not client:
        return False

    # 2. Find test deliverable
    deliverable_summary = await test_find_test_deliverable(client)
    if not deliverable_summary:
        print("\nNo deliverables to test. Create one first.")
        return True  # Not a failure, just no data

    # 3. Get full deliverable
    deliverable = await test_get_full_deliverable(client, deliverable_summary["id"])

    # 4. Execute generation
    result = await test_execute_generation(client, deliverable)
    if not result or not result.get("success"):
        print("\nGeneration failed or skipped")
        return result is None  # True if skipped, False if failed

    version_id = result.get("version_id")

    # 5. Verify work_ticket
    ticket_ok = await test_verify_work_ticket(client, version_id)

    # 6. Verify version shape
    version_ok = await test_verify_version_shape(client, version_id)

    # 7. Verify execution log
    log_ok = await test_verify_execution_log(client, version_id)

    # 8. Cleanup
    await cleanup_test_version(client, version_id)

    # Summary
    print("\n" + "=" * 60)
    all_passed = ticket_ok and version_ok and log_ok
    if all_passed:
        print("All integration tests PASSED")
    else:
        print("Some tests FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    sys.exit(0 if success else 1)
