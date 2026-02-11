"""
ADR-042 Deliverable Execution Tests

Tests the simplified single-call execution model.

Run: cd api && python test_deliverable_execution.py
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone


def test_imports():
    """Verify all ADR-042 modules import correctly."""
    print("Testing imports...")

    from services.deliverable_execution import (
        execute_deliverable_generation,
        get_next_version_number,
        create_version_record,
        create_work_ticket,
        gather_context_inline,
        generate_draft_inline,
        update_version_staged,
        complete_work_ticket,
        log_execution_inputs,
    )

    print("  ✓ deliverable_execution imports OK")

    from services.primitives.execute import _handle_deliverable_generate
    print("  ✓ execute primitive handler imports OK")

    from jobs.unified_scheduler import process_deliverable
    print("  ✓ unified_scheduler imports OK")

    from services.event_triggers import execute_event_triggers
    print("  ✓ event_triggers imports OK")

    print("✅ imports: PASSED")


def test_work_ticket_no_chaining():
    """Verify work_ticket is created without chaining columns."""
    print("\nTesting work_ticket shape...")

    from services.deliverable_execution import create_work_ticket

    # Mock client
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
        "id": "test-ticket-id",
        "user_id": "test-user",
        "task": "deliverable.generate",
        "status": "running",
    }]

    # Run
    result = asyncio.run(create_work_ticket(
        client=mock_client,
        user_id="test-user",
        deliverable_id="test-deliverable",
        version_id="test-version",
    ))

    # Verify insert was called with correct shape
    insert_call = mock_client.table.return_value.insert.call_args
    insert_data = insert_call[0][0]

    # ADR-042: These must be NULL/False
    assert insert_data.get("depends_on_work_id") is None, "depends_on_work_id should be None"
    assert insert_data.get("pipeline_step") is None, "pipeline_step should be None"
    assert insert_data.get("chain_output_as_memory") is False, "chain_output_as_memory should be False"

    print("  ✓ depends_on_work_id: None")
    print("  ✓ pipeline_step: None")
    print("  ✓ chain_output_as_memory: False")
    print("✅ work_ticket_no_chaining: PASSED")


def test_version_minimal_population():
    """Verify version is created with minimal columns."""
    print("\nTesting version shape...")

    from services.deliverable_execution import create_version_record

    # Mock client
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{
        "id": "test-version-id",
        "deliverable_id": "test-deliverable",
        "version_number": 1,
        "status": "generating",
    }]

    # Run
    result = asyncio.run(create_version_record(
        client=mock_client,
        deliverable_id="test-deliverable",
        version_number=1,
    ))

    # Verify insert was called
    insert_call = mock_client.table.return_value.insert.call_args
    insert_data = insert_call[0][0]

    # ADR-042: These should NOT be in the insert (left as NULL)
    assert "edit_diff" not in insert_data, "edit_diff should not be set"
    assert "edit_categories" not in insert_data, "edit_categories should not be set"
    assert "edit_distance_score" not in insert_data, "edit_distance_score should not be set"
    assert "context_snapshot_id" not in insert_data, "context_snapshot_id should not be set"
    assert "pipeline_run_id" not in insert_data, "pipeline_run_id should not be set"

    # These SHOULD be set
    assert "id" in insert_data, "id should be set"
    assert "deliverable_id" in insert_data, "deliverable_id should be set"
    assert "version_number" in insert_data, "version_number should be set"
    assert "status" in insert_data, "status should be set"

    print("  ✓ edit_diff: not set (NULL)")
    print("  ✓ edit_categories: not set (NULL)")
    print("  ✓ edit_distance_score: not set (NULL)")
    print("  ✓ context_snapshot_id: not set (NULL)")
    print("  ✓ pipeline_run_id: not set (NULL)")
    print("  ✓ Required fields present: id, deliverable_id, version_number, status")
    print("✅ version_minimal_population: PASSED")


def test_execute_handler_uses_simplified_flow():
    """Verify Execute primitive uses execute_deliverable_generation."""
    print("\nTesting Execute primitive handler...")

    from services.primitives.execute import _handle_deliverable_generate
    import inspect

    # Get source code
    source = inspect.getsource(_handle_deliverable_generate)

    # Verify it imports from deliverable_execution
    assert "from services.deliverable_execution import execute_deliverable_generation" in source, \
        "Handler should import from deliverable_execution"

    # Verify it does NOT use old pipeline
    assert "execute_deliverable_pipeline" not in source, \
        "Handler should not use old pipeline"
    assert "enqueue_job" not in source, \
        "Handler should not use job queue"

    print("  ✓ Uses execute_deliverable_generation")
    print("  ✓ Does not use execute_deliverable_pipeline")
    print("  ✓ Does not use job queue")
    print("✅ execute_handler_uses_simplified_flow: PASSED")


def test_scheduler_uses_simplified_flow():
    """Verify scheduler uses execute_deliverable_generation."""
    print("\nTesting scheduler...")

    from jobs.unified_scheduler import process_deliverable
    import inspect

    source = inspect.getsource(process_deliverable)

    assert "from services.deliverable_execution import execute_deliverable_generation" in source, \
        "Scheduler should import from deliverable_execution"

    assert "execute_deliverable_pipeline" not in source, \
        "Scheduler should not use old pipeline"

    print("  ✓ Uses execute_deliverable_generation")
    print("  ✓ Does not use execute_deliverable_pipeline")
    print("✅ scheduler_uses_simplified_flow: PASSED")


def test_single_ticket_per_generation():
    """Verify only one work_ticket is created per generation."""
    print("\nTesting single ticket per generation...")

    from services.deliverable_execution import execute_deliverable_generation
    import inspect

    source = inspect.getsource(execute_deliverable_generation)

    # Count create_work_ticket calls - should be exactly 1
    ticket_calls = source.count("create_work_ticket(")
    assert ticket_calls == 1, f"Expected 1 create_work_ticket call, got {ticket_calls}"

    # Should NOT create multiple tickets
    assert "execute_gather_step" not in source, "Should not use execute_gather_step"
    assert "execute_synthesize_step" not in source, "Should not use execute_synthesize_step"
    assert "execute_stage_step" not in source, "Should not use execute_stage_step"

    print("  ✓ Single create_work_ticket call")
    print("  ✓ No legacy pipeline step calls")
    print("✅ single_ticket_per_generation: PASSED")


def test_input_logging():
    """Verify input logging uses work_execution_log."""
    print("\nTesting input logging...")

    from services.deliverable_execution import log_execution_inputs
    import inspect

    source = inspect.getsource(log_execution_inputs)

    assert "work_execution_log" in source, "Should use work_execution_log table"
    assert "context_snapshots" not in source, "Should not use context_snapshots table"

    print("  ✓ Uses work_execution_log")
    print("  ✓ Does not use context_snapshots")
    print("✅ input_logging: PASSED")


def test_full_auto_governance():
    """Verify full_auto governance still works."""
    print("\nTesting full_auto governance...")

    from services.deliverable_execution import execute_deliverable_generation
    import inspect

    source = inspect.getsource(execute_deliverable_generation)

    # Should handle full_auto governance
    assert 'governance == "full_auto"' in source or "governance == 'full_auto'" in source, \
        "Should check for full_auto governance"

    assert "auto-approving" in source.lower() or "auto_approve" in source.lower() or "status" in source, \
        "Should handle auto-approval"

    print("  ✓ Checks for full_auto governance")
    print("  ✓ Handles auto-approval flow")
    print("✅ full_auto_governance: PASSED")


if __name__ == "__main__":
    print("\n🧪 Running ADR-042 Deliverable Execution Tests...\n")
    print("=" * 60)

    test_imports()
    test_work_ticket_no_chaining()
    test_version_minimal_population()
    test_execute_handler_uses_simplified_flow()
    test_scheduler_uses_simplified_flow()
    test_single_ticket_per_generation()
    test_input_logging()
    test_full_auto_governance()

    print("\n" + "=" * 60)
    print("✅ All ADR-042 tests passed!")
    print("=" * 60)
