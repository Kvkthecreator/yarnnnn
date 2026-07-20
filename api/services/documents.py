"""
Document Processing Service

ADR-249: Two-Intent File Handling — Ephemeral vs Persistent.

Persistent uploads (POST /documents/upload) write extracted text to
/workspace/uploads/{slug}.md via the Authored Substrate (ADR-209).
YARNNN sees uploaded content immediately via ReadFile — no chunking,
no separate DB table needed.

Ephemeral chat attachments are handled separately via POST /api/chat/attach
(Anthropic Files API path). See api/routes/chat.py.
"""

import io
import re
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# =============================================================================
# TEXT EXTRACTION
# =============================================================================

async def extract_text_from_pdf(file_content: bytes) -> tuple[str, int]:
    """Extract text from PDF. Returns (text, page_count)."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_content))
        pages = [page.extract_text() for page in reader.pages if page.extract_text()]
        return "\n\n".join(pages), len(reader.pages)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return "", 0


async def extract_text_from_docx(file_content: bytes) -> tuple[str, int]:
    """Extract text from DOCX. Returns (text, paragraph_count)."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs), len(paragraphs)
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return "", 0


async def extract_text_from_txt(file_content: bytes) -> tuple[str, int]:
    """Extract text from plain text or markdown. Returns (text, line_count)."""
    try:
        text = file_content.decode("utf-8")
        return text, len(text.split("\n"))
    except Exception as e:
        logger.error(f"TXT extraction failed: {e}")
        return "", 0


async def extract_text(file_content: bytes, file_type: str) -> tuple[str, int]:
    """Dispatch text extraction by file type. Returns (text, unit_count)."""
    file_type = file_type.lower().strip(".")
    if file_type == "pdf":
        return await extract_text_from_pdf(file_content)
    elif file_type in ("docx", "doc"):
        return await extract_text_from_docx(file_content)
    else:
        return await extract_text_from_txt(file_content)


# Phase-A chassis (ADR-457 D6 as amended): image uploads ride the SAME raw
# lane (private bucket + content_url reference) with no text projection — a
# vision model reads the bytes via a signed URL at turn time. NOT gated on
# ADR-427 (the utf-8 wall is the CAS ledger path; raw uploads never touch it).
IMAGE_TYPES = {"png", "jpg", "jpeg", "webp", "gif"}


def upload_mime(file_type: str) -> str:
    """The real MIME for a raw upload's revision row."""
    ft = file_type.lower().strip(".")
    if ft in IMAGE_TYPES:
        return f"image/{'jpeg' if ft in ('jpg', 'jpeg') else ft}"
    return f"application/{ft}"


# =============================================================================
# SLUG GENERATION
# =============================================================================

def _filename_to_slug(filename: str) -> str:
    """Convert a filename to a workspace-safe slug (max 60 chars).

    Unicode-preserving (2026-07-01 fix): the prior ASCII-only filter
    (`[^a-z0-9-]`) replaced EVERY non-Latin character with a dash, so a fully
    non-ASCII name (e.g. Korean `배출증 출력.pdf`) collapsed to all-dashes →
    stripped → the generic `"document"` fallback (operator-observed KVK). Path
    segments in this filesystem are Unicode-safe (the tree already holds Korean
    filenames), so we keep letters/digits of ANY script + dash, lowercase only
    the ASCII (casefold on CJK is a no-op), and replace only whitespace +
    path-unsafe punctuation with dashes.
    """
    # Strip extension
    name = filename.rsplit(".", 1)[0] if "." in filename else filename
    slug = name.strip().lower()
    # Replace anything that is NOT a Unicode word char (letters/digits/_ of any
    # script) or a dash with a dash. `re.UNICODE` is default in Py3; `\w`
    # includes CJK/Hangul. Underscores → dashes for kebab consistency.
    slug = re.sub(r"[^\w-]", "-", slug, flags=re.UNICODE)
    slug = slug.replace("_", "-")
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:60] or "document"


