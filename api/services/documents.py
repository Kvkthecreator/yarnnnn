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
from typing import Iterable, Optional
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


# Word, Excel and PowerPoint are read by the office kernel (`services/office/`,
# ADR-671): their projections carry the addresses an in-place edit takes, so
# the reader and the editor live in one module per format.


#: Ceiling on the bytes an archive-shaped format may inflate to while we read it
#: (hwpx members, hwp section streams). A 25MB upload that expands past this is
#: a decompression bomb, not a document; it reads as empty and takes the marker.
_MAX_INFLATED_BYTES = 64 * 1024 * 1024


def _local(tag) -> str:
    """An XML tag's local name — OWPML ships under more than one namespace URI."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _hwpx_t_text(t) -> str:
    """One OWPML `t` run's text — inline `tab`/`lineBreak` elements kept."""
    parts = [t.text or ""]
    for child in t:
        tag = _local(child.tag)
        parts.append("\t" if tag == "tab" else "\n" if tag == "lineBreak" else "")
        parts.append(child.tail or "")
    return "".join(parts)


def _hwpx_element(el, out: list[str]) -> None:
    """One OWPML element in document order: a `p` is a paragraph, a `tbl` is
    TSV rows, anything else is walked for the paragraphs it holds.

    A table sits INSIDE a run of its anchoring paragraph, and its cells hold
    paragraphs of their own — so a paragraph's text is only its own `t`
    elements, and anything nested (tables, text boxes) is walked as its own
    blocks after it. Collecting every `t` under a `p` would print each cell
    twice.
    """
    tag = _local(el.tag)
    if tag == "p":
        own: list[str] = []
        nested: list = []
        for run in el:
            if _local(run.tag) != "run":
                continue
            for part in run:
                if _local(part.tag) == "t":
                    own.append(_hwpx_t_text(part))
                else:
                    nested.append(part)
        text = "".join(own).strip()
        if text:
            out.append(text)
        for part in nested:
            _hwpx_element(part, out)
    elif tag == "tbl":
        rows: list[str] = []
        for tr in (c for c in el if _local(c.tag) == "tr"):
            cells = []
            for tc in (c for c in tr if _local(c.tag) == "tc"):
                inner: list[str] = []
                for child in tc:
                    _hwpx_element(child, inner)
                cells.append(" ".join(inner).replace("\t", " ").strip())
            if any(cells):
                rows.append("\t".join(cells))
        if rows:
            out.append("\n".join(rows))
    else:
        for child in el:
            _hwpx_element(child, out)


async def extract_text_from_hwpx(file_content: bytes) -> tuple[str, int]:
    """Extract text from HWPX (Hancom Office's OWPML) — ADR-395 am.2 D18.

    An HWPX is a zip of XML; the body is `Contents/section{N}.xml`, in section
    order. Parsed with entity resolution and network access OFF — this is a
    member's upload, and XML is a format that can ask to fetch things.
    Returns (text, section_count).
    """
    try:
        import re as _re
        import zipfile
        from lxml import etree

        parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
        blocks: list[str] = []
        with zipfile.ZipFile(io.BytesIO(file_content)) as zf:
            sections = sorted(
                (i for i in zf.infolist()
                 if _re.fullmatch(r"Contents/section\d+\.xml", i.filename)),
                key=lambda i: int(_re.search(r"\d+", i.filename.rsplit("/", 1)[-1]).group()),
            )
            if sum(i.file_size for i in sections) > _MAX_INFLATED_BYTES:
                return "", 0
            for info in sections:
                _hwpx_element(etree.fromstring(zf.read(info), parser), blocks)
        return "\n\n".join(blocks), len(sections)
    except Exception as e:
        logger.error(f"HWPX extraction failed: {e}")
        return "", 0


#: HWP 5.x paragraph text record (HWPTAG_BEGIN 0x10 + 51).
_HWPTAG_PARA_TEXT = 67
#: Control characters that occupy EIGHT UTF-16 units in a PARA_TEXT record
#: (inline + extended controls: code, a 4-unit payload, the code again).
#: Every other code below 32 is one unit wide.
_HWP_WIDE_CONTROLS = frozenset({1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23})


