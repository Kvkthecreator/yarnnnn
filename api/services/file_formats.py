"""
The format registry — ADR-395 amendment 2, D14 (the format harness).

ONE declarative row per file format, owned by the kernel. Every question the
system asks about a format is answered by reading a row here:

  * what MIME a path derives to, and which UTI base it conforms to
    (`services/content_types.py` reads `mime` / `base` / `zip_container`);
  * whether a model can read it and how (`projection` + `extractor` —
    the ADR-395 D2 derive-registry, `registry_strategy`);
  * which view kind the client draws it with (`view`);
  * what it can be written AS (`export_as` — ADR-395 am.2 D16, read by the
    outbound writer).

── Why one table, and why here ───────────────────────────────────────────────

Before am.2 the same extension lists lived in five places that had each
drifted: `_EXT_MIMES`/`_ZIP_EXT_MIMES`/`_CONFORMS` (content_types),
`_TEXT_FORMATS`/`_PASSTHROUGH_FORMATS`/`_DEFERRED_FORMATS` (the derive
primitive), the `extract_text` if-chain (documents), `_MIME_EXTS` (the upload
route) and `_BINARY_TEXT_FAMILY` (machine_projection). The registry listed
`doc` as readable while python-docx cannot open an OLE `.doc` at all — a row
of one table claiming what another table's parser could not do. That is the
§8.1 split (the upload door and the registry disagreeing) at a smaller scale.

This is its own module rather than a block inside `content_types.py` because
a row carries its EXTRACTOR (a callable in `services/documents.py`), and the
byte-sniffing module must stay a dependency-free pure function. The dependency
runs one way: content_types → file_formats → documents (whose module scope
imports nothing from `services`).

── What is deliberately NOT here ─────────────────────────────────────────────

  * The React component that draws a view kind. That binding is the client's
    (`web/lib/file-types/apps.tsx`); the server names the KIND, never the
    component (ADR-436).
  * Icons and "Kind" labels (`FileIcon.tsx`, `NodeDetailsPanel.tsx`). They are
    presentation for tree rows that are never fetched, and they cover formats
    this registry does not declare (`.xls`, `.ppt`, `.doc`); nothing about a
    format's capability rides on them.
  * Round-trip editing, and any format needing execution to read (am.2 D19).

Canonical reference:
docs/adr/ADR-395-model-consumable-projection-and-upload-intake-conformance.md §11
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Optional, Tuple

from services.documents import (
    extract_text_from_docx,
    extract_text_from_hwp,
    extract_text_from_hwpx,
    extract_text_from_pdf,
    extract_text_from_pptx,
    extract_text_from_xlsx,
)

Extractor = Callable[[bytes], Awaitable[Tuple[str, int]]]


@dataclass(frozen=True)
class ExportTarget:
    """One format a file can be written AS (ADR-395 am.2 D16).

    `to` is the target extension. `when_app` narrows it to an HTML artifact
    whose declared type (`data-template`, ADR-459) is owned by that app — a
    Slides deck can become a `.pptx`; a blog post cannot, although both are
    `.html`. None means every file of the format qualifies.
    """

    to: str
    when_app: Optional[str] = None


@dataclass(frozen=True)
class FileFormat:
    """One format, declared once. The first of `exts` is the canonical one.

    projection  'text' | 'passthrough' | 'deferred' — the derive-registry
                verdict (ADR-395 D2). `text`: a projection is extracted;
                `passthrough`: already model-consumable (a vision image);
                `deferred`: retained, legibly marked, not yet read.
    extractor   the byte parser for a BINARY text-family format. None for a
                format whose bytes are utf-8 text (read as-is).
    view        the view kind the client draws (ADR-395 am.2 D15). The client
                binds kind → component; the server never names a component.
    """

    exts: Tuple[str, ...]
    mime: str
    base: str
    projection: str
    view: str
    extractor: Optional[Extractor] = None
    zip_container: bool = False
    export_as: Tuple[ExportTarget, ...] = field(default_factory=tuple)


_IMG, _MOV, _AUD, _TXT, _DAT = (
    "public.image", "public.movie", "public.audio", "public.text", "public.data",
)

#: THE table. Order is irrelevant; an extension appears in exactly one row
#: (asserted at import, below).
FORMATS: Tuple[FileFormat, ...] = (
    # ── prose and structured text — the bytes ARE utf-8 text ─────────────────
    FileFormat(("md", "markdown"), "text/markdown", _TXT, "text", "markdown",
               export_as=(ExportTarget("docx"),)),
    FileFormat(("txt",), "text/plain", _TXT, "text", "text"),
    FileFormat(("csv",), "text/csv", _TXT, "text", "csv",
               export_as=(ExportTarget("xlsx"),)),
    FileFormat(("tsv",), "text/tab-separated-values", _TXT, "deferred", "csv"),
    FileFormat(("html", "htm"), "text/html", _TXT, "text", "html",
               export_as=(ExportTarget("docx"), ExportTarget("pptx", when_app="slides"))),
    # json/yaml read `deferred` — unchanged by am.2, recorded as a finding (§11.7).
    FileFormat(("json",), "application/json", _TXT, "deferred", "text"),
    FileFormat(("yaml", "yml"), "application/yaml", _TXT, "deferred", "text"),
    # ── binary documents with an in-process text extractor (am.1 D10, am.2 D18)
    FileFormat(("pdf",), "application/pdf", _DAT, "text", "pdf",
               extractor=extract_text_from_pdf),
    FileFormat(("docx",),
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
               _DAT, "text", "wordprocessing",
               extractor=extract_text_from_docx, zip_container=True),
    FileFormat(("xlsx",),
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
               _DAT, "text", "spreadsheet",
               extractor=extract_text_from_xlsx, zip_container=True),
    FileFormat(("pptx",),
               "application/vnd.openxmlformats-officedocument.presentationml.presentation",
               _DAT, "text", "presentation",
               extractor=extract_text_from_pptx, zip_container=True),
    FileFormat(("hwpx",), "application/hwp+zip", _DAT, "text", "download",
               extractor=extract_text_from_hwpx, zip_container=True),
    FileFormat(("hwp",), "application/x-hwp", _DAT, "text", "download",
               extractor=extract_text_from_hwp),
    # ── images: a vision model reads the first five as they are ──────────────
    FileFormat(("png",), "image/png", _IMG, "passthrough", "image"),
    FileFormat(("jpg", "jpeg"), "image/jpeg", _IMG, "passthrough", "image"),
    FileFormat(("gif",), "image/gif", _IMG, "passthrough", "image"),
    FileFormat(("webp",), "image/webp", _IMG, "passthrough", "image"),
    FileFormat(("svg",), "image/svg+xml", _IMG, "deferred", "image"),
    FileFormat(("avif",), "image/avif", _IMG, "deferred", "image"),
    FileFormat(("bmp",), "image/bmp", _IMG, "deferred", "image"),
    FileFormat(("ico",), "image/x-icon", _IMG, "deferred", "image"),
    # ── time-based media: retained, played, not read (DP34) ──────────────────
    FileFormat(("mp4", "m4v"), "video/mp4", _MOV, "deferred", "video"),
    FileFormat(("mov",), "video/quicktime", _MOV, "deferred", "video"),
    FileFormat(("webm",), "video/webm", _MOV, "deferred", "video"),
    FileFormat(("mkv",), "video/x-matroska", _MOV, "deferred", "video"),
    FileFormat(("avi",), "video/x-msvideo", _MOV, "deferred", "video"),
    FileFormat(("mp3",), "audio/mpeg", _AUD, "deferred", "audio"),
    FileFormat(("wav",), "audio/wav", _AUD, "deferred", "audio"),
    FileFormat(("m4a",), "audio/mp4", _AUD, "deferred", "audio"),
    FileFormat(("ogg",), "audio/ogg", _AUD, "deferred", "audio"),
    FileFormat(("flac",), "audio/flac", _AUD, "deferred", "audio"),
    FileFormat(("aac",), "audio/aac", _AUD, "deferred", "audio"),
    # ── archives ─────────────────────────────────────────────────────────────
    FileFormat(("zip",), "application/zip", _DAT, "deferred", "download"),
)


def _index() -> Dict[str, FileFormat]:
    out: Dict[str, FileFormat] = {}
    for fmt in FORMATS:
        for ext in fmt.exts:
            if ext in out:  # pragma: no cover — a table error, caught at import
                raise ValueError(f"format registry declares .{ext} twice")
            out[ext] = fmt
    return out


_BY_EXT: Dict[str, FileFormat] = _index()


def ext_of(path: Optional[str]) -> str:
    """A path's lowercased extension ('' when the leaf has none)."""
    leaf = (path or "").rsplit("/", 1)[-1]
    return leaf.rsplit(".", 1)[-1].lower() if "." in leaf else ""


