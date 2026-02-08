"""
Project Resources API - ADR-031 Phase 6

Endpoints for managing project-to-resource mappings.
These link abstract "projects" to concrete platform resources like
Slack channels, Gmail labels, and Notion pages.

Endpoints:
- GET /projects/:id/resources - List resources linked to a project
- POST /projects/:id/resources - Add a resource to a project
- DELETE /projects/:id/resources/:resource_id - Remove a resource
- GET /projects/:id/resources/suggest - Auto-suggest resources for a project
- GET /projects/:id/context-summary - Get cross-platform context summary
"""

import logging
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.supabase import UserClient
from services.cross_platform_synthesizer import (
    get_project_resources,
    add_project_resource,
    suggest_project_resources,
    PlatformResource,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ProjectResourceCreate(BaseModel):
    """Create a project-to-resource mapping."""
    platform: Literal["slack", "gmail", "notion", "calendar"]
    resource_type: str  # channel, label, page, database, calendar
    resource_id: str  # Platform-specific ID
    resource_name: Optional[str] = None  # Human-readable name
    is_primary: bool = False
    include_filters: Optional[dict] = None


class ProjectResourceResponse(BaseModel):
    """Project resource mapping response."""
    id: str
    platform: str
    resource_type: str
    resource_id: str
    resource_name: Optional[str] = None
    is_primary: bool = False
    include_filters: dict = Field(default_factory=dict)
    exclude_filters: dict = Field(default_factory=dict)
    last_synced_at: Optional[str] = None


class ResourceSuggestion(BaseModel):
    """Suggested resource for a project."""
    platform: str
    resource_id: str
    resource_name: Optional[str] = None
    confidence: float  # 0-1 score
    reason: str


class ContextSummaryItem(BaseModel):
    """Summary of context from one resource."""
    platform: str
    resource_id: str
    resource_name: Optional[str] = None
    item_count: int
    latest_item: Optional[str] = None
    oldest_item: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/{project_id}/resources")
async def list_project_resources(
    project_id: UUID,
    platform: Optional[str] = None,
    auth: UserClient = None,
):
    """
    List resources linked to a project.

    Args:
        project_id: Project UUID
        platform: Optional filter by platform (slack, gmail, notion)

    Returns:
        List of ProjectResourceResponse
    """
    # Verify project belongs to user
    project = auth.client.table("projects").select("id, name").eq(
        "id", str(project_id)
    ).single().execute()

    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    resources = await get_project_resources(
        db_client=auth.client,
        project_id=str(project_id),
        platform=platform,
    )

    return [
        ProjectResourceResponse(
            id=r.id,
            platform=r.platform,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            resource_name=r.resource_name,
            is_primary=r.is_primary,
            include_filters=r.include_filters,
            exclude_filters=r.exclude_filters,
            last_synced_at=r.last_synced_at.isoformat() if r.last_synced_at else None,
        )
        for r in resources
    ]


@router.post("/{project_id}/resources")
async def create_project_resource(
    project_id: UUID,
    resource: ProjectResourceCreate,
    auth: UserClient = None,
):
    """
    Add a resource to a project.

    Links a platform resource (Slack channel, Gmail label, etc.)
    to a project for cross-platform synthesis.

    Args:
        project_id: Project UUID
        resource: Resource configuration

    Returns:
        Created ProjectResourceResponse
    """
    # Verify project belongs to user
    project = auth.client.table("projects").select("id, name").eq(
        "id", str(project_id)
    ).single().execute()

    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        created = await add_project_resource(
            db_client=auth.client,
            user_id=auth.user_id,
            project_id=str(project_id),
            platform=resource.platform,
            resource_type=resource.resource_type,
            resource_id=resource.resource_id,
            resource_name=resource.resource_name,
            is_primary=resource.is_primary,
            include_filters=resource.include_filters,
        )

        return ProjectResourceResponse(
            id=created.id,
            platform=created.platform,
            resource_type=created.resource_type,
            resource_id=created.resource_id,
            resource_name=created.resource_name,
            is_primary=created.is_primary,
            include_filters=created.include_filters,
        )

    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail="This resource is already linked to the project"
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/resources/{resource_id}")
async def delete_project_resource(
    project_id: UUID,
    resource_id: UUID,
    auth: UserClient = None,
):
    """
    Remove a resource from a project.

    Args:
        project_id: Project UUID
        resource_id: Resource mapping UUID

    Returns:
        Success message
    """
    # Delete the resource (RLS will ensure user owns it)
    result = auth.client.table("project_resources").delete().eq(
        "id", str(resource_id)
    ).eq(
        "project_id", str(project_id)
    ).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Resource mapping not found")

    return {"status": "ok", "message": "Resource removed from project"}


@router.get("/{project_id}/resources/suggest")
async def suggest_resources(
    project_id: UUID,
    auth: UserClient = None,
):
    """
    Auto-suggest resources for a project.

    Analyzes the user's ephemeral context to find platform resources
    that might be related to the project based on name similarity.

    Args:
        project_id: Project UUID

    Returns:
        List of ResourceSuggestion
    """
    # Get project name
    project = auth.client.table("projects").select("id, name").eq(
        "id", str(project_id)
    ).single().execute()

    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    suggestions = await suggest_project_resources(
        db_client=auth.client,
        user_id=auth.user_id,
        project_name=project.data["name"],
    )

    return [
        ResourceSuggestion(
            platform=s["platform"],
            resource_id=s["resource_id"],
            resource_name=s.get("resource_name"),
            confidence=s["confidence"],
            reason=s["reason"],
        )
        for s in suggestions
    ]


@router.get("/{project_id}/context-summary")
async def get_context_summary(
    project_id: UUID,
    days: int = 7,
    auth: UserClient = None,
):
    """
    Get a summary of cross-platform context for a project.

    Shows how much ephemeral context is available from each
    linked resource, useful for previewing synthesizer output.

    Args:
        project_id: Project UUID
        days: How far back to look (default 7 days)

    Returns:
        List of ContextSummaryItem
    """
    from datetime import datetime, timezone, timedelta

    # Verify project exists
    project = auth.client.table("projects").select("id, name").eq(
        "id", str(project_id)
    ).single().execute()

    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get resources for this project
    resources = await get_project_resources(
        db_client=auth.client,
        project_id=str(project_id),
    )

    if not resources:
        return []

    # Query context for each resource
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    summary = []

    for resource in resources:
        result = auth.client.table("ephemeral_context").select(
            "id, source_timestamp",
            count="exact"
        ).eq(
            "user_id", auth.user_id
        ).eq(
            "platform", resource.platform
        ).eq(
            "resource_id", resource.resource_id
        ).gt(
            "created_at", since.isoformat()
        ).gt(
            "expires_at", now.isoformat()
        ).order("source_timestamp", desc=True).limit(1).execute()

        count = result.count or 0
        latest = None
        oldest = None

        if result.data:
            latest = result.data[0].get("source_timestamp")

            # Get oldest too
            oldest_result = auth.client.table("ephemeral_context").select(
                "source_timestamp"
            ).eq(
                "user_id", auth.user_id
            ).eq(
                "platform", resource.platform
            ).eq(
                "resource_id", resource.resource_id
            ).gt(
                "created_at", since.isoformat()
            ).order("source_timestamp").limit(1).execute()

            if oldest_result.data:
                oldest = oldest_result.data[0].get("source_timestamp")

        summary.append(ContextSummaryItem(
            platform=resource.platform,
            resource_id=resource.resource_id,
            resource_name=resource.resource_name,
            item_count=count,
            latest_item=latest,
            oldest_item=oldest,
        ))

    return summary
