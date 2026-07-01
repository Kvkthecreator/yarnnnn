"""
Document routes - File upload and management

ADR-249: Two-Intent File Handling — Ephemeral vs Persistent.
ADR-395: persistent uploads retain the RAW blob + derive a text projection (DP34).
ADR-127: User-shared file staging (TP-level)

Endpoints:
- POST /documents/upload  - Persistent upload → inbound/uploads/{principal}/{slug}.{ext} raw + .extracted.md projection (ADR-395)
- GET /documents/blob     - Resolve a raw blob's content_url to a fresh signed URL (ADR-395)
- POST /share             - Share a file to global user_shared/ (ADR-127)
- GET /documents          - List workspace uploads (reads workspace_files)
- GET /documents/{id}/download - Download original binary from storage
- DELETE /documents/{id}  - Archive workspace file (trash-semantics)
"""

import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)

from services.supabase import UserClient, get_service_client
from services.documents import process_document, create_signed_url_for_storage_path

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

# ADR-331 D5: per-file result inside a batch upload. Non-transactional —
# each file succeeds or fails independently; the batch is never rolled back.
class UploadResultItem(BaseModel):
    filename: str
    success: bool
    workspace_path: Optional[str] = None
    word_count: Optional[int] = None
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    # ADR-331 D5: one call, N files (multi-select + .zip expansion). The
    # single-file caller gets a one-element results list — one path, not two.
    results: List[UploadResultItem]
    succeeded: int
    failed: int


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

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB per file
_ALLOWED_EXTS = ("pdf", "docx", "txt", "md")


def _resolve_file_type(content_type: str, filename: str) -> Optional[str]:
    """Resolve a file to its processing type, or None if unsupported."""
    if content_type in ALLOWED_TYPES:
        return ALLOWED_TYPES[content_type]
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return ext if ext in _ALLOWED_EXTS else None


async def _process_single_upload(
    *, content: bytes, content_type: str, filename: str, user_id: str, service,
) -> UploadResultItem:
    """The single-file pipeline, callable N times (ADR-331 D5 + ADR-395).

    Storage upload → land the RAW blob at inbound/uploads/{principal}/{slug}.{ext}
    (content_url, immutable) → derive the text projection inline (ADR-395 Piece
    A+B). Never raises — returns a per-file UploadResultItem so a batch can report
    partial success. process_document's _unique_raw_path guarantees N files → N
    distinct rows.
    """
    file_type = _resolve_file_type(content_type, filename)
    if file_type is None:
        return UploadResultItem(
            filename=filename, success=False,
            error=f"Unsupported file type. Allowed: {', '.join(t.upper() for t in _ALLOWED_EXTS)}",
        )
    if len(content) > MAX_FILE_SIZE:
        return UploadResultItem(
            filename=filename, success=False,
            error=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)}MB",
        )
    if len(content) < 10:
        return UploadResultItem(filename=filename, success=False, error="File is empty or too small")

    import uuid
    document_id = str(uuid.uuid4())
    storage_path = f"{user_id}/{document_id}/original.{file_type}"

    # Store binary in Supabase Storage
    try:
        storage_result = service.storage.from_("documents").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type or f"application/{file_type}"},
        )
        if hasattr(storage_result, "error") and storage_result.error:
            return UploadResultItem(filename=filename, success=False, error=f"Storage error: {storage_result.error}")
    except Exception as e:  # noqa: BLE001 — per-file isolation, batch must not abort
        logger.error(f"[DOCUMENTS] Storage upload error for {filename}: {e}", exc_info=True)
        return UploadResultItem(filename=filename, success=False, error=f"Failed to upload file: {e}")

    # Retain the raw blob + derive the text projection (ADR-395)
    result = await process_document(
        document_id=document_id,
        file_content=content,
        file_type=file_type,
        filename=filename,
        file_size=len(content),
        storage_path=storage_path,
        user_id=user_id,
        db_client=service,
    )
    if not result.get("success"):
        # Clean up storage on processing failure
        try:
            service.storage.from_("documents").remove([storage_path])
        except Exception:
            pass
        return UploadResultItem(filename=filename, success=False, error=result.get("error", "Processing failed"))

    return UploadResultItem(
        filename=filename, success=True,
        workspace_path=result["workspace_path"],
        word_count=result.get("word_count", 0),
    )


