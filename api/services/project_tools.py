"""
Tools for Thinking Partner (ADR-007, ADR-009)

Defines tools and handlers that give TP authority to:
- Manage projects (ADR-007)
- Initiate and track work (ADR-009)

Phase 1-2: Read-only tools (list_projects)
Phase 3: Mutation tools (create_project)
Phase 3.5: Update tools (rename_project, update_project)
Phase 4: Work tools (create_work, list_work, get_work_status)
"""

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

CREATE_PROJECT_TOOL = {
    "name": "create_project",
    "description": "Create a new project when the user explicitly asks to create one, or when a distinct topic/goal emerges that clearly warrants separate context. Always explain to the user why you're creating the project.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Short, descriptive project name (2-5 words)"
            },
            "description": {
                "type": "string",
                "description": "Brief description of project scope and purpose"
            }
        },
        "required": ["name"]
    }
}

RENAME_PROJECT_TOOL = {
    "name": "rename_project",
    "description": "Rename an existing project. Use when the user asks to change a project's name or when you identify that a project name could be clearer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "The UUID of the project to rename"
            },
            "new_name": {
                "type": "string",
                "description": "The new name for the project (2-5 words)"
            }
        },
        "required": ["project_id", "new_name"]
    }
}

UPDATE_PROJECT_TOOL = {
    "name": "update_project",
    "description": "Update a project's description. Use when the user wants to clarify or change what a project is about.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "The UUID of the project to update"
            },
            "description": {
                "type": "string",
                "description": "The new description for the project"
            }
        },
        "required": ["project_id", "description"]
    }
}


# =============================================================================
# Work Tools (ADR-009)
# =============================================================================

CREATE_WORK_TOOL = {
    "name": "create_work",
    "description": "Create a work request for an agent to complete a task. Use when the user asks you to research something, create content, or generate a report. The work will be processed asynchronously.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Clear description of what needs to be done"
            },
            "agent_type": {
                "type": "string",
                "enum": ["research", "content", "reporting"],
                "description": "Type of agent: 'research' for investigation/analysis, 'content' for writing/drafts, 'reporting' for summaries/reports"
            },
            "project_id": {
                "type": "string",
                "description": "UUID of the project this work belongs to. Required."
            },
            "parameters": {
                "type": "object",
                "description": "Optional agent-specific parameters (e.g., depth, format, tone)"
            }
        },
        "required": ["task", "agent_type", "project_id"]
    }
}

LIST_WORK_TOOL = {
    "name": "list_work",
    "description": "List work requests for a project or across all projects. Use to check what work is pending, running, or completed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Optional: Filter to a specific project. Omit to list across all projects."
            },
            "status": {
                "type": "string",
                "enum": ["pending", "running", "completed", "failed", "all"],
                "description": "Filter by status. Default: 'all'"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results. Default: 10"
            }
        },
        "required": []
    }
}

GET_WORK_STATUS_TOOL = {
    "name": "get_work_status",
    "description": "Get detailed status of a specific work request, including any outputs produced.",
    "input_schema": {
        "type": "object",
        "properties": {
            "work_id": {
                "type": "string",
                "description": "UUID of the work request"
            }
        },
        "required": ["work_id"]
    }
}


