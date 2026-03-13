"""
Knowledge routes - ADR-107 Phase 2+3

Mounted at /api/knowledge.

Provides user-scoped browsing, CRUD, and versioning of the /knowledge/ filesystem.

Endpoints:
  GET  /knowledge/files           - List knowledge files (filterable by content_class)
  GET  /knowledge/files/read      - Read a single knowledge file by path
  GET  /knowledge/files/versions  - List version history for a knowledge file
  POST /knowledge/files           - Create a user-contributed knowledge file
  GET  /knowledge/summary         - Per-class and total counts
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


class KnowledgeFileDetail(BaseModel):
    path: str
    name: str
    content_class: str
    content: str
    summary: Optional[str] = None
    metadata: Optional[dict] = None
    updated_at: Optional[str] = None


class KnowledgeFileCreate(BaseModel):
    title: str
    content: str
    content_class: str


class KnowledgeVersion(BaseModel):
    path: str
    version: int
    summary: Optional[str] = None
    metadata: Optional[dict] = None
    updated_at: Optional[str] = None


class KnowledgeVersionsResponse(BaseModel):
    canonical_path: str
    versions: list[KnowledgeVersion]
    total: int


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

    # ADR-107 Phase 2: Exclude version archive files (v*.md) from main listing
    import re
    _VERSION_FILE_RE = re.compile(r"/v\d+\.md$")

    files: list[KnowledgeFile] = []
    for row in rows:
        path = row.get("path", "")
        if _VERSION_FILE_RE.search(path):
            continue
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


@router.get("/knowledge/files/read", response_model=KnowledgeFileDetail)
async def read_knowledge_file(
    auth: UserClient,
    path: str = Query(..., description="Full path e.g. /knowledge/digests/weekly-slack-digest-2026-03-11.md"),
):
    """Read a single knowledge file's content by path."""
    if not path.startswith("/knowledge/"):
        raise HTTPException(status_code=400, detail="Path must start with /knowledge/")

    kb = KnowledgeBase(auth.client, auth.user_id)
    content = await kb.read(path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    parsed_class, name = _extract_class_and_name(path)

    # Get metadata from the row
    try:
        result = (
            auth.client.table("workspace_files")
            .select("summary, metadata, updated_at")
            .eq("user_id", auth.user_id)
            .eq("path", path)
            .single()
            .execute()
        )
        row = result.data or {}
    except Exception:
        row = {}

    return KnowledgeFileDetail(
        path=path,
        name=name,
        content_class=parsed_class,
        content=content,
        summary=row.get("summary"),
        metadata=row.get("metadata"),
        updated_at=row.get("updated_at"),
    )


@router.get("/knowledge/files/versions", response_model=KnowledgeVersionsResponse)
async def list_knowledge_versions(
    auth: UserClient,
    path: str = Query(..., description="Canonical file path e.g. /knowledge/research/topic/latest.md"),
):
    """List version history for a knowledge file (ADR-107 Phase 2)."""
    if not path.startswith("/knowledge/"):
        raise HTTPException(status_code=400, detail="Path must start with /knowledge/")

    kb = KnowledgeBase(auth.client, auth.user_id)
    rows = await kb.list_versions(path)

    versions: list[KnowledgeVersion] = []
    for row in rows:
        meta = row.get("metadata") or {}
        version_num = meta.get("version_number", 0)
        versions.append(
            KnowledgeVersion(
                path=row["path"],
                version=version_num,
                summary=row.get("summary"),
                metadata=meta,
                updated_at=row.get("updated_at"),
            )
        )

    return KnowledgeVersionsResponse(
        canonical_path=path,
        versions=versions,
        total=len(versions),
    )


@router.post("/knowledge/files", response_model=KnowledgeFile, status_code=201)
async def create_knowledge_file(
    body: KnowledgeFileCreate,
    auth: UserClient,
):
    """Create a user-contributed knowledge file in /knowledge/{class}/."""
    content_class = body.content_class.strip().lower()
    if content_class not in ALLOWED_CONTENT_CLASSES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_CLASSES))
        raise HTTPException(status_code=400, detail=f"Invalid content_class '{content_class}'. Allowed: {allowed}")

    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content is required")

    # Slugify title for path
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if not slug:
        slug = "untitled"
    path = f"/knowledge/{content_class}/{slug}.md"

    kb = KnowledgeBase(auth.client, auth.user_id)

    # Check if path already exists — append a suffix if so
    existing = await kb.read(path)
    if existing is not None:
        from datetime import datetime
        suffix = datetime.utcnow().strftime("%Y%m%d%H%M")
        path = f"/knowledge/{content_class}/{slug}-{suffix}.md"

    summary = body.content[:120].replace('\n', ' ').strip()
    await kb.write(
        path=path,
        content=body.content,
        summary=summary,
        metadata={"source": "user_upload"},
    )

    parsed_class, name = _extract_class_and_name(path)
    return KnowledgeFile(
        path=path,
        name=name,
        content_class=parsed_class,
        summary=summary,
        metadata={"source": "user_upload"},
    )


@router.get("/knowledge/summary", response_model=KnowledgeSummaryResponse)
async def get_knowledge_summary(auth: UserClient):
    """Get per-class and total counts for /knowledge/ files."""
    import re
    _VERSION_FILE_RE = re.compile(r"/v\d+\.md$")

    class_counts: list[KnowledgeClassCount] = []
    total = 0

    for content_class in sorted(ALLOWED_CONTENT_CLASSES):
        result = (
            auth.client.table("workspace_files")
            .select("path", count="exact")
            .eq("user_id", auth.user_id)
            .like("path", f"/knowledge/{content_class}/%")
            .execute()
        )
        # Exclude version archive files (v1.md, v2.md, etc.) to match list endpoint
        count = sum(
            1 for row in (result.data or [])
            if not _VERSION_FILE_RE.search(row.get("path", ""))
        )
        total += count
        class_counts.append(KnowledgeClassCount(content_class=content_class, count=count))

    return KnowledgeSummaryResponse(total=total, classes=class_counts)
