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
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

from services.supabase import UserClient, get_service_client
from services.workspace_context import substrate_scope_filter
from services.documents import (
    process_document,
    create_signed_url_for_storage_path,
    blob_content_url,
)
from services.primitives.workspace import _is_path_readable_for_principal

router = APIRouter()


# =============================================================================
# POWERBOX BLOB READ-GATE (2026-07-10 — ADR-373 read-scope, ADR-427 seam)
# =============================================================================
# A raw upload's blob is served OUT-OF-BAND (a signed URL / content_url), so it
# does NOT pass through the primitive ReadFile gate. Without this, a narrowed
# principal who cannot ReadFile a path could still fetch its blob by URL. This
# closes that hole by consulting the SAME read-scope the primitives use.
#
# SAFETY INVARIANT: every live grant is NULL-scoped, so
# `_is_path_readable_for_principal` returns True (read-all) and this gate is a
# pure no-op — byte-identical to the pre-powerbox serving path. Only a narrowed
# principal (explicit read_scopes) is ever denied.


def _workspace_path_for_storage_path(auth: UserClient, storage_path: str) -> Optional[str]:
    """Map a `documents`-bucket key back to the workspace_files path that serves
    it, for the read-scope consult.

    A raw upload row carries `content_url` = `/api/documents/blob?storage_path=…`
    (ADR-395), so the row whose `content_url` == blob_content_url(storage_path) is
    the file this blob belongs to. Returns its `path`, or None when no such row is
    found (the mapping is genuinely unavailable — the caller then falls back to
    the ownership guard alone, never fabricating a path)."""
    try:
        target = blob_content_url(storage_path)
        result = (
            auth.client.table("workspace_files")
            .select("path")
            .eq(*substrate_scope_filter(auth.user_id))
            .eq("content_url", target)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("path")
    except Exception:  # noqa: BLE001 — best-effort; never break serving on a lookup error
        logger.warning("[POWERBOX] blob→path lookup failed for %s", storage_path, exc_info=True)
    return None


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

# ADR-427 Phase 3: the intake gate is a CONFORMANCE question (D5), not a
# stored-MIME allowlist. The type is DERIVED from magic bytes + extension
# (services/content_types.py — the single source), and acceptance asks "does
# the derived type conform to a base yarnnn declares?" — public.image /
# public.movie / public.audio / public.text, plus the concrete document set.
_DOC_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_MEDIA_BASES = ("public.image", "public.movie", "public.audio")

MAX_FILE_SIZE = 25 * 1024 * 1024        # 25MB — documents/images
MAX_MEDIA_SIZE = 100 * 1024 * 1024      # 100MB — movie/audio (versioned binary)
                                        # NOTE: the effective ceiling is ALSO
                                        # gated by the Supabase project's
                                        # global upload limit — infra config a
                                        # gate cannot see; verify in dashboard.

# Extension resolution for the EXTRACTOR (which parser reads the bytes) —
# derived-type-first, filename fallback. Not a gate.
_MIME_EXTS = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif",
    "video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm",
    "audio/mpeg": "mp3", "audio/wav": "wav", "audio/mp4": "m4a", "audio/ogg": "ogg",
}


