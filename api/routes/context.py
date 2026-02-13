"""
Context routes - Knowledge Base Management (ADR-058)

ADR-058: Knowledge Base Architecture
ADR-034: Context v2 - Domain-based scoping

Knowledge endpoints:
- GET /profile - Get user's knowledge profile
- PATCH /profile - Update user's stated profile fields
- GET /styles - Get user's communication styles
- PATCH /styles/{platform} - Update style preferences

Entry (Memory) endpoints:
- GET /user/memories - List user-scoped knowledge entries
- POST /user/memories - Create knowledge entry manually
- POST /user/memories/import - Bulk import text
- GET /user/onboarding-state - Get onboarding state
- PATCH /memories/:id - Update entry
- DELETE /memories/:id - Soft-delete entry

For domain-scoped entries, use /api/domains/{domain_id}/memories
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
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
        memory_result = auth.client.table("knowledge_entries")\
            .select("id", count="exact")\
            .eq("user_id", auth.user_id)\
            .eq("is_active", True)\
            .execute()
        memory_count = memory_result.count or 0

        # Count documents
        doc_result = auth.client.table("filesystem_documents")\
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
        result = auth.client.table("knowledge_entries")\
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

        result = auth.client.table("knowledge_entries")\
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
        result = auth.client.table("knowledge_entries")\
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


# =============================================================================
# ADR-058: Knowledge Profile Endpoints
# =============================================================================

class ProfileResponse(BaseModel):
    """User's knowledge profile (inferred + stated)."""
    id: Optional[UUID] = None
    # Effective values (stated takes precedence over inferred)
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    summary: Optional[str] = None
    # Source indicators
    name_source: Optional[str] = None  # 'stated' or 'inferred'
    role_source: Optional[str] = None
    company_source: Optional[str] = None
    timezone_source: Optional[str] = None
    summary_source: Optional[str] = None
    # Inference metadata
    last_inferred_at: Optional[datetime] = None
    inference_confidence: Optional[float] = None


