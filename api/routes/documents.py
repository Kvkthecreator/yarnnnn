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

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)

from services.supabase import UserClient, get_service_client
from services.workspace_context import substrate_scope_filter
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


async def _embed_projection_deferred(user_id: str, projection_path: str) -> None:
    """Embed an upload's text projection OFF the request (ADR-395 / ADR-325).

    Scheduled by the upload route as a FastAPI BackgroundTask so the paid,
    rate-limitable OpenAI call never blocks (or breaks) the upload response. The
    projection is already BM25-searchable when the response returns; this is the
    enrichment that catches up. Reads the projection content fresh from the DB
    (the row is already written) and runs the same mechanical embed as inline —
    attributed system:extract, not operator-gated (ADR-325 D6: upload embed is
    operator-initiated, not Reviewer-gated). Never raises."""
    try:
        from services.supabase import get_service_client
        from services.primitives.embed import is_embed_eligible
        from services.primitives.workspace import _embed_workspace_file

        service = get_service_client()
        row = service.table("workspace_files").select("content").eq(
            "user_id", user_id).eq("path", projection_path).limit(1).execute()
        if not row.data:
            logger.warning(f"[DOCUMENTS] deferred embed: projection gone {projection_path}")
            return
        content = row.data[0].get("content") or ""
        rel = projection_path.lstrip("/")
        if rel.startswith("workspace/"):
            rel = rel[len("workspace/"):]
        eligible, reason = is_embed_eligible(rel, content)
        if not eligible:
            logger.info(f"[DOCUMENTS] deferred embed skipped ({reason}): {projection_path}")
            return
        await _embed_workspace_file(service, user_id, projection_path, content[:2000])
        logger.info(f"[DOCUMENTS] deferred embed done: {projection_path}")
    except Exception as e:  # noqa: BLE001 — background, never surfaces to the user
        logger.warning(f"[DOCUMENTS] deferred embed failed for {projection_path}: {e}")


async def _process_single_upload(
    *, content: bytes, content_type: str, filename: str, user_id: str, service,
) -> tuple[UploadResultItem, Optional[str]]:
    """The single-file pipeline, callable N times (ADR-331 D5 + ADR-395).

    Storage upload → land the RAW blob at inbound/uploads/{principal}/{slug}.{ext}
    (content_url, immutable) → derive the text projection (ADR-395 Piece A+B), with
    the embed DEFERRED off the request. Never raises — returns a per-file
    UploadResultItem plus the projection path to embed in the background (or None
    when nothing is owed). process_document's _unique_raw_path guarantees N files
    → N distinct rows.
    """
    def _fail(error: str) -> tuple[UploadResultItem, Optional[str]]:
        return UploadResultItem(filename=filename, success=False, error=error), None

    file_type = _resolve_file_type(content_type, filename)
    if file_type is None:
        return _fail(f"Unsupported file type. Allowed: {', '.join(t.upper() for t in _ALLOWED_EXTS)}")
    if len(content) > MAX_FILE_SIZE:
        return _fail(f"File too large. Max {MAX_FILE_SIZE // (1024*1024)}MB")
    if len(content) < 10:
        return _fail("File is empty or too small")

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
            return _fail(f"Storage error: {storage_result.error}")
    except Exception as e:  # noqa: BLE001 — per-file isolation, batch must not abort
        logger.error(f"[DOCUMENTS] Storage upload error for {filename}: {e}", exc_info=True)
        return _fail(f"Failed to upload file: {e}")

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
        return _fail(result.get("error", "Processing failed"))

    # Deferred embed: hand the projection path up to the route to schedule as a
    # BackgroundTask (only when an embed is owed — embed_pending).
    to_embed = result.get("projection_path") if result.get("embed_pending") else None
    return UploadResultItem(
        filename=filename, success=True,
        workspace_path=result["workspace_path"],
        word_count=result.get("word_count", 0),
    ), to_embed


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
    background_tasks: BackgroundTasks,
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
        item, to_embed = await _process_single_upload(
            content=content, content_type=ctype, filename=fname,
            user_id=auth.user_id, service=service,
        )
        results.append(item)
        # Defer the paid embed off the response (ADR-395 / ADR-325): the upload
        # returns as soon as the raw + BM25-searchable projection are written;
        # the embedding enrichment runs as a BackgroundTask after the response.
        if to_embed:
            background_tasks.add_task(_embed_projection_deferred, auth.user_id, to_embed)

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
        .eq(*substrate_scope_filter(auth.user_id)) \
        .or_(
            "path.like./workspace/inbound/uploads/%,"
            "path.like./workspace/uploads/%.md"
        ) \
        .or_("lifecycle.is.null,lifecycle.neq.archived") \
        .order("updated_at", desc=True) \
        .range(offset, offset + limit - 1) \
        .execute()

    from services.documents import is_upload_projection
    items = []
    for row in (result.data or []):
        path = row["path"]
        # Skip the derived text projection — it's the derivation, not the upload
        # (shared predicate, ADR-395: narrow to inbound/uploads/**.extracted.md).
        if is_upload_projection(path):
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
# BLOB (ADR-395 Piece A — stable content_url → fresh signed URL)
# =============================================================================
# A raw upload's `content_url` is `/api/documents/blob?storage_path=<key>` — a
# stable reference on the immutable raw revision. The FE resolves it to a fresh
# signed URL via an AUTHENTICATED fetch (Bearer header), then points the
# img/iframe/download `src` at the DIRECT Supabase signed URL.
#
# Why not a header-auth redirect the img/iframe hits directly: a browser-native
# `<img src>` / `<iframe src>` / download-anchor request carries NO Authorization
# header (only a `fetch()` can), so a header-auth route is unreachable from those
# elements — it 401s and the iframe renders the error JSON as the "file" (the
# operator-observed viewer bug). The signed URL is itself time-boxed + scoped, so
# putting IT (not a JWT) in the element src is safe; the JWT never leaves the
# authed fetch. This also avoids a JWT-in-URL anti-pattern (history/referrer/log
# leakage) that a `?token=` redirect would introduce.


