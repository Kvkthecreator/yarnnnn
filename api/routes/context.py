"""
Context routes - Memory management

ADR-005: Unified memory with embeddings

Endpoints:
- GET /user/memories - List user-scoped memories
- POST /user/memories - Create user memory manually
- PATCH /memories/:id - Update memory
- DELETE /memories/:id - Soft-delete memory
- GET /projects/:id/memories - List project memories
- POST /projects/:id/memories - Create project memory manually
- POST /projects/:id/memories/import - Bulk import text → extract memories
- GET /projects/:id/context - Get full context bundle
- POST /projects/:id/documents - Upload document
- GET /projects/:id/documents - List documents
"""

import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient
from services.extraction import extract_from_bulk_text, create_memory_manual
from services.documents import process_document

router = APIRouter()


# --- Pydantic Models ---

class MemoryCreate(BaseModel):
    content: str
    tags: list[str] = []
    importance: float = 0.5


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    importance: Optional[float] = None


class MemoryResponse(BaseModel):
    id: UUID
    content: str
    tags: list[str]
    entities: dict
    importance: float
    source_type: str
    project_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BulkImportRequest(BaseModel):
    text: str  # Raw text to extract memories from


class BulkImportResponse(BaseModel):
    memories_extracted: int
    project_id: UUID


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_url: str
    file_type: Optional[str]
    file_size: Optional[int]
    processing_status: Optional[str]
    project_id: UUID
    created_at: datetime


class ContextBundleResponse(BaseModel):
    project_id: UUID
    user_memories: list[MemoryResponse]
    project_memories: list[MemoryResponse]
    documents: list[DocumentResponse]


# --- User Memory Routes ---

@router.get("/user/memories", response_model=list[MemoryResponse])
async def list_user_memories(auth: UserClient):
    """
    List all user-scoped memories for the authenticated user.

    Returns items sorted by importance (highest first).
    """
    try:
        result = auth.client.table("memories")\
            .select("*")\
            .eq("user_id", auth.user_id)\
            .is_("project_id", "null")\
            .eq("is_active", True)\
            .order("importance", desc=True)\
            .execute()

        return result.data or []

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/memories", response_model=MemoryResponse)
async def create_user_memory(memory: MemoryCreate, auth: UserClient):
    """Create a user-scoped memory manually."""
    try:
        result = await create_memory_manual(
            user_id=auth.user_id,
            content=memory.content,
            db_client=auth.client,
            project_id=None,  # User-scoped
            tags=memory.tags,
            importance=memory.importance
        )

        if not result:
            raise HTTPException(status_code=400, detail="Failed to create memory")

        return result

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


# --- Project Memory Routes ---

