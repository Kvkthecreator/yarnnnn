"""
Work routes - Ticket lifecycle management

Endpoints:
- POST /projects/:id/tickets - Create work request
- GET /projects/:id/tickets - List tickets
- GET /tickets/:id - Get ticket with outputs
- GET /tickets/:id/outputs - Get outputs only
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from uuid import UUID

router = APIRouter()


class TicketCreate(BaseModel):
    task: str
    agent_type: Literal["research", "content", "reporting"]
    parameters: Optional[dict] = None


class TicketResponse(BaseModel):
    id: UUID
    task: str
    agent_type: str
    status: str  # pending, running, completed, failed
    project_id: UUID
    created_at: str


class OutputResponse(BaseModel):
    id: UUID
    title: str
    output_type: str  # text, file
    content: Optional[str] = None
    file_url: Optional[str] = None
    ticket_id: UUID
    created_at: str


@router.post("/projects/{project_id}/tickets")
async def create_ticket(project_id: UUID, ticket: TicketCreate) -> TicketResponse:
    """Create a new work request."""
    # TODO: Implement with Supabase + trigger agent execution
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/projects/{project_id}/tickets")
async def list_tickets(project_id: UUID) -> list[TicketResponse]:
    """List all tickets in project."""
    # TODO: Implement with Supabase
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: UUID) -> dict:
    """Get ticket with outputs."""
    # TODO: Implement with Supabase
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/tickets/{ticket_id}/outputs")
async def get_outputs(ticket_id: UUID) -> list[OutputResponse]:
    """Get outputs for ticket."""
    # TODO: Implement with Supabase
    raise HTTPException(status_code=501, detail="Not implemented")
