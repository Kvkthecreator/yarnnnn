"""
Memory routes — ADR-133 + ADR-206: Workspace Context Architecture

Mounted at /api/memory. Reads/writes workspace context files:
  /workspace/context/_shared/IDENTITY.md  → User identity (ADR-206 relocation)
  /workspace/context/_shared/BRAND.md     → Brand identity (ADR-206 relocation)
  /workspace/memory/notes.md              → YARNNN-accumulated knowledge (ADR-206 relocation)

Endpoints:
  GET  /profile              - Get identity from /workspace/context/_shared/IDENTITY.md
  PATCH /profile             - Update identity fields
  GET  /user/brand           - Get brand from /workspace/context/_shared/BRAND.md
  POST /user/brand           - Save brand
  GET  /user/memories        - List notes from /memory/notes.md
  POST /user/memories        - Add a note
  POST /user/memories/import - Bulk import from text
  DELETE /memories/{id}      - Delete a note
  GET  /user/onboarding-state - Check if user has agents
  POST /user/onboarding      - Scaffold agents + tasks from onboarding
  GET  /activity             - List recent activity
"""

import hashlib
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient
from services.workspace import UserMemory

logger = logging.getLogger(__name__)

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


class NoteEntry(BaseModel):
    """A note from notes.md, presented as a memory entry."""
    id: str  # Content hash (stable identifier for deletion)
    key: str  # Type prefix + truncated content (backwards compat)
    value: str
    source: str
    confidence: float
    source_ref: Optional[UUID] = None
    source_type: Optional[str] = None
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
    """ADR-138: Check if user has completed onboarding (has any agents)."""
    has_agents: bool = False


# ─── ADR-140: Onboarding state (roster scaffolding) ──
# ADR-144/146: POST /user/onboarding deleted — context enrichment via UpdateContext primitive


# ─── Helpers ──────────────────────────────────────────────────────────────────

STYLE_PLATFORM_ALIASES = {}  # ADR-131: No aliases needed (Gmail/Calendar sunset)
ALLOWED_STYLE_PLATFORMS = {"slack", "notion"}


def _normalize_style_platform(platform: str) -> str:
    """Normalize style platform names and enforce allowed user-facing values."""
    normalized = (platform or "").strip().lower()
    normalized = STYLE_PLATFORM_ALIASES.get(normalized, normalized)
    if normalized not in ALLOWED_STYLE_PLATFORMS:
        allowed = ", ".join(sorted(ALLOWED_STYLE_PLATFORMS))
        raise HTTPException(status_code=400, detail=f"Unsupported platform '{platform}'. Allowed: {allowed}")
    return normalized


def _note_to_entry(note: dict, idx: int) -> dict:
    """Convert a parsed note dict to NoteEntry-compatible dict for API response."""
    content = note["content"]
    note_type = note.get("type", "fact")
    content_hash = hashlib.sha256(f"{note_type}:{content}".encode()).hexdigest()[:16]
    now = datetime.utcnow().isoformat()
    return {
        "id": content_hash,
        "key": f"{note_type}:{content[:60]}",
        "value": content,
        "source": "filesystem",
        "confidence": 1.0,
        "source_ref": None,
        "source_type": None,
        "created_at": now,
        "updated_at": now,
    }


# ─── Onboarding ───────────────────────────────────────────────────────────────