def _unique_raw_path(raw_path: str, db_client, user_id: str) -> str:
    """Return `raw_path`, appending -N before the extension if it already exists.

    Works on a full raw-lane path with its REAL extension (e.g.
    /workspace/inbound/uploads/operator/acme-brief.pdf), so re-uploading the
    same filename yields acme-brief-2.pdf rather than clobbering. The projection
    sibling is derived from whichever raw path this returns, so the two stay
    co-located and collision-free together.
    """
    head, _, ext = raw_path.rpartition(".")
    stem = head if _ else raw_path  # no dot → treat whole path as stem
    suffix = f".{ext}" if _ else ""
    try:
        existing = db_client.table("workspace_files") \
            .select("path") \
            .eq("user_id", user_id) \
            .like("path", f"{stem}%{suffix}") \
            .execute()
        paths = {r["path"] for r in (existing.data or [])}
    except Exception:
        paths = set()

    if raw_path not in paths:
        return raw_path

    for i in range(2, 100):
        candidate = f"{stem}-{i}{suffix}"
        if candidate not in paths:
            return candidate
    return f"{stem}-{int(datetime.now(timezone.utc).timestamp())}{suffix}"


# =============================================================================
# WORKSPACE FILE WRITE
# =============================================================================

# ADR-395: `_build_upload_workspace_file` (the frontmatter-in-body extracted-text
# builder, ADR-249) is DELETED. Uploads no longer write a derived `.md` as the
# substrate object — the raw blob is retained (content_url) and the text is a
# separate derived projection (Piece B). Singular Implementation: one intake
# shape, DP34-conformant.


# =============================================================================
# DOCUMENT PROCESSING PIPELINE (ADR-249 persistent path)
# =============================================================================

