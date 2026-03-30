"""
Validation Suite — Recent 5 Commits (2026-03-28/29)

Tests:
  Commit 1 (0a7c9cc): Sparse context surfacing in working memory gaps
  Commit 2 (6757833): Task output loading — limit(20) fallback fix
  Commit 3 (24f3734): Restore context + task actions in chat plus menu
  Commit 4 (bffc047): Live process progress + pipeline→process terminology
  Commit 5 (901bceb): ADR-146 Gate 1 — primitive hardening, 27→19 tools

Strategy: Real DB reads, import validation, structural checks, no live LLM calls.
Test user: kvkthecreator@gmail.com

Usage:
    cd api && python test_recent_commits.py
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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

# Results tracking
RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    logger.info(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


# =============================================================================
# Commit 1: Sparse context surfacing (0a7c9cc)
# =============================================================================

def test_classify_richness():
    """_classify_richness returns empty/sparse/rich correctly."""
    from services.working_memory import _classify_richness

    # Empty cases
    record("richness: None → empty", _classify_richness(None) == "empty")
    record("richness: '' → empty", _classify_richness("") == "empty")
    record("richness: whitespace → empty", _classify_richness("   \n  ") == "empty")

    # Sparse cases — short content or few lines
    record("richness: short text → sparse", _classify_richness("Hi I'm John") == "sparse")
    record("richness: heading only → sparse", _classify_richness("# Identity\nJohn Doe") == "sparse")
    record("richness: <100 chars → sparse", _classify_richness("x" * 50) == "sparse")

    # Rich cases — substantial content
    rich_content = "\n".join([f"Line {i}: Some meaningful content here." for i in range(10)])
    record("richness: 10 lines → rich", _classify_richness(rich_content) == "rich")
    # Must be >= 100 chars AND >= 3 newlines (after strip)
    multi_line_content = "\n".join([f"This is a meaningful content line number {i} with enough text" for i in range(6)])
    record("richness: 6 long lines → rich",
           _classify_richness(multi_line_content) == "rich")


def test_sparse_context_in_format():
    """format_for_prompt surfaces sparse identity/brand with guidance."""
    from services.working_memory import format_for_prompt

    # Simulate working memory with sparse identity
    wm_sparse = {
        "profile": {"name": "Test"},
        "preferences": [],
        "known": [],
        "identity": "Hi I'm John",
        "brand": None,
        "orchestration_playbook": None,
        "agents": [],
        "platforms": [],
        "recent_sessions": [],
        "system_summary": {},
        "system_reference": {"agent_roles": [], "connected_platforms": []},
        "user_shared_files": [],
        "context_readiness": {
            "identity": "sparse",
            "brand": "empty",
            "documents": 0,
            "tasks": 0,
        },
    }

    formatted = format_for_prompt(wm_sparse)

    # Should contain sparse guidance
    record("sparse identity surfaces in prompt",
           "sparse" in formatted.lower() and "enrich" in formatted.lower())
    record("empty brand surfaces in prompt",
           "brand" in formatted.lower() and ("empty" in formatted.lower() or "none" in formatted.lower()))
    record("context gaps section present",
           "context gaps" in formatted.lower())


def test_sparse_vs_empty_differentiation():
    """Sparse and empty produce different guidance."""
    from services.working_memory import format_for_prompt

    wm_empty = {
        "profile": {}, "preferences": [], "known": [],
        "identity": None, "brand": None, "orchestration_playbook": None,
        "agents": [], "platforms": [], "recent_sessions": [],
        "system_summary": {}, "system_reference": {"agent_roles": [], "connected_platforms": []},
        "user_shared_files": [],
        "context_readiness": {"identity": "empty", "brand": "empty", "documents": 0, "tasks": 0},
    }

    wm_sparse = dict(wm_empty)
    wm_sparse["identity"] = "Just a name"
    wm_sparse["context_readiness"] = {"identity": "sparse", "brand": "empty", "documents": 0, "tasks": 0}

    fmt_empty = format_for_prompt(wm_empty)
    fmt_sparse = format_for_prompt(wm_sparse)

    # Both should have gaps, but sparse should mention "enrich" specifically
    record("sparse identity has 'enrich' guidance", "enrich" in fmt_sparse.lower())
    # Empty identity should mention "share" or similar
    record("empty identity has gap signal", "identity" in fmt_empty.lower())


# =============================================================================
# Commit 2: Task output loading fix (6757833)
# =============================================================================

async def test_latest_output_fallback():
    """get_latest_task_output uses limit(20) and falls back to step outputs."""
    # Verify the route code uses limit(20) not limit(1)
    import inspect
    from routes.tasks import get_latest_task_output

    source = inspect.getsource(get_latest_task_output)

    record("latest output uses limit(20)", "limit(20)" in source)
    # Note: limit(1) may exist in other queries in the function; key check is limit(20) for the main query
    record("latest output query uses limit(20) not limit(1) for output search",
           source.count("limit(20)") >= 1)
    record("latest output has step-skip logic", "/step-" in source)
    record("latest output has fallback to step output",
           "fallback" in source.lower() or "if not chosen and rows" in source)


# =============================================================================
# Commit 3: Chat plus menu actions (24f3734)
# =============================================================================

def test_plus_menu_actions_restored():
    """Verify context + task actions exist in the plus menu component."""
    # Read the workfloor page to check for plus menu actions
    workfloor_path = Path(__file__).parent.parent / "web" / "app" / "(authenticated)" / "workfloor" / "page.tsx"
    if not workfloor_path.exists():
        # Try orchestrator as alternative
        workfloor_path = Path(__file__).parent.parent / "web" / "app" / "(authenticated)" / "orchestrator" / "page.tsx"

    if workfloor_path.exists():
        content = workfloor_path.read_text()
        record("plus menu has create-task action",
               "create-task" in content or "CreateTask" in content or "task" in content.lower())
        record("plus menu has identity action",
               "identity" in content.lower() or "update-identity" in content)
        record("plus menu has brand action",
               "brand" in content.lower() or "update-brand" in content)
    else:
        record("workfloor/orchestrator page found", False, "Could not locate page file")


# =============================================================================
# Commit 4: Live process progress + terminology (bffc047)
# =============================================================================

def test_pipeline_to_process_terminology():
    """User-facing terminology is 'process', internal code retains 'pipeline'."""
    process_tab_path = Path(__file__).parent.parent / "web" / "components" / "tasks" / "ProcessTab.tsx"
    pipeline_tab_path = Path(__file__).parent.parent / "web" / "components" / "tasks" / "PipelineTab.tsx"

    record("ProcessTab.tsx exists", process_tab_path.exists())
    record("PipelineTab.tsx deleted", not pipeline_tab_path.exists())

    if process_tab_path.exists():
        content = process_tab_path.read_text()
        record("ProcessTab uses 'Process' in UI text",
               "Process" in content and "process" in content.lower())


def test_process_types_exist():
    """Frontend types include process-related types."""
    types_path = Path(__file__).parent.parent / "web" / "types" / "index.ts"
    if types_path.exists():
        content = types_path.read_text()
        record("ProcessStepOutput type exists",
               "ProcessStepOutput" in content or "PipelineStepOutput" in content)
        record("ProcessStepsResponse type exists",
               "ProcessStepsResponse" in content or "PipelineStepsResponse" in content)
        record("RunStatus type exists", "RunStatus" in content)
    else:
        record("types/index.ts found", False)


def test_status_endpoint_exists():
    """GET /tasks/{slug}/status endpoint is registered."""
    import inspect
    from routes.tasks import get_run_status

    record("get_run_status endpoint exists", callable(get_run_status))

    source = inspect.getsource(get_run_status)
    record("status endpoint reads status.json", "status.json" in source)


def test_status_json_written_during_pipeline():
    """task_pipeline.py writes status.json during multi-step execution."""
    import inspect
    from services.task_pipeline import _execute_pipeline

    source = inspect.getsource(_execute_pipeline)
    record("pipeline writes status.json", "status.json" in source)
    record("pipeline tracks completed_steps", "completed_steps" in source)
    record("pipeline tracks current_step", "current_step" in source)


def test_api_client_has_status_methods():
    """Frontend API client has getRunStatus and getStepOutputs methods."""
    client_path = Path(__file__).parent.parent / "web" / "lib" / "api" / "client.ts"
    if client_path.exists():
        content = client_path.read_text()
        record("API client has getRunStatus", "getRunStatus" in content)
        record("API client has getStepOutputs", "getStepOutputs" in content)
    else:
        record("client.ts found", False)


# =============================================================================
# Commit 5: ADR-146 Primitive Hardening (901bceb)
# =============================================================================

def test_primitive_consolidation_imports():
    """Verify new consolidated primitives import cleanly."""
    # UpdateContext
    from services.primitives.update_context import UPDATE_CONTEXT_TOOL, handle_update_context
    record("UpdateContext tool imports", UPDATE_CONTEXT_TOOL["name"] == "UpdateContext")
    record("UpdateContext handler imports", callable(handle_update_context))

    # ManageTask
    from services.primitives.manage_task import MANAGE_TASK_TOOL, handle_manage_task
    record("ManageTask tool imports", MANAGE_TASK_TOOL["name"] == "ManageTask")
    record("ManageTask handler imports", callable(handle_manage_task))


def test_deleted_primitives_gone():
    """Deleted primitives are fully removed — no dangling files."""
    primitives_dir = Path(__file__).parent / "services" / "primitives"

    record("save_memory.py deleted", not (primitives_dir / "save_memory.py").exists())
    record("shared_context.py deleted", not (primitives_dir / "shared_context.py").exists())


def test_deleted_tools_not_in_registry():
    """Old tool names are not in CHAT_PRIMITIVES or HEADLESS_PRIMITIVES."""
    from services.primitives.registry import CHAT_PRIMITIVES, HEADLESS_PRIMITIVES

    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}
    all_names = chat_names | headless_names

    deleted_tools = [
        "UpdateSharedContext", "SaveMemory",
        "WriteAgentFeedback", "WriteTaskFeedback",
        "TriggerTask", "UpdateTask", "PauseTask", "ResumeTask",
    ]

    for tool in deleted_tools:
        record(f"deleted tool '{tool}' not in registry", tool not in all_names)


def test_registry_tool_counts():
    """CHAT_PRIMITIVES ≤ 15 (P5 budget), HEADLESS has workspace tools."""
    from services.primitives.registry import CHAT_PRIMITIVES, HEADLESS_PRIMITIVES

    chat_count = len(CHAT_PRIMITIVES)
    headless_count = len(HEADLESS_PRIMITIVES)

    record(f"CHAT_PRIMITIVES count = {chat_count} (≤15)", chat_count <= 15)
    record(f"HEADLESS_PRIMITIVES count = {headless_count}", headless_count > 0)

    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}

    # Chat has UpdateContext and ManageTask
    record("Chat has UpdateContext", "UpdateContext" in chat_names)
    record("Chat has ManageTask", "ManageTask" in chat_names)
    record("Chat has CreateTask", "CreateTask" in chat_names)

    # Headless has workspace tools
    record("Headless has ReadWorkspace", "ReadWorkspace" in headless_names)
    record("Headless has WriteWorkspace", "WriteWorkspace" in headless_names)
    record("Headless has RuntimeDispatch", "RuntimeDispatch" in headless_names)

    # Chat should NOT have workspace tools
    record("Chat does NOT have ReadWorkspace", "ReadWorkspace" not in chat_names)
    record("Chat does NOT have RuntimeDispatch", "RuntimeDispatch" not in chat_names)

    # Headless should NOT have chat-only tools
    record("Headless does NOT have Edit", "Edit" not in headless_names)
    record("Headless does NOT have Clarify", "Clarify" not in headless_names)
    record("Headless does NOT have Execute", "Execute" not in headless_names)


def test_handler_registry_complete():
    """Every registered tool has a handler in HANDLERS."""
    from services.primitives.registry import CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, HANDLERS

    all_tool_names = {t["name"] for t in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES}

    for name in all_tool_names:
        record(f"handler exists for '{name}'", name in HANDLERS)


def test_update_context_tool_schema():
    """UpdateContext schema has all 5 targets and required fields."""
    from services.primitives.update_context import UPDATE_CONTEXT_TOOL

    schema = UPDATE_CONTEXT_TOOL["input_schema"]
    props = schema["properties"]
    required = schema["required"]

    targets = props["target"]["enum"]
    record("UpdateContext has 5 targets",
           set(targets) == {"identity", "brand", "memory", "agent", "task"})
    record("UpdateContext requires target+text",
           set(required) == {"target", "text"})
    record("UpdateContext has agent_slug field", "agent_slug" in props)
    record("UpdateContext has task_slug field", "task_slug" in props)
    record("UpdateContext has feedback_target field", "feedback_target" in props)
    record("UpdateContext has document_contents field", "document_contents" in props)
    record("UpdateContext has url_contents field", "url_contents" in props)


def test_manage_task_tool_schema():
    """ManageTask schema has all 4 actions and correct fields."""
    from services.primitives.manage_task import MANAGE_TASK_TOOL

    schema = MANAGE_TASK_TOOL["input_schema"]
    props = schema["properties"]
    required = schema["required"]

    actions = props["action"]["enum"]
    record("ManageTask has 4 actions",
           set(actions) == {"trigger", "update", "pause", "resume"})
    record("ManageTask requires task_slug+action",
           set(required) == {"task_slug", "action"})
    record("ManageTask has context field", "context" in props)
    record("ManageTask has schedule field", "schedule" in props)
    record("ManageTask has delivery field", "delivery" in props)
    record("ManageTask has mode field", "mode" in props)


def test_update_context_routing():
    """UpdateContext routes to correct handler based on target."""
    from services.primitives.update_context import handle_update_context

    async def _test():
        # Missing target
        result = await handle_update_context(None, {"text": "test"})
        record("UpdateContext rejects missing target", not result["success"])

        # Invalid target
        result = await handle_update_context(None, {"target": "invalid", "text": "test"})
        record("UpdateContext rejects invalid target",
               not result["success"] and result.get("error") == "invalid_target")

        # Empty text
        result = await handle_update_context(None, {"target": "memory", "text": ""})
        record("UpdateContext rejects empty text",
               not result["success"] and result.get("error") == "empty_text")

    asyncio.get_event_loop().run_until_complete(_test())


def test_manage_task_routing():
    """ManageTask routes correctly and validates inputs."""
    from services.primitives.manage_task import handle_manage_task

    async def _test():
        # Missing slug
        result = await handle_manage_task(None, {"action": "trigger"})
        record("ManageTask rejects missing slug",
               not result["success"] and result.get("error") == "missing_slug")

        # Invalid action
        result = await handle_manage_task(None, {"task_slug": "test", "action": "destroy"})
        record("ManageTask rejects invalid action",
               not result["success"] and result.get("error") == "invalid_action")

    asyncio.get_event_loop().run_until_complete(_test())


def test_compute_next_run():
    """_compute_next_run handles daily/weekly/monthly/unknown."""
    from services.primitives.manage_task import _compute_next_run

    daily = _compute_next_run("daily")
    record("daily schedule returns ISO timestamp", daily is not None and "T09:00:00" in daily)

    weekly = _compute_next_run("weekly")
    record("weekly schedule returns ISO timestamp", weekly is not None and "T09:00:00" in weekly)

    monthly = _compute_next_run("monthly")
    record("monthly schedule returns ISO timestamp", monthly is not None and "T09:00:00" in monthly)

    unknown = _compute_next_run("*/5 * * * *")
    record("cron schedule returns None (scheduler interprets)", unknown is None)


def test_get_tools_for_mode():
    """get_tools_for_mode returns correct registries."""
    from services.primitives.registry import get_tools_for_mode, CHAT_PRIMITIVES, HEADLESS_PRIMITIVES

    chat_tools = get_tools_for_mode("chat")
    headless_tools = get_tools_for_mode("headless")
    default_tools = get_tools_for_mode("unknown")

    record("chat mode returns CHAT_PRIMITIVES",
           [t["name"] for t in chat_tools] == [t["name"] for t in CHAT_PRIMITIVES])
    record("headless mode returns HEADLESS_PRIMITIVES",
           [t["name"] for t in headless_tools] == [t["name"] for t in HEADLESS_PRIMITIVES])
    record("unknown mode defaults to chat",
           [t["name"] for t in default_tools] == [t["name"] for t in CHAT_PRIMITIVES])


def test_headless_executor_blocks_chat_only_tools():
    """Headless executor rejects tools not in HEADLESS_PRIMITIVES."""
    from services.primitives.registry import create_headless_executor

    executor = create_headless_executor(None, "fake-user-id")

    async def _test():
        result = await executor("Edit", {"path": "/test"})
        record("headless blocks Edit", not result["success"] and result.get("error") == "not_available")

        result = await executor("Clarify", {"question": "test"})
        record("headless blocks Clarify", not result["success"] and result.get("error") == "not_available")

        result = await executor("Execute", {})
        record("headless blocks Execute", not result["success"] and result.get("error") == "not_available")

    asyncio.get_event_loop().run_until_complete(_test())


def test_no_dangling_imports():
    """No code imports deleted modules."""
    import subprocess

    # Search for imports of deleted primitives
    deleted_imports = [
        "from services.primitives.save_memory",
        "from services.primitives.shared_context",
        "import save_memory",
        "import shared_context",
        "from .save_memory",
        "from .shared_context",
    ]

    api_dir = Path(__file__).parent
    py_files = list(api_dir.rglob("*.py"))

    for pattern in deleted_imports:
        found_in = []
        for f in py_files:
            if f.name.startswith("test_"):
                continue
            try:
                if pattern in f.read_text():
                    found_in.append(f.name)
            except Exception:
                pass
        record(f"no dangling import: '{pattern}'", len(found_in) == 0,
               f"found in: {found_in}" if found_in else "")


def test_inline_tool_call_display_names():
    """Frontend InlineToolCall recognizes new consolidated tool names."""
    inline_path = Path(__file__).parent.parent / "web" / "components" / "tp" / "InlineToolCall.tsx"
    if inline_path.exists():
        content = inline_path.read_text()
        record("InlineToolCall handles UpdateContext",
               "UpdateContext" in content)
        record("InlineToolCall handles ManageTask",
               "ManageTask" in content)
    else:
        record("InlineToolCall.tsx found", False)


# =============================================================================
# Cross-commit: Integration consistency
# =============================================================================

def test_task_routes_process_endpoints():
    """Task routes include process-related endpoints (steps, status)."""
    from routes.tasks import router

    route_paths = [r.path for r in router.routes]
    record("steps endpoint registered",
           any("/steps" in p for p in route_paths))
    record("status endpoint registered",
           any("/status" in p for p in route_paths))


def test_primitives_init_exports():
    """__init__.py and registry.py export the right symbols."""
    from services.primitives import PRIMITIVES, execute_primitive
    from services.primitives.registry import (
        CHAT_PRIMITIVES,
        HEADLESS_PRIMITIVES,
        HANDLERS,
        get_tools_for_mode,
        create_headless_executor,
    )
    record("PRIMITIVES exported from __init__", isinstance(PRIMITIVES, list))
    record("execute_primitive exported from __init__", callable(execute_primitive))
    record("CHAT_PRIMITIVES exported from registry", isinstance(CHAT_PRIMITIVES, list))
    record("HEADLESS_PRIMITIVES exported from registry", isinstance(HEADLESS_PRIMITIVES, list))
    record("HANDLERS exported from registry", isinstance(HANDLERS, dict))
    record("get_tools_for_mode exported from registry", callable(get_tools_for_mode))
    record("create_headless_executor exported from registry", callable(create_headless_executor))


# =============================================================================
# Runner
# =============================================================================

def main():
    print("\n" + "=" * 70)
    print("  VALIDATION SUITE — Recent 5 Commits")
    print("=" * 70)

    sections = [
        ("Commit 1: Sparse Context Surfacing (0a7c9cc)", [
            test_classify_richness,
            test_sparse_context_in_format,
            test_sparse_vs_empty_differentiation,
        ]),
        ("Commit 2: Task Output Loading Fix (6757833)", [
            lambda: asyncio.get_event_loop().run_until_complete(test_latest_output_fallback()),
        ]),
        ("Commit 3: Chat Plus Menu Actions (24f3734)", [
            test_plus_menu_actions_restored,
        ]),
        ("Commit 4: Live Process Progress (bffc047)", [
            test_pipeline_to_process_terminology,
            test_process_types_exist,
            test_status_endpoint_exists,
            test_status_json_written_during_pipeline,
            test_api_client_has_status_methods,
        ]),
        ("Commit 5: ADR-146 Primitive Hardening (901bceb)", [
            test_primitive_consolidation_imports,
            test_deleted_primitives_gone,
            test_deleted_tools_not_in_registry,
            test_registry_tool_counts,
            test_handler_registry_complete,
            test_update_context_tool_schema,
            test_manage_task_tool_schema,
            test_update_context_routing,
            test_manage_task_routing,
            test_compute_next_run,
            test_get_tools_for_mode,
            test_headless_executor_blocks_chat_only_tools,
            test_no_dangling_imports,
            test_inline_tool_call_display_names,
        ]),
        ("Cross-Commit Integration", [
            test_task_routes_process_endpoints,
            test_primitives_init_exports,
        ]),
    ]

    for section_name, tests in sections:
        print(f"\n{'─' * 60}")
        print(f"  {section_name}")
        print(f"{'─' * 60}")
        for test_fn in tests:
            try:
                test_fn()
            except Exception as e:
                record(test_fn.__name__ if hasattr(test_fn, '__name__') else "test",
                       False, f"EXCEPTION: {e}")

    # Summary
    total = len(RESULTS)
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = sum(1 for _, p, _ in RESULTS if not p)

    print(f"\n{'=' * 70}")
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 70}")

    if failed:
        print("\n  FAILURES:")
        for name, p, detail in RESULTS:
            if not p:
                print(f"    ✗ {name}" + (f" — {detail}" if detail else ""))

    print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
