"""ADR-590 gate — the rendered face is the editing surface.

Script-style (`python3 test_adr590_rendered_face.py`) like its neighbours —
under pytest these report a false pass, so run them directly.

The claims, at the altitudes they can actually fail:

1. **D1 — rendered stays rendered.** No decoration reverts to source because
   the caret arrived. Driven in a mounted canvas, never grepped: a name check
   here matched its own explanatory comment on the first attempt, which is the
   trap this gate family has paid for repeatedly.
2. **D2 — the cell IS the text field**, and typing in it writes markdown back.
   The write-back is the claim that matters and it is EXECUTED: a cell is
   edited, the document is read back, and the bytes are asserted. A check that
   only asked whether cells were `contenteditable` would pass over a widget
   that accepted keystrokes and dropped them.
3. **D2 — the round trip is lossless.** A cell carrying a `|` must survive
   serialization and re-parse, or an ordinary edit silently restructures the
   table.
4. **D3 — the fences render as themselves**, and a mermaid diagram's source is
   reachable ONLY by the declared affordance, never by the caret.

⭐ Every check here was falsified against a real break before being recorded.
The D1 falsification needed BOTH halves undone (the branch AND the field's
selection dependency) — restoring the branch alone left the gate green, because
the field no longer recomputes on a bare selection change. A falsifier that
only half-undoes the fix proves nothing, and this one nearly shipped.
"""

import json
import subprocess
import sys
from pathlib import Path

API = Path(__file__).parent
WEB = API.parent / "web"

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, bool(ok), detail))


# The shared mount preamble — jsdom + React + the real ProseCanvas, the same
# harness `test_adr571_text_app.py` uses for its canvas probes.
_PRE = r"""
const fs = require('fs'); const path = require('path');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
require.extensions['.tsx'] = require.extensions['.ts'] = function (m, f) {
  m._compile(transform(fs.readFileSync(f,'utf8'),{transforms:['typescript','jsx','imports'],jsxRuntime:'automatic',production:true}).code, f);
};
const Module = require('module'); const orig = Module._resolveFilename;
Module._resolveFilename = function (r, ...a) {
  if (r.startsWith('@/')) { const b = path.join(WEB, r.slice(2));
    for (const e of ['', '.tsx', '.ts']) { try { return orig.call(this, b + e, ...a); } catch (x) {} } }
  return orig.call(this, r, ...a);
};
const { JSDOM } = require(WEB + '/node_modules/jsdom');
const dom = new JSDOM('<!doctype html><body><div id="h"></div></body>', { pretendToBeVisual: true });
const def = (k, v) => Object.defineProperty(globalThis, k, { value: v, configurable: true, writable: true });
for (const k of ['window','document','HTMLElement','Element','Node','Range','DOMParser',
                 'getComputedStyle','requestAnimationFrame','cancelAnimationFrame','MutationObserver'])
  def(k, dom.window[k]);
def('navigator', dom.window.navigator);
def('ResizeObserver', class { observe(){} unobserve(){} disconnect(){} });
def('IS_REACT_ACT_ENVIRONMENT', true);
const React = require(WEB + '/node_modules/react');
const { createRoot } = require(WEB + '/node_modules/react-dom/client');
const { act } = React;
const { ProseCanvas } = require(WEB + '/components/text/ProseCanvas.tsx');
const host = dom.window.document.getElementById('h');
"""


def _probe(script: str) -> dict:
    try:
        return json.loads(
            subprocess.run(
                ["node", "-e", _PRE + script, str(WEB), str(WEB / "node_modules" / "sucrase")],
                capture_output=True, text=True, timeout=180, check=True,
            ).stdout
        )
    except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate
        return {"error": str(exc)}


# ── 1 + 2. the table: rendered, editable, and writing back ───────────────
_TABLE = r"""
const DOC = 'intro\n\n| Milestone | Target |\n| --- | --- |\n'
  + '| Pre-seed | $750K |\n| Seed | $3.5M |\n\ntail\n';
let value = DOC, handle = null;
act(() => createRoot(host).render(React.createElement(ProseCanvas, {
  value, onChange: (v) => { value = v; }, handleRef: (h) => { if (h) handle = h; },
})));
const q = (s) => host.querySelectorAll(s).length;
const cell = (r, c) =>
  host.querySelector(`.cm-mdTable [data-row="${r}"][data-col="${c}"]`);

const rendered = q('table.cm-mdTable') === 1;

// ── D1: the caret INSIDE the table changes nothing ──
const inside = DOC.indexOf('| Pre-seed') + 4;
act(() => handle.reveal(inside, inside));
const stillRendered = q('table.cm-mdTable') === 1;
// No line decoration may have replaced the grid, under ANY spelling.
const noSourceLines = q('.cm-line[class*="ableSource"]') === 0;
const docUntouchedByCaret = value === DOC;

// ── D2: every cell is a text field, addressed by row/col ──
const cells = [...host.querySelectorAll('.cm-mdTable th, .cm-mdTable td')];
const allEditable = cells.length === 6
  && cells.every((c) => c.getAttribute('contenteditable') === 'plaintext-only');
const addressed = cells.every(
  (c) => c.dataset.row !== undefined && c.dataset.col !== undefined);

// ── D2: EDITING A CELL WRITES MARKDOWN BACK. The claim that matters. ──
// A body cell (row 1 = the first data row) gets new text and blurs.
const target = cell(1, 1);
target.textContent = '$900K';
act(() => target.dispatchEvent(new dom.window.Event('blur')));
const wroteBack = value.includes('| Pre-seed | $900K |');
const oldGone = !value.includes('$750K');
// The table must still be a table: same shape, delimiter intact, tail kept.
const shapeKept = value.includes('| --- | --- |')
  && value.includes('| Seed | $3.5M |')
  && value.startsWith('intro\n\n')
  && value.trimEnd().endsWith('tail');
// A HEADER cell is editable too (row 0) — it is content, not machinery.
const head = cell(0, 1);
head.textContent = 'Amount';
act(() => head.dispatchEvent(new dom.window.Event('blur')));
const headerWroteBack = value.includes('| Milestone | Amount |');

// ── D2: a blur with NO change writes nothing (no empty undo step) ──
const before = value;
const idle = cell(1, 0);
act(() => idle.dispatchEvent(new dom.window.Event('blur')));
const noopBlur = value === before;

// ── D2: a `|` typed into a cell is escaped, and survives the round trip ──
const piped = cell(2, 0);
piped.textContent = 'Seed | extended';
act(() => piped.dispatchEvent(new dom.window.Event('blur')));
const escaped = value.includes('Seed \\| extended');
// ...and re-parses to ONE cell, not two — the row still has 2 columns.
const reparsedCells = [...host.querySelectorAll('.cm-mdTable tbody tr')]
  .map((tr) => tr.cells.length);
const stillTwoWide = reparsedCells.every((n) => n === 2);

console.log(JSON.stringify({
  rendered, stillRendered, noSourceLines, docUntouchedByCaret,
  allEditable, addressed,
  wroteBack, oldGone, shapeKept, headerWroteBack, noopBlur,
  escaped, stillTwoWide,
}));
"""
_t = _probe(_TABLE)

check("1a D1 — a table renders as a real <table>",
      _t.get("rendered") is True, str(_t)[:300])
check("1b ⭐ D1 — the caret INSIDE the table does NOT reveal its source. This "
      "is D14.a's ruling ('i don't want the hashtags visible') finally applied "
      "to the one construct D15 shipped without it — the operator's "
      "'when clicked on its the raw style and i want to edit on the render style'",
      _t.get("stillRendered") is True, str(_t)[:300])
check("1c ⭐ D1 — no line decoration replaced the grid, under any spelling. "
      "Driven, not grepped: the first version of this check matched its own "
      "explanatory comment naming the deleted class",
      _t.get("noSourceLines") is True, str(_t)[:300])
check("1d D1 — moving the caret writes nothing to the document",
      _t.get("docUntouchedByCaret") is True, str(_t)[:300])

check("2a ⭐ D2 — every rendered cell IS a text field (contenteditable), which "
      "is the whole Notion property: you type into the rendered thing because "
      "the rendered thing is the document",
      _t.get("allEditable") is True, str(_t)[:300])
check("2b D2 — each cell carries its row/col, so an edit knows which source "
      "row to rewrite",
      _t.get("addressed") is True, str(_t)[:300])
check("2c ⭐⭐⭐ D2 — EDITING A CELL WRITES MARKDOWN BACK. The claim that "
      "matters, and the one a contenteditable check passes over: a widget can "
      "accept every keystroke and drop them all. Executed against a mounted "
      "canvas and asserted on the DOCUMENT BYTES",
      _t.get("wroteBack") is True and _t.get("oldGone") is True, str(_t)[:300])
check("2d D2 — the rest of the table and the prose around it are untouched by "
      "a cell edit (delimiter intact, sibling row intact, tail kept)",
      _t.get("shapeKept") is True, str(_t)[:300])
check("2e D2 — a HEADER cell writes back too; a header is content, not "
      "machinery. (The delimiter row is the machinery, and it is never a cell)",
      _t.get("headerWroteBack") is True, str(_t)[:300])
check("2f D2 — a blur with no change writes NOTHING, so tabbing through a "
      "table does not push empty transactions onto the undo stack",
      _t.get("noopBlur") is True, str(_t)[:300])
check("2g ⭐ D2 — a `|` typed into a cell is ESCAPED on the way out. Without "
      "this an ordinary edit silently splits one cell into two and the table "
      "restructures itself under the member",
      _t.get("escaped") is True, str(_t)[:300])
check("2h ⭐ D2 — ...and the escaped cell re-parses as ONE cell: the round "
      "trip is closed, not merely half-written",
      _t.get("stillTwoWide") is True, str(_t)[:300])


# ── 3. the fences (D3) ───────────────────────────────────────────────────
_FENCE = r"""
const DOC = 'before\n\n```mermaid\ngraph TD\n  A[Start] --> B[Next]\n```\n\n'
  + 'between\n\n```js\nconst x = 1;\n```\n\nafter\n';
let value = DOC, handle = null;
act(() => createRoot(host).render(React.createElement(ProseCanvas, {
  value, onChange: (v) => { value = v; }, handleRef: (h) => { if (h) handle = h; },
})));
const q = (s) => host.querySelectorAll(s).length;

// A mermaid fence is claimed by the diagram widget; a code fence is styled
// lines whose text stays editable in place (its content IS its source).
const diagram = q('.cm-mdDiagram') === 1;
const codeStyled = q('.cm-line.cm-mdCode') > 0;
const langLabel = [...host.querySelectorAll('.cm-mdCodeLang')]
  .map((e) => e.textContent).includes('js');
// The raw fence text must NOT be sitting in the prose. Before D3 the canvas
// rendered no fence at all, so the word "mermaid" and the graph definition
// read as serif body copy — the operator's screenshot.
const content = host.querySelector('.cm-content').textContent;
const rawGone = !content.includes('```');

// ── D3 — the caret does NOT open a diagram (D1 holds here too) ──
const at = DOC.indexOf('graph TD') + 2;
act(() => handle.reveal(at, at));
const caretKeptDiagram = q('.cm-mdDiagram') === 1 && q('.cm-line.cm-mdFenceOpen') === 0;

// ── D3 — the DECLARED gesture does open it ──
const btn = host.querySelector('.cm-mdDiagramEdit');
const hasAffordance = !!btn;
act(() => btn.dispatchEvent(new dom.window.MouseEvent('mousedown', { bubbles: true })));
const opened = q('.cm-line.cm-mdFenceOpen') > 0;
const docUntouched = value === DOC;

console.log(JSON.stringify({
  diagram, codeStyled, langLabel, rawGone,
  caretKeptDiagram, hasAffordance, opened, docUntouched,
}));
"""
_f = _probe(_FENCE)

check("3a ⭐ D3 — a ```mermaid fence renders AS A DIAGRAM. Before this the "
      "canvas rendered no fence at all: the operator's screenshot shows the "
      "bare word 'mermaid' and a graph definition set in serif body copy, "
      "because nothing claimed them",
      _f.get("diagram") is True, str(_f)[:300])
check("3b D3 — a code fence renders as one styled block, and its language "
      "shows as a label where ```lang used to read",
      _f.get("codeStyled") is True and _f.get("langLabel") is True, str(_f)[:300])
check("3c D3 — no ``` fence punctuation is left sitting in the prose",
      _f.get("rawGone") is True, str(_f)[:300])
check("3d ⭐ D3 — the caret entering a diagram does NOT open its source. D1's "
      "rule holds here: the ban is on the INCIDENTAL gesture (clicking where "
      "you meant to read), never on a control the member pressed",
      _f.get("caretKeptDiagram") is True, str(_f)[:300])
check("3e ⭐ D3 — a diagram carries an explicit edit affordance, and pressing "
      "it opens that block's source. A diagram's source is a different "
      "LANGUAGE from its picture, so no in-place gesture can edit it — this is "
      "the one genuine exception in ADR-590, and it is an exception to HOW the "
      "source is reached, never to whether the caret reaches it",
      _f.get("hasAffordance") is True and _f.get("opened") is True, str(_f)[:300])
check("3f D3 — opening a diagram for editing writes NOTHING to the document: "
      "reveal is view state, not content",
      _f.get("docUntouched") is True, str(_f)[:300])


# ── 4. the model boundary still holds (ADR-456 D1) ───────────────────────
_SRC = (WEB / "components" / "text" / "ProseCanvas.tsx").read_text()
check("4a ⭐ ADR-456 D1 — an EDITABLE widget is still not a block model. The "
      "document is CodeMirror's plain string: nothing here mints an id, and no "
      "`data-block-id` enters the text. (ADR-590 §2 records that the opposite "
      "reading — that D1 bans writing back — has now been caught three times "
      "in this app: ADR-572 D8, D13, and the docstring this arc replaced.)",
      "data-block-id" not in _SRC and "blockId" not in _SRC, "")
check("4b ⭐ D2 — a cell edit dispatches over the table's OWN range and "
      "re-emits the whole table. A per-cell character splice would have to "
      "reason about the delimiter row, which the member never edits",
      "serializeTable(rows)" in _SRC and "view.dispatch" in _SRC, "")


# ── report ───────────────────────────────────────────────────────────────
_failed = [r for r in results if not r[1]]
for label, ok, detail in results:
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  {detail}"))
print(
    f"ADR-590 gate {'GREEN' if not _failed else 'FAILED'} — "
    f"{len(results) - len(_failed)}/{len(results)}"
)
sys.exit(1 if _failed else 0)