@router.get("/user/onboarding-state", response_model=OnboardingStateResponse)
async def get_onboarding_state(request: Request, auth: UserClient):
    """Check if user has completed onboarding (ADR-138/140).

    Lazy scaffolding: if no agents exist, create the default workforce roster.
    Returns has_agents: True if user has any active agents.
    Used by auth callback to gate new users to /onboarding.
    """
    try:
        result = (
            auth.client.table("agents")
            .select("id")
            .eq("user_id", auth.user_id)
            .neq("status", "archived")
            .limit(1)
            .execute()
        )
        has_agents = len(result.data or []) > 0

        # ADR-152: Full workspace initialization on first check
        if not has_agents:
            from services.workspace_init import initialize_workspace
            # Infer timezone from browser header (sent by frontend via X-Timezone).
            # Falls back to UTC inside initialize_workspace if absent or invalid.
            browser_tz = request.headers.get("X-Timezone")
            init_result = await initialize_workspace(auth.client, auth.user_id, browser_tz=browser_tz)
            has_agents = True

            # ADR-179: Write workspace_init_complete system card as persisted session_messages row.
            # Zero LLM cost. TP reads as conversation history on every subsequent turn.
            if not init_result.get("already_initialized"):
                try:
                    from routes.chat import get_or_create_session, append_message
                    session = await get_or_create_session(auth.client, auth.user_id)
                    agents_created = init_result.get("agents_created", [])
                    tasks_created = init_result.get("tasks_created", [])
                    # ADR-219 envelope: workspace_init is the heartbeat
                    # that confirms the operator's account is alive. One
                    # firing per workspace lifetime; material because
                    # everything else depends on it. Role stays
                    # 'assistant' so the frontend continues to render
                    # the SystemCard inside YARNNN's bubble (the
                    # `system_card` metadata key drives the UI dispatch,
                    # not the role).
                    await append_message(
                        client=auth.client,
                        session_id=session["id"],
                        role="assistant",
                        content=(
                            "Your workspace is ready. I've set up 9 agents, scaffolded your "
                            "directories, and scheduled a daily update at 9am. "
                            "Tell me what you work on and I'll set up the rest."
                        ),
                        metadata={
                            "system_card": "workspace_init_complete",
                            "agents_created": len(agents_created),
                            "tasks_created": tasks_created,
                            "summary": "Workspace ready",
                            "pulse": "heartbeat",
                            "weight": "material",
                        },
                    )
                except Exception as card_err:
                    # Non-fatal — workspace init succeeded, card write is best-effort
                    logger.warning(f"[SYSTEM_CARD] Failed to write workspace_init_complete: {card_err}")

        return OnboardingStateResponse(
            has_agents=has_agents,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# _scaffold_default_roster — DELETED (ADR-205 Primitive Collapse, 2026-04-22).
# Was already deprecated in favor of workspace_init.initialize_workspace().
# ADR-144: POST /user/onboarding DELETED — context enrichment now via
# UpdateContext TP primitive (ADR-146).


# ─── Brand (ADR-133 — workspace-level brand) ────────────────────────────────

# ─── Identity (ADR-144: workspace-level identity) ────────────────────────────

@router.get("/user/identity")
async def get_identity(auth: UserClient):
    """Get workspace identity. Reads /workspace/context/_shared/IDENTITY.md (ADR-206)."""
    try:
        from services.workspace_paths import SHARED_IDENTITY_PATH
        um = UserMemory(auth.client, auth.user_id)
        content = await um.read(SHARED_IDENTITY_PATH)
        if content and content.strip():
            return {"content": content, "exists": True}
        return {"content": None, "exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class IdentitySaveRequest(BaseModel):
    content: str


@router.post("/user/identity")
async def save_identity(body: IdentitySaveRequest, auth: UserClient):
    """Save workspace identity. Writes /workspace/context/_shared/IDENTITY.md (ADR-206).

    ADR-209 Phase 4: operator-initiated edit — attribute to `operator` so the
    RevisionHistoryPanel correctly surfaces this as an operator edit, not a
    system write.
    """
    try:
        from services.workspace_paths import SHARED_IDENTITY_PATH
        um = UserMemory(auth.client, auth.user_id)
        success = await um.write(
            SHARED_IDENTITY_PATH,
            body.content,
            summary="User identity",
            authored_by="operator",
            message="edit IDENTITY.md (settings surface)",
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to write IDENTITY.md")
        return {"exists": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Brand (ADR-133 — workspace-level brand) ────────────────────────────────

@router.get("/user/brand")
async def get_brand(auth: UserClient):
    """Get workspace brand. Reads /workspace/context/_shared/BRAND.md (ADR-206)."""
    try:
        from services.workspace_paths import SHARED_BRAND_PATH
        um = UserMemory(auth.client, auth.user_id)
        content = await um.read(SHARED_BRAND_PATH)
        if content and content.strip():
            return {"content": content, "exists": True}
        return {"content": None, "exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BrandSaveRequest(BaseModel):
    content: str


@router.post("/user/brand")
async def save_brand(body: BrandSaveRequest, auth: UserClient):
    """Save workspace brand. Writes /workspace/context/_shared/BRAND.md (ADR-206).

    ADR-209 Phase 4: operator-initiated edit — attribute to `operator`.
    """
    try:
        from services.workspace_paths import SHARED_BRAND_PATH
        um = UserMemory(auth.client, auth.user_id)
        success = await um.write(
            SHARED_BRAND_PATH,
            body.content,
            summary="Brand identity",
            authored_by="operator",
            message="edit BRAND.md (settings surface)",
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to write BRAND.md")
        return {"exists": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Profile ──────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(auth: UserClient):
    """Get user's profile fields. Reads from /workspace/IDENTITY.md via UserMemory."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        profile = await um.get_profile()
        return ProfileResponse(**{k: profile.get(k) for k in ("name", "role", "company", "timezone", "summary")})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(update: ProfileUpdate, auth: UserClient):
    """Update profile fields in /memory/MEMORY.md."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        updates = {}
        for key in update.model_fields_set:
            value = getattr(update, key, None)
            if isinstance(value, str):
                value = value.strip()
            updates[key] = value if value else None
        await um.update_profile(updates)
        return await get_profile(auth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Styles ───────────────────────────────────────────────────────────────────

@router.get("/styles", response_model=StylesListResponse)
async def get_styles(auth: UserClient):
    """Get tone/verbosity preferences from /workspace/style.md."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        prefs = await um.get_preferences()
        styles = [
            StyleItem(platform=p, tone=v.get("tone"), verbosity=v.get("verbosity"))
            for p, v in sorted(prefs.items())
        ]
        return StylesListResponse(styles=styles)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/styles/{platform}", response_model=StyleItem)
async def update_style(platform: str, update: StyleUpdate, auth: UserClient):
    """Set tone/verbosity for a platform in /workspace/style.md."""
    try:
        platform = _normalize_style_platform(platform)
        um = UserMemory(auth.client, auth.user_id)

        updates = {}
        if "tone" in update.model_fields_set:
            updates["tone"] = update.tone.strip() if isinstance(update.tone, str) and update.tone.strip() else None
        if "verbosity" in update.model_fields_set:
            updates["verbosity"] = update.verbosity.strip() if isinstance(update.verbosity, str) and update.verbosity.strip() else None

        await um.update_preferences(platform, updates)

        # Return current state
        prefs = await um.get_preferences()
        platform_prefs = prefs.get(platform, {})
        return StyleItem(platform=platform, tone=platform_prefs.get("tone"), verbosity=platform_prefs.get("verbosity"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/styles/{platform}", response_model=StyleItem)
async def get_style(platform: str, auth: UserClient):
    """Get tone/verbosity for a single platform."""
    try:
        platform = _normalize_style_platform(platform)
        um = UserMemory(auth.client, auth.user_id)
        prefs = await um.get_preferences()
        platform_prefs = prefs.get(platform, {})
        return StyleItem(platform=platform, tone=platform_prefs.get("tone"), verbosity=platform_prefs.get("verbosity"))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/styles/{platform}", response_model=StyleItem)
async def delete_style(platform: str, auth: UserClient):
    """Clear tone/verbosity preferences for a single platform."""
    try:
        platform = _normalize_style_platform(platform)
        um = UserMemory(auth.client, auth.user_id)
        await um.update_preferences(platform, {"tone": None, "verbosity": None})
        return StyleItem(platform=platform, tone=None, verbosity=None)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Entries (Notes/Memories) ────────────────────────────────────────────────

@router.get("/user/memories", response_model=list[NoteEntry])
async def list_user_memories(auth: UserClient):
    """List notes from /memory/notes.md."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        notes = await um.get_notes()
        return [_note_to_entry(n, i) for i, n in enumerate(notes)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/memories", response_model=NoteEntry)
async def create_user_memory(entry: EntryCreate, auth: UserClient):
    """Add a note to /memory/notes.md."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        await um.add_note(entry.entry_type, entry.content)
        note = {"type": entry.entry_type, "content": entry.content}
        return _note_to_entry(note, 0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/memories/import", response_model=BulkImportResponse)
async def import_user_memories(request: BulkImportRequest, auth: UserClient):
    """Bulk import: extract knowledge entries from pasted text → notes.md."""
    if not request.text or len(request.text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Text too short (minimum 50 characters)")

    try:
        from services.memory import extract_from_text_to_user_memory
        count = await extract_from_text_to_user_memory(
            user_id=auth.user_id,
            text=request.text,
            db_client=auth.client,
        )
        return BulkImportResponse(memories_extracted=count)

    except ImportError:
        return BulkImportResponse(memories_extracted=0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memories/{entry_id}")
async def delete_memory(entry_id: str, auth: UserClient):
    """Delete a note by content hash ID."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        notes = await um.get_notes()

        # Find the note matching this hash
        target_note = None
        for note in notes:
            content_hash = hashlib.sha256(
                f"{note.get('type', 'fact')}:{note['content']}".encode()
            ).hexdigest()[:16]
            if content_hash == entry_id:
                target_note = note
                break

        if not target_note:
            raise HTTPException(status_code=404, detail="Entry not found")

        await um.remove_note(target_note["content"])
        return {"deleted": True, "id": entry_id}

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
    limit: int = 200,
    days: int = 30,
    event_type: Optional[str] = None,
):
    """
    List recent activity from activity_log.

    ADR-063: Four-layer model — Activity layer (what YARNNN has done).
    """
    from datetime import timedelta
    from services.supabase import get_service_client

    try:
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()

        client = get_service_client()
        query = client.table("activity_log")\
            .select("*", count="exact")\
            .eq("user_id", auth.user_id)\
            .gte("created_at", since)\
            .order("created_at", desc=True)\
            .limit(limit)

        if event_type:
            query = query.eq("event_type", event_type)
        else:
            # Exclude system heartbeat events — they're noise for the activity page
            query = query.not_.in_("event_type", ["scheduler_heartbeat", "composer_heartbeat"])

        result = query.execute()

        logger.info(
            f"[ACTIVITY] user={auth.user_id[:8]} data_len={len(result.data or [])} "
            f"count={result.count} filter={event_type}"
        )

        return ActivityListResponse(
            activities=result.data or [],
            total=result.count or 0,
        )

    except Exception as e:
        logger.error(f"[ACTIVITY] Error for user={auth.user_id[:8]}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
