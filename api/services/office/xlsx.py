"""Excel workbooks — the addressed projection and the in-place edit (ADR-671).

── The address ───────────────────────────────────────────────────────────────

A cell is addressed as Excel addresses it: `Budget!B7`, `'Q3 Plan'!B7`, or `B7`
when the workbook has one sheet. The projection draws each sheet as a Markdown
table under a column-letter header, each row led by its row number — so the
address of every value is on the page. A formula cell shows its formula beside
its last-calculated value (`=SUM(B2:B19) → 4210`): an agent needs both to
change a sheet without breaking it.

── The edit ──────────────────────────────────────────────────────────────────

Written at the XML level, never through openpyxl's workbook model, which drops
charts, pivot caches and images from a workbook it loads and saves. Only the
edited sheet's XML (and, on a formula change, the calculation chain) changes:

  * text is written as an INLINE string, so `sharedStrings.xml` is never
    rewritten;
  * the cell keeps its style index, so a percent stays a percent;
  * overwriting the master cell of a shared formula first gives every
    dependent cell its own formula (openpyxl's Translator), so none is lost;
  * `fullCalcOnLoad` is set and a stale `calcChain.xml` dropped, so Excel
    recalculates on open. yarnnn computes nothing: until the file is opened in
    Excel, a dependent cell shows its value as last calculated, and says so.

A formula is the member's or the agent's to write, but not a channel out: DDE
(`cmd|' /C …'`) and the XLM executors (`CALL`, `REGISTER`, `EXEC`) are refused.
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from services.office.package import OfficeEditError, OfficeKind, Package, local

S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def s(tag: str) -> str:
    return f"{{{S}}}{tag}"


RECALC_NOTE = (
    "(This workbook changed since it was last calculated. A formula's value is as last "
    "calculated; Excel recalculates when the file is next opened.)"
)


# ── addresses ───────────────────────────────────────────────────────────────


_REF = re.compile(
    r"^\s*(?:(?:'((?:[^']|'')+)'|([^!]+?))\s*!)?\s*\$?([A-Za-z]{1,3})\$?(\d{1,7})\s*$"
)


def col_letter(n: int) -> str:
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def col_index(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - 64)
    return n


def parse_ref(at: str) -> Tuple[Optional[str], int, int]:
    """'Budget!B7' → ('Budget', 7, 2). The sheet is None when not named."""
    m = _REF.match(at or "")
    if not m:
        raise OfficeEditError(
            f"{at!r} is not a cell address. A workbook is addressed as Excel addresses it: "
            "'Budget!B7', or 'B7' in a one-sheet workbook."
        )
    sheet = m.group(1).replace("''", "'") if m.group(1) is not None else m.group(2)
    return (sheet.strip() if sheet else None), int(m.group(4)), col_index(m.group(3))


# ── display (one spelling, used by the projection AND the edit's guard) ─────


def _num(v: float) -> str:
    if isinstance(v, int) or (isinstance(v, float) and v.is_integer() and abs(v) < 1e15):
        return str(int(v))
    return format(v, ".15g")


def show(value, number_format: Optional[str] = None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ") if (value.hour or value.minute or value.second) else value.date().isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, (int, float)):
        if number_format and "%" in number_format:
            return f"{_num(value * 100)}%"
        return _num(value)
    text = str(value)
    # Excel's own convention: a leading apostrophe marks literal text, so a
    # text cell that SAYS "=SUM(…)" never reads like a formula (parse_value
    # takes the same apostrophe back off).
    return "'" + text if text.startswith(("=", "'")) else text


def _formula_text(cell) -> Optional[str]:
    if getattr(cell, "data_type", None) != "f":
        return None
    v = cell.value
    text = getattr(v, "text", v)
    return str(text) if text is not None else None


def _cell_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


# ── the projection ──────────────────────────────────────────────────────────


def _needs_recalc(pkg: Package) -> bool:
    calc = pkg.xml(pkg.main_part()).find(s("calcPr"))
    return calc is not None and calc.get("fullCalcOnLoad") in ("1", "true")


def project(data: bytes) -> Tuple[str, int]:
    """Every sheet as an addressed table. Returns (text, sheet_count)."""
    import openpyxl

    values = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    formulas = openpyxl.load_workbook(io.BytesIO(data), data_only=False, read_only=True)
    try:
        sections: List[str] = []
        for ws_v, ws_f in zip(values.worksheets, formulas.worksheets):
            # A stored <dimension> is a hint other tools leave stale; read the rows.
            ws_v.reset_dimensions()
            ws_f.reset_dimensions()
            rows: List[Tuple[int, List[str]]] = []
            width = 0
            for r, (row_v, row_f) in enumerate(
                zip(ws_v.iter_rows(min_row=1, min_col=1), ws_f.iter_rows(min_row=1, min_col=1)),
                start=1,
            ):
                cells: List[str] = []
                for cv, cf in zip(row_v, row_f):
                    shown = show(getattr(cv, "value", None), getattr(cv, "number_format", None))
                    formula = _formula_text(cf)
                    if formula:
                        shown = f"{formula} → {shown}" if shown else formula
                    cells.append(_cell_md(shown))
                while cells and not cells[-1].strip():
                    cells.pop()
                if cells:
                    rows.append((r, cells))
                    width = max(width, len(cells))
            if not rows:
                continue
            head = "|  | " + " | ".join(col_letter(c) for c in range(1, width + 1)) + " |"
            sep = "|---|" + "---|" * width
            body = [f"| {r} | " + " | ".join(c + [""] * (width - len(c))) + " |" for r, c in rows]
            sections.append(f"## {ws_v.title}\n\n" + "\n".join([head, sep, *body]))
    finally:
        values.close()
        formulas.close()
    if sections and _needs_recalc(Package(data)):
        sections.insert(0, RECALC_NOTE)
    return "\n\n".join(sections), len([x for x in sections if x.startswith("## ")])


# ── the edit ────────────────────────────────────────────────────────────────


_NUM = re.compile(r"^[-+]?(\d+(\.\d+)?|\.\d+)([eE][-+]?\d+)?$")
_GROUPED = re.compile(r"^[-+]?\d{1,3}(,\d{3})+(\.\d+)?$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$")
_FORBIDDEN = re.compile(r"\b(CALL|REGISTER(\.ID)?|EXEC)\s*\(", re.I)
_BUILTIN_DATE_FMTS = {14, 15, 16, 17, 18, 19, 20, 21, 22, 45, 46, 47}


def parse_value(new: Optional[str]):
    """A string an agent or member typed → (kind, value)."""
    if new is None or not new.strip():
        return "clear", None
    text = new.strip()
    if text.startswith("'"):
        return "text", new.lstrip()[1:]
    if text.startswith("="):
        formula = text[1:]
        outside_strings = re.sub(r'"[^"]*"', "", formula)
        if "|" in outside_strings or _FORBIDDEN.search(outside_strings):
            raise OfficeEditError(
                "That formula calls outside the workbook (DDE or an XLM executor) — refused."
            )
        return "formula", formula
    if text.upper() in ("TRUE", "FALSE"):
        return "bool", text.upper() == "TRUE"
    pct = text.endswith("%")
    core = text[:-1].strip() if pct else text
    if _GROUPED.match(core):
        core = core.replace(",", "")
    if _NUM.match(core):
        if not pct and re.fullmatch(r"[-+]?\d+", core):
            return "number", int(core)
        number = float(core)
        return "number", number / 100 if pct else number
    if _ISO_DATE.match(text):
        return "date", datetime.fromisoformat(text.replace(" ", "T"))
    return "text", new


def _excel_serial(dt: datetime) -> float:
    delta = dt - datetime(1899, 12, 30)
    return delta.days + delta.seconds / 86400


class _Book:
    """The workbook's sheet map, styles and calc settings, read from its XML."""

    def __init__(self, pkg: Package):
        self.pkg = pkg
        self.main = pkg.main_part()
        root = pkg.xml(self.main)
        rels = pkg.rels(self.main)
        self.sheets: Dict[str, str] = {}
        self.order: List[str] = []
        sheets_el = root.find(s("sheets"))
        for sh in (sheets_el if sheets_el is not None else []):
            rid = sh.get(f"{{{R_NS}}}id")
            if rid in rels:
                self.sheets[sh.get("name")] = rels[rid]
                self.order.append(sh.get("name"))
        self._date_xfs: Optional[set] = None

    def sheet_part(self, name: Optional[str]) -> Tuple[str, str]:
        if name is None:
            if len(self.order) != 1:
                raise OfficeEditError(
                    f"This workbook has {len(self.order)} sheets — name one: "
                    + ", ".join(f"'{n}'!B7" for n in self.order[:6])
                )
            name = self.order[0]
        for real in self.order:
            if real.lower() == name.lower():
                return real, self.sheets[real]
        raise OfficeEditError(
            f"There is no sheet {name!r}. The sheets are: " + ", ".join(self.order) + "."
        )

    def is_date_style(self, s_index: Optional[str]) -> bool:
        if self._date_xfs is None:
            self._date_xfs = set()
            styles = self.pkg.targets_of_type(self.main, "styles")
            if styles:
                root = self.pkg.xml(styles[0])
                custom = {}
                numfmts = root.find(s("numFmts"))
                for nf in (numfmts if numfmts is not None else []):
                    code = re.sub(r'"[^"]*"|\[[^\]]*\]', "", nf.get("formatCode") or "")
                    custom[int(nf.get("numFmtId"))] = bool(re.search(r"[dy]|h.*m|m.*s", code, re.I))
                xfs = root.find(s("cellXfs"))
                for i, xf in enumerate(xfs if xfs is not None else []):
                    fid = int(xf.get("numFmtId") or 0)
                    if fid in _BUILTIN_DATE_FMTS or custom.get(fid):
                        self._date_xfs.add(i)
        return s_index is not None and s_index.isdigit() and int(s_index) in self._date_xfs

    def mark_recalc(self, drop_chain: bool) -> None:
        root = self.pkg.xml(self.main)
        calc = root.find(s("calcPr"))
        if calc is None:
            calc = root.makeelement(s("calcPr"), {})
            after = None
            for tag in ("sheets", "functionGroups", "externalReferences", "definedNames"):
                el = root.find(s(tag))
                if el is not None:
                    after = el
            (after.addnext(calc) if after is not None else root.append(calc))
        calc.set("fullCalcOnLoad", "1")
        self.pkg.touch(self.main)
        if drop_chain:
            self._drop_calc_chain()

    def _drop_calc_chain(self) -> None:
        chain = [t for t in self.pkg.targets_of_type(self.main, "calcChain")]
        if not chain:
            return
        folder = self.main.rsplit("/", 1)[0]
        rels_name = f"{folder}/_rels/{self.main.rsplit('/', 1)[1]}.rels"
        rels = self.pkg.xml(rels_name)
        for rel in list(rels):
            if (rel.get("Type") or "").endswith("/calcChain"):
                rels.remove(rel)
        self.pkg.touch(rels_name)
        ct = self.pkg.xml("[Content_Types].xml")
        for ov in list(ct):
            if ov.get("PartName", "").lstrip("/") in chain:
                ct.remove(ov)
        self.pkg.touch("[Content_Types].xml")
        for part in chain:
            self.pkg.remove(part)