@router.get("/projects/{project_id}/memories", response_model=list[MemoryResponse])
async def list_project_memories(project_id: UUID, auth: UserClient):
    """List all memories for a project (project-scoped only)."""
    try:
        # Verify project access
        project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        result = auth.client.table("memories")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .eq("is_active", True)\
            .order("importance", desc=True)\
            .execute()

        return result.data or []

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/memories", response_model=MemoryResponse)
async def create_project_memory(project_id: UUID, memory: MemoryCreate, auth: UserClient):
    """Create a project-scoped memory manually."""
    try:
        # Verify project access
        project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        result = await create_memory_manual(
            user_id=auth.user_id,
            content=memory.content,
            db_client=auth.client,
            project_id=str(project_id),
            tags=memory.tags,
            importance=memory.importance
        )

        if not result:
            raise HTTPException(status_code=400, detail="Failed to create memory")

        return result

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/memories/import", response_model=BulkImportResponse)
async def import_memories(project_id: UUID, request: BulkImportRequest, auth: UserClient):
    """
    Bulk import: paste text → extract memories.

    Takes raw text (notes, meeting transcripts, documents) and uses LLM
    to extract memories. Solves cold start problem.
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short (minimum 50 characters)")

    try:
        count = await extract_from_bulk_text(
            user_id=auth.user_id,
            project_id=str(project_id),
            text=request.text,
            db_client=auth.client
        )

        return BulkImportResponse(
            memories_extracted=count,
            project_id=project_id
        )

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


# --- Memory Management Routes ---

@router.patch("/memories/{memory_id}", response_model=MemoryResponse)
async def update_memory(memory_id: UUID, update: MemoryUpdate, auth: UserClient):
    """Update a memory (content, tags, or importance)."""
    try:
        # Build update dict with only provided fields
        update_data = {}
        if update.content is not None:
            update_data["content"] = update.content
        if update.tags is not None:
            update_data["tags"] = update.tags
        if update.importance is not None:
            update_data["importance"] = max(0.0, min(1.0, update.importance))

        if not update_data:
            raise HTTPException(status_code=400, detail="No update fields provided")

        update_data["updated_at"] = datetime.utcnow().isoformat()

        result = auth.client.table("memories")\
            .update(update_data)\
            .eq("id", str(memory_id))\
            .eq("user_id", auth.user_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Memory not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: UUID, auth: UserClient):
    """Soft-delete a memory (sets is_active=false)."""
    try:
        result = auth.client.table("memories")\
            .update({
                "is_active": False,
                "updated_at": datetime.utcnow().isoformat()
            })\
            .eq("id", str(memory_id))\
            .eq("user_id", auth.user_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Memory not found")

        return {"deleted": True, "id": str(memory_id)}

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


# --- Context Bundle Route ---

@router.get("/projects/{project_id}/context", response_model=ContextBundleResponse)
async def get_context_bundle(project_id: UUID, auth: UserClient):
    """Get full context bundle (user memories + project memories + documents)."""
    try:
        # Verify project access
        project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Fetch user memories
        user_result = auth.client.table("memories")\
            .select("*")\
            .eq("user_id", auth.user_id)\
            .is_("project_id", "null")\
            .eq("is_active", True)\
            .order("importance", desc=True)\
            .limit(20)\
            .execute()

        # Fetch project memories
        project_mem_result = auth.client.table("memories")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .eq("is_active", True)\
            .order("importance", desc=True)\
            .execute()

        # Fetch documents
        docs_result = auth.client.table("documents")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .order("created_at", desc=False)\
            .execute()

        return ContextBundleResponse(
            project_id=project_id,
            user_memories=user_result.data or [],
            project_memories=project_mem_result.data or [],
            documents=docs_result.data or []
        )

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


# --- Document Routes ---

class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    file_type: str
    file_size: int
    processing_status: str
    project_id: UUID


@router.post("/projects/{project_id}/documents", response_model=DocumentUploadResponse)
async def upload_document(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    auth: UserClient,
    file: UploadFile = File(...)
):
    """
    Upload a document for processing.

    Supports: PDF, DOCX, TXT, MD files.
    Processing happens in background (chunking, embedding, memory extraction).
    """
    # Verify project access
    project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate file type
    allowed_types = {"pdf", "docx", "doc", "txt", "md", "markdown"}
    file_ext = file.filename.split(".")[-1].lower() if file.filename else ""
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {', '.join(allowed_types)}"
        )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Max 10MB
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        # Create document record
        doc_result = auth.client.table("documents").insert({
            "filename": file.filename,
            "file_url": "",  # We don't store the actual file in storage for now
            "file_type": file_ext,
            "file_size": file_size,
            "project_id": str(project_id),
            "processing_status": "pending"
        }).execute()

        if not doc_result.data:
            raise HTTPException(status_code=500, detail="Failed to create document record")

        document = doc_result.data[0]

        # Process document in background
        background_tasks.add_task(
            process_document,
            document_id=document["id"],
            file_content=file_content,
            file_type=file_ext,
            project_id=str(project_id),
            user_id=auth.user_id,
            db_client=auth.client
        )

        return DocumentUploadResponse(
            id=UUID(document["id"]),
            filename=document["filename"],
            file_type=file_ext,
            file_size=file_size,
            processing_status="pending",
            project_id=project_id
        )

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/documents", response_model=list[DocumentResponse])
async def list_documents(project_id: UUID, auth: UserClient):
    """List all documents in a project."""
    try:
        # Verify project access
        project_result = auth.client.table("projects").select("id").eq("id", str(project_id)).single().execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        result = auth.client.table("documents")\
            .select("*")\
            .eq("project_id", str(project_id))\
            .order("created_at", desc=True)\
            .execute()

        return result.data or []

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}")
async def get_document(document_id: UUID, auth: UserClient):
    """Get document details including processing status."""
    try:
        result = auth.client.table("documents")\
            .select("*")\
            .eq("id", str(document_id))\
            .single()\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this document")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(document_id: UUID, auth: UserClient):
    """Delete a document and its chunks."""
    try:
        # Delete chunks first (cascades from document FK)
        auth.client.table("chunks")\
            .delete()\
            .eq("document_id", str(document_id))\
            .execute()

        # Delete document
        result = auth.client.table("documents")\
            .delete()\
            .eq("id", str(document_id))\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"deleted": True, "id": str(document_id)}

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this document")
        raise HTTPException(status_code=500, detail=str(e))