async def process_document(
    document_id: str,
    file_content: bytes,
    file_type: str,
    filename: str,
    file_size: int,
    storage_path: Optional[str],
    user_id: str,
    db_client,
) -> dict:
    """
    Persistent upload pipeline — ADR-395 conformance (retain raw · derive projection).

    DP34 / DP32: an uploaded file enters as an IMMUTABLE attributed RAW
    observation, and the searchable text is a SEPARATE derived act that cites
    the raw. Concretely:
      1. Land the RAW as a VERSIONED BINARY revision (ADR-427 Phase 3) at
         inbound/uploads/{principal}/{slug}.{ext} — bytes in the CAS behind
         the storage seam, type derived (D5), serving minted at read (D4).
         (`storage_path` is a legacy parameter; the un-versioned bucket copy
         is retired — pass None.)
      2. Derive the TEXT PROJECTION inline (Piece B) via the ExtractTextFromBlob
         primitive — a co-located `.extracted.md` sibling carrying
         `derived_from: <raw path>`, embedded for search. Model-consumable
         (DP34): the projection is what a model reads; the raw is retained.

    Inline-mechanical (ADR-395 refined): the derive runs in THIS request
    (zero-LLM, deterministic) so the file is searchable the instant upload
    returns — an upload is a one-shot, not a cadenced capture.

    Returns:
        {success, workspace_path, raw_path, projection_path, word_count}
        or {success: False, error}. `workspace_path` is the RAW path (what the
        surface opens); the projection is a sibling.
    """
    # 1. Extract text up front to fail fast on unreadable files (before we write
    #    a raw revision for something with no derivable projection). The SAME
    #    extraction the derive primitive runs — computed once here for the
    #    fast-fail, handed to the primitive so it isn't re-run.
    from services.content_types import conforms_to, derive_content_type

    mime = derive_content_type(filename, file_content[:64])
    is_media = any(
        conforms_to(mime, b) for b in ("public.image", "public.movie", "public.audio")
    )
    if is_media:
        # Media carries no text projection — the raw IS the substance; a
        # vision model reads an image via a minted URL at turn time (Phase A);
        # movie/audio are retained-not-yet-consumable (DP34).
        text, unit_count = "", 0
    else:
        text, unit_count = await extract_text(file_content, file_type)
        if not text or len(text.strip()) < 50:
            return {"success": False, "error": "No text could be extracted from document"}

    slug = _filename_to_slug(filename)
    # 2. RETAIN — land the raw as a VERSIONED BINARY revision (ADR-427 Phase 3):
    #    the bytes enter the content-addressed store behind the storage seam —
    #    attributed, parent-pointered, revertible; type derived at the door
    #    (D5); serving minted at read (D4). No un-versioned bucket copy, no
    #    stored content_url. principal defaults to "operator" (ADR-373).
    principal = "operator"
    raw_path = _unique_raw_path(resolve_upload_raw_path(principal, slug, file_type), db_client, user_id)
    try:
        from services.authored_substrate import write_revision
        write_revision(
            db_client,
            user_id=user_id,
            path=raw_path,
            content_bytes=file_content,
            authored_by=principal,
            message=f"upload {filename}",
            lifecycle="active",
            # ADR-448 (closing the ADR-423 D3 gap): an inbound/ write is an
            # observation — the arrival badge on the ledger, not the path.
            revision_kind="observation",
        )
    except Exception as e:
        logger.error(f"[DOCUMENTS] Failed to write raw upload {raw_path}: {e}")
        return {"success": False, "error": f"Failed to write workspace file: {e}"}

    if is_media:
        # No projection to derive — the raw is retained + attributed (DP32);
        # consumption is visual (vision content parts / a minted URL) or
        # retained-not-yet-consumable for movie/audio (DP34).
        logger.info(f"[DOCUMENTS] Uploaded {raw_path} (raw media {mime}, no projection)")
        return {
            "success": True,
            "workspace_path": raw_path,
            "raw_path": raw_path,
            "projection_path": None,
            "word_count": 0,
            "embed_pending": False,
        }

    # 3. DERIVE — the text projection, inline + mechanical (Piece B / DP34).
    #    Runs the ExtractTextFromBlob primitive so upload + connector share ONE
    #    derive path (Singular Implementation). We pass the already-extracted
    #    text so the blob isn't re-fetched/re-parsed.
    projection_path = upload_projection_path(raw_path)
    try:
        from services.primitives.registry import execute_primitive
        from services.supabase import AuthenticatedClient
        # The derive is MECHANICAL make-AI-ready, not the operator's authored
        # act — attributed `system:extract` (ADR-288 D2; same spirit as the
        # capture lane's `system:<slug>`). It writes the derived projection,
        # NOT the raw (the raw is the operator's, written above).
        auth = AuthenticatedClient(
            client=db_client, user_id=user_id, caller_identity="system:extract",
        )
        # embed=False: DEFER the paid embed off this synchronous request. The
        # projection is written + BM25-searchable the instant this returns; the
        # embedding (enrichment) is scheduled by the route as a background task
        # (ADR-325: embedding is enrichment; the mechanical floor is the promise).
        derive = await execute_primitive(auth, "ExtractTextFromBlob", {
            "raw_path": raw_path,
            "write_to": projection_path,
            "text": text,          # reuse the fast-fail extraction (no re-parse)
            "source_filename": filename,
            "file_type": file_type,
            "embed": False,
        })
        if isinstance(derive, dict) and derive.get("success"):
            embed_pending = bool(derive.get("embed_pending"))
        else:
            # Non-fatal: the raw is retained; the projection just isn't there
            # yet (retained-but-not-yet-consumable, DP34). Surface in the log.
            embed_pending = False
            logger.warning(f"[DOCUMENTS] Projection derive failed for {raw_path}: {derive}")
    except Exception as e:
        embed_pending = False
        logger.warning(f"[DOCUMENTS] Projection derive raised for {raw_path}: {e}")

    word_count = len(text.split())
    logger.info(f"[DOCUMENTS] Uploaded {raw_path} (raw) + {projection_path} (projection, {word_count} words)")

    return {
        "success": True,
        "workspace_path": raw_path,       # the surface opens the raw
        "raw_path": raw_path,
        "projection_path": projection_path,
        "word_count": word_count,
        # The route reads this to schedule the deferred embed as a background task.
        "embed_pending": embed_pending,
    }


# =============================================================================
# BLOB REFERENCE + SIGNED URL (ADR-395 Piece A + C)
# =============================================================================
# The raw upload blob lives in the PRIVATE `documents` bucket, so a persisted
# content_url cannot be a signed URL (it expires in 1h). content_url instead
# carries a STABLE app endpoint that mints a fresh signed URL on each access
# (ADR-395: the raw revision stores a stable reference; the URL is resolved at
# read-time). This is also the seam Piece C's MCP raw-reference reuses.

# The bucket the upload route stores originals in (routes/documents.py).
DOCUMENTS_BUCKET = "documents"


