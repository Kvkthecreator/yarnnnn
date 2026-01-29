"""
Project tools for Thinking Partner (ADR-007)

Defines tools and handlers that give TP authority to manage projects.
Phase 1-2: Read-only tools (list_projects)
Phase 3+: Mutation tools (create_project, etc.)
"""

import json
from typing import Callable, Any

# Type alias for tool handlers
# Handler signature: async def handler(auth: UserClient, input: dict) -> dict
ToolHandler = Callable[[Any, dict], Any]


# =============================================================================
# Tool Definitions (Anthropic format)
# =============================================================================

LIST_PROJECTS_TOOL = {
    "name": "list_projects",
    "description": "Get the user's existing projects to understand their current organization. Use this to see what projects exist before suggesting organization changes.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

# Phase 3: Create project tool (commented out for now)
# CREATE_PROJECT_TOOL = {
#     "name": "create_project",
#     "description": "Create a new project when a distinct topic/goal emerges that warrants separate context. Use sparingly - only when conversation clearly indicates a new domain.",
#     "input_schema": {
#         "type": "object",
#         "properties": {
#             "name": {
#                 "type": "string",
#                 "description": "Short, descriptive project name"
#             },
#             "description": {
#                 "type": "string",
#                 "description": "Brief description of project scope"
#             },
#             "reason": {
#                 "type": "string",
#                 "description": "Why this warrants a new project (shown to user)"
#             }
#         },
#         "required": ["name", "reason"]
#     }
# }

# Tools available to Thinking Partner (Phase 2: read-only)
THINKING_PARTNER_TOOLS = [
    LIST_PROJECTS_TOOL,
]


# =============================================================================
# Tool Handlers
# =============================================================================

async def handle_list_projects(auth, input: dict) -> dict:
    """
    List user's projects.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input (empty for this tool)

    Returns:
        Dict with projects list and count
    """
    # Import here to avoid circular dependency
    from routes.projects import get_or_create_workspace

    workspace = await get_or_create_workspace(auth)

    result = auth.client.table("projects")\
        .select("id, name, description, created_at")\
        .eq("workspace_id", workspace["id"])\
        .order("created_at", desc=False)\
        .execute()

    projects = result.data or []

    return {
        "success": True,
        "projects": [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description", ""),
            }
            for p in projects
        ],
        "count": len(projects),
        "message": f"Found {len(projects)} project(s)" if projects else "No projects yet"
    }


# Phase 3: Create project handler (commented out for now)
# async def handle_create_project(auth, input: dict) -> dict:
#     """
#     Create a new project on behalf of TP.
#
#     Args:
#         auth: UserClient with authenticated Supabase client
#         input: Tool input with name, description, reason
#
#     Returns:
#         Dict with created project details
#     """
#     from routes.projects import get_or_create_workspace
#
#     workspace = await get_or_create_workspace(auth)
#
#     result = auth.client.table("projects").insert({
#         "name": input["name"],
#         "description": input.get("description", ""),
#         "workspace_id": workspace["id"],
#     }).execute()
#
#     if not result.data:
#         return {
#             "success": False,
#             "error": "Failed to create project"
#         }
#
#     project = result.data[0]
#     return {
#         "success": True,
#         "project": {
#             "id": project["id"],
#             "name": project["name"],
#             "description": project.get("description", ""),
#         },
#         "message": f"Created project '{input['name']}'"
#     }


# Registry mapping tool names to handlers
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "list_projects": handle_list_projects,
    # "create_project": handle_create_project,  # Phase 3
}


# =============================================================================
# Tool Execution Helper
# =============================================================================

async def execute_tool(auth, tool_name: str, tool_input: dict) -> dict:
    """
    Execute a tool by name with the given input.

    Args:
        auth: UserClient for database access
        tool_name: Name of the tool to execute
        tool_input: Input parameters for the tool

    Returns:
        Tool result dict
    """
    handler = TOOL_HANDLERS.get(tool_name)

    if not handler:
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }

    try:
        return await handler(auth, tool_input)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