def _hwp_para_text(payload: bytes) -> str:
    """One PARA_TEXT record → its visible text, controls skipped (tab kept)."""
    units = [int.from_bytes(payload[i:i + 2], "little") for i in range(0, len(payload) - 1, 2)]
    out: list[str] = []
    i = 0
    while i < len(units):
        u = units[i]
        if u >= 32:
            out.append(chr(u))
            i += 1
        elif u in _HWP_WIDE_CONTROLS:
            if u == 9:
                out.append("\t")
            i += 8
        else:
            if u in (10, 13):
                out.append("\n")
            i += 1
    return "".join(out)


async def extract_text_from_hwp(file_content: bytes) -> tuple[str, int]:
    """Extract text from HWP 5.x (the binary Hancom format) — ADR-395 am.2 D18.

    An OLE compound file. `FileHeader` says whether the body is compressed
    (bit 0) or password-protected (bit 1); `BodyText/Section{N}` streams are raw
    deflate when compressed, and hold a flat run of tagged records whose
    PARA_TEXT payloads are UTF-16LE. Table cells are paragraphs too, so they
    read in document order as their own lines. A password-protected or
    distribution-locked file has no readable body and returns empty — the
    upload then takes the am.1 D9 marker rather than failing.
    Returns (text, section_count).
    """
    try:
        import re as _re
        import zlib
        import olefile

        ole = olefile.OleFileIO(io.BytesIO(file_content))
        try:
            header = ole.openstream("FileHeader").read()
            if not header.startswith(b"HWP Document File"):
                return "", 0
            flags = int.from_bytes(header[36:40], "little")
            if flags & 0b10:  # password-protected: the body is encrypted
                return "", 0
            compressed = bool(flags & 0b1)
            sections = sorted(
                (e for e in ole.listdir()
                 if len(e) == 2 and e[0] == "BodyText" and _re.fullmatch(r"Section\d+", e[1])),
                key=lambda e: int(e[1][len("Section"):]),
            )
            paragraphs: list[str] = []
            budget = _MAX_INFLATED_BYTES
            for entry in sections:
                raw = ole.openstream(entry).read()
                if compressed:
                    raw = zlib.decompressobj(-15).decompress(raw, budget)
                budget -= len(raw)
                if budget <= 0:
                    return "", 0
                pos = 0
                while pos + 4 <= len(raw):
                    head = int.from_bytes(raw[pos:pos + 4], "little")
                    tag, size = head & 0x3FF, (head >> 20) & 0xFFF
                    pos += 4
                    if size == 0xFFF:
                        size = int.from_bytes(raw[pos:pos + 4], "little")
                        pos += 4
                    if tag == _HWPTAG_PARA_TEXT:
                        text = _hwp_para_text(raw[pos:pos + size]).strip()
                        if text:
                            paragraphs.append(text)
                    pos += size
            return "\n\n".join(paragraphs), len(sections)
        finally:
            ole.close()
    except Exception as e:
        logger.error(f"HWP extraction failed: {e}")
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
    """Dispatch text extraction by file type. Returns (text, unit_count).

    Reached only for a format the derive-registry calls `text`
    (`registry_strategy`, ADR-395 D2) — the registry is the gate, and since
    ADR-395 am.2 D14 it is also the parser table: each format's row in
    `services/file_formats.py` names its extractor. A row with no extractor is
    utf-8 text. An empty return is a legible outcome, not a failure: ADR-395
    am.1 D9 lands the raw and marks the projection.
    """
    from services.file_formats import format_for

    fmt = format_for(file_type)
    if fmt is not None and fmt.extractor is not None:
        return await fmt.extractor(file_content)
    return await extract_text_from_txt(file_content)