class ProfileUpdate(BaseModel):
    """Update user's stated profile fields."""
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    summary: Optional[str] = None


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(auth: UserClient):
    """
    Get user's knowledge profile.

    ADR-058: Returns effective profile (stated values take precedence over inferred).
    """
    try:
        # Use limit(1) instead of maybe_single() to avoid 406 errors
        result = auth.client.table("knowledge_profile")\
            .select("*")\
            .eq("user_id", auth.user_id)\
            .limit(1)\
            .execute()

        if not result.data or len(result.data) == 0:
            # Return empty profile if none exists
            return ProfileResponse()

        row = result.data[0]  # Get first row from list

        # Build effective profile with source indicators
        def get_effective(stated_key: str, inferred_key: str):
            stated = row.get(stated_key)
            inferred = row.get(inferred_key)
            if stated:
                return stated, "stated"
            elif inferred:
                return inferred, "inferred"
            return None, None

        name, name_src = get_effective("stated_name", "inferred_name")
        role, role_src = get_effective("stated_role", "inferred_role")
        company, company_src = get_effective("stated_company", "inferred_company")
        timezone, tz_src = get_effective("stated_timezone", "inferred_timezone")
        summary, summary_src = get_effective("stated_summary", "inferred_summary")

        return ProfileResponse(
            id=row.get("id"),
            name=name,
            role=role,
            company=company,
            timezone=timezone,
            summary=summary,
            name_source=name_src,
            role_source=role_src,
            company_source=company_src,
            timezone_source=tz_src,
            summary_source=summary_src,
            last_inferred_at=row.get("last_inferred_at"),
            inference_confidence=row.get("inference_confidence"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(update: ProfileUpdate, auth: UserClient):
    """
    Update user's stated profile fields.

    ADR-058: Stated values take precedence over inferred values.
    """
    try:
        # Build update data (only include non-None fields)
        update_data = {}
        if update.name is not None:
            update_data["stated_name"] = update.name if update.name else None
        if update.role is not None:
            update_data["stated_role"] = update.role if update.role else None
        if update.company is not None:
            update_data["stated_company"] = update.company if update.company else None
        if update.timezone is not None:
            update_data["stated_timezone"] = update.timezone if update.timezone else None
        if update.summary is not None:
            update_data["stated_summary"] = update.summary if update.summary else None

        if not update_data:
            # No fields to update, just return current profile
            return await get_profile(auth)

        update_data["updated_at"] = datetime.utcnow().isoformat()

        # Check if profile exists (use limit(1) to avoid 406 errors)
        existing = auth.client.table("knowledge_profile")\
            .select("id")\
            .eq("user_id", auth.user_id)\
            .limit(1)\
            .execute()

        if existing.data and len(existing.data) > 0:
            # Update existing
            auth.client.table("knowledge_profile")\
                .update(update_data)\
                .eq("user_id", auth.user_id)\
                .execute()
        else:
            # Create new profile
            update_data["user_id"] = auth.user_id
            auth.client.table("knowledge_profile")\
                .insert(update_data)\
                .execute()

        # Return updated profile
        return await get_profile(auth)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ADR-058: Knowledge Styles Endpoints
# =============================================================================

class StyleResponse(BaseModel):
    """Communication style for a platform."""
    id: Optional[UUID] = None
    platform: str
    tone: Optional[str] = None  # 'casual', 'formal', 'mixed'
    verbosity: Optional[str] = None  # 'minimal', 'moderate', 'detailed'
    formatting: Optional[dict] = None  # {uses_emoji, uses_bullets, etc.}
    vocabulary_notes: Optional[str] = None
    sample_excerpts: Optional[list[str]] = None
    stated_preferences: Optional[dict] = None
    sample_count: int = 0
    last_inferred_at: Optional[datetime] = None


class StylesListResponse(BaseModel):
    """List of all user styles."""
    styles: list[StyleResponse]


class StyleUpdate(BaseModel):
    """Update style preferences for a platform."""
    tone: Optional[str] = None
    verbosity: Optional[str] = None
    stated_preferences: Optional[dict] = None


@router.get("/styles", response_model=StylesListResponse)
async def get_styles(auth: UserClient):
    """
    Get user's communication styles for all platforms.

    ADR-058: Styles are inferred from user-authored content in filesystem_items.
    """
    try:
        result = auth.client.table("knowledge_styles")\
            .select("*")\
            .eq("user_id", auth.user_id)\
            .order("platform")\
            .execute()

        styles = []
        for row in result.data or []:
            styles.append(StyleResponse(
                id=row.get("id"),
                platform=row.get("platform"),
                tone=row.get("tone"),
                verbosity=row.get("verbosity"),
                formatting=row.get("formatting"),
                vocabulary_notes=row.get("vocabulary_notes"),
                sample_excerpts=row.get("sample_excerpts"),
                stated_preferences=row.get("stated_preferences"),
                sample_count=row.get("sample_count", 0),
                last_inferred_at=row.get("last_inferred_at"),
            ))

        return StylesListResponse(styles=styles)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/styles/{platform}", response_model=StyleResponse)
async def get_style(platform: str, auth: UserClient):
    """
    Get user's communication style for a specific platform.
    """
    try:
        result = auth.client.table("knowledge_styles")\
            .select("*")\
            .eq("user_id", auth.user_id)\
            .eq("platform", platform)\
            .maybe_single()\
            .execute()

        if not result.data:
            # Return empty style for platform
            return StyleResponse(platform=platform)

        row = result.data
        return StyleResponse(
            id=row.get("id"),
            platform=row.get("platform"),
            tone=row.get("tone"),
            verbosity=row.get("verbosity"),
            formatting=row.get("formatting"),
            vocabulary_notes=row.get("vocabulary_notes"),
            sample_excerpts=row.get("sample_excerpts"),
            stated_preferences=row.get("stated_preferences"),
            sample_count=row.get("sample_count", 0),
            last_inferred_at=row.get("last_inferred_at"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/styles/{platform}", response_model=StyleResponse)
async def update_style(platform: str, update: StyleUpdate, auth: UserClient):
    """
    Update user's stated style preferences for a platform.

    ADR-058: Stated preferences override inferred styles when generating content.
    """
    try:
        # Build update data
        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if update.tone is not None:
            # Store in stated_preferences
            update_data.setdefault("stated_preferences", {})
            if isinstance(update_data["stated_preferences"], dict):
                update_data["stated_preferences"]["tone"] = update.tone

        if update.verbosity is not None:
            update_data.setdefault("stated_preferences", {})
            if isinstance(update_data["stated_preferences"], dict):
                update_data["stated_preferences"]["verbosity"] = update.verbosity

        if update.stated_preferences is not None:
            update_data["stated_preferences"] = update.stated_preferences

        # Check if style exists
        existing = auth.client.table("knowledge_styles")\
            .select("id, stated_preferences")\
            .eq("user_id", auth.user_id)\
            .eq("platform", platform)\
            .maybe_single()\
            .execute()

        if existing.data:
            # Merge stated_preferences if needed
            if "stated_preferences" in update_data and existing.data.get("stated_preferences"):
                merged = {**existing.data["stated_preferences"], **update_data["stated_preferences"]}
                update_data["stated_preferences"] = merged

            auth.client.table("knowledge_styles")\
                .update(update_data)\
                .eq("user_id", auth.user_id)\
                .eq("platform", platform)\
                .execute()
        else:
            # Create new style record
            update_data["user_id"] = auth.user_id
            update_data["platform"] = platform
            auth.client.table("knowledge_styles")\
                .insert(update_data)\
                .execute()

        # Return updated style
        return await get_style(platform, auth)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
