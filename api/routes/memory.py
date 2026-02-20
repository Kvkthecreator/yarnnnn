"""
Memory routes - ADR-059: Simplified Context Model + ADR-063: Activity Log

Mounted at /api/memory. Single store: user_context table (key/value with source tracking).

Endpoints:
  GET  /profile              - Get profile fields (name, role, company, timezone, summary)
  PATCH /profile             - Upsert profile fields
  GET  /styles               - Get tone/verbosity preferences per platform
  PATCH /styles/{platform}   - Set tone/verbosity for a platform
  GET  /user/memories        - List fact/instruction/preference entries
  POST /user/memories        - Create a knowledge entry
  POST /user/memories/import - Bulk import: extract from text
  DELETE /memories/{id}      - Delete a context entry by id
  GET  /user/onboarding-state - Detect onboarding state
  GET  /activity             - List recent activity from activity_log (ADR-063)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient

router = APIRouter()


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class ProfileResponse(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    summary: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    summary: Optional[str] = None


class StyleItem(BaseModel):
    platform: str
    tone: Optional[str] = None
    verbosity: Optional[str] = None


class StylesListResponse(BaseModel):
    styles: list[StyleItem]


class StyleUpdate(BaseModel):
    tone: Optional[str] = None
    verbosity: Optional[str] = None


class ContextEntry(BaseModel):
    id: UUID
    key: str
    value: str
    source: str
    confidence: float
    source_ref: Optional[UUID] = None  # ADR-072: FK to source record (deliverable_version_id, session_id)
    source_type: Optional[str] = None  # ADR-072: type of source (deliverable_feedback, conversation_extraction, pattern_analysis)
    created_at: datetime
    updated_at: datetime


class EntryCreate(BaseModel):
    content: str
    entry_type: str = "fact"  # 'fact' | 'preference' | 'instruction'


class BulkImportRequest(BaseModel):
    text: str


class BulkImportResponse(BaseModel):
    memories_extracted: int


class OnboardingStateResponse(BaseModel):
    state: str           # 'cold_start' | 'minimal_context' | 'active'
    memory_count: int
    document_count: int
    has_recent_chat: bool


# ─── Helpers ──────────────────────────────────────────────────────────────────

PROFILE_KEYS = {"name", "role", "company", "timezone", "summary"}
ENTRY_PREFIXES = ("fact:", "instruction:", "preference:")


def _upsert_context(client, user_id: str, key: str, value: str, source: str = "user_stated") -> None:
    """Upsert a single key in user_context."""
    client.table("user_context").upsert({
        "user_id": user_id,
        "key": key,
        "value": value,
        "source": source,
        "confidence": 1.0,
        "updated_at": datetime.utcnow().isoformat(),
    }, on_conflict="user_id,key").execute()


def _delete_context_key(client, user_id: str, key: str) -> None:
    """Delete a single key from user_context (hard delete — no need for soft delete here)."""
    client.table("user_context").delete().eq("user_id", user_id).eq("key", key).execute()


# ─── Onboarding ───────────────────────────────────────────────────────────────

@router.get("/user/onboarding-state", response_model=OnboardingStateResponse)
async def get_onboarding_state(auth: UserClient):
    """Detect user's onboarding state for welcome UX."""
    from datetime import timedelta

    try:
        # Count user_context entries (fact/instruction/preference)
        memory_result = auth.client.table("user_context")\
            .select("id", count="exact")\
            .eq("user_id", auth.user_id)\
            .execute()
        memory_count = memory_result.count or 0

        doc_result = auth.client.table("filesystem_documents")\
            .select("id", count="exact")\
            .eq("user_id", auth.user_id)\
            .execute()
        document_count = doc_result.count or 0

        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        session_result = auth.client.table("chat_sessions")\
            .select("id")\
            .eq("user_id", auth.user_id)\
            .gte("updated_at", seven_days_ago)\
            .limit(1)\
            .execute()
        has_recent_chat = len(session_result.data or []) > 0

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
        raise HTTPException(status_code=500, detail=str(e))


# ─── Profile ──────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(auth: UserClient):
    """Get user's profile from user_context."""
    try:
        result = auth.client.table("user_context")\
            .select("key, value")\
            .eq("user_id", auth.user_id)\
            .in_("key", list(PROFILE_KEYS))\
            .execute()

        profile: dict[str, Optional[str]] = {k: None for k in PROFILE_KEYS}
        for row in result.data or []:
            if row["key"] in PROFILE_KEYS:
                profile[row["key"]] = row["value"]

        return ProfileResponse(**profile)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(update: ProfileUpdate, auth: UserClient):
    """Upsert profile fields in user_context."""
    try:
        update_dict = update.model_dump(exclude_none=True)

        for key, value in update_dict.items():
            if key in PROFILE_KEYS:
                if value:
                    _upsert_context(auth.client, auth.user_id, key, value)
                else:
                    # Empty string = clear the field
                    _delete_context_key(auth.client, auth.user_id, key)

        return await get_profile(auth)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Styles ───────────────────────────────────────────────────────────────────

