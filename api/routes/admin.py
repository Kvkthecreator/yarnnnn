"""
Admin routes for dashboard statistics and user management.

Endpoints:
- GET /stats - Overview dashboard statistics
- GET /users - List users with activity metrics
- GET /memory-stats - Memory system health metrics
- GET /document-stats - Document pipeline statistics
- GET /chat-stats - Chat engagement metrics
- GET /export/users - Export users data as Excel
- POST /trigger-analysis/{user_id} - Manually trigger conversation analysis (ADR-060)
- POST /trigger-analysis-all - Trigger analysis for all active users
"""

from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
        memories_result = client.table("knowledge_entries")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .execute()
        total_memories = memories_result.count or 0

        # Memories in last 7 days
        memories_7d_result = client.table("knowledge_entries")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .gte("created_at", seven_days_ago)\
            .execute()
        memories_7d = memories_7d_result.count or 0

        # Total documents
        documents_result = client.table("filesystem_documents").select("id", count="exact").execute()
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
            memories = client.table("knowledge_entries")\
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
            result = client.table("knowledge_entries")\
                .select("id", count="exact")\
                .eq("source_type", source)\
                .eq("is_active", True)\
                .execute()
            by_source[source] = result.count or 0

        # By scope (user vs project)
        # Get total active memories first
        total_result = client.table("knowledge_entries")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .execute()
        total_active_memories = total_result.count or 0

        user_scoped = client.table("knowledge_entries")\
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
        all_memories = client.table("knowledge_entries")\
            .select("importance")\
            .eq("is_active", True)\
            .execute()

        avg_importance = 0.0
        if all_memories.data:
            importances = [m.get("importance", 0) or 0 for m in all_memories.data]
            if importances:
                avg_importance = sum(importances) / len(importances)

        # Total active
        total_active = client.table("knowledge_entries")\
            .select("id", count="exact")\
            .eq("is_active", True)\
            .execute()

        # Total soft-deleted
        total_deleted = client.table("knowledge_entries")\
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
            result = client.table("filesystem_documents")\
                .select("id", count="exact")\
                .eq("processing_status", status)\
                .execute()
            by_status[status] = result.count or 0

        # Total storage (sum of file_size)
        all_docs = client.table("filesystem_documents")\
            .select("file_size")\
            .execute()

        total_storage_bytes = 0
        if all_docs.data:
            total_storage_bytes = sum(d.get("file_size", 0) or 0 for d in all_docs.data)

        # Total chunks
        chunks_result = client.table("filesystem_chunks")\
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


