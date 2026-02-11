"""
Work routes - Ticket lifecycle management

ADR-009: Work and Agent Orchestration
ADR-039: Background Work Agents

Endpoints:
- POST /work - Create and execute work request
- POST /work/async - Create work request (async execution)
- POST /work/background - Create and queue for background execution (ADR-039)
- GET /work - List work tickets
- GET /work/:id - Get ticket with outputs
- GET /work/:id/status - Get real-time execution status (ADR-039)
- POST /work/:id/execute - Execute a pending ticket
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID

from services.supabase import UserClient
from services.work_execution import (
    create_and_execute_work,
    execute_work_ticket,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class WorkCreate(BaseModel):
    """Create work request.

    ADR-045: Agent types renamed for clarity:
    - synthesizer: Synthesizes pre-fetched context (formerly "research")
    - deliverable: Generates deliverables (formerly "content")
    - report: Generates standalone reports (formerly "reporting")

    Legacy names still accepted for backwards compatibility.
    """
    task: str
    agent_type: str  # synthesizer, deliverable, report (or legacy: research, content, reporting)
    parameters: Optional[dict] = None
    run_in_background: bool = False  # ADR-039: Background execution


class WorkResponse(BaseModel):
    """Work ticket response."""
    id: str
    task: str
    agent_type: str
    status: str  # pending, running, completed, failed
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class WorkExecutionResponse(BaseModel):
    """Work execution result."""
    success: bool
    ticket_id: str
    status: str
    outputs: list[dict] = []
    output_count: int = 0
    execution_time_ms: Optional[int] = None
    error: Optional[str] = None


class OutputResponse(BaseModel):
    """Work output response."""
    id: str
    title: str
    output_type: str
    content: Optional[str] = None
    file_url: Optional[str] = None
    status: str
    created_at: str


class WorkStatusResponse(BaseModel):
    """Work status response (ADR-039)."""
    ticket_id: str
    status: str  # pending, queued, running, completed, failed
    execution_mode: str  # foreground, background
    progress: Optional[dict] = None  # {stage, percent, message}
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    recent_logs: Optional[list] = None
    output_available: bool = False


class BackgroundWorkResponse(BaseModel):
    """Background work creation response (ADR-039)."""
    success: bool
    ticket_id: str
    job_id: Optional[str] = None
    status: str
    execution_mode: str
    message: str
    error: Optional[str] = None


# =============================================================================
# Routes
# =============================================================================

@router.post("")
async def create_and_execute(
    request: WorkCreate,
    auth: UserClient,
) -> WorkExecutionResponse:
    """
    Create and execute a work request synchronously.

    This creates a work ticket and immediately executes the agent.
    Use this for interactive workflows where you want immediate results.

    Args:
        request: Work request with task, agent_type, parameters
        auth: Authenticated user

    Returns:
        Execution result with outputs
    """
    logger.info(
        f"[WORK] Creating and executing: user={auth.user_id}, "
        f"agent={request.agent_type}, task='{request.task[:50]}...'"
    )

    result = await create_and_execute_work(
        client=auth.client,
        user_id=auth.user_id,
        task=request.task,
        agent_type=request.agent_type,
        parameters=request.parameters,
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Work execution failed")
        )

    return WorkExecutionResponse(
        success=True,
        ticket_id=result["ticket_id"],
        status=result["status"],
        outputs=result.get("outputs", []),
        output_count=result.get("output_count", 0),
        execution_time_ms=result.get("execution_time_ms"),
    )


@router.post("/async")
async def create_ticket_async(
    request: WorkCreate,
    auth: UserClient,
) -> WorkResponse:
    """
    Create a work ticket for async execution.

    This creates the ticket but does NOT execute it immediately.
    Use GET /work/{id} to check status and POST /work/{id}/execute to run it.

    Args:
        request: Work request with task, agent_type, parameters
        auth: Authenticated user

    Returns:
        Created ticket details
    """
    # Validate agent type (support both new and legacy names)
    from agents.factory import LEGACY_TYPE_MAP, get_valid_agent_types
    valid_types = get_valid_agent_types() + list(LEGACY_TYPE_MAP.keys())
    if request.agent_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent_type. Must be one of: {', '.join(get_valid_agent_types())}"
        )

    # Create ticket
    ticket_data = {
        "user_id": auth.user_id,
        "task": request.task,
        "agent_type": request.agent_type,
        "parameters": request.parameters or {},
        "status": "pending",
    }

    ticket_result = (
        auth.client.table("work_tickets")
        .insert(ticket_data)
        .execute()
    )

    if not ticket_result.data:
        raise HTTPException(status_code=500, detail="Failed to create work ticket")

    ticket = ticket_result.data[0]
    logger.info(f"[WORK] Created async ticket: {ticket['id']}")

    return WorkResponse(
        id=ticket["id"],
        task=ticket["task"],
        agent_type=ticket["agent_type"],
        status=ticket["status"],
        created_at=ticket["created_at"],
    )


@router.post("/background")
async def create_background_work(
    request: WorkCreate,
    auth: UserClient,
) -> BackgroundWorkResponse:
    """
    ADR-039: Create work for background execution.

    This creates a work ticket and queues it for background processing.
    Returns immediately with ticket_id and job_id for tracking.
    Poll GET /work/{id}/status for progress updates.

    Args:
        request: Work request with task, agent_type, parameters
        auth: Authenticated user

    Returns:
        Background work response with queue info
    """
    logger.info(
        f"[WORK] Creating background work: user={auth.user_id}, "
        f"agent={request.agent_type}, task='{request.task[:50]}...'"
    )

    result = await create_and_execute_work(
        client=auth.client,
        user_id=auth.user_id,
        task=request.task,
        agent_type=request.agent_type,
        parameters=request.parameters,
        run_in_background=True,
    )

    if not result.get("success"):
        return BackgroundWorkResponse(
            success=False,
            ticket_id=result.get("ticket_id", ""),
            status="failed",
            execution_mode="background",
            message=result.get("error", "Failed to queue work"),
            error=result.get("error"),
        )

    return BackgroundWorkResponse(
        success=True,
        ticket_id=result["ticket_id"],
        job_id=result.get("job_id"),
        status=result.get("status", "queued"),
        execution_mode=result.get("execution_mode", "background"),
        message=result.get("message", "Work queued for background execution"),
    )


@router.get("")
async def list_work(
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[WorkResponse]:
    """
    List work tickets for the user.

    Args:
        auth: Authenticated user
        status: Optional filter by status (pending, running, completed, failed)
        limit: Maximum tickets to return

    Returns:
        List of work tickets
    """
    # Build query
    query = (
        auth.client.table("work_tickets")
        .select("*")
        .eq("user_id", auth.user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    tickets = result.data or []

    return [
        WorkResponse(
            id=t["id"],
            task=t["task"],
            agent_type=t["agent_type"],
            status=t["status"],
            created_at=t["created_at"],
            started_at=t.get("started_at"),
            completed_at=t.get("completed_at"),
            error_message=t.get("error_message"),
        )
        for t in tickets
    ]


@router.get("/{ticket_id}")
async def get_work(
    ticket_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Get work ticket with outputs.

    Args:
        ticket_id: Work ticket UUID
        auth: Authenticated user

    Returns:
        Ticket details with outputs
    """
    # Get ticket
    ticket_result = (
        auth.client.table("work_tickets")
        .select("*")
        .eq("id", str(ticket_id))
        .single()
        .execute()
    )

    if not ticket_result.data:
        raise HTTPException(status_code=404, detail="Work ticket not found")

    ticket = ticket_result.data

    # Get outputs
    outputs_result = (
        auth.client.table("work_outputs")
        .select("*")
        .eq("ticket_id", str(ticket_id))
        .order("created_at")
        .execute()
    )

    outputs = outputs_result.data or []

    return {
        "ticket": {
            "id": ticket["id"],
            "task": ticket["task"],
            "agent_type": ticket["agent_type"],
            "status": ticket["status"],
            "parameters": ticket.get("parameters", {}),
            "created_at": ticket["created_at"],
            "started_at": ticket.get("started_at"),
            "completed_at": ticket.get("completed_at"),
            "error_message": ticket.get("error_message"),
        },
        "outputs": [
            {
                "id": o["id"],
                "title": o["title"],
                "output_type": o["output_type"],
                "content": o.get("content"),
                "file_url": o.get("file_url"),
                "file_format": o.get("file_format"),
                "status": o.get("status", "delivered"),
                "created_at": o["created_at"],
            }
            for o in outputs
        ],
        "output_count": len(outputs),
    }


