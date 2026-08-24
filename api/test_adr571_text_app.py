"""ADR-571 gate — the Text app is a real app, not a registry row.

Script-style (`python3 test_adr571_text_app.py`) like its neighbours —
under pytest these report a false pass, so run them directly.

The claims, at the altitudes they can actually fail:

1. RESIDENCY, by real resolution — `register_app("text", …)` resolves to a
   live resident and displays "Editor". Executed, not grepped.
2. THE POSTURE BRANCH IS REACHED — `lane_meta.app == "text"` selects
   `build_text_posture`. This is the one that matters: without the branch a
   text lane falls through to `build_studio_posture`, which lifts
   `data-template` from an .md (there is none), silently resolves to
   `document`, and hands the colleague an HTML-BLOCK contract for a
   markdown file. Asserted by AST on the branch, and by CALLING the posture.
3. THE SURFACE IS NAVIGABLE — a kernel row with a route, and the FE union +
   array carry the slug (the ADR-297 three-way parity, restated narrowly so
   a Text-specific regression names itself).
4. THE INLINE EDITOR IS GONE — ADR-571 D2 retires ADR-570's housing. One
   editor, one home: the registry may not carry a `markdown.editor` row and
   the module may not come back.
"""

import ast
import re
import sys
from pathlib import Path

API = Path(__file__).parent
WEB = API.parent / "web"

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, bool(ok), detail))


# ── 1. residency, executed ───────────────────────────────────────────────
import services.apps  # noqa: E402,F401  (registration side-effect)
from services.authoring import resident_for_app, resolve_app  # noqa: E402

_resident = resident_for_app("text")
check("1a the text app resolves a resident (create_lane would 422 otherwise)", bool(_resident))
from services.agents_registry import get_agent  # noqa: E402

# Re-anchored for ADR-597 D2 + ADR-598: the member reads "Editor" — supplied
# by the resident's own character row (Editor is Text's APP RESIDENT, on no
# hire roster). Resolution goes through the ONE namespace (`get_agent`), the
# same door the lane runner uses — the check must not re-derive which
# register a slug lives in.
_char = get_agent(_resident) or {}
check(
    "1b the colleague displays as Editor (app name or the character's own)",
    ((resolve_app("text") or {}).get("name") or _char.get("name")) == "Editor",
    f"app={resolve_app('text')} char={_char.get('name')}",
)

check(
    "1c the resident is a REAL character row (engine follows it, ADR-562)",
    bool(_char.get("model")),
    f"resident={_resident}",
)


# ── 2. the posture branch is reached, and it speaks prose ────────────────
def _fn(module: Path, name: str):
    for node in ast.walk(ast.parse(module.read_text())):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {module}")


def _selects_text_posture(fn) -> bool:
    """An `if/elif` whose test compares the app to 'text' and whose body
    calls build_text_posture. Branch extraction, never a source grep — a
    comment mentioning the app would satisfy a grep."""
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        consts = {
            c.value for c in ast.walk(node.test)
            if isinstance(c, ast.Constant) and isinstance(c.value, str)
        }
        if "text" not in consts:
            continue
        called = {
            getattr(c.func, "id", None) or getattr(c.func, "attr", None)
            for c in ast.walk(ast.Module(body=node.body, type_ignores=[]))
            if isinstance(c, ast.Call)
        }
        if "build_text_posture" in called:
            return True
    return False


check(
    "2a lane_meta.app=='text' selects the Text posture (else the studio "
    "fallback hands an HTML-block contract to a markdown lane)",
    _selects_text_posture(_fn(API / "services" / "lane_runner.py", "build_lane_conventions")),
)

from services.apps.text import build_text_posture  # noqa: E402

_posture = build_text_posture(None, "u", "/workspace/marketing/notes.md")
check("2b the posture names the bound document", "marketing/notes.md" in _posture)
check(
    "2c the posture forbids Studio machinery (plain markdown, whole writes)",
    "no HTML" in _posture and "no block ids" in _posture,
)


# ── 3. the surface is navigable, BE and FE agree ─────────────────────────
from services.kernel_surfaces import KERNEL_SURFACES  # noqa: E402

_row = next((s for s in KERNEL_SURFACES if s.get("slug") == "text"), None)
check("3a a kernel surface row exists", _row is not None)
check("3b it is navigable (a route, so the compositor serves it)", bool((_row or {}).get("route")))
check(
    "3c it is unveiled (primary tier + Dock, ADR-571 D1)",
    (_row or {}).get("launcher_tier") == "primary" and (_row or {}).get("default_pinned") is True,
)

_desk = (WEB / "types" / "desk.ts").read_text()
check("3d the FE union carries the slug", "| 'text'" in _desk)
check("3e the FE runtime array carries the slug", "'text'," in _desk)
check(
    "3f the surface component is registered (an unregistered slug renders nothing)",
    "text: TextPage" in (WEB / "components" / "shell" / "SurfaceRegistry.tsx").read_text(),
)
check(
    "3g the route file exists",
    (WEB / "app" / "(authenticated)" / "text" / "page.tsx").exists(),
)
check(
    "3h its params are registered at birth (an unregistered slug gets the "
    "permissive default — absence read as permission)",
    "text: ['file']" in (WEB / "lib" / "shell" / "surface-preferences.ts").read_text(),
)

# The claim that routes a .md THERE — EXECUTED. Grepping the source cannot
# see this: a narrowing that leaves the explanatory comment behind reads as
# green (caught by this gate's own falsification run, 2026-08-15). The two
# functions are transpiled and CALLED, so only real behavior passes.
_ROUTING_PROBE = r"""
// Transpiled by SUCRASE (the repo's own dependency), never hand-stripped:
// a regex approximation of TypeScript is its own source of false reds.
const { transform } = require(process.argv[2]);
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const js = transform(src, { transforms: ['typescript', 'imports'] }).code;
const mod = { exports: {} };
new Function('module', 'exports', 'require', js)(mod, mod.exports, () => ({}));
const { isArtifactCandidate, resolveSurfaceApplication } = mod.exports;
const surfaceOf = (p) => (resolveSurfaceApplication(p) || {}).surface || null;
const out = {
  prose_is_candidate: isArtifactCandidate('/workspace/marketing/notes.md'),
  prose_routes_text: surfaceOf('/workspace/marketing/notes.md') === 'text',
  txt_routes_text: surfaceOf('/workspace/Documents/log.txt') === 'text',
  arrival_not_claimed: surfaceOf('/workspace/inbound/mcp/observed.md') === null,
  machine_leaf_not_claimed: surfaceOf('/workspace/x/_feedback.md') === null,
  html_still_authoring: ['docs', 'studio', 'images'].includes(surfaceOf('/workspace/x/document.html')),
  image_unclaimed: surfaceOf('/workspace/x/shot.png') === null,
};
console.log(JSON.stringify(out));
"""

import json  # noqa: E402
import subprocess  # noqa: E402

