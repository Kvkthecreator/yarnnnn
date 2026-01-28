"""
Context routes - Block and document management

Endpoints:
- POST /projects/:id/blocks - Add block
- GET /projects/:id/blocks - List blocks
- POST /projects/:id/documents - Upload document
- GET /projects/:id/context - Get full context bundle
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

router = APIRouter()


class BlockCreate(BaseModel):
    content: str
    block_type: str = "text"  # text, structured, extracted
    metadata: Optional[dict] = None


class BlockResponse(BaseModel):
    id: UUID
    content: str
    block_type: str
    project_id: UUID
    created_at: str


@router.post("/projects/{project_id}/blocks")
async def create_block(project_id: UUID, block: BlockCreate) -> BlockResponse:
    """Add a new block to project context."""
    # TODO: Implement with Supabase
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/projects/{project_id}/blocks")
async def list_blocks(project_id: UUID) -> list[BlockResponse]:
    """List all blocks in project."""
    # TODO: Implement with Supabase
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/projects/{project_id}/context")
async def get_context_bundle(project_id: UUID) -> dict:
    """Get full context bundle (blocks + documents) for agent execution."""
    # TODO: Implement with Supabase
    raise HTTPException(status_code=501, detail="Not implemented")