@router.get("/styles", response_model=StylesListResponse)
async def get_styles(auth: UserClient):
    """Get tone/verbosity preferences per platform from user_context."""
    try:
        result = auth.client.table("user_context")\
            .select("key, value")\
            .eq("user_id", auth.user_id)\
            .or_("key.like.tone_%,key.like.verbosity_%")\
            .execute()

        platforms: dict[str, dict] = {}
        for row in result.data or []:
            key = row["key"]
            value = row["value"]
            if key.startswith("tone_"):
                platform = key[5:]
                platforms.setdefault(platform, {})["tone"] = value
            elif key.startswith("verbosity_"):
                platform = key[10:]
                platforms.setdefault(platform, {})["verbosity"] = value

        styles = [
            StyleItem(platform=p, tone=v.get("tone"), verbosity=v.get("verbosity"))
            for p, v in sorted(platforms.items())
        ]

        return StylesListResponse(styles=styles)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/styles/{platform}", response_model=StyleItem)
async def update_style(platform: str, update: StyleUpdate, auth: UserClient):
    """Set tone/verbosity for a platform in user_context."""
    try:
        if update.tone is not None:
            if update.tone:
                _upsert_context(auth.client, auth.user_id, f"tone_{platform}", update.tone)
            else:
                _delete_context_key(auth.client, auth.user_id, f"tone_{platform}")

        if update.verbosity is not None:
            if update.verbosity:
                _upsert_context(auth.client, auth.user_id, f"verbosity_{platform}", update.verbosity)
            else:
                _delete_context_key(auth.client, auth.user_id, f"verbosity_{platform}")

        # Return current state
        result = auth.client.table("user_context")\
            .select("key, value")\
            .eq("user_id", auth.user_id)\
            .in_("key", [f"tone_{platform}", f"verbosity_{platform}"])\
            .execute()

        tone = None
        verbosity = None
        for row in result.data or []:
            if row["key"] == f"tone_{platform}":
                tone = row["value"]
            elif row["key"] == f"verbosity_{platform}":
                verbosity = row["value"]

        return StyleItem(platform=platform, tone=tone, verbosity=verbosity)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Entries (Memories) ───────────────────────────────────────────────────────

@router.get("/user/memories", response_model=list[ContextEntry])
async def list_user_memories(auth: UserClient):
    """
    List knowledge entries from user_context.

    Returns all rows whose key starts with fact:, instruction:, or preference:.
    """
    try:
        result = auth.client.table("user_context")\
            .select("*")\
            .eq("user_id", auth.user_id)\
            .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
            .order("created_at", desc=True)\
            .execute()

        return result.data or []

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/memories", response_model=ContextEntry)
async def create_user_memory(entry: EntryCreate, auth: UserClient):
    """Create a knowledge entry in user_context."""
    try:
        # Build a key from type + content (truncated, alphanumeric)
        import re
        safe_content = re.sub(r'[^a-zA-Z0-9_ -]', '', entry.content)[:60].strip()
        key = f"{entry.entry_type}:{safe_content}"

        now = datetime.utcnow().isoformat()
        record = {
            "user_id": auth.user_id,
            "key": key,
            "value": entry.content,
            "source": "user_stated",
            "confidence": 1.0,
            "created_at": now,
            "updated_at": now,
        }

        result = auth.client.table("user_context")\
            .upsert(record, on_conflict="user_id,key")\
            .execute()

        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create entry")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/memories/import", response_model=BulkImportResponse)
async def import_user_memories(request: BulkImportRequest, auth: UserClient):
    """
    Bulk import: extract knowledge entries from pasted text.

    Uses LLM extraction, then writes results to user_context.
    """
    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short (minimum 50 characters)")

    try:
        from services.memory import extract_from_text_to_user_context
        count = await extract_from_text_to_user_context(
            user_id=auth.user_id,
            text=request.text,
            db_client=auth.client,
        )
        return BulkImportResponse(memories_extracted=count)

    except ImportError:
        # extraction service may not have the new function yet — fall back to 0
        return BulkImportResponse(memories_extracted=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memories/{entry_id}")
async def delete_memory(entry_id: UUID, auth: UserClient):
    """Delete a context entry by id (hard delete)."""
    try:
        result = auth.client.table("user_context")\
            .delete()\
            .eq("id", str(entry_id))\
            .eq("user_id", auth.user_id)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Entry not found")

        return {"deleted": True, "id": str(entry_id)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Activity Log (ADR-063) ───────────────────────────────────────────────────

class ActivityItem(BaseModel):
    id: UUID
    event_type: str
    event_ref: Optional[UUID] = None
    summary: str
    metadata: Optional[dict] = None
    created_at: datetime


class ActivityListResponse(BaseModel):
    activities: list[ActivityItem]
    total: int


@router.get("/activity", response_model=ActivityListResponse)
async def list_activity(
    auth: UserClient,
    limit: int = 50,
    days: int = 30,
    event_type: Optional[str] = None,
):
    """
    List recent activity from activity_log.

    ADR-063: Four-layer model — Activity layer (what YARNNN has done).

    Args:
        limit: Max items to return (default 50)
        days: Lookback window in days (default 30)
        event_type: Filter by type (deliverable_run, memory_written, platform_synced, chat_session)
    """
    from datetime import timedelta

    try:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = auth.client.table("activity_log")\
            .select("*", count="exact")\
            .eq("user_id", auth.user_id)\
            .gte("created_at", since)\
            .order("created_at", desc=True)\
            .limit(limit)

        if event_type:
            query = query.eq("event_type", event_type)

        result = query.execute()

        return ActivityListResponse(
            activities=result.data or [],
            total=result.count or 0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
