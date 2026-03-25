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



@router.post("/user/onboarding")
async def onboarding_scaffold(body: OnboardingRequest, auth: UserClient):
    """Onboarding endpoint — context enrichment + task inference (ADR-138/140).

    Agents are pre-scaffolded at sign-up (ADR-140). Onboarding:
    1. Saves user identity/brand
    2. Reads uploaded documents → enriches /knowledge/
    3. Calls Sonnet to infer tasks from user context
    4. Creates tasks assigned to existing roster agents
    """
    try:
        um = UserMemory(auth.client, auth.user_id)

        # Save identity + brand
        if body.name:
            profile = await um.get_profile()
            if not profile.get("name"):
                await um.update_profile({"name": body.name})

        if body.brand_content:
            await um.write("BRAND.md", body.brand_content, summary="Brand identity")

        # Gather user context for inference
        text_description = ""
        if body.projects:
            text_description = " ".join(p.name for p in body.projects)

        document_contents = []
        if body.document_ids:
            from services.project_inference import read_uploaded_documents
            document_contents = await read_uploaded_documents(
                auth.client, auth.user_id, body.document_ids
            )

        # Skip inference if no context at all
        if not text_description.strip() and not document_contents:
            logger.info("[ONBOARDING] No context provided, skipping task inference")
            return {"tasks_created": [], "count": 0}

        # Infer tasks via Sonnet
        from services.project_inference import infer_work_scopes
        inference = await infer_work_scopes(text_description, document_contents)

        # Save brand if inferred
        brand = inference.get("brand", {})
        if brand.get("name") and not body.brand_content:
            brand_md = f"# {brand['name']}\n\nTone: {brand.get('tone', 'professional')}"
            await um.write("BRAND.md", brand_md, summary="Inferred brand identity")

        # Save user context
        user_context = inference.get("user_context", "")
        if user_context:
            profile = await um.get_profile()
            if not profile.get("context"):
                await um.update_profile({"context": user_context})

        # Get existing roster agents to assign tasks
        roster = (
            auth.client.table("agents")
            .select("id, title, role")
            .eq("user_id", auth.user_id)
            .neq("status", "archived")
            .execute()
        ).data or []
        roster_by_role = {a["role"]: a for a in roster}

        # Create tasks from inferred scopes, assign to existing roster agents
        from services.task_workspace import TaskWorkspace
        from services.workspace import AgentWorkspace, get_agent_slug
        import re
        import json as json_mod

        created = []
        for scope in inference.get("tasks", []):
            try:
                task_title = scope.get("task_title", "New Task")
                task_slug = re.sub(r'[^a-z0-9]+', '-', task_title.lower()).strip('-')[:60]
                cadence = scope.get("cadence", "weekly")
                objective = scope.get("objective", {})
                success_criteria = scope.get("success_criteria", [])
                output_spec = scope.get("output_spec", [])

                # Match inferred agent_role to existing roster agent
                inferred_role = scope.get("agent_role", "research")
                agent = roster_by_role.get(inferred_role, roster_by_role.get("research"))
                if not agent:
                    logger.warning(f"[ONBOARDING] No agent for role {inferred_role}, skipping")
                    continue

                agent_slug = get_agent_slug(agent)

                # Insert task DB row
                task_data = {
                    "user_id": auth.user_id,
                    "slug": task_slug,
                    "status": "active",
                    "schedule": cadence,
                }
                auth.client.table("tasks").insert(task_data).execute()

                # Write TASK.md
                tw = TaskWorkspace(auth.client, auth.user_id, task_slug)
                task_md_parts = [f"# {task_title}\n"]

                if objective:
                    task_md_parts.append("## Objective")
                    for k, v in objective.items():
                        task_md_parts.append(f"- **{k.title()}**: {v}")
                    task_md_parts.append("")

                if success_criteria:
                    task_md_parts.append("## Success Criteria")
                    for c in success_criteria:
                        task_md_parts.append(f"- {c}")
                    task_md_parts.append("")

                task_md_parts.append("## Process")
                task_md_parts.append(f"- **Agent**: {agent_slug}")
                task_md_parts.append(f"- **Cadence**: {cadence}")
                task_md_parts.append("")

                if output_spec:
                    task_md_parts.append("## Output Specification")
                    for s in output_spec:
                        task_md_parts.append(f"- {s}")
                    task_md_parts.append("")

                await tw.write("TASK.md", "\n".join(task_md_parts),
                               summary=f"Task definition for {task_title}")

                # Update agent's tasks.json
                ws = AgentWorkspace(auth.client, auth.user_id, agent_slug)
                tasks_json = await ws.read("memory/tasks.json")
                existing_tasks = json_mod.loads(tasks_json) if tasks_json else []
                existing_tasks.append({"task_slug": task_slug, "task_title": task_title})
                await ws.write("memory/tasks.json", json_mod.dumps(existing_tasks, indent=2),
                               summary="Task assignment")

                created.append({
                    "task_slug": task_slug,
                    "task_title": task_title,
                    "agent_slug": agent_slug,
                    "agent_title": agent["title"],
                    "agent_role": agent["role"],
                })
                logger.info(f"[ONBOARDING] Created task '{task_title}' → {agent['title']}")

            except Exception as e:
                logger.error(f"[ONBOARDING] Failed to create task: {e}")
                continue

        logger.info(f"[ONBOARDING] Created {len(created)} tasks")
        return {"tasks_created": created, "count": len(created)}

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
