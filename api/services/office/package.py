"""The OOXML package — read parts, change some, write the rest back as they were.

ADR-671 D3. A `.docx`/`.xlsx`/`.pptx` is a zip of XML parts. An edit touches one
or two of them (`word/document.xml`, one sheet, one slide); everything else — the
styles, the theme, the images, the charts, the macros, parts no library models —
must come back with identical content. That is the whole reason this layer exists
instead of a library object model: python-docx and python-pptx keep unknown parts,
but openpyxl drops charts and pivot caches from a workbook it loads, and a member's
budget is exactly the file that carries them.

Written back member by member in the original order, with each member's original
`ZipInfo` (name, timestamp, compression, attributes). An unchanged member's
content is byte-identical; its compressed stream may differ, which no reader sees.

XML is parsed with entity resolution and network access OFF — an office file is
untrusted input (the same parser settings as the HWPX reader, ADR-395 am.2 D18).
"""

from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

from lxml import etree


class OfficeEditError(ValueError):
    """The edit was refused — the message is legible to the member and the agent."""


@dataclass(frozen=True)
class OfficeKind:
    """Everything the system knows about one office format, declared once by the
    module that reads and edits it, and carried on the format registry's row
    (ADR-671). Nothing outside the registry names a format.

    name            what a member calls the format ("Word document")
    address_hint    how its projection spells an address, for the words that
                    teach an agent the edit loop
    tracks_changes  a model-authored edit lands as the format's own tracked
                    change, signed by the principal (D4)
    project         bytes → (addressed text, unit count)
    apply           (bytes, edits, *, author, when) → (bytes, one line per edit)
    """

    name: str
    address_hint: str
    tracks_changes: bool
    project: Callable[[bytes], Tuple[str, int]]
    apply: Callable[..., Tuple[bytes, List[str]]]

    async def extract(self, data: bytes) -> Tuple[str, int]:
        """The registry's async extractor contract. A file the projector cannot
        read yields ("", 0), so the upload takes the D9 marker (ADR-395 am.1)
        instead of failing — the bytes are retained."""
        try:
            return self.project(data)
        except Exception as exc:  # noqa: BLE001 — an unreadable file is a marker, not a 500
            logging.getLogger(__name__).error("%s projection failed: %s", self.name, exc)
            return "", 0


#: Ceiling on the bytes a package may inflate to while we read it. The same
#: ceiling the HWPX/HWP readers hold (`documents._MAX_INFLATED_BYTES`).
def _max_inflated() -> int:
    from services.documents import _MAX_INFLATED_BYTES
    return _MAX_INFLATED_BYTES


_PARSER = etree.XMLParser(
    resolve_entities=False, no_network=True, remove_blank_text=False, huge_tree=False,
)

XML_NS = "http://www.w3.org/XML/1998/namespace"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def local(el) -> str:
    """An element's tag without its namespace ('' for comments / PIs)."""
    tag = el.tag
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def parse_xml(data: bytes):
    """Parse one untrusted XML part (entities and network off)."""
    return etree.fromstring(data, _PARSER)