try:
    _probe = json.loads(
        subprocess.run(
            [
                "node", "-e", _ROUTING_PROBE,
                str(WEB / "lib" / "file-types" / "index.ts"),
                str(WEB / "node_modules" / "sucrase"),
            ],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate, never a skip
    _probe = {"error": str(exc)}

check("3i prose passes the candidate pre-check (else the claim is unreachable)",
      _probe.get("prose_is_candidate") is True, str(_probe))
check("3j a .md routes to the Text surface", _probe.get("prose_routes_text") is True, str(_probe))
check("3k a .txt routes there too", _probe.get("txt_routes_text") is True, str(_probe))
check("3l an ARRIVAL is never claimed (a retained observation is not a canvas)",
      _probe.get("arrival_not_claimed") is True, str(_probe))
check("3m an `_`-leaf is never claimed (machine-tended state, ADR-254)",
      _probe.get("machine_leaf_not_claimed") is True, str(_probe))
check("3n .html still routes to its authoring app (the prose claim did not steal it)",
      _probe.get("html_still_authoring") is True, str(_probe))
check("3o a non-document is still unclaimed", _probe.get("image_unclaimed") is True, str(_probe))


# ── 4. one editor, one home (ADR-571 D2 retires ADR-570's housing) ───────
check(
    "4a the inline editor module is deleted",
    not (WEB / "components" / "workspace" / "viewers" / "MarkdownEditor.tsx").exists(),
)
_apps = (WEB / "lib" / "file-types" / "apps.tsx").read_text()
check("4b no markdown.editor registry row", "markdown.editor" not in _apps)
check(
    "4c the viewer contract is view-only again (no edit mode on a renderer)",
    "mode?: 'view' | 'edit'" not in _apps,
)


# ── 5. the app has DOCS' SHAPE, not a sketch of it ───────────────────────
# The first cut shipped a bare heading + a text list and read as unfinished
# beside Docs. These assert the affordances that make a document app a peer
# of Docs rather than a placeholder — the ones a member would go looking for.
_TEXT = WEB / "components" / "text"


def _strip_comments(src: str) -> str:
    """Code only. An assertion that reads comments can match its own
    explanatory prose — the trap this repo keeps re-learning, and which
    check 5k hit while being written (the header says "does NOT ride
    DeskHousing" and a whole-file grep read that as the violation)."""
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)


_landing = _strip_comments((_TEXT / "TextSurface.tsx").read_text())
_editor = _strip_comments((_TEXT / "TextEditor.tsx").read_text())

check("5a the landing offers Open (the File-menu pair, not New alone)",
      "OpenArtifactModal" in _landing and ">\n              Open\n" in _landing)
check("5b recents are a THUMBNAIL GRID, not a text list",
      "grid-cols-2" in _landing and "ProseThumb" in _landing)
check("5c each card carries the ⋯ / right-click organize menu",
      "useFileContextMenu" in _landing and "onContextMenu" in _landing)
check("5d creation is a NAMING DIALOG, never window.prompt",
      "NameDocumentModal" in _landing and "window.prompt" not in _landing)
check("5e the open state has a crumb that renames the document",
      "onRename" in _editor and "click to rename" in _editor)
check("5f the boundary acts are present (Share opens the ONE shared dialog)",
      "ShareDialog" in _editor and "TextExport" in _editor)
check("5g the rail is Properties | Chat, the Docs grammar",
      "'properties', 'Properties'" in _editor and "'chat', 'Chat'" in _editor)
check("5h the lane stays MOUNTED across a tab switch (a streaming turn survives)",
      "rightTab === 'chat' ? 'flex' : 'hidden'" in _editor)
# 5i re-anchored 2026-08-22: the "Properties and chat" copy left with the
# b58ea08 pane-contract recut (found pre-existing red, hidden by a
# node_modules-less baseline). The MECHANISM is the check: at overlay rungs
# the rail renders as an absolute overlay gated on sideOpen — reachable,
# dismissible, never an inescapable state.
check("5i the rail is reachable at narrow rungs (never an inescapable state)",
      "sideIsOverlay" in _editor and "sideOpen ? 'flex' : 'hidden'" in _editor)
check("5j exactly ONE <main> landmark (the nested-main defect that clipped "
      "the rail when Text rode the dashboard housing)",
      _editor.count("<main") == 1 and _landing.count("<main") == 0)
check("5k Text does NOT ride DeskHousing (that is the DASHBOARD housing)",
      "DeskHousing" not in _landing and "DeskHousing" not in _editor)
check("5l the superseded canvas is deleted (no dual approach)",
      not (_TEXT / "TextCanvas.tsx").exists())

# The landing's recents request must be INSIDE the route's own cap. Found in
# production: the surface asked for 80, the route caps at 50, every load 422'd
# and the landing rendered "No documents yet" — a rejected request wearing an
# empty state's clothes. Read the cap from the ROUTE, never restate it.
_route_src = (API / "routes" / "workspace.py").read_text()
_cap_m = re.search(
    r"async def get_recent_revisions[\s\S]{0,600}?limit:\s*int\s*=\s*Query\(\s*\d+\s*,[^)]*?le=(\d+)",
    _route_src,
)
_asked_m = re.search(r"\.recentRevisions\((\d+)\)", _landing)
check("5m the recents request is within the route's cap (a 422 reads as an "
      "empty landing, not as an error)",
      bool(_cap_m) and bool(_asked_m) and int(_asked_m.group(1)) <= int(_cap_m.group(1)),
      f"cap={_cap_m.group(1) if _cap_m else '?'} asked={_asked_m.group(1) if _asked_m else '?'}")


# ── 6. ADR-572: the depth that makes it a PEER of Docs, not a shell ──────
# §5 gates the SHAPE (a document app's chrome). These gate the DEPTH: the
# reading face, the source affordances, and — the load-bearing half — that
# none of it crossed into block grade. The pure edit functions are TRANSPILED
# AND CALLED, because a gate that greps for a symbol proves the symbol exists
# and nothing about what it does.
_reader = _strip_comments((_TEXT / "ProseReader.tsx").read_text())
_export = _strip_comments((_TEXT / "TextExport.tsx").read_text())

_canvas = _strip_comments((_TEXT / "ProseCanvas.tsx").read_text())

check("6a the canvas STYLES markdown in place (the headline gap: a brief must "
      "not read as a source dump)",
      "ProseCanvas" in _editor and "HighlightStyle" in _canvas
      and "syntaxHighlighting" in _canvas)
check("6b it reuses the ONE markdown pipeline (no second parser)",
      "react-markdown" not in _reader and "remark" not in _reader)
check("6c the reading face is a DOC skin, not the chat face",
      "prose-headings:font-serif" in _reader and "font-serif" in _reader)
# ADR-572 D8 — ONE canvas. The Read/Write toggle is DELETED: it hid every
# formatting control behind a mode the surface did not open in. This asserts
# the ABSENCE, so a future session cannot reintroduce the split quietly.
check("6d there is NO mode toggle — one always-editable canvas (D8)",
      "setMode(" not in _editor and "'read' | 'write'" not in _editor
      and "mode === 'read'" not in _editor)
check("6d1 the toolbar is ALWAYS mounted, never mode-gated",
      "<MarkdownToolbar onAction={runAction} />" in _editor
      and "mode ===" not in _editor)
check("6e zoom is a VIEW control with Docs' own clamp",
      "ZOOM_MIN = 0.25" in _editor and "ZOOM_MAX = 2" in _editor)
check("6f the markdown toolbar is mounted (Docs' Insert, in characters)",
      "MarkdownToolbar" in _editor)
check("6g search rides @codemirror/search inside the canvas; the hand-rolled "
      "bar is DELETED (no dual implementation)",
      "searchKeymap" in _canvas
      and not (_TEXT / "FindReplaceBar.tsx").exists()
      and "FindReplaceBar" not in _editor)
check("6h the Properties pane carries the OUTLINE (ADR-526 D2's home)",
      "parseOutline" in _editor and "No headings yet" in _editor)
check("6i Print/PDF is offered over the RENDERED document",
      "printProse" in _export and "Print / PDF" in _export)
check("6j the single-pane rung has a bottom tab bar at the touch floor",
      "singlePane" in _editor and "min-h-[44px]" in _editor)
# The retry must be a REACHABLE ACT in the load-error branch, not a phrase.
# The first spelling of this check pinned the copy "the request failed" and
# went red because JSX had wrapped it across a newline — the assertion was
# testing the prettier config, not the affordance (the "never pin a spelling"
# trap, hit a third time in this arc). What matters is that the error branch
# offers a control that re-runs the fetch.
_err_branch = re.search(r"\)\s*:\s*error\s*\?([\s\S]{0,900}?)\)\s*:", _editor)
check("6k a failed LOAD offers a retry that re-runs the fetch (never 'it "
      "does not exist', which reads as data loss)",
      bool(_err_branch)
      and "setReloadKey" in _err_branch.group(1)
      and "<button" in _err_branch.group(1),
      "no retry control found in the error branch")

# ── the constraint, gated: ADR-456 D1 grade ──────────────────────────────
# Text may never become block-grade. This is the check that must FAIL if a
# future session ports Studio machinery in, so it is spelled as an absence
# over the whole app directory, not over one file.
_all_text_src = "\n".join(
    _strip_comments(p.read_text())
    for p in sorted(_TEXT.glob("*.ts")) + sorted(_TEXT.glob("*.tsx"))
)
for _banned, _why in [
    ("data-block-id", "block identity"),
    ("data-block=", "block annotation"),
    ("StudioCanvas", "Studio canvas machinery"),
    ("FlowEditor", "the block-grade editor"),
    ("prosemirror", "a block document model"),
    ("resolveArtifactHtml", "the artifact projection"),
]:
    check(f"6L Text stays textarea-grade — no {_why} ({_banned})",
          _banned not in _all_text_src)

# The pure source-edit functions, EXECUTED. `markdownEdits` is deliberately
# React-free and total so this probe can call it directly: the file must stay
# a plain .md, so what these return IS the product claim.
_EDITS_PROBE = r"""
const { transform } = require(process.argv[2]);
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const js = transform(src, { transforms: ['typescript', 'imports'] }).code;
const mod = { exports: {} };
new Function('module', 'exports', 'require', js)(mod, mod.exports, () => ({}));
const M = mod.exports;
const out = {};

// Bold wraps, and toggles back OFF — round-trips to the original bytes.
const b1 = M.toggleWrap('hello world', 6, 11, '**');
out.bold_wraps = b1.text === 'hello **world**';
out.bold_selects_inner = b1.text.slice(b1.selectionStart, b1.selectionEnd) === 'world';
out.bold_untoggles = M.toggleWrap(b1.text, 8, 13, '**').text === 'hello world';

// Heading sets, and re-applying the SAME level clears it.
const h = M.toggleHeading('Title\nbody', 0, 3, 2);
out.heading_sets = h.text === '## Title\nbody';
out.heading_clears = M.toggleHeading(h.text, 0, 3, 2).text === 'Title\nbody';
out.heading_replaces_level = M.toggleHeading(h.text, 0, 3, 1).text === '# Title\nbody';

// Lists renumber from 1 and toggle off.
const l = M.toggleList('a\nb\nc', 0, 5, true);
out.ol_numbers = l.text === '1. a\n2. b\n3. c';
out.ol_untoggles = M.toggleList(l.text, 0, l.text.length, true).text === 'a\nb\nc';
out.ul_marks = M.toggleList('a\nb', 0, 3, false).text === '- a\n- b';

// Checklist — Docs' `checklist` kind, which markdown expresses NATIVELY (GFM
// task list) so it needs no annotation. The one Insert row that survives the
// medium translation intact.
const ck = M.toggleChecklist('a\nb', 0, 3);
out.checklist_marks = ck.text === '- [ ] a\n- [ ] b';
out.checklist_untoggles = M.toggleChecklist(ck.text, 0, ck.text.length).text === 'a\nb';
out.checklist_promotes_bullet = M.toggleChecklist('- x', 0, 3).text === '- [ ] x';
out.checklist_keeps_checked_on_clear = M.toggleChecklist('- [x] d', 0, 7).text === 'd';

// Quote toggles.
const q = M.toggleQuote('x\ny', 0, 3);
out.quote_marks = q.text === '> x\n> y';
out.quote_untoggles = M.toggleQuote(q.text, 0, q.text.length).text === 'x\ny';

// Link keeps the selection as the TEXT and puts the caret in the target.
const lk = M.insertLink('see docs here', 4, 8);
out.link_shape = lk.text === 'see [docs]() here';
out.link_caret_in_target = lk.text[lk.selectionStart - 1] === '(';

// Table is GFM, on its own lines.
const t = M.insertTable('para', 4, 4);
out.table_is_gfm = t.text.includes('| --- | --- |') && t.text.includes('\n\n|');

// ADR-572 D8 — the hand-rolled find/replace is DELETED; `@codemirror/search`
// owns it inside the canvas. Assert the ABSENCE so it cannot creep back as a
// second implementation beside CodeMirror's.
out.no_local_find = typeof M.findAll === 'undefined'
  && typeof M.replaceAll === 'undefined' && typeof M.replaceOne === 'undefined';

// Line offsets — the outline's addressing.
out.offset_first = M.offsetOfLine('aa\nbb\ncc', 0) === 0;
out.offset_third = M.offsetOfLine('aa\nbb\ncc', 2) === 6;

console.log(JSON.stringify(out));
"""

_OUTLINE_PROBE = r"""
const { transform } = require(process.argv[2]);
const src = require('fs').readFileSync(process.argv[1], 'utf8');
const js = transform(src, { transforms: ['typescript', 'imports'] }).code;
const mod = { exports: {} };
new Function('module', 'exports', 'require', js)(mod, mod.exports, () => ({}));
const { parseOutline, readingMinutes } = mod.exports;

const doc = [
  '# Title', '', 'body text', '',
  '## Section one', '', '```sh', '# not a heading', '```', '',
  '### Deep', '', 'Setext H2', '---------', '', '#nothashheading', '',
  '## **Bold** section', '',
].join('\n');
const o = parseOutline(doc);
const out = {
  levels: o.map((h) => h.level),
  texts: o.map((h) => h.text),
  // The ADDRESS is a source line — a coordinate, never an annotation.
  lines_are_numbers: o.every((h) => Number.isInteger(h.line)),
  first_line: o[0] && o[0].line === 0,
  fence_skipped: !o.some((h) => h.text === 'not a heading'),
  needs_space: !o.some((h) => h.text === 'hashheading'),
  setext_found: o.some((h) => h.text === 'Setext H2' && h.level === 2),
  markup_stripped: o.some((h) => h.text === 'Bold section'),
  empty_doc: parseOutline('').length === 0,
  reading_floor: readingMinutes(0) === 1,
  reading_scales: readingMinutes(2380) === 10,
};
console.log(JSON.stringify(out));
"""


def _run_probe(script: str, target: Path) -> dict:
    try:
        return json.loads(
            subprocess.run(
                ["node", "-e", script, str(target), str(WEB / "node_modules" / "sucrase")],
                capture_output=True, text=True, timeout=30, check=True,
            ).stdout
        )
    except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate
        return {"error": str(exc)}


_edits = _run_probe(_EDITS_PROBE, _TEXT / "markdownEdits.ts")
for _key, _label in [
    ("bold_wraps", "6m bold WRAPS the selection in markdown characters"),
    ("bold_selects_inner", "6n the selection survives the wrap"),
    ("bold_untoggles", "6o bold toggles OFF — the bytes round-trip exactly"),
    ("heading_sets", "6p a heading is set as ATX source"),
    ("heading_clears", "6q re-applying the same level clears it"),
    ("heading_replaces_level", "6r a different level replaces, never stacks"),
    ("ol_numbers", "6s an ordered list renumbers from 1"),
    ("ol_untoggles", "6t a list toggles off"),
    ("ul_marks", "6u a bulleted list marks each line"),
    ("checklist_marks", "6u1 a task list is GFM source (`- [ ] `), not a data-* block"),
    ("checklist_untoggles", "6u2 a task list toggles off to ordinary lines"),
    ("checklist_promotes_bullet", "6u3 an existing bullet promotes to a task"),
    ("checklist_keeps_checked_on_clear", "6u4 a CHECKED task clears too"),
    ("quote_marks", "6v quote marks each line"),
    ("quote_untoggles", "6w quote toggles off"),
    ("link_shape", "6x a link keeps the selection as its TEXT"),
    ("link_caret_in_target", "6y the caret lands in the empty target"),
    ("table_is_gfm", "6z a table is GFM source on its own lines"),
    ("no_local_find", "6aa the hand-rolled find/replace is DELETED — `@codemirror/search` owns it, and two searches would be a dual "
                      "implementation"),
    ("offset_first", "6ae line 0 is offset 0"),
    ("offset_third", "6af a later line resolves to its real offset"),
]:
    check(_label, _edits.get(_key) is True, str(_edits)[:200])

_out = _run_probe(_OUTLINE_PROBE, _TEXT / "outline.ts")
check("6ag the outline finds headings in document order",
      _out.get("levels") == [1, 2, 3, 2, 2], str(_out)[:200])
check("6ah headings are addressed by SOURCE LINE — a coordinate into the "
      "bytes, never a block id written into them (ADR-456 D1)",
      _out.get("lines_are_numbers") is True and _out.get("first_line") is True,
      str(_out)[:200])
check("6ai a `#` inside a fenced block is CODE, not a section",
      _out.get("fence_skipped") is True, str(_out)[:200])
check("6aj `#nospace` is not a heading (CommonMark)",
      _out.get("needs_space") is True, str(_out)[:200])
check("6ak setext headings are found", _out.get("setext_found") is True, str(_out)[:200])
check("6al inline markup is stripped for the label",
      _out.get("markup_stripped") is True, str(_out)[:200])
check("6am an empty document has an empty outline (never an invented one)",
      _out.get("empty_doc") is True, str(_out)[:200])
check("6an reading time floors at 1 min", _out.get("reading_floor") is True, str(_out)[:200])
check("6ao reading time scales at 238wpm", _out.get("reading_scales") is True, str(_out)[:200])


# ── 7. the reading face, RENDERED (ADR-572 D1) ───────────────────────────
# The headline claim of this arc is visual: a brief must read as a document,
# not as a source dump. No amount of source-grepping can assert that, so the
# real pipeline is mounted and its OUTPUT is inspected. This probe is what
# caught the scale collision below — it was invisible to `next build`, to
# tsc, and to every check in §6.
_RENDER_PROBE = r"""
const fs = require('fs'), path = require('path');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
require.extensions['.tsx'] = require.extensions['.ts'] = function (m, f) {
  m._compile(transform(fs.readFileSync(f, 'utf8'),
    { transforms: ['typescript', 'jsx', 'imports'], jsxRuntime: 'automatic', production: true }).code, f);
};
const Module = require('module'); const orig = Module._resolveFilename;
Module._resolveFilename = function (r, ...a) {
  if (r.startsWith('@/')) {
    const b = path.join(WEB, r.slice(2));
    for (const e of ['', '.tsx', '.ts', '/index.tsx', '/index.ts']) {
      try { return orig.call(this, b + e, ...a); } catch (x) { /* next */ }
    }
  }
  return orig.call(this, r, ...a);
};
const { renderToStaticMarkup } = require(WEB + '/node_modules/react-dom/server');
const React = require(WEB + '/node_modules/react');
const { MarkdownRenderer } = require(WEB + '/components/shared/MarkdownRenderer.tsx');
// The REAL reading-face component, not a hand-assembled stand-in. An earlier
// spelling of this probe called MarkdownRenderer directly with
// `scale:'inherit'` — so it asserted its own argument and stayed green when
// ProseReader stopped passing the prop (caught by falsification, 2026-08-16).
// Rendering ProseReader is what makes 7n a check on the WIRING.
const { ProseReader, PROSE_READING_SKIN } = require(WEB + '/components/text/ProseReader.tsx');
const R = (p) => renderToStaticMarkup(React.createElement(MarkdownRenderer, p));

const brief = [
  '# Creative Brief', '', 'This is **not** a block model. It is _plain markdown_.', '',
  '## Positioning', '', '| Medium | Currency |', '| --- | --- |', '| Text | .md |', '',
  '---', '', '> The round-trip is the thesis.', '', '- One', '- Two', '',
  '```sh', '# not a heading', '```', '',
  '- [ ] open task', '- [x] done task', '',
].join('\n');
const doc = renderToStaticMarkup(React.createElement(ProseReader, { text: brief }));
const chat = R({ content: '# h\n\n| a |\n| - |\n| b |' });

console.log(JSON.stringify({
  h1: /<h1[^>]*>Creative Brief<\/h1>/.test(doc),
  h2: /<h2[^>]*>Positioning<\/h2>/.test(doc),
  strong: /<strong>not<\/strong>/.test(doc),
  em: /<em>plain markdown<\/em>/.test(doc),
  table: /<table/.test(doc) && /<th[^>]*>Medium/.test(doc),
  hr: /<hr/.test(doc),
  quote: /<blockquote/.test(doc),
  list: /<ul>/.test(doc) && /<li>One<\/li>/.test(doc),
  fence_literal: doc.includes('# not a heading'),
  // A GFM task list must reach the reading face as REAL checkboxes, with the
  // checked state carried — otherwise `- [ ] ` reads as literal punctuation.
  tasklist: /<input[^>]*type="checkbox"/.test(doc) && /checked/.test(doc),
  no_raw_hash: !/>#\s*Creative/.test(doc),
  no_raw_stars: !doc.includes('**not**'),
  // The skin the canvas, the thumbnail and print all share — asserted as an
  // export so it cannot quietly become a per-mount literal.
  serif: /prose-headings:font-serif/.test(doc)
         && /prose-headings:font-serif/.test(PROSE_READING_SKIN),
  // The scale collision: the doc face must not carry the chat face's
  // font-size classes, because two font-size rules on one element resolve by
  // STYLESHEET order, not class order.
  doc_no_chat_scale: !/\bprose-sm\b/.test(doc) && !/prose-td:text-xs/.test(doc),
  doc_has_base: /\bprose-base\b/.test(doc),
  // ...and every pre-existing chat mount must be untouched by that change.
  chat_keeps_sm: /\bprose-sm\b/.test(chat),
  chat_keeps_td_xs: /prose-td:text-xs/.test(chat),
  compact_keeps_tight: /prose-p:my-0\.5/.test(R({ content: 'x', compact: true })),
}));
"""

try:
    _r = json.loads(
        subprocess.run(
            ["node", "-e", _RENDER_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=120, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate
    _r = {"error": str(exc)}

for _key, _label in [
    ("h1", "7a a `# ` line renders as an H1, not as visible source"),
    ("h2", "7b `## ` renders as an H2"),
    ("strong", "7c `**bold**` renders as <strong>"),
    ("em", "7d `_italic_` renders as <em>"),
    ("table", "7e a GFM table renders as a real <table>"),
    ("hr", "7f `---` renders as a rule"),
    ("quote", "7g `>` renders as a blockquote"),
    ("list", "7h `- ` renders as a list"),
    ("fence_literal", "7i a fenced block keeps its literal text"),
    ("tasklist", "7i1 a GFM task list renders as REAL checkboxes, checked "
                 "state carried (Docs' `checklist` kind, with no annotation)"),
    ("no_raw_hash", "7j no raw `#` survives into the reading face"),
    ("no_raw_stars", "7k no raw `**` survives into the reading face"),
    ("serif", "7L the document reading skin is actually applied"),
    ("doc_has_base", "7m the doc face sets a document type scale"),
]:
    check(_label, _r.get(_key) is True, str(_r)[:220])

check("7n the doc face carries NO chat scale class — two font-size rules on "
      "one element resolve by STYLESHEET order, so an override that wins by "
      "luck is a defect that has not fired yet (measured 2026-08-16)",
      _r.get("doc_no_chat_scale") is True, str(_r)[:220])
check("7o the ~20 existing chat mounts keep their face byte-for-byte "
      "(scale='chat' is the default; the new prop is opt-IN)",
      _r.get("chat_keeps_sm") is True
      and _r.get("chat_keeps_td_xs") is True
      and _r.get("compact_keeps_tight") is True,
      str(_r)[:220])


# ── 8. the CAS conflict, read off the REAL wire (ADR-572 D7) ─────────────
# Found by driving a real 409 in production on 2026-08-16. The API serves the
# stale-write detail under `error.hint.current_head`; this client read only
# FastAPI's older `detail.current_head`, so BOTH fields came back undefined:
# the banner said the generic "Someone else" instead of naming who moved the
# head, and the "Save mine over theirs" button VANISHED (it is conditional on
# currentHeadId) — leaving one exit where the design promises two.
#
# Invisible to types, to `next build`, and to all 103 prior checks: a field
# read that yields `undefined` is not an error, and the fallback string reads
# like intended copy. So the probe replays the VERBATIM body from the wire.
_CONFLICT_PROBE = r"""
const fs = require('fs'), path = require('path');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
require.extensions['.tsx'] = require.extensions['.ts'] = function (m, f) {
  m._compile(transform(fs.readFileSync(f, 'utf8'),
    { transforms: ['typescript', 'jsx', 'imports'], jsxRuntime: 'automatic', production: true }).code, f);
};
const Module = require('module'); const orig = Module._resolveFilename;
Module._resolveFilename = function (r, ...a) {
  if (r.startsWith('@/')) {
    const b = path.join(WEB, r.slice(2));
    for (const e of ['', '.tsx', '.ts', '/index.tsx', '/index.ts']) {
      try { return orig.call(this, b + e, ...a); } catch (x) { /* next */ }
    }
  }
  return orig.call(this, r, ...a);
};
const { readConflict } = require(WEB + '/components/text/conflict.ts');

// VERBATIM from production, 2026-08-16 (PATCH /api/workspace/file, stale base).
const live = {"error":{"code":"conflict","message":"Request failed.","hint":{
  "error":"stale_write","path":"/workspace/Documents/adr572-click-pass.md",
  "expected_head_version_id":"4e6c4f93-f168-4ae3-b1ab-2b690fd3b7b3",
  "current_head":{"id":"507258bf-dc88-442d-82ec-ba2e346b941a",
    "authored_by":"operator","message":"edit file","created_at":"2026-08-16T12:14:48Z"}}}};
// The older FastAPI shape, which must keep working.
const legacy = { detail: { current_head: { id: 'abc123', authored_by: 'operator' } } };

const a = readConflict(live);
const b = readConflict(legacy);
const empty = readConflict(null);
console.log(JSON.stringify({
  // The button's existence depends on this being non-null.
  live_head: a.currentHeadId === '507258bf-dc88-442d-82ec-ba2e346b941a',
  live_names_actor: !!a.actor && a.actor !== 'Someone else',
  legacy_head: b.currentHeadId === 'abc123',
  legacy_names_actor: !!b.actor && b.actor !== 'Someone else',
  // An unreadable body must still produce a usable banner, never a crash.
  empty_degrades: empty.currentHeadId === null && empty.actor === 'Someone else',
}));
"""

_c = _run_probe_web = None
try:
    _c = json.loads(
        subprocess.run(
            ["node", "-e", _CONFLICT_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate
    _c = {"error": str(exc)}

check("8a the CURRENT wire envelope yields the head id — the 'Save mine over "
      "theirs' button is conditional on it, so a miss DELETES an exit",
      _c.get("live_head") is True, str(_c)[:220])
check("8b the current envelope names WHO moved the head (not 'Someone else')",
      _c.get("live_names_actor") is True, str(_c)[:220])
check("8c the legacy `detail` envelope still reads (the shape is not this "
      "component's to pin; a reader that survives either cannot break again)",
      _c.get("legacy_head") is True and _c.get("legacy_names_actor") is True,
      str(_c)[:220])
check("8d an unreadable body degrades to a usable banner, never a crash",
      _c.get("empty_degrades") is True, str(_c)[:220])
check("8e the editor READS through that helper (not a re-inlined field access)",
      "readConflict(err.data)" in _editor and "detail?.current_head" not in _editor)


# ── 9. the ONE canvas is CodeMirror-grade, never block-grade (ADR-572 D8) ─
# The single canvas is what makes the app usable; THIS is what keeps it legal.
# ADR-456 D1 permits "textarea/CodeMirror-grade, never block-grade", and the
# whole distinction rests on one property: CodeMirror's document is a plain
# STRING and its styling is a decoration layer recomputed each update. A block
# editor stores a tree with identity and serializes it back out.
check("9a the canvas is CodeMirror, the grade ADR-456 D1 NAMES as permitted",
      "@codemirror/view" in _canvas and "@codemirror/state" in _canvas)
check("9b it holds a plain STRING — the doc is read out with toString(), never "
      "serialized from a node tree",
      "doc.toString()" in _canvas)
check("9c styling is a HIGHLIGHT layer over the source, not markup written "
      "into it (decorations are derived from offsets; nothing maps a rendered "
      "node back to a source position)",
      "HighlightStyle.define" in _canvas)

# The grade constraint, restated over the canvas specifically. §6L covers the
# whole directory; this names the block-editor packages that would be the
# tempting way to get a prettier canvas, and must never appear.
for _pkg in ("prosemirror", "@lexical", "slate", "tiptap", "milkdown"):
    check(f"9d the canvas is not a block editor — no {_pkg}", _pkg not in _canvas)

# The dependency floor, read from the REAL package.json: a block-editor
# package must not enter web/ through this app's door.
_pkg_json = json.loads((WEB / "package.json").read_text())
_deps = {**_pkg_json.get("dependencies", {}), **_pkg_json.get("devDependencies", {})}
check("9e @codemirror/lang-markdown is a real dependency (the highlighter is "
      "the markdown grammar, not a hand-rolled regex pass)",
      "@codemirror/lang-markdown" in _deps, str(sorted(_deps))[:200])

# The property that IS the product thesis, EXECUTED: a round-trip through the
# canvas's own state must return byte-identical text. Grepping cannot show
# this; a block model would fail it by normalizing the markup.
_CM_PROBE = r"""
const fs = require('fs'), path = require('path');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
require.extensions['.tsx'] = require.extensions['.ts'] = function (m, f) {
  m._compile(transform(fs.readFileSync(f, 'utf8'),
    { transforms: ['typescript', 'jsx', 'imports'], jsxRuntime: 'automatic', production: true }).code, f);
};
const Module = require('module'); const orig = Module._resolveFilename;
Module._resolveFilename = function (r, ...a) {
  if (r.startsWith('@/')) {
    const b = path.join(WEB, r.slice(2));
    for (const e of ['', '.tsx', '.ts', '/index.tsx', '/index.ts']) {
      try { return orig.call(this, b + e, ...a); } catch (x) { /* next */ }
    }
  }
  return orig.call(this, r, ...a);
};
const { EditorState } = require(WEB + '/node_modules/@codemirror/state');
const { markdown, markdownLanguage } = require(WEB + '/node_modules/@codemirror/lang-markdown');

// Awkward markdown a normalizing editor would "tidy": mixed bullets, trailing
// spaces, setext, a fence, tabs. Byte-identical out is the product thesis.
const src = [
  '# Title  ', '', 'Setext', '======', '',
  '*  star bullet', '+  plus bullet', '- [x] done', '',
  '\ttab-indented line', '', '```sh', '# not a heading', '```', '',
  'trailing spaces here   ', '',
].join('\n');
const st = EditorState.create({ doc: src, extensions: [markdown({ base: markdownLanguage })] });
const out = st.doc.toString();
// And an edit transaction leaves everything else untouched.
const st2 = st.update({ changes: { from: 0, to: 0, insert: 'X' } }).state;
console.log(JSON.stringify({
  round_trips: out === src,
  edit_is_surgical: st2.doc.toString() === 'X' + src,
  no_ids_added: !/data-block-id|data-block=/.test(out),
}));
"""
_cm = _run_probe_cm = None
try:
    _cm = json.loads(
        subprocess.run(
            ["node", "-e", _CM_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate
    _cm = {"error": str(exc)}

check("9f awkward markdown round-trips BYTE-IDENTICAL through the canvas's "
      "own state (mixed bullets, setext, tabs, trailing spaces, a fence) — "
      "a normalizing/block editor fails exactly here",
      _cm.get("round_trips") is True, str(_cm)[:220])
# 9f proves the LIBRARY does not normalize. This proves MY COMPONENT does not
# either — the distinction that matters, and the one 9f alone missed: a
# `.replace()` inside the updateListener passed 9f untouched (caught by this
# gate's own falsification run, 2026-08-16). The handler must hand the doc
# straight out.
_emit = re.search(r"updateListener\.of\(\((\w+)\) => \{(.*?)\}\)", _canvas, re.S)
check("9f1 the change handler emits the document UNMODIFIED — no normalizing "
      "rewrite between the canvas and the file",
      bool(_emit) and ".toString()" in _emit.group(2)
      and ".replace(" not in _emit.group(2)
      and ".trim(" not in _emit.group(2)
      and ".normalize(" not in _emit.group(2),
      (_emit.group(2)[:160] if _emit else "no updateListener found"))
check("9g an edit is SURGICAL — it changes what was typed and nothing else",
      _cm.get("edit_is_surgical") is True, str(_cm)[:220])
check("9h no ids or data-* are introduced by the editor",
      _cm.get("no_ids_added") is True, str(_cm)[:220])


# ── 10. document identity is never REPLAYED from storage (ADR-572 D9) ────
# `text.file` was OWNED (§3h) but absent from the EPHEMERAL list, and those are
# two different registries. In `reconcileUrl` the merge order is
# `{...incoming, ...remembered, ...delivered}` — so `remembered` OUTRANKS the
# URL, and a stored document id beat the one the member asked for. Observed
# four times on three paths (another file's param, a bare `/text`, an
# explicitly emptied `?text.file=`), and it reopened a TRASHED document.
_prefs = (WEB / "lib" / "shell" / "surface-preferences.ts").read_text()


def _registry(name: str) -> dict[str, list[str]]:
    """Parse a `Record<string, readonly string[]>` literal into {slug: [keys]},
    comments stripped — an assertion that reads comments can match its own
    explanatory prose (the trap this repo keeps re-learning)."""
    m = re.search(name + r"\s*:\s*Record<[^>]*>\s*=\s*\{(.*?)\n\};", _prefs, re.S)
    if not m:
        return {}
    body = re.sub(r"//.*", "", m.group(1))
    out: dict[str, list[str]] = {}
    for row in re.finditer(r"'?([a-z-]+)'?\s*:\s*\[([^\]]*)\]", body):
        out[row.group(1)] = re.findall(r"'([^']+)'", row.group(2))
    return out


_owned = _registry("SURFACE_PARAM_KEYS")
_ephemeral = _registry("SURFACE_EPHEMERAL_PARAM_KEYS")

check("10a both param registries parse (the gate is reading real rows)",
      len(_owned) >= 5 and len(_ephemeral) >= 5,
      f"owned={len(_owned)} ephemeral={len(_ephemeral)}")
check("10b text.file is EPHEMERAL — a document is a drill-in, never a posture",
      "file" in _ephemeral.get("text", []), str(_ephemeral.get("text")))

# The CLASS of bug, not just this instance: any surface owning a document
# identity key must strip it from the remembered set. Text is the third surface
# to miss a registry at birth (radar 2026-08-13, files before it) — so the
# invariant is asserted over EVERY surface, and a new document app that forgets
# names itself instead of shipping the same bug.
_IDENTITY_KEYS = ("file", "path")
for _slug, _keys in sorted(_owned.items()):
    for _k in _IDENTITY_KEYS:
        if _k not in _keys:
            continue
        check(
            f"10c {_slug}.{_k} is a document identity — it must be stripped "
            f"from the REMEMBERED set, or a stored value outranks the URL",
            _k in _ephemeral.get(_slug, []),
            f"{_slug} ephemeral={_ephemeral.get(_slug)}",
        )


# ── 11. ADR-572 D10 — the operator's click-pass findings ─────────────────
# Five defects the operator found by DRIVING the shipped app. Every one was
# invisible to `next build`, to tsc, and to the 128 checks above, because each
# is about behaviour or rendered output rather than about source text.
#
# The rule these checks are written to: EXECUTE the thing. §11a-c mount the
# real CodeMirror canvas in jsdom and read what it produced; §11d calls the
# real edit functions. A grep would have passed over all five defects.

# ── 11a-c. one reading face, and the table that had none ─────────────────
_CANVAS_PROBE = r"""
const fs = require('fs'), path = require('path');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
require.extensions['.tsx'] = require.extensions['.ts'] = function (m, f) {
  m._compile(transform(fs.readFileSync(f, 'utf8'),
    { transforms: ['typescript', 'jsx', 'imports'], jsxRuntime: 'automatic', production: true }).code, f);
};
const Module = require('module'); const orig = Module._resolveFilename;
Module._resolveFilename = function (r, ...a) {
  if (r.startsWith('@/')) {
    const b = path.join(WEB, r.slice(2));
    for (const e of ['', '.tsx', '.ts', '/index.tsx', '/index.ts']) {
      try { return orig.call(this, b + e, ...a); } catch (x) { /* next */ }
    }
  }
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

const React = require(WEB + '/node_modules/react');
const { renderToStaticMarkup } = require(WEB + '/node_modules/react-dom/server');
const { ProseCanvas } = require(WEB + '/components/text/ProseCanvas.tsx');
const { ProseReader, PROSE_READING_SKIN } = require(WEB + '/components/text/ProseReader.tsx');
const FACE_MOD = require(WEB + '/components/text/readingFace.ts');
const { HEADING_SCALE, FACE } = FACE_MOD;

// Mount the REAL canvas component (not a hand-assembled EditorView), so this
// checks the wiring — the lesson 7n paid for when it asserted its own input.
const host = dom.window.document.getElementById('h');
const src = '# Title\n\n| Medium | Currency |\n| --- | --- |\n| Text | .md |\n\n- [ ] task\n\n~~gone~~\n';
let handle = null;
const { createRoot } = require(WEB + '/node_modules/react-dom/client');
def('IS_REACT_ACT_ENVIRONMENT', true);
const { act } = require(WEB + '/node_modules/react');
const root = createRoot(host);
act(() => {
  root.render(React.createElement(ProseCanvas, {
    value: src, onChange: () => {}, handleRef: (h) => { handle = h; },
  }));
});
const canvasHtml = host.innerHTML;
const liveDoc = handle ? null : null;

// The rendered reading face, for the cross-engine comparison.
const readerHtml = renderToStaticMarkup(React.createElement(ProseReader, { text: src }));

const out = {
  // 11a — the table must be VISIBLY a table on the canvas, not raw pipes.
  //       Three source lines => three decorated rows, header and last marked.
  canvas_table_rows: (canvasHtml.match(/cm-tableRow(?![-\w])/g) || []).length >= 3,
  canvas_table_header: /cm-tableRow-header/.test(canvasHtml),
  canvas_table_last: /cm-tableRow-last/.test(canvasHtml),
  // 11b — the canvas still renders headings/marks (the decoration layer did
  //       not displace syntax highlighting).
  canvas_styled: /class="[^"]*\bcm-/.test(canvasHtml) && canvasHtml.includes('Title'),
  // 11c — the file is untouched by all of it (ADR-456 D1 still holds).
  canvas_doc_identical: canvasHtml.includes('Medium') && !/data-block|data-mark|data-align/.test(canvasHtml),
  // 11d — BOTH engines draw a table. Before D10 the rendered face drew a
  //       grid and the canvas drew nothing, so the thumbnail and the print
  //       sheet were more styled than the surface you type in.
  reader_table: /<table/.test(readerHtml) && /<th[^>]*>/.test(readerHtml),
  // 11e — the shared declaration is REACHED by both, not restated. If the
  //       reader's literal classes drift from HEADING_SCALE, this fails.
  scale_agrees_h1: PROSE_READING_SKIN.includes('prose-h1:text-[' + HEADING_SCALE.h1.rem + ']'),
  scale_agrees_h2: PROSE_READING_SKIN.includes('prose-h2:text-[' + HEADING_SCALE.h2.rem + ']'),
  scale_agrees_h3: PROSE_READING_SKIN.includes('prose-h3:text-[' + HEADING_SCALE.h3.rem + ']'),
  // 11f — the canvas reads the APP type token, never a Docs artifact-skin var
  //       with an inline fallback (which can never resolve in a .md and so
  //       always silently took a DIFFERENT stack than Tailwind's font-serif).
  face_is_token: FACE.serif === 'var(--font-serif)' && FACE.mono === 'var(--font-mono)',
};
console.log(JSON.stringify(out));
"""

try:
    _d10 = json.loads(
        subprocess.run(
            ["node", "-e", _CANVAS_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=180, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate
    _d10 = {"error": str(exc)}

# 11a/11a1/11a2 asserted D10's LINE-decoration table (a styled row per source
# line). D15 replaces the whole range with a real <table>, so those assertions
# are now false BY DESIGN — §15b tests the replacement. Recorded, not deleted:
# the line-based approach was driven twice and failed for a structural reason
# worth keeping visible (lines lay out independently, so columns cannot align).
check("11b the decoration layer did NOT displace syntax highlighting",
      _d10.get("canvas_styled") is True, str(_d10)[:260])
check("11c the canvas writes NOTHING into the document — no data-* reaches "
      "the source (ADR-456 D1 holds with the table decoration in place)",
      _d10.get("canvas_doc_identical") is True, str(_d10)[:260])
check("11d the RENDERED face draws a table too — both engines agree, so the "
      "print sheet and the landing thumbnail cannot be more styled than the "
      "canvas the member types in",
      _d10.get("reader_table") is True, str(_d10)[:260])
for _k, _lbl in [("scale_agrees_h1", "h1"), ("scale_agrees_h2", "h2"), ("scale_agrees_h3", "h3")]:
    check(f"11e the reading skin's {_lbl} size AGREES with HEADING_SCALE — "
          f"one declaration, two renderers; a drift is a failed check, never "
          f"a quiet asymmetry",
          _d10.get(_k) is True, str(_d10)[:260])
check("11f the canvas face is the APP type token (var(--font-serif)), not a "
      "Docs ARTIFACT-SKIN var — a .md has no skin, so that var could never "
      "resolve and the inline fallback silently won a DIFFERENT stack than "
      "Tailwind's font-serif: one document, two faces",
      _d10.get("face_is_token") is True, str(_d10)[:260])

# The type tokens must actually be declared, or `var(--font-serif)` is just a
# prettier spelling of the same undefined read.
_globals_css = (WEB / "app" / "globals.css").read_text(encoding="utf-8")
_tw_config = (WEB / "tailwind.config.ts").read_text(encoding="utf-8")
check("11g --font-serif and --font-mono are DECLARED in globals.css (the app "
      "type vocabulary, distinct from skinVars.ts's artifact vocabulary)",
      "--font-serif:" in _globals_css and "--font-mono:" in _globals_css,
      "missing from :root")
# Read the ACTUAL mapping, not the file's text. The first spelling of this
# check asserted `"var(--font-serif)" in _tw_config` and PASSED its own
# falsification: pointing `serif` at a hardcoded `["Georgia","serif"]` left the
# string present in this check's own explanatory comment and in the `mono:`
# line beside it. Fourth time this arc that an assertion matched something
# other than the thing it names — so it now extracts the per-key value.
def _tw_font(key: str) -> str:
    m = re.search(rf"^\s*{key}:\s*\[([^\]]*)\]", _strip_comments(_tw_config), re.M)
    return m.group(1) if m else ""


check("11h Tailwind's font-serif POINTS AT the token, so a `font-serif` class "
      "and a `var(--font-serif)` read cannot resolve to different stacks",
      "var(--font-serif)" in _tw_font("serif"),
      f"tailwind serif => {_tw_font('serif')!r}")
check("11h1 Tailwind's font-mono POINTS AT the token",
      "var(--font-mono)" in _tw_font("mono"),
      f"tailwind mono => {_tw_font('mono')!r}")

# ── 11i. the toolbar on an empty line ────────────────────────────────────
# Operator: "the tool bar inserts don't work for an empty line." Four of the
# eight source edits were silent no-ops on a blank line — the ONE place a
# member reaches for the button instead of typing the marker by hand.
_EMPTY_PROBE = r"""
const fs = require('fs');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
const js = transform(fs.readFileSync(WEB + '/components/text/markdownEdits.ts', 'utf8'),
  { transforms: ['typescript', 'imports'] }).code;
const mod = { exports: {} };
new Function('module', 'exports', 'require', js)(mod, mod.exports, () => ({}));
const M = mod.exports;
const D = 'Hi\n\n';           // caret at 4 == a blank line at the end
console.log(JSON.stringify({
  // Each must MARK the empty line, and leave the caret past the marker.
  list:      M.toggleList(D, 4, 4, false).text === 'Hi\n\n- ',
  ordered:   M.toggleList(D, 4, 4, true).text  === 'Hi\n\n1. ',
  checklist: M.toggleChecklist(D, 4, 4).text   === 'Hi\n\n- [ ] ',
  quote:     M.toggleQuote(D, 4, 4).text       === 'Hi\n\n> ',
  caret_usable: M.toggleChecklist('', 0, 0).selectionEnd === 6,
  // The controls that ALREADY worked must be untouched.
  heading_ok: M.toggleHeading(D, 4, 4, 2).text === 'Hi\n\n## ',
  table_ok:   M.insertTable(D, 4, 4).text.includes('| Column | Column |'),
  // REGRESSION: the permissive blank-line clause exists so a gap INSIDE a
  // multi-line selection does not veto toggling OFF. That must still hold —
  // this is the behaviour the naive fix breaks.
  multiline_off: M.toggleList('- a\n\n- b', 0, 8, false).text === 'a\n\nb',
  multiline_quote_off: M.toggleQuote('> a\n\n> b', 0, 8).text === 'a\n\nb',
  multiline_on_keeps_gap: M.toggleList('a\n\nb', 0, 4, false).text === '- a\n\n- b',
  // A non-empty line is unchanged by the fix.
  nonempty: M.toggleList('Hello', 0, 5, false).text === '- Hello',

  // ⭐ ADR-575 D8.d — the marker must SURVIVE the next keystroke.
  //
  // 11i4 above asks only where the selection ENDS, and a span ending past the
  // marker satisfies that exactly as well as a caret does. So all four toggles
  // returned the CONVERT branch's span on an empty line: the `- ` was written
  // and handed back SELECTED, and the member's first character replaced it.
  // The text assertions above were all green over it — the row appeared and
  // was destroyed one keystroke later, which is the slash palette's EVERY pick
  // (a slash run is by definition a collapsed caret on an otherwise-bare line).
  //
  // Stated as the property that failed: type a character and the marker is
  // still there. Computed the way CodeMirror applies a selection, so this
  // cannot pass on a span.
  marker_survives_typing: (() => {
    const cases = [
      ['- ',      M.toggleList(D, 4, 4, false)],
      ['1. ',     M.toggleList(D, 4, 4, true)],
      ['- [ ] ',  M.toggleChecklist(D, 4, 4)],
      ['> ',      M.toggleQuote(D, 4, 4)],
      ['## ',     M.toggleHeading(D, 4, 4, 2)],
    ];
    return cases.every(([marker, e]) => {
      const typed = e.text.slice(0, e.selectionStart) + 'x' + e.text.slice(e.selectionEnd);
      return typed === 'Hi\n\n' + marker + 'x';
    });
  })(),
  // The same claim on the caret itself, so a failure names WHICH property broke.
  marker_caret_collapsed: [
    M.toggleList(D, 4, 4, false), M.toggleList(D, 4, 4, true),
    M.toggleChecklist(D, 4, 4), M.toggleQuote(D, 4, 4), M.toggleHeading(D, 4, 4, 2),
  ].every((e) => e.selectionStart === e.selectionEnd),
  // REGRESSION — CONVERT is a different claim and keeps its span: the member
  // pointed at existing text and changed what it is, and seeing what moved is
  // right. Collapsing this one too would be the naive over-fix.
  convert_keeps_span: (() => {
    const c = M.toggleList('Hello\nworld', 7, 7, false);
    const h = M.toggleHeading('Hello\nworld', 7, 7, 2);
    const q = M.toggleQuote('one\ntwo', 0, 7);
    return c.text === 'Hello\n- world' && c.selectionStart === 6 && c.selectionEnd === 13
      && h.selectionStart === 6 && h.selectionEnd === 14
      && q.selectionStart === 0 && q.selectionEnd === 11;
  })(),
  // ...and so does toggling OFF.
  toggle_off_keeps_span: (() => {
    const o = M.toggleList('- a\n- b', 0, 7, false);
    return o.text === 'a\nb' && o.selectionStart === 0 && o.selectionEnd === 3;
  })(),
}));
"""

try:
    _e = json.loads(
        subprocess.run(
            ["node", "-e", _EMPTY_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _e = {"error": str(exc)}

for _k, _lbl in [
    ("list", "11i a bulleted list"),
    ("ordered", "11i1 a numbered list"),
    ("checklist", "11i2 a task list"),
    ("quote", "11i3 a quote"),
]:
    check(f"{_lbl} can be started ON AN EMPTY LINE — the blank-line clause made "
          f"the 'already marked?' test vacuously true, so the toggle took the "
          f"UN-mark branch and the button did nothing",
          _e.get(_k) is True, str(_e)[:260])
check("11i4 the caret lands PAST the inserted marker, ready to type",
      _e.get("caret_usable") is True, str(_e)[:260])
check("11i5 heading + table on an empty line still work (they always did)",
      _e.get("heading_ok") is True and _e.get("table_ok") is True, str(_e)[:260])
check("11i6 the inserted marker SURVIVES the next keystroke — every toggle "
      "returned the CONVERT branch's span on an empty line, so the `- ` came "
      "back SELECTED and the member's first character replaced it. 11i4 asks "
      "only where the selection ENDS, which a span satisfies as well as a "
      "caret does; the row was created and destroyed one keystroke later, on "
      "the slash palette's EVERY pick",
      _e.get("marker_survives_typing") is True, str(_e)[:260])
check("11i7 ...and the caret is COLLAPSED, naming which half of 11i6 broke",
      _e.get("marker_caret_collapsed") is True, str(_e)[:260])
check("11i8 REGRESSION — CONVERT keeps its span (the member pointed at existing "
      "text and changed what it is; showing what moved is right). Collapsing "
      "this too is the naive over-fix",
      _e.get("convert_keeps_span") is True, str(_e)[:260])
check("11i9 REGRESSION — toggling a marker OFF keeps its span for the same reason",
      _e.get("toggle_off_keeps_span") is True, str(_e)[:260])
check("11j REGRESSION — a blank line INSIDE a multi-line selection still does "
      "not veto toggling off; that is what the permissive clause was for, and "
      "the naive fix breaks exactly here",
      _e.get("multiline_off") is True and _e.get("multiline_quote_off") is True,
      str(_e)[:260])
check("11j1 REGRESSION — toggling a multi-line span ON preserves its gap",
      _e.get("multiline_on_keeps_gap") is True, str(_e)[:260])
check("11j2 REGRESSION — a non-empty line is unaffected",
      _e.get("nonempty") is True, str(_e)[:260])

# ── 11k. file handling matches Docs (D10 supersedes D5) ──────────────────
_editor = (WEB / "components" / "text" / "TextEditor.tsx").read_text(encoding="utf-8")
# Comments stripped before asserting an ABSENCE — an assertion has matched its
# own explanatory comment three times this arc.
_editor_ast = _strip_comments(_editor)

check("11k the Save BUTTON is deleted — saving is automatic, and two save "
      "models in one surface is the dual-approach shape CLAUDE.md §2 forbids",
      not re.search(r"<button[^>]*>[^<]*\bSave\b\s*</button>", _editor_ast, re.S)
      and ">\n          Save\n        </button>" not in _editor,
      "a Save button survives in TextEditor")
check("11k1 an idle debounce commits the document (Docs' COMMIT_IDLE_MS)",
      "COMMIT_IDLE_MS" in _editor and "2000" in _editor, "no idle commit")
check("11k2 the commit reads the LIVE text through a ref — a timer closing "
      "over `text` writes a revision one keystroke behind and reports success",
      "textRef" in _editor and "textRef.current" in _editor, "stale-closure risk")
check("11k3 writes are SERIALIZED — a second commit's CAS base is the head "
      "the first one acked, so they must not race (Docs' writeTail rule)",
      "writeTail" in _editor, "concurrent commits can race the CAS base")
check("11k4 leaving the document flushes pending text (beforeunload + "
      "visibilitychange + teardown), or autosave silently loses the last edit",
      "beforeunload" in _editor and "visibilitychange" in _editor, "no flush")
check("11k5 the 409 CONFLICT BANNER SURVIVES — Docs can auto-recompute a "
      "conflict because it commits replayable OPS; Text commits whole text, "
      "so it must ask the member instead of inventing a merge",
      "setConflict(readConflict(" in _editor and "Save mine over theirs" in _editor,
      "the conflict banner was lost with the Save button")

# ── 11L. the Properties pane: the ⋯, and the visible refusal ─────────────
# Assert the WIRING (a button whose handler opens the menu on this file), not
# the presence of two labels. The first spelling required `openMenuFromButton`
# and the string "File actions" — deleting the aria-label left `title="File
# actions"` behind and the check stayed green. Same lesson as 11h, one screen
# apart: a check must name the BEHAVIOUR, never a decoration of it.
_kebab_wired = re.search(
    r"onClick=\{\(e\)\s*=>\s*openMenuFromButton\(\s*\{\s*path\s*,", _editor_ast
)
check("11L the OPEN document's Properties pane carries the ⋯ file menu, WIRED "
      "to this document — it existed on the landing cards and vanished once a "
      "document was open, so the moment the member was working on a file was "
      "the one moment they could not act on it as one",
      _kebab_wired is not None and "{fileMenu}" in _editor_ast,
      "no kebab wired to openMenuFromButton, or the menu node is not mounted")
check("11L1 it reuses the SHARED menu, not a re-typed popover — Docs hand-rolls "
      "~90 lines of inline JSX for this and that must not be copied",
      "useFileContextMenu" in _editor
      and not re.search(r"absolute right-0 top-full z-30", _editor),
      "the pane forked its own popover")
check("11L2 the shared hook EXPORTS the button opener, so a pane can anchor "
      "the menu on any pointer (Kebab is coarse-pointer only)",
      "openMenuFromButton," in (WEB / "components" / "workspace" / "FileContextMenu.tsx")
      .read_text(encoding="utf-8").split("return {")[-1],
      "openMenuFromButton is still internal")
# 11M asserted the Appearance section that D10 added to print the
# colour/highlight refusal in the pane. **D16 removes it entirely** — the
# operator: *"we don't need this appearance info on properties at all remove
# altogether."* The refusal REASONING still holds (markdown has nowhere to keep
# a colour), but a paragraph explaining an absence is itself clutter in a pane
# that should describe the document, not litigate its design. Recorded rather
# than deleted: D10 added this copy deliberately, and the reversal is the point.
check("11M the Appearance explainer is GONE from the pane — a refusal does not "
      "need a standing paragraph once it is simply how the app works",
      "APPEARANCE" not in _editor and "Appearance" not in _editor,
      "the Appearance section survives")


# ── 12. ADR-572 D11 — insert vs turn-into, and two autosave defects ──────
# Found by the operator driving D10 on production. The screenshot showed
# `> dddd` WELDED to the end of a body paragraph: pressing Quote with the caret
# resting at the end of a finished line converted that line instead of opening
# a new one. Docs keeps Insert and Turn-into as separate acts; Text collapsed
# them into one toolbar, so the button read as insert and behaved as turn-into.
_D11_PROBE = r"""
const fs = require('fs');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
const js = transform(fs.readFileSync(WEB + '/components/text/markdownEdits.ts', 'utf8'),
  { transforms: ['typescript', 'imports'] }).code;
const mod = { exports: {} };
new Function('module', 'exports', 'require', js)(mod, mod.exports, () => ({}));
const M = mod.exports;

const P = 'Hello there.';   // a FINISHED paragraph
const E = P.length;         // caret resting at its end
const Q = '> quoted', B = '- item', K = '- [ ] task';
const D = 'one\ntwo\nthree';

console.log(JSON.stringify({
  // The operator's exact gesture, for every line-shaped kind.
  new_quote:  M.toggleQuote(P, E, E).text      === P + '\n> ',
  new_task:   M.toggleChecklist(P, E, E).text  === P + '\n- [ ] ',
  new_bullet: M.toggleList(P, E, E, false).text === P + '\n- ',
  new_number: M.toggleList(P, E, E, true).text  === P + '\n1. ',
  new_head:   M.toggleHeading(P, E, E, 2).text  === P + '\n## ',
  // The caret must land ready to type, not before the marker.
  caret_ready: M.toggleQuote(P, E, E).selectionStart === (P + '\n> ').length,
  // TURN-INTO must survive: a caret INSIDE the line still converts it.
  inside_converts: M.toggleQuote(P, 5, 5).text === '> ' + P,
  head_inside_converts: M.toggleHeading(P, 5, 5, 2).text === '## ' + P,
  // A SELECTION always means convert — never insert.
  selection_converts: M.toggleQuote(P, 0, E).text === '> ' + P,
  multiline_converts: M.toggleList('a\nb', 0, 3, false).text === '- a\n- b',
  // At the end of an ALREADY-marked line the member is continuing a list, so
  // the toggle must turn it OFF, not append a second marker.
  marked_toggles_off: M.toggleQuote(Q, Q.length, Q.length).text === 'quoted'
    && M.toggleList(B, B.length, B.length, false).text === 'item'
    && M.toggleChecklist(K, K.length, K.length).text === 'task',
  // D10's empty-line fix must survive D11.
  empty_still_marks: M.toggleQuote('Hi\n\n', 4, 4).text === 'Hi\n\n> '
    && M.toggleChecklist('Hi\n\n', 4, 4).text === 'Hi\n\n- [ ] ',
  // Mid-document: the new line goes BELOW, and nothing after it moves.
  mid_doc: M.toggleQuote(D, 7, 7).text === 'one\ntwo\n> \nthree',
  // D10 regression: toggling OFF across an internal gap.
  gap_off: M.toggleList('- a\n\n- b', 0, 8, false).text === 'a\n\nb',
}));
"""

try:
    _d11 = json.loads(
        subprocess.run(
            ["node", "-e", _D11_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d11 = {"error": str(exc)}

for _k, _lbl in [
    ("new_quote", "12a Quote"),
    ("new_task", "12a1 Task list"),
    ("new_bullet", "12a2 Bulleted list"),
    ("new_number", "12a3 Numbered list"),
    ("new_head", "12a4 Heading"),
]:
    check(f"{_lbl} at the END of a finished paragraph OPENS A NEW LINE — the "
          f"operator's screenshot showed `> dddd` welded onto a body paragraph, "
          f"because a button that reads as INSERT behaved as TURN-INTO",
          _d11.get(_k) is True, str(_d11)[:300])
check("12b the caret lands PAST the new marker, ready to type",
      _d11.get("caret_ready") is True, str(_d11)[:300])
check("12c TURN-INTO survives — a caret INSIDE the line still converts it "
      "(the affordance Docs puts in a separate pane section)",
      _d11.get("inside_converts") is True and _d11.get("head_inside_converts") is True,
      str(_d11)[:300])
check("12d a SELECTION always converts, never inserts — single and multi-line",
      _d11.get("selection_converts") is True and _d11.get("multiline_converts") is True,
      str(_d11)[:300])
check("12e at the end of an ALREADY-marked line the toggle turns it OFF rather "
      "than appending a second marker — the member is continuing a list, not "
      "starting one",
      _d11.get("marked_toggles_off") is True, str(_d11)[:300])
check("12f D10's empty-line fix SURVIVES D11 (an empty line has nothing to "
      "convert, so it is marked in place)",
      _d11.get("empty_still_marks") is True, str(_d11)[:300])
check("12g mid-document the new line opens BELOW and nothing after it moves",
      _d11.get("mid_doc") is True, str(_d11)[:300])
check("12h D10 regression — toggling OFF across an internal gap still works",
      _d11.get("gap_off") is True, str(_d11)[:300])

# ── 12i-j. the two autosave defects the same click-pass exposed ──────────
# Assert the ref is READ IN THE GUARD, not merely declared. The first spelling
# checked `"inFlightBody" in _editor` and PASSED its own falsification: deleting
# the comparison left the `useRef` declaration and the JSDoc behind, both
# carrying the name. Sixth occurrence this arc of a check matching a name where
# it meant a behaviour — the declaration is not the guard.
_noop_guard = re.search(
    r"body\s*===\s*baselineRef\.current\s*\|\|\s*body\s*===\s*inFlightBody\.current"
    r"|body\s*===\s*inFlightBody\.current\s*\|\|\s*body\s*===\s*baselineRef\.current",
    _editor_ast,
)
check("12i the no-op guard consults the QUEUE's own record, not only React "
      "state — `baselineRef` mirrors state and lags a render, so two triggers "
      "firing close together (idle timer, then a blur flush) both saw the old "
      "baseline and BOTH wrote, minting a duplicate revision of identical bytes",
      _noop_guard is not None and "inFlightBody.current = body" in _editor_ast,
      "the in-flight body is not READ in the no-op guard (or never assigned)")
check("12j 'Save mine over theirs' is ALWAYS offered — it was conditional on "
      "`currentHeadId`, so whenever the server could not name the head the "
      "button silently vanished and the member had ONE exit where the design "
      "promises two. D7 fixed one CAUSE of that; the condition itself was the "
      "deeper defect, because any future cause reproduces it",
      re.search(r"\{conflict\.currentHeadId\s*&&", _editor_ast) is None
      and "Save mine over theirs" in _editor_ast,
      "the override button is still conditional on a field the server may omit")


# ── 13. ADR-572 D12 — typing after a toolbar insert was destroyed ────────
# The operator: "post insert, i input text, the inputted gets ignored and goes
# to new line." Reproduced against a real EditorView: after a toolbar press,
# React re-renders with the value the update listener QUEUED, which is now one
# keystroke behind, and the external-change effect applied that stale prop over
# the newer document — deleting the character just typed and snapping the caret
# back. Invisible to types and to `next build`: both values are valid strings.
_D12_PROBE = r"""
const fs = require('fs'), path = require('path');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
require.extensions['.tsx'] = require.extensions['.ts'] = function (m, f) {
  m._compile(transform(fs.readFileSync(f, 'utf8'),
    { transforms: ['typescript', 'jsx', 'imports'], jsxRuntime: 'automatic', production: true }).code, f);
};
const Module = require('module'); const orig = Module._resolveFilename;
Module._resolveFilename = function (r, ...a) {
  if (r.startsWith('@/')) {
    const b = path.join(WEB, r.slice(2));
    for (const e of ['', '.tsx', '.ts', '/index.tsx', '/index.ts']) {
      try { return orig.call(this, b + e, ...a); } catch (x) { /* next */ }
    }
  }
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

let handle = null, value = 'abc';
const root = createRoot(dom.window.document.getElementById('h'));
const render = () => act(() => {
  root.render(React.createElement(ProseCanvas, {
    value, onChange: (v) => { value = v; }, handleRef: (h) => { if (h) handle = h; },
  }));
});
render();

// 1. The toolbar press. Its emission is what React will re-render with.
act(() => handle.apply('abc\n- ', 6, 6));
const staleProp = value;

// 2. The member types immediately, before that render lands.
act(() => handle.apply('abc\n- x', 7, 7));
const afterTyping = value;

// 3. React re-renders with the STALE value from step 1. The canvas must
//    recognise its OWN echo and leave the newer document alone.
value = staleProp;
render();
const survived = value !== 'abc\n- ' || handle.selection()[0] >= 7;

// 4. A GENUINE external write (a lane, a conflict reload) must still land.
value = 'abc\n- x\n\nfrom the lane';
render();
const externalLanded = handle.selection()[0] >= 0;

const src = fs.readFileSync(WEB + '/components/text/ProseCanvas.tsx', 'utf8');
console.log(JSON.stringify({
  typed_survives: survived,
  after_typing_ok: afterTyping === 'abc\n- x',
  external_lands: externalLanded,
  // The guard must be a SET of everything emitted, not the last emission:
  // by the time the stale prop arrives, the member's typing has already
  // superseded a single-value ref, so the echo would not be recognised.
  guard_is_a_set: /emittedRef\s*=\s*useRef<Set<string>>/.test(src)
    && /emittedRef\.current\.has\(value\)/.test(src)
    && /emittedRef\.current\.add\(/.test(src),
  // `apply` must be a MINIMAL change, not a whole-document replace.
  apply_is_minimal: !/changes:\s*\{\s*from:\s*0,\s*to:\s*view\.state\.doc\.length/.test(src),
  // ...and its own undo step, or one ⌘Z eats the press AND the typing.
  apply_isolates_history: /annotations:\s*isolateHistory\.of/.test(src),
}));
"""

try:
    _d12 = json.loads(
        subprocess.run(
            ["node", "-e", _D12_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=180, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d12 = {"error": str(exc)}

check("13a typing immediately after a toolbar insert SURVIVES — the stale "
      "render the insert itself queued must not be applied over the newer "
      "document (operator: 'post insert, i input text, the inputted gets "
      "ignored and goes to new line')",
      _d12.get("typed_survives") is True, str(_d12)[:300])
check("13b the insert itself still reaches the document",
      _d12.get("after_typing_ok") is True, str(_d12)[:300])
check("13c a GENUINE external write (a lane, a conflict reload) still lands — "
      "the echo guard must not deafen the canvas to real writes",
      _d12.get("external_lands") is True, str(_d12)[:300])
check("13d the echo guard is a SET of everything emitted, not the LAST "
      "emission — a single-value ref is overwritten by the member's own typing "
      "before the stale prop arrives, so the echo goes unrecognised",
      _d12.get("guard_is_a_set") is True, str(_d12)[:300])
check("13e `apply` dispatches a MINIMAL change, never a whole-document "
      "replace — the latter rewrites lines the edit never touched",
      _d12.get("apply_is_minimal") is True, str(_d12)[:300])
check("13f a toolbar press is its OWN history entry — `history()` coalesces "
      "edits within ~500ms, so without this one ⌘Z swallows both the character "
      "just typed and the button press before it",
      _d12.get("apply_isolates_history") is True, str(_d12)[:300])


# ── 14. ADR-572 D13 — live preview, and the constraint re-read ───────────
# The operator: "think that closest to notion (not sure why i see the # or
# alike)". D8 shipped the marks permanently visible and called it an honest
# limitation, claiming ADR-456 D1 banned hiding them. That was WRONG — D1
# constrains the document MODEL (a string, never a tree of identified blocks),
# not the rendered appearance. Hiding a mark is Decoration.replace() over a
# range read from the syntax tree; the .md stays byte-identical. §14 mounts the
# real canvas and READS WHAT IT PAINTED, because no source check can see it.
_D13_PROBE = r"""
const fs = require('fs'), path = require('path');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
require.extensions['.tsx'] = require.extensions['.ts'] = function (m, f) {
  m._compile(transform(fs.readFileSync(f, 'utf8'),
    { transforms: ['typescript', 'jsx', 'imports'], jsxRuntime: 'automatic', production: true }).code, f);
};
const Module = require('module'); const orig = Module._resolveFilename;
Module._resolveFilename = function (r, ...a) {
  if (r.startsWith('@/')) {
    const b = path.join(WEB, r.slice(2));
    for (const e of ['', '.tsx', '.ts']) { try { return orig.call(this, b + e, ...a); } catch (x) {} }
  }
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

const DOC = '# Standing facts\n\nSome **bold** and _em_ text.\n\n## The copy bank\n\n'
  + '| Users | None yet |\n| --- | --- |\n| Revenue | None |\n\n> a quote\n';
let handle = null, value = DOC;
const host = dom.window.document.getElementById('h');
const root = createRoot(host);
act(() => root.render(React.createElement(ProseCanvas, {
  value, onChange: (v) => { value = v; }, handleRef: (h) => { if (h) handle = h; },
})));
const shown = () => host.querySelector('.cm-content').textContent;

act(() => handle.reveal(0, 0));           // caret on line 1
const s1 = shown();
const off = DOC.indexOf('## The copy bank') + 3;
act(() => handle.reveal(off, off));       // caret on the H2
const s2 = shown();

console.log(JSON.stringify({
  active_keeps_marks: s1.includes('# Standing facts'),
  inactive_hides_h2: !s1.includes('## The copy bank') && s1.includes('The copy bank'),
  inactive_hides_bold: !s1.includes('**bold**') && s1.includes('bold'),
  inactive_hides_em: !s1.includes('_em_') && s1.includes('em'),
  inactive_hides_quote: !s1.includes('> a quote') && s1.includes('a quote'),
  // The table's pipes are NOT syntax marks to hide — the grid decoration
  // needs them, and hiding them would leave cells running together.
  table_pipes_survive: s1.includes('| Users | None yet |'),
  // Moving the caret reveals that line and re-hides the one just left.
  caret_reveals: s2.includes('## The copy bank'),
  caret_rehides: !s2.includes('# Standing facts') && s2.includes('Standing facts'),
  // The whole point: none of this touches the file.
  doc_byte_identical: value === DOC,
}));
"""

try:
    _d13 = json.loads(
        subprocess.run(
            ["node", "-e", _D13_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=180, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d13 = {"error": str(exc)}

for _k, _lbl in [
    ("inactive_hides_h2", "14a a heading's `## ` is HIDDEN off the active line"),
    ("inactive_hides_bold", "14a1 `**` is hidden"),
    ("inactive_hides_em", "14a2 `_` is hidden"),
    ("inactive_hides_quote", "14a3 `> ` is hidden"),
]:
    check(f"{_lbl} — the operator asked for 'closest to notion (not sure why i "
          f"see the # or alike)'; D8's claim that hiding needs the banned "
          f"node↔offset map re-read D1's MODEL constraint as an appearance one",
          _d13.get(_k) is True, str(_d13)[:300])
# 14b/14c/14d were D13's and are REVERSED by D14 — kept as a record of what
# changed rather than deleted, because a check that silently disappears leaves
# no trace that the behaviour it defended was a decision someone overturned.
#
#   14b "the ACTIVE line keeps its marks"  → D14 hides them everywhere; the
#       operator drove D13 and rejected it ("i don't want the hashtags
#       visible"). §15a now asserts the OPPOSITE, deliberately.
#   14c "moving the caret reveals that line" → same reversal.
#   14d "a table's PIPES survive"          → D14 hides them and draws real
#       cells instead; §15b asserts the grid.
#
# The reasoning behind 14b was mine, not the operator's, and it lost on
# contact: a `##` appearing when you click into a heading is the source leaking
# through the document, which is what the reading face exists to stop.
check("14e the document is BYTE-IDENTICAL through all of it — decorations are "
      "read FROM offsets and never written back, so ADR-456 D1's actual "
      "constraint (the MODEL is a string) holds with live preview on",
      _d13.get("doc_byte_identical") is True, str(_d13)[:300])



# ── 15. ADR-572 D14 — marks always hidden, a real table, and `/` ─────────
# Three operator asks from driving D13: "i don't want the hashtags visible",
# "the table rendering still looks off", and "can you consider if we can use
# the slash command shortcut key on the page like notion?".
_D14_PROBE = r"""
const fs = require('fs'), path = require('path');
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
const { ProseCanvas, readSlashRun } = require(WEB + '/components/text/ProseCanvas.tsx');
const { filterSlashItems, SLASH_ITEMS } = require(WEB + '/components/text/SlashMenu.tsx');

const DOC = '## Structure\n\n| Section | Idea |\n| --- | --- |\n| Verse 1 | lists everything |\n'
  + '| Chorus | sung warmly |\n\n## The one good line\n\nplain **bold** text\n';
let value = DOC, handle = null;
const host = dom.window.document.getElementById('h');
act(() => createRoot(host).render(React.createElement(ProseCanvas, {
  value, onChange: (v) => { value = v; }, handleRef: (h) => { if (h) handle = h; },
})));
const el = host.querySelector('.cm-content');
const t = el.textContent;
// Put the caret ON the first heading — under D13 that revealed its marks.
act(() => handle.reveal(2, 2));
const tActive = host.querySelector('.cm-content').textContent;

console.log(JSON.stringify({
  h2_hidden: !t.includes('## Structure') && t.includes('Structure'),
  bold_hidden: !t.includes('**bold**') && t.includes('bold'),
  // The D14 change: hidden even when the caret is ON that line.
  hidden_on_active_line: !tActive.includes('## Structure'),
  // The table is a GRID of cells, not a monospace slab.
  pipes_hidden: !t.includes('| Section'),
  cells: el.querySelectorAll('.cm-tableCell').length,
  rows: el.querySelectorAll('.cm-tableRow').length,
  delimiter_collapsed: el.querySelectorAll('.cm-tableDelimiter').length === 1
    && !t.includes('---'),
  doc_byte_identical: value === DOC,
  // `/` runs.
  slash_start: JSON.stringify(readSlashRun('/', 1)) === JSON.stringify({from:0,to:1,filter:''}),
  slash_filter: (readSlashRun('/ta', 3) || {}).filter === 'ta',
  slash_not_midword: readSlashRun('and/or', 6) === null,
  slash_not_url: readSlashRun('see http://x', 12) === null,
  slash_space_closes: readSlashRun('/table of', 9) === null,
  // The palette's rows come from the SAME actions the toolbar dispatches.
  slash_filters: filterSlashItems('quo').length === 1
    && filterSlashItems('todo').some((i) => i.id === 'task')
    && filterSlashItems('').length === SLASH_ITEMS.length,
}));
"""

try:
    _d14 = json.loads(
        subprocess.run(
            ["node", "-e", _D14_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=180, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d14 = {"error": str(exc)}

check("15a the markdown marks are hidden ALWAYS, including on the line the "
      "caret occupies — D13's reveal-on-active-line was driven and rejected "
      "(operator: 'i don't want the hashtags visible')",
      _d14.get("h2_hidden") is True and _d14.get("hidden_on_active_line") is True,
      str(_d14)[:300])
check("15a1 inline marks (`**`) are hidden too",
      _d14.get("bold_hidden") is True, str(_d14)[:300])
# 15b/15b1 asserted D14's per-cell MARK decorations. D15 replaces those too —
# see §16, which asserts a real <table>. Two line-based attempts failed here
# for the same structural reason; the record of that is the point.
check("15c the document is BYTE-IDENTICAL through all of it — every one of "
      "these is a decoration read FROM offsets, never written back",
      _d14.get("doc_byte_identical") is True, str(_d14)[:300])
for _k, _lbl in [
    ("slash_start", "15d `/` at the start of a line opens a run"),
    ("slash_filter", "15d1 the text after `/` is the filter"),
    ("slash_not_midword", "15e `and/or` does NOT open a palette"),
    ("slash_not_url", "15e1 a URL's `//` does NOT open a palette"),
    ("slash_space_closes", "15e2 a space in the filter closes the run"),
]:
    check(f"{_lbl} — the Notion gesture the operator asked for, with the "
          f"false-positive cases that make it usable in prose",
          _d14.get(_k) is True, str(_d14)[:300])
check("15f the palette filters, and its rows are the SAME ToolbarAction values "
      "the toolbar dispatches — a second DOOR to one mechanism, never a second "
      "mechanism (the rule Docs states for its own toolbar/slash pair)",
      _d14.get("slash_filters") is True, str(_d14)[:300])



# ── 16. ADR-572 D15 — a real <table>, and the slash pick that did nothing ──
# Two operator reports: "the slash command pops up but when i select it nothing
# happens", and "the table doesn't look right… these should be rather
# conventional approaches" (with a screenshot showing every row's divider at a
# different x — the structural failure of ANY line-based table).
_D15_PROBE = r"""
const fs = require('fs'), path = require('path');
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
const E = require(WEB + '/components/text/markdownEdits.ts');
const CANVAS_SRC = fs.readFileSync(WEB + '/components/text/ProseCanvas.tsx', 'utf8');

const DOC = '## Structure\n\n| Section | Idea |\n| --- | --- |\n'
  + '| Verse 1 | lists everything |\n| Final chorus | half the volume |\n\nafter\n';
let value = DOC, handle = null;
const host = dom.window.document.getElementById('h');
act(() => createRoot(host).render(React.createElement(ProseCanvas, {
  value, onChange: (v) => { value = v; }, handleRef: (h) => { if (h) handle = h; },
})));
const q = (s) => host.querySelectorAll(s).length;
const headers = [...host.querySelectorAll('.cm-mdTable th')].map((e) => e.textContent);
const body = [...host.querySelectorAll('.cm-mdTable tbody tr')].map((tr) =>
  [...tr.cells].map((c) => c.textContent));
const resting = { table: q('table.cm-mdTable'), src: q('.cm-tableSource') };
// ⭐ ADR-590 D1 REVERSES D15.b here. The caret entering a table used to swap
// the grid for four `.cm-tableSource` lines; it now does NOTHING. Kept as a
// reversed assertion rather than deleted, the convention D15.b itself set.
const off = DOC.indexOf('| Verse 1') + 3;
act(() => handle.reveal(off, off));
const editing = { table: q('table.cm-mdTable'), src: q('.cm-tableSource') };
act(() => handle.reveal(0, 0));
const back = q('table.cm-mdTable');

// The slash pick, as ONE edit computed over `text` (D15) — the shape that
// replaced two dispatches racing one render.
const withRun = 'Hello\n\n/';
const cut = withRun.slice(0, 7) + withRun.slice(8);
const picked = E.toggleQuote(cut, 7, 7);

console.log(JSON.stringify({
  is_real_table: resting.table === 1,
  header_cells: headers.length === 2 && headers[0] === 'Section',
  // Real <td>s in real <tr>s is what makes columns align — the property two
  // line-based attempts could not have.
  body_grid: body.length === 2 && body[0].length === 2
    && body[1][0] === 'Final chorus',
  delimiter_absent: !body.some((r) => r.join('').includes('---')),
  // ⭐ ADR-590 D1 — REVERSED. Was `editing.table === 0 && editing.src === 4`
  // ("caret in → source"). The rendered face does not break for the caret.
  caret_does_not_reveal: editing.table === 1 && editing.src === 0,
  leaving_re_renders: back === 1,
  // ⭐ ADR-590 D1 — the second rendering path is GONE from the app, not merely
  // unreached: a class nothing emits is a class the next widget's author will
  // wire back up.
  // Anchored on the WIRED path, never a name: mount a canvas, put the caret
  // inside the table, and require that NO line decoration replaced the grid.
  // (A spelling check here matched its own explanatory comment — the trap this
  // gate has paid for repeatedly.)
  table_source_path_gone: editing.table === 1
    && host.querySelectorAll('.cm-line[class*="ableSource"]').length === 0,
  // ⭐ ADR-590 D2 — the cell IS the text field.
  cells_editable: [...host.querySelectorAll('.cm-mdTable th, .cm-mdTable td')]
    .every((c) => c.getAttribute('contenteditable') === 'plaintext-only'),
  cells_addressed: [...host.querySelectorAll('.cm-mdTable td')]
    .every((c) => c.dataset.row !== undefined && c.dataset.col !== undefined),
  doc_byte_identical: value === DOC,
  // The pick produces the same markdown a toolbar press would.
  pick_applies: picked.text === 'Hello\n\n> ',
  pick_caret_ready: picked.selectionEnd === 'Hello\n\n> '.length,
}));
"""

try:
    _d15 = json.loads(
        subprocess.run(
            ["node", "-e", _D15_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=180, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d15 = {"error": str(exc)}

check("16a a table renders as a REAL <table> element — two line-based attempts "
      "(D10's styled rows, D14's per-cell marks) both failed because a line "
      "decoration styles ONE LINE and lines lay out independently, so cells in "
      "different rows share no column box and the dividers land at different x "
      "(operator: 'these should be rather conventional approaches')",
      _d15.get("is_real_table") is True, str(_d15)[:300])
check("16a1 its header row is real <th> cells",
      _d15.get("header_cells") is True, str(_d15)[:300])
check("16a2 its body is a real grid of <td> — this is what makes the columns "
      "align, and it is a property no line-based approach can have",
      _d15.get("body_grid") is True, str(_d15)[:300])
check("16a3 the `| --- |` delimiter row is not a body row",
      _d15.get("delimiter_absent") is True, str(_d15)[:300])
check("16b ⭐ ADR-590 D1 REVERSES D15.b — the caret entering a table does NOT "
      "reveal its source. D14.a settled this for every mark ('i don\'t want "
      "the hashtags visible'); D15 shipped the table five decisions later and "
      "did not carry the ruling into it, so D13's reversed reveal rule "
      "survived in the one place D14.a never reached. Was: `editing.table === "
      "0 && editing.src === 4`",
      _d15.get("caret_does_not_reveal") is True, str(_d15)[:300])
check("16b1 leaving the table renders it again (unchanged — it never stopped)",
      _d15.get("leaving_re_renders") is True, str(_d15)[:300])
check("16b2 ⭐ ADR-590 D1 — the source-revealing path is GONE, driven rather "
      "than grepped: with the caret inside the table the grid still stands and "
      "no line decoration replaced it. A second rendering path for one "
      "construct is what the next widget's author wires back up",
      _d15.get("table_source_path_gone") is True, str(_d15)[:300])
check("16b3 ⭐ ADR-590 D2 — every rendered cell IS a text field "
      "(contenteditable), which is the whole Notion property: you type into "
      "the rendered thing because the rendered thing is the document",
      _d15.get("cells_editable") is True, str(_d15)[:300])
check("16b4 ⭐ ADR-590 D2 — each cell carries its row/col, so an edit knows "
      "which source row to rewrite",
      _d15.get("cells_addressed") is True, str(_d15)[:300])
check("16c the document is BYTE-IDENTICAL with a widget on screen — the "
      "widget is built FROM the source each update and never written back, so "
      "ADR-456 D1 holds (delete the class and the file is unchanged)",
      _d15.get("doc_byte_identical") is True, str(_d15)[:300])
check("16d a slash pick APPLIES — it was two dispatches racing one render "
      "(deleteRange, then an apply whose text the view had moved past) and did "
      "nothing on click; it is now ONE pure edit over `text`, the same path "
      "every toolbar button takes (operator: 'pops up but when i select it "
      "nothing happens')",
      _d15.get("pick_applies") is True, str(_d15)[:300])
check("16d1 and the caret lands ready to type",
      _d15.get("pick_caret_ready") is True, str(_d15)[:300])

# The block-decoration rule that forced the StateField — a ViewPlugin throws
# "Block decorations may not be specified via plugins" on mount.
_canvas_src = (WEB / "components" / "text" / "ProseCanvas.tsx").read_text(encoding="utf-8")
check("16e the table renderer is a StateField, NOT a ViewPlugin — CodeMirror "
      "refuses block decorations from a plugin outright, and the first cut of "
      "D15 was a ViewPlugin that threw on mount",
      re.search(r"StateField\.define<DecorationSet>", _canvas_src) is not None
      and "block: true" in _canvas_src,
      "the table widget is not provided from a StateField")
check("16f the slash pick is ONE edit — no `deleteRange` + `applyEdit` pair, "
      "which is the composition that silently half-applied",
      "deleteRange(run.from" not in _strip_comments(
          (WEB / "components" / "text" / "TextEditor.tsx").read_text(encoding="utf-8")),
      "the two-dispatch pick survives")



# ── 17. ADR-572 D17 — the media kinds markdown carries natively ──────────
# Operator: "can't we have similar other format types like images, gallery,
# table csv, component alike? check studio apps to infer what i mean."
#
# The audit's decisive finding: Docs' rich kinds (figure/gallery/table/chart)
# persist as EMPTY `data-ref` elements resolved client-side only — a connector
# reading a Docs artifact gets empty containers, which ADR-574 names as a
# reason Docs is being paused. Porting them would import that defect. So the
# three added are the ones whose CONTENT lives in the file.
_D17_PROBE = r"""
const fs = require('fs');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
const load = (rel) => {
  const js = transform(fs.readFileSync(WEB + rel, 'utf8'),
    { transforms: ['typescript', 'imports'] }).code;
  const m = { exports: {} };
  new Function('module', 'exports', 'require', js)(m, m.exports, () => ({}));
  return m.exports;
};
const M = load('/components/text/markdownEdits.ts');
const D = 'Hello.';
const img = M.insertImage(D, 6, 6, 'notes/diagram.png');
const mer = M.insertMermaid(D, 6, 6);
const code = M.insertFence(D, 6, 6);
const all = img.text + mer.text + code.text;
console.log(JSON.stringify({
  image_is_markdown: img.text === 'Hello.\n\n![diagram](notes/diagram.png)\n',
  mermaid_is_fence: mer.text.includes('```mermaid\ngraph TD'),
  code_is_fence: code.text.includes('```\n'),
  fence_wraps_selection: M.insertFence('let x = 1', 0, 9).text === '```\nlet x = 1\n```\n',
  mermaid_selects_body: mer.text.slice(mer.selectionStart, mer.selectionEnd).startsWith('graph TD'),
  // The property that separates these from Docs' citation blocks.
  no_data_attrs: !/data-/.test(all),
  no_html: !/<[a-z]/i.test(all),
}));
"""

try:
    _d17 = json.loads(
        subprocess.run(
            ["node", "-e", _D17_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d17 = {"error": str(exc)}

check("17a Image inserts native markdown `![alt](path)` — Docs writes "
      "`<figure data-block><img data-ref data-ref-rev>`, which pins the cited "
      "revision but is `data-*` on a minted element (ADR-456 D1) and "
      "unreadable as markdown. The pin is the accepted loss.",
      _d17.get("image_is_markdown") is True, str(_d17)[:300])
check("17b Diagram inserts a ```mermaid fence — the shared renderer ALREADY "
      "paints these, so this was a pure gap. The diagram's whole source is in "
      "the file; Docs' `chart` is an empty <div data-ref='…csv'> whose bars "
      "are manufactured at render time.",
      _d17.get("mermaid_is_fence") is True, str(_d17)[:300])
check("17c Code inserts a fence, and wraps a selection when there is one. "
      "Docs has NO code block kind at all (blockRows maps an icon for a "
      "registry row that does not exist), so this exceeds the reference app.",
      _d17.get("code_is_fence") is True and _d17.get("fence_wraps_selection") is True,
      str(_d17)[:300])
check("17d the diagram's body is SELECTED so it can be typed over",
      _d17.get("mermaid_selects_body") is True, str(_d17)[:300])
check("17e none of the three writes `data-*` or raw HTML — this is the test "
      "that decided WHICH kinds were addable, and the reason gallery, callout, "
      "metrics and button are refused. "
      "SUPERSEDED IN PART by D18: this check used to name table-from-CSV in "
      "that refused list. The refusal was too strong — it conflated a SNAPSHOT "
      "(rows written as real markdown; possible, and now shipped) with an "
      "AUTOMATICALLY LIVE view (a pointer; still refused, and still for this "
      "reason). §18 asserts the snapshot obeys the very rule stated here.",
      _d17.get("no_data_attrs") is True and _d17.get("no_html") is True,
      str(_d17)[:300])

_toolbar = (WEB / "components" / "text" / "MarkdownToolbar.tsx").read_text(encoding="utf-8")
_slash = (WEB / "components" / "text" / "SlashMenu.tsx").read_text(encoding="utf-8")
# Assert the RENDERED ROWS, not the presence of a string. The first spelling
# grepped for `'mermaid'` anywhere in each file and PASSED its own
# falsification: deleting the Diagram row from the toolbar left the token in
# the `ToolbarAction` union and in this feature's own comment. **Seventh time
# this arc** that a check matched a name where it meant a behaviour — so it now
# parses the GROUPS/SLASH_ITEMS arrays and reads the action kinds out.
def _kinds_in(src: str, array_name: str) -> set:
    """The `kind:` values inside a named array literal."""
    m = re.search(rf"{array_name}[^=]*=\s*\[(.*?)\n\];", src, re.S)
    return set(re.findall(r"kind:\s*'([a-z]+)'", m.group(1))) if m else set()


_toolbar_kinds = _kinds_in(_strip_comments(_toolbar), "GROUPS")
_slash_kinds = _kinds_in(_strip_comments(_slash), "SLASH_ITEMS")
check("17f BOTH doors RENDER the new kinds — the toolbar and `/` are two doors "
      "to one mechanism, so a kind reachable from only one of them is a split",
      {"image", "mermaid", "code"} <= _toolbar_kinds
      and {"image", "mermaid", "code"} <= _slash_kinds,
      f"toolbar={sorted(_toolbar_kinds)} slash={sorted(_slash_kinds)}")

_renderer = (WEB / "components" / "shared" / "MarkdownRenderer.tsx").read_text(encoding="utf-8")
check("17g the renderer RESOLVES a workspace image path — the CAS serving URL "
      "is minted with a 1-hour TTL (ADR-427 D4), so it cannot be written into "
      "the document; the `.md` keeps the portable PATH and the viewer mints "
      "its own access per read",
      "MarkdownImage" in _renderer and "blobUrl" in _renderer,
      "an image path would render as a broken <img>")


# ── 18. ADR-572 D18 — a CSV table is a SNAPSHOT, and the rows are in the file ──
# Operator asked whether a CSV-sourced table is structurally impossible in
# markdown. It is not. Three cases, one blocked:
#   - snapshot (rows + a prose source note)  → possible; SHIPPED here
#   - automatically live                      → blocked (a pointer, = Docs'
#     `data-ref`, whose content is EMPTY in the file — an ADR-574 pause reason)
#   - a `csv-table` fence carrying both       → possible but a CONVENTION;
#     not taken (the operator chose the snapshot)
#
# The whole decision rests on ONE property, so that is what §18 measures: after
# an insert, are the CSV's actual values present as text in the `.md`?
_D18_PROBE = r"""
const fs = require('fs');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
const load = (rel) => {
  const js = transform(fs.readFileSync(WEB + rel, 'utf8'),
    { transforms: ['typescript', 'imports'] }).code;
  const m = { exports: {} };
  new Function('module', 'exports', 'require', js)(m, m.exports, () => ({}));
  return m.exports;
};
const M = load('/components/text/markdownEdits.ts');
const WHEN = new Date(2026, 7, 17); // local-time ctor: the fn reads local parts

// A deliberately NASTY csv: a quoted comma, a quoted newline, an escaped
// quote, an embedded pipe, and a short (ragged) row. Assembled from char
// codes where a literal would collide with this file's own string quoting.
const Q = String.fromCharCode(34);   // "
const NL = String.fromCharCode(10);  // \n
const CR = String.fromCharCode(13);  // \r
const NASTY =
  'Region,Owner,Note' + CR + NL +
  'APAC,' + Q + 'Kim, Kevin' + Q + ',' + Q + 'said ' + Q + Q + 'ok' + Q + Q + Q + NL +
  'EMEA,Lee,' + Q + 'a | pipe' + Q + NL +
  'US,Ray,' + Q + 'two' + NL + 'lines' + Q + NL +
  'LATAM' + NL;

const rows = M.parseCsv(NASTY);
const snap = M.csvToMarkdownTable(NASTY);
const ins = M.insertCsvTable('Intro.', 6, 6, 'data/q3.csv', NASTY, WHEN);

// Every data value must survive into the document as TEXT. This is the
// property Docs' citation block lacks and the reason this kind is legal.
const VALUES = ['APAC', 'Kim, Kevin', 'EMEA', 'a \\| pipe', 'LATAM',
                'said ' + Q + 'ok' + Q];

const capped = 'h' + NL + Array.from({length: 250}, (_, i) => 'r' + i).join(NL);
const cappedSnap = M.csvToMarkdownTable(capped);

console.log(JSON.stringify({
  // parseCsv
  quoted_comma_is_one_cell: rows[1][1] === 'Kim, Kevin',
  escaped_quote_unwrapped: rows[1][2] === 'said "ok"',
  quoted_newline_is_one_cell: rows[3][2] === 'two\nlines',
  // the table
  values_present_as_text: VALUES.every((v) => ins.text.includes(v)),
  pipe_escaped: snap.table.includes('a \\| pipe'),
  // An unescaped pipe would SPLIT the row, so the header's width must hold on
  // every row. Count CELL boundaries the way a GFM parser does — an ESCAPED
  // `\|` is content, not a delimiter. The first spelling of this check split
  // on a bare '|' and FAILED against correct output: it counted the escaped
  // pipe as a boundary, i.e. it asserted the very corruption the escape
  // prevents. Falsification caught it; the gate was wrong, not the code.
  all_rows_same_width: (() => {
    const ls = snap.table.trim().split('\n');
    const w = (l) => l.replace(/\\\|/g, '').split('|').length;
    return ls.every((l) => w(l) === w(ls[0]));
  })(),
  // The control for the check above: with the escape REMOVED the widths must
  // disagree, proving this measures alignment and not "did it split at all".
  unescaped_pipe_would_break: (() => {
    const ls = snap.table.trim().split('\n').map((l) => l.replace(/\\\|/g, '|'));
    return !ls.every((l) => l.split('|').length === ls[0].split('|').length);
  })(),
  ragged_row_padded: snap.table.includes('| LATAM |  |  |'),
  newline_folded_in_cell: !snap.table.split('\n').some((l) => l && !l.startsWith('|')),
  has_delimiter_row: /\|\s*---\s*\|/.test(snap.table),
  // provenance
  note_names_source_and_date: ins.text.includes('_From `data/q3.csv` · snapshot 2026-08-17'),
  note_is_italic_prose: !/data-|<[a-z]/i.test(M.csvSourceNote('a.csv', WHEN)),
  // the legality property, asserted on the FULL inserted document
  no_data_attrs: !/data-/.test(ins.text),
  no_html: !/<[a-z]/i.test(ins.text),
  no_fence: !ins.text.includes('```'),
  // the cap
  cap_applied: cappedSnap.rows === M.CSV_SNAPSHOT_ROW_CAP && cappedSnap.omitted === 50,
  cap_disclosed: M.csvSourceNote('a.csv', WHEN, 50).includes('50 more in the source'),
  cap_silent_when_none: !M.csvSourceNote('a.csv', WHEN, 0).includes('more in the source'),
  // an empty source says so rather than writing a broken grid
  empty_csv_says_so: M.insertCsvTable('', 0, 0, 'e.csv', '', WHEN).text.includes('no rows'),
  empty_csv_no_bare_grid: !M.insertCsvTable('', 0, 0, 'e.csv', '', WHEN).text.includes('|  |'),
}));
"""

try:
    _d18 = json.loads(
        subprocess.run(
            ["node", "-e", _D18_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d18 = {"error": str(exc)}

check("18a the CSV parser is QUOTE-AWARE — a naive split(',') corrupts exactly "
      "the data worth tabulating: `\"Kim, Kevin\"` becomes two cells and every "
      "column after it shifts, silently",
      _d18.get("quoted_comma_is_one_cell") is True
      and _d18.get("escaped_quote_unwrapped") is True
      and _d18.get("quoted_newline_is_one_cell") is True, str(_d18)[:400])
check("18b ⭐ THE DECIDING PROPERTY — every CSV VALUE is present in the .md as "
      "TEXT. This is the whole reason a CSV table is legal here and Docs' is "
      "not: Docs writes `<div data-block='table' data-ref='…csv'></div>`, an "
      "EMPTY element whose rows are manufactured at render time, so a connector "
      "reads a container with no data in it (an ADR-574 pause reason).",
      _d18.get("values_present_as_text") is True, str(_d18)[:400])
check("18c a `|` inside a cell is ESCAPED, and every row keeps the header's "
      "width — an unescaped pipe ENDS the cell, silently splitting one column "
      "into two and knocking the rest of the grid out of alignment",
      _d18.get("pipe_escaped") is True and _d18.get("all_rows_same_width") is True
      and _d18.get("unescaped_pipe_would_break") is True,
      str(_d18)[:400])
check("18d a ragged row is PADDED, not rejected — a short row is a real thing "
      "in real CSV, and a table that renders beats a refusal that does not; a "
      "quoted newline is folded so it cannot end the row",
      _d18.get("ragged_row_padded") is True
      and _d18.get("newline_folded_in_cell") is True
      and _d18.get("has_delimiter_row") is True, str(_d18)[:400])
check("18e the SOURCE NOTE names the file and the date. A snapshot's defect is "
      "SILENCE — rows that look live and are not — so the freeze is stated in "
      "the document, as ordinary italic prose a member can edit or delete",
      _d18.get("note_names_source_and_date") is True
      and _d18.get("note_is_italic_prose") is True, str(_d18)[:400])
check("18f the inserted document carries NO `data-*`, NO raw HTML and NO fence "
      "— it is the same GFM table the member could have typed. The `csv-table` "
      "fence alternative was offered and NOT taken: it round-trips, but it is a "
      "CONVENTION other markdown tools render as a code block.",
      _d18.get("no_data_attrs") is True and _d18.get("no_html") is True
      and _d18.get("no_fence") is True, str(_d18)[:400])
check("18g the row cap is applied AND DISCLOSED in the note — a snapshot that "
      "silently drops rows is the same silence the note exists to prevent; with "
      "nothing omitted the note stays quiet",
      _d18.get("cap_applied") is True and _d18.get("cap_disclosed") is True
      and _d18.get("cap_silent_when_none") is True, str(_d18)[:400])
check("18h an empty source writes the note plus '(that file has no rows)', "
      "never a bare `|  |` grid — a broken-looking table would misreport an "
      "empty file as a malformed one",
      _d18.get("empty_csv_says_so") is True
      and _d18.get("empty_csv_no_bare_grid") is True, str(_d18)[:400])

check("18i BOTH doors render `csvtable` — the toolbar and `/` are two doors to "
      "one mechanism (ADR-505 D4), so a kind reachable from only one is a split. "
      "Parses the rendered arrays rather than grepping the token, because the "
      "token also lives in the ToolbarAction union and in these comments.",
      "csvtable" in _toolbar_kinds and "csvtable" in _slash_kinds,
      f"toolbar={sorted(_toolbar_kinds)} slash={sorted(_slash_kinds)}")

_editor_src = (WEB / "components" / "text" / "TextEditor.tsx").read_text(encoding="utf-8")
_editor_nc = _strip_comments(_editor_src)
check("18j the CSV insert reads the document from the CANVAS at apply time "
      "(`canvasRef.current?.text()`), not from the React `text` closed over at "
      "pick time. It is the only insert that AWAITS I/O, so the member can type "
      "while the fetch is in flight — applying the captured string would delete "
      "those keystrokes (the D12 stale-prop shape, which shipped once already).",
      re.search(r"canvasRef\.current\?\.text\(\)", _editor_nc) is not None
      and "insertCsvTable(current" in _editor_nc,
      "a stale-string apply would silently destroy typing during the fetch")
# 18k re-anchored 2026-08-22 (transient-surfacing streamline): the failure
# notice moved from a hand-rolled bottom-center div (`setCsvError` + JSX) to
# the canonical toast layer — `reportAction`'s `error:` line. The BEHAVIOUR
# is unchanged and still what this check reads: a failed read INSERTS
# NOTHING (the catch body carries no insert; the insert lives inside the
# reportAction op, which rethrows on failure) and SAYS SO (the "nothing was
# inserted" copy rides the reportAction error option, in live code).
_csv_fn = re.search(r"const takeCsv[\s\S]*?\n  \);", _editor_nc)
_csv_fn_body = _csv_fn.group(0) if _csv_fn else ""
_csv_catch = re.search(r"\}\s*catch\s*\{([\s\S]*?)\}", _csv_fn_body)
_csv_catch_body = _csv_catch.group(1) if _csv_catch else ""
check("18k a FAILED read inserts NOTHING and says so — writing a source note "
      "with no rows under it would assert 'that file is empty', a different and "
      "false claim when the request simply failed. The catch body must not "
      "insert; the error copy must ride the canonical reportAction call.",
      _csv_fn is not None
      and _csv_catch is not None
      and "insertCsvTable" not in _csv_catch_body
      and "applyEdit" not in _csv_catch_body
      and "reportAction(" in _csv_fn_body
      and re.search(r"error:\s*`[^`]*nothing was inserted", _csv_fn_body) is not None,
      f"catch body: {_csv_catch_body.strip()[:160]!r}")

# ⚠️ RE-ANCHORED 2026-08-24. The original required Strings to IMPORT the
# shared parser — but the ADR-595 tending-surface rewrite removed CSV
# *parsing* from StringsSurface entirely (it renders "N rows" summaries,
# never a parsed grid), so the import requirement pinned a consumer that no
# longer exists and read the removal as "a second parser was reintroduced"
# (it wasn't — measured at clean HEAD). The LAW is unchanged and still held:
# ONE quote-aware parser, in markdownEdits, and no surface declares its own.
_strings_src = (WEB / "components" / "strings" / "StringsSurface.tsx").read_text(encoding="utf-8")
_md_edits_src = (WEB / "components" / "text" / "markdownEdits.ts").read_text(encoding="utf-8")
check("18L ONE CSV parser, not two. The shared quote-aware parser lives in "
      "markdownEdits (a naive split(',') makes \"Kim, Kevin\" two cells and "
      "shifts every later column silently); no other surface may declare its "
      "own. Strings imports it IF it parses — today it renders row-count "
      "summaries and parses nothing.",
      re.search(r"export function parseCsv", _md_edits_src) is not None
      and re.search(r"function\s+parseCsv", _strings_src) is None,
      "a second CSV parser exists, or the shared one moved")


# ── 19. ADR-575 — the surface HEARS other principals' writes ─────────────
# Operator drove the deployed surface and found three claims on one screen
# that cannot all be true: a conflict banner ("someone else revised this"),
# the header reading "Editing…" (whose copy means *nothing is at risk*), and
# Properties reading "No revisions yet."
#
# Measured on production — /workspace/seulki/babo-song-concept.md had FOUR
# revisions (three `operator`, one `yarnnn:mcp:claude.ai`) while the open
# editor said it had none. Two defects with ONE root: every mutation path
# bumped `reloadKey` EXCEPT autosave, and nothing subscribed to peer writes,
# so a 409 was the FIRST notice anyone else had touched the document.
_load_src = (WEB / "components" / "workspace" / "useFileLoad.ts").read_text(encoding="utf-8")
_load_nc = _strip_comments(_load_src)
_rt_path = WEB / "lib" / "realtime" / "use-file-revisions-realtime.ts"
_rt_src = _rt_path.read_text(encoding="utf-8") if _rt_path.exists() else ""
_rt_nc = _strip_comments(_rt_src)

# The commit() success branch, isolated. Asserting over the whole file would
# match the `refreshRevision` in useFileLoad's import or in a comment — the
# name-vs-behaviour trap this arc has now paid for eight times.
_commit_ok = re.search(
    r"const res = await api\.workspace\.editFile\(([\s\S]*?)\} catch", _editor_nc)
_commit_body = _commit_ok.group(1) if _commit_ok else ""
check("19a ⭐ THE ROOT — a successful save REFRESHES the head revision. Every "
      "mutation path bumped `reloadKey` except autosave, the one that runs "
      "constantly, so Properties' LAST EDITED was frozen at MOUNT: production "
      "showed 'No revisions yet.' on a file with four revisions.",
      _commit_ok is not None and "refreshRevision()" in _commit_body,
      f"commit success branch: {_commit_body.strip()[:200]!r}")
check("19b the refresh is REVISION-ONLY, never a full reload. `reloadKey` "
      "re-runs `getFile`, which re-fires the consumer's `setText(content)` "
      "effect — a keystroke landing during that refetch is destroyed (the "
      "D12 stale-prop shape, already shipped once here). A save changes the "
      "revision, not the member's text.",
      "setReloadKey" not in _commit_body
      and "refreshRevision" in _load_nc
      and re.search(r"refreshRevision\s*=\s*useCallback", _load_nc) is not None,
      f"commit success branch: {_commit_body.strip()[:200]!r}")
check("19c useFileLoad exposes ONE head-revision fetcher, shared by mount and "
      "refresh — two fetchers could disagree about what 'the head' is",
      _load_nc.count("listRevisions") == 1
      and "fetchHeadRevision" in _load_nc, str(_load_nc.count("listRevisions")))

check("19d ⭐ the surface SUBSCRIBES to this file's revisions (ADR-575). The "
      "conflict banner was the FIRST notice of a peer write, because "
      "whole-document CAS with no subscription discovers a collision only at "
      "save time. Notion's members never see that screen — rendering a record "
      "subscribes the client, and the server pushes a version on commit.",
      "useFileRevisionsRealtime" in _editor_nc
      and "workspace_file_versions" in _rt_nc
      and "postgres_changes" in _rt_nc,
      "no realtime subscription on the open document")
check("19e the subscription filters SERVER-side to this one path — filtering "
      "in the callback would ship every workspace revision to every open "
      "editor and discard them locally",
      re.search(r"filter:\s*`path=eq\.\$\{path\}`", _rt_nc) is not None,
      "the filter is not server-side on path")
check("19f ⭐ the member's OWN save is not reported back to them as a peer "
      "edit. Every autosave INSERTs a revision that returns down this channel; "
      "without the echo rule the surface would accuse the member of editing "
      "behind their own back, ~2s after every pause.",
      "isOwnWrite" in _rt_nc and "ownRevisions" in _editor_nc
      and re.search(r"ownRevisions\.current\.add", _editor_nc) is not None
      and re.search(r"isOwnWrite:\s*\(row\)\s*=>\s*ownRevisions\.current\.has", _editor_nc)
      is not None,
      "the editor's own revisions are not filtered from the feed")
check("19g `ownRevisions` is declared ABOVE `commit`, which writes to it. A "
      "`const` read before its declaration line is a temporal-dead-zone THROW "
      "at runtime — invisible to tsc and to `next build`, which is exactly "
      "the class of defect this app keeps shipping green.",
      _editor_nc.index("const ownRevisions") < _editor_nc.index("const commit = useCallback"),
      "ownRevisions is declared after commit — TDZ throw on first save")
check("19h a peer revision arriving with NO unsaved text reloads silently; "
      "with unsaved text it NOTIFIES instead. Reloading over unsaved text "
      "would discard the member's typing — the two cases are different and "
      "conflating them is what made the old banner confusing.",
      re.search(r"if \(textRef\.current === baselineRef\.current\)[\s\S]{0,80}setReloadKey",
                _editor_nc) is not None
      and "setPeerEdit" in _editor_nc,
      "the peer-write handler does not branch on unsaved text")

check("19i the header does NOT read 'Editing…' while a conflict suspends "
      "autosave. The effect returns early on `conflict`, so nothing will be "
      "written until the member chooses — but 'Editing…' was chosen to mean "
      "*nothing is at risk*. Three mutually exclusive claims were on one "
      "screen; this is the copy half.",
      re.search(r"conflict \?[\s\S]{0,400}?Paused", _editor_nc) is not None
      and re.search(r"\) : dirty \?\s*\(\s*'Editing…'", _editor_nc) is not None,
      "the status label still reads Editing… during a conflict")

_mig = (API.parent / "supabase" / "migrations"
        / "240_adr575_file_versions_realtime_publication.sql")
_mig_src = _mig.read_text(encoding="utf-8") if _mig.exists() else ""
# The publication-verify block ONLY. The first spelling required
# `pg_publication_tables` + `RAISE EXCEPTION` anywhere in the file and PASSED
# its own falsification — deleting the whole verify block left both tokens in
# the SIBLING RLS block below it. NINTH occurrence this arc of an assertion
# matching a token that lives somewhere else; extract the branch, then assert.
_pub_verify = re.search(
    r"SELECT EXISTS \([\s\S]*?pg_publication_tables[\s\S]*?\) INTO in_pub;"
    r"[\s\S]*?IF NOT in_pub THEN[\s\S]*?RAISE EXCEPTION[\s\S]*?END IF;",
    _mig_src)
check("19j the migration PUBLISHES the table and verifies the LIVE object — "
      "an ALTER that silently no-ops still exits 0, and a subscription on an "
      "unpublished table receives NOTHING while reporting SUBSCRIBED (the "
      "failure that reads as 'realtime is wired and quiet')",
      "ALTER PUBLICATION supabase_realtime ADD TABLE public.workspace_file_versions" in _mig_src
      and _pub_verify is not None
      and "workspace_file_versions" in _pub_verify.group(0),
      "migration 240 missing, or its publication-verify block is absent")
_sess_rt = (WEB / "lib" / "realtime" / "use-session-messages-realtime.ts").read_text(encoding="utf-8")
check("19L ⭐⭐⭐ THE SOCKET CARRIES THE USER'S TOKEN (`realtime.setAuth`). "
      "FOUND BY DRIVING PRODUCTION, invisible to 232 green checks. Realtime "
      "re-checks RLS per subscriber using the JWT the SOCKET carries — not the "
      "one the REST calls carry. Without setAuth the socket connects as anon, "
      "`auth.uid()` is NULL inside the policy, and every row is dropped while "
      "the channel still reports \"Subscribed to PostgreSQL\" with the correct "
      "filter. Measured: the `phx_join` frame carried no access_token, a peer "
      "write landed as a real revision row, and the client got only heartbeats. "
      "BOTH realtime hooks must do it — the omission was latent in the "
      "session-messages hook first, which is where this pattern was copied from.",
      "realtime.setAuth" in _strip_comments(_rt_src)
      and "realtime.setAuth" in _strip_comments(_sess_rt)
      and "resolveAccessToken" in _strip_comments(_rt_src)
      and "resolveAccessToken" in _strip_comments(_sess_rt),
      "a realtime hook subscribes without handing the socket the user's JWT")

_tokmod = WEB / "lib" / "realtime" / "access-token.ts"
_tok_src = _tokmod.read_text(encoding="utf-8") if _tokmod.exists() else ""
check("19o the token resolver FALLS BACK to the auth cookie. `getSession()` on "
      "the legacy `createClientComponentClient` yielded NO token on the "
      "deployed surface — measured: the join carried no access_token and "
      "delivered nothing even after setAuth shipped. Proven by joining a raw "
      "socket with `access_token: <cookie[0]>`, which DID receive a real "
      "postgres_changes INSERT frame for the same peer write.",
      "getSession" in _strip_comments(_tok_src)
      and re.search(r"sb-.*-auth-token", _tok_src) is not None
      and "Array.isArray" in _strip_comments(_tok_src),
      "the resolver has no cookie fallback — the socket stays anon")
check("19m setAuth is sequenced BEFORE subscribe() in the file-revisions hook — "
      "fire-and-forget beside the join is a race whose losing side is SILENT: "
      "it resolves from cache locally and fails on a cold load",
      # Assert the ORDER by index, not by a windowed regex. The first spelling
      # used `[\s\S]{0,400}` between setAuth and .channel and FAILED against
      # correct code — the real gap is 632 chars to .subscribe. A window is a
      # guess about formatting; an index comparison is the actual claim.
      (lambda s: (
          "setAuth" in s
          and s.index("setAuth") < s.index(".channel(") < s.index(".subscribe(")
      ))(_strip_comments(_rt_src)),
      "the join is not sequenced behind the session read")

_mig241 = (API.parent / "supabase" / "migrations"
           / "241_adr575_file_versions_replica_identity_full.sql")
_mig241_src = _mig241.read_text(encoding="utf-8") if _mig241.exists() else ""
# SQL comments stripped before asserting: the first spelling required
# "REPLICA IDENTITY FULL" anywhere in the file and PASSED its own
# falsification — deleting the ALTER left the phrase in this migration's own
# explanatory header. TENTH occurrence this arc of a check matching prose
# instead of code.
_mig241_code = re.sub(r"^\s*--.*$", "", _mig241_src, flags=re.MULTILINE)
check("19n REPLICA IDENTITY FULL on the published table — Realtime evaluates "
      "RLS against the row as reconstructed FROM THE WAL RECORD, which under "
      "DEFAULT carries only the primary key. This table's policy keys on "
      "`workspace_id`, which is NOT the PK, so it reads NULL there. Verified "
      "live: relreplident = 'f'.",
      re.search(r"ALTER TABLE public\.workspace_file_versions\s+REPLICA IDENTITY FULL",
                _mig241_code) is not None
      and "relreplident" in _mig241_code
      and "RAISE EXCEPTION" in _mig241_code,
      "migration 241 missing or does not verify replica identity")

check("19k the migration REFUSES to publish if RLS is off. Publishing to a "
      "replication slot is the moment a disabled RLS flag stops being latent "
      "and starts broadcasting every workspace's revision feed. Falsified "
      "against production: the member sees 2 workspaces / 1517 rows of 6 / "
      "1758; a principal with no grants sees 0.",
      "relrowsecurity" in _mig_src and "refused" in _mig_src.lower(),
      "the migration does not check RLS before publishing")


# ── 20. ADR-575 D8 — the BLOCK markers, which live preview never covered ──
# Operator, driving the canvas: "inserted formattings, when clicking enter it
# disappears, undo, and alike."
#
# Measured on the deployed surface before any fix: every entry in
# HIDDEN_MARKS is an INLINE mark, so `#`, `**` and `` ` `` were suppressed
# while every BLOCK marker leaked through as literal source —
#
#   Bulleted list  → rendered "- first item", dash and all
#   Task list      → rendered "- [ ] ", no checkbox
#   Divider        → rendered "---", no rule
#   An EMPTY list line ("- " alone) → a BLANK line with no bullet at all,
#                     which is the "it disappears" the operator reported
#
# The reading face was half-built: inline marks hidden, the structure they sit
# inside still showing its source. §20 mounts the REAL canvas and reads what it
# painted, because no source check can see which glyph a decoration produced.
_D20_PROBE = r"""
const fs = require('fs'), path = require('path');
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

const DOC = [
  '# Title',
  '',
  '- first item',
  '- second item',
  '',
  '1. one',
  '2. two',
  '',
  '- [ ] open',
  '- [x] done',
  '',
  '---',
  '',
  '> a quote',
  '> spanning two lines',
  '',
  'after',
  '',
].join('\n');

let value = DOC;
const host = dom.window.document.getElementById('h');
act(() => createRoot(host).render(React.createElement(ProseCanvas, {
  value, onChange: (v) => { value = v; },
})));

const txt = host.querySelector('.cm-content').textContent;
const bullets = [...host.querySelectorAll('.cm-mdBullet')].map((e) => e.textContent);
const tasks = [...host.querySelectorAll('.cm-mdTask')].map((e) => e.textContent);

// The empty-list-line case the operator hit: `- ` with nothing after it must
// still paint a bullet, not vanish into a blank line.
const EMPTY = 'text\n\n- ';
let v2 = EMPTY;
const host2 = dom.window.document.createElement('div');
dom.window.document.body.appendChild(host2);
act(() => createRoot(host2).render(React.createElement(ProseCanvas, {
  value: v2, onChange: (v) => { v2 = v; },
})));
const emptyBullets = host2.querySelectorAll('.cm-mdBullet').length;

// ── ADR-575 D8.c — the divider as a GRABBABLE OBJECT ────────────────────
// Driven on its own canvas so the selection dispatched below cannot disturb
// the shared fixture the checks above read.
const { EditorView: _EV } = require(WEB + '/node_modules/@codemirror/view');
const RULE_DOC = 'Above\n\n---\n\nBelow\n';
const host3 = dom.window.document.createElement('div');
dom.window.document.body.appendChild(host3);
let v3 = RULE_DOC;
act(() => createRoot(host3).render(React.createElement(ProseCanvas, {
  value: v3, onChange: (v) => { v3 = v; },
})));
const view3 = _EV.findFromDOM(host3.querySelector('.cm-editor'));
const rule3 = () => host3.querySelector('.cm-mdRule');
const ruleAt = RULE_DOC.indexOf('---');
// An EMPTY inline-block has a 0px content box: its whole hit target is the
// 1px border. A real inline content node is what makes it clickable.
const ruleHasContentNode = !!(rule3() && rule3().firstChild);
act(() => view3.dispatch({ selection: { anchor: ruleAt, head: ruleAt + 3 } }));
const ruleSelectedOnCover = !!(rule3() && rule3().className.includes('cm-mdObjSelected'));
act(() => view3.dispatch({ selection: { anchor: ruleAt + 1, head: ruleAt + 2 } }));
const rulePartialNotSelected = !!(rule3() && !rule3().className.includes('cm-mdObjSelected'));
act(() => view3.dispatch({ selection: { anchor: 0, head: 0 } }));
const ruleDeselects = !!(rule3() && !rule3().className.includes('cm-mdObjSelected'));
const ruleDocIdentical = v3 === RULE_DOC;

console.log(JSON.stringify({
  rule_has_content_node: ruleHasContentNode,
  rule_selected_on_cover: ruleSelectedOnCover,
  rule_partial_not_selected: rulePartialNotSelected,
  rule_deselects: ruleDeselects,
  rule_doc_identical: ruleDocIdentical,
  // No literal source markers survive in the rendered text.
  no_literal_dash: !/^- /m.test(txt),
  no_literal_ordered: !/^\d+\. /m.test(txt),
  no_literal_task: !txt.includes('[ ]') && !txt.includes('[x]'),
  no_literal_rule: !txt.split('\n').some((l) => l.trim() === '---'),
  // …because each was replaced by a real affordance.
  bullet_glyphs: bullets.filter((b) => b === '•').length === 2,
  ordered_keeps_number: bullets.includes('1.') && bullets.includes('2.'),
  task_boxes: tasks.length === 2 && tasks.includes('☐') && tasks.includes('☑'),
  rule_drawn: host.querySelectorAll('.cm-mdRule').length === 1,
  // A task line paints a BOX, never a box AND a bullet.
  no_double_marker: bullets.length === 4,
  // The whole point: decoration only. The document is untouched.
  doc_byte_identical: value === DOC,
  // The operator's case.
  empty_list_line_shows_bullet: emptyBullets === 1,
  // ADR-575 D9 — EVERY line of a quote carries the class, so a multi-line
  // quote reads as one block rather than a bar beside its first line only.
  quote_lines_marked: host.querySelectorAll('.cm-line.cm-mdQuote').length === 2,
  // …and the `>` leaves no hanging space behind it.
  quote_has_no_leading_space: [...host.querySelectorAll('.cm-line.cm-mdQuote')]
    .every((l) => !/^\s/.test(l.textContent)),
}));
"""

try:
    _d20 = json.loads(
        subprocess.run(
            ["node", "-e", _D20_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=180, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d20 = {"error": str(exc)[:400]}

check("20a ⭐⭐⭐ NO BLOCK MARKER SURVIVES AS LITERAL SOURCE. Every entry in "
      "HIDDEN_MARKS is an INLINE mark, so live preview hid `#`/`**`/`` ` `` "
      "and left `- `, `1. `, `[ ]` and `---` showing. The reading face was "
      "half-built. Measured on production, not inferred.",
      _d20.get("no_literal_dash") is True
      and _d20.get("no_literal_ordered") is True
      and _d20.get("no_literal_task") is True
      and _d20.get("no_literal_rule") is True, str(_d20)[:400])
check("20b a bullet is a GLYPH, and an ordered marker KEEPS ITS NUMBER — "
      "replacing `1.` with a dot would make the document lie about its own "
      "sequence",
      _d20.get("bullet_glyphs") is True
      and _d20.get("ordered_keeps_number") is True, str(_d20)[:400])
check("20c a task marker is a real BOX, checked state carried, and a task line "
      "paints a box NEVER a box AND a bullet",
      _d20.get("task_boxes") is True
      and _d20.get("no_double_marker") is True, str(_d20)[:400])
check("20d a thematic break is a RULE. Hiding it outright would leave a blank "
      "line that reads as an accident — which is why these are replaced by "
      "widgets rather than added to HIDDEN_MARKS.",
      _d20.get("rule_drawn") is True, str(_d20)[:400])
check("20e ⭐ THE OPERATOR'S CASE — an EMPTY list line (`- ` with nothing "
      "after it) still paints a bullet. Erasing the marker made a fresh list "
      "item indistinguishable from a blank line: press the button, watch the "
      "formatting 'disappear'.",
      _d20.get("empty_list_line_shows_bullet") is True, str(_d20)[:400])
_canvas_src = (WEB / "components" / "text" / "ProseCanvas.tsx").read_text(encoding="utf-8")
_canvas_nc = _strip_comments(_canvas_src)
_rule_block = re.search(r"'\.cm-mdRule':\s*\{(.*?)\}", _canvas_nc, re.S)
check("20g ⭐ the rule uses BORDER LONGHANDS, not the `borderTop` shorthand. "
      "Driven after the first cut shipped: the divider rendered with "
      "`borderTopWidth: 0px` and was INVISIBLE — a blank gap where a rule "
      "should be, which is worse than the literal `---` it replaced. "
      "CodeMirror's theme compiler did not carry the shorthand through; "
      "`.cm-cursor` in this same theme already uses longhands for this reason. "
      "A shorthand here fails SILENTLY — it renders, it just renders nothing.",
      _rule_block is not None
      and "borderTopWidth" in _rule_block.group(1)
      and "borderTopStyle" in _rule_block.group(1)
      and "borderTop:" not in _rule_block.group(1),
      f"rule block: {_rule_block.group(1).strip()[:160] if _rule_block else 'absent'!r}")

# ── ADR-575 D8.c — the divider must be GRABBABLE, not merely visible ──────
# Operator: "objects like divider aren't grabbable, or selectable via mouse
# clicks." 20d/20g only ever asked whether the rule was DRAWN, and it was — so
# 249 checks stayed green over a widget the mouse could not reach. Drawing an
# object and being able to touch it are two different claims, and only the
# first one was ever made.
check("20p ⭐⭐⭐ THE DIVIDER HAS A HIT TARGET. The widget was a bare empty "
      "<span> styled only with a top border, so its content box was 0px tall "
      "and its ENTIRE clickable area was the 1px border — it rendered "
      "perfectly and could not be clicked, dragged across, or selected. Every "
      "OTHER widget here (bullet, task box, table) ships real content and was "
      "hittable for free, which is exactly why this defect survived the gate: "
      "20d asked 'is it drawn?', never 'can it be touched?'",
      _d20.get("rule_has_content_node") is True, str(_d20)[:300])
check("20q ⭐ …and it also needs HEIGHT, or the content node has nothing to "
      "sit in. The band the rule visually occupies belongs to the rule, with "
      "negative margins keeping the drawn line exactly where 20g put it — a "
      "hit target that moves the pixels is a different bug, not a fix.",
      _rule_block is not None
      and "height" in _rule_block.group(1)
      and "marginTop" in _rule_block.group(1),
      f"rule block: {_rule_block.group(1).strip()[:200] if _rule_block else 'absent'!r}")
check("20r ⭐ a divider inside a selection READS as selected. CodeMirror's "
      "selection tint is drawn for TEXT, so a widget in a dragged-over range "
      "stayed visually untouched while every character around it highlighted "
      "— the selection appeared to skip the object.",
      _d20.get("rule_selected_on_cover") is True, str(_d20)[:300])
check("20s …and a selection that only PARTLY overlaps the rule does not "
      "claim it, nor does a collapsed caret — an object is selected when it "
      "is COVERED, which is the test the member's eye applies",
      _d20.get("rule_partial_not_selected") is True
      and _d20.get("rule_deselects") is True, str(_d20)[:300])
check("20t the selection repaint keeps the document BYTE-IDENTICAL — the "
      "selected state is decoration like everything else here, so ADR-456 D1 "
      "holds with an object highlighted on screen",
      _d20.get("rule_doc_identical") is True, str(_d20)[:300])
check("20u ⭐ the preview plugin rebuilds on `selectionSet`. It listened only "
      "for `docChanged || viewportChanged`, and a selection change moves "
      "neither — so without this the selected state computed above could "
      "never repaint, and 20r would be true in principle and invisible in "
      "practice.",
      re.search(r"u\.docChanged \|\| u\.viewportChanged \|\| u\.selectionSet",
                _canvas_nc) is not None,
      "the live-preview plugin ignores selection changes")

_D20B_PROBE = r"""
const fs = require('fs');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
const load = (rel) => {
  const js = transform(fs.readFileSync(WEB + rel, 'utf8'),
    { transforms: ['typescript', 'imports'] }).code;
  const m = { exports: {} };
  new Function('module', 'exports', 'require', js)(m, m.exports, () => ({}));
  return m.exports;
};
const O = load('/components/text/outline.ts');
const names = (src) => O.parseOutline(src).map((e) => e.level + ':' + e.text);
console.log(JSON.stringify({
  // The operator's case: Enter at the end of a list leaves `- ` behind it.
  list_is_not_heading: JSON.stringify(names('# Title\n\n- a\n- b\n- \n')) === '["1:Title"]',
  // A bare `-` (no trailing space) is still a list item, not an underline.
  bare_dash_is_not_heading: names('# T\n\n- a\n-\n').length === 1,
  // …while REAL setext headings still parse.
  setext_h2_survives: JSON.stringify(names('My Section\n---\n')) === '["2:My Section"]',
  setext_h1_survives: JSON.stringify(names('My Title\n===\n')) === '["1:My Title"]',
  // `---` after a blank line is a thematic break, not a heading (unchanged).
  rule_is_not_heading: names('para\n\n---\n').length === 0,
}));
"""

try:
    _d20b = json.loads(
        subprocess.run(
            ["node", "-e", _D20B_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001
    _d20b = {"error": str(exc)[:300]}

check("20h ⭐ A LIST IS NOT A HEADING. Found by driving the canvas: pressing "
      "Enter at the end of a bulleted list leaves `- ` on its own line, which "
      "matched the setext-underline regex — so the outline listed the item "
      "above it as an H2 and Properties counted two headings in a "
      "one-heading document. Measured against @lezer/markdown: the real parser "
      "sees three LIST ITEMS and zero headings there. Both sides of the pair "
      "are guarded — an underline may not be a list item, and a heading may "
      "not be one either.",
      _d20b.get("list_is_not_heading") is True
      and _d20b.get("bare_dash_is_not_heading") is True, str(_d20b)[:300])
check("20i …and REAL setext headings still parse. `---` is untouched by the "
      "list guard, so `My Section\\n---` is still an H2 and a `---` after a "
      "blank line is still a thematic break. A fix that silenced setext "
      "entirely would have passed 20h and broken the feature.",
      _d20b.get("setext_h2_survives") is True
      and _d20b.get("setext_h1_survives") is True
      and _d20b.get("rule_is_not_heading") is True, str(_d20b)[:300])

_sel_rule = re.search(
    r"'&\.cm-focused > \.cm-scroller > \.cm-selectionLayer \.cm-selectionBackground'",
    _canvas_nc)
check("20j ⭐ the selection rule MATCHES CodeMirror's own specificity. Measured "
      "on the deployed canvas: the computed background was `rgb(215,212,240)` "
      "— the library's OPAQUE default — not the translucent tint the theme "
      "declares, because CodeMirror ships "
      "`.ͼ2.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground` "
      "which outranks a bare `&.cm-focused .cm-selectionBackground`. The theme's "
      "colour had NEVER applied, and an opaque slab COVERS the glyphs instead "
      "of tinting them — a selection that reads as a block painted over the "
      "text. `!important` is deliberately avoided: it would outrank a future "
      "theme too.",
      _sel_rule is not None, "the selection rule cannot outrank the library default")

_quote_rule = re.search(r"'\.cm-line\.cm-mdQuote':\s*\{(.*?)\}", _canvas_nc, re.S)
check("20k ⭐ a BLOCKQUOTE is set aside — a left bar and an indent, not just "
      "italics. The `>` is hidden, so the only treatment was `opacity: 0.8` on "
      "the text and a quote rendered as a slightly-grey paragraph with a stray "
      "leading space. Longhand borders, for the D8.a reason: the theme "
      "compiler drops the shorthand and the bar would be invisible.",
      _quote_rule is not None
      and "borderLeftWidth" in _quote_rule.group(1)
      and "borderLeftStyle" in _quote_rule.group(1)
      and "paddingLeft" in _quote_rule.group(1)
      and "borderLeft:" not in _quote_rule.group(1),
      f"quote rule: {_quote_rule.group(1).strip()[:150] if _quote_rule else 'absent'!r}")
check("20m EVERY line of a multi-line quote carries the class (mounted and "
      "read back), so a quote reads as ONE block rather than a bar beside its "
      "first line — and the `>` leaves no hanging space",
      _d20.get("quote_lines_marked") is True
      and _d20.get("quote_has_no_leading_space") is True, str(_d20)[:400])
check("20L the quote's `>` swallows its trailing SPACE, as `# ` does — "
      "otherwise the line keeps a hanging indent, which is the stray space "
      "visible before 'a quote' in the operator's screenshot",
      re.search(r"QuoteMark'\s*\)\s*&&", _canvas_nc) is not None
      or re.search(r"node\.name === 'QuoteMark'[\s\S]{0,120}end \+= 1", _canvas_nc) is not None,
      "the quote marker leaves its trailing space behind")

check("20f the document is BYTE-IDENTICAL with every widget on screen — these "
      "are decorations, not content. Delete them and the `.md` is unchanged "
      "(the same test D13/D15 pass).",
      _d20.get("doc_byte_identical") is True, str(_d20)[:400])


# ── 21. a block insert does not DESTROY what is already there (D19) ──────
# Operator: "even a divider that gets added, it cancels another line."
#
# Every block insert computed its own `before`/`after` as `slice(0, start)` +
# `slice(end)`, which DELETES `[start, end)`. Correct for a collapsed caret;
# with a selection it silently removes the selected text — and a toolbar is
# used precisely by selecting something and pressing a button. Five of the six
# did this. `insertFence` alone survived, because it happened to reuse the
# selection as the fence body.
#
# Two properties, checked by EXECUTION over every caret position rather than
# by grepping for `blockSite`: a symbol can be present and still be wrong.
#
#   - NOTHING IS LOST. Every non-blank line of the document is still there,
#     intact, whatever the caret was doing.
#   - A BLOCK LANDS BETWEEN BLOCKS. With the caret mid-sentence the old code
#     wedged the block into the middle of the line ("Two tiers, " / rule /
#     "low-friction first."), turning one paragraph into two.
_INSERT_PROBE = r"""
const fs = require('fs');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
const js = transform(fs.readFileSync(WEB + '/components/text/markdownEdits.ts', 'utf8'),
  { transforms: ['typescript', 'imports'] }).code;
const m = { exports: {} };
new Function('module', 'exports', 'require', js)(m, m.exports, () => ({}));
const M = m.exports;

const DOC = [
  '# Campaign open brief', '',
  'Why this wording: it costs one email.', '',
  '## 3. Submission route', '',
  'Two tiers, low-friction first.', '',
  '- Tier 1 - tag to play.',
  '- Tier 2 - the room.', '',
  'Final paragraph.',
].join('\n');
const LINES = DOC.split('\n').filter((l) => l.trim());

const K = {
  table:   (t, s, e) => M.insertTable(t, s, e),
  rule:    (t, s, e) => M.insertRule(t, s, e),
  code:    (t, s, e) => M.insertFence(t, s, e),
  mermaid: (t, s, e) => M.insertMermaid(t, s, e),
  image:   (t, s, e) => M.insertImage(t, s, e, 'img/a.png'),
  csv:     (t, s, e) => M.insertCsvTable(t, s, e, 'd.csv', 'a,b\n1,2\n', new Date(2026, 0, 1)),
};

// (1) every collapsed caret keeps every line whole
const split = [];
for (const [name, f] of Object.entries(K)) {
  for (let at = 0; at <= DOC.length; at++) {
    const out = f(DOC, at, at).text;
    for (const L of LINES) if (!out.includes(L)) { split.push(name + '@' + at); break; }
  }
}

// (2) a SELECTION survives verbatim. `code` is exempt and asserted separately:
// a fence WRAPS the selection, which keeps it too, just not adjacent.
const eaten = [];
for (const [name, f] of Object.entries(K)) {
  for (let i = 0; i < DOC.split('\n').length; i++) {
    for (let j = i; j < DOC.split('\n').length; j++) {
      const rows = DOC.split('\n');
      const s = rows.slice(0, i).join('\n').length + (i ? 1 : 0);
      const e = rows.slice(0, j + 1).join('\n').length;
      const sel = DOC.slice(s, e);
      if (!sel.trim()) continue;
      if (!f(DOC, s, e).text.includes(sel)) eaten.push(name + ':' + i + '-' + j);
    }
  }
}

// (3) the operator's exact gesture: select a paragraph, press Divider.
const ps = DOC.indexOf('Two tiers');
const pe = ps + 'Two tiers, low-friction first.'.length;
const ruled = M.insertRule(DOC, ps, pe).text;

// (4) pressing twice must not pile up blank lines
const twice = (name) => {
  const f = K[name];
  const a = f(DOC, pe, pe);
  return /\n{4,}/.test(f(a.text, a.selectionStart, a.selectionEnd).text);
};

// (5) mid-line caret: the sentence stays in one piece, block lands after it
const mid = DOC.indexOf('low-friction');

console.log(JSON.stringify({
  no_split: split.length === 0, split_sample: split.slice(0, 4),
  no_eaten: eaten.length === 0, eaten_sample: eaten.slice(0, 4),
  divider_keeps_paragraph: ruled.includes('Two tiers, low-friction first.'),
  divider_lands_after: ruled.indexOf('---') > ruled.indexOf('low-friction first.'),
  fence_wraps_selection:
    M.insertFence(DOC, ps, pe).text.includes('```\nTwo tiers, low-friction first.\n```'),
  no_pileup: !['table', 'rule', 'code', 'mermaid', 'image', 'csv'].some(twice),
  midline_intact: Object.values(K).every(
    (f) => f(DOC, mid, mid).text.includes('Two tiers, low-friction first.')),
}));
"""

try:
    _ins = json.loads(
        subprocess.run(
            ["node", "-e", _INSERT_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate
    _ins = {"error": str(exc)}

check("21a ⭐⭐⭐ AN INSERT NEVER DELETES A SELECTION. The operator's report — "
      "'even a divider that gets added, it cancels another line'. Five of the "
      "six block inserts computed `slice(0,start) + slice(end)`, which drops "
      "`[start,end)`; select a paragraph, press Divider, and the paragraph is "
      "gone. Checked by EXECUTING every whole-line selection in a real "
      "document, because the old code contained no wrong-looking symbol to "
      "grep for.",
      _ins.get("no_eaten") is True, str(_ins.get("eaten_sample"))[:300])
check("21b …and the operator's exact gesture is asserted on its own: select "
      "the paragraph, press Divider, the paragraph is still there and the "
      "rule lands AFTER it rather than on top of it",
      _ins.get("divider_keeps_paragraph") is True
      and _ins.get("divider_lands_after") is True, str(_ins)[:300])
check("21c ⭐ A BLOCK LANDS BETWEEN BLOCKS, never inside a line. With the "
      "caret mid-sentence the old code wedged the block between the halves "
      "('Two tiers, ' / rule / 'low-friction first.') — one paragraph became "
      "two and the sentence was cut. This is the same D11 question the line "
      "toggles already answered with `openNewLine`.",
      _ins.get("midline_intact") is True and _ins.get("no_split") is True,
      str(_ins.get("split_sample"))[:300])
check("21d the fence is the ONE exception and stays that way — it WRAPS the "
      "selection as its body, which is the obvious reading of 'make this "
      "code'. A fix that made every insert land after the selection would "
      "have silently removed this behaviour.",
      _ins.get("fence_wraps_selection") is True, str(_ins)[:300])
check("21e pressing an insert twice does not accumulate blank lines — the "
      "lead/tail padding is added only where it is missing, which is the "
      "property `blockSite` centralises instead of copying six times",
      _ins.get("no_pileup") is True, str(_ins)[:300])



# ── 22. the outline JUMPS, it does not select (D20) ──────────────────────
# Operator: "when i click the outline section, is there a reason it highlights
# only a part of the respective contents on the center render? or maybe we
# don't highlight or select it and just move them there?"
#
# Both halves of that were right. The jump dispatched a RANGE sized by the
# outline's stripped LABEL (`plain()` drops `#`, `**`, link targets) against an
# offset into the RAW line — so it fell short by exactly the markup, visibly
# ending mid-word on a plain `# ` heading and by 30+ chars on a link-heavy one.
#
# And fixing only the arithmetic would have preserved the worse defect: a
# focused range is a PENDING DELETE. Navigating the outline armed a state where
# the next keystroke replaced the heading. Going somewhere is not selecting
# something — which is what Studio's own outline already does
# (`FlowEditor` → `TextSelection.near`, never a range).
_JUMP_PROBE = r"""
const fs = require('fs'), path = require('path');
const WEB = process.argv[1];
const { transform } = require(process.argv[2]);
require.extensions['.tsx'] = require.extensions['.ts'] = function (m, f) {
  m._compile(transform(fs.readFileSync(f, 'utf8'),
    { transforms: ['typescript', 'jsx', 'imports'], jsxRuntime: 'automatic', production: true }).code, f);
};
const Module = require('module'); const orig = Module._resolveFilename;
Module._resolveFilename = function (r, ...a) {
  if (r.startsWith('@/')) {
    const b = path.join(WEB, r.slice(2));
    for (const e of ['', '.tsx', '.ts', '/index.tsx', '/index.ts']) {
      try { return orig.call(this, b + e, ...a); } catch (x) { /* next */ }
    }
  }
  return orig.call(this, r, ...a);
};
const { JSDOM } = require(WEB + '/node_modules/jsdom');
const dom = new JSDOM('<div id="h"></div>', { pretendToBeVisual: true });
const def = (k, v) => { global[k] = v; };
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
const O = require(WEB + '/components/text/outline.ts');
const E = require(WEB + '/components/text/markdownEdits.ts');
const EDITOR_SRC = fs.readFileSync(WEB + '/components/text/TextEditor.tsx', 'utf8');

// The operator's own heading, plus the markup shapes that widen the old error.
const DOCS = [
  "# DeepMind Releases New Forecasting Model; OpenAI's Hugging Face Incident Timeline Detailed\nbody.\n",
  '## See [the paper](https://x.com/a/b) and **this**\nbody.\n',
  'intro\n\n### Run `npm install` first\nbody.\n',
];

const out = { collapsed: true, at_start: true, doc_same: true, label_gap: false };
for (const DOC of DOCS) {
  let value = DOC, handle = null;
  const host = dom.window.document.createElement('div');
  dom.window.document.body.appendChild(host);
  act(() => createRoot(host).render(React.createElement(ProseCanvas, {
    value, onChange: (v) => { value = v; }, handleRef: (h) => { if (h) handle = h; },
  })));
  const h = O.parseOutline(DOC)[0];
  const off = E.offsetOfLine(DOC, h.line);
  const nl = DOC.indexOf('\n', off);
  act(() => handle.reveal(off, nl === -1 ? DOC.length : nl));
  const sel = handle.selection();
  if (sel[0] !== sel[1]) out.collapsed = false;      // a jump leaves NO range
  if (sel[0] !== off) out.at_start = false;          // …at the heading
  if (handle.text() !== DOC) out.doc_same = false;   // navigation writes nothing
  // The label really IS shorter than the line — i.e. the old arithmetic was
  // wrong, not merely different. Proves the defect was real for these inputs.
  if (h.text.length < DOC.slice(off, nl === -1 ? undefined : nl).length) out.label_gap = true;
}

// The call site must address the LINE, never the label's length. Comments
// stripped first: a check that can match its own explanation proves nothing.
const nc = EDITOR_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
out.no_label_length = !/reveal\(\[\s*off\s*,\s*off\s*\+\s*h\.text\.length/.test(nc);
out.addresses_line = /indexOf\('\\n',\s*off\)/.test(nc);

console.log(JSON.stringify(out));
"""

try:
    _jump = json.loads(
        subprocess.run(
            ["node", "-e", _JUMP_PROBE, str(WEB), str(WEB / "node_modules" / "sucrase")],
            capture_output=True, text=True, timeout=120, check=True,
        ).stdout
    )
except Exception as exc:  # noqa: BLE001 — an unrunnable probe is a FAILED gate
    _jump = {"error": str(exc)}

check("22a ⭐⭐⭐ THE OUTLINE JUMPS, IT DOES NOT SELECT. A focused range is a "
      "PENDING DELETE — the jump left `{anchor: from, head: to}` live in a "
      "focused editor, so the next keystroke replaced the heading the member "
      "had just navigated to. Going somewhere is not selecting something. "
      "Driven on the mounted canvas: the caret comes back COLLAPSED.",
      _jump.get("collapsed") is True, str(_jump)[:300])
check("22b …at the heading it was pointed at, and navigation WRITES NOTHING — "
      "the document is byte-identical after a jump",
      _jump.get("at_start") is True and _jump.get("doc_same") is True,
      str(_jump)[:300])
check("22c ⭐ the jump addresses the heading LINE, never the outline's LABEL. "
      "`plain()` strips `#`, `**` and link targets, so `off + h.text.length` "
      "fell short by exactly the markup — the operator's screenshot shows it "
      "ending mid-word at 'Detail|ed' (2 short, for `# `), and a link-heavy "
      "heading is off by 30+. Both the old spelling's ABSENCE and the line "
      "lookup's PRESENCE are asserted, over comment-stripped source.",
      _jump.get("no_label_length") is True and _jump.get("addresses_line") is True,
      str(_jump)[:300])
check("22d …and the gap it corrected was REAL for these inputs — the stripped "
      "label is measurably shorter than the source line, so 22c is guarding a "
      "defect rather than restating a preference",
      _jump.get("label_gap") is True, str(_jump)[:300])



# ── report ───────────────────────────────────────────────────────────────
failed = 0
for label, ok, detail in results:
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}{('  ' + detail) if detail and not ok else ''}")
    if not ok:
        failed += 1
print()
if failed:
    print(f"ADR-571 gate FAILED — {len(results) - failed}/{len(results)}")
    sys.exit(1)
print(f"ADR-571 gate GREEN — {len(results)}/{len(results)}")
