"""
Deliverables routes - Recurring deliverable management

ADR-018: Recurring Deliverables Product Pivot

Endpoints:
- POST /deliverables - Create a new deliverable
- GET /deliverables - List user's deliverables
- GET /deliverables/:id - Get deliverable with version history
- PATCH /deliverables/:id - Update deliverable settings
- DELETE /deliverables/:id - Archive a deliverable
- POST /deliverables/:id/run - Trigger an ad-hoc run
- GET /deliverables/:id/versions - List versions
- GET /deliverables/:id/versions/:version_id - Get version detail
- PATCH /deliverables/:id/versions/:version_id - Update version (approve, reject, save edits)
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient
from routes.projects import get_or_create_workspace

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class RecipientContext(BaseModel):
    """Who receives the deliverable and what they care about."""
    name: Optional[str] = None
    role: Optional[str] = None
    priorities: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class TemplateStructure(BaseModel):
    """Extracted or defined template for the deliverable."""
    sections: list[str] = Field(default_factory=list)
    typical_length: Optional[str] = None  # e.g., "500-800 words"
    tone: Optional[str] = None  # e.g., "professional", "casual"
    format_notes: Optional[str] = None


class ScheduleConfig(BaseModel):
    """Schedule configuration for recurring execution."""
    frequency: Literal["daily", "weekly", "biweekly", "monthly", "custom"]
    day: Optional[str] = None  # e.g., "monday", "1", "15"
    time: Optional[str] = None  # e.g., "09:00"
    timezone: str = "America/Los_Angeles"
    cron: Optional[str] = None  # For custom frequency


class DataSource(BaseModel):
    """A source of information for the deliverable."""
    type: Literal["url", "document", "description"]
    value: str  # URL, document_id, or description text
    label: Optional[str] = None


class DeliverableCreate(BaseModel):
    """Create deliverable request."""
    title: str
    description: Optional[str] = None
    project_id: Optional[str] = None  # Optional - will create project if not provided
    recipient_context: Optional[RecipientContext] = None
    template_structure: Optional[TemplateStructure] = None
    schedule: ScheduleConfig
    sources: list[DataSource] = Field(default_factory=list)


class DeliverableUpdate(BaseModel):
    """Update deliverable request."""
    title: Optional[str] = None
    description: Optional[str] = None
    recipient_context: Optional[RecipientContext] = None
    template_structure: Optional[TemplateStructure] = None
    schedule: Optional[ScheduleConfig] = None
    sources: Optional[list[DataSource]] = None
    status: Optional[Literal["active", "paused", "archived"]] = None


class DeliverableResponse(BaseModel):
    """Deliverable response."""
    id: str
    title: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    recipient_context: Optional[dict] = None
    template_structure: Optional[dict] = None
    schedule: dict
    sources: list[dict] = Field(default_factory=list)
    status: str
    created_at: str
    updated_at: str
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    version_count: int = 0
    latest_version_status: Optional[str] = None


class VersionResponse(BaseModel):
    """Deliverable version response."""
    id: str
    deliverable_id: str
    version_number: int
    status: str  # generating, staged, reviewing, approved, rejected
    draft_content: Optional[str] = None
    final_content: Optional[str] = None
    edit_distance_score: Optional[float] = None
    feedback_notes: Optional[str] = None
    created_at: str
    staged_at: Optional[str] = None
    approved_at: Optional[str] = None


class VersionUpdate(BaseModel):
    """Update version request (for approval/rejection/editing)."""
    status: Optional[Literal["reviewing", "approved", "rejected"]] = None
    final_content: Optional[str] = None
    feedback_notes: Optional[str] = None


# =============================================================================
# Deliverable CRUD Routes
# =============================================================================

@router.post("")
async def create_deliverable(
    request: DeliverableCreate,
    auth: UserClient,
) -> DeliverableResponse:
    """
    Create a new recurring deliverable.

    If project_id is not provided, creates a new project for this deliverable.
    """
    project_id = request.project_id

    # Create project if not provided
    if not project_id:
        # Get or create workspace first
        workspace = await get_or_create_workspace(auth)

        project_result = (
            auth.client.table("projects")
            .insert({
                "name": request.title,
                "description": f"Project for deliverable: {request.title}",
                "workspace_id": workspace["id"],
            })
            .execute()
        )
        if not project_result.data:
            raise HTTPException(status_code=500, detail="Failed to create project")
        project_id = project_result.data[0]["id"]
        logger.info(f"[DELIVERABLE] Created project {project_id} for deliverable")
    else:
        # Verify project access
        project_check = (
            auth.client.table("projects")
            .select("id")
            .eq("id", project_id)
            .single()
            .execute()
        )
        if not project_check.data:
            raise HTTPException(status_code=404, detail="Project not found")

    # Calculate next_run_at based on schedule
    next_run_at = calculate_next_run(request.schedule)

    # Create deliverable
    deliverable_data = {
        "user_id": auth.user_id,
        "project_id": project_id,
        "title": request.title,
        "description": request.description,
        "recipient_context": request.recipient_context.model_dump() if request.recipient_context else {},
        "template_structure": request.template_structure.model_dump() if request.template_structure else {},
        "schedule": request.schedule.model_dump(),
        "sources": [s.model_dump() for s in request.sources],
        "status": "active",
        "next_run_at": next_run_at,
    }

    result = (
        auth.client.table("deliverables")
        .insert(deliverable_data)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create deliverable")

    deliverable = result.data[0]
    logger.info(f"[DELIVERABLE] Created: {deliverable['id']} - {deliverable['title']}")

    return DeliverableResponse(
        id=deliverable["id"],
        title=deliverable["title"],
        description=deliverable.get("description"),
        project_id=deliverable.get("project_id"),
        recipient_context=deliverable.get("recipient_context"),
        template_structure=deliverable.get("template_structure"),
        schedule=deliverable["schedule"],
        sources=deliverable.get("sources", []),
        status=deliverable["status"],
        created_at=deliverable["created_at"],
        updated_at=deliverable["updated_at"],
        next_run_at=deliverable.get("next_run_at"),
    )


@router.get("")
async def list_deliverables(
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[DeliverableResponse]:
    """
    List user's deliverables.

    Args:
        status: Filter by status (active, paused, archived)
        limit: Maximum results
    """
    query = (
        auth.client.table("deliverables")
        .select("*, deliverable_versions(id, status, version_number)")
        .eq("user_id", auth.user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    deliverables = result.data or []

    responses = []
    for d in deliverables:
        versions = d.get("deliverable_versions", [])
        version_count = len(versions)
        latest_version = max(versions, key=lambda v: v["version_number"]) if versions else None

        responses.append(DeliverableResponse(
            id=d["id"],
            title=d["title"],
            description=d.get("description"),
            project_id=d.get("project_id"),
            recipient_context=d.get("recipient_context"),
            template_structure=d.get("template_structure"),
            schedule=d["schedule"],
            sources=d.get("sources", []),
            status=d["status"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            last_run_at=d.get("last_run_at"),
            next_run_at=d.get("next_run_at"),
            version_count=version_count,
            latest_version_status=latest_version["status"] if latest_version else None,
        ))

    return responses


@router.get("/{deliverable_id}")
async def get_deliverable(
    deliverable_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Get deliverable with recent version history.
    """
    # Get deliverable
    result = (
        auth.client.table("deliverables")
        .select("*")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    deliverable = result.data

    # Get recent versions
    versions_result = (
        auth.client.table("deliverable_versions")
        .select("*")
        .eq("deliverable_id", str(deliverable_id))
        .order("version_number", desc=True)
        .limit(10)
        .execute()
    )

    versions = versions_result.data or []

    return {
        "deliverable": DeliverableResponse(
            id=deliverable["id"],
            title=deliverable["title"],
            description=deliverable.get("description"),
            project_id=deliverable.get("project_id"),
            recipient_context=deliverable.get("recipient_context"),
            template_structure=deliverable.get("template_structure"),
            schedule=deliverable["schedule"],
            sources=deliverable.get("sources", []),
            status=deliverable["status"],
            created_at=deliverable["created_at"],
            updated_at=deliverable["updated_at"],
            last_run_at=deliverable.get("last_run_at"),
            next_run_at=deliverable.get("next_run_at"),
            version_count=len(versions),
        ),
        "versions": [
            VersionResponse(
                id=v["id"],
                deliverable_id=v["deliverable_id"],
                version_number=v["version_number"],
                status=v["status"],
                draft_content=v.get("draft_content"),
                final_content=v.get("final_content"),
                edit_distance_score=v.get("edit_distance_score"),
                feedback_notes=v.get("feedback_notes"),
                created_at=v["created_at"],
                staged_at=v.get("staged_at"),
                approved_at=v.get("approved_at"),
            )
            for v in versions
        ],
    }


@router.patch("/{deliverable_id}")
async def update_deliverable(
    deliverable_id: UUID,
    request: DeliverableUpdate,
    auth: UserClient,
) -> DeliverableResponse:
    """
    Update deliverable settings.
    """
    # Verify ownership
    check = (
        auth.client.table("deliverables")
        .select("id")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    # Build update data
    update_data = {"updated_at": datetime.utcnow().isoformat()}

    if request.title is not None:
        update_data["title"] = request.title
    if request.description is not None:
        update_data["description"] = request.description
    if request.recipient_context is not None:
        update_data["recipient_context"] = request.recipient_context.model_dump()
    if request.template_structure is not None:
        update_data["template_structure"] = request.template_structure.model_dump()
    if request.schedule is not None:
        update_data["schedule"] = request.schedule.model_dump()
        update_data["next_run_at"] = calculate_next_run(request.schedule)
    if request.sources is not None:
        update_data["sources"] = [s.model_dump() for s in request.sources]
    if request.status is not None:
        update_data["status"] = request.status

    result = (
        auth.client.table("deliverables")
        .update(update_data)
        .eq("id", str(deliverable_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update deliverable")

    d = result.data[0]

    return DeliverableResponse(
        id=d["id"],
        title=d["title"],
        description=d.get("description"),
        project_id=d.get("project_id"),
        recipient_context=d.get("recipient_context"),
        template_structure=d.get("template_structure"),
        schedule=d["schedule"],
        sources=d.get("sources", []),
        status=d["status"],
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        last_run_at=d.get("last_run_at"),
        next_run_at=d.get("next_run_at"),
    )


@router.delete("/{deliverable_id}")
async def archive_deliverable(
    deliverable_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Archive a deliverable (soft delete).
    """
    result = (
        auth.client.table("deliverables")
        .update({"status": "archived", "updated_at": datetime.utcnow().isoformat()})
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    logger.info(f"[DELIVERABLE] Archived: {deliverable_id}")

    return {"success": True, "message": "Deliverable archived"}


# =============================================================================
# Pipeline Execution Routes
# =============================================================================

@router.post("/{deliverable_id}/run")
async def trigger_run(
    deliverable_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Trigger an ad-hoc deliverable run.

    Creates a new version and starts the gather → synthesize → stage pipeline.
    """
    from services.deliverable_pipeline import execute_deliverable_pipeline

    # Get deliverable
    result = (
        auth.client.table("deliverables")
        .select("*")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    deliverable = result.data

    if deliverable["status"] == "archived":
        raise HTTPException(status_code=400, detail="Cannot run archived deliverable")

    # Get next version number
    version_result = (
        auth.client.table("deliverable_versions")
        .select("version_number")
        .eq("deliverable_id", str(deliverable_id))
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )

    next_version = 1
    if version_result.data:
        next_version = version_result.data[0]["version_number"] + 1

    logger.info(f"[DELIVERABLE] Triggering run: {deliverable_id} v{next_version}")

    # Execute pipeline
    pipeline_result = await execute_deliverable_pipeline(
        client=auth.client,
        user_id=auth.user_id,
        deliverable_id=str(deliverable_id),
        version_number=next_version,
    )

    return {
        "success": pipeline_result.get("success", False),
        "version_id": pipeline_result.get("version_id"),
        "version_number": next_version,
        "status": pipeline_result.get("status"),
        "message": pipeline_result.get("message"),
    }


# =============================================================================
# Version Management Routes
# =============================================================================

@router.get("/{deliverable_id}/versions")
async def list_versions(
    deliverable_id: UUID,
    auth: UserClient,
    limit: int = 20,
) -> list[VersionResponse]:
    """
    List all versions for a deliverable.
    """
    # Verify ownership
    check = (
        auth.client.table("deliverables")
        .select("id")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    result = (
        auth.client.table("deliverable_versions")
        .select("*")
        .eq("deliverable_id", str(deliverable_id))
        .order("version_number", desc=True)
        .limit(limit)
        .execute()
    )

    versions = result.data or []

    return [
        VersionResponse(
            id=v["id"],
            deliverable_id=v["deliverable_id"],
            version_number=v["version_number"],
            status=v["status"],
            draft_content=v.get("draft_content"),
            final_content=v.get("final_content"),
            edit_distance_score=v.get("edit_distance_score"),
            feedback_notes=v.get("feedback_notes"),
            created_at=v["created_at"],
            staged_at=v.get("staged_at"),
            approved_at=v.get("approved_at"),
        )
        for v in versions
    ]


@router.get("/{deliverable_id}/versions/{version_id}")
async def get_version(
    deliverable_id: UUID,
    version_id: UUID,
    auth: UserClient,
) -> VersionResponse:
    """
    Get a specific version with full content.
    """
    # Verify ownership through deliverable
    check = (
        auth.client.table("deliverables")
        .select("id")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    result = (
        auth.client.table("deliverable_versions")
        .select("*")
        .eq("id", str(version_id))
        .eq("deliverable_id", str(deliverable_id))
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Version not found")

    v = result.data

    return VersionResponse(
        id=v["id"],
        deliverable_id=v["deliverable_id"],
        version_number=v["version_number"],
        status=v["status"],
        draft_content=v.get("draft_content"),
        final_content=v.get("final_content"),
        edit_distance_score=v.get("edit_distance_score"),
        feedback_notes=v.get("feedback_notes"),
        created_at=v["created_at"],
        staged_at=v.get("staged_at"),
        approved_at=v.get("approved_at"),
    )


@router.patch("/{deliverable_id}/versions/{version_id}")
async def update_version(
    deliverable_id: UUID,
    version_id: UUID,
    request: VersionUpdate,
    auth: UserClient,
) -> VersionResponse:
    """
    Update a version (approve, reject, or save edits).

    When final_content differs from draft_content, computes edit diff and score.
    """
    from services.feedback_engine import compute_edit_metrics

    # Verify ownership through deliverable
    check = (
        auth.client.table("deliverables")
        .select("id")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    # Get current version
    version_result = (
        auth.client.table("deliverable_versions")
        .select("*")
        .eq("id", str(version_id))
        .eq("deliverable_id", str(deliverable_id))
        .single()
        .execute()
    )

    if not version_result.data:
        raise HTTPException(status_code=404, detail="Version not found")

    current = version_result.data

    # Build update
    update_data = {}

    if request.status is not None:
        update_data["status"] = request.status
        if request.status == "approved":
            update_data["approved_at"] = datetime.utcnow().isoformat()

    if request.final_content is not None:
        update_data["final_content"] = request.final_content

        # Compute edit metrics if we have both draft and final
        if current.get("draft_content"):
            metrics = compute_edit_metrics(
                draft=current["draft_content"],
                final=request.final_content,
            )
            update_data["edit_diff"] = metrics.get("diff")
            update_data["edit_categories"] = metrics.get("categories")
            update_data["edit_distance_score"] = metrics.get("distance_score")

    if request.feedback_notes is not None:
        update_data["feedback_notes"] = request.feedback_notes

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    result = (
        auth.client.table("deliverable_versions")
        .update(update_data)
        .eq("id", str(version_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update version")

    v = result.data[0]

    logger.info(f"[DELIVERABLE] Version updated: {version_id} -> {v['status']}")

    return VersionResponse(
        id=v["id"],
        deliverable_id=v["deliverable_id"],
        version_number=v["version_number"],
        status=v["status"],
        draft_content=v.get("draft_content"),
        final_content=v.get("final_content"),
        edit_distance_score=v.get("edit_distance_score"),
        feedback_notes=v.get("feedback_notes"),
        created_at=v["created_at"],
        staged_at=v.get("staged_at"),
        approved_at=v.get("approved_at"),
    )


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_next_run(schedule: ScheduleConfig) -> str:
    """
    Calculate the next run timestamp based on schedule configuration.

    For now, returns a simple calculation. Will be enhanced with proper
    cron parsing and timezone handling.
    """
    from datetime import timedelta
    import pytz

    now = datetime.utcnow()
    tz = pytz.timezone(schedule.timezone) if schedule.timezone else pytz.UTC

    # Simple frequency-based calculation
    if schedule.frequency == "daily":
        next_run = now + timedelta(days=1)
    elif schedule.frequency == "weekly":
        next_run = now + timedelta(weeks=1)
    elif schedule.frequency == "biweekly":
        next_run = now + timedelta(weeks=2)
    elif schedule.frequency == "monthly":
        next_run = now + timedelta(days=30)
    else:
        # Custom - default to weekly
        next_run = now + timedelta(weeks=1)

    # If time is specified, set it
    if schedule.time:
        try:
            hour, minute = map(int, schedule.time.split(":"))
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (ValueError, AttributeError):
            pass

    return next_run.isoformat()
