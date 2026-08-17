#!/usr/bin/env python3
"""Gate: ADR-485 — the frame a percent is a percent of.

The operator asked why a resized block would not go back out to full width.
The answer was that a percent was COMMITTED as a fraction of the frame's border
box and APPLIED by CSS against its content box, so every drag lost the padding
fraction and each correction lost it again:

    width  100 -> 87 -> 76 -> 66 -> 57 -> 50   (Chrome, 992x558 slide)
    height 100 -> 80

Corroborated by the live corpus: six authored widths existed across all 16
production artifacts and NONE exceeded 78%, with the padded artifacts sitting on
the predicted decay curve and the zero-padding IMAGES stages sitting higher.

Why 25 green gates missed it, which is the durable lesson:

    Every Studio gate is a STATIC-SOURCE assertion. test_adr461_geometry.py has
    47 checks and asserts, correctly, that the committed value is "a PERCENT OF
    THE FRAME, not a pixel" -- while never asking WHICH RECTANGLE the frame is.
    A round-trip invariant (read-back equals write) is invisible to a grep by
    construction. Nothing in the system had ever written down which rectangle a
    percent was a percent of, so measurableFrame guessed it, CSS resolved it,
    and returnToFlow never re-asked -- three answers to an unasked question.

So the load-bearing half of this gate EXECUTES: `web/scripts/gates/
adr485_measure_frame.mjs` runs the real commit bodies extracted from
projection.ts over a frame whose padding is known, asserts the round trip, and
ships FALSIFIERS that restore the pre-fix arithmetic and prove the check goes
red. This file is the static regression guard on the source's shape.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

_pass = 0
_fail = 0


def _declared_grains(py: str) -> set:
    """The grain slugs MEASURE_GRAINS actually declares, read as a SET.

    Read rather than pinned so a RENAME or a NARROWING (ADR-544 D3 moved
    position from `staged` to `artboard`) is not mistaken for a violation of
    the aperture it tightens. Only a WIDENING past the frame-bounded set is one.
    """
    m = re.search(r"MEASURE_GRAINS = \{([^}]*)\}", py)
    return set(re.findall(r'"([a-z-]+)"', m.group(1))) if m else set()


def _check(label: str, cond: bool) -> None:
    global _pass, _fail
    print(("[PASS] " if cond else "[FAIL] ") + label)
    if cond:
        _pass += 1
    else:
        _fail += 1


proj = (WEB / "components/workspace/viewers/projection.ts").read_text()
ops = (WEB / "components/authoring/artifactOps.ts").read_text()
tab = (WEB / "components/authoring/StudioDesignTab.tsx").read_text()
canvas = (WEB / "components/authoring/StudioCanvas.tsx").read_text()
surface = (WEB / "components/authoring/StudioSurface.tsx").read_text()
studio_py = (ROOT / "api/services/authoring.py").read_text()

print("\n-- 1. D1: the rectangle is named once, and every caller reads it --")
_check("frameRects exists (the one place the box model is answered)",
       "function frameRects(" in proj)
_check("it returns the CONTENT box (what width:%/height:% resolve against)",
       "contentW:" in proj and "contentH:" in proj)
_check("it returns the PADDING box + origin (what left:%/top:% resolve against)",
       "padW:" in proj and "padLeft:" in proj)

for fn in ("resizeMove", "resizeEnd", "moveMove", "moveEnd"):
    i = proj.index(f"function {fn}(")
    body = proj[i:proj.index("\n  }", i)]
    _check(f"{fn} reads frameRects()", "frameRects(" in body)
    _check(f"{fn} takes NO raw frame.getBoundingClientRect() denominator",
           "frame.getBoundingClientRect()" not in body)

print("\n-- 1b. D6: the ORIGIN travels with the box, and the overlay draws it --")
_check("frameRects names the content ORIGIN, not only the content WIDTH",
       "contentLeft:" in proj and "contentTop:" in proj)
_check("showFrame reads frameRects (its fifth caller, once the only bypass)",
       "frameRects(" in proj[proj.index("function showFrame("):
                             proj.index("function hideFrame(")])
_check("the deck stage is READ from the document, never restated as a literal",
       # The canvas declared its own `992` and pinned .slide to it with
       # !important, overriding the document's own --stage-w. Now it reads the
       # same var chain PagedNavigator uses, with the SHARED fallback constant.
       "DECK_STAGE_FALLBACK_W" in proj
       and re.search(r"^\s*const\s+DECK_STAGE_W\b", proj, re.M) is None
       and "var(--stage-w," in proj)

print("\n-- 2. D3: the clamp reads the SERVED bound; the receipt reports what landed --")
_check("the served bounds reach the runtime as data (__yarnnnMeasureBounds)",
       "__yarnnnMeasureBounds" in proj)
_check("resolveArtifactHtml accepts measureBounds", "measureBounds?:" in proj)
_check("StudioCanvas threads it as a projection input",
       # NEVER pin a SPELLING: this asserted the literal "measureBounds]" — the
       # dep array's LAST entry — so appending `blockLabels` to that array read
       # as the mechanism being removed. The invariant is that the value reaches
       # the projection call AND re-runs the effect, not where it sits in a list.
       "measureBounds" in canvas
       and re.search(r"resolveArtifactHtml\([^)]*measureBounds", canvas, re.S) is not None
       and re.search(r"\},\s*\[[^\]]*measureBounds[^\]]*\]\)", canvas, re.S) is not None)
_check("StudioSurface derives it from the SERVED vocabulary.measures",
       "vocabulary?.measures ?? []" in surface)
i = proj.index("function resizeMove(")
rm = proj[i:proj.index("\n  }", i)]
_check("resizeMove no longer hardcodes a floor of 1",
       not re.search(r"Math\.max\(1,\s*Math\.min", rm))
_check("resizeMove clamps width from MEASURE_MIN.w", "MEASURE_MIN.w" in rm)
_check("resizeMove clamps height from MEASURE_MIN.h", "MEASURE_MIN.h" in rm)
i = proj.index("function resizeEnd(")
re_body = proj[i:proj.index("\n  }", i)]
_check("resizeEnd clamps at the COMMIT too (clampMeasure)", "clampMeasure(" in re_body)
_check("the revision receipt is built from the CLAMPED value",
       "const landed = (" in surface and "landed('w', geo.w)" in surface)

print("\n-- 3. D2: the clear-grain matches the write-grain --")
i = ops.index("function returnToFlow(")
rf = ops[i:ops.index("\n}", i)]
_check("returnToFlow clears all five geometry keys, not two",
       re.search(r"keys\s*=\s*\[[^\]]*'x'[^\]]*'y'[^\]]*'w'[^\]]*'h'[^\]]*'z'", rf) is not None)
_check("and strips every geometry custom property",
       all(v in ops for v in ("'--yx:'", "'--yy:'", "'--yw:'", "'--yh:'", "'--yz:'")))

print("\n-- 4. D4: the positioned test reads BOTH attributes, as the kernel rule does --")
_check("'Return to flow' requires data-x AND data-y",
       # ADR-511 D4 loosened the spelling pin (the Position row rewrote the
       # render); the invariant is unchanged — the positioned test reads BOTH
       # attributes, exactly as the kernel rule does.
       re.search(r"hasAttribute\('data-x'\)\s*&&\s*\w+\.hasAttribute\('data-y'\)", tab)
       is not None)
_check("the kernel rule it mirrors still requires both",
       "[data-block][data-x][data-y]" in studio_py)

print("\n-- 5. D5: the dead export is gone --")
_check("STAGE_DEFAULT_W is no longer declared (zero importers, false promise)",
       re.search(r"^\s*(export\s+)?const\s+STAGE_DEFAULT_W\b", proj, re.M) is None)

print("\n-- 6. The ADR-461 D4 aperture is UNCHANGED (this ADR widens nothing) --")
_check("aperture: measures apply to FRAME-BOUNDED grains only (never a reflowing page)",
       # Asserted as a SET, not a literal — the same correction the executing
       # gate already carries. This pinned `{"block-staged", "media"}`; ADR-544
       # D3 renamed the grains and NARROWED position to `artboard`, so a
       # deliberate narrowing read as a violation of the aperture it tightened.
       # What must hold is the ADR-461 D4 boundary: no grain outside the
       # frame-bounded set, ever.
       _declared_grains(studio_py) <= {"staged", "artboard", "media"}
       and len(_declared_grains(studio_py)) > 0)
_check("w keeps its served bound [10,100]",
       re.search(r'"w":\s*\{[^}]*"min":\s*10[^}]*"max":\s*100', studio_py, re.S) is not None)
_check("h keeps its distinct floor of 1 (the axes honestly differ)",
       re.search(r'"h":\s*\{[^}]*"min":\s*1\b', studio_py, re.S) is not None)
_check("no continuous value reaches a reflowing layout",
       ".slide [data-w]" in studio_py
       and not re.search(r'\[data-template="(document|article|page)"\][^\n]*data-w', studio_py))

print("\n-- 7. The EXECUTING gate (the half a grep cannot do) --")
mjs = WEB / "scripts/gates/adr485_measure_frame.mjs"
_check("the executing gate ships", mjs.exists())
if mjs.exists():
    r = subprocess.run(["node", str(mjs)], capture_output=True, text=True, cwd=str(ROOT))
    ok = r.returncode == 0
    _check("it passes (round trip + falsifiers)", ok)
    if not ok:
        print(r.stdout[-3000:])
        print(r.stderr[-2000:])
    _check("it proves the round trip does not decay",
           "five repeats do not decay" in r.stdout)
    _check("it ships a falsifier that reproduces the ratchet",
           "FALSIFIER: the border-box denominator DOES decay" in r.stdout)

print(f"\n{_pass} passed, {_fail} failed")
sys.exit(1 if _fail else 0)
