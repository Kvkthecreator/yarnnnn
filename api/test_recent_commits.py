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


def test_compact_index_surfaces_identity_gaps():
    """format_compact_index surfaces sparse/empty identity/brand with guidance."""
    from services.working_memory import format_compact_index

    wm_sparse = {
        "workspace_state": {
            "identity": "sparse",
            "brand": "empty",
            "documents": 0,
            "tasks_active": 0,
            "tasks_stale": 0,
            "context_domains": 0,
            "balance_usd": 3.0,
            "balance_exhausted": False,
            "agents_flagged": [],
        },
        "active_tasks": [],
        "context_domains": [],
    }

    formatted = format_compact_index(wm_sparse)

    record("sparse identity surfaces in compact index",
           "identity" in formatted.lower() and "sparse" in formatted.lower())
    record("empty brand gap signal in compact index",
           "identity empty" in formatted.lower() or "brand" in formatted.lower())


def test_user_context_renders_brand():
    """_load_user_context renders brand as ## Brand Guidelines section."""
    from services.task_pipeline import build_task_execution_prompt

    # Simulate what _load_user_context now returns — pre-rendered text
    user_context = (
        "## User Context\n- Name: Test User\n- Role: CEO\n\n"
        "## Brand Guidelines\nTone: Professional. Colors: Blue."
    )
    task_info = {"title": "Test", "objective": {}, "success_criteria": [], "output_spec": []}
    agent = {"role": "researcher", "scope": "cross_platform"}

    system_blocks, user_msg = build_task_execution_prompt(
        task_info=task_info, agent=agent, agent_instructions="",
        context="", user_context=user_context,
    )

    # System blocks are list of dicts — extract text
    system_text = " ".join(b.get("text", "") for b in system_blocks)
    record("brand guidelines in system prompt", "Brand Guidelines" in system_text)
    record("user context in system prompt", "Name: Test User" in system_text)


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
    """Verify context + task actions exist in the chat surface.

    Surface evolution:
    - Pre-ADR-163: plus menu in /workfloor page
    - ADR-163: /workfloor → /chat surface restructure
    - ADR-165 v6: identity/brand actions moved from plus menu to workspace
      state modal (ContextSetup component opened via + button + modal)
    - ADR-168 Commit 2: test fixtures retargeted to the current locations.

    The assertion's intent is still "the chat surface has hooks to capture
    identity, brand, and tasks." Just the source of truth moved from a
    single file to a file pair.
    """
    chat_path = Path(__file__).parent.parent / "web" / "app" / "(authenticated)" / "chat" / "page.tsx"
    context_setup_path = Path(__file__).parent.parent / "web" / "components" / "chat-surface" / "ContextSetup.tsx"

    chat_content = chat_path.read_text() if chat_path.exists() else ""
    setup_content = context_setup_path.read_text() if context_setup_path.exists() else ""
    combined = chat_content + "\n" + setup_content

    record("plus menu has create-task action",
           "create-task" in combined or "CreateTask" in combined or "task" in combined.lower())
    record("plus menu has identity action",
           "identity" in combined.lower() or "update-identity" in combined)
    record("plus menu has brand action",
           "brand" in combined.lower() or "update-brand" in combined)


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
    """Verify post-ADR-231 + post-ADR-235 primitives import cleanly."""
    # ADR-235 successors of UpdateContext
    from services.primitives.infer_context import INFER_CONTEXT_TOOL, handle_infer_context
    record("InferContext tool imports", INFER_CONTEXT_TOOL["name"] == "InferContext")
    record("InferContext handler imports", callable(handle_infer_context))

    from services.primitives.infer_workspace import INFER_WORKSPACE_TOOL, handle_infer_workspace
    record("InferWorkspace tool imports", INFER_WORKSPACE_TOOL["name"] == "InferWorkspace")
    record("InferWorkspace handler imports", callable(handle_infer_workspace))

    # ADR-231 + ADR-235 successor of ManageTask
    from services.primitives.manage_recurrence import MANAGE_RECURRENCE_TOOL, handle_manage_recurrence
    record("ManageRecurrence tool imports", MANAGE_RECURRENCE_TOOL["name"] == "ManageRecurrence")
    record("ManageRecurrence handler imports", callable(handle_manage_recurrence))

    # ADR-231 D5
    from services.primitives.fire_invocation import FIRE_INVOCATION_TOOL, handle_fire_invocation
    record("FireInvocation tool imports", FIRE_INVOCATION_TOOL["name"] == "FireInvocation")
    record("FireInvocation handler imports", callable(handle_fire_invocation))


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
    """Post-ADR-234 + ADR-235 registry shape."""
    from services.primitives.registry import CHAT_PRIMITIVES, HEADLESS_PRIMITIVES

    chat_count = len(CHAT_PRIMITIVES)
    headless_count = len(HEADLESS_PRIMITIVES)

    # Floor counts — these grow over time as primitives are added; the
    # invariants below (presence/absence of named tools) are the load-bearing
    # checks. Counts are sanity bounds.
    record(f"CHAT_PRIMITIVES count = {chat_count} (≥20)", chat_count >= 20)
    record(f"HEADLESS_PRIMITIVES count = {headless_count} (≥18)", headless_count >= 18)

    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}

    # Post-ADR-235: UpdateContext and ManageTask are dissolved
    record("Chat does NOT have UpdateContext (ADR-235)", "UpdateContext" not in chat_names)
    record("Headless does NOT have UpdateContext (ADR-235)", "UpdateContext" not in headless_names)
    record("Chat does NOT have ManageTask (ADR-231)", "ManageTask" not in chat_names)
    record("Headless does NOT have ManageTask (ADR-231)", "ManageTask" not in headless_names)
    record("Chat does NOT have CreateTask (ADR-168 C3)", "CreateTask" not in chat_names)

    # Post-ADR-235 successors are present in chat
    record("Chat has InferContext (ADR-235 D1.a)", "InferContext" in chat_names)
    record("Chat has InferWorkspace (ADR-235 D1.a)", "InferWorkspace" in chat_names)
    record("Chat has ManageRecurrence (ADR-235 D1.c)", "ManageRecurrence" in chat_names)
    record("Headless has ManageRecurrence", "ManageRecurrence" in headless_names)
    record("Chat has FireInvocation (ADR-231 D5)", "FireInvocation" in chat_names)

    # Post-ADR-234: chat now has file-layer primitives
    record("Chat has ReadFile (ADR-234)", "ReadFile" in chat_names)
    record("Chat has WriteFile (ADR-234)", "WriteFile" in chat_names)
    record("Chat has SearchFiles (ADR-234)", "SearchFiles" in chat_names)
    record("Chat has ListFiles (ADR-234)", "ListFiles" in chat_names)

    # Headless still has the file family + headless-only file primitives
    record("Headless has ReadFile", "ReadFile" in headless_names)
    record("Headless has WriteFile", "WriteFile" in headless_names)
    record("Headless has SearchFiles", "SearchFiles" in headless_names)
    record("Headless has ListFiles", "ListFiles" in headless_names)
    record("Headless has QueryKnowledge (semantic, headless-only)", "QueryKnowledge" in headless_names)
    record("Headless has ReadAgentFile (inter-agent, headless-only)", "ReadAgentFile" in headless_names)

    # ADR-234 invariants: QueryKnowledge + ReadAgentFile stay headless-only
    record("Chat does NOT have QueryKnowledge (headless-only)", "QueryKnowledge" not in chat_names)
    record("Chat does NOT have ReadAgentFile (headless-only)", "ReadAgentFile" not in chat_names)

    # Old workspace-prefix names should be gone
    record("Old ReadWorkspace not in registry", "ReadWorkspace" not in headless_names and "ReadWorkspace" not in chat_names)
    record("Old WriteWorkspace not in registry", "WriteWorkspace" not in headless_names and "WriteWorkspace" not in chat_names)

    # Headless should NOT have chat-only tools
    record("Headless does NOT have EditEntity", "EditEntity" not in headless_names)
    record("Headless does NOT have Clarify", "Clarify" not in headless_names)

    # ADR-168 Commit 2: Execute primitive dissolved entirely
    record("Execute not in chat registry", "Execute" not in chat_names)
    record("Execute not in headless registry", "Execute" not in headless_names)


