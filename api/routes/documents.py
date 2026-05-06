"""
Document routes - File upload and management

ADR-249: Two-Intent File Handling — Ephemeral vs Persistent.
ADR-127: User-shared file staging (TP-level)

Endpoints:
- POST /documents/upload  - Persistent upload → /workspace/uploads/{slug}.md
- POST /share             - Share a file to global user_shared/ (ADR-127)
- GET /documents          - List workspace uploads (reads workspace_files)
- GET /documents/{id}/download - Download original binary from storage (reads frontmatter)
- DELETE /documents/{id}  - Delete workspace file + storage binary
"""

import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

from services.supabase import UserClient, get_service_client
from services.documents import process_document

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class UploadResponse(BaseModel):
    workspace_path: str
    filename: str
    processing_status: str
    message: str


class WorkspaceUploadItem(BaseModel):
    path: str
    filename: str
    word_count: int
    uploaded_at: str


class DownloadResponse(BaseModel):
    url: str
    expires_in: int  # seconds


# =============================================================================
# UPLOAD (ADR-249 persistent path)
# =============================================================================

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
}

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


@router.post("/documents/upload", response_model=UploadResponse)
async def upload_document(
    auth: UserClient,
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),  # accepted for compat, ignored
):
    """Persistent document upload (ADR-249 Type B).

    Extracts text → writes /workspace/uploads/{slug}.md via authored substrate.
    Original binary stored in Supabase Storage (documents bucket).
    YARNNN sees the file immediately in its compact index via ListFiles.
    """
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        ext = (file.filename or "").split(".")[-1].lower()
        if ext not in ("pdf", "docx", "txt", "md"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}. Allowed: PDF, DOCX, TXT, MD"
            )
        file_type = ext
    else:
        file_type = ALLOWED_TYPES[content_type]

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)}MB")
    if len(content) < 10:
        raise HTTPException(status_code=400, detail="File is empty or too small")

    import uuid
    document_id = str(uuid.uuid4())
    storage_path = f"{auth.user_id}/{document_id}/original.{file_type}"
    filename = file.filename or f"document.{file_type}"

    # Store binary in Supabase Storage
    try:
        service = get_service_client()
        storage_result = service.storage.from_("documents").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type or f"application/{file_type}"}
        )
        if hasattr(storage_result, "error") and storage_result.error:
            raise HTTPException(status_code=500, detail=f"Storage error: {storage_result.error}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Storage upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    # Extract text and write /workspace/uploads/{slug}.md
    service = get_service_client()
    result = await process_document(
        document_id=document_id,
        file_content=content,
        file_type=file_type,
        filename=filename,
        file_size=len(content),
        storage_path=storage_path,
        user_id=auth.user_id,
        db_client=service,
    )

    if not result.get("success"):
        # Clean up storage on failure
        try:
            service.storage.from_("documents").remove([storage_path])
        except Exception:
            pass
        raise HTTPException(status_code=422, detail=result.get("error", "Processing failed"))

    workspace_path = result["workspace_path"]
    word_count = result.get("word_count", 0)

    return UploadResponse(
        workspace_path=workspace_path,
        filename=filename,
        processing_status="completed",
        message=f"Added to workspace: {workspace_path} ({word_count} words)"
    )


# =============================================================================
# LIST (reads workspace_files)
# =============================================================================

@router.get("/documents")
async def list_documents(
    auth: UserClient,
    limit: int = 50,
    offset: int = 0,
):
    """List persistent workspace uploads."""
    result = auth.client.table("workspace_files") \
        .select("path, content, updated_at") \
        .eq("user_id", auth.user_id) \
        .like("path", "/workspace/uploads/%.md") \
        .order("updated_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()

    items = []
    for row in (result.data or []):
        raw = row.get("content", "") or ""
        original_filename = row["path"].rsplit("/", 1)[-1].removesuffix(".md")
        word_count = 0
        for line in raw.split("\n"):
            if line.startswith("original_filename:"):
                original_filename = line.split(":", 1)[1].strip()
            elif line.startswith("word_count:"):
                try:
                    word_count = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    pass
        items.append(WorkspaceUploadItem(
            path=row["path"],
            filename=original_filename,
            word_count=word_count,
            uploaded_at=(row.get("updated_at") or "")[:10],
        ))

    return {"uploads": items, "total": len(items), "limit": limit, "offset": offset}


# =============================================================================
# DOWNLOAD (reads storage_path from workspace file frontmatter)
# =============================================================================

@router.get("/documents/{document_path:path}/download")
async def download_document(auth: UserClient, document_path: str):
    """Get a signed download URL for a persistent upload.

    document_path is the workspace file path, e.g.
    'workspace/uploads/acme-brief.md' (leading slash optional).
    """
    if not document_path.startswith("/"):
        document_path = "/" + document_path

    result = auth.client.table("workspace_files") \
        .select("content") \
        .eq("user_id", auth.user_id) \
        .eq("path", document_path) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    raw = result.data[0].get("content", "") or ""
    storage_path = None
    for line in raw.split("\n"):
        if line.startswith("storage_path:"):
            storage_path = line.split(":", 1)[1].strip()
            break

    if not storage_path:
        raise HTTPException(status_code=404, detail="Storage path not found in document frontmatter")

    try:
        service = get_service_client()
        signed = service.storage.from_("documents").create_signed_url(
            path=storage_path,
            expires_in=3600
        )
        return DownloadResponse(
            url=signed.get("signedURL") or signed.get("signedUrl"),
            expires_in=3600
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {e}")


# =============================================================================
# DELETE
# =============================================================================

@router.delete("/documents/{document_path:path}")
async def delete_document(auth: UserClient, document_path: str):
    """Delete a workspace upload and its storage binary."""
    if not document_path.startswith("/"):
        document_path = "/" + document_path

    result = auth.client.table("workspace_files") \
        .select("content") \
        .eq("user_id", auth.user_id) \
        .eq("path", document_path) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    raw = result.data[0].get("content", "") or ""
    storage_path = None
    for line in raw.split("\n"):
        if line.startswith("storage_path:"):
            storage_path = line.split(":", 1)[1].strip()
            break

    # Delete storage binary
    if storage_path:
        try:
            service = get_service_client()
            service.storage.from_("documents").remove([storage_path])
        except Exception as e:
            logger.warning(f"Failed to delete storage file: {e}")

    # Delete workspace file
    auth.client.table("workspace_files") \
        .delete() \
        .eq("user_id", auth.user_id) \
        .eq("path", document_path) \
        .execute()

    return {"success": True, "message": "Document deleted"}


# =============================================================================
# SHARE FILE — ADR-127: TP-Level User-Shared File Staging
# =============================================================================

class ShareFileRequest(BaseModel):
    filename: str
    content: str


@router.post("/share")
async def share_file_global(
    body: ShareFileRequest,
    auth: UserClient = None,
):
    """ADR-127: Share a file to the global user_shared/ staging area."""
    import re
    from services.authored_substrate import write_revision

    filename = body.filename.strip()
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")
    content = body.content
    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '-', filename).strip('-')
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = f"/user_shared/{safe_filename}"

    try:
        write_revision(
            auth.client,
            user_id=auth.user_id,
            path=path,
            content=content,
            authored_by="operator",
            message=f"share user file {safe_filename}",
            summary=f"User shared: {safe_filename}",
            lifecycle="ephemeral",
        )
    except Exception as e:
        logger.error(f"[SHARE] Failed to write user_shared file: {e}")
        raise HTTPException(status_code=500, detail="Failed to share file")

    return {
        "success": True,
        "path": path,
        "filename": safe_filename,
        "message": "File shared. TP can reference it in conversation.",
    }
