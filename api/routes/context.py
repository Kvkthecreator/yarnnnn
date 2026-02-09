"""
Context routes - Memory management

ADR-005: Unified memory with embeddings
ADR-034: Context v2 - Domain-based scoping

User-scoped endpoints:
- GET /user/memories - List user-scoped memories
- POST /user/memories - Create user memory manually
- POST /user/memories/import - Bulk import text (user-scoped)
- GET /user/onboarding-state - Get onboarding state

Memory management:
- PATCH /memories/:id - Update memory
- DELETE /memories/:id - Soft-delete memory

For domain-scoped memories, use /api/domains/{domain_id}/memories
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient
from services.extraction import extract_from_bulk_text, create_memory_manual

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
    source_ref: Optional[dict] = None  # Platform provenance for imports (ADR-029)
    domain_id: Optional[UUID] = None  # Domain scoping (ADR-034)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BulkImportRequest(BaseModel):
    text: str  # Raw text to extract memories from


class UserBulkImportResponse(BaseModel):
    """Response for user-level bulk import."""
    memories_extracted: int


# --- User Onboarding State ---

class OnboardingStateResponse(BaseModel):
    """Response for onboarding state detection."""
    state: str  # "cold_start", "minimal_context", or "active"
    memory_count: int
    document_count: int
    has_recent_chat: bool


@router.get("/user/onboarding-state", response_model=OnboardingStateResponse)
async def get_onboarding_state(auth: UserClient):
    """
    Detect user's onboarding state for welcome UX.

    States:
    - cold_start: No memories, no documents, no recent chat
    - minimal_context: <3 memories, no recent chat
    - active: Has context, ready to chat
    """
    from datetime import timedelta

    try:
        # Count user memories
        memory_result = auth.client.table("memories")\
            .select("id", count="exact")\
            .eq("user_id", auth.user_id)\
            .eq("is_active", True)\
            .execute()
        memory_count = memory_result.count or 0

        # Count documents
        doc_result = auth.client.table("documents")\
            .select("id", count="exact")\
            .eq("user_id", auth.user_id)\
            .execute()
        document_count = doc_result.count or 0

        # Check for recent chat (within last 7 days)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        session_result = auth.client.table("chat_sessions")\
            .select("id")\
            .eq("user_id", auth.user_id)\
            .gte("updated_at", seven_days_ago)\
            .limit(1)\
            .execute()
        has_recent_chat = len(session_result.data or []) > 0

        # Determine state
        if memory_count == 0 and document_count == 0:
            state = "cold_start"
        elif memory_count < 3 and not has_recent_chat:
            state = "minimal_context"
        else:
            state = "active"

        return OnboardingStateResponse(
            state=state,
            memory_count=memory_count,
            document_count=document_count,
            has_recent_chat=has_recent_chat,
        )

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


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
            .eq("is_active", True)\
            .order("importance", desc=True)\
            .execute()

        return result.data or []

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/memories/import", response_model=UserBulkImportResponse)
async def import_user_memories(request: BulkImportRequest, auth: UserClient):
    """
    Bulk import: paste text → extract user-scoped memories.

    Takes raw text (notes, bios, preferences) and uses LLM to extract
    memories. For onboarding and context bootstrapping.
    """
    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short (minimum 50 characters)")

    try:
        count = await extract_from_bulk_text(
            user_id=auth.user_id,
            project_id=None,  # User-scoped (no project)
            text=request.text,
            db_client=auth.client
        )

        return UserBulkImportResponse(memories_extracted=count)

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
