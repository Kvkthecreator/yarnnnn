"""
Project and Workspace routes

Endpoints:
- GET /workspaces - List user's workspaces
- POST /workspaces - Create workspace
- GET /workspaces/:id/projects - List projects in workspace
- POST /workspaces/:id/projects - Create project
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

class WorkspaceCreate(BaseModel):
    name: str


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
    block_count: int = 0
    ticket_count: int = 0


# --- Routes ---

@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces(db: UserClient):
    """List all workspaces for authenticated user."""
    try:
        result = db.table("workspaces")\
            .select("*")\
            .order("created_at", desc=False)\
            .execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(workspace: WorkspaceCreate, db: UserClient):
    """Create a new workspace."""
    try:
        # Get current user ID from auth
        user_response = db.auth.get_user()
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Could not get user from token")

        user_id = user_response.user.id

        result = db.table("workspaces").insert({
            "name": workspace.name,
            "owner_id": user_id
        }).execute()

        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create workspace")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/projects", response_model=list[ProjectResponse])
async def list_projects(workspace_id: UUID, db: UserClient):
    """List all projects in a workspace."""
    try:
        result = db.table("projects")\
            .select("*")\
            .eq("workspace_id", str(workspace_id))\
            .order("created_at", desc=False)\
            .execute()
        return result.data
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this workspace")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/projects", response_model=ProjectResponse)
async def create_project(workspace_id: UUID, project: ProjectCreate, db: UserClient):
    """Create a new project in a workspace."""
    try:
        result = db.table("projects").insert({
            "name": project.name,
            "description": project.description,
            "workspace_id": str(workspace_id)
        }).execute()

        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create project")

        return result.data[0]

    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this workspace")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}", response_model=ProjectWithCounts)
async def get_project(project_id: UUID, db: UserClient):
    """Get project details with counts."""
    try:
        # Get project
        project_result = db.table("projects")\
            .select("*")\
            .eq("id", str(project_id))\
            .single()\
            .execute()

        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get block count
        blocks_result = db.table("blocks")\
            .select("id", count="exact")\
            .eq("project_id", str(project_id))\
            .execute()

        # Get ticket count
        tickets_result = db.table("work_tickets")\
            .select("id", count="exact")\
            .eq("project_id", str(project_id))\
            .execute()

        return ProjectWithCounts(
            **project_result.data,
            block_count=blocks_result.count or 0,
            ticket_count=tickets_result.count or 0
        )

    except HTTPException:
        raise
    except Exception as e:
        if "violates row-level security" in str(e):
            raise HTTPException(status_code=403, detail="Access denied to this project")
        raise HTTPException(status_code=500, detail=str(e))
