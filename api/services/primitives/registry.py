"""
Primitive Registry

Central registry for all primitives and their handlers.
ADR-050: Platform tools are routed via handle_platform_tool.
ADR-080: Mode-gated primitives — each primitive declares which modes
it supports (chat, headless). get_tools_for_mode() and
create_headless_executor() provide the headless mode interface.
"""

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

from .read import READ_TOOL, handle_read
from .write import WRITE_TOOL, handle_write
from .edit import EDIT_TOOL, handle_edit
from .search import SEARCH_TOOL, handle_search
from .list import LIST_TOOL, handle_list
from .execute import EXECUTE_TOOL, handle_execute
from .refresh import REFRESH_PLATFORM_CONTENT_TOOL, handle_refresh_platform_content
from .todo import TODO_TOOL, handle_todo
from .web_search import WEB_SEARCH_PRIMITIVE, handle_web_search
from .system_state import GET_SYSTEM_STATE_TOOL, handle_get_system_state
from .coordinator import (
    CREATE_AGENT_TOOL, handle_create_agent,
    ADVANCE_AGENT_SCHEDULE_TOOL, handle_advance_agent_schedule,
)
from .workspace import (
    READ_WORKSPACE_TOOL, handle_read_workspace,
    WRITE_WORKSPACE_TOOL, handle_write_workspace,
    SEARCH_WORKSPACE_TOOL, handle_search_workspace,
    QUERY_KNOWLEDGE_TOOL, handle_query_knowledge,
    LIST_WORKSPACE_TOOL, handle_list_workspace,
    DISCOVER_AGENTS_TOOL, handle_discover_agents,
    READ_AGENT_CONTEXT_TOOL, handle_read_agent_context,
)
from .save_memory import SAVE_MEMORY_TOOL, handle_save_memory
from .runtime_dispatch import RUNTIME_DISPATCH_TOOL, handle_runtime_dispatch
from .project import (
    CREATE_PROJECT_TOOL, handle_create_project,
    READ_PROJECT_TOOL, handle_read_project,
)
from .project_execution import (
    CHECK_CONTRIBUTOR_FRESHNESS_TOOL, handle_check_contributor_freshness,
    READ_PROJECT_STATUS_TOOL, handle_read_project_status,
    REQUEST_CONTRIBUTOR_ADVANCE_TOOL, handle_request_contributor_advance,
    UPDATE_PROJECT_INTENT_TOOL, handle_update_project_intent,
)
from services.platform_tools import is_platform_tool, handle_platform_tool