@router.get("/{ticket_id}/status")
async def get_work_status(
    ticket_id: UUID,
    auth: UserClient,
) -> WorkStatusResponse:
    """
    ADR-039: Get real-time status of work execution.

    Use this to poll for progress on background work.
    Returns progress info, execution logs, and completion status.

    Args:
        ticket_id: Work ticket UUID
        auth: Authenticated user

    Returns:
        Work status with progress and logs
    """
    # Use the database function for comprehensive status
    try:
        result = auth.client.rpc(
            "get_work_status",
            {"p_ticket_id": str(ticket_id)}
        ).execute()

        if result.data and len(result.data) > 0:
            status_data = result.data[0]
            return WorkStatusResponse(
                ticket_id=str(ticket_id),
                status=status_data.get("status", "unknown"),
                execution_mode=status_data.get("execution_mode", "foreground"),
                progress=status_data.get("progress"),
                queued_at=status_data.get("queued_at"),
                started_at=status_data.get("started_at"),
                completed_at=status_data.get("completed_at"),
                error_message=status_data.get("error_message"),
                recent_logs=status_data.get("recent_logs"),
                output_available=status_data.get("status") == "completed",
            )
    except Exception as e:
        logger.warning(f"Failed to get work status via RPC: {e}")

    # Fallback to direct query
    ticket_result = (
        auth.client.table("work_tickets")
        .select("*")
        .eq("id", str(ticket_id))
        .single()
        .execute()
    )

    if not ticket_result.data:
        raise HTTPException(status_code=404, detail="Work ticket not found")

    ticket = ticket_result.data

    # Get recent logs if available
    recent_logs = None
    try:
        log_result = (
            auth.client.table("work_execution_log")
            .select("stage, message, timestamp")
            .eq("ticket_id", str(ticket_id))
            .order("timestamp", desc=True)
            .limit(10)
            .execute()
        )
        if log_result.data:
            recent_logs = log_result.data
    except Exception:
        pass  # Table might not exist yet

    return WorkStatusResponse(
        ticket_id=str(ticket_id),
        status=ticket["status"],
        execution_mode=ticket.get("execution_mode", "foreground"),
        progress=ticket.get("progress"),
        queued_at=ticket.get("queued_at"),
        started_at=ticket.get("started_at"),
        completed_at=ticket.get("completed_at"),
        error_message=ticket.get("error_message"),
        recent_logs=recent_logs,
        output_available=ticket["status"] == "completed",
    )


