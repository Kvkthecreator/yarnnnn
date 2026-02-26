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

import os
from io import BytesIO

from fastapi import APIRouter, HTTPException, Header
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

        # Total memories (ADR-059: user_context entry-type keys)
        memories_result = client.table("user_context")\
            .select("id", count="exact")\
            .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
            .execute()
        total_memories = memories_result.count or 0

        # Memories in last 7 days
        memories_7d_result = client.table("user_context")\
            .select("id", count="exact")\
            .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
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

            # Get memory count (ADR-059)
            memories = client.table("user_context")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
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

        # ADR-059: user_context replaces knowledge_entries; count by source
        by_source = {}
        for source in ["user_stated", "tp_extracted", "document"]:
            result = client.table("user_context")\
                .select("id", count="exact")\
                .eq("source", source)\
                .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
                .execute()
            by_source[source] = result.count or 0

        # All entry-type context rows
        total_result = client.table("user_context")\
            .select("id", count="exact")\
            .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
            .execute()
        total_active_memories = total_result.count or 0

        by_scope = {
            "user_scoped": total_active_memories,
            "project_scoped": 0,  # ADR-059: no project-scoped memories
        }

        # Average confidence (replaces importance)
        all_memories = client.table("user_context")\
            .select("confidence")\
            .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
            .execute()

        avg_importance = 0.0
        if all_memories.data:
            confidences = [m.get("confidence", 1.0) or 1.0 for m in all_memories.data]
            if confidences:
                avg_importance = sum(confidences) / len(confidences)

        return AdminMemoryStats(
            by_source=by_source,
            by_scope=by_scope,
            avg_importance=round(avg_importance, 3),
            total_active=total_active_memories,
            total_soft_deleted=0,  # ADR-059: hard deletes only
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

            # Get memory count (ADR-059)
            memories = client.table("user_context")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
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

        # Memories (ADR-059: user_context entry-type keys)
        memories_result = client.table("user_context")\
            .select("id, created_at", count="exact")\
            .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
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

            # Memory count (ADR-059)
            memories = client.table("user_context")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .or_("key.like.fact:%,key.like.instruction:%,key.like.preference:%")\
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


# =============================================================================
# Pipeline Observability Endpoints (ADR-073)
# =============================================================================

class AdminSyncHealth(BaseModel):
    """Cross-user sync registry health metrics."""
    total_sources: int = 0
    sources_fresh: int = 0
    sources_stale: int = 0
    sources_never_synced: int = 0
    sources_with_cursor: int = 0
    by_platform: dict = {}
    users_with_sync: int = 0
    last_sync_event_at: Optional[str] = None


class AdminPipelineStats(BaseModel):
    """Pipeline health metrics from platform_content, activity_log, event_trigger_log."""
    # Content layer
    content_total: int = 0
    content_retained: int = 0
    content_ephemeral: int = 0
    content_by_platform: dict = {}
    content_retained_by_reason: dict = {}
    # Scheduler
    last_heartbeat_at: Optional[str] = None
    heartbeats_24h: int = 0
    deliverables_scheduled_24h: int = 0
    deliverables_executed_24h: int = 0
    # Signals
    signals_processed_24h: int = 0
    signals_processed_7d: int = 0
    # Event triggers
    triggers_executed_24h: int = 0
    triggers_skipped_24h: int = 0
    triggers_failed_24h: int = 0


@router.get("/sync-health", response_model=AdminSyncHealth)
async def get_sync_health(admin: AdminAuth):
    """Get cross-user platform sync health metrics from sync_registry."""
    try:
        client = admin.client
        now = datetime.now(timezone.utc)
        freshness_threshold = now - timedelta(hours=24)

        # Fetch all sync_registry rows
        registry_result = client.table("sync_registry").select(
            "user_id, platform, resource_id, last_synced_at, platform_cursor"
        ).execute()

        rows = registry_result.data or []
        total = len(rows)
        fresh = 0
        stale = 0
        never = 0
        with_cursor = 0
        user_ids = set()
        by_platform: dict[str, dict] = {}

        for row in rows:
            platform = row.get("platform", "unknown")
            user_ids.add(row["user_id"])

            if row.get("platform_cursor"):
                with_cursor += 1

            bp = by_platform.setdefault(platform, {"total": 0, "fresh": 0, "stale": 0})
            bp["total"] += 1

            last_synced = row.get("last_synced_at")
            if not last_synced:
                never += 1
            else:
                try:
                    dt = datetime.fromisoformat(last_synced.replace("Z", "+00:00"))
                    if dt >= freshness_threshold:
                        fresh += 1
                        bp["fresh"] += 1
                    else:
                        stale += 1
                        bp["stale"] += 1
                except (ValueError, TypeError):
                    stale += 1
                    bp["stale"] += 1

        # Most recent platform_synced event
        sync_event = client.table("activity_log").select(
            "created_at"
        ).eq("event_type", "platform_synced").order(
            "created_at", desc=True
        ).limit(1).execute()
        last_sync_at = sync_event.data[0]["created_at"] if sync_event.data else None

        return AdminSyncHealth(
            total_sources=total,
            sources_fresh=fresh,
            sources_stale=stale,
            sources_never_synced=never,
            sources_with_cursor=with_cursor,
            by_platform=by_platform,
            users_with_sync=len(user_ids),
            last_sync_event_at=last_sync_at,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sync health: {str(e)}")


@router.get("/pipeline-stats", response_model=AdminPipelineStats)
async def get_pipeline_stats(admin: AdminAuth):
    """Get pipeline health metrics from platform_content, activity_log, event_trigger_log."""
    try:
        client = admin.client
        now = datetime.now(timezone.utc)
        cutoff_24h = (now - timedelta(hours=24)).isoformat()
        cutoff_7d = (now - timedelta(days=7)).isoformat()

        # ─── Content Layer ─────────────────────────────────────────────────────
        # Total non-expired content
        total_result = client.table("platform_content").select(
            "id", count="exact"
        ).or_(f"retained.eq.true,expires_at.gt.{now.isoformat()}").execute()
        content_total = total_result.count or 0

        # Retained content
        retained_result = client.table("platform_content").select(
            "id", count="exact"
        ).eq("retained", True).execute()
        content_retained = retained_result.count or 0

        # By platform
        content_by_platform = {}
        for p in ["slack", "gmail", "notion", "calendar"]:
            p_result = client.table("platform_content").select(
                "id", count="exact"
            ).eq("platform", p).or_(
                f"retained.eq.true,expires_at.gt.{now.isoformat()}"
            ).execute()
            content_by_platform[p] = p_result.count or 0

        # By retention reason
        content_retained_by_reason = {}
        for reason in ["deliverable_execution", "signal_processing", "tp_session"]:
            r_result = client.table("platform_content").select(
                "id", count="exact"
            ).eq("retained", True).eq("retained_reason", reason).execute()
            content_retained_by_reason[reason] = r_result.count or 0

        # ─── Scheduler Health ──────────────────────────────────────────────────
        # Latest heartbeat
        hb_result = client.table("activity_log").select(
            "created_at"
        ).eq("event_type", "scheduler_heartbeat").order(
            "created_at", desc=True
        ).limit(1).execute()
        last_heartbeat = hb_result.data[0]["created_at"] if hb_result.data else None

        # Heartbeats in 24h
        hb_24h = client.table("activity_log").select(
            "id", count="exact"
        ).eq("event_type", "scheduler_heartbeat").gte(
            "created_at", cutoff_24h
        ).execute()
        heartbeats_24h = hb_24h.count or 0

        # Deliverables scheduled 24h
        ds_24h = client.table("activity_log").select(
            "id", count="exact"
        ).eq("event_type", "deliverable_scheduled").gte(
            "created_at", cutoff_24h
        ).execute()
        deliverables_scheduled_24h = ds_24h.count or 0

        # Deliverables executed 24h
        de_24h = client.table("activity_log").select(
            "id", count="exact"
        ).eq("event_type", "deliverable_run").gte(
            "created_at", cutoff_24h
        ).execute()
        deliverables_executed_24h = de_24h.count or 0

        # ─── Signals ──────────────────────────────────────────────────────────
        sig_24h = client.table("activity_log").select(
            "id", count="exact"
        ).eq("event_type", "signal_processed").gte(
            "created_at", cutoff_24h
        ).execute()
        signals_24h = sig_24h.count or 0

        sig_7d = client.table("activity_log").select(
            "id", count="exact"
        ).eq("event_type", "signal_processed").gte(
            "created_at", cutoff_7d
        ).execute()
        signals_7d = sig_7d.count or 0

        # ─── Event Triggers ───────────────────────────────────────────────────
        triggers_executed = 0
        triggers_skipped = 0
        triggers_failed = 0

        try:
            for result_type, counter_name in [
                ("executed", "triggers_executed"),
                ("skipped", "triggers_skipped"),
                ("failed", "triggers_failed"),
            ]:
                t_result = client.table("event_trigger_log").select(
                    "id", count="exact"
                ).eq("result", result_type).gte(
                    "triggered_at", cutoff_24h
                ).execute()
                if counter_name == "triggers_executed":
                    triggers_executed = t_result.count or 0
                elif counter_name == "triggers_skipped":
                    triggers_skipped = t_result.count or 0
                else:
                    triggers_failed = t_result.count or 0
        except Exception:
            pass  # event_trigger_log may not have data yet

        return AdminPipelineStats(
            content_total=content_total,
            content_retained=content_retained,
            content_ephemeral=content_total - content_retained,
            content_by_platform=content_by_platform,
            content_retained_by_reason=content_retained_by_reason,
            last_heartbeat_at=last_heartbeat,
            heartbeats_24h=heartbeats_24h,
            deliverables_scheduled_24h=deliverables_scheduled_24h,
            deliverables_executed_24h=deliverables_executed_24h,
            signals_processed_24h=signals_24h,
            signals_processed_7d=signals_7d,
            triggers_executed_24h=triggers_executed,
            triggers_skipped_24h=triggers_skipped,
            triggers_failed_24h=triggers_failed,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pipeline stats: {str(e)}")


# =============================================================================
# Admin Sync Trigger (for testing)
# =============================================================================

@router.post("/trigger-sync/{user_id}/{provider}")
async def admin_trigger_sync(
    user_id: str,
    provider: str,
    x_service_key: Optional[str] = Header(None),
) -> dict:
    """
    Admin endpoint to trigger platform sync for a specific user+provider.
    Protected by service key header. Runs synchronously and returns results.
    """
    from workers.platform_worker import _sync_platform_async

    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not x_service_key or x_service_key != supabase_key:
        raise HTTPException(status_code=403, detail="Invalid service key")

    supabase_url = os.environ.get("SUPABASE_URL", "")
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Missing Supabase credentials")

    try:
        result = await _sync_platform_async(
            user_id=user_id,
            provider=provider,
            selected_sources=None,  # Will be fetched from landscape
            supabase_url=supabase_url,
            supabase_key=supabase_key,
        )
        return {
            "user_id": user_id,
            "provider": provider,
            "result": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/trigger-signal-processing/{user_id}")
async def admin_trigger_signal_processing(
    user_id: str,
    x_service_key: Optional[str] = Header(None),
) -> dict:
    """
    Admin endpoint to trigger signal processing for a specific user.
    Protected by service key header. Runs synchronously and returns results.
    """
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not x_service_key or x_service_key != supabase_key:
        raise HTTPException(status_code=403, detail="Invalid service key")

    supabase_url = os.environ.get("SUPABASE_URL", "")
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Missing Supabase credentials")

    from supabase import create_client
    from services.signal_extraction import extract_signal_summary
    from services.signal_processing import process_signal

    client = create_client(supabase_url, supabase_key)

    try:
        # Extract signals from platform_content
        summary = await extract_signal_summary(client, user_id)
        extraction_result = {
            "platforms_queried": summary.platforms_queried,
            "total_items": summary.total_items,
            "has_calendar": summary.calendar_content is not None,
            "has_gmail": summary.gmail_content is not None,
            "has_slack": summary.slack_content is not None,
            "has_notion": summary.notion_content is not None,
        }

        if summary.total_items == 0:
            return {
                "user_id": user_id,
                "status": "no_content",
                "extraction": extraction_result,
                "processing": None,
            }

        # Gather context needed by process_signal
        uc_result = client.table("user_context").select("*").eq("user_id", user_id).execute()
        user_context = uc_result.data or []

        al_result = client.table("activity_log").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).limit(20).execute()
        recent_activity = al_result.data or []

        dl_result = client.table("deliverables").select("*").eq(
            "user_id", user_id
        ).in_("status", ["active", "paused"]).execute()
        existing_deliverables = dl_result.data or []

        # Process signals (LLM triage)
        processing_result = await process_signal(
            client, user_id, summary, user_context, recent_activity, existing_deliverables
        )

        return {
            "user_id": user_id,
            "status": "completed",
            "extraction": extraction_result,
            "processing": {
                "signals_detected": getattr(processing_result, "signals_detected", 0),
                "actions": [str(a) for a in getattr(processing_result, "actions", [])],
                "reasoning": getattr(processing_result, "reasoning_summary", ""),
            },
        }
    except Exception as e:
        import traceback
        return {
            "user_id": user_id,
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


# =============================================================================
# Admin Deliverable Run Trigger (for testing)
# =============================================================================

@router.post("/trigger-deliverable/{deliverable_id}")
async def admin_trigger_deliverable(
    deliverable_id: str,
    x_service_key: Optional[str] = Header(None),
) -> dict:
    """
    Admin endpoint to trigger a deliverable run.
    Protected by service key header. Runs full pipeline and returns results.
    """
    from services.deliverable_execution import execute_deliverable_generation

    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not x_service_key or x_service_key != supabase_key:
        raise HTTPException(status_code=403, detail="Invalid service key")

    supabase_url = os.environ.get("SUPABASE_URL", "")
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=500, detail="Missing Supabase credentials")

    from supabase import create_client
    client = create_client(supabase_url, supabase_key)

    # Fetch deliverable
    result = client.table("deliverables").select("*").eq("id", deliverable_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    deliverable = result.data
    user_id = deliverable["user_id"]

    try:
        exec_result = await execute_deliverable_generation(
            client=client,
            user_id=user_id,
            deliverable=deliverable,
            trigger_context={"type": "admin_test"},
        )
        return {
            "deliverable_id": deliverable_id,
            "deliverable_type": deliverable.get("deliverable_type"),
            "title": deliverable.get("title"),
            "success": exec_result.get("success", False),
            "version_id": exec_result.get("version_id"),
            "version_number": exec_result.get("version_number"),
            "status": exec_result.get("status"),
            "message": exec_result.get("message"),
        }
    except Exception as e:
        import traceback
        return {
            "deliverable_id": deliverable_id,
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@router.post("/backfill-sources/{user_id}")
async def admin_backfill_sources(
    user_id: str,
    x_service_key: Optional[str] = Header(None),
) -> dict:
    """
    ADR-078: Backfill selected_sources for a user using smart auto-selection.

    For each connected platform, if the current selected_sources count is below
    the tier limit, expands selection using compute_smart_defaults heuristics.
    """
    from supabase import create_client
    from services.landscape import compute_smart_defaults
    from services.platform_limits import get_limits_for_user, PROVIDER_LIMIT_MAP

    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not x_service_key or x_service_key != supabase_key:
        raise HTTPException(status_code=403, detail="Invalid service key")

    supabase_url = os.environ.get("SUPABASE_URL", "")
    client = create_client(supabase_url, supabase_key)

    limits = get_limits_for_user(client, user_id)
    results = {}

    # Get all active platform connections
    connections = client.table("platform_connections").select(
        "id, platform, landscape, status"
    ).eq("user_id", user_id).in_(
        "status", ["connected", "active"]
    ).execute()

    for conn in (connections.data or []):
        platform = conn["platform"]
        landscape = conn.get("landscape", {}) or {}
        resources = landscape.get("resources", [])
        current_selected = landscape.get("selected_sources", [])

        if not resources:
            results[platform] = {"skipped": "no_landscape", "current": 0}
            continue

        # Get limit for this platform
        limit_field = PROVIDER_LIMIT_MAP.get(
            "gmail" if platform == "google" else platform,
            "slack_channels"
        )
        max_sources = getattr(limits, limit_field, 5)
        if max_sources == -1:
            max_sources = 999

        current_count = len(current_selected)
        if current_count >= max_sources:
            results[platform] = {
                "skipped": "at_limit",
                "current": current_count,
                "limit": max_sources,
            }
            continue

        # Compute smart defaults for all resources
        smart_selected = compute_smart_defaults(platform, resources, max_sources)

        # Merge: keep existing selections, add new ones up to limit
        existing_ids = {
            s.get("id") if isinstance(s, dict) else s
            for s in current_selected
        }
        merged = list(current_selected)
        for s in smart_selected:
            if s["id"] not in existing_ids and len(merged) < max_sources:
                merged.append(s)
                existing_ids.add(s["id"])

        added_count = len(merged) - current_count

        if added_count > 0:
            landscape["selected_sources"] = merged
            client.table("platform_connections").update({
                "landscape": landscape,
            }).eq("id", conn["id"]).execute()

        results[platform] = {
            "previous": current_count,
            "added": added_count,
            "total": len(merged),
            "limit": max_sources,
            "new_sources": [s.get("name", s.get("id")) for s in merged[current_count:]],
        }

    return {
        "user_id": user_id,
        "tier": get_limits_for_user(client, user_id).__class__.__name__,
        "results": results,
    }
