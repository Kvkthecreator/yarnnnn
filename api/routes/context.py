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


class UserContextItemResponse(BaseModel):
    id: UUID
    category: str
    key: str
    content: str
    importance: float
    confidence: float
    source_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserContextItemUpdate(BaseModel):
    content: Optional[str] = None
    importance: Optional[float] = None


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


# --- User Context Routes (ADR-004) ---

@router.get("/user/context", response_model=list[UserContextItemResponse])
async def list_user_context(auth: UserClient):
    """
    List all user context items for the authenticated user.

    Returns items grouped and sorted by importance (highest first).
    """
    try:
        result = auth.client.table("user_context")\
            .select("*")\
            .eq("user_id", auth.user_id)\
            .order("importance", desc=True)\
            .execute()

        return result.data or []

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/user/context/{item_id}", response_model=UserContextItemResponse)
async def update_user_context_item(
    item_id: UUID,
    update: UserContextItemUpdate,
    auth: UserClient
):
    """Update a user context item (content or importance)."""
    try:
        # Build update dict with only provided fields
        update_data = {}
        if update.content is not None:
            update_data["content"] = update.content
        if update.importance is not None:
            update_data["importance"] = max(0.0, min(1.0, update.importance))

        if not update_data:
            raise HTTPException(status_code=400, detail="No update fields provided")

        update_data["updated_at"] = datetime.utcnow().isoformat()

        result = auth.client.table("user_context")\
            .update(update_data)\
            .eq("id", str(item_id))\
            .eq("user_id", auth.user_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="User context item not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/user/context/{item_id}")
async def delete_user_context_item(item_id: UUID, auth: UserClient):
    """Delete a user context item."""
    try:
        result = auth.client.table("user_context")\
            .delete()\
            .eq("id", str(item_id))\
            .eq("user_id", auth.user_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="User context item not found")

        return {"deleted": True, "id": str(item_id)}

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))