# `IMAGE_TYPES` + `upload_mime` were DELETED by ADR-395 am.2 D14: no caller
# remained, and they were a sixth hand-kept copy of the image extension list.
# A raw upload's MIME is `content_types.derive_content_type`, read off the
# format registry.


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
    # NFC first, before anything measures or compares this name. macOS sends a
    # DECOMPOSED filename, so `배출증` off a Finder upload and the same name
    # typed in the browser are different bytes that print identically — and
    # `\w` below happily preserves either, so both reached `path` verbatim.
    # Two production rows were created that way (see `services/naming.py::nfc`).
    from services.naming import nfc
    slug = nfc(name).strip().lower()
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
    /workspace/inbound/uploads/acme-brief.pdf), so re-uploading the
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
    destination: Optional[str] = None,
) -> dict:
    """
    Persistent upload pipeline — ADR-395 conformance (retain raw · derive projection).

    DP34 / DP32: an uploaded file enters as an IMMUTABLE attributed RAW
    observation, and the searchable text is a SEPARATE derived act that cites
    the raw. Concretely:
      1. Land the RAW as a VERSIONED BINARY revision (ADR-427 Phase 3) at
         inbound/uploads/{slug}.{ext} — bytes in the CAS behind
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
    # ADR-395 am.1 D9: the registry decides whether a projection is OWED, and an
    # extraction that comes back empty is a property of the PROJECTION — never a
    # verdict on the file. This branch used to `return success: False` under a
    # 50-character floor, which failed the WHOLE upload: the bytes never landed,
    # so DP34's "retained-but-not-yet-consumable, legibly marked" had no
    # reachable path on this door. A scanned PDF, a chart-only deck and a
    # formula-only sheet are all real files a member can see, open, download and
    # share — they are simply not yet readable by a model, and they say so.
    from services.file_formats import registry_strategy

    strategy = registry_strategy(file_type)
    if is_media or strategy == "passthrough":
        # Media carries no text projection — the raw IS the substance; a
        # vision model reads an image via a minted URL at turn time (Phase A);
        # movie/audio are retained-not-yet-consumable (DP34).
        text, unit_count = "", 0
    elif strategy == "text":
        text, unit_count = await extract_text(file_content, file_type)
    else:
        text, unit_count = "", 0

    slug = _filename_to_slug(filename)
    # 2. RETAIN — land the raw as a VERSIONED BINARY revision (ADR-427 Phase 3):
    #    the bytes enter the content-addressed store behind the storage seam —
    #    attributed, parent-pointered, revertible; type derived at the door
    #    (D5); serving minted at read (D4). No un-versioned bucket copy, no
    #    stored content_url.
    #
    # ATTRIBUTION, not address: the upload is authored by the operator seat
    # (ADR-373). This names WHO, and rides `authored_by` on the revision below;
    # it is deliberately NOT a path segment (ADR-555 amendment 2026-09-16 — a
    # sublane with one possible value disambiguates nothing, and the arrival is
    # badged on the ledger by `revision_kind='observation'`, per D1).
    authored_by = "operator"
    # ADR-555 D3 — where the arrival lands. A caller-supplied destination is the
    # folder the member dropped on; absent one, the intake lane is the default.
    # The lane is a DEFAULT, not a law (D1).
    raw_path = _unique_raw_path(
        resolve_upload_raw_path(slug, file_type, destination=destination),
        db_client,
        user_id,
    )
    try:
        from services.authored_substrate import write_revision
        write_revision(
            db_client,
            user_id=user_id,
            path=raw_path,
            content_bytes=file_content,
            authored_by=authored_by,
            message=f"upload {filename}",
            lifecycle="active",
            # ADR-448 (closing the ADR-423 D3 gap): an inbound/ write is an
            # observation — the arrival badge on the ledger, not the path.
            revision_kind="observation",
        )
    except Exception as e:
        logger.error(f"[DOCUMENTS] Failed to write raw upload {raw_path}: {e}")
        return {"success": False, "error": f"Failed to write workspace file: {e}"}

    if is_media or strategy == "passthrough":
        # No projection to derive — the raw is retained + attributed (DP32);
        # consumption is visual (vision content parts / a minted URL).
        #
        # ADR-395 am.1 D9: movie/audio stay here rather than taking a marker.
        # They are `is_media`, so every surface already presents them as a
        # playable thing — a .md sibling saying "not readable" would add a file
        # to the member's folder to explain something the player already shows.
        # The marker exists for a file that otherwise looks like a dead end.
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
    derived = await derive_upload_projection(
        db_client, user_id, raw_path, text, filename=filename, file_type=file_type,
    )
    projection_path = derived["projection_path"] or upload_projection_path(raw_path)
    embed_pending = derived["embed_pending"]

    word_count = len(text.split())
    kind = "projection" if word_count else "marker"   # am.1 D9
    logger.info(f"[DOCUMENTS] Uploaded {raw_path} (raw) + {projection_path} ({kind}, {word_count} words)")

    return {
        "success": True,
        "workspace_path": raw_path,       # the surface opens the raw
        "raw_path": raw_path,
        "projection_path": projection_path,
        "word_count": word_count,
        # The route reads this to schedule the deferred embed as a background task.
        "embed_pending": embed_pending,
    }


async def derive_upload_projection(
    db_client,
    user_id: str,
    raw_path: str,
    text: str,
    *,
    filename: str,
    file_type: str,
    workspace_id: Optional[str] = None,
) -> dict:
    """Derive a landed binary's `.extracted.md` projection (ADR-395 Piece B).

    The ONE derive tail for a binary that has just landed: an upload
    (`process_document`), a new office file (`services/office/create.py`) and an
    office edit or a restore (`land_binary_revision`) all call it, so a file yarnnn WROTE is indexed exactly as a
    file a member UPLOADED — same sibling, same attribution, same marker when
    the text is empty. Runs the ExtractTextFromBlob primitive with the
    already-extracted `text`, so the bytes are not re-parsed.

    Returns {projection_path, word_count, embed_pending}; projection_path is
    None when the derive failed (non-fatal — the raw is already retained).
    """
    projection_path = upload_projection_path(raw_path)
    try:
        from services.primitives.registry import execute_primitive
        from services.supabase import AuthenticatedClient
        # The derive is MECHANICAL make-AI-ready, not the member's authored
        # act — attributed `system:extract` (ADR-288 D2; same spirit as the
        # capture lane's `system:<slug>`). It writes the derived projection,
        # NOT the raw (the raw is the member's, written by the caller).
        auth = AuthenticatedClient(
            client=db_client, user_id=user_id, caller_identity="system:extract",
            workspace_id=workspace_id,
        )
        # embed=False: DEFER the paid embed off this synchronous request. The
        # projection is written + BM25-searchable the instant this returns; the
        # embedding (enrichment) is scheduled by the route as a background task
        # (ADR-325: embedding is enrichment; the mechanical floor is the promise).
        derive = await execute_primitive(auth, "ExtractTextFromBlob", {
            "raw_path": raw_path,
            "write_to": projection_path,
            "text": text,          # reuse the extraction already done (no re-parse)
            "source_filename": filename,
            "file_type": file_type,
            "embed": False,
        })
        if isinstance(derive, dict) and derive.get("success"):
            return {
                "projection_path": derive.get("projection_path"),
                "word_count": int(derive.get("word_count") or 0),
                "embed_pending": bool(derive.get("embed_pending")),
            }
        # Non-fatal: the raw is retained; the projection just isn't there
        # yet (retained-but-not-yet-consumable, DP34). Surface in the log.
        logger.warning(f"[DOCUMENTS] Projection derive failed for {raw_path}: {derive}")
    except Exception as e:
        logger.warning(f"[DOCUMENTS] Projection derive raised for {raw_path}: {e}")
    return {"projection_path": None, "word_count": 0, "embed_pending": False}


async def land_binary_revision(
    auth,
    *,
    path: str,
    data: bytes,
    authored_by: str,
    message: str,
    author_identity_uuid: Optional[str] = None,
    summary: Optional[str] = None,
    revision_kind: str = "authored",
    derived_from: Optional[list] = None,
    expected_parent_version_id: Optional[str] = None,
) -> dict:
    """Land `data` as a new revision of `path`, then re-derive its projection.

    The ONE tail for bytes yarnnn writes over a workspace path — a new office
    file (`office/create.py`), an in-place office edit (`office/edit.py`) and a
    revision restore (`routes/workspace.py`). Three copies of this sequence
    existed before ADR-671; the order matters and was easy to get wrong:

      1. the bytes ride the SERVICE client — the `workspace-cas` bucket refuses
         a member JWT (ADR-395 am.2 §11.12). Authorization already happened on
         the caller's own client; the service client is REACH, never attribution
         (that stays `authored_by` + `author_identity_uuid`);
      2. the write is conditional on the head the caller read, when given
         (ADR-406 D4) — a `StaleWriteError` propagates to the caller;
      3. a format the registry READS has its `.extracted.md` re-derived from
         the WRITTEN bytes, so an agent never reads the words of a version that
         is no longer the file. Best-effort: the bytes are what matter.

    Returns {revision_id, projection_path, word_count, embed_pending}.
    """
    from services.authored_substrate import write_revision
    from services.file_formats import format_of_path
    from services.supabase import get_service_client

    kwargs: dict = {}
    if expected_parent_version_id is not None:
        kwargs["expected_parent_version_id"] = expected_parent_version_id
    workspace_id = getattr(auth, "workspace_id", None)
    revision_id = write_revision(
        get_service_client(),
        user_id=auth.user_id,
        workspace_id=workspace_id,
        path=path,
        content_bytes=data,
        authored_by=authored_by,
        author_identity_uuid=author_identity_uuid,
        message=message,
        summary=summary,
        lifecycle="active",
        revision_kind=revision_kind,
        derived_from=derived_from,
        **kwargs,
    )
    out = {"revision_id": revision_id, "projection_path": None, "word_count": 0, "embed_pending": False}
    fmt = format_of_path(path)
    if fmt is None or fmt.projection != "text":
        return out
    ext = path.rsplit(".", 1)[-1].lower()
    try:
        text, _units = await extract_text(data, ext)
        out.update(await derive_upload_projection(
            auth.client, auth.user_id, path, text,
            filename=path.rsplit("/", 1)[-1], file_type=ext, workspace_id=workspace_id,
        ))
    except Exception as exc:  # noqa: BLE001 — the bytes landed; the index is best-effort
        logger.warning(f"[DOCUMENTS] projection re-derive failed for {path}: {exc}")
    return out


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
# A human upload lands its RAW blob at inbound/uploads/{slug}.{ext}, immutable +
# attributed, sibling to the machine inbound/{transport}/ sublanes.
# The DERIVED text projection (ADR-395 Piece B) lands co-located as a sibling
# `.extracted.md`, citing the raw via `derived_from`.

INBOUND_UPLOADS_PREFIX = "/workspace/inbound/uploads"


def resolve_upload_raw_path(
    slug: str, ext: str, destination: Optional[str] = None
) -> str:
    """Where a human upload's RAW blob lands (ADR-395 Piece A / DP32).

    With no `destination`: inbound/uploads/{slug}.{ext} — the intake lane
    itself. `ext` is the real file extension (pdf/docx/…), so the raw lane
    preserves the original format. The derived text projection is a sibling
    (see `upload_projection_path`).

    ── No `{principal}/` sublane (ADR-555 amendment, 2026-09-16) ─────────────
    The lane used to carry a `{principal}/` segment to keep many principals
    from colliding in one intake lane. It never had a second value: the segment
    was the literal `"operator"` fixed at the single call site, and every
    upload row in production sat under it. A sublane with one possible value
    disambiguates nothing — it is address-shaped ceremony that leaks ADR-373
    vocabulary into a path members read in Files. ADR-555 §1 already named that
    literal as the defect; D1 already ruled that an arrival is badged on the
    ledger (`revision_kind='observation'`), not by its address. So the segment
    goes and the badge stays. Attribution is UNAFFECTED — `authored_by` on the
    revision still records who uploaded; only the PATH loses the segment.

    Old rows keep their `inbound/uploads/operator/...` paths and keep
    resolving: they are ordinary `workspace_files` rows under the same lane
    root, and every rule that touches the lane (the ADR-422 D2 organizability
    carve, `is_upload_projection`, embed eligibility) keys on the
    `inbound/uploads/` PREFIX, which is unchanged. No migration moves them.

    ── With a destination (ADR-555 D3) ───────────────────────────────────────
    The folder the member dropped on wins, and the file keeps its real name
    there: `{destination}/{slug}.{ext}`.

    The lane is a default, not a law: an arrival is recorded by its
    `revision_kind='observation'` badge on the ledger, not by its address
    (D1, quoting ADR-448). The CALLER authorizes the destination — this
    resolver composes a path and decides nothing about permission.
    """
    ext = (ext or "bin").lstrip(".")
    dest = (destination or "").strip().strip("/")
    if dest.startswith("workspace/"):
        dest = dest[len("workspace/"):]
    if dest:
        return f"/workspace/{dest}/{slug}.{ext}"
    return f"{INBOUND_UPLOADS_PREFIX}/{slug}.{ext}"


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


def strip_projection_header(body: str) -> str:
    """The projection's text, without the plumbing its file carries.

    A projection opens with `derived_from: <raw>` + a `# <filename>` title —
    both written for the substrate (the reference edge, ADR-448) and both noise
    to a member who is looking at that very file, or an agent reading it. The
    words start after them. One home, two readers: the file route's preview
    (ADR-395 am.1 D12) and ReadFile on the raw (am.2 §11.12).
    """
    lines = body.splitlines()
    out: list[str] = []
    skipping = True
    for line in lines:
        if skipping:
            st = line.strip()
            if not st or st.startswith("derived_from:") or st.startswith("# "):
                continue
            skipping = False
        out.append(line)
    return "\n".join(out).strip()


#: The marker's opening token (ADR-395 am.1 D9). A marker and a projection are
#: both `.extracted.md` rows citing the same raw; this is what tells them apart
#: without re-running an extractor. Kept beside the writer that emits it.
_MARKER_TOKEN = "NOTE:"


def readable_state(
    path: str,
    *,
    content_type: Optional[str] = None,
    projection_content: Optional[str] = None,
    has_projection: bool = False,
) -> str:
    """Can an agent read this file's contents? — ADR-395 am.1 D11.

    Returns one of:
      `read`     — a text projection exists and carries the file's words.
      `unread`   — the file is retained in full, and yarnnn cannot read it.
      `native`   — the file IS its own content (prose, an image, a video):
                   nothing is owed and nothing is missing.

    ── Why the SERVER answers this ───────────────────────────────────────────

    The viewer showed the same "can't preview here" for a `.sketch` (genuinely
    unreadable) and an `.xlsx` (read perfectly well since am.1 D10). Both are
    binaries with no inline preview, so the VIEWER's question — "can I draw
    this?" — cannot separate them. The member's question is different: *does my
    agent know what is in this file?* That is the derive-registry's question,
    and the registry lives here.

    ⭐ Answering it in the client would mean re-deriving `registry_strategy` in
    TypeScript — a second home for the rule, and the exact shape that let the
    upload door and the derive-registry disagree in the first place (am.1 §8.1).
    So this ships like `access` (ADR-643 D3): the server decides, the client
    reads, and an absent value means UNKNOWN rather than a guess.

    `projection_content` distinguishes a real projection from a D9 MARKER. A
    caller that has not fetched the sibling passes `has_projection` alone and
    gets the conservative answer for a binary: `unread` unless the words are in
    hand. Saying "your agent can read this" when it cannot is the failure that
    matters; the reverse is merely modest.
    """
    from services.file_formats import registry_strategy
    from services.content_types import conforms_to

    mime = content_type or ""
    # Media and prose are their own content — an image IS what a vision model
    # reads, and a .md IS its own text. Neither is owed a projection, so neither
    # can be missing one.
    if mime and (
        conforms_to(mime, "public.image")
        or conforms_to(mime, "public.movie")
        or conforms_to(mime, "public.audio")
        or conforms_to(mime, "public.text")
    ):
        return "native"

    ext = path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
    if registry_strategy(ext) == "passthrough":
        return "native"

    if projection_content is not None:
        body = projection_content.strip()
        # A marker states the gap and carries no extracted words. A projection
        # carries the file's own text. Both open with `derived_from:` + a title.
        return "unread" if _MARKER_TOKEN in body else "read"

    return "read" if has_projection else "unread"


def is_upload_projection(
    path: str,
    content: Optional[str] = None,
    siblings: Optional[Iterable[str]] = None,
) -> bool:
    """True iff `path` is an upload's DERIVED text projection (ADR-395 Piece B).

    The projection is plumbing — a searchable text derivation of a raw upload,
    consumed by recall/QueryKnowledge, NOT a user file. The Files surface hides
    it so the operator sees ONE file (their PDF), not a confusing raw+extracted
    pair.

    ── The anchor moved from the LANE to the EDGE (ADR-554 D2, 2026-08-12) ────
    This used to require the `inbound/uploads/` prefix AND the `.extracted.md`
    suffix. That was deliberate — anchoring on the suffix ALONE would hide a
    member's own `notes.extracted.md` anywhere in the workspace, which the rule
    must never do.

    But the lane anchor broke the moment the raw MOVED. Uploads are organizable
    (ADR-422 D2 carves `inbound/uploads/` back out of intake immutability), and
    the blessed workflow is upload-then-move; once the projection followed its
    raw into a meaning folder (D1), a lane-anchored rule stopped hiding it and
    the member saw the raw+extracted pair the rule exists to prevent.

    The edge is the honest anchor: a projection is plumbing because it is
    DERIVED FROM a sibling raw, not because of where it happens to sit. The
    narrowness the lane gave us is preserved and improved — a member's own
    `notes.extracted.md` is unhidden because it cites nothing, rather than
    because of its address.

    Outside the lane the edge is read from whichever evidence the caller HAS,
    and the two forms are equivalent for a real projection:

    * `siblings` — the paths the caller already listed. A projection's raw is
      its co-located twin (`x.pdf` ↔ `x.extracted.md`), so a caller that is
      enumerating a folder can answer without fetching a single body. This is
      the cheap form, and the one the tree + recents use: their queries hold
      the sibling rows already.
    * `content` — the file's own `derived_from:` frontmatter, for a caller
      that has the body but not the neighbourhood (the uploads listing).

    Both default to None so every existing caller keeps working; with neither,
    the lane rule still answers (the pre-move case, unchanged).
    """
    norm = path.lstrip("/")
    if norm.startswith("workspace/"):
        norm = norm[len("workspace/"):]
    if not norm.endswith(".extracted.md"):
        return False
    if norm.startswith("inbound/uploads/"):
        return True  # the pre-move case — the lane still answers on its own

    stem = f"/workspace/{norm[: -len('.extracted.md')]}"
    # A sibling raw in the caller's own listing: `x.<ext>` beside `x.extracted.md`.
    # `.md` is excluded so a member's `notes.md` never turns `notes.extracted.md`
    # into plumbing — a projection's raw is a non-text upload by construction
    # (a pure-text upload produces no projection at all).
    if siblings:
        for other in siblings:
            o = other if other.startswith("/") else f"/workspace/{other.lstrip('/')}"
            if o == f"{stem}.extracted.md" or "." not in o.rsplit("/", 1)[-1]:
                continue
            if o.rsplit(".", 1)[0] == stem and not o.endswith(".md"):
                return True
    if content is not None:
        # Requiring the SIBLING relationship — not merely any citation — is what
        # keeps a member's own derived prose visible.
        from services.authored_substrate import extract_derived_from_list

        return any(
            cite.rsplit(".", 1)[0] == stem
            for cite in extract_derived_from_list(content)
            if cite
        )
    return False