def blob_content_url(storage_path: str) -> str:
    """The STABLE content_url for a raw upload blob (ADR-395 Piece A).

    A relative app endpoint (not a signed URL) — the FE/consumer hits it and it
    302-redirects to a freshly-minted signed URL. Stored on the raw revision so
    the reference never goes stale. `storage_path` is the private-bucket key
    (e.g. `{user_id}/{document_id}/original.pdf`).
    """
    from urllib.parse import quote
    return f"/api/documents/blob?storage_path={quote(storage_path, safe='')}"


def create_signed_url_for_storage_path(
    service_client, storage_path: str, expires_in: int = 3600
) -> Optional[str]:
    """Mint a signed download URL for a `documents`-bucket storage_path.

    The service-layer wrapper around `create_signed_url` (was inline in
    routes/documents.py's download route). Returns None on failure — callers
    decide whether that is fatal. Reused by the /blob redirect route (Piece A)
    and, later, the MCP raw-reference (Piece C).
    """
    try:
        signed = service_client.storage.from_(DOCUMENTS_BUCKET).create_signed_url(
            path=storage_path,
            expires_in=expires_in,
        )
        return signed.get("signedURL") or signed.get("signedUrl")
    except Exception as e:  # noqa: BLE001 — caller decides fatality
        logger.error(f"[DOCUMENTS] Signed-URL mint failed for {storage_path}: {e}")
        return None


# =============================================================================
# RAW-LANE UPLOAD PATH (ADR-395 Piece A / DP32)
# =============================================================================
# uploads/ is the N=human case of the inbound/ raw lane (DP32 / ADR-376 §4).
# A human upload lands its RAW blob at inbound/uploads/{principal}/{slug}.{ext},
# immutable + attributed, sibling to the machine inbound/{transport}/ sublanes.
# The DERIVED text projection (ADR-395 Piece B) lands co-located as a sibling
# `.extracted.md`, citing the raw via `derived_from`.

INBOUND_UPLOADS_PREFIX = "/workspace/inbound/uploads"


def resolve_upload_raw_path(principal: str, slug: str, ext: str) -> str:
    """Where a human upload's RAW blob lands (ADR-395 Piece A / DP32).

    inbound/uploads/{principal}/{slug}.{ext} — immutable, attributed to the
    uploading principal. `ext` is the real file extension (pdf/docx/…), so the
    raw lane preserves the original format. The derived text projection is a
    sibling (see `upload_projection_path`).
    """
    p = _filename_to_slug(principal) or "operator"
    ext = (ext or "bin").lstrip(".")
    return f"{INBOUND_UPLOADS_PREFIX}/{p}/{slug}.{ext}"


def upload_projection_path(raw_path: str) -> str:
    """The derived text-projection path for a raw upload (ADR-395 Piece B).

    Co-located sibling of the raw blob, `.extracted.md` — a searchable text
    derivation that CITES the raw via `derived_from`. Kept beside the raw so the
    two are atomic (ADR-395 §7.1: sibling projection, not a separate operation/
    file for Phase 1; the additive seat-derive into operation/ layers on later).
    """
    # Strip the raw extension, append `.extracted.md`.
    base = raw_path.rsplit(".", 1)[0] if "." in raw_path.rsplit("/", 1)[-1] else raw_path
    return f"{base}.extracted.md"


def is_upload_projection(path: str) -> bool:
    """True iff `path` is an upload's DERIVED text projection (ADR-395 Piece B).

    The projection is plumbing — a searchable text derivation of a raw upload,
    consumed by recall/QueryKnowledge, NOT a user file. The Files surface hides
    it so the operator sees ONE file (their PDF), not a confusing raw+extracted
    pair. The predicate is intentionally NARROW + SYMMETRIC: it matches ONLY the
    co-located projection under the upload raw lane —

        inbound/uploads/{principal}/{slug}.extracted.md

    so a user's own prose `.md` (under uploads/, operation/, anywhere) is NEVER
    hidden, and a PURE-TEXT upload — which has no separate raw container and
    produces no projection to hide — shows normally. Anchoring on BOTH the
    `.extracted.md` suffix AND the `inbound/uploads/` lane (not the suffix alone)
    is what makes the rule seamless + reversible: remove the derive and nothing
    is hidden; the raw is always visible either way.
    """
    norm = path.lstrip("/")
    if norm.startswith("workspace/"):
        norm = norm[len("workspace/"):]
    return norm.startswith("inbound/uploads/") and norm.endswith(".extracted.md")
