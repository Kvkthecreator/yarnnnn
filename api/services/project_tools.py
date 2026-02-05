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


# =============================================================================
# Memory Tools (ADR-023 Supervisor Desk Architecture)
# =============================================================================

LIST_MEMORIES_TOOL = {
    "name": "list_memories",
    "description": """List user's memories (context) with optional filtering.

ADR-023: Memory tools allow TP to help users manage their context.

Use this to help users see what context/memories they have stored.
Memories can be scoped to user-level (global) or project-level.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["user", "project"],
                "description": "Filter by scope: 'user' for global memories, 'project' for project-specific. Default: show all."
            },
            "project_id": {
                "type": "string",
                "description": "Filter to specific project's memories. Only used if scope='project'."
            },
            "tag": {
                "type": "string",
                "description": "Filter by tag (e.g., 'preference', 'fact', 'instruction')."
            },
            "search": {
                "type": "string",
                "description": "Search memories by content."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results. Default: 20"
            }
        },
        "required": []
    }
}

CREATE_MEMORY_TOOL = {
    "name": "create_memory",
    "description": """Create a new memory (context) for the user.

ADR-023: Use this to store important context that should persist across sessions.
ADR-024: Memory Routing - ALWAYS determine the appropriate scope before creating.

MEMORY ROUTING (decide scope first):
- User-scoped (project_id omitted): Facts about the user that apply everywhere
  - Communication preferences ("prefers bullet points over prose")
  - Business facts ("works at Acme Corp", "10 years in fintech")
  - Domain expertise ("expert in machine learning")
  - Work patterns ("likes morning meetings")

- Project-scoped (project_id provided): Information specific to one initiative
  - Requirements ("report needs 3 sections")
  - Deadlines ("due Tuesday to Sarah")
  - Client details ("client prefers formal tone")
  - Task-specific context

ROUTING RULES:
1. Default to project-scoped if user is in a project context
2. If content clearly applies across all work, use user-scoped
3. When uncertain, ask the user: "Should I save this to your personal context or to [Project Name]?"
4. ALWAYS state your routing decision when creating memory

TAG SUGGESTIONS:
- 'preference': User preferences and settings
- 'fact': Facts about user, company, or domain
- 'instruction': How to help the user
- 'context': Background context
- 'goal': User's goals or objectives""",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The memory content to store"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags to categorize this memory (e.g., ['preference', 'communication'])"
            },
            "project_id": {
                "type": "string",
                "description": "Link to a project for project-scoped context. Omit for user-scoped (personal) context that applies everywhere."
            }
        },
        "required": ["content"]
    }
}

UPDATE_MEMORY_TOOL = {
    "name": "update_memory",
    "description": """Update an existing memory.

Use this to modify or refine stored context when the user provides corrections
or when information becomes outdated.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "memory_id": {
                "type": "string",
                "description": "UUID of the memory to update"
            },
            "content": {
                "type": "string",
                "description": "New content for the memory"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Updated tags for the memory"
            }
        },
        "required": ["memory_id"]
    }
}

DELETE_MEMORY_TOOL = {
    "name": "delete_memory",
    "description": """Delete a memory.

Use this when the user wants to remove stored context or when context is no longer relevant.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "memory_id": {
                "type": "string",
                "description": "UUID of the memory to delete"
            }
        },
        "required": ["memory_id"]
    }
}


SUGGEST_PROJECT_FOR_MEMORY_TOOL = {
    "name": "suggest_project_for_memory",
    "description": """ADR-024: Suggest which project a memory belongs to based on content.

Use this when you need to determine where extracted context should be stored.
This tool analyzes the content and compares it against existing projects.

Returns a suggestion with confidence score:
- High confidence (>0.7): Content clearly relates to an existing project
- Medium confidence (0.4-0.7): Content may relate to a project
- Low confidence (<0.4): Content is likely user-level (personal)

After getting a suggestion, you can:
1. Use create_memory with the suggested project_id
2. Ask the user to confirm if confidence is medium
3. Store as user-scoped if no good project match""",
    "input_schema": {
        "type": "object",
        "properties": {
            "memory_content": {
                "type": "string",
                "description": "The content to analyze for project routing"
            }
        },
        "required": ["memory_content"]
    }
}


# =============================================================================
# Todo Tracking Tool (ADR-025 Claude Code Alignment)
# =============================================================================

TODO_WRITE_TOOL = {
    "name": "todo_write",
    "description": """Track and update task progress for multi-step work.

ADR-025: Claude Code Agentic Alignment - Use this for visibility and accountability.

Use this when:
- Setting up a new deliverable (multiple steps involved)
- Executing a complex user request
- Any work requiring 3+ steps

Task states:
- pending: Not yet started
- in_progress: Currently working on (only ONE at a time)
- completed: Finished successfully

Always:
- Create todos at the start of multi-step work
- Update status as you progress
- Mark complete immediately when done (don't batch)
- Include both content (imperative: "Gather details") and activeForm (present continuous: "Gathering details")
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Task description in imperative form (e.g., 'Gather details')"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"]
                        },
                        "activeForm": {
                            "type": "string",
                            "description": "Task description in present continuous (e.g., 'Gathering details')"
                        }
                    },
                    "required": ["content", "status"]
                }
            }
        },
        "required": ["todos"]
    }
}


# =============================================================================
# Communication Tools (ADR-023 Unified Tool Model)
# =============================================================================

RESPOND_TOOL = {
    "name": "respond",
    "description": """Send a conversational response to the user.

Use this tool when you need to communicate through text - explanations, answers,
thinking through ideas, or any message that doesn't require navigation or action.

This is an EXPLICIT choice - you're deciding that conversation is the right response.
The message will appear in the chat interface.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to send to the user"
            }
        },
        "required": ["message"]
    }
}

