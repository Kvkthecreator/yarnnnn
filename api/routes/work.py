"""
Work routes - Ticket lifecycle management

ADR-009: Work and Agent Orchestration

Endpoints:
- POST /projects/:id/work - Create and execute work request
- POST /projects/:id/work/async - Create work request (async execution)
- GET /projects/:id/work - List work tickets
- GET /work/:id - Get ticket with outputs
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
    """Create work request."""
    task: str
    agent_type: Literal["research", "content", "reporting"]
    parameters: Optional[dict] = None


class WorkResponse(BaseModel):
    """Work ticket response."""
    id: str
    task: str
    agent_type: str
    status: str  # pending, running, completed, failed
    project_id: str
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


# =============================================================================
# Routes
# =============================================================================

@router.post("/projects/{project_id}/work")
async def create_and_execute(
    project_id: UUID,
    request: WorkCreate,
    auth: UserClient,
) -> WorkExecutionResponse:
    """
    Create and execute a work request synchronously.

    This creates a work ticket and immediately executes the agent.
    Use this for interactive workflows where you want immediate results.

    Args:
        project_id: Project UUID
        request: Work request with task, agent_type, parameters
        auth: Authenticated user

    Returns:
        Execution result with outputs
    """
    # Verify project access
    project_result = (
        auth.client.table("projects")
        .select("id, name")
        .eq("id", str(project_id))
        .single()
        .execute()
    )
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info(
        f"[WORK] Creating and executing: project={project_id}, "
        f"agent={request.agent_type}, task='{request.task[:50]}...'"
    )

    result = await create_and_execute_work(
        client=auth.client,
        user_id=auth.user_id,
        project_id=str(project_id),
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


@router.post("/projects/{project_id}/work/async")
async def create_ticket_async(
    project_id: UUID,
    request: WorkCreate,
    auth: UserClient,
) -> WorkResponse:
    """
    Create a work ticket for async execution.

    This creates the ticket but does NOT execute it immediately.
    Use GET /work/{id} to check status and POST /work/{id}/execute to run it.

    Args:
        project_id: Project UUID
        request: Work request with task, agent_type, parameters
        auth: Authenticated user

    Returns:
        Created ticket details
    """
    # Verify project access
    project_result = (
        auth.client.table("projects")
        .select("id")
        .eq("id", str(project_id))
        .single()
        .execute()
    )
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate agent type
    valid_types = ["research", "content", "reporting"]
    if request.agent_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent_type. Must be one of: {', '.join(valid_types)}"
        )

    # Create ticket
    ticket_data = {
        "task": request.task,
        "agent_type": request.agent_type,
        "project_id": str(project_id),
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
        project_id=ticket["project_id"],
        created_at=ticket["created_at"],
    )


@router.get("/projects/{project_id}/work")
async def list_work(
    project_id: UUID,
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[WorkResponse]:
    """
    List work tickets for a project.

    Args:
        project_id: Project UUID
        auth: Authenticated user
        status: Optional filter by status (pending, running, completed, failed)
        limit: Maximum tickets to return

    Returns:
        List of work tickets
    """
    # Verify project access
    project_result = (
        auth.client.table("projects")
        .select("id")
        .eq("id", str(project_id))
        .single()
        .execute()
    )
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Build query
    query = (
        auth.client.table("work_tickets")
        .select("*")
        .eq("project_id", str(project_id))
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
            project_id=t["project_id"],
            created_at=t["created_at"],
            started_at=t.get("started_at"),
            completed_at=t.get("completed_at"),
            error_message=t.get("error_message"),
        )
        for t in tickets
    ]


@router.get("/work/{ticket_id}")
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
        .select("*, projects(name)")
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
            "project_id": ticket["project_id"],
            "project_name": ticket.get("projects", {}).get("name") if ticket.get("projects") else None,
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


@router.post("/work/{ticket_id}/execute")
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
