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
    "description": """Create a work request for an agent to complete a task.

Use when the user asks you to research something, create content, or generate a report.

CONTEXT ROUTING (ADR-015):
- If user is in a project context, use that project_id
- If request clearly relates to an existing project, route it there
- If request is personal/one-off, omit project_id (creates ambient work)
- If request suggests new ongoing topic, you may suggest creating a project first

Ambient work (no project_id) is perfectly valid for one-off tasks.""",
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
                "description": "UUID of the project this work belongs to. Optional - omit for ambient/personal work."
            },
            "parameters": {
                "type": "object",
                "description": "Optional agent-specific parameters (e.g., depth, format, tone)"
            }
        },
        "required": ["task", "agent_type"]
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

CANCEL_WORK_TOOL = {
    "name": "cancel_work",
    "description": "Cancel a pending or running work request. Use when the user wants to stop work that hasn't completed yet.",
    "input_schema": {
        "type": "object",
        "properties": {
            "work_id": {
                "type": "string",
                "description": "UUID of the work request to cancel"
            }
        },
        "required": ["work_id"]
    }
}


# =============================================================================
# Scheduling Tools (ADR-009 Phase 3)
# =============================================================================

SCHEDULE_WORK_TOOL = {
    "name": "schedule_work",
    "description": "Schedule recurring work to run automatically. Use when the user wants regular reports, research updates, or content generation. Common schedules: 'daily at 9am', 'weekly on Mondays', 'every hour'.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Clear description of what needs to be done on each run"
            },
            "agent_type": {
                "type": "string",
                "enum": ["research", "content", "reporting"],
                "description": "Type of agent: 'research' for investigation/analysis, 'content' for writing/drafts, 'reporting' for summaries/reports"
            },
            "project_id": {
                "type": "string",
                "description": "UUID of the project this work belongs to"
            },
            "schedule": {
                "type": "string",
                "description": "Human-readable schedule like 'daily at 9am', 'every Monday at 10am', 'every 6 hours'. Will be converted to cron."
            },
            "timezone": {
                "type": "string",
                "description": "User's timezone, e.g., 'America/Los_Angeles', 'Europe/London'. Default: 'UTC'"
            },
            "parameters": {
                "type": "object",
                "description": "Optional agent-specific parameters"
            }
        },
        "required": ["task", "agent_type", "project_id", "schedule"]
    }
}

LIST_SCHEDULES_TOOL = {
    "name": "list_schedules",
    "description": "List scheduled work templates for the user. Shows what recurring work is set up and when it will next run.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_id": {
                "type": "string",
                "description": "Optional: Filter to a specific project"
            }
        },
        "required": []
    }
}

UPDATE_SCHEDULE_TOOL = {
    "name": "update_schedule",
    "description": "Update or pause/resume a scheduled work template.",
    "input_schema": {
        "type": "object",
        "properties": {
            "schedule_id": {
                "type": "string",
                "description": "UUID of the schedule (work template) to update"
            },
            "enabled": {
                "type": "boolean",
                "description": "Set to false to pause, true to resume"
            },
            "schedule": {
                "type": "string",
                "description": "New schedule (human-readable, will be converted to cron)"
            },
            "task": {
                "type": "string",
                "description": "Updated task description"
            }
        },
        "required": ["schedule_id"]
    }
}

DELETE_SCHEDULE_TOOL = {
    "name": "delete_schedule",
    "description": "Delete a scheduled work template. This stops all future runs.",
    "input_schema": {
        "type": "object",
        "properties": {
            "schedule_id": {
                "type": "string",
                "description": "UUID of the schedule to delete"
            }
        },
        "required": ["schedule_id"]
    }
}


