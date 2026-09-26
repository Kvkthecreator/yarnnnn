"""Word documents — the addressed projection and the in-place edit (ADR-671).

ONE module owns both halves, so the address a reader is shown and the address an
edit resolves are computed by the same function (`_paragraphs`) and cannot drift.

── The address ───────────────────────────────────────────────────────────────

`pN` is the Nth `w:p` of the document body in document order — body paragraphs,
table-cell paragraphs and text-box paragraphs alike (a text box's `mc:Fallback`
copy is skipped: Word writes the same paragraphs twice, once per rendering).
Position is deliberately the address: python-docx, Google Docs and LibreOffice do
not write Word's `w14:paraId`, and Word regenerates it on edit. A position is made
safe by content, not by identity — an edit names the text it expects
(`old_string`) or replaces the whole paragraph, so a stale address fails loudly.

── The edit ──────────────────────────────────────────────────────────────────

Operations change `w:t` text inside existing runs, so every run keeps its own
formatting; new text takes the formatting of the first run it replaces. When an
`author` is given the change is a Word TRACKED change (`w:ins` / `w:del` /
`w:pPrChange`) authored by that name — attribution the member sees in Word
itself (D4). Without one, the edit is direct.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from services.office.package import (
    OfficeKind,
    MC_NS,
    OfficeEditError,
    Package,
    find_unique,
    local,
    replace_in_segments,
    set_preserved_text,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def w(tag: str) -> str:
    return f"{{{W}}}{tag}"


_PSEUDO = {"tab": "\t", "br": "\n", "cr": "\n", "noBreakHyphen": "-"}
#: Containers whose text is not the paragraph's visible text.
_SKIP = {w("del"), w("moveFrom"), w("pPr"), w("rPr"), f"{{{MC_NS}}}Fallback"}

TRACKED_NOTE = (
    "(This document has tracked changes pending; its text reads as if they were accepted.)"
)


# ── the address space ───────────────────────────────────────────────────────


def _in_fallback(el) -> bool:
    return any(a.tag == f"{{{MC_NS}}}Fallback" for a in el.iterancestors())


def _paragraphs(body) -> list:
    """Every addressable paragraph, in document order. THE address function."""
    return [p for p in body.iter(w("p")) if not _in_fallback(p)]


def _segments(p) -> List[Tuple[object, str, object]]:
    """(element, text, run) for the paragraph's visible text, in order.

    `element` is a `w:t` for text a run holds, or None for a tab / line break
    (structure a replacement cannot absorb). Nested paragraphs (text boxes) are
    their own addresses and are skipped, as is deleted text.
    """
    out: List[Tuple[object, str, object]] = []

    def walk(el, run):
        for child in el:
            if not isinstance(child.tag, str) or child.tag in _SKIP or child.tag == w("p"):
                continue
            name = local(child)
            r = child if child.tag == w("r") else run
            if child.tag == w("t"):
                out.append((child, child.text or "", r))
            elif child.tag.startswith(f"{{{W}}}") and name in _PSEUDO:
                out.append((None, _PSEUDO[name], r))
            else:
                walk(child, r)

    walk(p, None)
    return out


def _text(p) -> str:
    return "".join(t for _el, t, _r in _segments(p))


def _parse_address(at: str, count: int) -> int:
    m = re.match(r"^\s*\[?\s*[pP¶]\s*(\d+)", at or "")
    if not m:
        raise OfficeEditError(
            f"{at!r} is not a paragraph address. A Word document is addressed by the "
            "`pN` labels its text shows, e.g. anchor={'at': 'p12'}."
        )
    n = int(m.group(1))
    if not 1 <= n <= count:
        raise OfficeEditError(f"p{n} does not exist — the document has {count} paragraphs.")
    return n


# ── styles ───────────────────────────────────────────────────────────────────


def _styles(pkg: Package, main: str) -> Tuple[Dict[str, str], Optional[str]]:
    """(styleId → display name, the default paragraph style id)."""
    names: Dict[str, str] = {}
    default = None
    for part in pkg.targets_of_type(main, "styles"):
        for st in pkg.xml(part).iter(w("style")):
            if st.get(w("type")) != "paragraph":
                continue
            sid = st.get(w("styleId"))
            name_el = st.find(w("name"))
            name = name_el.get(w("val")) if name_el is not None else sid
            names[sid] = name
            if st.get(w("default")) in ("1", "true"):
                default = sid
    return names, default


def _style_of(p) -> Optional[str]:
    ppr = p.find(w("pPr"))
    ps = ppr.find(w("pStyle")) if ppr is not None else None
    return ps.get(w("val")) if ps is not None else None


def _label(sid: Optional[str], names: Dict[str, str], default: Optional[str]) -> str:
    if not sid or sid == default:
        return ""
    name = names.get(sid, sid)
    return "" if name.lower() == "normal" else name[:1].upper() + name[1:]


# ── the projection ───────────────────────────────────────────────────────────


def _nearest(el, tag: str):
    for a in el.iterancestors():
        if a.tag == tag:
            return a
    return None


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def project(data: bytes) -> Tuple[str, int]:
    """The document's words, each paragraph labelled with its address.

    Body order; a table as a Markdown table whose cells carry their paragraphs'
    addresses; headers and footers last, labelled and unaddressed (read-only in
    Phase 1). Returns (text, block_count).
    """
    pkg = Package(data)
    main = pkg.main_part()
    root = pkg.xml(main)
    body = root.find(w("body"))
    if body is None:
        return "", 0
    paras = _paragraphs(body)
    index = {p: n for n, p in enumerate(paras, start=1)}
    names, default = _styles(pkg, main)
    blocks: List[str] = []

    def line(p) -> Optional[str]:
        text = _text(p)
        if not text.strip():
            return None
        label = _label(_style_of(p), names, default)
        return f"[p{index[p]}{' · ' + label if label else ''}] {text.strip()}"

    def table(tbl) -> Optional[str]:
        rows: List[List[str]] = []
        for tr in tbl.iter(w("tr")):
            if _nearest(tr, w("tbl")) is not tbl:
                continue
            cells = []
            for tc in tr.iter(w("tc")):
                if _nearest(tc, w("tr")) is not tr:
                    continue
                parts = [
                    f"[p{index[p]}] {_text(p).strip()}"
                    for p in tc.iter(w("p")) if p in index and _text(p).strip()
                ]
                cells.append(_cell(" ".join(parts)))
            rows.append(cells)
        if not any(any(c for c in r) for r in rows):
            return None
        width = max(len(r) for r in rows)
        out = []
        for i, r in enumerate(rows):
            out.append("| " + " | ".join(r + [""] * (width - len(r))) + " |")
            if i == 0:
                out.append("|" + "---|" * width)
        return "\n".join(out)

    def walk(container):
        for child in container:
            if child.tag == w("p"):
                own = line(child)
                if own:
                    blocks.append(own)
                # Text boxes anchored in this paragraph are their own addresses.
                for inner in child.iter(w("p")):
                    if inner is not child and inner in index:
                        nested = line(inner)
                        if nested:
                            blocks.append(nested)
            elif child.tag == w("tbl"):
                t = table(child)
                if t:
                    blocks.append(t)
            elif child.tag in (w("sdt"), w("sdtContent"), w("customXml")):
                walk(child)

    walk(body)

    tracked = root.find(f".//{w('ins')}") is not None or root.find(f".//{w('del')}") is not None
    if tracked:
        blocks.insert(0, TRACKED_NOTE)

    seen = set()
    for kind in ("header", "footer"):
        for part in pkg.targets_of_type(main, kind):
            text = " ".join(_text(p).strip() for p in pkg.xml(part).iter(w("p")) if _text(p).strip())
            if text and (kind, text) not in seen:
                seen.add((kind, text))
                blocks.append(f"{kind.capitalize()}: {text}")

    return "\n\n".join(blocks), len(blocks)


# ── the edit ─────────────────────────────────────────────────────────────────


class _Revision:
    """Mints tracked-change markup for one author, with document-unique ids."""

    def __init__(self, root, author: Optional[str], when: str):
        self.author = author
        self.when = when
        ids = [int(v) for el in root.iter() for k, v in el.attrib.items()
               if k == w("id") and v.lstrip("-").isdigit()]
        self._next = max(ids, default=0) + 1

    @property
    def tracked(self) -> bool:
        return bool(self.author)

    def mark(self, tag: str):
        el = _ELEMENT_FACTORY(w(tag))
        el.set(w("id"), str(self._next))
        self._next += 1
        el.set(w("author"), self.author or "")
        el.set(w("date"), self.when)
        return el


def _ELEMENT_FACTORY(tag):
    from lxml import etree
    return etree.Element(tag, nsmap={"w": W})


def _sub(parent, tag: str, index: Optional[int] = None):
    el = _ELEMENT_FACTORY(w(tag))
    if index is None:
        parent.append(el)
    else:
        parent.insert(index, el)
    return el


def _run(rpr, text: str):
    """A new run carrying `rpr` (copied) and `text`, with line breaks as `w:br`."""
    r = _ELEMENT_FACTORY(w("r"))
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    for i, piece in enumerate(text.split("\n")):
        if i:
            _sub(r, "br")
        if piece:
            set_preserved_text(_sub(r, "t"), piece)
    return r


def _first_rpr(p):
    for _el, _t, run in _segments(p):
        if run is not None:
            return run.find(w("rPr"))
    return None


def _split(t_el, k: int):
    """Split the run holding `t_el` so its text breaks at character `k`."""
    r = t_el.getparent()
    if r is None or r.tag != w("r"):
        raise OfficeEditError("The text sits outside a run and cannot be tracked.")
    kids = list(r)
    idx = kids.index(t_el)
    text = t_el.text or ""
    r2 = copy.deepcopy(r)
    kids2 = list(r2)
    for j, kid in enumerate(kids2):
        if j < idx and kid.tag != w("rPr"):
            r2.remove(kid)
    set_preserved_text(kids2[idx], text[k:])
    for kid in kids[idx + 1:]:
        r.remove(kid)
    set_preserved_text(t_el, text[:k])
    r.addnext(r2)


def _split_at(p, pos: int) -> None:
    offset = 0
    for el, text, _run in _segments(p):
        if el is not None and offset < pos < offset + len(text):
            _split(el, pos - offset)
            return
        offset += len(text)


def _runs_in(p, start: int, end: int) -> list:
    runs, offset = [], 0
    for _el, text, run in _segments(p):
        lo, hi = offset, offset + len(text)
        offset = hi
        if lo >= start and hi <= end and hi > lo and run is not None and run not in runs:
            runs.append(run)
    return runs


def _delete_runs(runs, rev: _Revision):
    """Wrap each run in `w:del`, its text becoming deleted text. Returns the last wrapper."""
    last = None
    for run in runs:
        for t in run.iter(w("t")):
            t.tag = w("delText")
        for t in run.iter(w("instrText")):
            t.tag = w("delInstrText")
        wrapper = rev.mark("del")
        run.addprevious(wrapper)
        wrapper.append(run)
        last = wrapper
    return last


def _tracked_replace(p, start: int, end: int, new: str, rev: _Revision) -> None:
    rpr = None
    if end > start:
        _split_at(p, end)
        _split_at(p, start)
        runs = _runs_in(p, start, end)
        rpr = runs[0].find(w("rPr")) if runs else None
        anchor = _delete_runs(runs, rev)
    else:
        anchor = None
    if not new:
        return
    ins = rev.mark("ins")
    ins.append(_run(rpr if rpr is not None else _first_rpr(p), new))
    if anchor is None:
        p.append(ins)
    elif anchor.getparent() is not None and anchor.getparent().tag == w("ins"):
        anchor.getparent().addnext(ins)  # never an insertion inside another's insertion
    else:
        anchor.addnext(ins)


def _mark_paragraph(p, tag: str, rev: _Revision) -> None:
    """Mark the paragraph MARK itself inserted or deleted (`w:pPr/w:rPr/w:ins|del`)."""
    ppr = p.find(w("pPr"))
    if ppr is None:
        ppr = _sub(p, "pPr", 0)
    rpr = ppr.find(w("rPr"))
    if rpr is None:
        rpr = _ELEMENT_FACTORY(w("rPr"))
        tail = next((c for c in ppr if c.tag in (w("sectPr"), w("pPrChange"))), None)
        if tail is not None:
            tail.addprevious(rpr)
        else:
            ppr.append(rpr)
    # CT_ParaRPr puts ins/del FIRST; Word treats an out-of-order child as damage.
    rpr.insert(0, rev.mark(tag))


def _replace_whole(p, new: str, rev: _Revision) -> None:
    text = _text(p)
    if rev.tracked:
        _tracked_replace(p, 0, len(text), new, rev)
        return
    rpr = _first_rpr(p)
    # Direct: drop every run's text, then put the new words in the first run.
    for _el, _t, run in _segments(p):
        if run is not None and run.getparent() is not None:
            run.getparent().remove(run)
    if new:
        ppr = p.find(w("pPr"))
        r = _run(rpr, new)
        if ppr is not None:
            ppr.addnext(r)
        else:
            p.insert(0, r)


def _delete_paragraph(p, rev: _Revision) -> None:
    if rev.tracked:
        _replace_whole(p, "", rev)
        _mark_paragraph(p, "del", rev)
        return
    parent = p.getparent()
    siblings = [c for c in parent if c.tag == w("p")]
    if parent.tag == w("tc") and len(siblings) == 1:
        _replace_whole(p, "", rev)  # a table cell must keep one paragraph
        return
    parent.remove(p)


def _new_paragraph_after(anchor, text: str, style_id: Optional[str], rev: _Revision):
    p = _ELEMENT_FACTORY(w("p"))
    src = anchor.find(w("pPr"))
    if src is not None:
        ppr = copy.deepcopy(src)
        for drop in (w("sectPr"), w("pPrChange"), w("rPr")):
            for el in ppr.findall(drop):
                ppr.remove(el)
        p.append(ppr)
    if style_id:
        _set_style(p, style_id)
    rpr = None if style_id else _first_rpr(anchor)
    if rev.tracked:
        _mark_paragraph(p, "ins", rev)
        if text:
            ins = rev.mark("ins")
            ins.append(_run(rpr, text))
            p.append(ins)
    elif text:
        p.append(_run(rpr, text))
    anchor.addnext(p)
    return p


def _set_style(p, style_id: str) -> None:
    ppr = p.find(w("pPr"))
    if ppr is None:
        ppr = _sub(p, "pPr", 0)
    ps = ppr.find(w("pStyle"))
    if ps is None:
        ps = _sub(ppr, "pStyle", 0)
    ps.set(w("val"), style_id)


def _restyle(p, style_id: str, rev: _Revision) -> None:
    if rev.tracked:
        ppr = p.find(w("pPr"))
        before = copy.deepcopy(ppr) if ppr is not None else _ELEMENT_FACTORY(w("pPr"))
        for drop in (w("rPr"), w("sectPr"), w("pPrChange")):
            for el in before.findall(drop):
                before.remove(el)
        _set_style(p, style_id)
        change = rev.mark("pPrChange")
        change.append(before)
        p.find(w("pPr")).append(change)
    else:
        _set_style(p, style_id)


def _resolve_style(style: str, names: Dict[str, str]) -> str:
    want = (style or "").strip().lower()
    for sid, name in names.items():
        if want in (sid.lower(), name.lower()):
            return sid
    offered = ", ".join(sorted({n[:1].upper() + n[1:] for n in names.values()})[:24])
    raise OfficeEditError(
        f"This document has no paragraph style {style!r}. Its styles: {offered}."
    )


def apply(data: bytes, edits: List[dict], *, author: Optional[str] = None,
          when: Optional[str] = None) -> Tuple[bytes, List[str]]:
    """Apply addressed edits to a Word document; returns (bytes, one line per edit).

    Each edit: {"op": "replace"|"insert"|"style", "at": "p12", "old"?, "new"?, "style"?}.
    Every address resolves against the document AS READ, before any edit lands,
    so a batch means what its reader saw.
    """
    pkg = Package(data)
    main = pkg.main_part()
    root = pkg.xml(main)
    body = root.find(w("body"))
    if body is None:
        raise OfficeEditError("This document has no body.")
    paras = _paragraphs(body)
    names, _default = _styles(pkg, main)
    rev = _Revision(root, author, when or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

    resolved = [(e, paras[_parse_address(e.get("at", ""), len(paras)) - 1]) for e in edits]
    done: List[str] = []
    for edit, p in resolved:
        op, at = edit.get("op"), f"p{paras.index(p) + 1}"
        if op not in ("replace", "style", "insert"):
            raise OfficeEditError(f"Unknown edit {op!r}.")
        new = edit.get("new")
        style_id = _resolve_style(edit["style"], names) if edit.get("style") else None
        if op == "insert":
            prev = p
            for part in (new or "").split("\n\n"):
                prev = _new_paragraph_after(prev, part.strip("\n"), style_id, rev)
            done.append(f"inserted after {at}")
            continue
        if op == "replace":
            old = edit.get("old")
            if old:
                if "\n" in (new or ""):
                    raise OfficeEditError(
                        "A line break cannot go inside a phrase. Replace the whole "
                        f"paragraph (anchor {at}, no old_string) to split it."
                    )
                s, e = find_unique(_text(p), old, at)
                if rev.tracked:
                    _tracked_replace(p, s, e, new or "", rev)
                else:
                    replace_in_segments([(el, t) for el, t, _r in _segments(p)], s, e, new or "")
                done.append(f"replaced text in {at}")
            elif not new:
                _delete_paragraph(p, rev)
                done.append(f"deleted {at}")
                continue
            else:
                first, *rest = new.split("\n\n")
                _replace_whole(p, first.strip("\n"), rev)
                prev = p
                for part in rest:
                    prev = _new_paragraph_after(prev, part.strip("\n"), None, rev)
                done.append(f"rewrote {at}" + (f" as {len(rest) + 1} paragraphs" if rest else ""))
        if style_id:
            _restyle(p, style_id, rev)
            done.append(f"restyled {at} as {names.get(style_id, style_id)}")

    pkg.touch(main)
    return pkg.save(), done


KIND = OfficeKind(
    name="Word document",
    address_hint="[p12] is a paragraph",
    tracks_changes=True,
    project=project,
    apply=apply,
)

__all__ = ["KIND", "TRACKED_NOTE", "apply", "project"]