def _expand_zip(content: bytes) -> List[tuple]:
    """Expand a .zip into (filename, bytes) tuples for supported entries.

    ADR-331 D5: the archive is a transport envelope — expanded and discarded,
    never retained as a blob. Each entry is processed through the same
    single-file path. Directories, hidden/system entries, unsupported types,
    and oversized entries are filtered (oversize re-checked per entry in
    _process_single_upload). Returns [] on a corrupt archive.
    """
    import io
    import zipfile

    out: List[tuple] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for info in zf.infolist():
                name = info.filename
                if info.is_dir():
                    continue
                base = name.rsplit("/", 1)[-1]
                # Skip hidden / macOS resource-fork / system entries
                if not base or base.startswith(".") or name.startswith("__MACOSX/"):
                    continue
                ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
                if ext not in _ALLOWED_EXTS:
                    continue
                # Guard against zip-bomb single entries before reading.
                if info.file_size > MAX_FILE_SIZE:
                    continue
                try:
                    out.append((base, zf.read(info)))
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"[DOCUMENTS] zip entry {name} unreadable: {e}")
    except zipfile.BadZipFile:
        logger.warning("[DOCUMENTS] corrupt .zip archive — no entries expanded")
    return out


@router.post("/documents/upload", response_model=BatchUploadResponse)
async def upload_documents(
    auth: UserClient,
    files: List[UploadFile] = File(...),
    project_id: Optional[str] = Form(None),  # accepted for compat, ignored
):
    """Persistent document upload — multi-file + .zip (ADR-331 D5, ADR-249 Type B).

    Accepts one or more files in a single call. A .zip is expanded server-side
    to per-file uploads (the archive is a transport envelope, not retained).
    Each file flows through the SAME single-file path (retain the raw blob at
    inbound/uploads/ + derive a text projection, ADR-395, attributed operator).
    Non-transactional: per-file results are reported; partial success is fine.

    Singular Implementation: this is the one upload endpoint. The single-file
    caller sends one file and gets a one-element results list — no parallel
    bulk-ingestion subsystem, no background job, no progress table (ADR-331 D5).
    """
    service = get_service_client()

    # Build the work list: each file, with .zip entries expanded inline.
    work: List[tuple] = []  # (filename, content_type, bytes)
    for f in files:
        raw = await f.read()
        fname = f.filename or "document"
        is_zip = (f.content_type == "application/zip") or fname.lower().endswith(".zip")
        if is_zip:
            for entry_name, entry_bytes in _expand_zip(raw):
                work.append((entry_name, "", entry_bytes))  # type resolved by extension
        else:
            work.append((fname, f.content_type or "", raw))

    if not work:
        raise HTTPException(
            status_code=400,
            detail="No supported files. Allowed: PDF, DOCX, TXT, MD (or a .zip of those).",
        )

    results: List[UploadResultItem] = []
    for fname, ctype, content in work:
        item = await _process_single_upload(
            content=content, content_type=ctype, filename=fname,
            user_id=auth.user_id, service=service,
        )
        results.append(item)

    succeeded = sum(1 for r in results if r.success)
    return BatchUploadResponse(
        results=results,
        succeeded=succeeded,
        failed=len(results) - succeeded,
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
    """List persistent workspace uploads.

    ADR-395: uploads now land as RAW blobs in inbound/uploads/{principal}/ (not a
    derived .md under uploads/). We list the raw lane AND the legacy uploads/
    root (pre-ADR-395 files stay listed), skipping the co-located `.extracted.md`
    text projections (they're the derivation, not the upload). The filename comes
    from the path; legacy .md files may still carry `original_filename:` in a
    frontmatter header (read when present, harmless when absent).
    """
    result = auth.client.table("workspace_files") \
        .select("path, content, updated_at") \
        .eq("user_id", auth.user_id) \
        .or_(
            "path.like./workspace/inbound/uploads/%,"
            "path.like./workspace/uploads/%.md"
        ) \
        .or_("lifecycle.is.null,lifecycle.neq.archived") \
        .order("updated_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()

    items = []
    for row in (result.data or []):
        path = row["path"]
        # Skip the derived text projection — it's the derivation, not the upload.
        if path.endswith(".extracted.md"):
            continue
        raw = row.get("content", "") or ""
        # Filename from the path leaf (raw lane preserves the real name+ext);
        # legacy uploads/ .md drops the .md suffix.
        leaf = path.rsplit("/", 1)[-1]
        original_filename = leaf.removesuffix(".md") if path.endswith(".md") else leaf
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
            path=path,
            filename=original_filename,
            word_count=word_count,
            uploaded_at=(row.get("updated_at") or "")[:10],
        ))

    return {"uploads": items, "total": len(items), "limit": limit, "offset": offset}