def _intake_verdict(filename: str, head: bytes) -> tuple[Optional[str], Optional[str], bool]:
    """The conformance-DAG intake check (ADR-427 D5 / Phase 3).

    Returns (mime, file_type, is_media) — mime None means rejected."""
    from services.content_types import conforms_to, derive_content_type

    mime = derive_content_type(filename, head)
    is_media = any(conforms_to(mime, b) for b in _MEDIA_BASES)
    accepted = is_media or mime in _DOC_MIMES or conforms_to(mime, "public.text")
    if not accepted:
        return None, None, False
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    file_type = _MIME_EXTS.get(mime) or ext or "bin"
    return mime, file_type, is_media


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
            *substrate_scope_filter(user_id)).eq("path", projection_path).limit(1).execute()
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

    # ADR-427 Phase 3: derive the type from the bytes + name (D5) and gate by
    # conformance, never by the caller-declared content_type.
    mime, file_type, is_media = _intake_verdict(filename, content[:64])
    if mime is None:
        return _fail("Unsupported file type — images, video, audio, PDF, DOCX, and text conform")
    from services.content_types import conforms_to
    cap = MAX_MEDIA_SIZE if conforms_to(mime, "public.movie") or conforms_to(mime, "public.audio") else MAX_FILE_SIZE
    if len(content) > cap:
        return _fail(f"File too large. Max {cap // (1024*1024)}MB")
    if len(content) < 10:
        return _fail("File is empty or too small")

    import uuid
    document_id = str(uuid.uuid4())

    # ADR-427 Phase 3: the bytes land as a VERSIONED binary revision in the
    # CAS (workspace-cas bucket behind the storage seam) — attributed,
    # parent-pointered, revertible. The un-versioned documents-bucket copy is
    # retired for new uploads; legacy rows keep serving via /documents/blob.
    result = await process_document(
        document_id=document_id,
        file_content=content,
        file_type=file_type,
        filename=filename,
        file_size=len(content),
        storage_path=None,
        user_id=user_id,
        db_client=service,
    )
    if not result.get("success"):
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
                # ADR-427 Phase 3: entries face the same conformance verdict
                # as direct uploads (extension-only here — bytes are checked
                # again in _process_single_upload after read).
                ext = base.rsplit(".", 1)[-1].lower() if "." in base else ""
                if ext not in _MIME_EXTS.values():
                    continue
                # Guard against zip-bomb single entries before reading.
                if info.file_size > MAX_MEDIA_SIZE:
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

    # POWERBOX read-gate: a narrowed principal must not fetch a blob whose
    # workspace path is outside its read scope. NULL-scoped grants (all live
    # grants) → _is_path_readable_for_principal True → no-op (byte-identical).
    ws_path = _workspace_path_for_storage_path(auth, storage_path)
    if ws_path and not _is_path_readable_for_principal(auth, ws_path):
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

    # POWERBOX read-gate: a narrowed principal must not download a file outside
    # its read scope. The workspace path is `document_path` directly. NULL-scoped
    # grants (all live grants) → readable True → no-op (byte-identical).
    if not _is_path_readable_for_principal(auth, document_path):
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


def _content_form_for_head(auth: UserClient, row: dict) -> dict:
    """The write_revision content form that preserves a file's head blob
    verbatim (ADR-427 Phase 2): {'content_ref': <head blob sha>} when the
    chain exists (text and binary both round-trip), falling back to the text
    denorm re-write for chainless legacy rows."""
    head_id = row.get("head_version_id")
    if head_id:
        try:
            head = (
                auth.client.table("workspace_file_versions")
                .select("blob_sha")
                .eq("id", head_id)
                .limit(1)
                .execute()
            ).data
            if head and head[0].get("blob_sha"):
                return {"content_ref": head[0]["blob_sha"]}
        except Exception as exc:  # noqa: BLE001 — fall back to the denorm
            logger.warning("[DOCUMENTS] head blob lookup failed: %s", exc)
    return {"content": row.get("content", "") or ""}


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
        .select("content, head_version_id") \
        .eq(*substrate_scope_filter(auth.user_id)) \
        .eq("path", document_path) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    # Archive = new revision, lifecycle='archived', operator-attributed.
    # ADR-427 Phase 2: re-reference the head's BLOB (content_ref) instead of
    # re-writing the text denorm — a binary file's denorm is '' and re-writing
    # it would put an empty TEXT revision at the head of a binary chain.
    # Text files behave byte-identically through content_ref.
    service = get_service_client()
    write_revision(
        db_client=service,
        user_id=auth.user_id,
        path=document_path,
        **_content_form_for_head(auth, result.data[0]),
        authored_by="operator",
        author_identity_uuid=auth.user_id,  # ADR-410/412 viewer pass — which human
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
        .select("content, lifecycle, head_version_id") \
        .eq(*substrate_scope_filter(auth.user_id)) \
        .eq("path", path) \
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="File not found")
    row = result.data[0]
    if row.get("lifecycle") != "archived":
        raise HTTPException(status_code=409, detail="File is not in the trash")

    service = get_service_client()
    # ADR-427 Phase 2: content_ref preserves the head blob (text OR binary)
    # verbatim — see delete_document.
    write_revision(
        db_client=service,
        user_id=auth.user_id,
        path=path,
        **_content_form_for_head(auth, row),
        authored_by="operator",
        author_identity_uuid=auth.user_id,  # ADR-410/412 viewer pass — which human
        message="Restored from trash",
        lifecycle="active",
    )
    return {"success": True, "message": "Restored", "path": path}