def _row(sheet_data, r: int):
    for row in sheet_data.iterchildren(s("row")):
        n = int(row.get("r") or 0)
        if n == r:
            return row
        if n > r:
            new = row.makeelement(s("row"), {"r": str(r)})
            row.addprevious(new)
            return new
    new = sheet_data.makeelement(s("row"), {"r": str(r)})
    sheet_data.append(new)
    return new


def _cell(row, ref: str, c: int):
    for cell in row.iterchildren(s("c")):
        m = re.match(r"([A-Z]+)", cell.get("r") or "")
        idx = col_index(m.group(1)) if m else 0
        if idx == c:
            return cell
        if idx > c:
            new = cell.makeelement(s("c"), {"r": ref})
            cell.addprevious(new)
            return new
    new = row.makeelement(s("c"), {"r": ref})
    row.append(new)
    return new


def _widen_dimension(sheet, r: int, c: int) -> None:
    """Keep `<dimension ref>` covering every written cell — readers trust it."""
    dim = sheet.find(s("dimension"))
    if dim is None:
        return
    m = re.match(r"([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$", dim.get("ref") or "")
    if not m:
        return
    c1, r1 = col_index(m.group(1)), int(m.group(2))
    c2, r2 = (col_index(m.group(3)), int(m.group(4))) if m.group(3) else (c1, r1)
    c1, r1, c2, r2 = min(c1, c), min(r1, r), max(c2, c), max(r2, r)
    dim.set("ref", f"{col_letter(c1)}{r1}:{col_letter(c2)}{r2}")