# =============================================================================
# BLOB (ADR-395 Piece A — stable content_url → fresh signed URL redirect)
# =============================================================================

@router.get("/documents/blob")
async def get_blob(auth: UserClient, storage_path: str):
    """Resolve a raw-upload blob's STABLE content_url to a fresh signed URL.

    A raw upload's `content_url` is `/api/documents/blob?storage_path=<key>`
    (ADR-395 Piece A) — a stable reference stored on the immutable raw revision.
    This route mints a fresh (1h) signed URL for the private-bucket blob and
    302-redirects, so the FE (img/iframe/download `src`) always reaches live
    bytes without a persisted URL going stale.

    Ownership: the `documents`-bucket key is `{user_id}/{document_id}/…`, so a
    caller may only resolve blobs under their OWN user_id prefix — this prevents
    reading another principal's blob by guessing the key.
    """
    if not storage_path or not storage_path.startswith(f"{auth.user_id}/"):
        # Not owned by the caller (or empty) — 404, don't leak existence.
        raise HTTPException(status_code=404, detail="Blob not found")

    service = get_service_client()
    signed = create_signed_url_for_storage_path(service, storage_path, expires_in=3600)
    if not signed:
        raise HTTPException(status_code=404, detail="Blob not found")
    return RedirectResponse(url=signed, status_code=302)


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

    service = get_service_client()
    signed = create_signed_url_for_storage_path(service, storage_path, expires_in=3600)
    if not signed:
        raise HTTPException(status_code=500, detail="Failed to generate download URL")
    return DownloadResponse(url=signed, expires_in=3600)


# =============================================================================
# DELETE
# =============================================================================

# Operator-owned root for the archive (delete) verb. The operator may
# archive what the operator authored — uploads. System-authored substrate
# (Reviewer principles, agent context, the constitution) is NOT archivable
# from the UI: that's ADR-320 topology-as-permission. Operator-authored
# constitution files are EDITED via chat, never deleted from a browser.
# ADR-395: uploads now land in the inbound/uploads/ raw lane (the N=human case
# of inbound/); the legacy uploads/ root stays archivable for pre-ADR-395 files.
_OPERATOR_ARCHIVABLE_PREFIXES = ("/workspace/uploads/", "/workspace/inbound/uploads/")


@router.delete("/documents/{document_path:path}")
async def delete_document(auth: UserClient, document_path: str):
    """Archive a workspace upload (the operator-facing 'Delete' verb).

    Trash-semantics, NOT erasure. Per ADR-209 (every mutation attributed +
    retained) this does NOT remove the row — it writes a new revision with
    lifecycle='archived', attributed to the operator. The file leaves the
    active workspace (filtered from the tree, dropped from context) but the
    revision chain keeps the record and the storage binary stays. Reversible.

    Scope (ADR-320 topology): operator may archive only operator-authored
    material under /workspace/uploads/. Anything else returns 403 — the
    operator does not delete what the system authored on their behalf.
    """
    from services.authored_substrate import write_revision

    if not document_path.startswith("/"):
        document_path = "/" + document_path

    # ADR-320 scope guard: operator-archivable roots only.
    if not document_path.startswith(_OPERATOR_ARCHIVABLE_PREFIXES):
        raise HTTPException(
            status_code=403,
            detail="Only uploaded files can be deleted. System-authored substrate is managed through chat.",
        )

    result = auth.client.table("workspace_files") \
        .select("content") \
        .eq("user_id", auth.user_id) \
        .eq("path", document_path) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    content = result.data[0].get("content", "") or ""

    # Archive = new revision, lifecycle='archived', operator-attributed.
    # Retains the row + revision chain (ADR-209); storage binary untouched
    # so an un-archive can fully restore. Content preserved verbatim.
    service = get_service_client()
    write_revision(
        db_client=service,
        user_id=auth.user_id,
        path=document_path,
        content=content,
        authored_by="operator",
        message="Archived by operator (removed from active workspace)",
        lifecycle="archived",
    )

    return {"success": True, "message": "Moved to trash", "archived": True}


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