def format_for(file_type: Optional[str]) -> Optional[FileFormat]:
    """The row for an extension (`xlsx` or `.xlsx`), or None if undeclared."""
    return _BY_EXT.get((file_type or "").lower().lstrip("."))


def format_of_path(path: Optional[str]) -> Optional[FileFormat]:
    """The row for a path's extension, or None if undeclared."""
    return _BY_EXT.get(ext_of(path))


def registry_strategy(file_type: Optional[str]) -> str:
    """The derive-registry verdict for a format (ADR-395 D2 / DP34).

    Returns 'text' | 'passthrough' | 'deferred'. A format the registry has
    never heard of is 'deferred' — retained-but-not-yet-consumable, legibly
    marked, never silently dropped or fabricated.
    """
    fmt = format_for(file_type)
    return fmt.projection if fmt else "deferred"


def is_binary_text_family(file_type: Optional[str]) -> bool:
    """A readable format whose RAW bytes are not text (pdf, the office family).

    Its projection comes from a byte parser at upload time; its raw bytes must
    never be emitted as though they were text (DP34, ADR-530 §machine
    projection). Derived from the row — a text projection AND a parser — so it
    cannot omit a member the way the hand-kept set it replaces did.
    """
    fmt = format_for(file_type)
    return bool(fmt and fmt.projection == "text" and fmt.extractor is not None)


