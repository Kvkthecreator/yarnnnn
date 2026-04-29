"""
Primitive Registry — ADR-146: Primitive Hardening

Central registry for all primitives and their handlers.
Two explicit mode registries (P4): CHAT_PRIMITIVES and HEADLESS_PRIMITIVES.

ADR-050: Platform tools are routed via handle_platform_tool.
ADR-080: Mode-gated primitives — chat vs. headless.
ADR-146: Consolidated from 27 → 19 primitives.
  - UpdateContext replaces UpdateSharedContext, SaveMemory, WriteAgentFeedback, WriteTaskFeedback
  - ManageTask replaces TriggerTask, UpdateTask, PauseTask, ResumeTask
"""

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Imports — only live primitives
# ---------------------------------------------------------------------------
from .read import LOOKUP_ENTITY_TOOL, handle_lookup_entity
from .edit import EDIT_ENTITY_TOOL, handle_edit_entity
from .search import SEARCH_ENTITIES_TOOL, handle_search_entities
from .list import LIST_ENTITIES_TOOL, handle_list_entities
from .web_search import WEB_SEARCH_PRIMITIVE, handle_web_search
from .system_state import GET_SYSTEM_STATE_TOOL, handle_get_system_state
from .coordinator import MANAGE_AGENT_TOOL, handle_manage_agent
# ADR-231 Phase 3.7: ManageTask DELETED. Lifecycle dissolves into
# UpdateContext(target='recurrence', ...) and FireInvocation per D5.
from .fire_invocation import FIRE_INVOCATION_TOOL, handle_fire_invocation
from .update_context import UPDATE_CONTEXT_TOOL, handle_update_context
from .scaffold import MANAGE_DOMAINS_TOOL, handle_manage_domains
from .workspace import (
    READ_FILE_TOOL, handle_read_file,
    WRITE_FILE_TOOL, handle_write_file,
    SEARCH_FILES_TOOL, handle_search_files,
    QUERY_KNOWLEDGE_TOOL, handle_query_knowledge,
    LIST_FILES_TOOL, handle_list_files,
    DISCOVER_AGENTS_TOOL, handle_discover_agents,
    READ_AGENT_FILE_TOOL, handle_read_agent_file,
)
# ADR-209 Phase 3: revision-aware read primitives (Authored Substrate).
from .revisions import (
    LIST_REVISIONS_TOOL, handle_list_revisions,
    READ_REVISION_TOOL, handle_read_revision,
    DIFF_REVISIONS_TOOL, handle_diff_revisions,
)
from .runtime_dispatch import RUNTIME_DISPATCH_TOOL, handle_runtime_dispatch
from .repurpose import REPURPOSE_OUTPUT_TOOL, handle_repurpose_output
from .propose_action import (
    PROPOSE_ACTION_TOOL, handle_propose_action,
    EXECUTE_PROPOSAL_TOOL, handle_execute_proposal,
    REJECT_PROPOSAL_TOOL, handle_reject_proposal,
)
from services.platform_tools import (
    is_platform_tool, handle_platform_tool, get_platform_tools_for_agent,
)

# ---------------------------------------------------------------------------
# Deleted imports (ADR-146 — absorbed into UpdateContext / ManageTask):
# - save_memory.py → UpdateContext(target="memory")
# - shared_context.py → UpdateContext(target="identity"|"brand")
# - workspace.py: WRITE_AGENT_FEEDBACK_TOOL → UpdateContext(target="agent")
# - workspace.py: WRITE_TASK_FEEDBACK_TOOL → UpdateContext(target="task")
# - task.py: TRIGGER_TASK_TOOL → ManageTask(action="trigger")
# - task.py: UPDATE_TASK_TOOL → ManageTask(action="update")
# - task.py: PAUSE_TASK_TOOL → ManageTask(action="pause")
# - task.py: RESUME_TASK_TOOL → ManageTask(action="resume")
#
# Deleted imports (ADR-168 Commit 2 — finish ADR-146 Phase 3):
# - execute.py → Execute primitive dissolved entirely
#     agent.generate    → ManageTask(task_slug=..., action="trigger")
#     agent.acknowledge → UpdateContext(target="agent", agent_slug=..., text=...)
#     platform.publish  → delivery is a task property (ManageTask update)
#     agent.schedule    → ManageTask(task_slug=..., action="update", schedule=...)
#
# Deleted imports (ADR-168 Commit 3 — CreateTask folded into ManageTask):
# - task.py → CreateTask primitive dissolved entirely
#     CreateTask(title=..., type_key=..., ...) →
#       ManageTask(action="create", title=..., type_key=..., ...)
#   Symmetric with ManageAgent which already covers agent creation.
# ---------------------------------------------------------------------------