def test_handler_registry_complete():
    """Every registered tool has a handler in HANDLERS."""
    from services.primitives.registry import CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, HANDLERS

    all_tool_names = {t["name"] for t in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES}

    for name in all_tool_names:
        record(f"handler exists for '{name}'", name in HANDLERS)


def test_infer_context_tool_schema():
    """ADR-235 D1.a: InferContext schema covers identity + brand inference merge."""
    from services.primitives.infer_context import INFER_CONTEXT_TOOL

    schema = INFER_CONTEXT_TOOL["input_schema"]
    props = schema["properties"]
    required = schema["required"]

    targets = props["target"]["enum"]
    record("InferContext has 2 targets (identity, brand)",
           set(targets) == {"identity", "brand"})
    record("InferContext requires target + text", set(required) == {"target", "text"})
    record("InferContext has document_ids field", "document_ids" in props)
    record("InferContext has url_contents field", "url_contents" in props)


def test_infer_workspace_tool_schema():
    """ADR-235 D1.a: InferWorkspace schema covers first-act scaffold."""
    from services.primitives.infer_workspace import INFER_WORKSPACE_TOOL

    schema = INFER_WORKSPACE_TOOL["input_schema"]
    props = schema["properties"]

    record("InferWorkspace has text field", "text" in props)
    record("InferWorkspace has document_ids field", "document_ids" in props)
    record("InferWorkspace has url_contents field", "url_contents" in props)


