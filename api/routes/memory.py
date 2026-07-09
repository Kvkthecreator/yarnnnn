"""
Memory routes — ADR-133 + ADR-206: Workspace Context Architecture

Mounted at /api/memory. Reads/writes workspace context files:
  /workspace/persona/IDENTITY.md  → User identity (ADR-206 relocation)
  /workspace/operation/BRAND.md     → Brand identity (ADR-206 relocation)
  /workspace/system/notes.md              → YARNNN-accumulated knowledge (ADR-206 relocation)

Endpoints:
  GET  /profile              - Get identity from /workspace/persona/IDENTITY.md
  PATCH /profile             - Update identity fields
  GET  /user/brand           - Get brand from /workspace/operation/BRAND.md
  POST /user/brand           - Save brand
  GET  /user/memories        - List notes from /system/notes.md
  POST /user/memories        - Add a note
  POST /user/memories/import - Bulk import from text
  DELETE /memories/{id}      - Delete a note
  GET  /activity             - List recent activity

ADR-244 (2026-05-01): GET /user/onboarding-state DELETED — workspace
lifecycle state moved to GET /api/workspace/state (routes/workspace.py).
The "onboarding" framing dies with the modal; one canonical workspace-state
read.
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
from services.workspace_context import substrate_scope_filter

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


# ADR-244 (2026-05-01): OnboardingStateResponse + GET /user/onboarding-state
# DELETED. Replaced by GET /api/workspace/state (routes/workspace.py) with
# extended shape (substrate_status + capability_gaps + available_programs).
# ADR-144/146/235: POST /user/onboarding deleted — identity/brand authoring is
# inline WriteFile (chat) + context_inference.author_identity (MCP) per ADR-324
# (InferContext dissolved; InferWorkspace removed earlier per ADR-314 D4).


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


# ─── Onboarding endpoints — DELETED ──────────────────────────────────────────
#
# ADR-244 (2026-05-01): GET /user/onboarding-state moved to GET /api/workspace/state
# (routes/workspace.py). Singular implementation: one canonical workspace-state
# read, one canonical URL.
#
# ADR-205 (2026-04-22): _scaffold_default_roster deleted. Was already deprecated
# in favor of workspace_init.initialize_workspace().
#
# ADR-144 / ADR-235 / ADR-146: POST /user/onboarding deleted. Identity/brand
# authoring is inline WriteFile (chat) + author_identity helper (MCP) per ADR-324.


# ─── Brand (ADR-133 — workspace-level brand) ────────────────────────────────

# ─── Identity (ADR-144: workspace-level identity) ────────────────────────────

@router.get("/user/identity")
async def get_identity(auth: UserClient):
    """Get workspace identity. Reads /workspace/persona/IDENTITY.md (ADR-206)."""
    try:
        from services.workspace_paths import PERSONA_IDENTITY_PATH
        um = UserMemory(auth.client, auth.user_id)
        content = await um.read(PERSONA_IDENTITY_PATH)
        if content and content.strip():
            return {"content": content, "exists": True}
        return {"content": None, "exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class IdentitySaveRequest(BaseModel):
    content: str


@router.post("/user/identity")
async def save_identity(body: IdentitySaveRequest, auth: UserClient):
    """Save workspace identity. Writes /workspace/persona/IDENTITY.md (ADR-206).

    ADR-209 Phase 4: operator-initiated edit — attribute to `operator` so the
    RevisionHistoryPanel correctly surfaces this as an operator edit, not a
    system write.
    """
    try:
        from services.workspace_paths import PERSONA_IDENTITY_PATH
        um = UserMemory(auth.client, auth.user_id)
        success = await um.write(
            PERSONA_IDENTITY_PATH,
            body.content,
            summary="User identity",
            authored_by="operator",
            author_identity_uuid=auth.user_id,  # ADR-410/412 viewer pass — which human
            message="edit IDENTITY.md (settings surface)",
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to write IDENTITY.md")
        return {"exists": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Brand — RETIRED (ADR-432 D1c, 2026-07-09) ──────────────────────────────
# The GET/POST /user/brand endpoints are DELETED. operation/BRAND.md was read by
# no producing path; brand voice is a hired agent's output-styling concern that
# homes per-agent (agents/{slug}/) when load-bearing, not a workspace file
# (ADR-432 D1b). This was the one live writer of BRAND.md — removed so nothing
# orphan-writes the retired file.


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
    """List notes from /system/notes.md."""
    try:
        um = UserMemory(auth.client, auth.user_id)
        notes = await um.get_notes()
        return [_note_to_entry(n, i) for i, n in enumerate(notes)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/memories", response_model=NoteEntry)
async def create_user_memory(entry: EntryCreate, auth: UserClient):
    """Add a note to /system/notes.md."""
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