@router.post("/{ticket_id}/execute")
async def execute_ticket(
    ticket_id: UUID,
    auth: UserClient,
) -> WorkExecutionResponse:
    """
    Execute a pending work ticket.

    Use this to run a ticket that was created with the async endpoint.

    Args:
        ticket_id: Work ticket UUID
        auth: Authenticated user

    Returns:
        Execution result with outputs
    """
    # Get ticket to verify access and status
    ticket_result = (
        auth.client.table("work_tickets")
        .select("*")
        .eq("id", str(ticket_id))
        .single()
        .execute()
    )

    if not ticket_result.data:
        raise HTTPException(status_code=404, detail="Work ticket not found")

    ticket = ticket_result.data

    if ticket["status"] not in ["pending", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot execute ticket with status '{ticket['status']}'. Must be 'pending' or 'failed'."
        )

    logger.info(f"[WORK] Executing ticket: {ticket_id}")

    result = await execute_work_ticket(
        client=auth.client,
        user_id=auth.user_id,
        ticket_id=str(ticket_id),
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Work execution failed")
        )

    return WorkExecutionResponse(
        success=True,
        ticket_id=result["ticket_id"],
        status=result["status"],
        outputs=result.get("outputs", []),
        output_count=result.get("output_count", 0),
        execution_time_ms=result.get("execution_time_ms"),
    )


# =============================================================================
# ADR-017: Unified Work Model Routes
# =============================================================================

class WorkUpdateRequest(BaseModel):
    """Update work request."""
    is_active: Optional[bool] = None
    task: Optional[str] = None
    frequency: Optional[str] = None


@router.get("/all")
async def list_all_work(
    auth: UserClient,
    active_only: bool = False,
    include_completed: bool = True,
    limit: int = 10,
) -> dict:
    """
    ADR-017: List all work for the current user.

    Supports filtering by active status and completion status.
    Returns both one-time and recurring work.

    Args:
        auth: Authenticated user
        active_only: Only show active recurring work
        include_completed: Include completed one-time work
        limit: Maximum results

    Returns:
        Dict with work list, count, message
    """
    from services.project_tools import handle_list_work

    result = await handle_list_work(auth, {
        "active_only": active_only,
        "include_completed": include_completed,
        "limit": limit,
    })

    return result


@router.patch("/{work_id}")
async def update_work(
    work_id: str,
    request: WorkUpdateRequest,
    auth: UserClient,
) -> dict:
    """
    ADR-017: Update work settings.

    Use to pause/resume recurring work, change frequency, or update task.

    Args:
        work_id: Work UUID
        request: Update data (is_active, task, frequency)
        auth: Authenticated user

    Returns:
        Dict with updated work details
    """
    from services.project_tools import handle_update_work

    input_data = {"work_id": work_id}
    if request.is_active is not None:
        input_data["is_active"] = request.is_active
    if request.task is not None:
        input_data["task"] = request.task
    if request.frequency is not None:
        input_data["frequency"] = request.frequency

    result = await handle_update_work(auth, input_data)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Update failed"))

    return result


@router.delete("/{work_id}")
async def delete_work(
    work_id: str,
    auth: UserClient,
) -> dict:
    """
    ADR-017: Delete work and all its outputs.

    Args:
        work_id: Work UUID
        auth: Authenticated user

    Returns:
        Dict confirming deletion
    """
    from services.project_tools import handle_delete_work

    result = await handle_delete_work(auth, {"work_id": work_id})

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Delete failed"))

    return result