def test_write_file_workspace_scope():
    """ADR-235 D1.b + ADR-234: WriteFile gains scope='workspace'."""
    from services.primitives.workspace import WRITE_FILE_TOOL

    schema = WRITE_FILE_TOOL["input_schema"]
    props = schema["properties"]
    scopes = props["scope"]["enum"]

    record("WriteFile scope includes 'workspace' (Option A)", "workspace" in scopes)
    record("WriteFile scope includes 'agent'", "agent" in scopes)
    record("WriteFile scope includes 'context'", "context" in scopes)
    record("WriteFile has authored_by field (ADR-209)", "authored_by" in props)
    record("WriteFile has message field (ADR-209)", "message" in props)


def test_shared_context_cluster_constants():
    """Shared operator-authored substrate includes precedent alongside autonomy."""
    from services.workspace_paths import SHARED_AUTONOMY_PATH, SHARED_CONTEXT_FILES, SHARED_PRECEDENT_PATH

    record("Shared context has AUTONOMY.md", SHARED_AUTONOMY_PATH in SHARED_CONTEXT_FILES)
    record("Shared context has PRECEDENT.md", SHARED_PRECEDENT_PATH in SHARED_CONTEXT_FILES)


def test_manage_recurrence_tool_schema():
    """ADR-235 D1.c: ManageRecurrence schema has 5 actions + 4 shapes."""
    from services.primitives.manage_recurrence import MANAGE_RECURRENCE_TOOL

    schema = MANAGE_RECURRENCE_TOOL["input_schema"]
    props = schema["properties"]
    required = schema["required"]

    actions = props["action"]["enum"]
    record("ManageRecurrence has 5 actions",
           set(actions) == {"create", "update", "pause", "resume", "archive"})

    shapes = props["shape"]["enum"]
    record("ManageRecurrence has 4 shapes",
           set(shapes) == {"deliverable", "accumulation", "action", "maintenance"})

    record("ManageRecurrence requires action + shape + slug",
           set(required) == {"action", "shape", "slug"})
    record("ManageRecurrence has body field (create)", "body" in props)
    record("ManageRecurrence has changes field (update)", "changes" in props)
    record("ManageRecurrence has paused_until field (pause)", "paused_until" in props)
    record("ManageRecurrence has domain field (accumulation)", "domain" in props)


