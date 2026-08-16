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
check(
    "1b the colleague displays as Editor (the app's name over the resident)",
    (resolve_app("text") or {}).get("name") == "Editor",
    str(resolve_app("text")),
)

from services.agents_registry import KERNEL_AGENTS, KERNEL_POSTURES  # noqa: E402

check(
    "1c the resident is a REAL agent row (engine follows it, ADR-562)",
    _resident in KERNEL_AGENTS or _resident in KERNEL_POSTURES,
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
check("5i the rail is reachable at narrow rungs (never an inescapable state)",
      "sideIsOverlay" in _editor and "Properties and chat" in _editor)
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

check("6a the canvas RENDERS markdown (the headline gap: a brief must not "
      "read as a source dump)",
      "ProseReader" in _editor and "MarkdownRenderer" in _reader)
check("6b it reuses the ONE markdown pipeline (no second parser)",
      "react-markdown" not in _reader and "remark" not in _reader)
check("6c the reading face is a DOC skin, not the chat face",
      "prose-headings:font-serif" in _reader and "font-serif" in _reader)
check("6d Read|Write is a real toggle over one source",
      "'read'" in _editor and "'write'" in _editor and "mode === 'read'" in _editor)
check("6e zoom is a VIEW control with Docs' own clamp",
      "ZOOM_MIN = 0.25" in _editor and "ZOOM_MAX = 2" in _editor)
check("6f the markdown toolbar is mounted (Docs' Insert, in characters)",
      "MarkdownToolbar" in _editor)
check("6g find/replace is mounted and keyed to ⌘F",
      "FindReplaceBar" in _editor and "'f'" in _editor)
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

// find/replace is LITERAL, case-insensitive, and total.
out.find_counts = M.findAll('a A ab a', 'a').length === 4;
out.find_empty_is_none = M.findAll('abc', '').length === 0;
out.replace_all = M.replaceAll('a b a', 'a', 'X').text === 'X b X';
out.replace_one = M.replaceOne('a b a', [0, 1], 'X').text === 'X b a';

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
    ("quote_marks", "6v quote marks each line"),
    ("quote_untoggles", "6w quote toggles off"),
    ("link_shape", "6x a link keeps the selection as its TEXT"),
    ("link_caret_in_target", "6y the caret lands in the empty target"),
    ("table_is_gfm", "6z a table is GFM source on its own lines"),
    ("find_counts", "6aa find is literal + case-insensitive"),
    ("find_empty_is_none", "6ab an empty needle matches nothing"),
    ("replace_all", "6ac replace-all replaces every occurrence"),
    ("replace_one", "6ad replace-one replaces exactly one"),
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
