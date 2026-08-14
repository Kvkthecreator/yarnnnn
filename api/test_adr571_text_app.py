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