def ext_for_mime(mime: Optional[str]) -> Optional[str]:
    """The canonical extension for a MIME — used only when a name has none."""
    for fmt in FORMATS:
        if fmt.mime == mime:
            return fmt.exts[0]
    return None


def _owned_by_app(content: Optional[str], app: str) -> bool:
    """Is this HTML artifact's declared type owned by `app`? (ADR-473 D2)

    Conservative: any failure answers False, so a conditional target is
    withheld rather than offered for a file the writer cannot convert.
    """
    try:
        import services.apps  # noqa: F401  (registration side-effect)
        from services.authoring import canonical_layout_slug, extract_template, kinds_for_app

        kind = extract_template(content or "")
        return bool(kind) and canonical_layout_slug(kind) in kinds_for_app(app)
    except Exception:  # noqa: BLE001
        return False


def export_targets(path: str, content: Optional[str] = None) -> list:
    """The formats THIS file can be written as (ADR-395 am.2 D16).

    Per-file, not per-format: a target narrowed by `when_app` needs the file's
    own declared type, which lives in its bytes. An undeclared format has no
    targets — the answer is known, and it is empty.
    """
    fmt = format_of_path(path)
    if fmt is None:
        return []
    return [
        t.to for t in fmt.export_as
        if t.when_app is None or _owned_by_app(content, t.when_app)
    ]


def served_capabilities(path: str, content: Optional[str] = None) -> dict:
    """The per-file format fields `GET /workspace/file` serves (am.2 D15/D16).

    `view`       — the view kind, or None when the registry does not declare
                   the format (the client then falls back to its extension
                   cache, which a gate holds in parity with this table).
    `export_as`  — the formats this file can be written as; [] when none.
    """
    fmt = format_of_path(path)
    return {
        "view": fmt.view if fmt else None,
        "export_as": export_targets(path, content),
    }


__all__ = [
    "ExportTarget",
    "FileFormat",
    "FORMATS",
    "ext_of",
    "ext_for_mime",
    "export_targets",
    "format_for",
    "format_of_path",
    "is_binary_text_family",
    "registry_strategy",
    "served_capabilities",
]
