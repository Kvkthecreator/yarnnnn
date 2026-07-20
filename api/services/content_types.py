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

# ---------------------------------------------------------------------------
# Magic-byte signatures (checked against the blob's leading bytes; first match
# wins, ordered specific-before-general). The path extension is the tiebreaker
# for container formats (zip → docx/xlsx/pptx) and the fallback when no bytes
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

# Zip-based container formats disambiguated by extension.
_ZIP_EXT_MIMES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

# Extension fallback (no bytes available, or bytes were inconclusive).
_EXT_MIMES = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml",
    "pdf": "application/pdf",
    "mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm",
    "mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4", "ogg": "audio/ogg",
    "md": "text/markdown", "txt": "text/plain", "csv": "text/csv",
    "html": "text/html", "json": "application/json",
    "yaml": "application/yaml", "yml": "application/yaml",
    "zip": "application/zip",
    **_ZIP_EXT_MIMES,
}

_DEFAULT_TEXT = "text/markdown"       # the substrate's historic text default
_DEFAULT_BINARY = "application/octet-stream"


def _ext(path: Optional[str]) -> str:
    name = (path or "").rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


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
            return _ZIP_EXT_MIMES.get(_ext(path), "application/zip")
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
    # concrete MIME → immediate base
    "image/png": "public.image", "image/jpeg": "public.image",
    "image/gif": "public.image", "image/webp": "public.image",
    "image/svg+xml": "public.image",
    "video/mp4": "public.movie", "video/quicktime": "public.movie",
    "video/webm": "public.movie", "video/x-msvideo": "public.movie",
    "audio/mpeg": "public.audio", "audio/wav": "public.audio",
    "audio/mp4": "public.audio", "audio/ogg": "public.audio",
    "application/pdf": "public.data",
    "application/zip": "public.data",
    "application/json": "public.text",
    "application/yaml": "public.text",
    # every base conforms to public.data (the root)
    "public.image": "public.data", "public.movie": "public.data",
    "public.audio": "public.data", "public.text": "public.data",
    **{m: "public.data" for m in _ZIP_EXT_MIMES.values()},
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