CLARIFY_TOOL = {
    "name": "clarify",
    "description": """Ask the user for clarification or input before proceeding.

Use this when you need more information to complete a task, or when offering
choices that the user should decide between. Appears as a focused modal/prompt.

Examples:
- "Which project should I add this to?" with options
- "Do you want the detailed or summary version?"
- "What timeframe should I use for the analysis?" """,
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask the user"
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices to present (if applicable)"
            }
        },
        "required": ["question"]
    }
}


# =============================================================================
# Deliverable Tools (ADR-018 Recurring Deliverables)
# =============================================================================

LIST_DELIVERABLES_TOOL = {
    "name": "list_deliverables",
    "description": """List the user's recurring deliverables.

ADR-018: Recurring Deliverables - scheduled reports, updates, and documents.

Shows all deliverables with their status, schedule, and latest version state.
Use this to help users see what deliverables they have set up.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["active", "paused", "archived"],
                "description": "Filter by status. Default: show all non-archived."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results. Default: 10"
            }
        },
        "required": []
    }
}

GET_DELIVERABLE_TOOL = {
    "name": "get_deliverable",
    "description": """Get detailed information about a specific deliverable.

Returns the deliverable configuration, recent versions, and their status.
Use this when the user asks about a specific deliverable.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "deliverable_id": {
                "type": "string",
                "description": "UUID of the deliverable"
            }
        },
        "required": ["deliverable_id"]
    }
}

RUN_DELIVERABLE_TOOL = {
    "name": "run_deliverable",
    "description": """Trigger an ad-hoc run of a deliverable.

Creates a new version and starts the generation pipeline.
Use when the user wants to generate their deliverable now instead of waiting for the schedule.

IMPORTANT: After triggering, the deliverable will be in "Generating" state.
Direct the user to the deliverables dashboard to review once ready.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "deliverable_id": {
                "type": "string",
                "description": "UUID of the deliverable to run"
            }
        },
        "required": ["deliverable_id"]
    }
}

UPDATE_DELIVERABLE_TOOL = {
    "name": "update_deliverable",
    "description": """Update a deliverable's settings (pause, resume, change schedule).

Use this to:
- Pause a deliverable (status="paused")
- Resume a paused deliverable (status="active")
- Archive a deliverable (status="archived")

Note: For complex config changes, direct users to the deliverables dashboard.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "deliverable_id": {
                "type": "string",
                "description": "UUID of the deliverable"
            },
            "status": {
                "type": "string",
                "enum": ["active", "paused", "archived"],
                "description": "New status for the deliverable"
            },
            "title": {
                "type": "string",
                "description": "New title for the deliverable"
            }
        },
        "required": ["deliverable_id"]
    }
}