# Tools available to Thinking Partner
THINKING_PARTNER_TOOLS = [
    # Project management (ADR-007)
    LIST_PROJECTS_TOOL,
    CREATE_PROJECT_TOOL,
    RENAME_PROJECT_TOOL,
    UPDATE_PROJECT_TOOL,
    # Work management (ADR-009, ADR-016)
    CREATE_WORK_TOOL,
    LIST_WORK_TOOL,
    GET_WORK_STATUS_TOOL,
    CANCEL_WORK_TOOL,
    # Scheduling (ADR-009 Phase 3)
    SCHEDULE_WORK_TOOL,
    LIST_SCHEDULES_TOOL,
    UPDATE_SCHEDULE_TOOL,
    DELETE_SCHEDULE_TOOL,
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

    ADR-015: Supports ambient work (no project_id).

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with task, agent_type, optional project_id, and optional parameters

    Returns:
        Dict with work execution results including outputs
    """
    import logging
    from services.work_execution import execute_work_ticket
    from jobs.email import send_work_complete_email

    logger = logging.getLogger(__name__)

    task = input["task"]
    agent_type = input["agent_type"]
    project_id = input.get("project_id")  # Optional - None for ambient work
    parameters = input.get("parameters", {})

    # Validate agent_type
    valid_agent_types = ["research", "content", "reporting"]
    if agent_type not in valid_agent_types:
        return {
            "success": False,
            "error": f"Invalid agent_type. Must be one of: {', '.join(valid_agent_types)}"
        }

    # Create work ticket
    # ADR-015: Include user_id for ambient work (required when project_id is NULL)
    ticket_data = {
        "task": task,
        "agent_type": agent_type,
        "parameters": parameters,
        "status": "pending",
        "user_id": auth.user_id,  # Always set for RLS
    }
    if project_id:
        ticket_data["project_id"] = project_id

    result = auth.client.table("work_tickets").insert(ticket_data).execute()

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

    # ADR-016: Format single output for TP response
    output = execution_result.get("output")
    output_summary = None

    if output:
        # Get preview of content (first 200 chars)
        content = output.get("content", "")
        preview = content[:200] + "..." if len(content) > 200 else content

        output_summary = {
            "id": output.get("id"),
            "title": output.get("title"),
            "preview": preview,
            "metadata": output.get("metadata", {}),
        }

    # Backward compat: keep outputs list format
    output_summaries = [output_summary] if output_summary else []

    # Send email notification if user has email
    email_sent = False
    if auth.email and output_summaries:
        try:
            # Get project name for email (or "Personal Work" for ambient)
            project_name = "Personal Work"
            if project_id:
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

    # ADR-016: TP should be brief when work completes
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
        "output": output_summary,  # ADR-016: single output
        "outputs": output_summaries,  # Backward compat
        "output_count": 1 if output_summary else 0,
        "email_sent": email_sent,
        "message": f"Work complete. Output available in the output panel.",
        # ADR-016: TP should keep response brief and reference output
        "instruction_to_assistant": "Keep your response brief (1-2 sentences). Acknowledge the work is done and direct the user to the output panel. Do NOT duplicate the output content in your response.",
        # ADR-013: UI action to open output surface with completed work
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "output",
            "data": {
                "ticketId": ticket_id,
                "projectId": project_id,
            }
        }
    }


async def handle_list_work(auth, input: dict) -> dict:
    """
    List work requests, optionally filtered by project and status.

    ADR-015: Includes ambient work (project_id IS NULL) when no project filter.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with optional project_id, status, and limit

    Returns:
        Dict with work requests list
    """
    project_id = input.get("project_id")
    status_filter = input.get("status", "all")
    limit = input.get("limit", 10)

    # Build query - RLS handles access control
    # ADR-015: Query includes both project work and ambient work
    query = auth.client.table("work_tickets")\
        .select("id, task, agent_type, status, project_id, user_id, created_at, started_at, completed_at, projects(name)")\
        .eq("is_template", False)\
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
        # ADR-015: Show "Personal" for ambient work
        if t.get("project_id"):
            project_name = t.get("projects", {}).get("name", "Unknown") if t.get("projects") else "Unknown"
        else:
            project_name = "Personal"

        work_items.append({
            "id": t["id"],
            "task": t["task"][:100] + "..." if len(t["task"]) > 100 else t["task"],
            "agent_type": t["agent_type"],
            "status": t["status"],
            "project_name": project_name,
            "is_ambient": t.get("project_id") is None,
            "created_at": t["created_at"],
        })

    return {
        "success": True,
        "work": work_items,
        "count": len(work_items),
        "message": f"Found {len(work_items)} work request(s)"
    }


async def handle_cancel_work(auth, input: dict) -> dict:
    """
    Cancel a pending or running work request.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with work_id

    Returns:
        Dict confirming cancellation
    """
    from datetime import datetime, timezone

    work_id = input["work_id"]

    # Get current status
    ticket_result = auth.client.table("work_tickets")\
        .select("id, status, task")\
        .eq("id", work_id)\
        .single()\
        .execute()

    if not ticket_result.data:
        return {
            "success": False,
            "error": "Work request not found or access denied"
        }

    ticket = ticket_result.data
    current_status = ticket["status"]

    # Can only cancel pending or running work
    if current_status not in ["pending", "running"]:
        return {
            "success": False,
            "error": f"Cannot cancel work with status '{current_status}'. Only pending or running work can be cancelled."
        }

    # Update to cancelled
    auth.client.table("work_tickets").update({
        "status": "cancelled",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "error_message": "Cancelled by user"
    }).eq("id", work_id).execute()

    return {
        "success": True,
        "work_id": work_id,
        "previous_status": current_status,
        "message": f"Cancelled work request: {ticket['task'][:50]}..."
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


# =============================================================================
# Scheduling Tool Handlers (ADR-009 Phase 3)
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


async def handle_schedule_work(auth, input: dict) -> dict:
    """
    Create a scheduled work template.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with task, agent_type, project_id, schedule, timezone

    Returns:
        Dict with created schedule details
    """
    from datetime import datetime, timezone as tz
    from jobs.work_scheduler import calculate_next_run

    task = input["task"]
    agent_type = input["agent_type"]
    project_id = input["project_id"]
    schedule = input["schedule"]
    user_timezone = input.get("timezone", "UTC")
    parameters = input.get("parameters", {})

    # Validate agent type
    valid_types = ["research", "content", "reporting"]
    if agent_type not in valid_types:
        return {
            "success": False,
            "error": f"Invalid agent_type. Must be one of: {', '.join(valid_types)}"
        }

    # Convert schedule to cron
    cron_expr = parse_schedule_to_cron(schedule)

    # Calculate first run time
    try:
        next_run = calculate_next_run(cron_expr, user_timezone)
    except Exception as e:
        return {
            "success": False,
            "error": f"Invalid schedule: {e}"
        }

    # Create template ticket
    result = auth.client.table("work_tickets").insert({
        "task": task,
        "agent_type": agent_type,
        "project_id": project_id,
        "user_id": auth.user_id,
        "parameters": parameters,
        "status": "pending",  # Templates stay pending
        "is_template": True,
        "schedule_cron": cron_expr,
        "schedule_timezone": user_timezone,
        "schedule_enabled": True,
        "schedule_next_run_at": next_run.isoformat(),
    }).execute()

    if not result.data:
        return {
            "success": False,
            "error": "Failed to create scheduled work"
        }

    template = result.data[0]
    human_schedule = cron_to_human(cron_expr)

    return {
        "success": True,
        "schedule": {
            "id": template["id"],
            "task": task,
            "agent_type": agent_type,
            "schedule": human_schedule,
            "cron": cron_expr,
            "timezone": user_timezone,
            "next_run": next_run.isoformat(),
            "enabled": True,
        },
        "message": f"Scheduled {agent_type} work: {human_schedule}. First run: {next_run.strftime('%Y-%m-%d %H:%M %Z')}"
    }


async def handle_list_schedules(auth, input: dict) -> dict:
    """
    List scheduled work templates for the user.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with optional project_id

    Returns:
        Dict with schedules list
    """
    project_id = input.get("project_id")

    # Query templates
    query = auth.client.table("work_tickets")\
        .select("id, task, agent_type, project_id, schedule_cron, schedule_timezone, schedule_enabled, schedule_next_run_at, schedule_last_run_at, projects(name)")\
        .eq("is_template", True)\
        .eq("user_id", auth.user_id)\
        .order("created_at", desc=True)

    if project_id:
        query = query.eq("project_id", project_id)

    result = query.execute()
    templates = result.data or []

    schedules = []
    for t in templates:
        project_name = t.get("projects", {}).get("name", "Unknown") if t.get("projects") else "Unknown"
        human_schedule = cron_to_human(t["schedule_cron"]) if t.get("schedule_cron") else "Unknown"

        schedules.append({
            "id": t["id"],
            "task": t["task"][:100] + "..." if len(t["task"]) > 100 else t["task"],
            "agent_type": t["agent_type"],
            "project_name": project_name,
            "schedule": human_schedule,
            "cron": t.get("schedule_cron"),
            "timezone": t.get("schedule_timezone", "UTC"),
            "enabled": t.get("schedule_enabled", True),
            "next_run": t.get("schedule_next_run_at"),
            "last_run": t.get("schedule_last_run_at"),
        })

    return {
        "success": True,
        "schedules": schedules,
        "count": len(schedules),
        "message": f"Found {len(schedules)} scheduled work item(s)"
    }


async def handle_update_schedule(auth, input: dict) -> dict:
    """
    Update a scheduled work template.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with schedule_id and optional updates

    Returns:
        Dict with updated schedule details
    """
    from jobs.work_scheduler import calculate_next_run

    schedule_id = input["schedule_id"]
    updates = {}

    # Check what's being updated
    if "enabled" in input:
        updates["schedule_enabled"] = input["enabled"]

    if "task" in input:
        updates["task"] = input["task"]

    if "schedule" in input:
        cron_expr = parse_schedule_to_cron(input["schedule"])
        updates["schedule_cron"] = cron_expr

        # Recalculate next run
        # Get current timezone from template
        template_result = auth.client.table("work_tickets")\
            .select("schedule_timezone")\
            .eq("id", schedule_id)\
            .eq("is_template", True)\
            .single()\
            .execute()

        if template_result.data:
            tz = template_result.data.get("schedule_timezone", "UTC")
            try:
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
        .eq("id", schedule_id)\
        .eq("is_template", True)\
        .eq("user_id", auth.user_id)\
        .execute()

    if not result.data:
        return {
            "success": False,
            "error": "Schedule not found or access denied"
        }

    template = result.data[0]
    human_schedule = cron_to_human(template.get("schedule_cron", "")) if template.get("schedule_cron") else "Unknown"

    status_msg = "paused" if not template.get("schedule_enabled") else "active"

    return {
        "success": True,
        "schedule": {
            "id": template["id"],
            "task": template["task"],
            "schedule": human_schedule,
            "enabled": template.get("schedule_enabled", True),
            "next_run": template.get("schedule_next_run_at"),
        },
        "message": f"Schedule updated ({status_msg})"
    }


async def handle_delete_schedule(auth, input: dict) -> dict:
    """
    Delete a scheduled work template.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with schedule_id

    Returns:
        Dict confirming deletion
    """
    schedule_id = input["schedule_id"]

    # Verify it's a template and belongs to user
    check_result = auth.client.table("work_tickets")\
        .select("id, task")\
        .eq("id", schedule_id)\
        .eq("is_template", True)\
        .eq("user_id", auth.user_id)\
        .single()\
        .execute()

    if not check_result.data:
        return {
            "success": False,
            "error": "Schedule not found or access denied"
        }

    task = check_result.data["task"]

    # Delete the template
    auth.client.table("work_tickets")\
        .delete()\
        .eq("id", schedule_id)\
        .execute()

    return {
        "success": True,
        "message": f"Deleted scheduled work: {task[:50]}..."
    }


# Registry mapping tool names to handlers
TOOL_HANDLERS: dict[str, ToolHandler] = {
    # Project tools (ADR-007)
    "list_projects": handle_list_projects,
    "create_project": handle_create_project,
    "rename_project": handle_rename_project,
    "update_project": handle_update_project,
    # Work tools (ADR-009, ADR-016)
    "create_work": handle_create_work,
    "list_work": handle_list_work,
    "get_work_status": handle_get_work_status,
    "cancel_work": handle_cancel_work,
    # Scheduling tools (ADR-009 Phase 3)
    "schedule_work": handle_schedule_work,
    "list_schedules": handle_list_schedules,
    "update_schedule": handle_update_schedule,
    "delete_schedule": handle_delete_schedule,
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