def _in_merge(sheet, r: int, c: int) -> Optional[str]:
    merges = sheet.find(s("mergeCells"))
    for mc in (merges if merges is not None else []):
        m = re.match(r"([A-Z]+)(\d+):([A-Z]+)(\d+)", mc.get("ref") or "")
        if not m:
            continue
        c1, r1, c2, r2 = col_index(m.group(1)), int(m.group(2)), col_index(m.group(3)), int(m.group(4))
        if r1 <= r <= r2 and c1 <= c <= c2 and (r, c) != (r1, c1):
            return f"{m.group(1)}{r1}"
    return None


def _materialise_shared(sheet, master) -> None:
    """Give every cell of a shared-formula group its own formula (D10)."""
    from openpyxl.formula.translate import Translator

    f = master.find(s("f"))
    si, text, origin = f.get("si"), f.text or "", master.get("r")
    for cell in sheet.iter(s("c")):
        cf = cell.find(s("f"))
        if cf is None or cf.get("t") != "shared" or cf.get("si") != si:
            continue
        if cell is not master:
            cf.text = Translator("=" + text, origin=origin).translate_formula(cell.get("r"))[1:]
        for attr in ("t", "si", "ref"):
            cf.attrib.pop(attr, None)


def _write(cell, kind: str, value, book: _Book) -> None:
    for tag in ("f", "v", "is"):
        for el in cell.findall(s(tag)):
            cell.remove(el)
    cell.attrib.pop("t", None)
    if kind == "clear":
        return
    if kind == "date":
        if not book.is_date_style(cell.get("s")):
            kind, value = "text", value.date().isoformat() if not value.hour else value.isoformat(sep=" ")
        else:
            kind, value = "number", _excel_serial(value)
    if kind == "formula":
        f = cell.makeelement(s("f"), {})
        f.text = value
        cell.append(f)
    elif kind == "number":
        v = cell.makeelement(s("v"), {})
        v.text = _num(value)
        cell.append(v)
    elif kind == "bool":
        cell.set("t", "b")
        v = cell.makeelement(s("v"), {})
        v.text = "1" if value else "0"
        cell.append(v)
    else:
        cell.set("t", "inlineStr")
        is_el = cell.makeelement(s("is"), {})
        t = is_el.makeelement(s("t"), {})
        t.text = value
        if value != value.strip():
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        is_el.append(t)
        cell.append(is_el)