class Package:
    """An opened OOXML package. Parts are read lazily and written back whole."""

    def __init__(self, data: bytes):
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise OfficeEditError("This file is not a readable Office document.") from exc
        infos = zf.infolist()
        if sum(i.file_size for i in infos) > _max_inflated():
            raise OfficeEditError("This file expands past the size yarnnn reads.")
        self._infos: List[zipfile.ZipInfo] = infos
        self._raw: Dict[str, bytes] = {i.filename: zf.read(i.filename) for i in infos}
        self._xml: Dict[str, "etree._Element"] = {}
        self._decl: Dict[str, Tuple[bool, Optional[bool]]] = {}
        self._dirty: set = set()
        self._removed: set = set()

    # ── reading ──────────────────────────────────────────────────────────────

    def names(self) -> List[str]:
        return [i.filename for i in self._infos if i.filename not in self._removed]

    def has(self, name: str) -> bool:
        return name in self._raw and name not in self._removed

    def read(self, name: str) -> bytes:
        return self._raw[name]

    def xml(self, name: str):
        """The parsed root of an XML part — the SAME object on every call, so
        a caller edits it in place and marks it with `touch`."""
        if name not in self._xml:
            if not self.has(name):
                raise OfficeEditError(f"The file has no part {name}.")
            raw = self._raw[name]
            self._xml[name] = parse_xml(raw)
            head = raw[:200].lstrip()
            standalone = None
            if head.startswith(b"<?xml"):
                decl = head.split(b"?>", 1)[0]
                if b"standalone" in decl:
                    standalone = b'"yes"' in decl or b"'yes'" in decl
            self._decl[name] = (head.startswith(b"<?xml"), standalone)
        return self._xml[name]

    def _rel_rows(self, part: str) -> List[Tuple[str, str, str]]:
        """(rId, type, absolute target) for one part's internal relationships.
        `part=''` reads the package's own relationships (`_rels/.rels`)."""
        folder, leaf = part.rsplit("/", 1) if "/" in part else ("", part)
        rels_name = f"{folder}/_rels/{leaf}.rels" if folder else f"_rels/{leaf}.rels"
        if not self.has(rels_name):
            return []
        return [
            (rel.get("Id"), rel.get("Type") or "", resolve_target(folder, rel.get("Target") or ""))
            for rel in self.xml(rels_name)
            if rel.get("TargetMode") != "External"
        ]

    def rels(self, part: str) -> Dict[str, str]:
        """rId → absolute part name, for one part's relationships."""
        return {rid: target for rid, _type, target in self._rel_rows(part)}

    def targets_of_type(self, part: str, type_suffix: str) -> List[str]:
        """The parts `part` relates to with a relationship type ending in
        `/{type_suffix}` (e.g. 'styles', 'header', 'notesSlide')."""
        return [t for _rid, typ, t in self._rel_rows(part) if typ.endswith("/" + type_suffix)]

    def main_part(self) -> str:
        """The package's main document part (document.xml / workbook.xml /
        presentation.xml) — named by the package's own relationship, never assumed."""
        found = self.targets_of_type("", "officeDocument")
        if not found:
            raise OfficeEditError("This file has no main document part.")
        return found[0]

    # ── writing ──────────────────────────────────────────────────────────────

    def touch(self, name: str) -> None:
        """Mark a parsed part changed; `save` serialises it."""
        self._dirty.add(name)

    def remove(self, name: str) -> None:
        self._removed.add(name)

    def save(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as out:
            for info in self._infos:
                name = info.filename
                if name in self._removed:
                    continue
                if name in self._dirty:
                    has_decl, standalone = self._decl.get(name, (True, None))
                    data = etree.tostring(
                        self._xml[name], xml_declaration=has_decl, encoding="UTF-8",
                        standalone=standalone,
                    )
                else:
                    data = self._raw[name]
                out.writestr(info, data)
        return buf.getvalue()


def resolve_target(folder: str, target: str) -> str:
    """A relationship target, resolved against its source part's folder."""
    if target.startswith("/"):
        return target.lstrip("/")
    parts = [p for p in folder.split("/") if p] if folder else []
    for seg in target.split("/"):
        if seg == "..":
            if parts:
                parts.pop()
        elif seg and seg != ".":
            parts.append(seg)
    return "/".join(parts)


def set_preserved_text(t_el, text: str) -> None:
    """Set a text element's value, keeping leading/trailing spaces meaningful."""
    t_el.text = text
    if text != text.strip() or "  " in text:
        t_el.set(f"{{{XML_NS}}}space", "preserve")


# ── one run-aware replacement, shared by Word and PowerPoint ────────────────


def find_unique(haystack: str, needle: str, where: str) -> Tuple[int, int]:
    """The span of `needle` in `haystack`, which must occur exactly once."""
    if not needle:
        raise OfficeEditError("old_string is empty — omit it to replace the whole element.")
    count = haystack.count(needle)
    if count == 0:
        raise OfficeEditError(
            f"{where} does not contain {needle!r}. Its text is {haystack!r} — "
            "re-read the file; the address may be stale."
        )
    if count > 1:
        raise OfficeEditError(
            f"{needle!r} occurs {count} times in {where}. Include more of the surrounding "
            "text in old_string so it names one place."
        )
    start = haystack.index(needle)
    return start, start + len(needle)


def replace_in_segments(
    segments: Iterable[Tuple[object, str]], start: int, end: int, new: str,
    set_text=set_preserved_text,
) -> None:
    """Replace the character span [start, end) of the text the `segments` spell.

    `segments` is the ordered list of (text element, its text) that make up one
    paragraph. The replacement lands in the FIRST element the span touches, so
    the new words take that run's formatting; the rest of the span is removed
    from the elements it covers. Elements are never split or reordered, so every
    run keeps its own properties. `set_text` writes an element's text (Word
    marks significant spaces with `xml:space`; DrawingML does not).
    """
    offset = 0
    placed = False
    for el, text in segments:
        seg_start, seg_end = offset, offset + len(text)
        offset = seg_end
        if seg_end <= start or seg_start >= end:
            continue
        if el is None:
            # A tab or a line break: structure, not text a run can absorb.
            raise OfficeEditError(
                "The text to replace spans a tab or a line break. Edit the parts on "
                "either side of it, or replace the whole element (omit old_string)."
            )
        lo = max(start, seg_start) - seg_start
        hi = min(end, seg_end) - seg_start
        if not placed:
            set_text(el, text[:lo] + new + text[hi:])
            placed = True
        else:
            set_text(el, text[:lo] + text[hi:])
    if not placed:
        raise OfficeEditError("The text to replace was not found in the element's runs.")


__all__ = [
    "MC_NS", "OFFICE_REL_NS", "REL_NS", "CT_NS", "XML_NS",
    "OfficeEditError", "OfficeKind", "Package", "find_unique", "local", "parse_xml",
    "replace_in_segments", "resolve_target", "set_preserved_text",
]
