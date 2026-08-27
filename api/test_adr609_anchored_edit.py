"""ADR-609 — the member's selection is an ADDRESS, not a description.

Defends the whole funnel this ADR closes. Before it, a precise selection was
rendered to prose and the colleague had to re-find the target by string search
against a CLIPPED PREFIX; `EditFile` then demanded an exact, unique match over
the whole file. Two media, one defect.

EXECUTION-ANCHORED where it matters: the anchor resolver and the edit core are
imported and DRIVEN, not grepped. A grep can pass because an assertion matched
its own comment; only running the resolver proves a nested block does not eat
its sibling.

Run: python3 test_adr609_anchored_edit.py   (from api/)
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "api"
WEB = ROOT / "web"

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ── Load the pure core WITHOUT importing the service package ───────────────
# workspace.py pulls the whole substrate stack on import (py3.9 venv, supabase
# clients); the anchor core is pure and is exec'd on its own so this gate runs
# anywhere. The slice is bounded by real definitions, so a rename breaks the
# gate loudly rather than silently testing nothing.
_ws_src = read(API / "services" / "primitives" / "workspace.py")
_start = _ws_src.find("#: HTML void elements")
_end = _ws_src.find("async def handle_edit_file")
check("anchor core is locatable", _start != -1 and _end > _start,
      "the _VOID_TAGS/_resolve_anchor/_apply_edit block moved — re-anchor this gate")

if _start == -1 or _end <= _start:
    print("\n".join(f"FAIL {f}" for f in failures))
    sys.exit(1)

_ns: Dict[str, Any] = {"re": re, "Optional": Optional, "Any": Any,
                       "Dict": Dict, "List": List}
exec(compile(_ws_src[_start:_end], "workspace_anchor_core", "exec"), _ns)
resolve_anchor = _ns["_resolve_anchor"]
apply_edit = _ns["_apply_edit"]

# ── D1: the anchor resolves the member's ACTUAL span ───────────────────────
HTML = (
    '<div data-block="area" data-block-id="b1">'
    '<p>old text</p><div>NESTED</div><span>TAIL</span>'
    "</div>"
    '<p data-block-id="b2">old text</p>'
    '<img data-block-id="b3" src="x.png">'
)

span, err = resolve_anchor(HTML, {"block_id": "b1"})
check("D1 block anchor resolves", err is None and span is not None, str(err))
if span:
    got = HTML[span[0]:span[1]]
    # THE case depth-counting exists for: a same-tag child must not end the
    # span early. A regex to the first </div> would stop after NESTED.
    # TAIL sits AFTER the nested child's close: a resolver that stops at the
    # first </div> keeps NESTED and still ends in "</div>", so only content
    # past that point proves the depth count actually ran.
    check("D1 nested same-tag child does not truncate the span",
          "TAIL" in got and got.count("<div") == 2 and got.count("</div>") == 2,
          f"resolved {got!r}")
    check("D1 the span does not reach a sibling block",
          'data-block-id="b2"' not in got, f"resolved {got!r}")

span, _ = resolve_anchor(HTML, {"block_id": "b3"})
check("D1 a void element anchors to its own tag",
      span is not None and HTML[span[0]:span[1]].startswith("<img"),
      "void tags have no close tag to count to")

span, err = resolve_anchor("hello world", {"start": 6, "end": 11})
check("D1 offsets resolve to the exact span", span == (6, 11), str(err))

# Failures are NAMED, never silently clamped — a clamp would edit a region the
# member never selected, which is the ADR-373 D6 incorrect-success class.
_, err = resolve_anchor("hi", {"start": 0, "end": 99})
check("D1 an out-of-range span is refused, not clamped",
      err is not None and err.get("error") == "anchor_not_found", str(err))
_, err = resolve_anchor(HTML, {"block_id": "nope"})
check("D1 a missing block id is refused",
      err is not None and err.get("error") == "anchor_not_found", str(err))
_, err = resolve_anchor(HTML, {"block_id": "b1", "start": 1, "end": 2})
check("D1 one file has one address — both kinds is refused",
      err is not None and err.get("error") == "anchor_ambiguous", str(err))
span, err = resolve_anchor(HTML, None)
check("D1 no anchor is not an error", span is None and err is None, str(err))

# ── D1: the anchor CONFINES the edit ───────────────────────────────────────
# The proof that the anchor does real work: an edit that is AMBIGUOUS
# file-wide succeeds when anchored, and leaves the other occurrence alone.
out, err = apply_edit(HTML, "old text", "fresh", False, None)
check("D1 the unanchored contract still collides on an ambiguous string",
      err is not None and err.get("error") == "old_string_not_unique", str(err))

out, err = apply_edit(HTML, "old text", "fresh", False, {"block_id": "b1"})
check("D1 the SAME edit succeeds when anchored", err is None, str(err))
if out:
    check("D1 the anchored edit changed the target",
          "<p>fresh</p>" in out, out)
    check("D1 the anchored edit left the sibling block untouched",
          '<p data-block-id="b2">old text</p>' in out, out)

# Wholesale span replacement — the "rewrite THIS" case, no string to rebuild.
out, err = apply_edit(HTML, "", '<p data-block-id="b1">NEW</p>', False,
                      {"block_id": "b1"})
check("D1 omitting old_string replaces the span wholesale", err is None, str(err))
if out:
    check("D1 wholesale replace kept the rest of the file",
          'data-block-id="b2"' in out and 'data-block-id="b3"' in out, out)

out, err = apply_edit("hello world", "", "there", False, {"start": 6, "end": 11})
check("D1 a prose span replaces by offset", out == "hello there", str(err or out))

_, err = apply_edit(HTML, "zzz", "y", False, {"block_id": "b1"})
check("D1 a string absent from the span is refused",
      err is not None and err.get("error") == "old_string_not_found", str(err))

# The unanchored contract is UNCHANGED — this ADR adds a mode, never edits one.
_, err = apply_edit(HTML, "", "x", False, None)
check("D1 unanchored still requires old_string",
      err is not None and err.get("error") == "missing_old_string", str(err))
out, err = apply_edit("a b a", "b", "c", False, None)
check("D1 unanchored unique replace is byte-identical to before",
      out == "a c a", str(err or out))

# ── The module must actually IMPORT what the core uses ─────────────────────
# The exec above supplies `re` from this gate's own namespace, so a missing
# module-level import in workspace.py passes here and raises NameError in
# production on the first anchored edit. It DID: the gate was green while the
# real handler was broken. Assert the import the way the runtime resolves it.
check("the anchor core's `re` is imported at module level, not by the gate",
      re.search(r"^import re$", _ws_src, re.MULTILINE) is not None,
      "workspace.py must import re itself — exec'ing the core hides this")
check("`re` has ONE spelling in the module (no `import re as _re` alias)",
      "import re as _re" not in _ws_src,
      "two spellings of one dependency; singular implementation")


# ── D2: the extent travels — FE and wire ───────────────────────────────────
lane_panel = read(WEB / "components" / "chat-surface" / "LanePanel.tsx")
check("D2 SeedTarget carries the range",
      re.search(r"range:\s*\{\s*start:\s*number;\s*end:\s*number\s*\}\s*\|\s*null",
                lane_panel) is not None,
      "the extent must ride typed beside the clipped excerpt")
check("D2 the range goes up the wire",
      "range: t.range ?" in lane_panel, "seedToWire must send it")
check("D2 a persisted range reads back",
      "readRange" in lane_panel, "seedFromMeta must restore it")

text_editor = read(WEB / "components" / "text" / "TextEditor.tsx")
# The offsets used to be computed here and dropped on the next line.
check("D2 Text KEEPS the offsets the canvas reports",
      "const range = selection ? { start: from, end: to } : null;" in text_editor,
      "onCanvasSelection must retain the extent, not just its clipped name")
check("D2 Text has a gesture door at last",
      "rewriteSelection" in text_editor and "composerSeed={seed}" in text_editor,
      "the SeedTarget protocol was built and Text produced no seeds")
check("D2 the Text door carries the range",
      re.search(r"verb:\s*'rewrite'[\s\S]{0,400}range:\s*focusPoint\.range",
                text_editor) is not None,
      "a door that omits the extent rebuilds the defect")

lanes = read(API / "routes" / "lanes.py")
check("D2 LaneSeed accepts a range", "range: Optional[LaneSeedRange]" in lanes)
check("D2 LaneSeedRange is defined before use",
      lanes.find("class LaneSeedRange") < lanes.find("class LaneSeed("),
      "a forward reference here would depend on model_rebuild order")

# ── D3: the frame hands over the ADDRESS, not just the name ────────────────
runner = read(API / "services" / "lane_runner.py")
# DRIVEN, not grepped. The first version of these two checks searched the
# module for the f-string SOURCE — which survives intact when the code around
# it is dead. Falsified 2026-08-27: an early `return line` placed above the
# whole D3 clause left both greps matching their own comments while no seed
# line ever carried an anchor. Render the line and read what it SAYS.
_seed_src = read(API / "services" / "lane_runner.py")
_s0 = _seed_src.find("def _seed_line(")
_s1 = _seed_src.find("\ndef ", _s0 + 1)
check("D3 _seed_line is locatable", _s0 != -1 and _s1 > _s0,
      "re-anchor this gate — the function moved or was renamed")
_seed_ns: Dict[str, Any] = {"Optional": Optional, "Any": Any, "Dict": Dict}
exec(compile(_seed_src[_s0:_s1], "lane_runner_seed_line", "exec"), _seed_ns)
_seed_line = _seed_ns["_seed_line"]

_ranged = _seed_line({"verb": "rewrite", "label": "selection",
                      "excerpt": "A paragraph with bold,",
                      "range": {"start": 22, "end": 44}})
check("D3 a ranged gesture names its anchor",
      "anchor={'start': 22, 'end': 44}" in _ranged,
      f"rendered: {_ranged!r}")
_block = _seed_line({"verb": "rewrite", "label": "heading", "block_id": "b7",
                     "excerpt": "The one-line thesis"})
check("D3 a block gesture names its anchor",
      "anchor={'block_id': 'b7'}" in _block,
      f"rendered: {_block!r}")
# The anchor is an ADDITION to the target sentence, never a replacement for it:
# a colleague told only the address loses the noun it is acting on.
check("D3 the anchor rides BESIDE the named target",
      "this turn's target" in _ranged and "this turn's target" in _block,
      "the address is handed over in addition to the gesture, not instead of it")

authoring = read(API / "services" / "authoring.py")
_DECK = '<html data-template="deck"><body><h1>T</h1></body></html>'
try:
    sys.path.insert(0, str(API))
    from services.authoring import build_studio_posture  # noqa: E402
    _posture = build_studio_posture("operation/q3/deck.html", _DECK)
except Exception as exc:  # noqa: BLE001
    _posture = ""
    check("D3 the studio posture RENDERS", False, f"{type(exc).__name__}: {exc}")
check("D3 the studio posture teaches the anchor",
      "anchor={'block_id': '<id>'}" in _posture,
      "asserted on the rendered posture — the template escapes its braces")
text_app = read(API / "services" / "apps" / "text.py")
check("D3 the text posture teaches the anchor",
      "anchor" in text_app and "clipped PREFIX" in text_app)

# ── D4: one clip marker, never two ─────────────────────────────────────────
projection = read(WEB / "components" / "workspace" / "viewers" / "projection.ts")
check("D4 the capture marks its own clip",
      "rawText.length > 120" in projection,
      "a silent first clip made the second marker describe the wrong cut")
check("D4 build_focus_line does not double-mark",
      'if clipped.endswith("…")' in authoring)
check("D4 the seed line does not double-mark",
      'if clipped.endswith("…")' in runner)

# ── The tool contract stays honest ─────────────────────────────────────────
check("EditFile no longer requires old_string (the anchored case)",
      '"required": ["path", "new_string"]' in _ws_src,
      "the wholesale-span case passes no old_string")
check("EditFile declares the anchor to the model",
      '"anchor": {' in _ws_src, "an undocumented param is an unused one")

if failures:
    print(f"\nADR-609 FAILED ({len(failures)}):")
    for f in failures:
        print(f"  FAIL {f}")
    sys.exit(1)
print("ADR-609 anchored edit: all checks pass")
sys.exit(0)
