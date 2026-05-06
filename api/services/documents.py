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


# =============================================================================
# SLUG GENERATION
# =============================================================================

def _filename_to_slug(filename: str) -> str:
    """Convert a filename to a workspace-safe slug (kebab-case, max 60 chars)."""
    # Strip extension
    name = filename.rsplit(".", 1)[0] if "." in filename else filename
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:60] or "document"


def _unique_upload_path(slug: str, db_client, user_id: str) -> str:
    """Return /workspace/uploads/{slug}.md, appending -N if path already exists."""
    base = f"/workspace/uploads/{slug}.md"
    try:
        existing = db_client.table("workspace_files") \
            .select("path") \
            .eq("user_id", user_id) \
            .like("path", f"/workspace/uploads/{slug}%.md") \
            .execute()
        paths = {r["path"] for r in (existing.data or [])}
    except Exception:
        paths = set()

    if base not in paths:
        return base

    for i in range(2, 100):
        candidate = f"/workspace/uploads/{slug}-{i}.md"
        if candidate not in paths:
            return candidate
    return f"/workspace/uploads/{slug}-{int(datetime.now(timezone.utc).timestamp())}.md"


# =============================================================================
# WORKSPACE FILE WRITE
# =============================================================================

def _build_upload_workspace_file(
    filename: str,
    file_type: str,
    file_size: int,
    storage_path: str,
    text: str,
    unit_count: int,
    uploaded_at: str,
    user_id: str,
) -> str:
    """Build the markdown content for /workspace/uploads/{slug}.md."""
    word_count = len(text.split())
    extraction_method = f"{file_type}-pypdf2" if file_type == "pdf" else f"{file_type}-extract"

    frontmatter_lines = [
        "---",
        f"original_filename: {filename}",
        f"mime_type: application/{file_type}",
        f"uploaded_at: {uploaded_at}",
        f"size_bytes: {file_size}",
        f"storage_path: {storage_path}",
        f"word_count: {word_count}",
        f"extraction_method: {extraction_method}",
        "---",
        "",
        f"# {filename}",
        "",
        text,
    ]
    return "\n".join(frontmatter_lines)


# =============================================================================
# DOCUMENT PROCESSING PIPELINE (ADR-249 persistent path)
# =============================================================================

async def process_document(
    document_id: str,
    file_content: bytes,
    file_type: str,
    filename: str,
    file_size: int,
    storage_path: str,
    user_id: str,
    db_client,
) -> dict:
    """
    Persistent upload pipeline (ADR-249 Type B):
      1. Extract text from file
      2. Build /workspace/uploads/{slug}.md content
      3. Write via authored_substrate.write_revision (ADR-209)
      4. Embed at file level via workspace_files.embedding

    No chunking. No filesystem_chunks writes.
    The workspace file IS the document — YARNNN reads it via ReadFile.

    Returns:
        {success, workspace_path, word_count} or {success: False, error}
    """
    uploaded_at = datetime.now(timezone.utc).isoformat()

    # 1. Extract text
    text, unit_count = await extract_text(file_content, file_type)

    if not text or len(text.strip()) < 50:
        return {"success": False, "error": "No text could be extracted from document"}

    # 2. Build workspace file content
    slug = _filename_to_slug(filename)
    workspace_path = _unique_upload_path(slug, db_client, user_id)
    content = _build_upload_workspace_file(
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=storage_path,
        text=text,
        unit_count=unit_count,
        uploaded_at=uploaded_at,
        user_id=user_id,
    )

    # 3. Write via authored substrate (ADR-209)
    try:
        from services.authored_substrate import write_revision
        write_revision(
            db_client,
            user_id=user_id,
            path=workspace_path,
            content=content,
            authored_by="operator",
            message=f"upload {filename}",
            lifecycle="permanent",
        )
    except Exception as e:
        logger.error(f"[DOCUMENTS] Failed to write workspace file {workspace_path}: {e}")
        return {"success": False, "error": f"Failed to write workspace file: {e}"}

    # 4. Embed at file level for SearchFiles findability
    try:
        from services.embeddings import get_embedding
        # Embed a representative excerpt (first 2000 chars of body text avoids frontmatter noise)
        excerpt = text[:2000]
        embedding = await get_embedding(excerpt)
        if embedding:
            db_client.table("workspace_files").update({
                "embedding": embedding
            }).eq("user_id", user_id).eq("path", workspace_path).execute()
    except Exception as e:
        # Non-fatal: file is readable, just not semantically searchable yet
        logger.warning(f"[DOCUMENTS] Embedding failed for {workspace_path}: {e}")

    word_count = len(text.split())
    logger.info(f"[DOCUMENTS] Wrote {workspace_path} ({word_count} words)")

    return {
        "success": True,
        "workspace_path": workspace_path,
        "word_count": word_count,
    }