# =============================================================================
# PERMANENT DELETE — ADR-478: the terminal step, unrecoverable-not-unremembered
# =============================================================================
# The second step of the delete verb. Trash (archive) is reversible; this is not.
# Removes the deleted path's row + chain + content (blobs no other path cites),
# preserves every OTHER file's ledger. Owner-grade (destroys shared content,
# ADR-478 D4 = ADR-476 D2), archived-only, and refused if a live file cites the
# path (ADR-478 D5 — the reference edge doing real work).


def _require_permadelete_authority(user_id: str) -> Optional[str]:
    """Owner-grade gate + the resolved workspace (ADR-478 D4). Returns the
    workspace_id for scoping. N=1 (no workspace resolved) → the caller IS the
    workspace, allowed — byte-identical to every solo operator today."""
    from services.workspace_purge import resolve_purge_workspace
    from services.principal_grants import has_workspace_clear_authority

    ws = resolve_purge_workspace(user_id)
    if ws and not has_workspace_clear_authority(user_id, ws):
        raise HTTPException(
            status_code=403,
            detail=(
                "Permanently deleting a file requires the workspace owner (or a "
                "principal granted `workspace:clear`). This destroys shared "
                "content and cannot be undone."
            ),
        )
    return ws


def _assert_archived_and_uncited(client: Any, user_id: str, ws: Optional[str], path: str) -> None:
    """The two content guards: the file must be in trash, and nothing live may
    cite it (ADR-478 D5). Raises 404 / 409 / 409 respectively."""
    from services.workspace_purge import _purge_scope
    from services.authored_substrate import list_dependents

    row = _purge_scope(
        client.table("workspace_files").select("lifecycle"), user_id, ws
    ).eq("path", path).limit(1).execute().data
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    if row[0].get("lifecycle") != "archived":
        raise HTTPException(
            status_code=409,
            detail="Only files in the trash can be permanently deleted. Move it to trash first.",
        )
    # ADR-478 D5 — refuse if a LIVE file's head cites this path. list_dependents
    # already excludes archived dependents, so a trashed file citing this one
    # does not block.
    deps = list_dependents(client, user_id=user_id, path=path, limit=5)
    if deps:
        names = ", ".join(d["path"].rsplit("/", 1)[-1] for d in deps[:5])
        raise HTTPException(
            status_code=409,
            detail=f"Can't permanently delete — {len(deps)} file(s) were made from this: {names}. Delete or update those first.",
        )


class PermanentDeleteRequest(BaseModel):
    path: str


@router.post("/documents/permanent-delete")
async def permanent_delete_document(body: PermanentDeleteRequest, auth: UserClient):
    """Permanently delete ONE trashed file (ADR-478). Unrecoverable.

    Owner-grade, archived-only, uncited-only. Removes the path's row + chain +
    content; every other file's ledger is untouched.
    """
    from services.permanent_delete import permanently_delete_file

    path = body.path if body.path.startswith("/") else "/" + body.path
    if not operator_can_organize(path):
        raise HTTPException(
            status_code=403,
            detail="This file is managed by the system and can't be deleted from here.",
        )
    ws = _require_permadelete_authority(auth.user_id)
    service = get_service_client()
    _assert_archived_and_uncited(service, auth.user_id, ws, path)
    summary = permanently_delete_file(
        service, user_id=auth.user_id, workspace_id=ws, path=path
    )
    return {"success": True, "message": "Permanently deleted", "path": path, **summary}


@router.post("/documents/trash/empty")
async def empty_trash(auth: UserClient):
    """Empty the trash — permanently delete every archived file in the operator's
    organize reach (ADR-478 D1). Unrecoverable.

    Owner-grade. A file that a live file still cites is SKIPPED (not fatal — the
    rest empty), and reported back so the operator knows what remained and why.
    """
    from services.permanent_delete import permanently_delete_file
    from services.authored_substrate import list_dependents
    from services.workspace_purge import _purge_scope

    ws = _require_permadelete_authority(auth.user_id)
    service = get_service_client()

    archived = _purge_scope(
        service.table("workspace_files").select("path"), auth.user_id, ws
    ).eq("lifecycle", "archived").limit(500).execute().data or []

    deleted = 0
    skipped: List[str] = []
    for row in archived:
        path = row["path"]
        if not operator_can_organize(path):
            continue
        if list_dependents(service, user_id=auth.user_id, path=path, limit=1):
            skipped.append(path.rsplit("/", 1)[-1])
            continue
        permanently_delete_file(service, user_id=auth.user_id, workspace_id=ws, path=path)
        deleted += 1

    msg = f"Permanently deleted {deleted} file(s)"
    if skipped:
        msg += f"; {len(skipped)} kept (still referenced): {', '.join(skipped[:5])}"
    return {"success": True, "message": msg, "deleted": deleted, "skipped": skipped}


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
# CREATE FOLDER — ADR-424 D2/D6: the operator makes a top-level PEER folder
# =============================================================================

