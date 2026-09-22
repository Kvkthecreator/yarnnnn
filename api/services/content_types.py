"""
Content Types — ADR-427 D5 (type is DERIVED, never stored)

The single source of truth for "what type is this file?" — a pure function of
the blob's leading bytes + the path's extension, both already Category-1 state.
No stored `content_type` string is ever trusted for a binary revision; the
column survives only as a denormalized cache of THIS derivation.

The conformance DAG (the UTI model, macOS primitive #2): yarnnn declares the
BASE media types it owns (`public.image`, `public.movie`, `public.audio`,
`public.data`, `public.text`); a concrete MIME conforms upward. The intake gate
(ADR-427 Phase 3) asks "does the derived type conform to a declared base?" —
a conformance question, not a stored-string allowlist. yarnnn owns base media
types; it never owns an app's project format.

Canonical reference: docs/adr/ADR-427-binary-native-substrate-and-the-storage-seam.md §6b
"""

from __future__ import annotations

from typing import Optional

from services.file_formats import FORMATS as _FORMATS
from services.file_formats import ext_of as _ext

# ---------------------------------------------------------------------------
# Magic-byte signatures (checked against the blob's leading bytes; first match
# wins, ordered specific-before-general). The path extension is the tiebreaker
# for container formats (zip → docx/xlsx/pptx/hwpx) and the fallback when no bytes
# are available.
# ---------------------------------------------------------------------------

_MAGIC: list[tuple[bytes, int, str]] = [
    # (signature, offset, mime)
    (b"\x89PNG\r\n\x1a\n", 0, "image/png"),
    (b"\xff\xd8\xff", 0, "image/jpeg"),
    (b"GIF87a", 0, "image/gif"),
    (b"GIF89a", 0, "image/gif"),
    (b"%PDF-", 0, "application/pdf"),
    (b"ftyp", 4, "video/mp4"),          # mp4/mov family (iso base media)
    (b"\x1a\x45\xdf\xa3", 0, "video/webm"),  # EBML (webm/mkv)
    (b"ID3", 0, "audio/mpeg"),
    (b"\xff\xfb", 0, "audio/mpeg"),
    (b"OggS", 0, "audio/ogg"),
]

# RIFF containers share a 4-byte prefix; the format tag is at offset 8.
_RIFF_FORMATS = {b"WEBP": "image/webp", b"WAVE": "audio/wav", b"AVI ": "video/x-msvideo"}

# ADR-395 am.2 D14 — the extension tables are DERIVED from the format registry
# (`services/file_formats.py`), never restated here. `_ZIP_EXT_MIMES` and a
# hand-kept `_EXT_MIMES` literal were deleted: they were the MIME column of a
# table that four other modules also kept a column of.
# Zip-based container formats disambiguated by extension (docx/xlsx/pptx/hwpx).
_ZIP_CONTAINER_MIMES = {
    ext: f.mime for f in _FORMATS if f.zip_container for ext in f.exts
}

# Extension fallback (no bytes available, or bytes were inconclusive).
_EXT_MIMES = {ext: f.mime for f in _FORMATS for ext in f.exts}

_DEFAULT_TEXT = "text/markdown"       # the substrate's historic text default
_DEFAULT_BINARY = "application/octet-stream"


def derive_content_type(path: Optional[str], head: Optional[bytes] = None) -> str:
    """Derive a file's MIME type from magic bytes + path extension (ADR-427 D5).

    Pure function of Category-1 state — never reads a stored type. `head` is
    the blob's leading bytes (>= 16 is plenty); None means "derive from the
    extension alone" (the text-write case, where bytes are utf-8 by contract).
    """
    if head:
        for sig, off, mime in _MAGIC:
            if head[off : off + len(sig)] == sig:
                # mp4-family refinement: quicktime brands
                if mime == "video/mp4" and head[8:12] in (b"qt  ",):
                    return "video/quicktime"
                return mime
        if head[:4] == b"RIFF" and len(head) >= 12:
            riff = _RIFF_FORMATS.get(head[8:12])
            if riff:
                return riff
        if head[:4] == b"PK\x03\x04":
            return _ZIP_CONTAINER_MIMES.get(_ext(path), "application/zip")
    ext = _ext(path)
    if ext in _EXT_MIMES:
        return _EXT_MIMES[ext]
    if head is not None:
        # Bytes present but no signature matched: text if utf-8-decodable.
        try:
            head.decode("utf-8")
            return _DEFAULT_TEXT
        except UnicodeDecodeError:
            return _DEFAULT_BINARY
    return _DEFAULT_TEXT


# ---------------------------------------------------------------------------
# The conformance DAG (D5) — MIME → declared base types, upward-walkable.
# yarnnn declares the bases; concrete types conform. Kept deliberately small:
# this is the UTI *shape*, not an exhaustive registry.
# ---------------------------------------------------------------------------

_BASES = {
    "public.image", "public.movie", "public.audio", "public.text", "public.data",
}

_CONFORMS: dict[str, str] = {
    # concrete MIME → immediate base, one row per declared format (am.2 D14).
    # `video/x-msvideo` arrives by RIFF sniff; `.avi` declares it too.
    **{f.mime: f.base for f in _FORMATS},
    # every base conforms to public.data (the root)
    "public.image": "public.data", "public.movie": "public.data",
    "public.audio": "public.data", "public.text": "public.data",
}


def conforms_to(mime: str, base: str) -> bool:
    """True if `mime` conforms (transitively) to `base` in the declared DAG.

    Any `text/*` conforms to public.text. Everything conforms to public.data.
    """
    if base == "public.data":
        return True
    node: Optional[str] = mime
    if mime.startswith("text/"):
        node = "public.text"
    seen = set()
    while node and node not in seen:
        if node == base:
            return True
        seen.add(node)
        node = _CONFORMS.get(node)
    return False


def is_text_type(mime: str) -> bool:
    """The read-side text-only contract check (ADR-427 §8): may this type's
    content be read as the inline TEXT denorm? Binary types read '' there."""
    return conforms_to(mime, "public.text")


__all__ = ["derive_content_type", "conforms_to", "is_text_type"]
