"""PowerPoint decks — the addressed projection and the in-place edit (ADR-671).

── The address ───────────────────────────────────────────────────────────────

`sN/id` — the Nth slide in the deck's own order (`p:sldIdLst`), and the shape's
own id on that slide (`p:cNvPr/@id`, unique per slide and stable across edits).
A table cell is `sN/id/rRcC` (1-based); the speaker notes are `sN/notes`.

The projection keeps the spelling the client's slide view already reads
(`## Slide {n}` sections, a `Speaker notes:` label), with each block led by its
address. The client strips the addresses before drawing (ADR-671 §7 holds the two
halves together by executing both).

── The edit ──────────────────────────────────────────────────────────────────

Text inside existing runs changes, so every run keeps its font, size and colour;
a shape keeps its position, its layout and its placeholder. Phase 1 edits TEXT —
adding, removing and reordering slides is Phase 2 (the Slides app's office mode).
PowerPoint has no tracked changes: attribution is the revision's.
"""

from __future__ import annotations

import copy
import re
from typing import List, Optional, Tuple

from services.office.package import (
    MC_NS, OfficeEditError, OfficeKind, Package, find_unique, local, replace_in_segments,
)

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def p_(tag: str) -> str:
    return f"{{{P}}}{tag}"


def a_(tag: str) -> str:
    return f"{{{A}}}{tag}"


_LABELS = {"title": "Title", "ctrTitle": "Title", "subTitle": "Subtitle"}


def _slides(pkg: Package) -> List[str]:
    main = pkg.main_part()
    rels = pkg.rels(main)
    lst = pkg.xml(main).find(p_("sldIdLst"))
    return [rels[s.get(f"{{{R_NS}}}id")] for s in (lst if lst is not None else [])
            if s.get(f"{{{R_NS}}}id") in rels]


def _plain(el, text: str) -> None:
    el.text = text


def _para_segments(para) -> List[Tuple[object, str]]:
    out: List[Tuple[object, str]] = []
    for child in para:
        if child.tag in (a_("r"), a_("fld")):
            t = child.find(a_("t"))
            if t is not None:
                out.append((t, t.text or ""))
        elif child.tag == a_("br"):
            out.append((None, "\n"))
    return out


def _paras(tx_body) -> list:
    return list(tx_body.iterchildren(a_("p")))


def _body_text(tx_body) -> str:
    return "\n".join("".join(t for _el, t in _para_segments(p)) for p in _paras(tx_body)).strip()


def _shape_id(shape) -> Optional[str]:
    for child in shape:
        if local(child).startswith("nv"):
            c = child.find(p_("cNvPr"))
            if c is not None:
                return c.get("id")
    return None


def _placeholder(shape) -> Optional[str]:
    for child in shape:
        if local(child).startswith("nv"):
            nv = child.find(p_("nvPr"))
            ph = nv.find(p_("ph")) if nv is not None else None
            if ph is not None:
                return ph.get("type") or "body"
    return None


def _shapes(tree) -> list:
    """Every shape, groups opened, in the slide's own z-order (Fallback skipped)."""
    out = []
    for child in tree:
        if child.tag == f"{{{MC_NS}}}AlternateContent":
            choice = child.find(f"{{{MC_NS}}}Choice")
            out.extend(_shapes(choice) if choice is not None else [])
        elif child.tag == p_("grpSp"):
            out.extend(_shapes(child))
        elif child.tag in (p_("sp"), p_("graphicFrame"), p_("cxnSp")):
            out.append(child)
    return out


def _table(frame):
    return frame.find(f".//{a_('tbl')}")


def _notes_body(pkg: Package, slide_part: str):
    for notes in pkg.targets_of_type(slide_part, "notesSlide"):
        for shape in _shapes(pkg.xml(notes).find(f".//{p_('spTree')}")):
            if _placeholder(shape) == "body":
                return notes, shape.find(p_("txBody"))
    return None, None


def project(data: bytes) -> Tuple[str, int]:
    """One `## Slide {n}` section per slide, each block led by its address."""
    pkg = Package(data)
    sections: List[str] = []
    for n, part in enumerate(_slides(pkg), start=1):
        tree = pkg.xml(part).find(f".//{p_('spTree')}")
        blocks: List[str] = []
        for shape in _shapes(tree if tree is not None else []):
            sid = _shape_id(shape)
            tbl = _table(shape) if shape.tag == p_("graphicFrame") else None
            if tbl is not None:
                rows = []
                for r, tr in enumerate(tbl.iterchildren(a_("tr")), start=1):
                    cells = []
                    for c, tc in enumerate(tr.iterchildren(a_("tc")), start=1):
                        body = tc.find(a_("txBody"))
                        text = _body_text(body) if body is not None else ""
                        cells.append(f"[s{n}/{sid}/r{r}c{c}] {text}".replace("|", "\\|").replace("\n", " ")
                                     if text else "")
                    rows.append(cells)
                if any(any(c for c in row) for row in rows):
                    width = max(len(row) for row in rows)
                    lines = []
                    for i, row in enumerate(rows):
                        lines.append("| " + " | ".join(row + [""] * (width - len(row))) + " |")
                        if i == 0:
                            lines.append("|" + "---|" * width)
                    blocks.append("\n".join(lines))
                continue
            body = shape.find(p_("txBody"))
            text = _body_text(body) if body is not None else ""
            if text:
                label = _LABELS.get(_placeholder(shape) or "")
                blocks.append(f"[s{n}/{sid}{' · ' + label if label else ''}] {text}")
        _notes, notes_body = _notes_body(pkg, part)
        if notes_body is not None:
            notes = _body_text(notes_body)
            if notes:
                blocks.append(f"[s{n}/notes] Speaker notes: {notes}")
        if blocks:
            sections.append(f"## Slide {n}\n\n" + "\n\n".join(blocks))
    return "\n\n".join(sections), len(sections)