class BlobUrlResponse(BaseModel):
    url: str
    expires_in: int  # seconds


@router.get("/documents/blob", response_model=BlobUrlResponse)
async def get_blob_url(auth: UserClient, storage_path: str):
    """Resolve a raw-upload blob's stable content_url key to a fresh signed URL.

    Authenticated (Bearer) JSON endpoint — the FE fetches this with the session
    token, then renders the returned signed URL directly (img/iframe/download).

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
    return BlobUrlResponse(url=signed, expires_in=3600)


# =============================================================================
# DOWNLOAD (reads storage_path from workspace file frontmatter)
# =============================================================================

def _storage_path_from_content_url(content_url: str) -> Optional[str]:
    """Extract the private-bucket key from a raw upload's content_url.

    ADR-395: a raw upload row carries `content_url` =
    `/api/documents/blob?storage_path=<url-encoded key>` (no frontmatter). Parse
    the `storage_path` query param back out. Returns None for a non-blob URL
    (e.g. an absolute output-gateway URL that isn't a private-bucket key).
    """
    from urllib.parse import urlparse, parse_qs, unquote
    if not content_url or "storage_path=" not in content_url:
        return None
    try:
        qs = parse_qs(urlparse(content_url).query)
        vals = qs.get("storage_path")
        return unquote(vals[0]) if vals else None
    except Exception:  # noqa: BLE001
        return None


@router.get("/documents/{document_path:path}/download")
async def download_document(auth: UserClient, document_path: str):
    """Get a signed download URL for a persistent upload.

    document_path is the workspace file path, e.g.
    '/workspace/inbound/uploads/operator/acme-brief.pdf' (leading slash optional).

    ADR-395: new uploads store the raw blob's key in `content_url` (no
    frontmatter). Resolve `storage_path` from content_url first; fall back to the
    legacy `storage_path:` frontmatter line for pre-ADR-395 uploads/*.md rows.
    """
    if not document_path.startswith("/"):
        document_path = "/" + document_path

    result = auth.client.table("workspace_files") \
        .select("content, content_url") \
        .eq(*substrate_scope_filter(auth.user_id)) \
        .eq("path", document_path) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    row = result.data[0]
    # ADR-395 raw row: storage_path lives in content_url. Legacy row: frontmatter.
    storage_path = _storage_path_from_content_url(row.get("content_url") or "")
    if not storage_path:
        raw = row.get("content", "") or ""
        for line in raw.split("\n"):
            if line.startswith("storage_path:"):
                storage_path = line.split(":", 1)[1].strip()
                break

    if not storage_path:
        raise HTTPException(status_code=404, detail="Storage path not found for document")

    # Ownership guard (parity with the /blob route, ADR-373): the documents-bucket
    # key is `{user_id}/…`, so only resolve blobs under the caller's own prefix.
    if not storage_path.startswith(f"{auth.user_id}/"):
        raise HTTPException(status_code=404, detail="Document not found")

    service = get_service_client()
    signed = create_signed_url_for_storage_path(service, storage_path, expires_in=3600)
    if not signed:
        raise HTTPException(status_code=500, detail="Failed to generate download URL")
    return DownloadResponse(url=signed, expires_in=3600)


# =============================================================================
# DELETE
# =============================================================================

# ADR-400 Amendment 1: the operator organizes (move/rename/trash) their WHOLE
# workspace except system/ (runtime state) + _*.yaml/_*.json machine-config (read
# by exact path). This is the SINGULAR source — `operator_can_organize` in
# workspace_paths — shared by every route below + mirrored by the FE. The prior
# `uploads/`-only scope was a misread of ADR-320's foreign-principal lock as an
# operator lock (Amendment 1 corrects it). Content EDIT still routes through chat
# (that boundary holds); this is ORGANIZE, which is the operator's.
from services.workspace_paths import operator_can_organize


@router.delete("/documents/{document_path:path}")
async def delete_document(auth: UserClient, document_path: str):
    """Move a workspace file to Trash (the operator-facing 'Delete' verb).

    Trash-semantics, NOT erasure. Per ADR-209 (every mutation attributed +
    retained) this does NOT remove the row — it writes a new revision with
    lifecycle='archived', attributed to the operator. The file leaves the
    active workspace (filtered from the tree, dropped from context) but the
    revision chain keeps the record and the storage binary stays. Reversible.

    Scope (ADR-400 Amendment 1): the operator may trash their WHOLE workspace
    except system/ (runtime state) + _*.yaml/_*.json machine-config (read by
    exact path). It's their filesystem; delete is reversible, so it's safe.
    Anything outside that reach returns 403 — surfaced honestly by the FE.
    """
    from services.authored_substrate import write_revision

    if not document_path.startswith("/"):
        document_path = "/" + document_path

    if not operator_can_organize(document_path):
        raise HTTPException(
            status_code=403,
            detail="This file is managed by the system and can't be moved to trash.",
        )

    result = auth.client.table("workspace_files") \
        .select("content") \
        .eq(*substrate_scope_filter(auth.user_id)) \
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
# TRASH — ADR-400: the visible, reversible home of the delete verb
# =============================================================================
# Delete is already trash-not-erase (archive, ADR-329/ADR-209): a deleted file
# becomes a lifecycle='archived' revision — retained, attributed, recoverable.
# ADR-400 makes that state a first-class SURFACE: a Trash view lists archived
# operator-owned files; Restore un-archives (a new 'active' revision). No
# hard-delete (Q3 — ADR-209 retain-everything; Trash is a view, not an eraser).


class TrashItem(BaseModel):
    path: str
    filename: str
    archived_at: str
    authored_by: Optional[str] = None  # who last authored before archiving


class TrashListResponse(BaseModel):
    items: List[TrashItem]


@router.get("/documents/trash", response_model=TrashListResponse)
async def list_trash(auth: UserClient):
    """List files the operator has moved to Trash (lifecycle='archived').

    ADR-400 D4 + Amendment 1: the Trash surface. Shows any archived file within
    the operator's organize reach (operator_can_organize) — i.e. what the
    operator could have trashed and can now restore. Newest first. Reversible
    via POST /documents/restore.
    """
    result = (
        auth.client.table("workspace_files")
        .select("path, updated_at, "
                "workspace_file_versions!head_version_id(authored_by)")
        .eq(*substrate_scope_filter(auth.user_id))
        .eq("lifecycle", "archived")
        .order("updated_at", desc=True)
        .limit(200)
        .execute()
    )
    items: List[TrashItem] = []
    for row in (result.data or []):
        path = row["path"]
        if not operator_can_organize(path):
            continue  # only files the operator could have trashed
        embed = row.get("workspace_file_versions") or {}
        leaf = path.rsplit("/", 1)[-1]
        filename = leaf.removesuffix(".md") if path.endswith(".md") else leaf
        items.append(TrashItem(
            path=path,
            filename=filename,
            archived_at=(row.get("updated_at") or "")[:19],
            authored_by=(embed.get("authored_by") if isinstance(embed, dict) else None),
        ))
    return TrashListResponse(items=items)


class RestoreRequest(BaseModel):
    path: str


@router.post("/documents/restore")
async def restore_document(body: RestoreRequest, auth: UserClient):
    """Restore a file from Trash — un-archive (ADR-400 D8).

    The inverse of delete: writes a new lifecycle='active' revision carrying the
    archived content verbatim, attributed operator ("restored from trash"). The
    file re-enters the active tree. Scoped to the operator's organize reach (an
    operator restores only what an operator could trash). Reversible by re-deleting.
    """
    from services.authored_substrate import write_revision

    path = body.path
    if not path.startswith("/"):
        path = "/" + path
    if not operator_can_organize(path):
        raise HTTPException(
            status_code=403,
            detail="This file is managed by the system and can't be restored from here.",
        )

    result = auth.client.table("workspace_files") \
        .select("content, lifecycle") \
        .eq(*substrate_scope_filter(auth.user_id)) \
        .eq("path", path) \
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="File not found")
    row = result.data[0]
    if row.get("lifecycle") != "archived":
        raise HTTPException(status_code=409, detail="File is not in the trash")

    service = get_service_client()
    write_revision(
        db_client=service,
        user_id=auth.user_id,
        path=path,
        content=row.get("content", "") or "",
        authored_by="operator",
        message="Restored from trash",
        lifecycle="active",
    )
    return {"success": True, "message": "Restored", "path": path}


# =============================================================================
# MOVE / RENAME — ADR-400 D2: relocate + rename as operator verbs
# =============================================================================
# The human reorganizes their OWN material (GitHub: you move files you have write
# access to). Both source AND destination must be operator-owned roots — you can
# reorganize your uploads, you cannot move a file INTO governance/ (that's an
# agent's job, through the gate). Delegates to the existing MoveFile primitive so
# the mechanics (attributed revision at new path + tombstone at old, overwrite
# refusal) + the ADR-307 gate are reused — no parallel move implementation.


class MoveRequest(BaseModel):
    path: str       # current path (operator-owned)
    new_path: str   # destination path (operator-owned); rename = same parent, new leaf


@router.post("/documents/move")
async def move_document(body: MoveRequest, auth: UserClient):
    """Move or rename a file (ADR-400 D2 / Q1 / Amendment 1).

    Move  = a new_path under a different folder.
    Rename = a new_path with the same parent, a new leaf.
    BOTH source and destination must be within the operator's organize reach
    (operator_can_organize): you can't move a system/ or machine-config file, and
    you can't move a file INTO system/ or turn it into a _*.yaml the machine reads
    by path. Everything else — constitution/persona/operation/uploads prose — is
    the operator's to reorganize. Delegates to the MoveFile primitive (attributed,
    gated, overwrite-safe).
    """
    src = body.path if body.path.startswith("/") else "/" + body.path
    dst = body.new_path if body.new_path.startswith("/") else "/" + body.new_path

    if not operator_can_organize(src):
        raise HTTPException(
            status_code=403,
            detail="This file is managed by the system and can't be moved or renamed.",
        )
    if not operator_can_organize(dst):
        raise HTTPException(
            status_code=403,
            detail="Files can't be moved into a system location or renamed to a machine-config name.",
        )
    if src == dst:
        raise HTTPException(status_code=400, detail="Source and destination are the same.")

    from services.primitives.registry import execute_primitive
    result = await execute_primitive(auth, "MoveFile", {
        "path": src, "new_path": dst, "scope": "workspace",
    })
    if not (isinstance(result, dict) and result.get("success")):
        err = (result or {}).get("error", "move_failed")
        detail = (result or {}).get("message", "Move failed")
        # destination_exists → 409; everything else → 400.
        raise HTTPException(status_code=409 if err == "destination_exists" else 400, detail=detail)
    return {"success": True, "path": dst}


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
