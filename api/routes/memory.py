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
  GET  /user/onboarding-state - Check if user has agents
  POST /user/onboarding      - Scaffold agents + tasks from onboarding
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
    """ADR-138: Check if user has completed onboarding (has any agents)."""
    has_agents: bool = False


# ─── ADR-138/140: Onboarding — context enrichment ──

class OnboardingRequest(BaseModel):
    description: Optional[str] = None
    name: Optional[str] = None
    document_ids: Optional[list[str]] = None
    # Legacy field — frontend may still send this
    projects: Optional[list] = None


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

        # ADR-140: Lazy scaffold default workforce roster on first check
        if not has_agents:
            await _scaffold_default_roster(auth.client, auth.user_id)
            # Roster created but no tasks yet — still gate to onboarding
            # for context enrichment. Return has_agents=True so they see the team.
            has_agents = True

        return OnboardingStateResponse(
            has_agents=has_agents,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _scaffold_default_roster(client, user_id: str):
    """Create the default 6-agent workforce roster for a new user (ADR-140).

    Called lazily on first onboarding-state check. Idempotent — checks
    for existing agents before creating.
    """
    from services.agent_framework import AGENT_TYPES, DEFAULT_ROSTER
    from services.agent_creation import create_agent_record

    for agent_def in DEFAULT_ROSTER:
        try:
            type_def = AGENT_TYPES.get(agent_def["role"], {})
            is_bot = type_def.get("class") == "bot"

            await create_agent_record(
                client=client,
                user_id=user_id,
                title=agent_def["title"],
                role=agent_def["role"],
                origin="system_bootstrap",
                agent_instructions=type_def.get("default_instructions", ""),
            )
            logger.info(f"[ROSTER] Created {agent_def['title']} for user {user_id[:8]}")
        except Exception as e:
            # Skip duplicates or errors — best effort
            logger.warning(f"[ROSTER] Failed to create {agent_def['title']}: {e}")

    # ADR-143: Seed TP orchestration playbook at workspace level
    try:
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        existing = await um.read("playbook-orchestration.md")
        if not existing:
            from services.agent_framework import TP_ORCHESTRATION_PLAYBOOK
            await um.write(
                "playbook-orchestration.md",
                TP_ORCHESTRATION_PLAYBOOK,
                summary="ADR-143: TP orchestration playbook (seed)",
            )
            logger.info(f"[ROSTER] Seeded TP orchestration playbook for {user_id[:8]}")
    except Exception as e:
        logger.warning(f"[ROSTER] TP playbook seed failed: {e}")



@router.post("/user/onboarding")
async def onboarding_enrich(body: OnboardingRequest, auth: UserClient):
    """Onboarding endpoint — context enrichment only (ADR-138/140).

    Agents are pre-scaffolded at sign-up. Onboarding enriches the workspace:
    1. Saves user name
    2. Reads uploaded documents
    3. Calls Sonnet to infer identity, brand, domains, work patterns
    4. Writes enriched context to workspace files

    Task creation is NOT done here — it's downstream via TP conversation.
    """
    try:
        um = UserMemory(auth.client, auth.user_id)

        # Save name
        if body.name:
            profile = await um.get_profile()
            if not profile.get("name"):
                await um.update_profile({"name": body.name})

        # Gather context for inference
        text_description = body.description or ""
        # Legacy compat: frontend may send projects[].name as description
        if not text_description and body.projects:
            text_description = " ".join(
                p.get("name", "") if isinstance(p, dict) else str(p)
                for p in body.projects
            )

        document_contents = []
        if body.document_ids:
            from services.context_inference import read_uploaded_documents
            document_contents = await read_uploaded_documents(
                auth.client, auth.user_id, body.document_ids
            )

        # Skip inference if no context at all
        if not text_description.strip() and not document_contents:
            logger.info("[ONBOARDING] No context provided, skipping inference")
            return {
                "enriched": False,
                "identity": {},
                "domains": [],
                "work_patterns": [],
            }

        # Infer workspace context via Sonnet
        from services.context_inference import enrich_context
        inference = await enrich_context(text_description, document_contents)

        # Write identity
        identity = inference.get("identity", {})
        if identity:
            profile_updates = {}
            if identity.get("name") and not body.name:
                profile_updates["name"] = identity["name"]
            if identity.get("role"):
                profile_updates["role"] = identity["role"]
            if identity.get("company"):
                profile_updates["company"] = identity["company"]
            if identity.get("industry"):
                profile_updates["industry"] = identity["industry"]
            if identity.get("context_summary"):
                profile_updates["context"] = identity["context_summary"]
            if profile_updates:
                await um.update_profile(profile_updates)

            # Write enriched IDENTITY.md
            identity_parts = [f"# {identity.get('name', 'User')}"]
            if identity.get("role"):
                identity_parts.append(f"\n**Role**: {identity['role']}")
            if identity.get("company"):
                identity_parts.append(f"**Company**: {identity['company']}")
            if identity.get("industry"):
                identity_parts.append(f"**Industry**: {identity['industry']}")
            if identity.get("context_summary"):
                identity_parts.append(f"\n{identity['context_summary']}")
            await um.write("IDENTITY.md", "\n".join(identity_parts),
                           summary="User identity from onboarding")

        # Write brand
        brand = inference.get("brand", {})
        if brand.get("name"):
            brand_parts = [f"# {brand['name']}"]
            if brand.get("tone"):
                brand_parts.append(f"\n**Tone**: {brand['tone']}")
            if brand.get("voice"):
                brand_parts.append(f"**Voice**: {brand['voice']}")
            await um.write("BRAND.md", "\n".join(brand_parts),
                           summary="Brand identity from onboarding")

        # Write domains + work patterns as workspace context
        domains = inference.get("domains", [])
        patterns = inference.get("work_patterns", [])
        if domains or patterns:
            context_parts = ["# Workspace Context\n"]
            if domains:
                context_parts.append("## Domains of Attention")
                for d in domains:
                    context_parts.append(f"- {d}")
                context_parts.append("")
            if patterns:
                context_parts.append("## Work Patterns")
                for p in patterns:
                    context_parts.append(f"- {p}")
                context_parts.append("")
            await um.write("CONTEXT.md", "\n".join(context_parts),
                           summary="Work context from onboarding")

        logger.info(f"[ONBOARDING] Enriched: {len(domains)} domains, {len(patterns)} patterns")
        return {
            "enriched": True,
            "identity": identity,
            "domains": domains,
            "work_patterns": patterns,
        }

    except Exception as e:
        logger.error(f"[ONBOARDING] Error: {e}")
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