def _current(data: bytes, sheet: str, r: int, c: int) -> Tuple[str, Optional[str]]:
    """The cell's current display value and formula, spelled as the projection spells them."""
    import openpyxl

    out = []
    for data_only in (True, False):
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=data_only, read_only=True)
        try:
            cell = next(wb[sheet].iter_rows(min_row=r, max_row=r, min_col=c, max_col=c))[0]
            out.append(cell)
        finally:
            wb.close()
    return show(getattr(out[0], "value", None), getattr(out[0], "number_format", None)), _formula_text(out[1])


def apply(data: bytes, edits: List[dict], *, author: Optional[str] = None,
          when: Optional[str] = None) -> Tuple[bytes, List[str]]:
    """Set addressed cells; returns (bytes, one line per edit).

    Each edit: {"op": "replace", "at": "Budget!B7", "old"?: str, "new": str}.
    `old`, when given, must match the cell as the projection shows it — its
    value, its formula, or both as printed. `author` is unused: a workbook has
    no tracked changes, so its attribution is the revision's.
    """
    pkg = Package(data)
    book = _Book(pkg)
    done: List[str] = []
    formula_changed = False
    for edit in edits:
        if edit.get("op") not in ("replace", None):
            raise OfficeEditError("A workbook edit sets a cell: anchor={'at': 'Sheet!B7'} with new_string.")
        sheet_name, r, c = parse_ref(edit.get("at", ""))
        real, part = book.sheet_part(sheet_name)
        ref = f"{col_letter(c)}{r}"
        where = f"'{real}'!{ref}" if " " in real else f"{real}!{ref}"
        old = edit.get("old")
        if old is not None and old.strip():
            shown, formula = _current(data, real, r, c)
            printed = f"{formula} → {shown}" if formula and shown else (formula or shown)
            if old.strip() not in {shown, formula or "", printed}:
                raise OfficeEditError(
                    f"{where} holds {printed!r}, not {old!r}. Re-read the sheet; it may have changed."
                )
        sheet = pkg.xml(part)
        anchor = _in_merge(sheet, r, c)
        if anchor:
            raise OfficeEditError(f"{where} is inside a merged range — write to its first cell, {anchor}.")
        sheet_data = sheet.find(s("sheetData"))
        row = _row(sheet_data, r)
        row.attrib.pop("spans", None)
        cell = _cell(row, ref, c)
        f = cell.find(s("f"))
        if f is not None:
            formula_changed = True
            if f.get("t") == "shared" and f.get("ref"):
                _materialise_shared(sheet, cell)
        kind, value = parse_value(edit.get("new"))
        formula_changed = formula_changed or kind == "formula"
        _write(cell, kind, value, book)
        _widen_dimension(sheet, r, c)
        pkg.touch(part)
        done.append(f"set {where}" if kind != "clear" else f"cleared {where}")
    book.mark_recalc(drop_chain=formula_changed)
    return pkg.save(), done


KIND = OfficeKind(
    name="Excel workbook",
    address_hint="a cell is Sheet!B7 — the table's column letter and row number",
    tracks_changes=False,
    project=project,
    apply=apply,
)

__all__ = ["KIND", "RECALC_NOTE", "apply", "col_letter", "parse_ref", "parse_value", "project", "show"]