class CreateFolderRequest(BaseModel):
    #: Workspace-relative path of the new folder (e.g. "the-acme-deal" or
    #: "operation/projects/q3"). A top-level value creates a peer of Documents.
    path: str


def _sanitize_folder_segment(seg: str) -> str:
    """A folder name segment → filesystem-safe (letters/digits/dash/underscore/
    space collapsed to dashes, lowercased). Rejects empty + traversal."""
    import re
    seg = seg.strip().strip("/").strip()
    seg = re.sub(r"[^\w\s-]", "", seg).strip()
    seg = re.sub(r"[\s_]+", "-", seg).lower()
    return seg


@router.post("/documents/folder")
async def create_folder(body: CreateFolderRequest, auth: UserClient):
    """Create a folder — including a TOP-LEVEL PEER of the Documents/Downloads
    homes (ADR-424 D2: pure-OS — you don't ask permission to name a folder for
    your work; the operator + AI both may).

    Folders are implicit in the substrate (a folder exists iff a file exists
    under its prefix — the tree is derived from paths). So "create a folder"
    seeds the folder's first file: a starter ``README.md`` (a real, useful
    file — the folder's note — not clutter). Written through the WriteFile
    primitive → the ADR-209 write path, operator-attributed.

    Guarded by ``operator_can_organize``: the operator may create a folder
    anywhere they may organize — i.e. everywhere except system/, inbound/ (the
    immutable arrival lane), and a machine-config leaf. A peer meaning-folder
    (unknown top-level root) is permitted (the gate lists LOCKED prefixes; an
    unknown root falls through — ADR-424).
    """
    # Normalize + sanitize each segment; reject empties / traversal.
    raw = (body.path or "").strip().lstrip("/")
    if raw.startswith("workspace/"):
        raw = raw[len("workspace/"):]
    segments = [_sanitize_folder_segment(s) for s in raw.split("/") if s.strip()]
    segments = [s for s in segments if s]
    if not segments:
        raise HTTPException(status_code=400, detail="Enter a folder name.")

    rel_folder = "/".join(segments)
    readme_path = f"{rel_folder}/README.md"
    abs_folder = f"/workspace/{rel_folder}"
    abs_readme = f"/workspace/{readme_path}"

    # The operator's organize reach is the create reach (ADR-424 D2). A folder
    # under system/ / inbound/ / a machine-config leaf is refused honestly.
    if not operator_can_organize(abs_readme):
        raise HTTPException(
            status_code=403,
            detail="You can't create a folder here — that location is managed by the system.",
        )

    # If the folder already has files, don't reseed (idempotent-ish create).
    existing = auth.client.table("workspace_files") \
        .select("path") \
        .eq(*substrate_scope_filter(auth.user_id)) \
        .like("path", f"{abs_folder}/%") \
        .or_("lifecycle.is.null,lifecycle.neq.archived") \
        .limit(1) \
        .execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="A folder with that name already exists.")

    from services.primitives.registry import execute_primitive
    leaf = segments[-1]
    result = await execute_primitive(auth, "WriteFile", {
        "scope": "workspace",
        "path": readme_path,
        "content": f"# {leaf}\n\n_This folder was created to hold work about {leaf}._\n",
        "message": f"Create folder: {rel_folder}",
        "authored_by": "operator",
    })
    if not (isinstance(result, dict) and result.get("success")):
        detail = (result or {}).get("message", "Could not create the folder.")
        raise HTTPException(status_code=400, detail=detail)
    return {"success": True, "path": abs_folder, "seeded": abs_readme}


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
            author_identity_uuid=auth.user_id,  # ADR-410/412 viewer pass — which human
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
