"""
Knowledge routes - ADR-107 Phase 3 UI surfacing

Mounted at /api/knowledge.

Provides user-scoped browsing of the /knowledge/ filesystem in workspace_files.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.supabase import UserClient
from services.workspace import KnowledgeBase

router = APIRouter()

ALLOWED_CONTENT_CLASSES = {"digests", "analyses", "briefs", "research", "insights"}


class KnowledgeFile(BaseModel):
    path: str
    name: str
    content_class: str
    summary: Optional[str] = None
    metadata: Optional[dict] = None
    updated_at: Optional[str] = None


class KnowledgeFilesResponse(BaseModel):
    files: list[KnowledgeFile]
    total: int
    content_class: Optional[str] = None
    limit: int


class KnowledgeClassCount(BaseModel):
    content_class: str
    count: int


class KnowledgeSummaryResponse(BaseModel):
    total: int
    classes: list[KnowledgeClassCount]


def _extract_class_and_name(path: str) -> tuple[str, str]:
    if not path.startswith("/knowledge/"):
        return "unknown", path

    # /knowledge/{class}/.../{file}
    relative = path[len("/knowledge/"):]
    parts = [p for p in relative.split("/") if p]
    if not parts:
        return "unknown", path

    return parts[0], parts[-1]


@router.get("/knowledge/files", response_model=KnowledgeFilesResponse)
async def list_knowledge_files(
    auth: UserClient,
    content_class: Optional[str] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=200),
):
    """List /knowledge/ files for the current user."""
    if content_class and content_class not in ALLOWED_CONTENT_CLASSES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_CLASSES))
        raise HTTPException(status_code=400, detail=f"Invalid content_class '{content_class}'. Allowed: {allowed}")

    kb = KnowledgeBase(auth.client, auth.user_id)
    rows = await kb.list_files(content_class=content_class, limit=limit)

    files: list[KnowledgeFile] = []
    for row in rows:
        path = row.get("path", "")
        parsed_class, name = _extract_class_and_name(path)
        files.append(
            KnowledgeFile(
                path=path,
                name=name,
                content_class=parsed_class,
                summary=row.get("summary"),
                metadata=row.get("metadata"),
                updated_at=row.get("updated_at"),
            )
        )

    return KnowledgeFilesResponse(
        files=files,
        total=len(files),
        content_class=content_class,
        limit=limit,
    )


@router.get("/knowledge/summary", response_model=KnowledgeSummaryResponse)
async def get_knowledge_summary(auth: UserClient):
    """Get per-class and total counts for /knowledge/ files."""
    class_counts: list[KnowledgeClassCount] = []
    total = 0

    for content_class in sorted(ALLOWED_CONTENT_CLASSES):
        result = (
            auth.client.table("workspace_files")
            .select("id", count="exact")
            .eq("user_id", auth.user_id)
            .like("path", f"/knowledge/{content_class}/%")
            .execute()
        )
        count = result.count or 0
        total += count
        class_counts.append(KnowledgeClassCount(content_class=content_class, count=count))

    return KnowledgeSummaryResponse(total=total, classes=class_counts)