@router.get("/export/users")
async def export_users_excel(admin: AdminAuth):
    """Export users data as Excel file."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        # Fetch users data (reuse logic from list_users)
        client = admin.client

        workspaces_result = client.table("workspaces")\
            .select("owner_id, owner_email, created_at")\
            .order("created_at", desc=True)\
            .execute()

        users_data = []
        for workspace in (workspaces_result.data or []):
            user_id = workspace["owner_id"]
            user_email = workspace.get("owner_email") or "unknown"
            user_created = workspace["created_at"]

            # Get project count
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
            memories = client.table("knowledge_entries")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            memory_count = memories.count or 0

            # Get session count and last activity
            sessions = client.table("chat_sessions")\
                .select("id, created_at", count="exact")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            session_count = sessions.count or 0
            last_activity = sessions.data[0].get("created_at") if sessions.data else None

            users_data.append({
                "id": user_id,
                "email": user_email,
                "created_at": user_created,
                "project_count": project_count,
                "memory_count": memory_count,
                "session_count": session_count,
                "last_activity": last_activity,
            })

        # Create Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Users"

        # Header styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Headers
        headers = ["Email", "User ID", "Projects", "Memories", "Sessions", "Last Activity", "Joined"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # Data rows
        for row, user in enumerate(users_data, 2):
            ws.cell(row=row, column=1, value=user["email"]).border = thin_border
            ws.cell(row=row, column=2, value=user["id"]).border = thin_border
            ws.cell(row=row, column=3, value=user["project_count"]).border = thin_border
            ws.cell(row=row, column=4, value=user["memory_count"]).border = thin_border
            ws.cell(row=row, column=5, value=user["session_count"]).border = thin_border
            ws.cell(row=row, column=6, value=user["last_activity"] or "—").border = thin_border
            ws.cell(row=row, column=7, value=user["created_at"]).border = thin_border

        # Auto-adjust column widths
        column_widths = [35, 40, 10, 10, 10, 25, 25]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col)].width = width

        # Freeze header row
        ws.freeze_panes = "A2"

        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"yarnnn_users_{timestamp}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl not installed. Run: pip install openpyxl"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export users: {str(e)}")


@router.get("/export/report")
async def export_full_report(admin: AdminAuth):
    """
    Export comprehensive report as multi-sheet Excel file.

    Sheets:
    - Summary: Key metrics for VC/IR reporting
    - Users: User list with engagement metrics
    - Activity: Weekly signup and engagement trends
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from collections import defaultdict

        client = admin.client
        now = datetime.now(timezone.utc)

        # --- Styling ---
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F46E5", end_color="4F46E5", fill_type="solid")
        metric_label_font = Font(bold=True, size=11)
        metric_value_font = Font(size=14, bold=True)
        section_font = Font(bold=True, size=12, color="4F46E5")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # --- Fetch all data ---

        # Users from workspaces
        workspaces_result = client.table("workspaces")\
            .select("owner_id, owner_email, created_at")\
            .order("created_at", desc=True)\
            .execute()

        # Projects
        projects_result = client.table("projects")\
            .select("id, created_at", count="exact")\
            .execute()
        total_projects = projects_result.count or 0

        # Memories
        memories_result = client.table("knowledge_entries")\
            .select("id, created_at", count="exact")\
            .eq("is_active", True)\
            .execute()
        total_memories = memories_result.count or 0

        # Documents
        docs_result = client.table("filesystem_documents")\
            .select("id, file_size, processing_status", count="exact")\
            .execute()
        total_documents = docs_result.count or 0
        total_storage = sum(d.get("file_size", 0) or 0 for d in (docs_result.data or []))

        # Chat sessions
        sessions_result = client.table("chat_sessions")\
            .select("id, created_at, user_id", count="exact")\
            .execute()
        total_sessions = sessions_result.count or 0

        # Messages
        messages_result = client.table("session_messages")\
            .select("id", count="exact")\
            .execute()
        total_messages = messages_result.count or 0

        # Build users data with metrics
        users_data = []
        for workspace in (workspaces_result.data or []):
            user_id = workspace["owner_id"]
            user_email = workspace.get("owner_email") or "unknown"
            user_created = workspace["created_at"]

            # Project count
            user_workspaces = client.table("workspaces")\
                .select("id")\
                .eq("owner_id", user_id)\
                .execute()
            project_count = 0
            if user_workspaces.data:
                workspace_ids = [w["id"] for w in user_workspaces.data]
                projects = client.table("projects")\
                    .select("id", count="exact")\
                    .in_("workspace_id", workspace_ids)\
                    .execute()
                project_count = projects.count or 0

            # Memory count
            memories = client.table("knowledge_entries")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .execute()
            memory_count = memories.count or 0

            # Session count
            sessions = client.table("chat_sessions")\
                .select("id, created_at", count="exact")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            session_count = sessions.count or 0
            last_activity = sessions.data[0].get("created_at") if sessions.data else None

            users_data.append({
                "id": user_id,
                "email": user_email,
                "created_at": user_created,
                "project_count": project_count,
                "memory_count": memory_count,
                "session_count": session_count,
                "last_activity": last_activity,
            })

        total_users = len(users_data)

        # Calculate growth metrics
        seven_days_ago = (now - timedelta(days=7)).isoformat()
        thirty_days_ago = (now - timedelta(days=30)).isoformat()

        users_7d = sum(1 for u in users_data if u["created_at"] >= seven_days_ago)
        users_30d = sum(1 for u in users_data if u["created_at"] >= thirty_days_ago)

        # Active users (had session in last 7 days)
        active_users_7d = sum(1 for u in users_data if u["last_activity"] and u["last_activity"] >= seven_days_ago)

        # Weekly cohort data for Activity sheet
        weekly_signups = defaultdict(int)
        weekly_sessions = defaultdict(int)

        for user in users_data:
            week = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00")).strftime("%Y-W%W")
            weekly_signups[week] += 1

        for session in (sessions_result.data or []):
            week = datetime.fromisoformat(session["created_at"].replace("Z", "+00:00")).strftime("%Y-W%W")
            weekly_sessions[week] += 1

        # --- Create Workbook ---
        wb = Workbook()

        # ==================== SUMMARY SHEET ====================
        ws_summary = wb.active
        ws_summary.title = "Summary"

        # Title
        ws_summary.merge_cells("A1:D1")
        title_cell = ws_summary["A1"]
        title_cell.value = "yarnnn - Platform Metrics Report"
        title_cell.font = Font(bold=True, size=16)
        title_cell.alignment = Alignment(horizontal="left")

        # Generated date
        ws_summary["A2"] = f"Generated: {now.strftime('%B %d, %Y at %H:%M UTC')}"
        ws_summary["A2"].font = Font(italic=True, color="666666")

        # Key Metrics Section
        row = 4
        ws_summary[f"A{row}"] = "KEY METRICS"
        ws_summary[f"A{row}"].font = section_font
        row += 2

        metrics = [
            ("Total Users", total_users),
            ("Users (Last 7 Days)", users_7d),
            ("Users (Last 30 Days)", users_30d),
            ("Active Users (7 Day)", active_users_7d),
            ("Total Projects", total_projects),
            ("Total Memories", total_memories),
            ("Total Documents", total_documents),
            ("Total Chat Sessions", total_sessions),
            ("Total Messages", total_messages),
        ]

        for i, (label, value) in enumerate(metrics):
            ws_summary[f"A{row + i}"] = label
            ws_summary[f"A{row + i}"].font = metric_label_font
            ws_summary[f"B{row + i}"] = value
            ws_summary[f"B{row + i}"].font = metric_value_font
            ws_summary[f"B{row + i}"].alignment = Alignment(horizontal="right")

        row += len(metrics) + 2

        # Engagement Metrics
        ws_summary[f"A{row}"] = "ENGAGEMENT"
        ws_summary[f"A{row}"].font = section_font
        row += 2

        avg_projects_per_user = total_projects / total_users if total_users > 0 else 0
        avg_memories_per_user = total_memories / total_users if total_users > 0 else 0
        avg_sessions_per_user = total_sessions / total_users if total_users > 0 else 0
        avg_messages_per_session = total_messages / total_sessions if total_sessions > 0 else 0

        engagement_metrics = [
            ("Avg Projects/User", f"{avg_projects_per_user:.1f}"),
            ("Avg Memories/User", f"{avg_memories_per_user:.1f}"),
            ("Avg Sessions/User", f"{avg_sessions_per_user:.1f}"),
            ("Avg Messages/Session", f"{avg_messages_per_session:.1f}"),
            ("Total Storage (MB)", f"{total_storage / (1024*1024):.1f}"),
        ]

        for i, (label, value) in enumerate(engagement_metrics):
            ws_summary[f"A{row + i}"] = label
            ws_summary[f"A{row + i}"].font = metric_label_font
            ws_summary[f"B{row + i}"] = value
            ws_summary[f"B{row + i}"].alignment = Alignment(horizontal="right")

        # Adjust column widths
        ws_summary.column_dimensions["A"].width = 25
        ws_summary.column_dimensions["B"].width = 15

        # ==================== USERS SHEET ====================
        ws_users = wb.create_sheet("Users")

        headers = ["Email", "User ID", "Projects", "Memories", "Sessions", "Last Activity", "Joined"]
        for col, header in enumerate(headers, 1):
            cell = ws_users.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border

        for row_idx, user in enumerate(users_data, 2):
            ws_users.cell(row=row_idx, column=1, value=user["email"]).border = thin_border
            ws_users.cell(row=row_idx, column=2, value=user["id"]).border = thin_border
            ws_users.cell(row=row_idx, column=3, value=user["project_count"]).border = thin_border
            ws_users.cell(row=row_idx, column=4, value=user["memory_count"]).border = thin_border
            ws_users.cell(row=row_idx, column=5, value=user["session_count"]).border = thin_border
            ws_users.cell(row=row_idx, column=6, value=user["last_activity"] or "—").border = thin_border
            ws_users.cell(row=row_idx, column=7, value=user["created_at"]).border = thin_border

        column_widths = [35, 40, 10, 10, 10, 25, 25]
        for col, width in enumerate(column_widths, 1):
            ws_users.column_dimensions[get_column_letter(col)].width = width
        ws_users.freeze_panes = "A2"

        # ==================== ACTIVITY SHEET ====================
        ws_activity = wb.create_sheet("Activity")

        # Get sorted weeks
        all_weeks = sorted(set(weekly_signups.keys()) | set(weekly_sessions.keys()))

        headers = ["Week", "New Users", "Chat Sessions"]
        for col, header in enumerate(headers, 1):
            cell = ws_activity.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border

        for row_idx, week in enumerate(all_weeks, 2):
            ws_activity.cell(row=row_idx, column=1, value=week).border = thin_border
            ws_activity.cell(row=row_idx, column=2, value=weekly_signups.get(week, 0)).border = thin_border
            ws_activity.cell(row=row_idx, column=3, value=weekly_sessions.get(week, 0)).border = thin_border

        ws_activity.column_dimensions["A"].width = 15
        ws_activity.column_dimensions["B"].width = 12
        ws_activity.column_dimensions["C"].width = 15
        ws_activity.freeze_panes = "A2"

        # --- Save and return ---
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"yarnnn_report_{timestamp}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl not installed. Run: pip install openpyxl"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")