# =============================================================================
# Inline tool definitions (small enough to live here)
# =============================================================================

CLARIFY_TOOL = {
    "name": "Clarify",
    "description": """Ask the user for input before proceeding.

Use when you need more information or want to offer choices.
Appears as a focused prompt.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask"
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices"
            }
        },
        "required": ["question"]
    }
}


async def handle_clarify(auth: Any, input: dict) -> dict:
    """Handle Clarify primitive."""
    question = input.get("question", "")
    options = input.get("options", [])
    return {
        "success": True,
        "question": question,
        "options": options,
        "ui_action": {
            "type": "CLARIFY",
            "data": {"question": question, "options": options},
        },
    }


LIST_INTEGRATIONS_TOOL = {
    "name": "list_integrations",
    "description": """List the user's connected platform integrations and their metadata.

Call this first when about to use a platform tool, to get:
- Which platforms are active (slack, notion, github, commerce, trading)
- Slack: authed_user_id — use as channel_id when sending DMs to self
- Trading: provider, paper mode, account_number
- Notion: designated_page_id — use as page_id when writing to user's YARNNN page

AGENTIC BEHAVIOR: Don't ask "are you connected to Slack?" — call list_integrations and find out.
If not connected, suggest connecting in Settings.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


async def handle_list_integrations(auth: Any, input: dict) -> dict:
    """List user's connected platform integrations."""
    result = auth.client.table("platform_connections")\
        .select("id, platform, status, metadata, created_at, updated_at")\
        .eq("user_id", auth.user_id)\
        .execute()

    integrations = result.data or []
    items = []
    for i in integrations:
        metadata = i.get("metadata") or {}
        item = {
            "platform": i["platform"],
            "status": i["status"],
            "connected_at": i["created_at"],
            "last_updated": i["updated_at"],
            "workspace_name": metadata.get("team_name") or metadata.get("workspace_name"),
            "email": metadata.get("email"),
        }
        if i["platform"] == "slack" and metadata.get("authed_user_id"):
            item["authed_user_id"] = metadata["authed_user_id"]
        if i["platform"] == "notion" and metadata.get("designated_page_id"):
            item["designated_page_id"] = metadata["designated_page_id"]
        if i["platform"] == "commerce":
            item["provider"] = metadata.get("provider", "")
            item["store_name"] = metadata.get("store_name", "")
        if i["platform"] == "trading":
            item["provider"] = metadata.get("provider", "")
            item["paper"] = metadata.get("paper", True)
            item["account_number"] = metadata.get("account_number", "")
        items.append(item)

    return {
        "success": True,
        "integrations": items,
        "count": len(items),
    }


# =============================================================================
# ADR-146: Explicit Mode Registries (P4)
# =============================================================================

# Chat mode: TP in user-facing conversation. ≤15 tools (P5 budget).
CHAT_PRIMITIVES = [
    # Entity layer (4) + Introspection (1)
    LOOKUP_ENTITY_TOOL,
    LIST_ENTITIES_TOOL,
    SEARCH_ENTITIES_TOOL,
    EDIT_ENTITY_TOOL,
    GET_SYSTEM_STATE_TOOL,
    # External (ADR-153: RefreshPlatformContent removed)
    WEB_SEARCH_PRIMITIVE,
    LIST_INTEGRATIONS_TOOL,
    # Context mutations — unified (1, was 4)
    UPDATE_CONTEXT_TOOL,
    # ADR-155: Domain scaffolding (TP-driven)
    MANAGE_DOMAINS_TOOL,
    # Agent lifecycle (1, was 2 pre-ADR-231)
    MANAGE_AGENT_TOOL,
    # ADR-231 D5: FireInvocation — manual fire of a recurrence declaration.
    # Replaces ManageTask(action="trigger"); other lifecycle actions
    # (create/update/pause/resume/archive) flow through UpdateContext
    # (target='recurrence'). ManageTask is DELETED in Phase 3.7.
    FIRE_INVOCATION_TOOL,
    # Repurpose (ADR-148 Phase 4)
    REPURPOSE_OUTPUT_TOOL,
    # Asset rendering (1) — Gemini image gen, charts, mermaid diagrams
    RUNTIME_DISPATCH_TOOL,
    # Approval loop (3) — ADR-193
    PROPOSE_ACTION_TOOL,
    EXECUTE_PROPOSAL_TOOL,
    REJECT_PROPOSAL_TOOL,
    # Interaction (1)
    CLARIFY_TOOL,
    # Authored Substrate — revision-aware reads (ADR-209 Phase 3)
    LIST_REVISIONS_TOOL,
    READ_REVISION_TOOL,
    DIFF_REVISIONS_TOOL,
]  # 21 tools — ADR-231 D5 added FireInvocation

# Headless mode: background agent execution.
# Base registry only. Provider-native platform tools are added dynamically per
# agent capability bundle via `get_headless_tools_for_agent()`.
HEADLESS_PRIMITIVES = [
    # Entity layer (3) + Introspection (1)
    LOOKUP_ENTITY_TOOL,
    LIST_ENTITIES_TOOL,
    SEARCH_ENTITIES_TOOL,
    GET_SYSTEM_STATE_TOOL,
    # External (ADR-153: RefreshPlatformContent removed)
    WEB_SEARCH_PRIMITIVE,
    # File layer (5)
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    SEARCH_FILES_TOOL,
    QUERY_KNOWLEDGE_TOOL,
    LIST_FILES_TOOL,
    # Inter-agent (2)
    DISCOVER_AGENTS_TOOL,
    READ_AGENT_FILE_TOOL,
    # Lifecycle (1, was 2 pre-ADR-231) + Domain management (1)
    MANAGE_AGENT_TOOL,
    # ADR-231 D5: FireInvocation — recurrence-aware dispatch.
    FIRE_INVOCATION_TOOL,
    MANAGE_DOMAINS_TOOL,
    # Asset rendering — writes to task output folder when task_slug set on auth
    RUNTIME_DISPATCH_TOOL,
    # Approval loop (ADR-193) — headless agents must propose when action is
    # soft/irreversible; autonomous execution without approval is unsafe.
    PROPOSE_ACTION_TOOL,
    # Authored Substrate — revision-aware reads (ADR-209 Phase 3).
    # Agents can inspect prior revisions of their own memory, upstream
    # context domains, or delivered outputs to track their own drift and
    # reason about accumulated change. Chat parity.
    LIST_REVISIONS_TOOL,
    READ_REVISION_TOOL,
    DIFF_REVISIONS_TOOL,
]  # 21 tools — ADR-231 D5 added FireInvocation

# Combined list — for handler registration and backwards compatibility
PRIMITIVES = list({t["name"]: t for t in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES}.values())


# =============================================================================
# Handler mapping — all unique handlers
# =============================================================================

HANDLERS: dict[str, Callable] = {
    # Entity layer (ADR-168 Commit 4: renamed from Read/List/Search/Edit)
    "LookupEntity": handle_lookup_entity,
    "EditEntity": handle_edit_entity,
    "SearchEntities": handle_search_entities,
    "ListEntities": handle_list_entities,
    # "Execute": DELETED (ADR-168 Commit 2 — finish ADR-146 Phase 3)
    # "RefreshPlatformContent": DELETED (ADR-153)
    "WebSearch": handle_web_search,
    "GetSystemState": handle_get_system_state,
    "Clarify": handle_clarify,
    "list_integrations": handle_list_integrations,
    "ManageAgent": handle_manage_agent,
    # "CreateTask": DELETED (ADR-168 Commit 3 — folded into ManageTask action="create")
    # "ManageTask": DELETED (ADR-231 Phase 3.7 — replaced by UpdateContext(target='recurrence') + FireInvocation per D5)
    # ADR-231 D5: FireInvocation — recurrence-aware dispatch.
    "FireInvocation": handle_fire_invocation,
    "UpdateContext": handle_update_context,
    "ManageDomains": handle_manage_domains,
    # File layer (ADR-168 Commit 4: renamed from ReadWorkspace/WriteWorkspace/etc.)
    "ReadFile": handle_read_file,
    "WriteFile": handle_write_file,
    "SearchFiles": handle_search_files,
    "QueryKnowledge": handle_query_knowledge,
    "ListFiles": handle_list_files,
    "DiscoverAgents": handle_discover_agents,
    "ReadAgentFile": handle_read_agent_file,
    "RuntimeDispatch": handle_runtime_dispatch,
    "RepurposeOutput": handle_repurpose_output,
    # ADR-193: Approval loop
    "ProposeAction": handle_propose_action,
    "ExecuteProposal": handle_execute_proposal,
    "RejectProposal": handle_reject_proposal,
    # ADR-209 Phase 3: Authored Substrate revision-aware reads
    "ListRevisions": handle_list_revisions,
    "ReadRevision": handle_read_revision,
    "DiffRevisions": handle_diff_revisions,
}


# =============================================================================
# ADR-146: Mode-aware tool resolution (replaces PRIMITIVE_MODES dict)
# =============================================================================

# Derived from explicit registries — no separate PRIMITIVE_MODES dict to drift
_CHAT_TOOL_NAMES = {t["name"] for t in CHAT_PRIMITIVES}
_HEADLESS_TOOL_NAMES = {t["name"] for t in HEADLESS_PRIMITIVES}


async def execute_primitive(auth: Any, name: str, input: dict) -> dict:
    """
    Execute a primitive by name.

    ADR-050: Platform tools (platform_*) are routed to MCP Gateway.
    """
    if is_platform_tool(name):
        try:
            return await handle_platform_tool(auth, name, input)
        except Exception as e:
            return {
                "success": False,
                "error": "platform_tool_error",
                "message": str(e),
                "tool": name,
            }

    handler = HANDLERS.get(name)
    if not handler:
        return {
            "success": False,
            "error": "unknown_primitive",
            "message": f"Unknown primitive: {name}",
            "available": list(HANDLERS.keys()),
        }

    try:
        return await handler(auth, input)
    except Exception as e:
        return {
            "success": False,
            "error": "execution_error",
            "message": str(e),
            "primitive": name,
        }


def get_tools_for_mode(mode: str) -> list[dict]:
    """
    Get tool definitions for a specific mode.

    ADR-146: Returns from explicit registries, not filtered from a combined list.
    """
    if mode == "chat":
        return list(CHAT_PRIMITIVES)
    elif mode == "headless":
        return list(HEADLESS_PRIMITIVES)
    else:
        return list(CHAT_PRIMITIVES)  # Default to chat


class HeadlessAuth:
    """Minimal auth context for headless execution."""

    def __init__(
        self,
        client,
        user_id,
        agent_sources=None,
        coordinator_agent_id=None,
        agent=None,
        task_slug=None,
    ):
        self.client = client
        self.user_id = user_id
        self.headless = True
        self.agent_sources = agent_sources
        self.coordinator_agent_id = coordinator_agent_id
        self.agent = agent
        self.task_slug = task_slug
        self.pending_renders: list[dict] = []
        if agent:
            from services.workspace import get_agent_slug
            self.agent_slug = get_agent_slug(agent)
        else:
            self.agent_slug = None


async def get_headless_tools_for_agent(
    client: Any,
    user_id: str,
    agent: Optional[dict] = None,
    agent_sources: Optional[list] = None,
    coordinator_agent_id: Optional[str] = None,
    task_required_capabilities: Optional[list[str]] = None,
) -> list[dict]:
    """
    Resolve the full headless tool surface for an agent.

    Headless execution always gets the base primitive registry. Platform tools
    are added dynamically when, and only when:
    1. the agent's role bundle grants them, OR (per ADR-227) the task's
       **Required Capabilities:** TASK.md field declares them, AND
    2. the user has the provider connected.

    The two sources merge: roles declare universal identity (ADR-176), tasks
    declare ICP-specific needs (ADR-188 + ADR-207 P4b). Without the merge,
    universal-role agents on program-specific tasks never receive
    program-specific platform tools.
    """
    tools = list(HEADLESS_PRIMITIVES)
    if not client or not user_id or not agent:
        return tools

    auth = HeadlessAuth(client, user_id, agent_sources, coordinator_agent_id, agent)
    platform_tools = await get_platform_tools_for_agent(
        auth, agent, task_required_capabilities=task_required_capabilities,
    )
    if platform_tools:
        tools.extend(platform_tools)
    return tools


def create_headless_executor(
    client: Any,
    user_id: str,
    agent_sources: Optional[list] = None,
    coordinator_agent_id: Optional[str] = None,
    agent: Optional[dict] = None,
    dynamic_tools: Optional[list[dict]] = None,
    task_slug: Optional[str] = None,
):
    """
    Create a tool executor function for headless mode.

    Returns an async callable (tool_name, tool_input) -> result_dict
    that dispatches to primitive handlers with headless-appropriate
    error handling (log + return error dict, never raise).
    """
    auth = HeadlessAuth(client, user_id, agent_sources, coordinator_agent_id, agent, task_slug=task_slug)
    allowed_tool_names = set(_HEADLESS_TOOL_NAMES)
    if dynamic_tools:
        allowed_tool_names.update(tool["name"] for tool in dynamic_tools if tool.get("name"))

    async def executor(tool_name: str, tool_input: dict) -> dict:
        # Headless execution gets the base registry plus capability-scoped
        # platform tools resolved for this agent.
        if tool_name not in allowed_tool_names:
            logger.warning(
                f"[HEADLESS] Tool {tool_name} not available in headless mode, skipping"
            )
            return {
                "success": False,
                "error": "not_available",
                "message": f"Tool {tool_name} is not available in headless mode",
            }

        try:
            return await execute_primitive(auth, tool_name, tool_input)
        except Exception as e:
            logger.error(f"[HEADLESS] Tool {tool_name} failed: {e}")
            return {
                "success": False,
                "error": "execution_error",
                "message": f"Tool execution failed: {e}",
            }

    executor.auth = auth  # type: ignore[attr-defined]
    return executor