# Communication primitives (kept from legacy for respond/clarify)
RESPOND_TOOL = {
    "name": "Respond",
    "description": """Send a message to the user.

Use after other primitives to provide context, confirm actions, or continue conversation.
The message appears inline in chat.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to send"
            }
        },
        "required": ["message"]
    }
}


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


async def handle_respond(auth: Any, input: dict) -> dict:
    """Handle Respond primitive."""
    message = input.get("message", "")
    return {
        "success": True,
        "message": message,
        "ui_action": {
            "type": "RESPOND",
            "data": {"message": message},
        },
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
        if i["platform"] == "google":
            if metadata.get("user_email"):
                item["user_email"] = metadata["user_email"]
            if metadata.get("designated_calendar_id"):
                item["designated_calendar_id"] = metadata["designated_calendar_id"]
        items.append(item)

    return {
        "success": True,
        "integrations": items,
        "count": len(items),
    }


LIST_INTEGRATIONS_TOOL = {
    "name": "list_integrations",
    "description": """List the user's connected platform integrations and their metadata.

Call this first when about to use a platform tool, to get:
- Which platforms are active (slack, gmail, notion, google/calendar)
- Slack: authed_user_id — use as channel_id when sending DMs to self
- Notion: designated_page_id — use as page_id when writing to user's YARNNN page
- Gmail/Calendar: user_email and designated_calendar_id

AGENTIC BEHAVIOR: Don't ask "are you connected to Slack?" — call list_integrations and find out.
If not connected, suggest connecting in Settings.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


# All primitives exposed to TP
# Excluded:
# - Todo: conversation stream IS the progress indicator (Claude Code pattern)
# - Respond: TP's natural text output serves as the response
PRIMITIVES = [
    # Data operations
    READ_TOOL,
    WRITE_TOOL,
    EDIT_TOOL,
    SEARCH_TOOL,
    LIST_TOOL,
    # External operations
    EXECUTE_TOOL,
    # Platform content refresh (ADR-085)
    REFRESH_PLATFORM_CONTENT_TOOL,
    # Web operations (ADR-045)
    WEB_SEARCH_PRIMITIVE,
    # Platform discovery — resolves connection metadata (authed_user_id, designated_page_id, etc.)
    LIST_INTEGRATIONS_TOOL,
    # System state introspection (ADR-072)
    GET_SYSTEM_STATE_TOOL,
    # Communication (Clarify only - Respond removed)
    CLARIFY_TOOL,
    # Coordinator write primitives — headless only (ADR-092)
    CREATE_AGENT_TOOL,
    ADVANCE_AGENT_SCHEDULE_TOOL,
    # Workspace primitives — headless only (ADR-106)
    READ_WORKSPACE_TOOL,
    WRITE_WORKSPACE_TOOL,
    SEARCH_WORKSPACE_TOOL,
    QUERY_KNOWLEDGE_TOOL,
    LIST_WORKSPACE_TOOL,
    # Inter-agent discovery — headless only (ADR-116)
    DISCOVER_AGENTS_TOOL,
    # Cross-agent workspace reading — headless only (ADR-116 Phase 3)
    READ_AGENT_CONTEXT_TOOL,
    # User memory — chat only (ADR-108)
    SAVE_MEMORY_TOOL,
    # Runtime dispatch — headless only (ADR-118)
    RUNTIME_DISPATCH_TOOL,
    # Project primitives — chat + headless (ADR-119 Phase 2)
    CREATE_PROJECT_TOOL,
    READ_PROJECT_TOOL,
    # PM project execution primitives — headless only (ADR-120 Phase 1 + P4)
    CHECK_CONTRIBUTOR_FRESHNESS_TOOL,
    READ_PROJECT_STATUS_TOOL,
    REQUEST_CONTRIBUTOR_ADVANCE_TOOL,
    UPDATE_PROJECT_INTENT_TOOL,
]


# Handler mapping
HANDLERS: dict[str, Callable] = {
    "Read": handle_read,
    "Write": handle_write,
    "Edit": handle_edit,
    "Search": handle_search,
    "List": handle_list,
    "Execute": handle_execute,
    "RefreshPlatformContent": handle_refresh_platform_content,
    "Todo": handle_todo,
    "WebSearch": handle_web_search,
    "GetSystemState": handle_get_system_state,
    "Respond": handle_respond,
    "Clarify": handle_clarify,
    "list_integrations": handle_list_integrations,
    "CreateAgent": handle_create_agent,
    "AdvanceAgentSchedule": handle_advance_agent_schedule,
    "ReadWorkspace": handle_read_workspace,
    "WriteWorkspace": handle_write_workspace,
    "SearchWorkspace": handle_search_workspace,
    "QueryKnowledge": handle_query_knowledge,
    "ListWorkspace": handle_list_workspace,
    "DiscoverAgents": handle_discover_agents,
    "ReadAgentContext": handle_read_agent_context,
    "SaveMemory": handle_save_memory,
    "RuntimeDispatch": handle_runtime_dispatch,
    "CreateProject": handle_create_project,
    "ReadProject": handle_read_project,
    "CheckContributorFreshness": handle_check_contributor_freshness,
    "ReadProjectStatus": handle_read_project_status,
    "RequestContributorAdvance": handle_request_contributor_advance,
    "UpdateProjectIntent": handle_update_project_intent,
}


async def execute_primitive(auth: Any, name: str, input: dict) -> dict:
    """
    Execute a primitive by name.

    ADR-050: Platform tools (platform_*) are routed to MCP Gateway.

    Args:
        auth: Auth context with user_id and client
        name: Primitive name (e.g., "Read", "Write") or platform tool (e.g., "platform_slack_send_message")
        input: Primitive input parameters

    Returns:
        Primitive result dict
    """
    # ADR-050: Route platform tools to MCP Gateway
    if is_platform_tool(name):
        try:
            result = await handle_platform_tool(auth, name, input)
            return result
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
        result = await handler(auth, input)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": "execution_error",
            "message": str(e),
            "primitive": name,
        }


# =============================================================================
# ADR-080: Mode-Gated Primitives
# =============================================================================