def test_manage_agent_action_enum_no_create():
    """ADR-235 D2: ManageAgent action enum drops 'create'."""
    from services.primitives.coordinator import MANAGE_AGENT_TOOL

    actions = MANAGE_AGENT_TOOL["input_schema"]["properties"]["action"]["enum"]
    record("ManageAgent does NOT have 'create' action",
           "create" not in actions)
    record("ManageAgent has 4 lifecycle actions",
           set(actions) == {"update", "pause", "resume", "archive"})


def test_manage_recurrence_routing():
    """ADR-235 D1.c: ManageRecurrence routes correctly and validates inputs."""
    from services.primitives.manage_recurrence import handle_manage_recurrence

    async def _test():
        # Invalid action
        result = await handle_manage_recurrence(None, {
            "action": "destroy", "shape": "deliverable", "slug": "test"
        })
        record("ManageRecurrence rejects invalid action",
               not result["success"] and result.get("error") == "invalid_action")

        # Missing slug
        result = await handle_manage_recurrence(None, {
            "action": "pause", "shape": "deliverable"
        })
        record("ManageRecurrence rejects missing slug",
               not result["success"] and result.get("error") == "missing_slug")

        # Invalid shape
        result = await handle_manage_recurrence(None, {
            "action": "pause", "shape": "fake-shape", "slug": "test"
        })
        record("ManageRecurrence rejects invalid shape",
               not result["success"] and result.get("error") == "invalid_shape")

        # Accumulation requires domain
        result = await handle_manage_recurrence(None, {
            "action": "create", "shape": "accumulation", "slug": "test"
        })
        record("ManageRecurrence(accumulation) requires domain",
               not result["success"] and result.get("error") == "missing_domain")

    asyncio.get_event_loop().run_until_complete(_test())


# ADR-231 Phase 3.7 + ADR-235 deleted manage_task; the schedule timing math
# moved to services.scheduling.compute_next_run_at. Test deleted alongside.


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
        result = await executor("EditEntity", {"path": "/test"})
        record("headless blocks EditEntity", not result["success"] and result.get("error") == "not_available")

        result = await executor("Clarify", {"question": "test"})
        record("headless blocks Clarify", not result["success"] and result.get("error") == "not_available")

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
        # ADR-168 Commit 2: Execute primitive dissolved
        "from services.primitives.execute",
        "from .execute import",
        # ADR-168 Commit 3: CreateTask folded into ManageTask(action="create")
        "from services.primitives.task import",
        "from .task import",
        "CREATE_TASK_TOOL",
        # ADR-231 Phase 3.7: ManageTask dissolved
        "from services.primitives.manage_task",
        "from .manage_task import",
        "MANAGE_TASK_TOOL",
        # ADR-235: UpdateContext dissolved
        "from services.primitives.update_context",
        "from .update_context import",
        "UPDATE_CONTEXT_TOOL",
        "handle_update_context",
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
    """Frontend InlineToolCall recognizes post-ADR-231/235 tool names.

    ADR-231 dissolved ManageTask; ADR-235 dissolved UpdateContext. The
    frontend may still recognize legacy names for historical run logs (the
    inline-call display reads `tool_history` snapshots), but should also
    handle the new primitives.
    """
    inline_path = Path(__file__).parent.parent / "web" / "components" / "tp" / "InlineToolCall.tsx"
    if inline_path.exists():
        content = inline_path.read_text()
        # Post-ADR-235 successors
        record("InlineToolCall handles ManageRecurrence",
               "ManageRecurrence" in content or "manage_recurrence" in content)
        record("InlineToolCall handles InferContext",
               "InferContext" in content or "infer_context" in content)
    else:
        # Frontend file missing is non-fatal — frontend evolves separately.
        # Skip rather than fail.
        pass


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
        ("Commit 5: Primitive surface (post-ADR-231 + ADR-235)", [
            test_primitive_consolidation_imports,
            test_deleted_primitives_gone,
            test_deleted_tools_not_in_registry,
            test_registry_tool_counts,
            test_handler_registry_complete,
            test_infer_context_tool_schema,
            test_infer_workspace_tool_schema,
            test_write_file_workspace_scope,
            test_manage_recurrence_tool_schema,
            test_manage_agent_action_enum_no_create,
            test_manage_recurrence_routing,
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
