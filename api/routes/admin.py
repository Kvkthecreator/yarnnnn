"""
Admin routes for dashboard statistics and user management.

Endpoints:
- GET /stats - Overview dashboard statistics
- GET /users - List users with activity metrics
- GET /memory-stats - Memory system health metrics
- GET /document-stats - Document pipeline statistics
- GET /chat-stats - Chat engagement metrics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone

from services.admin_auth import AdminAuth

router = APIRouter()


# --- Pydantic Models ---

class AdminOverviewStats(BaseModel):
    total_users: int
    total_projects: int
    total_memories: int
    total_documents: int
    total_sessions: int
    # Growth metrics (7-day)
    users_7d: int
    projects_7d: int
    memories_7d: int


class AdminMemoryStats(BaseModel):
    by_source: dict  # {chat: N, document: N, manual: N, import: N}
    by_scope: dict   # {user_scoped: N, project_scoped: N}
    avg_importance: float
    total_active: int
    total_soft_deleted: int


class AdminDocumentStats(BaseModel):
    by_status: dict  # {pending: N, processing: N, completed: N, failed: N}
    total_storage_bytes: int
    total_chunks: int
    avg_chunks_per_doc: float


class AdminChatStats(BaseModel):
    total_sessions: int
    active_sessions: int
    total_messages: int
    avg_messages_per_session: float
    sessions_today: int


class AdminUserRow(BaseModel):
    id: str
    email: str
    created_at: str
    project_count: int
    memory_count: int
    session_count: int
    last_activity: Optional[str] = None


# --- Helper Functions ---

def get_date_threshold(days: int) -> str:
    """Get ISO timestamp for N days ago."""
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    return threshold.isoformat()


# --- Routes ---

@router.get("/stats", response_model=AdminOverviewStats)
async def get_overview_stats(admin: AdminAuth):
    """Get overview dashboard statistics."""
    try:
        client = admin.client
        seven_days_ago = get_date_threshold(7)

        # Total users (derived from workspaces - each user has one workspace)
        users_result = client.table("workspaces").select("id", count="exact").execute()
        total_users = users_result.count or 0

        # Users in last 7 days (workspaces created in last 7 days)
        users_7d_result = client.table("workspaces")\
            .select("id", count="exact")\
            .gte("created_at", seven_days_ago)\
            .execute()
        users_7d = users_7d_result.count or 0

        # Total projects
        projects_result = client.table("projects").select("id", count="exact").execute()
        total_projects = projects_result.count or 0

        # Projects in last 7 days
        projects_7d_result = client.table("projects")\
            .select("id", count="exact")\
            .gte("created_at", seven_days_ago)\
            .execute()
        projects_7d = projects_7d_result.count or 0

        # Total memories (active only)
        memories_result = client.table("memories")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .execute()
        total_memories = memories_result.count or 0

        # Memories in last 7 days
        memories_7d_result = client.table("memories")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .gte("created_at", seven_days_ago)\
            .execute()
        memories_7d = memories_7d_result.count or 0

        # Total documents
        documents_result = client.table("documents").select("id", count="exact").execute()
        total_documents = documents_result.count or 0

        # Total chat sessions
        sessions_result = client.table("chat_sessions").select("id", count="exact").execute()
        total_sessions = sessions_result.count or 0

        return AdminOverviewStats(
            total_users=total_users,
            total_projects=total_projects,
            total_memories=total_memories,
            total_documents=total_documents,
            total_sessions=total_sessions,
            users_7d=users_7d,
            projects_7d=projects_7d,
            memories_7d=memories_7d,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/users", response_model=list[AdminUserRow])
async def list_users(admin: AdminAuth):
    """List all users with activity metrics."""
    try:
        client = admin.client

        # Get users from workspaces (each user has one workspace)
        # We include owner_email from workspaces for digest settings
        workspaces_result = client.table("workspaces")\
            .select("owner_id, owner_email, created_at")\
            .order("created_at", desc=True)\
            .limit(100)\
            .execute()

        if not workspaces_result.data:
            return []

        users = []
        for workspace in workspaces_result.data:
            user_id = workspace["owner_id"]
            user_email = workspace.get("owner_email") or "unknown"
            user_created = workspace["created_at"]

            # Get project count via workspace
            workspaces = client.table("workspaces")\
                .select("id")\
                .eq("owner_id", user_id)\
                .execute()

            project_count = 0
            if workspaces.data:
                workspace_ids = [w["id"] for w in workspaces.data]
                projects = client.table("projects")\
                    .select("id", count="exact")\
                    .in_("workspace_id", workspace_ids)\
                    .execute()
                project_count = projects.count or 0

            # Get memory count
            memories = client.table("memories")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            memory_count = memories.count or 0

            # Get session count
            sessions = client.table("chat_sessions")\
                .select("id, created_at", count="exact")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            session_count = sessions.count or 0

            # Last activity (most recent session)
            last_activity = None
            if sessions.data and len(sessions.data) > 0:
                last_activity = sessions.data[0].get("created_at")

            users.append(AdminUserRow(
                id=user_id,
                email=user_email,
                created_at=user_created,
                project_count=project_count,
                memory_count=memory_count,
                session_count=session_count,
                last_activity=last_activity,
            ))

        return users

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


@router.get("/memory-stats", response_model=AdminMemoryStats)
async def get_memory_stats(admin: AdminAuth):
    """Get memory system health metrics."""
    try:
        client = admin.client

        # By source type
        by_source = {}
        for source in ["chat", "document", "manual", "import"]:
            result = client.table("memories")\
                .select("id", count="exact")\
                .eq("source_type", source)\
                .eq("is_active", True)\
                .execute()
            by_source[source] = result.count or 0

        # By scope (user vs project)
        # Get total active memories first
        total_result = client.table("memories")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .execute()
        total_active_memories = total_result.count or 0

        user_scoped = client.table("memories")\
            .select("id", count="exact")\
            .is_("project_id", "null")\
            .eq("is_active", True)\
            .execute()
        user_scoped_count = user_scoped.count or 0

        # Project-scoped = total - user-scoped (avoids NOT NULL query)
        project_scoped_count = total_active_memories - user_scoped_count

        by_scope = {
            "user_scoped": user_scoped_count,
            "project_scoped": project_scoped_count,
        }

        # Average importance
        all_memories = client.table("memories")\
            .select("importance")\
            .eq("is_active", True)\
            .execute()

        avg_importance = 0.0
        if all_memories.data:
            importances = [m.get("importance", 0) or 0 for m in all_memories.data]
            if importances:
                avg_importance = sum(importances) / len(importances)

        # Total active
        total_active = client.table("memories")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .execute()

        # Total soft-deleted
        total_deleted = client.table("memories")\
            .select("id", count="exact")\
            .eq("is_active", False)\
            .execute()

        return AdminMemoryStats(
            by_source=by_source,
            by_scope=by_scope,
            avg_importance=round(avg_importance, 3),
            total_active=total_active.count or 0,
            total_soft_deleted=total_deleted.count or 0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch memory stats: {str(e)}")


@router.get("/document-stats", response_model=AdminDocumentStats)
async def get_document_stats(admin: AdminAuth):
    """Get document pipeline statistics."""
    try:
        client = admin.client

        # By processing status
        by_status = {}
        for status in ["pending", "processing", "completed", "failed"]:
            result = client.table("documents")\
                .select("id", count="exact")\
                .eq("processing_status", status)\
                .execute()
            by_status[status] = result.count or 0

        # Total storage (sum of file_size)
        all_docs = client.table("documents")\
            .select("file_size")\
            .execute()

        total_storage_bytes = 0
        if all_docs.data:
            total_storage_bytes = sum(d.get("file_size", 0) or 0 for d in all_docs.data)

        # Total chunks
        chunks_result = client.table("chunks")\
            .select("id", count="exact")\
            .execute()
        total_chunks = chunks_result.count or 0

        # Average chunks per document
        total_docs = sum(by_status.values())
        avg_chunks_per_doc = 0.0
        if total_docs > 0:
            avg_chunks_per_doc = total_chunks / total_docs

        return AdminDocumentStats(
            by_status=by_status,
            total_storage_bytes=total_storage_bytes,
            total_chunks=total_chunks,
            avg_chunks_per_doc=round(avg_chunks_per_doc, 2),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document stats: {str(e)}")


@router.get("/chat-stats", response_model=AdminChatStats)
async def get_chat_stats(admin: AdminAuth):
    """Get chat engagement metrics."""
    try:
        client = admin.client
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Total sessions
        total_result = client.table("chat_sessions")\
            .select("id", count="exact")\
            .execute()
        total_sessions = total_result.count or 0

        # Active sessions
        active_result = client.table("chat_sessions")\
            .select("id", count="exact")\
            .eq("status", "active")\
            .execute()
        active_sessions = active_result.count or 0

        # Sessions today
        today_result = client.table("chat_sessions")\
            .select("id", count="exact")\
            .gte("created_at", today.isoformat())\
            .execute()
        sessions_today = today_result.count or 0

        # Total messages
        messages_result = client.table("session_messages")\
            .select("id", count="exact")\
            .execute()
        total_messages = messages_result.count or 0

        # Average messages per session
        avg_messages = 0.0
        if total_sessions > 0:
            avg_messages = total_messages / total_sessions

        return AdminChatStats(
            total_sessions=total_sessions,
            active_sessions=active_sessions,
            total_messages=total_messages,
            avg_messages_per_session=round(avg_messages, 2),
            sessions_today=sessions_today,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat stats: {str(e)}")