# Which primitives are available in each mode.
# "chat" = full TP session (streaming, user present)
# "headless" = background generation (non-streaming, no user)
PRIMITIVE_MODES: dict[str, list[str]] = {
    # Read-only investigation — both modes
    "Search":           ["chat", "headless"],
    "Read":             ["chat", "headless"],
    "List":             ["chat", "headless"],
    "GetSystemState":   ["chat", "headless"],
    "WebSearch":        ["chat", "headless"],

    # Write/action/UI primitives — chat only
    "Write":            ["chat"],
    "Edit":             ["chat"],
    "Execute":          ["chat"],
    "RefreshPlatformContent": ["chat", "headless"],  # ADR-085, extended by ADR-092
    "Todo":             ["chat"],
    "Respond":          ["chat"],
    "Clarify":          ["chat"],
    "list_integrations": ["chat"],
    # Agent creation — chat + headless (ADR-111: unified CreateAgent)
    "CreateAgent":            ["chat", "headless"],
    # Coordinator-only primitives — headless only (ADR-092)
    "AdvanceAgentSchedule":   ["headless"],
    # Workspace primitives — headless only (ADR-106)
    "ReadWorkspace":          ["headless"],
    "WriteWorkspace":         ["headless"],
    "SearchWorkspace":        ["headless"],
    "QueryKnowledge":         ["headless"],
    "ListWorkspace":          ["headless"],
    # Inter-agent discovery — headless only (ADR-116)
    "DiscoverAgents":         ["headless"],
    # Cross-agent workspace reading — headless only (ADR-116 Phase 3)
    "ReadAgentContext":       ["headless"],
    # User memory — chat only (ADR-108)
    "SaveMemory":             ["chat"],
    # Runtime dispatch — headless only (ADR-118)
    "RuntimeDispatch":        ["headless"],
    # Project primitives — chat + headless (ADR-119 Phase 2)
    "CreateProject":          ["chat", "headless"],
    "ReadProject":            ["chat", "headless"],
    # PM project execution — headless only (ADR-120 Phase 1 + P4)
    "CheckContributorFreshness":  ["headless"],
    "ReadProjectStatus":          ["headless"],
    "RequestContributorAdvance":  ["headless"],
    "UpdateProjectIntent":        ["headless"],
}

# Note: platform_* tools (dynamic, loaded per user) are chat-only by default.


def get_tools_for_mode(mode: str) -> list[dict]:
    """
    Get tool definitions filtered by mode.

    Args:
        mode: "chat" or "headless"

    Returns:
        List of tool definition dicts for the Anthropic API
    """
    tools = []
    for tool_def in PRIMITIVES:
        name = tool_def.get("name", "")
        modes = PRIMITIVE_MODES.get(name, ["chat"])
        if mode in modes:
            tools.append(tool_def)
    return tools


def create_headless_executor(client: Any, user_id: str, agent_sources: Optional[list] = None, coordinator_agent_id: Optional[str] = None, agent: Optional[dict] = None):
    """
    Create a tool executor function for headless mode.

    Returns an async callable (tool_name, tool_input) -> result_dict
    that dispatches to primitive handlers with headless-appropriate
    error handling (log + return error dict, never raise).

    Args:
        client: Supabase client (service role)
        user_id: User UUID for data scoping
        agent_sources: ADR-092 — agent's configured sources list, used by
                             RefreshPlatformContent to scope headless refreshes
        coordinator_agent_id: ADR-092 — ID of the coordinator agent running this
                                    executor, used by CreateAgent for attribution
        agent: ADR-106 — full agent dict, used by workspace primitives for context
    """
    class HeadlessAuth:
        """Minimal auth context for headless execution."""
        def __init__(self, client, user_id, agent_sources=None, coordinator_agent_id=None, agent=None):
            self.client = client
            self.user_id = user_id
            self.headless = True  # ADR-092: signals headless mode to primitives
            self.agent_sources = agent_sources  # ADR-092: source scoping
            self.coordinator_agent_id = coordinator_agent_id  # ADR-092: attribution
            self.agent = agent  # ADR-106: workspace primitives need agent context
            self.pending_renders: list[dict] = []  # ADR-118 D.3: accumulate rendered files for save_output()
            # ADR-118 D.3: agent_slug for RuntimeDispatch workspace paths
            if agent:
                from services.workspace import get_agent_slug
                self.agent_slug = get_agent_slug(agent)
            else:
                self.agent_slug = None

    auth = HeadlessAuth(client, user_id, agent_sources, coordinator_agent_id, agent)

    async def executor(tool_name: str, tool_input: dict) -> dict:
        # Verify tool is allowed in headless mode
        modes = PRIMITIVE_MODES.get(tool_name, [])
        if "headless" not in modes:
            logger.warning(
                f"[HEADLESS] Tool {tool_name} not available in headless mode, skipping"
            )
            return {
                "success": False,
                "error": "not_available",
                "message": f"Tool {tool_name} is not available in headless mode",
            }

        handler = HANDLERS.get(tool_name)
        if not handler:
            return {
                "success": False,
                "error": "unknown_primitive",
                "message": f"Unknown primitive: {tool_name}",
            }

        try:
            result = await handler(auth, tool_input)
            return result
        except Exception as e:
            logger.error(f"[HEADLESS] Tool {tool_name} failed: {e}")
            return {
                "success": False,
                "error": "execution_error",
                "message": f"Tool execution failed: {e}",
            }

    # ADR-118 D.3: Expose auth context so callers can read pending_renders
    executor.auth = auth  # type: ignore[attr-defined]
    return executor
