"""
Project and Workspace routes

Endpoints:
- GET /workspace - Get or create user's default workspace
- GET /projects - List all projects (uses default workspace)
- POST /projects - Create project (uses default workspace)
- GET /projects/:id - Get project details
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient

router = APIRouter()


# --- Pydantic Models ---

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    workspace_id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectWithCounts(ProjectResponse):
    memory_count: int = 0
    ticket_count: int = 0


# --- Helper Functions ---

async def get_or_create_workspace(auth: UserClient) -> dict:
    """Get user's default workspace, creating one if it doesn't exist."""
    # Try to get existing workspace
    result = auth.client.table("workspaces")\
        .select("*")\
        .eq("owner_id", auth.user_id)\
        .limit(1)\
        .execute()

    if result.data and len(result.data) > 0:
        return result.data[0]

    # Create default workspace
    create_result = auth.client.table("workspaces").insert({
        "name": "My Workspace",
        "owner_id": auth.user_id
    }).execute()

    if not create_result.data:
        raise HTTPException(status_code=500, detail="Failed to create default workspace")

    return create_result.data[0]


# --- Routes ---

@router.get("/workspace", response_model=WorkspaceResponse)
async def get_workspace(auth: UserClient):
    """Get user's default workspace (auto-creates if needed)."""
    try:
        workspace = await get_or_create_workspace(auth)
        return workspace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(auth: UserClient):
    """List all projects for user (uses default workspace)."""
    try:
        workspace = await get_or_create_workspace(auth)

        result = auth.client.table("projects")\
            .select("*")\
            .eq("workspace_id", workspace["id"])\
            .order("created_at", desc=False)\
            .execute()
        return result.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, auth: UserClient):
    """Create a new project (uses default workspace)."""
    try:
        workspace = await get_or_create_workspace(auth)

        result = auth.client.table("projects").insert({
            "name": project.name,
            "description": project.description,
            "workspace_id": workspace["id"]
        }).execute()

        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create project")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectWithCounts)
async def get_project(project_id: UUID, auth: UserClient):
    """Get project details with counts."""
    try:
        # Get project
        project_result = auth.client.table("projects")\
            .select("*")\
            .eq("id", str(project_id))\
            .single()\
            .execute()

        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get memory count (ADR-005: unified memories table)
        memories_result = auth.client.table("memories")\
            .select("id", count="exact")\
            .eq("project_id", str(project_id))\
            .eq("is_active", True)\
            .execute()

        # Get ticket count
        tickets_result = auth.client.table("work_tickets")\
            .select("id", count="exact")\
            .eq("project_id", str(project_id))\
            .execute()

        return ProjectWithCounts(
            **project_result.data,
            memory_count=memories_result.count or 0,
            ticket_count=tickets_result.count or 0
        )

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))
