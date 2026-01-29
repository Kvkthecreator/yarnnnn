"""
Context routes - Block and document management

Endpoints:
- POST /projects/:id/blocks - Add block (manual)
- POST /projects/:id/blocks/import - Bulk import text → extract blocks
- GET /projects/:id/blocks - List blocks
- DELETE /blocks/:id - Delete block
- GET /projects/:id/context - Get full context bundle
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient
from services.extraction import extract_from_bulk_text

router = APIRouter()


# --- Pydantic Models ---

class BlockCreate(BaseModel):
    content: str
    block_type: str = "text"  # text, structured, extracted
    semantic_type: Optional[str] = None  # fact, guideline, requirement, insight, note, question
    metadata: Optional[dict] = None


class BulkImportRequest(BaseModel):
    text: str  # Raw text to extract blocks from


class BulkImportResponse(BaseModel):
    blocks_extracted: int
    project_id: UUID


class BlockResponse(BaseModel):
    id: UUID
    content: str
    block_type: str
    semantic_type: Optional[str] = None
    source_type: Optional[str] = None
    importance: Optional[float] = None
    metadata: Optional[dict]
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_url: str
    file_type: Optional[str]
    file_size: Optional[int]
    project_id: UUID
    created_at: datetime


class ContextBundle(BaseModel):
    project_id: UUID
    blocks: list[BlockResponse]
    documents: list[DocumentResponse]


# --- Routes ---

@router.post("/projects/{project_id}/blocks", response_model=BlockResponse)
async def create_block(project_id: UUID, block: BlockCreate, auth: UserClient):
    """Add a new block to project context (manual creation)."""
    try:
        result = auth.client.table("blocks").insert({
            "project_id": str(project_id),
            "content": block.content,
            "block_type": block.block_type,
            "semantic_type": block.semantic_type,
            "source_type": "manual",
            "importance": 0.5,
            "metadata": block.metadata or {}
        }).execute()

        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create block")

        return result.data[0]

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/blocks/import", response_model=BulkImportResponse)
async def import_blocks(project_id: UUID, request: BulkImportRequest, auth: UserClient):
    """
    Bulk import: paste text → extract semantic blocks.

    Takes raw text (notes, meeting transcripts, documents) and uses LLM
    to extract structured context blocks. Solves cold start problem.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short (minimum 50 characters)")

    try:
        count = await extract_from_bulk_text(
            project_id=str(project_id),
            text=request.text,
            db_client=auth.client
        )

        return BulkImportResponse(
            blocks_extracted=count,
            project_id=project_id
        )

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/blocks", response_model=list[BlockResponse])
async def list_blocks(project_id: UUID, auth: UserClient):
    """List all blocks in project."""
    try:
        result = auth.client.table("blocks")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .order("created_at", desc=False)\
            .execute()

        return result.data

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/blocks/{block_id}")
async def delete_block(block_id: UUID, auth: UserClient):
    """Delete a block."""
    try:
        result = auth.client.table("blocks")\
            .delete()\
            .eq("id", str(block_id))\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Block not found")

        return {"deleted": True, "id": str(block_id)}

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this block")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/context", response_model=ContextBundle)
async def get_context_bundle(project_id: UUID, auth: UserClient):
    """Get full context bundle (blocks + documents) for agent execution."""
    try:
        # Fetch blocks
        blocks_result = auth.client.table("blocks")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .order("created_at", desc=False)\
            .execute()

        # Fetch documents
        docs_result = auth.client.table("documents")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .order("created_at", desc=False)\
            .execute()

        return ContextBundle(
            project_id=project_id,
            blocks=blocks_result.data,
            documents=docs_result.data
        )

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))
