"""
Memory routes — ADR-108: User Memory Filesystem Migration

Mounted at /api/memory. Reads/writes /memory/ files in workspace_files.
Replaces the user_memory key-value table (ADR-059).

Three files back the Memory page:
  /memory/MEMORY.md      → Profile (name, role, company, timezone, summary)
  /memory/preferences.md → Per-platform tone/verbosity
  /memory/notes.md       → Facts, instructions, preferences (accumulated)

ADR-132 addition:
  /memory/WORK.md        → Work index (structure, scopes, project mappings)

Endpoints:
  GET  /profile              - Get profile fields from MEMORY.md
  PATCH /profile             - Update profile fields in MEMORY.md
  GET  /styles               - Get tone/verbosity from preferences.md
  GET  /styles/{platform}    - Get tone/verbosity for one platform
  PATCH /styles/{platform}   - Set tone/verbosity for a platform
  DELETE /styles/{platform}  - Clear tone/verbosity for a platform
  GET  /user/memories        - List notes from notes.md
  POST /user/memories        - Add a note to notes.md
  POST /user/memories/import - Bulk import: extract from text
  DELETE /memories/{id}      - Delete a note by content hash
  GET  /user/onboarding-state - Detect onboarding state
  POST /user/work            - Save work index (ADR-132)
  GET  /user/work            - Get work index (ADR-132)
  GET  /activity             - List recent activity from activity_log (ADR-063)
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
    """ADR-132: Simplified to work index check. Legacy state fields removed."""
    has_work_index: bool = False


# ─── ADR-132: Topics — macro context baskets that drive project scaffolding ──

class Topic(BaseModel):
    name: str
    lifecycle: str = "persistent"  # 'persistent' | 'bounded'
    projects: list[str] = []  # list of project_slugs (1:N — one topic can have multiple projects)
    status: str = "active"  # 'active' | 'completed'


class TopicsRequest(BaseModel):
    structure: str  # 'single' | 'multi'
    topics: list[Topic]
    name: Optional[str] = None


class TopicsResponse(BaseModel):
    structure: Optional[str] = None
    topics: list[Topic] = []
    exists: bool = False


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
    """Check if user has completed work-first onboarding (ADR-132).

    Returns has_work_index: True if /memory/WORK.md exists.
    Used by auth callback to gate new users to /onboarding.
    """
    try:
        um = UserMemory(auth.client, auth.user_id)
        work_content = await um.read("WORK.md")
        has_work_index = bool(work_content and work_content.strip())

        return OnboardingStateResponse(
            has_work_index=has_work_index,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Topics (ADR-132) ────────────────────────────────────────────────────────

def _format_topics_md(structure: str, topics: list[Topic]) -> str:
    """Format WORK.md from structured topic data."""
    lines = [
        "# Topics\n",
        f"structure: {structure}\n",
        "## Topics\n",
    ]
    for t in topics:
        lines.append(f"- **{t.name}**")
        lines.append(f"  - lifecycle: {t.lifecycle}")
        if t.projects:
            lines.append(f"  - projects: {', '.join(t.projects)}")
        lines.append(f"  - status: {t.status}")
        lines.append("")
    return "\n".join(lines)


def _parse_topics_md(content: str) -> tuple[Optional[str], list[Topic]]:
    """Parse WORK.md back into structured topic data.

    Backward compatible: reads both 'project_slug: x' (old) and 'projects: x, y' (new).
    """
    import re
    structure = None
    topics = []

    struct_match = re.search(r"^structure:\s*(.+)$", content, re.MULTILINE)
    if struct_match:
        structure = struct_match.group(1).strip()

    unit_pattern = re.compile(
        r"- \*\*(.+?)\*\*\n"
        r"((?:  - .+\n?)*)",
        re.MULTILINE,
    )
    for match in unit_pattern.finditer(content):
        name = match.group(1)
        props_text = match.group(2)
        lifecycle = "persistent"
        projects: list[str] = []
        status = "active"
        for prop_line in props_text.strip().split("\n"):
            prop_line = prop_line.strip().lstrip("- ")
            if prop_line.startswith("lifecycle:"):
                lifecycle = prop_line.split(":", 1)[1].strip()
            elif prop_line.startswith("projects:"):
                raw = prop_line.split(":", 1)[1].strip()
                projects = [p.strip() for p in raw.split(",") if p.strip()]
            elif prop_line.startswith("project_slug:"):
                # Backward compat: old format had single project_slug
                slug = prop_line.split(":", 1)[1].strip()
                if slug:
                    projects = [slug]
            elif prop_line.startswith("status:"):
                status = prop_line.split(":", 1)[1].strip()
        topics.append(Topic(
            name=name, lifecycle=lifecycle,
            projects=projects, status=status,
        ))
    return structure, topics


class TopicsSaveResponse(BaseModel):
    structure: Optional[str] = None
    topics: list[Topic] = []
    exists: bool = False
    projects_created: list[dict] = []


@router.post("/user/work", response_model=TopicsSaveResponse)
async def save_topics(body: TopicsRequest, auth: UserClient):
    """Save the user's topics and scaffold projects (ADR-132).

    Topics are macro context baskets — each can drive 1..N projects.
    Called from onboarding page on first setup, and by TP for ongoing updates.
    Initial scaffold creates 1 project per topic; Composer/TP can add more later.
    """
    try:
        um = UserMemory(auth.client, auth.user_id)

        # Update name in profile if provided
        if body.name:
            profile = await um.get_profile()
            if not profile.get("name"):
                await um.update_profile({"name": body.name})

        # Scaffold projects for each topic with type inference
        from services.project_registry import scaffold_project, infer_topic_type
        projects_created = []
        updated_topics = []

        for topic in body.topics:
            if topic.projects:
                updated_topics.append(topic)
                continue

            # Infer agent type and lifecycle from topic name
            inferred_type, inferred_lifecycle, inferred_purpose = infer_topic_type(topic.name)
            lifecycle = topic.lifecycle if topic.lifecycle != "persistent" else inferred_lifecycle
            type_key = "bounded_deliverable" if lifecycle == "bounded" else "workspace"

            result = await scaffold_project(
                client=auth.client,
                user_id=auth.user_id,
                type_key=type_key,
                scope_name=topic.name,
                execute_now=False,
                # Override contributor template with inferred type
                contributors_override=[{
                    "title_template": f"{{scope_name}} {inferred_type.title()}",
                    "role": inferred_type,
                    "scope": "cross_platform",
                    "frequency": "weekly" if lifecycle == "persistent" else "on_demand",
                    "sources_from": "work_unit",
                }] if inferred_type != "briefer" else None,  # briefer is already the default
                objective_override={
                    "deliverable": f"{topic.name} {'deliverable' if lifecycle == 'bounded' else 'update'}",
                    "audience": "You",
                    "format": "email",
                    "purpose": inferred_purpose,
                } if inferred_purpose else None,
            )

            if result.get("success"):
                updated_topics.append(Topic(
                    name=topic.name,
                    lifecycle=topic.lifecycle,
                    projects=[result["project_slug"]],
                    status=topic.status,
                ))
                projects_created.append({
                    "project_slug": result["project_slug"],
                    "title": result["title"],
                    "type_key": type_key,
                    "topic_name": topic.name,
                })
                logger.info(f"[TOPICS] Scaffolded project '{result['project_slug']}' for topic '{topic.name}'")
            else:
                updated_topics.append(topic)
                logger.warning(f"[TOPICS] Scaffold failed for topic '{topic.name}': {result.get('message')}")

        # Write WORK.md with projects backfilled
        content = _format_topics_md(body.structure, updated_topics)
        success = await um.write("WORK.md", content, summary="Topics (ADR-132)")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to write WORK.md")

        return TopicsSaveResponse(
            structure=body.structure,
            topics=updated_topics,
            exists=True,
            projects_created=projects_created,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/work", response_model=TopicsResponse)
async def get_topics(auth: UserClient):
    """Get the user's topics (ADR-132)."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        content = await um.read("WORK.md")
        if not content or not content.strip():
            return TopicsResponse(exists=False)

        structure, topics = _parse_topics_md(content)
        return TopicsResponse(
            structure=structure,
            topics=topics,
            exists=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Brand (ADR-132 — user/topic-level brand context) ────────────────────────

@router.get("/user/brand")
async def get_brand(auth: UserClient, name: str = "default"):
    """Get brand file content. Reads /brand/{name}/BRAND.md from workspace."""
    try:
        path = f"/brand/{name}/BRAND.md"
        result = (
            auth.client.table("workspace_files")
            .select("content")
            .eq("user_id", auth.user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if rows and rows[0].get("content", "").strip():
            return {"content": rows[0]["content"], "exists": True, "brand_name": name}
        return {"content": None, "exists": False, "brand_name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BrandSaveRequest(BaseModel):
    content: str
    name: str = "default"


@router.post("/user/brand")
async def save_brand(body: BrandSaveRequest, auth: UserClient):
    """Save brand file. Writes /brand/{name}/BRAND.md to workspace."""
    try:
        path = f"/brand/{body.name}/BRAND.md"
        from datetime import timezone as _tz
        data = {
            "user_id": auth.user_id,
            "path": path,
            "content": body.content,
            "summary": f"Brand: {body.name}",
            "updated_at": datetime.now(_tz.utc).isoformat(),
        }
        auth.client.table("workspace_files").upsert(
            data, on_conflict="user_id,path"
        ).execute()
        return {"exists": True, "brand_name": body.name}
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
