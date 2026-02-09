"""
Work Execution Service

ADR-009: Work and Agent Orchestration
ADR-016: Layered Agent Architecture (single output per work)

Handles the full work ticket lifecycle:
1. Create ticket → 2. Load context → 3. Execute agent → 4. Save output → 5. Update status
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from agents.base import ContextBundle, Memory, WorkOutput
from agents.factory import create_agent

logger = logging.getLogger(__name__)

# Default timeout for work execution (5 minutes)
DEFAULT_WORK_TIMEOUT_SECONDS = 300


async def load_context_for_work(
    client,
    user_id: str,
    task: Optional[str] = None,
    max_memories: int = 20,
) -> ContextBundle:
    """
    Load context for work execution.

    Loads user memories into a ContextBundle.
    Uses semantic search if task is provided.

    Args:
        client: Supabase client
        user_id: User ID
        task: Optional task description for semantic search
        max_memories: Maximum memories to load

    Returns:
        ContextBundle with loaded memories
    """
    memories = []

    try:
        # Load user memories
        user_result = (
            client.table("memories")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("importance", desc=True)
            .limit(max_memories)
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
            ))

        logger.info(f"Loaded {len(memories)} memories for work execution")

    except Exception as e:
        logger.warning(f"Error loading context: {e}")

    return ContextBundle(
        memories=memories,
        documents=[],
    )


async def execute_work_ticket(
    client,
    user_id: str,
    ticket_id: str,
    timeout_seconds: int = DEFAULT_WORK_TIMEOUT_SECONDS,
) -> dict:
    """
    Execute a work ticket.

    ADR-016: Each work execution produces ONE output.

    Full execution flow:
    1. Load ticket details
    2. Update status to 'running'
    3. Load context
    4. Execute agent
    5. Save output (single)
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
        agent_type = ticket["agent_type"]
        task = ticket["task"]
        # Handle parameters stored as either JSON string or dict
        raw_params = ticket.get("parameters", {})
        if isinstance(raw_params, str):
            try:
                parameters = json.loads(raw_params)
            except (json.JSONDecodeError, TypeError):
                parameters = {}
        else:
            parameters = raw_params or {}

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
            task=task,
        )

        # 4. Execute agent with timeout
        agent = create_agent(agent_type)
        try:
            result = await asyncio.wait_for(
                agent.execute(
                    task=task,
                    context=context,
                    parameters=parameters,
                ),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            # Update to failed with timeout error
            completed_at = datetime.now(timezone.utc)
            client.table("work_tickets").update({
                "status": "failed",
                "completed_at": completed_at.isoformat(),
                "error_message": f"Work execution timed out after {timeout_seconds} seconds",
            }).eq("id", ticket_id).execute()

            logger.warning(f"[WORK EXECUTION] Timeout after {timeout_seconds}s for ticket {ticket_id}")

            return {
                "success": False,
                "error": f"Work execution timed out after {timeout_seconds} seconds",
                "ticket_id": ticket_id,
            }

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

        # 5. Save output (ADR-016: single output per work)
        saved_output = None
        if result.work_output:
            output_data = {
                "ticket_id": ticket_id,
                "title": result.work_output.title,
                "content": result.work_output.content,  # Markdown content
                "output_type": "markdown",  # Required field - default to markdown for ADR-016
                "status": "delivered",
            }
            # Only include metadata if present (column may not exist in older schemas)
            if result.work_output.metadata:
                output_data["metadata"] = result.work_output.metadata

            try:
                output_result = (
                    client.table("work_outputs")
                    .insert(output_data)
                    .execute()
                )
            except Exception as insert_err:
                # If metadata column doesn't exist, retry without it
                if "metadata" in str(insert_err) and "metadata" in output_data:
                    logger.warning("[WORK EXECUTION] Retrying insert without metadata column")
                    del output_data["metadata"]
                    output_result = (
                        client.table("work_outputs")
                        .insert(output_data)
                        .execute()
                    )
                else:
                    raise

            if output_result.data:
                saved_output = output_result.data[0]
                logger.info(f"[WORK EXECUTION] Saved output: {saved_output['id']}")

        # 6. Update to completed
        client.table("work_tickets").update({
            "status": "completed",
            "completed_at": completed_at.isoformat(),
        }).eq("id", ticket_id).execute()

        # Format response (maintain backward compatibility with list format)
        outputs = [saved_output] if saved_output else []

        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": "completed",
            "output": saved_output,  # ADR-016: single output
            "outputs": outputs,  # Backward compat: list with 0 or 1 item
            "output_count": len(outputs),
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
        "user_id": user_id,
        "task": task,
        "agent_type": agent_type,
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