_ADDR = re.compile(r"^\s*\[?\s*s(\d+)\s*/\s*(notes|\d+)(?:\s*/\s*r(\d+)\s*c(\d+))?", re.I)


def _resolve(pkg: Package, slides: List[str], at: str):
    """(part, txBody, where) for an address."""
    m = _ADDR.match(at or "")
    if not m:
        raise OfficeEditError(
            f"{at!r} is not a slide address. A deck is addressed by the labels its text "
            "shows: 's3/5' (slide 3, shape 5), 's3/7/r2c1' (a table cell), 's3/notes'."
        )
    n = int(m.group(1))
    if not 1 <= n <= len(slides):
        raise OfficeEditError(f"Slide {n} does not exist — the deck has {len(slides)} slides.")
    part = slides[n - 1]
    where = f"s{n}/{m.group(2)}"
    if m.group(2).lower() == "notes":
        notes_part, body = _notes_body(pkg, part)
        if body is None:
            raise OfficeEditError(f"Slide {n} has no speaker notes yet; yarnnn does not add a notes page.")
        return notes_part, body, where
    tree = pkg.xml(part).find(f".//{p_('spTree')}")
    shape = next((sh for sh in _shapes(tree) if _shape_id(sh) == m.group(2)), None)
    if shape is None:
        raise OfficeEditError(f"Slide {n} has no shape {m.group(2)}. Re-read the deck.")
    if m.group(3):
        tbl = _table(shape)
        r, c = int(m.group(3)), int(m.group(4))
        rows = list(tbl.iterchildren(a_("tr"))) if tbl is not None else []
        cells = list(rows[r - 1].iterchildren(a_("tc"))) if 0 < r <= len(rows) else []
        if not 0 < c <= len(cells):
            raise OfficeEditError(f"{where} has no cell r{r}c{c}.")
        body = cells[c - 1].find(a_("txBody"))
        return part, body, f"{where}/r{r}c{c}"
    body = shape.find(p_("txBody"))
    if body is None:
        raise OfficeEditError(f"{where} holds no text.")
    return part, body, where


def _rewrite(body, new: str) -> None:
    """Replace a text body's paragraphs, keeping each position's paragraph and run
    properties (the first line takes the first paragraph's look, and so on)."""
    paras = _paras(body)
    lines = new.split("\n") if new else [""]
    template = paras[-1] if paras else None
    for i, line in enumerate(lines):
        if i < len(paras):
            para = paras[i]
        else:
            para = copy.deepcopy(template) if template is not None else body.makeelement(a_("p"), {})
            if paras:
                paras[-1].addnext(para)
            else:
                body.append(para)
            paras.append(para)
        run_props = None
        for child in list(para):
            if child.tag in (a_("r"), a_("fld")):
                if run_props is None and child.find(a_("rPr")) is not None:
                    run_props = copy.deepcopy(child.find(a_("rPr")))
                para.remove(child)
            elif child.tag == a_("br"):
                para.remove(child)
        if line:
            r = para.makeelement(a_("r"), {})
            if run_props is not None:
                r.append(run_props)
            t = r.makeelement(a_("t"), {})
            t.text = line
            r.append(t)
            end = para.find(a_("endParaRPr"))
            (end.addprevious(r) if end is not None else para.append(r))
    for extra in paras[len(lines):]:
        body.remove(extra)


def apply(data: bytes, edits: List[dict], *, author: Optional[str] = None,
          when: Optional[str] = None) -> Tuple[bytes, List[str]]:
    """Change text in addressed shapes, table cells and notes; returns (bytes, lines).

    Each edit: {"op": "replace", "at": "s3/5", "old"?: str, "new": str}. With
    `old` the phrase is replaced inside its run; without it the whole text body
    is rewritten, one paragraph per line of `new`.
    """
    pkg = Package(data)
    slides = _slides(pkg)
    resolved = [(e, *_resolve(pkg, slides, e.get("at", ""))) for e in edits]
    done: List[str] = []
    for edit, part, body, where in resolved:
        if edit.get("op") not in ("replace", None):
            raise OfficeEditError("A deck edit changes text: anchor={'at': 's3/5'} with new_string.")
        old, new = edit.get("old"), edit.get("new") or ""
        if old:
            if "\n" in old or "\n" in new:
                raise OfficeEditError(
                    f"A line break cannot go inside a phrase. Rewrite the whole of {where} (omit old_string)."
                )
            hits = [(p, t) for p in _paras(body)
                    for t in ["".join(x for _e, x in _para_segments(p))] if old in t]
            if not hits:
                raise OfficeEditError(f"{where} does not contain {old!r}. Its text is {_body_text(body)!r}.")
            if len(hits) > 1 or hits[0][1].count(old) > 1:
                raise OfficeEditError(f"{old!r} occurs more than once in {where}; include more of the text.")
            para, text = hits[0]
            s, e = find_unique(text, old, where)
            replace_in_segments(_para_segments(para), s, e, new, set_text=_plain)
            done.append(f"replaced text in {where}")
        else:
            _rewrite(body, new)
            done.append(f"rewrote {where}")
        pkg.touch(part)
    return pkg.save(), done


KIND = OfficeKind(
    name="PowerPoint deck",
    address_hint="[s3/5] is slide 3, shape 5; s3/7/r2c1 a table cell; s3/notes the notes",
    tracks_changes=False,
    project=project,
    apply=apply,
)

__all__ = ["KIND", "apply", "project"]