# Tools available to Thinking Partner
THINKING_PARTNER_TOOLS = [
    # Project management (ADR-007)
    LIST_PROJECTS_TOOL,
    CREATE_PROJECT_TOOL,
    RENAME_PROJECT_TOOL,
    UPDATE_PROJECT_TOOL,
    # Work management (ADR-009)
    CREATE_WORK_TOOL,
    LIST_WORK_TOOL,
    GET_WORK_STATUS_TOOL,
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


async def handle_create_project(auth, input: dict) -> dict:
    """
    Create a new project on behalf of TP.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with name and optional description

    Returns:
        Dict with created project details
    """
    from routes.projects import get_or_create_workspace

    workspace = await get_or_create_workspace(auth)

    result = auth.client.table("projects").insert({
        "name": input["name"],
        "description": input.get("description", ""),
        "workspace_id": workspace["id"],
    }).execute()

    if not result.data:
        return {
            "success": False,
            "error": "Failed to create project"
        }

    project = result.data[0]
    return {
        "success": True,
        "project": {
            "id": project["id"],
            "name": project["name"],
            "description": project.get("description", ""),
        },
        "message": f"Created project '{input['name']}'"
    }


async def handle_rename_project(auth, input: dict) -> dict:
    """
    Rename an existing project.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with project_id and new_name

    Returns:
        Dict with updated project details
    """
    project_id = input["project_id"]
    new_name = input["new_name"]

    # Update the project name
    result = auth.client.table("projects")\
        .update({"name": new_name})\
        .eq("id", project_id)\
        .execute()

    if not result.data:
        return {
            "success": False,
            "error": f"Project not found or access denied"
        }

    project = result.data[0]
    return {
        "success": True,
        "project": {
            "id": project["id"],
            "name": project["name"],
            "description": project.get("description", ""),
        },
        "message": f"Renamed project to '{new_name}'"
    }


async def handle_update_project(auth, input: dict) -> dict:
    """
    Update a project's description.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with project_id and description

    Returns:
        Dict with updated project details
    """
    project_id = input["project_id"]
    description = input["description"]

    # Update the project description
    result = auth.client.table("projects")\
        .update({"description": description})\
        .eq("id", project_id)\
        .execute()

    if not result.data:
        return {
            "success": False,
            "error": f"Project not found or access denied"
        }

    project = result.data[0]
    return {
        "success": True,
        "project": {
            "id": project["id"],
            "name": project["name"],
            "description": project.get("description", ""),
        },
        "message": f"Updated description for '{project['name']}'"
    }


# =============================================================================
# Work Tool Handlers (ADR-009)
# =============================================================================

async def handle_create_work(auth, input: dict) -> dict:
    """
    Create a work request for an agent and execute it immediately.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with task, agent_type, project_id, and optional parameters

    Returns:
        Dict with work execution results including outputs
    """
    import logging
    from services.work_execution import execute_work_ticket
    from jobs.email import send_work_complete_email

    logger = logging.getLogger(__name__)

    task = input["task"]
    agent_type = input["agent_type"]
    project_id = input["project_id"]
    parameters = input.get("parameters", {})

    # Validate agent_type
    valid_agent_types = ["research", "content", "reporting"]
    if agent_type not in valid_agent_types:
        return {
            "success": False,
            "error": f"Invalid agent_type. Must be one of: {', '.join(valid_agent_types)}"
        }

    # Create work ticket
    result = auth.client.table("work_tickets").insert({
        "task": task,
        "agent_type": agent_type,
        "project_id": project_id,
        "parameters": parameters,
        "status": "pending",
    }).execute()

    if not result.data:
        return {
            "success": False,
            "error": "Failed to create work request"
        }

    ticket = result.data[0]
    ticket_id = ticket["id"]

    # Execute the work immediately
    execution_result = await execute_work_ticket(
        auth.client,
        auth.user_id,
        ticket_id,
    )

    if not execution_result.get("success"):
        return {
            "success": False,
            "work": {
                "id": ticket_id,
                "task": task,
                "agent_type": agent_type,
                "status": "failed",
                "project_id": project_id,
            },
            "error": execution_result.get("error", "Work execution failed"),
            "message": f"Work request failed: {execution_result.get('error', 'Unknown error')}"
        }

    # Format outputs for TP response with summaries for conversation
    outputs = execution_result.get("outputs", [])
    output_summaries = []
    for output in outputs:
        # Parse content JSON to get summary
        summary = None
        content = output.get("content")
        if content:
            try:
                import json
                body = json.loads(content)
                summary = body.get("summary")
            except (json.JSONDecodeError, TypeError):
                pass

        output_summaries.append({
            "id": output.get("id"),
            "title": output.get("title"),
            "type": output.get("output_type"),
            "summary": summary,  # Include summary for TP to use in response
        })

    # Send email notification if user has email
    email_sent = False
    if auth.email and output_summaries:
        try:
            # Get project name for email
            project_result = auth.client.table("projects").select("name").eq("id", project_id).single().execute()
            project_name = project_result.data.get("name", "Unknown Project") if project_result.data else "Unknown Project"

            email_result = await send_work_complete_email(
                to=auth.email,
                project_name=project_name,
                agent_type=agent_type,
                task=task,
                outputs=output_summaries,
                project_id=project_id,
            )
            email_sent = email_result.success
            if not email_result.success:
                logger.warning(f"Failed to send work completion email: {email_result.error}")
        except Exception as e:
            logger.warning(f"Error sending work completion email: {e}")

    return {
        "success": True,
        "work": {
            "id": ticket_id,
            "task": task,
            "agent_type": agent_type,
            "status": "completed",
            "project_id": project_id,
            "execution_time_ms": execution_result.get("execution_time_ms"),
        },
        "outputs": output_summaries,
        "output_count": len(outputs),
        "email_sent": email_sent,
        "message": f"Completed {agent_type} work with {len(outputs)} output(s). See summaries below.",
        "instruction_to_assistant": "Present these outputs to the user conversationally. Mention each output by title and summarize what was found. Invite them to check the Work tab for full details."
    }


async def handle_list_work(auth, input: dict) -> dict:
    """
    List work requests, optionally filtered by project and status.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with optional project_id, status, and limit

    Returns:
        Dict with work requests list
    """
    from routes.projects import get_or_create_workspace

    workspace = await get_or_create_workspace(auth)
    project_id = input.get("project_id")
    status_filter = input.get("status", "all")
    limit = input.get("limit", 10)

    # Build query - join through projects to respect workspace ownership
    query = auth.client.table("work_tickets")\
        .select("id, task, agent_type, status, project_id, created_at, started_at, completed_at, projects(name)")\
        .order("created_at", desc=True)\
        .limit(limit)

    # Filter by project if specified
    if project_id:
        query = query.eq("project_id", project_id)

    # Filter by status if not "all"
    if status_filter and status_filter != "all":
        query = query.eq("status", status_filter)

    result = query.execute()
    tickets = result.data or []

    # Format response
    work_items = []
    for t in tickets:
        project_name = t.get("projects", {}).get("name", "Unknown") if t.get("projects") else "Unknown"
        work_items.append({
            "id": t["id"],
            "task": t["task"][:100] + "..." if len(t["task"]) > 100 else t["task"],
            "agent_type": t["agent_type"],
            "status": t["status"],
            "project_name": project_name,
            "created_at": t["created_at"],
        })

    return {
        "success": True,
        "work": work_items,
        "count": len(work_items),
        "message": f"Found {len(work_items)} work request(s)"
    }


async def handle_get_work_status(auth, input: dict) -> dict:
    """
    Get detailed status of a specific work request.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with work_id

    Returns:
        Dict with work request details and outputs
    """
    work_id = input["work_id"]

    # Get work ticket with project info
    ticket_result = auth.client.table("work_tickets")\
        .select("*, projects(name)")\
        .eq("id", work_id)\
        .single()\
        .execute()

    if not ticket_result.data:
        return {
            "success": False,
            "error": "Work request not found or access denied"
        }

    ticket = ticket_result.data
    project_name = ticket.get("projects", {}).get("name", "Unknown") if ticket.get("projects") else "Unknown"

    # Get any outputs for this ticket
    outputs_result = auth.client.table("work_outputs")\
        .select("id, title, output_type, content, file_url, file_format, created_at, status")\
        .eq("ticket_id", work_id)\
        .order("created_at", desc=False)\
        .execute()

    outputs = outputs_result.data or []

    return {
        "success": True,
        "work": {
            "id": ticket["id"],
            "task": ticket["task"],
            "agent_type": ticket["agent_type"],
            "status": ticket["status"],
            "project_name": project_name,
            "created_at": ticket["created_at"],
            "started_at": ticket.get("started_at"),
            "completed_at": ticket.get("completed_at"),
            "error_message": ticket.get("error_message"),
            "parameters": ticket.get("parameters", {}),
        },
        "outputs": [
            {
                "id": o["id"],
                "title": o["title"],
                "type": o["output_type"],
                "content_preview": o["content"][:200] + "..." if o.get("content") and len(o["content"]) > 200 else o.get("content"),
                "file_url": o.get("file_url"),
                "file_format": o.get("file_format"),
                "status": o.get("status", "delivered"),
            }
            for o in outputs
        ],
        "output_count": len(outputs),
        "message": f"Work status: {ticket['status']}" + (f" with {len(outputs)} output(s)" if outputs else "")
    }


# Registry mapping tool names to handlers
TOOL_HANDLERS: dict[str, ToolHandler] = {
    # Project tools (ADR-007)
    "list_projects": handle_list_projects,
    "create_project": handle_create_project,
    "rename_project": handle_rename_project,
    "update_project": handle_update_project,
    # Work tools (ADR-009)
    "create_work": handle_create_work,
    "list_work": handle_list_work,
    "get_work_status": handle_get_work_status,
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
