"""
Agent routes - Execution management

Endpoints:
- POST /tickets/:id/execute - Trigger agent execution
- GET /tickets/:id/status - Get execution status (SSE)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from uuid import UUID

router = APIRouter()


@router.post("/tickets/{ticket_id}/execute")
async def execute_agent(ticket_id: UUID) -> dict:
    """
    Trigger agent execution for a ticket.

    Flow:
    1. Load ticket and project context
    2. Create agent based on ticket.agent_type
    3. Execute agent with context
    4. Save outputs to work_outputs
    5. Update ticket status
    """
    # TODO: Implement agent execution
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/tickets/{ticket_id}/status")
async def get_execution_status(ticket_id: UUID):
    """
    Stream execution status updates (SSE).

    Events:
    - status: pending | running | completed | failed
    - progress: { step, message }
    - output: { id, title, type }
    """
    async def event_stream():
        # TODO: Implement SSE streaming
        yield f"data: {{'status': 'not_implemented'}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )
