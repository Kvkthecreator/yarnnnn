"""
Tools for Thinking Partner (ADR-007, ADR-017)

Defines tools and handlers that give TP authority to:
- Manage projects (ADR-007)
- Initiate and track work (ADR-017 Unified Work Model)

ADR-017: Unified Work Model
- Single create_work tool with frequency parameter
- "once" for one-time work, schedule strings for recurring
- Replaces separate schedule_work tool
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
# Work Tools (ADR-017 Unified Work Model)
# =============================================================================

CREATE_WORK_TOOL = {
    "name": "create_work",
    "description": """Create work for a specialized agent.

ADR-017: Unified Work Model - frequency is just an attribute of work.

FREQUENCY OPTIONS:
- "once" (default): Execute immediately, one time only
- "daily at 9am": Run every day at specified time
- "weekly on Monday at 10am": Run weekly on specified day
- "every 6 hours": Run at regular intervals

For recurring work (frequency != "once"), set run_first=true to also execute immediately.

CONTEXT ROUTING (ADR-015):
- If user is in a project context, use that project_id
- If request clearly relates to an existing project, route it there
- If request is personal/one-off, omit project_id (creates ambient work)

EXAMPLES:
- "Research competitors" → frequency="once"
- "Daily AI news digest" → frequency="daily at 9am"
- "Weekly status report" → frequency="weekly on Monday at 9am"
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "What the agent should do"
            },
            "agent_type": {
                "type": "string",
                "enum": ["research", "content", "reporting"],
                "description": "Type of agent: 'research' for investigation/analysis, 'content' for writing/drafts, 'reporting' for summaries/reports"
            },
            "frequency": {
                "type": "string",
                "description": "'once' for immediate one-time work, or a schedule like 'daily at 9am', 'weekly on Monday', 'every 6 hours'. Default: 'once'"
            },
            "project_id": {
                "type": "string",
                "description": "UUID of the project this work belongs to. Optional - omit for ambient/personal work."
            },
            "parameters": {
                "type": "object",
                "description": "Optional agent-specific parameters (e.g., depth, format, tone)"
            },
            "run_first": {
                "type": "boolean",
                "description": "For recurring work: also execute immediately? Default: true"
            },
            "timezone": {
                "type": "string",
                "description": "User's timezone for scheduled work, e.g., 'America/Los_Angeles'. Default: 'UTC'"
            }
        },
        "required": ["task", "agent_type"]
    }
}

LIST_WORK_TOOL = {
    "name": "list_work",
    "description": """List work for a project or across all projects.

ADR-017: Shows both one-time and recurring work. Use filters to narrow down.

FILTERS:
- active_only: Show only recurring work that's actively scheduled
- include_completed: Include completed one-time work (default: true)
- project_id: Filter to specific project""",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Optional: Filter to a specific project. Omit to list across all projects."
            },
            "active_only": {
                "type": "boolean",
                "description": "Only show active recurring work. Default: false"
            },
            "include_completed": {
                "type": "boolean",
                "description": "Include completed one-time work. Default: true"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results. Default: 10"
            }
        },
        "required": []
    }
}

GET_WORK_TOOL = {
    "name": "get_work",
    "description": """Get detailed information about specific work, including all outputs.

ADR-017: Shows work details and all outputs (run_number 1, 2, 3... for recurring).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "work_id": {
                "type": "string",
                "description": "UUID of the work"
            }
        },
        "required": ["work_id"]
    }
}

UPDATE_WORK_TOOL = {
    "name": "update_work",
    "description": """Update work settings. Use to pause/resume recurring work, change frequency, or update task.

ADR-017: Works for both one-time and recurring work.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "work_id": {
                "type": "string",
                "description": "UUID of the work to update"
            },
            "is_active": {
                "type": "boolean",
                "description": "Set to false to pause recurring work, true to resume"
            },
            "frequency": {
                "type": "string",
                "description": "New frequency (e.g., 'daily at 10am' instead of 9am)"
            },
            "task": {
                "type": "string",
                "description": "Updated task description"
            }
        },
        "required": ["work_id"]
    }
}