CREATE_DELIVERABLE_TOOL = {
    "name": "create_deliverable",
    "description": """Create a new recurring deliverable for the user.

**CRITICAL: Use the EXACT parameters the user specified!**
- If user said "monthly" → frequency MUST be "monthly"
- If user said "board update" → type should be "stakeholder_update" or "board_update"
- If user said it's for "Marcus" → recipient_name MUST be "Marcus"

**Before calling this tool, you MUST have:**
1. Parsed the user's request to extract: title, frequency, type, recipient
2. Confirmed your understanding with the user
3. Received confirmation ("yes", "sounds good", etc.)

**Never create with defaults that contradict what the user said!**

**TYPES:**
- status_report: Regular progress/status updates (for managers, teams)
- stakeholder_update: Updates for clients, investors, board members
- research_brief: Competitive intel, market research, trends
- meeting_summary: Recap of recurring meetings
- custom: Anything else

Returns the created deliverable. Always follow with respond() to:
1. Confirm creation with the actual parameters used
2. State what context will be used for generation
3. Offer to generate first draft""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Name of the deliverable (e.g., 'Weekly Status Report', 'Q1 Board Update')"
            },
            "deliverable_type": {
                "type": "string",
                "enum": ["status_report", "stakeholder_update", "research_brief", "meeting_summary", "custom"],
                "description": "Type of deliverable - determines generation strategy"
            },
            "frequency": {
                "type": "string",
                "enum": ["daily", "weekly", "biweekly", "monthly"],
                "description": "How often to generate. Default: weekly"
            },
            "day": {
                "type": "string",
                "description": "Day for generation. For weekly: monday-sunday. For monthly: 1-28. Drafts are ready for review."
            },
            "time": {
                "type": "string",
                "description": "Time to generate (24h format, e.g., '09:00'). Default: 09:00"
            },
            "recipient_name": {
                "type": "string",
                "description": "Who this deliverable is for (e.g., 'Sarah Chen', 'Leadership Team')"
            },
            "recipient_relationship": {
                "type": "string",
                "description": "Relationship to recipient (e.g., 'manager', 'client', 'board')"
            },
            "description": {
                "type": "string",
                "description": "Brief description of what this deliverable should cover"
            },
            "project_id": {
                "type": "string",
                "description": "Optional: Link to an existing project for context"
            }
        },
        "required": ["title", "deliverable_type"]
    }
}


# Tools available to Thinking Partner (ADR-023 Unified Tool Model)
# All outputs are tools - including conversation itself
THINKING_PARTNER_TOOLS = [
    # Communication (conversation as explicit tool choice)
    RESPOND_TOOL,
    CLARIFY_TOOL,
    # Progress tracking (ADR-025 Claude Code Alignment)
    TODO_WRITE_TOOL,
    # Navigation (open surfaces to show data)
    LIST_PROJECTS_TOOL,
    LIST_MEMORIES_TOOL,
    LIST_DELIVERABLES_TOOL,
    LIST_WORK_TOOL,
    GET_DELIVERABLE_TOOL,
    GET_WORK_TOOL,
    # Actions (CRUD operations)
    CREATE_PROJECT_TOOL,
    RENAME_PROJECT_TOOL,
    UPDATE_PROJECT_TOOL,
    CREATE_WORK_TOOL,
    UPDATE_WORK_TOOL,
    DELETE_WORK_TOOL,
    CREATE_MEMORY_TOOL,
    UPDATE_MEMORY_TOOL,
    DELETE_MEMORY_TOOL,
    SUGGEST_PROJECT_FOR_MEMORY_TOOL,  # ADR-024: Memory routing
    RUN_DELIVERABLE_TOOL,
    UPDATE_DELIVERABLE_TOOL,
    CREATE_DELIVERABLE_TOOL,
]


# =============================================================================
# Tool Handlers
# =============================================================================

# -----------------------------------------------------------------------------
# Communication Handlers (ADR-023)
# -----------------------------------------------------------------------------

async def handle_respond(auth, input: dict) -> dict:
    """
    Handle conversational response.

    The message is passed through to the UI which displays it in the chat.
    This makes conversation an explicit tool choice rather than a default.
    """
    message = input.get("message", "")

    return {
        "success": True,
        "message": message,
        "ui_action": {
            "type": "RESPOND",
            "data": {"message": message}
        }
    }


async def handle_clarify(auth, input: dict) -> dict:
    """
    Handle clarification request.

    Presents a focused question to the user, optionally with choices.
    UI displays this as a modal/prompt for focused input.
    """
    question = input.get("question", "")
    options = input.get("options", [])

    return {
        "success": True,
        "question": question,
        "options": options,
        "ui_action": {
            "type": "CLARIFY",
            "data": {
                "question": question,
                "options": options
            }
        }
    }


# -----------------------------------------------------------------------------
# Todo Tracking Handler (ADR-025 Claude Code Alignment)
# -----------------------------------------------------------------------------

async def handle_todo_write(auth, input: dict) -> dict:
    """
    Handle todo tracking for multi-step work.

    ADR-025: Todos are ephemeral (session-scoped), not persisted to database.
    The frontend displays them via ui_action and clears on session end.

    This tool provides visibility into TP's work process, enabling:
    - User to see progress through multi-step workflows
    - Audit trail of what TP planned vs executed
    - Trust building through transparency
    """
    todos = input.get("todos", [])

    # Return todos in ui_action for frontend to display
    return {
        "success": True,
        "todos": todos,
        "message": f"Tracking {len(todos)} tasks",
        "ui_action": {
            "type": "UPDATE_TODOS",
            "data": {
                "todos": todos
            }
        }
    }


# -----------------------------------------------------------------------------
# Project Handlers
# -----------------------------------------------------------------------------

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
        "message": f"Found {len(projects)} project(s)" if projects else "No projects yet",
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "project-list",
            "data": {}
        }
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
        "message": f"Found {len(work_items)} work item(s)",
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "work-list",
            "data": {}
        }
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
        "message": f"Work has {len(outputs)} output(s)",
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "work-output",
            "data": {"workId": work_id}
        }
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


# =============================================================================
# Deliverable Tool Handlers (ADR-018)
# =============================================================================

async def handle_list_deliverables(auth, input: dict) -> dict:
    """
    List user's recurring deliverables.

    ADR-018: Recurring Deliverables with scheduling.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with optional status and limit

    Returns:
        Dict with deliverables list
    """
    status_filter = input.get("status")
    limit = input.get("limit", 10)

    # Build query
    query = auth.client.table("deliverables")\
        .select("id, title, deliverable_type, status, schedule, next_run_at, last_run_at, created_at, deliverable_versions(id, status, version_number)")\
        .eq("user_id", auth.user_id)\
        .order("created_at", desc=True)\
        .limit(limit)

    if status_filter:
        query = query.eq("status", status_filter)
    else:
        # Exclude archived by default
        query = query.neq("status", "archived")

    result = query.execute()
    deliverables = result.data or []

    # Format for display
    items = []
    for d in deliverables:
        versions = d.get("deliverable_versions", [])
        latest = max(versions, key=lambda v: v["version_number"]) if versions else None

        # Human-readable schedule
        schedule = d.get("schedule", {})
        schedule_desc = format_schedule_description(schedule)

        items.append({
            "id": d["id"],
            "title": d["title"],
            "type": d.get("deliverable_type", "custom").replace("_", " ").title(),
            "status": d["status"],
            "schedule": schedule_desc,
            "next_run": d.get("next_run_at"),
            "version_count": len(versions),
            "latest_version_status": latest["status"] if latest else None,
        })

    return {
        "success": True,
        "deliverables": items,
        "count": len(items),
        "message": f"Found {len(items)} deliverable(s)" if items else "No deliverables yet. Would you like to create one?",
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "deliverable-list",
            "data": {}
        }
    }


async def handle_get_deliverable(auth, input: dict) -> dict:
    """
    Get detailed information about a deliverable.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with deliverable_id

    Returns:
        Dict with deliverable details and versions
    """
    deliverable_id = input["deliverable_id"]

    # Get deliverable with versions
    try:
        result = auth.client.table("deliverables")\
            .select("*, deliverable_versions(id, version_number, status, created_at, staged_at, approved_at)")\
            .eq("id", deliverable_id)\
            .eq("user_id", auth.user_id)\
            .single()\
            .execute()
    except Exception:
        return {
            "success": False,
            "error": "Deliverable not found or access denied"
        }

    if not result.data:
        return {
            "success": False,
            "error": "Deliverable not found"
        }

    d = result.data
    versions = d.get("deliverable_versions", [])
    versions_sorted = sorted(versions, key=lambda v: v["version_number"], reverse=True)

    # Human-readable schedule
    schedule = d.get("schedule", {})
    schedule_desc = format_schedule_description(schedule)

    # Format type config summary
    type_config = d.get("type_config", {})
    config_summary = summarize_type_config(d.get("deliverable_type", "custom"), type_config)

    return {
        "success": True,
        "deliverable": {
            "id": d["id"],
            "title": d["title"],
            "type": d.get("deliverable_type", "custom").replace("_", " ").title(),
            "status": d["status"],
            "schedule": schedule_desc,
            "next_run": d.get("next_run_at"),
            "last_run": d.get("last_run_at"),
            "config_summary": config_summary,
            "created_at": d["created_at"],
        },
        "versions": [
            {
                "version_number": v["version_number"],
                "status": v["status"],
                "created_at": v["created_at"],
            }
            for v in versions_sorted[:5]  # Last 5 versions
        ],
        "version_count": len(versions),
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "deliverable",
            "data": {"deliverableId": deliverable_id}
        }
    }


async def handle_run_deliverable(auth, input: dict) -> dict:
    """
    Trigger an ad-hoc run of a deliverable.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with deliverable_id

    Returns:
        Dict with run result
    """
    import logging
    from services.deliverable_pipeline import execute_deliverable_pipeline

    logger = logging.getLogger(__name__)
    deliverable_id = input["deliverable_id"]

    # Get deliverable
    try:
        result = auth.client.table("deliverables")\
            .select("id, title, status, deliverable_versions(version_number)")\
            .eq("id", deliverable_id)\
            .eq("user_id", auth.user_id)\
            .single()\
            .execute()
    except Exception:
        return {
            "success": False,
            "error": "Deliverable not found or access denied"
        }

    if not result.data:
        return {
            "success": False,
            "error": "Deliverable not found"
        }

    deliverable = result.data

    if deliverable["status"] == "archived":
        return {
            "success": False,
            "error": "Cannot run archived deliverable"
        }

    # Calculate next version number
    versions = deliverable.get("deliverable_versions", [])
    next_version = 1
    if versions:
        max_version = max(v["version_number"] for v in versions)
        next_version = max_version + 1

    logger.info(f"[TP-TOOL] Triggering deliverable run: {deliverable_id} v{next_version}")

    # Execute pipeline
    pipeline_result = await execute_deliverable_pipeline(
        client=auth.client,
        user_id=auth.user_id,
        deliverable_id=deliverable_id,
        version_number=next_version,
    )

    if pipeline_result.get("success"):
        return {
            "success": True,
            "deliverable_id": deliverable_id,
            "version_number": next_version,
            "message": f"Started generating '{deliverable['title']}' v{next_version}. Check the deliverables dashboard for the result.",
            "ui_action": {
                "type": "OPEN_SURFACE",
                "surface": "deliverable",
                "data": {"deliverableId": deliverable_id}
            },
            "instruction_to_assistant": "Let the user know their deliverable is being generated. Direct them to the deliverables dashboard to review once ready."
        }
    else:
        return {
            "success": False,
            "error": pipeline_result.get("message", "Failed to start generation"),
        }


async def handle_update_deliverable(auth, input: dict) -> dict:
    """
    Update a deliverable's settings.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with deliverable_id and updates

    Returns:
        Dict with update result
    """
    from datetime import datetime

    deliverable_id = input["deliverable_id"]
    updates = {}

    if "status" in input:
        updates["status"] = input["status"]

    if "title" in input:
        updates["title"] = input["title"]

    if not updates:
        return {
            "success": False,
            "error": "No updates provided"
        }

    updates["updated_at"] = datetime.utcnow().isoformat()

    # Apply update
    result = auth.client.table("deliverables")\
        .update(updates)\
        .eq("id", deliverable_id)\
        .eq("user_id", auth.user_id)\
        .execute()

    if not result.data:
        return {
            "success": False,
            "error": "Deliverable not found or access denied"
        }

    d = result.data[0]

    # Build status message
    status_msg = []
    if "status" in updates:
        if updates["status"] == "paused":
            status_msg.append("paused")
        elif updates["status"] == "active":
            status_msg.append("resumed")
        elif updates["status"] == "archived":
            status_msg.append("archived")

    if "title" in updates:
        status_msg.append(f"renamed to '{updates['title']}'")

    return {
        "success": True,
        "deliverable": {
            "id": d["id"],
            "title": d["title"],
            "status": d["status"],
        },
        "message": f"Deliverable {', '.join(status_msg)}"
    }


async def handle_create_deliverable(auth, input: dict) -> dict:
    """
    Create a new recurring deliverable.

    ADR-020: TP can scaffold deliverables on behalf of users.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with deliverable configuration

    Returns:
        Dict with created deliverable details
    """
    from datetime import datetime
    from jobs.unified_scheduler import calculate_next_run_from_schedule

    title = input["title"]
    deliverable_type = input["deliverable_type"]
    frequency = input.get("frequency", "weekly")
    day = input.get("day")
    time = input.get("time", "09:00")
    recipient_name = input.get("recipient_name")
    recipient_relationship = input.get("recipient_relationship")
    description = input.get("description")
    project_id = input.get("project_id")

    # Default day based on frequency
    if not day:
        if frequency == "weekly":
            day = "monday"
        elif frequency == "monthly":
            day = "1"
        elif frequency == "biweekly":
            day = "monday"
        # daily doesn't need a day

    # Build schedule
    schedule = {
        "frequency": frequency,
        "time": time,
        "timezone": "America/Los_Angeles",  # Default, user can change in settings
    }
    if day:
        schedule["day"] = day

    # Build type config based on deliverable type
    type_config = {}
    if deliverable_type == "status_report":
        type_config = {
            "subject": description or title,
            "audience": recipient_relationship or "stakeholder",
            "format": "email",
        }
    elif deliverable_type == "stakeholder_update":
        type_config = {
            "audience_type": recipient_relationship or "client",
            "include_metrics": True,
        }
    elif deliverable_type == "research_brief":
        type_config = {
            "focus_area": "competitive",
            "subjects": [],
        }
    elif deliverable_type == "meeting_summary":
        type_config = {
            "meeting_type": "team_sync",
        }
    elif deliverable_type == "custom":
        type_config = {
            "description": description or title,
        }

    # Calculate next run time
    try:
        next_run = calculate_next_run_from_schedule(schedule)
    except Exception:
        # Fallback: next day at specified time
        from datetime import timedelta
        import pytz
        tz = pytz.timezone(schedule.get("timezone", "UTC"))
        now = datetime.now(tz)
        next_run = (now + timedelta(days=1)).replace(
            hour=int(time.split(":")[0]),
            minute=int(time.split(":")[1]) if ":" in time else 0,
            second=0,
            microsecond=0
        )

    # Build recipient context (JSONB field)
    recipient_context = {}
    if recipient_name:
        recipient_context["name"] = recipient_name
    if recipient_relationship:
        recipient_context["role"] = recipient_relationship

    # Build deliverable data
    deliverable_data = {
        "title": title,
        "deliverable_type": deliverable_type,
        "user_id": auth.user_id,
        "status": "active",
        "schedule": schedule,
        "type_config": type_config,
        "next_run_at": next_run.isoformat() if hasattr(next_run, 'isoformat') else str(next_run),
    }

    if recipient_context:
        deliverable_data["recipient_context"] = recipient_context
    if project_id:
        deliverable_data["project_id"] = project_id

    # Create deliverable
    result = auth.client.table("deliverables").insert(deliverable_data).execute()

    if not result.data:
        return {
            "success": False,
            "error": "Failed to create deliverable"
        }

    deliverable = result.data[0]

    # Format schedule for display
    schedule_desc = format_schedule_description(schedule)

    # Fetch context counts for Setup Confirmation modal
    user_memory_count = 0
    deliverable_memory_count = 0
    document_count = 0
    sample_memories = []

    try:
        # Count user-level memories (project_id IS NULL)
        user_mem_result = auth.client.table("memories").select("id, content", count="exact").is_("project_id", "null").execute()
        user_memory_count = user_mem_result.count or 0

        # Get sample user memories (first 3)
        if user_mem_result.data:
            sample_memories = [m["content"][:100] for m in user_mem_result.data[:3]]

        # Count deliverable-specific memories (if project_id provided)
        if project_id:
            deliv_mem_result = auth.client.table("memories").select("id", count="exact").eq("project_id", project_id).execute()
            deliverable_memory_count = deliv_mem_result.count or 0

            # Count documents for this project
            doc_result = auth.client.table("documents").select("id", count="exact").eq("project_id", project_id).execute()
            document_count = doc_result.count or 0
    except Exception:
        # If context fetch fails, continue with zeros - modal will still work
        pass

    return {
        "success": True,
        "deliverable": {
            "id": deliverable["id"],
            "title": title,
            "type": deliverable_type.replace("_", " ").title(),
            "schedule": schedule_desc,
            "next_run": deliverable.get("next_run_at"),
            "recipient": recipient_name,
        },
        "message": f"Created '{title}' - {schedule_desc}. First draft will be ready for review at your next scheduled time.",
        "ui_action": {
            "type": "SHOW_SETUP_CONFIRM",
            "data": {
                "deliverableId": deliverable["id"],
                "title": title,
                "schedule": schedule_desc,
                "context": {
                    "user_memory_count": user_memory_count,
                    "deliverable_memory_count": deliverable_memory_count,
                    "document_count": document_count,
                    "sample_memories": sample_memories,
                }
            }
        },
        "instruction_to_assistant": "Confirm the deliverable was created. Let the user know they can find it in their deliverables dashboard and can fine-tune the configuration there. Offer to generate the first version now if they'd like."
    }


def format_schedule_description(schedule: dict) -> str:
    """Format schedule dict into human-readable description."""
    frequency = schedule.get("frequency", "weekly")
    day = schedule.get("day")
    time = schedule.get("time", "09:00")
    tz = schedule.get("timezone", "America/Los_Angeles")

    # Format time
    try:
        hour, minute = map(int, time.split(":"))
        ampm = "AM" if hour < 12 else "PM"
        hour12 = hour if hour <= 12 else hour - 12
        hour12 = 12 if hour12 == 0 else hour12
        time_str = f"{hour12}:{minute:02d} {ampm}"
    except Exception:
        time_str = time

    # Build description
    if frequency == "daily":
        return f"Daily at {time_str}"
    elif frequency == "weekly":
        day_name = day.capitalize() if day else "Monday"
        return f"Weekly on {day_name} at {time_str}"
    elif frequency == "biweekly":
        day_name = day.capitalize() if day else "Monday"
        return f"Every 2 weeks on {day_name} at {time_str}"
    elif frequency == "monthly":
        day_num = day or "1st"
        return f"Monthly on the {day_num} at {time_str}"
    else:
        return schedule.get("cron", frequency)


def summarize_type_config(deliverable_type: str, config: dict) -> str:
    """Create a brief summary of the type configuration."""
    if not config:
        return "Default configuration"

    summaries = {
        "status_report": lambda c: f"Subject: {c.get('subject', 'N/A')}, Audience: {c.get('audience', 'stakeholders')}",
        "stakeholder_update": lambda c: f"For: {c.get('company_or_project', 'N/A')}, Type: {c.get('audience_type', 'client')}",
        "research_brief": lambda c: f"Focus: {c.get('focus_area', 'competitive')}, Subjects: {', '.join(c.get('subjects', []))[:50]}",
        "meeting_summary": lambda c: f"Meeting: {c.get('meeting_name', 'N/A')}, Type: {c.get('meeting_type', 'team_sync')}",
        "client_proposal": lambda c: f"Client: {c.get('client_name', 'N/A')}, Service: {c.get('service_category', 'N/A')}",
        "board_update": lambda c: f"Company: {c.get('company_name', 'N/A')}, Stage: {c.get('stage', 'seed')}",
        "custom": lambda c: c.get("description", "Custom deliverable")[:100],
    }

    formatter = summaries.get(deliverable_type, lambda c: str(c)[:100])
    try:
        return formatter(config)
    except Exception:
        return "Custom configuration"


# =============================================================================
# Memory Tool Handlers (ADR-023 Supervisor Desk Architecture)
# =============================================================================

async def handle_list_memories(auth, input: dict) -> dict:
    """
    List user's memories with optional filtering.

    ADR-023: Memory tools for context management.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with optional scope, project_id, tag, search, limit

    Returns:
        Dict with memories list
    """
    scope = input.get("scope")
    project_id = input.get("project_id")
    tag = input.get("tag")
    search = input.get("search")
    limit = input.get("limit", 20)

    # Build query - filter is_active=true since schema uses soft delete
    query = auth.client.table("memories")\
        .select("id, content, tags, project_id, created_at, updated_at, projects(name)")\
        .eq("user_id", auth.user_id)\
        .eq("is_active", True)\
        .order("created_at", desc=True)\
        .limit(limit)

    # Apply scope filter
    if scope == "user":
        query = query.is_("project_id", "null")
    elif scope == "project":
        if project_id:
            query = query.eq("project_id", project_id)
        else:
            query = query.not_.is_("project_id", "null")

    # Apply tag filter
    if tag:
        query = query.contains("tags", [tag])

    # Apply search filter
    if search:
        query = query.ilike("content", f"%{search}%")

    result = query.execute()
    memories = result.data or []

    # Format response
    items = []
    for m in memories:
        project_name = None
        if m.get("project_id") and m.get("projects"):
            project_name = m["projects"].get("name")

        items.append({
            "id": m["id"],
            "content": m["content"][:200] + "..." if len(m["content"]) > 200 else m["content"],
            "tags": m.get("tags", []),
            "scope": "project" if m.get("project_id") else "user",
            "project_name": project_name,
            "created_at": m["created_at"],
        })

    return {
        "success": True,
        "memories": items,
        "count": len(items),
        "message": f"Found {len(items)} memory/memories" if items else "No memories stored yet.",
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "context",
            "data": {
                "scope": scope or "user",
                "scopeId": project_id,
            }
        }
    }


async def handle_create_memory(auth, input: dict) -> dict:
    """
    Create a new memory.

    ADR-023: Store context that persists across sessions.
    ADR-024: Includes project attribution for transparent routing.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with content, optional tags and project_id

    Returns:
        Dict with created memory details including project attribution
    """
    content = input["content"]
    tags = input.get("tags", [])
    project_id = input.get("project_id")

    # Build memory data
    # Note: source_type is required by schema (006_unified_memory.sql)
    memory_data = {
        "content": content,
        "tags": tags,
        "user_id": auth.user_id,
        "source_type": "manual",  # Created via TP tool
    }

    # Get project name for attribution if project_id provided
    project_name = None
    if project_id:
        memory_data["project_id"] = project_id
        try:
            project_result = auth.client.table("projects")\
                .select("name")\
                .eq("id", project_id)\
                .single()\
                .execute()
            if project_result.data:
                project_name = project_result.data["name"]
        except Exception:
            pass

    # Create memory
    result = auth.client.table("memories").insert(memory_data).execute()

    if not result.data:
        return {
            "success": False,
            "error": "Failed to create memory"
        }

    memory = result.data[0]
    scope = "project" if project_id else "user"

    # ADR-024: Build attribution message for transparency
    if project_id and project_name:
        scope_display = f"'{project_name}' project"
        attribution_message = f"Saved to {scope_display} context."
    else:
        scope_display = "Personal"
        attribution_message = "Saved to your personal context (applies across all projects)."

    return {
        "success": True,
        "memory": {
            "id": memory["id"],
            "content": content[:100] + "..." if len(content) > 100 else content,
            "tags": tags,
            "scope": scope,
            "project_id": project_id,
            "project_name": project_name,
        },
        "message": f"Memory stored. {attribution_message}",
        # ADR-024: Include attribution for confirmation UI
        "attribution": {
            "scope": scope,
            "scope_display": scope_display,
            "project_id": project_id,
            "project_name": project_name,
        },
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "context",
            "data": {
                "scope": scope,
                "scopeId": project_id,
            }
        }
    }


async def handle_update_memory(auth, input: dict) -> dict:
    """
    Update an existing memory.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with memory_id and optional content, tags

    Returns:
        Dict with updated memory details
    """
    from datetime import datetime

    memory_id = input["memory_id"]
    updates = {}

    if "content" in input:
        updates["content"] = input["content"]

    if "tags" in input:
        updates["tags"] = input["tags"]

    if not updates:
        return {
            "success": False,
            "error": "No updates provided"
        }

    updates["updated_at"] = datetime.utcnow().isoformat()

    # Apply update
    result = auth.client.table("memories")\
        .update(updates)\
        .eq("id", memory_id)\
        .eq("user_id", auth.user_id)\
        .execute()

    if not result.data:
        return {
            "success": False,
            "error": "Memory not found or access denied"
        }

    memory = result.data[0]

    return {
        "success": True,
        "memory": {
            "id": memory["id"],
            "content": memory["content"][:100] + "..." if len(memory["content"]) > 100 else memory["content"],
            "tags": memory.get("tags", []),
        },
        "message": "Memory updated."
    }


async def handle_delete_memory(auth, input: dict) -> dict:
    """
    Delete a memory.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with memory_id

    Returns:
        Dict confirming deletion
    """
    memory_id = input["memory_id"]

    # Verify ownership and get content preview (only active memories)
    try:
        memory_result = auth.client.table("memories")\
            .select("id, content")\
            .eq("id", memory_id)\
            .eq("user_id", auth.user_id)\
            .eq("is_active", True)\
            .single()\
            .execute()
    except Exception:
        return {
            "success": False,
            "error": "Memory not found or access denied"
        }

    if not memory_result.data:
        return {
            "success": False,
            "error": "Memory not found or access denied"
        }

    content_preview = memory_result.data["content"][:50] + "..." if len(memory_result.data["content"]) > 50 else memory_result.data["content"]

    # Soft delete memory (schema uses is_active pattern)
    auth.client.table("memories")\
        .update({"is_active": False})\
        .eq("id", memory_id)\
        .execute()

    return {
        "success": True,
        "message": f"Memory deleted: \"{content_preview}\""
    }


async def handle_suggest_project_for_memory(auth, input: dict) -> dict:
    """
    ADR-024: Suggest which project a memory belongs to based on content.

    Uses semantic similarity against project memories to determine routing.

    Args:
        auth: UserClient with authenticated Supabase client
        input: Tool input with memory_content

    Returns:
        Dict with suggested project and confidence
    """
    from routes.projects import get_or_create_workspace

    memory_content = input["memory_content"]
    content_lower = memory_content.lower()

    # Get user's projects with their descriptions
    workspace = await get_or_create_workspace(auth)
    projects_result = auth.client.table("projects")\
        .select("id, name, description")\
        .eq("workspace_id", workspace["id"])\
        .execute()

    projects = projects_result.data or []

    if not projects:
        # No projects exist - default to user-scoped
        return {
            "success": True,
            "suggested_scope": "user",
            "suggested_project_id": None,
            "suggested_project_name": "Personal",
            "confidence": 0.9,
            "reason": "No projects exist yet. This will be stored as personal context.",
            "alternatives": []
        }

    # Score each project based on name/description match and memory overlap
    suggestions = []

    for project in projects:
        score = 0.0
        reasons = []

        project_name = project["name"].lower()
        project_desc = (project.get("description") or "").lower()

        # Check if project name appears in content
        if project_name in content_lower:
            score += 0.4
            reasons.append(f"mentions '{project['name']}'")

        # Check if content keywords appear in project name/description
        content_words = set(content_lower.split())
        name_words = set(project_name.split())
        desc_words = set(project_desc.split())

        # Remove common words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'as', 'into', 'through', 'during', 'before', 'after', 'above',
                     'below', 'between', 'under', 'again', 'further', 'then', 'once',
                     'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                     'neither', 'not', 'only', 'own', 'same', 'than', 'too', 'very',
                     'can', 'just', 'now', 'i', 'me', 'my', 'we', 'our', 'you', 'your',
                     'he', 'she', 'it', 'they', 'them', 'their', 'this', 'that', 'these',
                     'those', 'which', 'who', 'whom', 'what', 'when', 'where', 'why', 'how'}

        content_keywords = content_words - stopwords
        name_keywords = name_words - stopwords
        desc_keywords = desc_words - stopwords

        # Name keyword overlap
        name_overlap = content_keywords & name_keywords
        if name_overlap:
            score += 0.3 * min(len(name_overlap) / max(len(content_keywords), 1), 1.0)
            reasons.append(f"keywords: {', '.join(list(name_overlap)[:3])}")

        # Description keyword overlap
        desc_overlap = content_keywords & desc_keywords
        if desc_overlap:
            score += 0.2 * min(len(desc_overlap) / max(len(content_keywords), 1), 1.0)

        # Check for project-specific context in the project's memories
        try:
            project_memories = auth.client.table("memories")\
                .select("content")\
                .eq("project_id", project["id"])\
                .eq("is_active", True)\
                .limit(10)\
                .execute()

            if project_memories.data:
                # Check if content relates to existing project memories
                project_memory_text = " ".join([m["content"].lower() for m in project_memories.data])
                project_mem_words = set(project_memory_text.split()) - stopwords
                mem_overlap = content_keywords & project_mem_words
                if mem_overlap:
                    score += 0.2 * min(len(mem_overlap) / max(len(content_keywords), 1), 1.0)
                    reasons.append(f"relates to existing context")
        except Exception:
            pass

        suggestions.append({
            "project_id": project["id"],
            "project_name": project["name"],
            "score": min(score, 1.0),
            "reasons": reasons
        })

    # Sort by score descending
    suggestions.sort(key=lambda x: x["score"], reverse=True)

    # Determine best suggestion
    best = suggestions[0] if suggestions else None

    # Heuristics for user-scoped content
    user_scope_indicators = [
        "i prefer", "i like", "my style", "always", "never",
        "in general", "typically", "usually", "my background",
        "i work at", "my company", "my role", "i am", "i have been"
    ]
    is_user_scoped = any(indicator in content_lower for indicator in user_scope_indicators)

    if is_user_scoped:
        # Content appears to be about the user, not a project
        return {
            "success": True,
            "suggested_scope": "user",
            "suggested_project_id": None,
            "suggested_project_name": "Personal",
            "confidence": 0.8,
            "reason": "Content describes personal preferences or user-level facts.",
            "alternatives": [
                {
                    "project_id": s["project_id"],
                    "project_name": s["project_name"],
                    "confidence": s["score"]
                }
                for s in suggestions[:3] if s["score"] > 0.2
            ]
        }

    if best and best["score"] >= 0.5:
        # Good match to a project
        reason_text = ", ".join(best["reasons"]) if best["reasons"] else "Content relates to this project"
        return {
            "success": True,
            "suggested_scope": "project",
            "suggested_project_id": best["project_id"],
            "suggested_project_name": best["project_name"],
            "confidence": best["score"],
            "reason": reason_text,
            "alternatives": [
                {
                    "project_id": s["project_id"],
                    "project_name": s["project_name"],
                    "confidence": s["score"]
                }
                for s in suggestions[1:4] if s["score"] > 0.2
            ]
        }
    elif best and best["score"] >= 0.3:
        # Medium confidence - might relate to a project
        return {
            "success": True,
            "suggested_scope": "uncertain",
            "suggested_project_id": best["project_id"],
            "suggested_project_name": best["project_name"],
            "confidence": best["score"],
            "reason": f"May relate to {best['project_name']}, but not certain. Consider asking the user.",
            "alternatives": [
                {"project_id": None, "project_name": "Personal", "confidence": 0.5},
                *[
                    {
                        "project_id": s["project_id"],
                        "project_name": s["project_name"],
                        "confidence": s["score"]
                    }
                    for s in suggestions[:3] if s["score"] > 0.2
                ]
            ]
        }
    else:
        # Low confidence - default to user-scoped
        return {
            "success": True,
            "suggested_scope": "user",
            "suggested_project_id": None,
            "suggested_project_name": "Personal",
            "confidence": 0.7,
            "reason": "Content appears to be general/cross-project. Storing as personal context.",
            "alternatives": [
                {
                    "project_id": s["project_id"],
                    "project_name": s["project_name"],
                    "confidence": s["score"]
                }
                for s in suggestions[:3] if s["score"] > 0.1
            ]
        }


# Registry mapping tool names to handlers
TOOL_HANDLERS: dict[str, ToolHandler] = {
    # Communication tools (ADR-023 Unified Tool Model)
    "respond": handle_respond,
    "clarify": handle_clarify,
    # Todo tracking (ADR-025 Claude Code Alignment)
    "todo_write": handle_todo_write,
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
    # Memory/Context tools (ADR-023, ADR-024)
    "list_memories": handle_list_memories,
    "create_memory": handle_create_memory,
    "update_memory": handle_update_memory,
    "delete_memory": handle_delete_memory,
    "suggest_project_for_memory": handle_suggest_project_for_memory,
    # Deliverable tools (ADR-018, ADR-020)
    "list_deliverables": handle_list_deliverables,
    "get_deliverable": handle_get_deliverable,
    "run_deliverable": handle_run_deliverable,
    "update_deliverable": handle_update_deliverable,
    "create_deliverable": handle_create_deliverable,
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
    import logging
    import sys
    logger = logging.getLogger(__name__)

    handler = TOOL_HANDLERS.get(tool_name)

    if not handler:
        msg = f"[TOOL] Unknown tool: {tool_name}"
        print(msg, file=sys.stderr, flush=True)
        logger.warning(msg)
        return {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        }

    try:
        msg = f"[TOOL] Executing {tool_name} with input: {str(tool_input)[:200]}"
        print(msg, file=sys.stderr, flush=True)
        logger.info(msg)

        result = await handler(auth, tool_input)

        msg = f"[TOOL] {tool_name} result: success={result.get('success')}, ui_action={result.get('ui_action')}"
        print(msg, file=sys.stderr, flush=True)
        logger.info(msg)

        return result
    except Exception as e:
        msg = f"[TOOL] {tool_name} failed with error: {e}"
        print(msg, file=sys.stderr, flush=True)
        logger.error(msg)
        return {
            "success": False,
            "error": str(e)
        }
