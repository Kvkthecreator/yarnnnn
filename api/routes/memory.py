"""
Memory routes — ADR-133: Workspace Context Architecture

Mounted at /api/memory. Reads/writes workspace context files:
  /workspace/IDENTITY.md  → User identity (name, role, company, industry)
  /workspace/BRAND.md     → Brand identity (colors, tone, voice)
  /memory/notes.md        → TP-accumulated knowledge (facts, instructions)

Endpoints:
  GET  /profile              - Get identity from /workspace/IDENTITY.md
  PATCH /profile             - Update identity fields
  GET  /user/brand           - Get brand from /workspace/BRAND.md
  POST /user/brand           - Save brand
  GET  /user/memories        - List notes from /memory/notes.md
  POST /user/memories        - Add a note
  POST /user/memories/import - Bulk import from text
  DELETE /memories/{id}      - Delete a note
  GET  /user/onboarding-state - Check if user has projects
  POST /user/onboarding      - Scaffold projects from onboarding
  GET  /activity             - List recent activity
"""

import hashlib
import logging
from fastapi import APIRouter, HTTPException
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
    """ADR-132: Check if user has completed onboarding (has any projects)."""
    has_projects: bool = False


# ─── ADR-132: Onboarding — scaffold projects directly ──

class OnboardingProject(BaseModel):
    name: str


class OnboardingRequest(BaseModel):
    projects: list[OnboardingProject]
    name: Optional[str] = None
    brand_content: Optional[str] = None
    document_ids: Optional[list[str]] = None  # ADR-136: uploaded doc IDs for inference


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
async def get_onboarding_state(auth: UserClient):
    """Check if user has completed onboarding (ADR-132).

    Returns has_projects: True if user has any projects.
    Used by auth callback to gate new users to /onboarding.
    """
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path")
            .eq("user_id", auth.user_id)
            .like("path", "/projects/%/PROJECT.md")
            .limit(1)
            .execute()
        )
        has_projects = len(result.data or []) > 0

        return OnboardingStateResponse(
            has_projects=has_projects,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/user/onboarding")
async def onboarding_scaffold(body: OnboardingRequest, auth: UserClient):
    """Onboarding endpoint — scaffold projects from user's declared workstreams (ADR-132).

    Each project name gets type-inferred (briefer/scout/drafter/etc.) and scaffolded.
    Called from the /onboarding page. Projects are the workstreams — no separate
    "topics" layer.
    """
    try:
        um = UserMemory(auth.client, auth.user_id)

        # ADR-133: Write workspace context first (identity + brand)
        # so scaffold_project() can seed it into projects
        if body.name:
            profile = await um.get_profile()
            if not profile.get("name"):
                await um.update_profile({"name": body.name})

        if body.brand_content:
            await um.write("BRAND.md", body.brand_content, summary="Brand identity")

        # Scaffold projects with LLM inference (ADR-136)
        from services.project_registry import scaffold_project, infer_topic_type
        from services.project_inference import enrich_scaffold_params
        projects_created = []

        # Gather document IDs if provided
        doc_ids = getattr(body, 'document_ids', None) or []

        for proj in body.projects:
            name = proj.name.strip()
            if not name:
                continue

            # ADR-136: Enrich with LLM inference (specific objective, success criteria, output spec)
            overrides = await enrich_scaffold_params(
                auth.client, auth.user_id, name,
                description="",  # Could be enriched from user text
                document_ids=doc_ids,
            )

            # Fallback to lightweight type inference if LLM fails
            inferred_type, inferred_lifecycle, inferred_purpose = infer_topic_type(name)
            type_key = "bounded_deliverable" if inferred_lifecycle == "bounded" else "workspace"

            result = await scaffold_project(
                client=auth.client,
                user_id=auth.user_id,
                type_key=type_key,
                scope_name=name,
                execute_now=False,
                contributors_override=overrides.get("contributors_override") or ([{
                    "title_template": f"{{scope_name}} {inferred_type.title()}",
                    "role": inferred_type,
                    "scope": "cross_platform",
                    "frequency": overrides.get("frequency", "weekly" if inferred_lifecycle == "persistent" else "on_demand"),
                    "sources_from": "work_unit",
                }] if inferred_type != "briefer" else None),
                objective_override=overrides.get("objective_override") or ({
                    "deliverable": f"{name} {'deliverable' if inferred_lifecycle == 'bounded' else 'update'}",
                    "audience": "You",
                    "format": "email",
                    "purpose": inferred_purpose,
                } if inferred_purpose else None),
                assembly_spec_override=overrides.get("assembly_spec_override"),
                success_criteria=overrides.get("_success_criteria"),
                output_spec=overrides.get("_output_spec"),
            )

            if result.get("success"):
                slug = result["project_slug"]
                projects_created.append({
                    "project_slug": slug,
                    "title": result["title"],
                    "type_key": type_key,
                })
                # ADR-133: IDENTITY.md + BRAND.md seeded automatically by scaffold_project()
                logger.info(f"[ONBOARDING] Scaffolded '{slug}' from '{name}'")
            else:
                logger.warning(f"[ONBOARDING] Scaffold failed for '{name}': {result.get('message')}")

        return {"projects_created": projects_created, "count": len(projects_created)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Brand (ADR-133 — workspace-level brand) ────────────────────────────────

@router.get("/user/brand")
async def get_brand(auth: UserClient):
    """Get workspace brand. Reads /workspace/BRAND.md."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        content = await um.read("BRAND.md")
        if content and content.strip():
            return {"content": content, "exists": True}
        return {"content": None, "exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BrandSaveRequest(BaseModel):
    content: str


@router.post("/user/brand")
async def save_brand(body: BrandSaveRequest, auth: UserClient):
    """Save workspace brand. Writes /workspace/BRAND.md."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        success = await um.write("BRAND.md", body.content, summary="Brand identity")
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
    """Get user's profile from /memory/MEMORY.md."""
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
    """Get tone/verbosity preferences from /memory/preferences.md."""
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
    """Set tone/verbosity for a platform in /memory/preferences.md."""
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
            query = query.neq("event_type", "scheduler_heartbeat")

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