DELETE_WORK_TOOL = {
    "name": "delete_work",
    "description": """Delete work and all its outputs. Use when user wants to remove work entirely.

For recurring work, this stops all future runs and removes history.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "work_id": {
                "type": "string",
                "description": "UUID of the work to delete"
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
    # Unified work management (ADR-017)
    CREATE_WORK_TOOL,
    LIST_WORK_TOOL,
    GET_WORK_TOOL,
    UPDATE_WORK_TOOL,
    DELETE_WORK_TOOL,
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
# Work Tool Handlers (ADR-017 Unified Work Model)
# =============================================================================

async def handle_create_work(auth, input: dict) -> dict:
    """
    Create work for an agent - handles both one-time and recurring.

    ADR-017: Unified Work Model - frequency is just an attribute.
    - frequency="once" (default): Execute immediately, one time
    - frequency="daily at 9am", etc.: Set up recurring work

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with task, agent_type, frequency, optional project_id, parameters

    Returns:
        Dict with work details and output (for immediate execution)
    """
    import logging
    from services.work_execution import execute_work_ticket
    from jobs.email import send_work_complete_email
    from jobs.work_scheduler import calculate_next_run

    logger = logging.getLogger(__name__)

    task = input["task"]
    agent_type = input["agent_type"]
    frequency = input.get("frequency", "once")
    project_id = input.get("project_id")
    parameters = input.get("parameters", {})
    run_first = input.get("run_first", True)
    user_timezone = input.get("timezone", "UTC")

    # Validate agent_type
    valid_agent_types = ["research", "content", "reporting"]
    if agent_type not in valid_agent_types:
        return {
            "success": False,
            "error": f"Invalid agent_type. Must be one of: {', '.join(valid_agent_types)}"
        }

    # Determine if this is recurring work
    is_recurring = frequency.lower() != "once"

    # Build work data
    work_data = {
        "task": task,
        "agent_type": agent_type,
        "parameters": parameters,
        "user_id": auth.user_id,
        "status": "pending",  # Status will move to outputs in future migration
        "is_template": False,  # ADR-017: No more templates, but keep for backward compat
    }

    if project_id:
        work_data["project_id"] = project_id

    if is_recurring:
        # Parse schedule to cron
        cron_expr = parse_schedule_to_cron(frequency)

        # Calculate next run time
        try:
            next_run = calculate_next_run(cron_expr, user_timezone)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid schedule '{frequency}': {e}"
            }

        work_data["schedule_cron"] = cron_expr
        work_data["schedule_timezone"] = user_timezone
        work_data["schedule_enabled"] = True
        work_data["schedule_next_run_at"] = next_run.isoformat()
        # Note: ADR-017 will rename these to frequency_cron, is_active, next_run_at
        # For now, using existing column names for backward compatibility

    # Create work record
    result = auth.client.table("work_tickets").insert(work_data).execute()

    if not result.data:
        return {
            "success": False,
            "error": "Failed to create work"
        }

    work = result.data[0]
    work_id = work["id"]

    # For one-time work OR recurring with run_first=True, execute immediately
    should_execute = not is_recurring or run_first
    output_summary = None
    execution_result = None

    if should_execute:
        execution_result = await execute_work_ticket(
            auth.client,
            auth.user_id,
            work_id,
        )

        if execution_result.get("success"):
            output = execution_result.get("output")
            if output:
                content = output.get("content", "")
                preview = content[:200] + "..." if len(content) > 200 else content
                output_summary = {
                    "id": output.get("id"),
                    "title": output.get("title"),
                    "preview": preview,
                    "metadata": output.get("metadata", {}),
                    "run_number": 1,
                }

            # Send email notification
            if auth.email and output_summary:
                try:
                    project_name = "Personal Work"
                    if project_id:
                        project_result = auth.client.table("projects").select("name").eq("id", project_id).single().execute()
                        project_name = project_result.data.get("name", "Unknown Project") if project_result.data else "Unknown Project"

                    await send_work_complete_email(
                        to=auth.email,
                        project_name=project_name,
                        agent_type=agent_type,
                        task=task,
                        outputs=[output_summary],
                        project_id=project_id,
                    )
                except Exception as e:
                    logger.warning(f"Error sending work completion email: {e}")

    # Build response
    human_schedule = cron_to_human(work_data.get("schedule_cron", "")) if is_recurring else None

    response = {
        "success": True,
        "work": {
            "id": work_id,
            "task": task,
            "agent_type": agent_type,
            "frequency": frequency,
            "project_id": project_id,
            "is_recurring": is_recurring,
        },
    }

    if is_recurring:
        response["work"]["schedule"] = human_schedule
        response["work"]["next_run"] = work_data.get("schedule_next_run_at")
        response["work"]["is_active"] = True

        if run_first and output_summary:
            response["output"] = output_summary
            response["message"] = f"Recurring work created ({human_schedule}). First output ready in the output panel."
        else:
            response["message"] = f"Recurring work created: {human_schedule}. First run scheduled."
    else:
        # One-time work
        if execution_result and execution_result.get("success"):
            response["work"]["status"] = "completed"
            response["work"]["execution_time_ms"] = execution_result.get("execution_time_ms")
            response["output"] = output_summary
            response["message"] = "Work complete. Output available in the output panel."
        else:
            response["work"]["status"] = "failed"
            response["error"] = execution_result.get("error", "Execution failed") if execution_result else "Failed to execute"
            response["message"] = f"Work failed: {response['error']}"
            return response

    # UI action for completed work
    if output_summary:
        response["ui_action"] = {
            "type": "OPEN_SURFACE",
            "surface": "output",
            "data": {
                "workId": work_id,
                "projectId": project_id,
            }
        }
        response["instruction_to_assistant"] = "Keep your response brief (1-2 sentences). Acknowledge the work is done and direct the user to the output panel."

    return response


async def handle_list_work(auth, input: dict) -> dict:
    """
    List work, including both one-time and recurring.

    ADR-017: Unified work listing with frequency info.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with optional project_id, active_only, include_completed, limit

    Returns:
        Dict with work list
    """
    project_id = input.get("project_id")
    active_only = input.get("active_only", False)
    include_completed = input.get("include_completed", True)
    limit = input.get("limit", 10)

    # Build query
    query = auth.client.table("work_tickets")\
        .select("id, task, agent_type, status, project_id, user_id, created_at, started_at, completed_at, schedule_cron, schedule_enabled, schedule_next_run_at, is_template, projects(name)")\
        .eq("user_id", auth.user_id)\
        .order("created_at", desc=True)\
        .limit(limit)

    # Filter by project if specified
    if project_id:
        query = query.eq("project_id", project_id)

    # Active only: show recurring work that's enabled
    if active_only:
        query = query.eq("schedule_enabled", True).not_.is_("schedule_cron", "null")

    result = query.execute()
    items = result.data or []

    # Format response
    work_items = []
    for t in items:
        # Determine if recurring (has schedule_cron)
        is_recurring = t.get("schedule_cron") is not None

        # Skip completed one-time work if not including completed
        if not include_completed and not is_recurring and t.get("status") == "completed":
            continue

        # Project name
        if t.get("project_id"):
            project_name = t.get("projects", {}).get("name", "Unknown") if t.get("projects") else "Unknown"
        else:
            project_name = "Personal"

        work_item = {
            "id": t["id"],
            "task": t["task"][:100] + "..." if len(t["task"]) > 100 else t["task"],
            "agent_type": t["agent_type"],
            "project_name": project_name,
            "is_ambient": t.get("project_id") is None,
            "is_recurring": is_recurring,
            "created_at": t["created_at"],
        }

        if is_recurring:
            work_item["frequency"] = cron_to_human(t["schedule_cron"])
            work_item["is_active"] = t.get("schedule_enabled", True)
            work_item["next_run"] = t.get("schedule_next_run_at")
        else:
            work_item["frequency"] = "once"
            work_item["status"] = t["status"]

        work_items.append(work_item)

    return {
        "success": True,
        "work": work_items,
        "count": len(work_items),
        "message": f"Found {len(work_items)} work item(s)"
    }


async def handle_get_work(auth, input: dict) -> dict:
    """
    Get detailed information about work, including all outputs.

    ADR-017: Shows work details and all outputs (with run_number for recurring).

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with work_id

    Returns:
        Dict with work details and outputs
    """
    work_id = input["work_id"]

    # Get work with project info
    try:
        work_result = auth.client.table("work_tickets")\
            .select("*, projects(name)")\
            .eq("id", work_id)\
            .eq("user_id", auth.user_id)\
            .single()\
            .execute()
    except Exception:
        # .single() throws when 0 rows returned
        return {
            "success": False,
            "error": "Work not found or access denied"
        }

    if not work_result.data:
        return {
            "success": False,
            "error": "Work not found or access denied"
        }

    work = work_result.data
    project_name = work.get("projects", {}).get("name", "Personal") if work.get("projects") else "Personal"
    is_recurring = work.get("schedule_cron") is not None

    # Get outputs for this work
    # Note: metadata column may not exist if migration 016 hasn't been applied
    # Use "*" to select all columns and handle missing columns gracefully
    outputs_result = auth.client.table("work_outputs")\
        .select("*")\
        .eq("ticket_id", work_id)\
        .order("created_at", desc=True)\
        .execute()

    outputs = outputs_result.data or []

    # Build work info
    work_info = {
        "id": work["id"],
        "task": work["task"],
        "agent_type": work["agent_type"],
        "project_name": project_name,
        "is_recurring": is_recurring,
        "created_at": work["created_at"],
        "parameters": work.get("parameters", {}),
    }

    if is_recurring:
        work_info["frequency"] = cron_to_human(work["schedule_cron"])
        work_info["is_active"] = work.get("schedule_enabled", True)
        work_info["next_run"] = work.get("schedule_next_run_at")
        work_info["last_run"] = work.get("schedule_last_run_at")
    else:
        work_info["frequency"] = "once"
        work_info["status"] = work["status"]
        work_info["started_at"] = work.get("started_at")
        work_info["completed_at"] = work.get("completed_at")
        if work.get("error_message"):
            work_info["error_message"] = work["error_message"]

    # Format outputs with run numbers
    output_list = []
    for i, o in enumerate(reversed(outputs)):  # Oldest first for run numbering
        output_list.append({
            "id": o["id"],
            "title": o["title"],
            "type": o["output_type"],
            "run_number": i + 1,
            "content_preview": o["content"][:200] + "..." if o.get("content") and len(o["content"]) > 200 else o.get("content"),
            "file_url": o.get("file_url"),
            "file_format": o.get("file_format"),
            "status": o.get("status", "delivered"),
            "created_at": o["created_at"],
        })

    return {
        "success": True,
        "work": work_info,
        "outputs": list(reversed(output_list)),  # Most recent first
        "output_count": len(outputs),
        "message": f"Work has {len(outputs)} output(s)"
    }


async def handle_update_work(auth, input: dict) -> dict:
    """
    Update work settings (pause/resume, change frequency, update task).

    ADR-017: Works for both one-time and recurring work.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with work_id and optional updates

    Returns:
        Dict with updated work details
    """
    work_id = input["work_id"]
    updates = {}

    # Build updates
    if "is_active" in input:
        updates["schedule_enabled"] = input["is_active"]

    if "task" in input:
        updates["task"] = input["task"]

    if "frequency" in input:
        frequency = input["frequency"]
        if frequency.lower() == "once":
            # Converting to one-time work
            updates["schedule_cron"] = None
            updates["schedule_enabled"] = False
            updates["schedule_next_run_at"] = None
        else:
            cron_expr = parse_schedule_to_cron(frequency)
            updates["schedule_cron"] = cron_expr

            # Get current timezone
            try:
                work_result = auth.client.table("work_tickets")\
                    .select("schedule_timezone")\
                    .eq("id", work_id)\
                    .eq("user_id", auth.user_id)\
                    .single()\
                    .execute()
            except Exception:
                work_result = None

            if work_result and work_result.data:
                tz = work_result.data.get("schedule_timezone", "UTC")
                try:
                    from jobs.work_scheduler import calculate_next_run
                    next_run = calculate_next_run(cron_expr, tz)
                    updates["schedule_next_run_at"] = next_run.isoformat()
                except Exception:
                    pass

    if not updates:
        return {
            "success": False,
            "error": "No updates provided"
        }

    # Apply updates
    result = auth.client.table("work_tickets")\
        .update(updates)\
        .eq("id", work_id)\
        .eq("user_id", auth.user_id)\
        .execute()

    if not result.data:
        return {
            "success": False,
            "error": "Work not found or access denied"
        }

    work = result.data[0]
    is_recurring = work.get("schedule_cron") is not None

    status_msg = []
    if "schedule_enabled" in updates:
        status_msg.append("paused" if not updates["schedule_enabled"] else "resumed")
    if "task" in updates:
        status_msg.append("task updated")
    if "schedule_cron" in updates:
        if updates["schedule_cron"]:
            status_msg.append(f"frequency changed to {cron_to_human(updates['schedule_cron'])}")
        else:
            status_msg.append("converted to one-time")

    return {
        "success": True,
        "work": {
            "id": work["id"],
            "task": work["task"],
            "is_recurring": is_recurring,
            "is_active": work.get("schedule_enabled", False) if is_recurring else None,
            "frequency": cron_to_human(work["schedule_cron"]) if is_recurring else "once",
            "next_run": work.get("schedule_next_run_at"),
        },
        "message": f"Work updated: {', '.join(status_msg)}"
    }


async def handle_delete_work(auth, input: dict) -> dict:
    """
    Delete work and all its outputs.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with work_id

    Returns:
        Dict confirming deletion
    """
    work_id = input["work_id"]

    # Verify ownership
    try:
        work_result = auth.client.table("work_tickets")\
            .select("id, task")\
            .eq("id", work_id)\
            .eq("user_id", auth.user_id)\
            .single()\
            .execute()
    except Exception:
        return {
            "success": False,
            "error": "Work not found or access denied"
        }

    if not work_result.data:
        return {
            "success": False,
            "error": "Work not found or access denied"
        }

    task = work_result.data["task"]

    # Delete outputs first (foreign key constraint)
    auth.client.table("work_outputs")\
        .delete()\
        .eq("ticket_id", work_id)\
        .execute()

    # Delete work
    auth.client.table("work_tickets")\
        .delete()\
        .eq("id", work_id)\
        .execute()

    return {
        "success": True,
        "message": f"Deleted work: {task[:50]}..."
    }


# =============================================================================
# Schedule Parsing Utilities
# =============================================================================

def parse_schedule_to_cron(schedule: str) -> str:
    """
    Convert human-readable schedule to cron expression.

    Examples:
    - "daily at 9am" -> "0 9 * * *"
    - "every Monday at 10am" -> "0 10 * * 1"
    - "every 6 hours" -> "0 */6 * * *"
    - "weekly on Friday at 3pm" -> "0 15 * * 5"
    """
    import re
    schedule = schedule.lower().strip()

    # "every X hours" pattern
    hours_match = re.search(r'every (\d+) hours?', schedule)
    if hours_match:
        hours = int(hours_match.group(1))
        return f"0 */{hours} * * *"

    # "every X minutes" pattern
    mins_match = re.search(r'every (\d+) minutes?', schedule)
    if mins_match:
        mins = int(mins_match.group(1))
        return f"*/{mins} * * * *"

    # Extract time (9am, 10:30am, 15:00, etc.)
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', schedule)
    hour = 9  # default
    minute = 0
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        meridian = time_match.group(3)
        if meridian == 'pm' and hour < 12:
            hour += 12
        elif meridian == 'am' and hour == 12:
            hour = 0

    # Day of week mapping
    day_map = {
        'sunday': 0, 'sun': 0,
        'monday': 1, 'mon': 1,
        'tuesday': 2, 'tue': 2,
        'wednesday': 3, 'wed': 3,
        'thursday': 4, 'thu': 4,
        'friday': 5, 'fri': 5,
        'saturday': 6, 'sat': 6,
    }

    # Check for specific day of week
    for day_name, day_num in day_map.items():
        if day_name in schedule:
            return f"{minute} {hour} * * {day_num}"

    # "daily" pattern
    if 'daily' in schedule or 'every day' in schedule:
        return f"{minute} {hour} * * *"

    # "weekly" without specific day defaults to Monday
    if 'weekly' in schedule:
        return f"{minute} {hour} * * 1"

    # "hourly" pattern
    if 'hourly' in schedule or 'every hour' in schedule:
        return f"0 * * * *"

    # Default: daily at specified time (or 9am)
    return f"{minute} {hour} * * *"


def cron_to_human(cron_expr: str) -> str:
    """Convert cron expression to human-readable format."""
    parts = cron_expr.split()
    if len(parts) != 5:
        return cron_expr

    minute, hour, dom, month, dow = parts

    days = {
        '0': 'Sunday', '1': 'Monday', '2': 'Tuesday',
        '3': 'Wednesday', '4': 'Thursday', '5': 'Friday', '6': 'Saturday'
    }

    # Every N minutes
    if minute.startswith('*/'):
        return f"Every {minute[2:]} minutes"

    # Every N hours
    if hour.startswith('*/'):
        return f"Every {hour[2:]} hours"

    # Specific day of week
    if dow != '*' and dow in days:
        h = int(hour)
        m = int(minute)
        ampm = 'AM' if h < 12 else 'PM'
        h12 = h if h <= 12 else h - 12
        h12 = 12 if h12 == 0 else h12
        time_str = f"{h12}:{m:02d} {ampm}" if m else f"{h12} {ampm}"
        return f"Weekly on {days[dow]} at {time_str}"

    # Daily
    if dow == '*' and dom == '*':
        h = int(hour)
        m = int(minute)
        ampm = 'AM' if h < 12 else 'PM'
        h12 = h if h <= 12 else h - 12
        h12 = 12 if h12 == 0 else h12
        time_str = f"{h12}:{m:02d} {ampm}" if m else f"{h12} {ampm}"
        return f"Daily at {time_str}"

    return cron_expr


# Registry mapping tool names to handlers
TOOL_HANDLERS: dict[str, ToolHandler] = {
    # Project tools (ADR-007)
    "list_projects": handle_list_projects,
    "create_project": handle_create_project,
    "rename_project": handle_rename_project,
    "update_project": handle_update_project,
    # Unified work tools (ADR-017)
    "create_work": handle_create_work,
    "list_work": handle_list_work,
    "get_work": handle_get_work,
    "update_work": handle_update_work,
    "delete_work": handle_delete_work,
    # Legacy aliases for backward compatibility (ADR-009 → ADR-017)
    "get_work_status": handle_get_work,  # Alias for get_work
    "cancel_work": handle_update_work,   # Use update_work with is_active=false
    "schedule_work": handle_create_work,  # Use create_work with frequency param
    "list_schedules": handle_list_work,   # Use list_work with active_only=true
    "update_schedule": handle_update_work,  # Use update_work
    "delete_schedule": handle_delete_work,  # Use delete_work
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