# --- Analysis Endpoints (ADR-060) ---

class AnalysisResult(BaseModel):
    """Result of running conversation analysis."""
    user_id: str
    sessions_analyzed: int
    suggestions_created: int
    suggestions: list[dict] = []


@router.post("/trigger-analysis/{user_id}", response_model=AnalysisResult)
async def trigger_analysis_for_user(user_id: str, admin: AdminAuth):
    """
    Manually trigger conversation analysis for a specific user.

    Creates suggested deliverables based on detected conversation patterns.
    Useful for testing the analysis pipeline without waiting for daily cron.
    """
    from services.conversation_analysis import (
        get_recent_sessions,
        get_user_deliverables,
        get_user_knowledge,
        analyze_conversation_patterns,
        create_suggested_deliverable,
    )

    try:
        client = admin.client

        # Get recent sessions
        sessions = await get_recent_sessions(client, user_id, days=7)
        if not sessions:
            return AnalysisResult(
                user_id=user_id,
                sessions_analyzed=0,
                suggestions_created=0,
                suggestions=[],
            )

        # Get existing deliverables and knowledge
        existing = await get_user_deliverables(client, user_id)
        knowledge = await get_user_knowledge(client, user_id)

        # Run analysis
        suggestions = await analyze_conversation_patterns(
            client, user_id, sessions, existing, knowledge
        )

        # Create suggestions that meet threshold
        created_suggestions = []
        for suggestion in suggestions:
            if suggestion.confidence >= 0.50:
                deliverable_id = await create_suggested_deliverable(
                    client, user_id, suggestion
                )
                if deliverable_id:
                    created_suggestions.append({
                        "id": deliverable_id,
                        "title": suggestion.title,
                        "type": suggestion.deliverable_type,
                        "confidence": suggestion.confidence,
                        "reason": suggestion.detection_reason,
                    })

        return AnalysisResult(
            user_id=user_id,
            sessions_analyzed=len(sessions),
            suggestions_created=len(created_suggestions),
            suggestions=created_suggestions,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed for user {user_id}: {str(e)}"
        )


