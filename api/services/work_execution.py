"""
Work Execution Service

ADR-009: Work and Agent Orchestration
Handles the full work ticket lifecycle:
1. Create ticket → 2. Load context → 3. Execute agent → 4. Save outputs → 5. Update status

This service bridges the gap between:
- TP tools (create_work, list_work, get_work_status)
- Work routes (REST API)
- Agent execution
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from agents.base import ContextBundle, Memory, WorkOutput
from agents.factory import create_agent

logger = logging.getLogger(__name__)


async def load_context_for_work(
    client,
    user_id: str,
    project_id: str,
    task: Optional[str] = None,
    max_memories: int = 20,
) -> ContextBundle:
    """
    Load context for work execution.

    Combines user memories and project memories into a ContextBundle.
    Uses semantic search if task is provided.

    Args:
        client: Supabase client
        user_id: User ID
        project_id: Project ID
        task: Optional task description for semantic search
        max_memories: Maximum memories to load

    Returns:
        ContextBundle with loaded memories
    """
    memories = []

    try:
        # Load user memories (project_id IS NULL)
        user_result = (
            client.table("memories")
            .select("*")
            .eq("user_id", user_id)
            .is_("project_id", "null")
            .eq("is_active", True)
            .order("importance", desc=True)
            .limit(max_memories // 2)
            .execute()
        )

        for row in (user_result.data or []):
            memories.append(Memory(
                id=UUID(row["id"]),
                content=row["content"],
                importance=row.get("importance", 0.5),
                tags=row.get("tags", []),
                entities=row.get("entities", {}),
                source_type=row.get("source_type", "chat"),
                project_id=None,
            ))

        # Load project memories
        project_result = (
            client.table("memories")
            .select("*")
            .eq("user_id", user_id)
            .eq("project_id", project_id)
            .eq("is_active", True)
            .order("importance", desc=True)
            .limit(max_memories // 2)
            .execute()
        )

        for row in (project_result.data or []):
            memories.append(Memory(
                id=UUID(row["id"]),
                content=row["content"],
                importance=row.get("importance", 0.5),
                tags=row.get("tags", []),
                entities=row.get("entities", {}),
                source_type=row.get("source_type", "chat"),
                project_id=UUID(row["project_id"]),
            ))

        # Get project name
        project_result = (
            client.table("projects")
            .select("name")
            .eq("id", project_id)
            .single()
            .execute()
        )
        project_name = project_result.data.get("name") if project_result.data else None

        logger.info(f"Loaded {len(memories)} memories for work execution")

    except Exception as e:
        logger.warning(f"Error loading context: {e}")

    return ContextBundle(
        memories=memories,
        documents=[],
        project_id=UUID(project_id),
        project_name=project_name,
    )


async def execute_work_ticket(
    client,
    user_id: str,
    ticket_id: str,
) -> dict:
    """
    Execute a work ticket.

    Full execution flow:
    1. Load ticket details
    2. Update status to 'running'
    3. Load context
    4. Execute agent
    5. Save outputs
    6. Update status to 'completed' or 'failed'

    Args:
        client: Supabase client
        user_id: User ID
        ticket_id: Work ticket ID

    Returns:
        Dict with execution result
    """
    started_at = datetime.now(timezone.utc)

    try:
        # 1. Load ticket
        ticket_result = (
            client.table("work_tickets")
            .select("*")
            .eq("id", ticket_id)
            .single()
            .execute()
        )

        if not ticket_result.data:
            return {
                "success": False,
                "error": "Work ticket not found",
            }

        ticket = ticket_result.data
        project_id = ticket["project_id"]
        agent_type = ticket["agent_type"]
        task = ticket["task"]
        parameters = ticket.get("parameters", {})

        logger.info(
            f"[WORK EXECUTION] Starting ticket {ticket_id}: "
            f"agent={agent_type}, task='{task[:50]}...'"
        )

        # 2. Update status to running
        client.table("work_tickets").update({
            "status": "running",
            "started_at": started_at.isoformat(),
        }).eq("id", ticket_id).execute()

        # 3. Load context
        context = await load_context_for_work(
            client,
            user_id,
            project_id,
            task=task,
        )

        # 4. Execute agent
        agent = create_agent(agent_type)
        result = await agent.execute(
            task=task,
            context=context,
            parameters=parameters,
        )

        completed_at = datetime.now(timezone.utc)
        execution_time_ms = int((completed_at - started_at).total_seconds() * 1000)

        if not result.success:
            # Update to failed
            client.table("work_tickets").update({
                "status": "failed",
                "completed_at": completed_at.isoformat(),
                "error_message": result.error,
            }).eq("id", ticket_id).execute()

            return {
                "success": False,
                "error": result.error,
                "ticket_id": ticket_id,
            }

        # 5. Save outputs
        saved_outputs = []
        for work_output in result.work_outputs:
            output_data = {
                "ticket_id": ticket_id,
                "title": work_output.title,
                "output_type": work_output.output_type,
                "content": json.dumps(work_output.body) if isinstance(work_output.body, dict) else work_output.body,
                "status": "delivered",
            }

            output_result = (
                client.table("work_outputs")
                .insert(output_data)
                .execute()
            )

            if output_result.data:
                saved_outputs.append(output_result.data[0])

        logger.info(f"[WORK EXECUTION] Saved {len(saved_outputs)} outputs")

        # 6. Update to completed
        client.table("work_tickets").update({
            "status": "completed",
            "completed_at": completed_at.isoformat(),
        }).eq("id", ticket_id).execute()

        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": "completed",
            "outputs": saved_outputs,
            "output_count": len(saved_outputs),
            "execution_time_ms": execution_time_ms,
            "agent_type": agent_type,
        }

    except Exception as e:
        logger.error(f"[WORK EXECUTION] Failed: {e}", exc_info=True)

        # Update to failed
        try:
            client.table("work_tickets").update({
                "status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error_message": str(e),
            }).eq("id", ticket_id).execute()
        except Exception as update_error:
            logger.error(f"Failed to update ticket status: {update_error}")

        return {
            "success": False,
            "error": str(e),
            "ticket_id": ticket_id,
        }


async def create_and_execute_work(
    client,
    user_id: str,
    project_id: str,
    task: str,
    agent_type: str,
    parameters: Optional[dict] = None,
) -> dict:
    """
    Create a work ticket and execute it synchronously.

    Combines ticket creation and execution for simpler workflows.

    Args:
        client: Supabase client
        user_id: User ID
        project_id: Project ID
        task: Task description
        agent_type: Agent type (research, content, reporting)
        parameters: Optional agent parameters

    Returns:
        Dict with ticket and execution result
    """
    # Validate agent type
    valid_types = ["research", "content", "reporting"]
    if agent_type not in valid_types:
        return {
            "success": False,
            "error": f"Invalid agent_type. Must be one of: {', '.join(valid_types)}",
        }

    # Create ticket
    ticket_data = {
        "task": task,
        "agent_type": agent_type,
        "project_id": project_id,
        "parameters": parameters or {},
        "status": "pending",
    }

    ticket_result = (
        client.table("work_tickets")
        .insert(ticket_data)
        .execute()
    )

    if not ticket_result.data:
        return {
            "success": False,
            "error": "Failed to create work ticket",
        }

    ticket = ticket_result.data[0]
    ticket_id = ticket["id"]

    logger.info(f"[WORK] Created ticket {ticket_id} for {agent_type} agent")

    # Execute
    result = await execute_work_ticket(client, user_id, ticket_id)

    return {
        **result,
        "ticket": ticket,
    }