class BulkAnalysisResult(BaseModel):
    """Result of running analysis for all users."""
    users_processed: int
    total_suggestions_created: int
    results: list[AnalysisResult] = []


@router.post("/trigger-analysis-all", response_model=BulkAnalysisResult)
async def trigger_analysis_all_users(admin: AdminAuth):
    """
    Trigger conversation analysis for all users with recent activity.

    Processes users who have had chat sessions in the last 7 days.
    Creates suggested deliverables based on detected patterns.
    """
    from services.conversation_analysis import run_analysis_for_user

    try:
        client = admin.client
        seven_days_ago = get_date_threshold(7)

        # Get users with recent sessions
        sessions_result = (
            client.table("chat_sessions")
            .select("user_id")
            .gte("created_at", seven_days_ago)
            .execute()
        )

        # Get unique user IDs
        user_ids = list(set(s["user_id"] for s in (sessions_result.data or [])))

        results = []
        total_created = 0

        for user_id in user_ids:
            try:
                created = await run_analysis_for_user(client, user_id)
                total_created += created
                results.append(AnalysisResult(
                    user_id=user_id,
                    sessions_analyzed=-1,  # Not tracked in run_analysis_for_user
                    suggestions_created=created,
                    suggestions=[],
                ))
            except Exception as e:
                # Log but continue with other users
                results.append(AnalysisResult(
                    user_id=user_id,
                    sessions_analyzed=0,
                    suggestions_created=0,
                    suggestions=[{"error": str(e)}],
                ))

        return BulkAnalysisResult(
            users_processed=len(user_ids),
            total_suggestions_created=total_created,
            results=results,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bulk analysis failed: {str(e)}"
        )
