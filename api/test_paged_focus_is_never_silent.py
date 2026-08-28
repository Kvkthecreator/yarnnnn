"""A paged surface always names the page the member is standing on.

The 2026-08-28 incident, in one sentence: the Editor was asked to split "this
slide", was told NOTHING about which slide the member was on, counted
`<section class="slide">` out of the raw markup by hand, and named slide 6 for
the slide the member was standing on. The edit landed correctly — it addressed
the slide by `data-block-id`, the address it actually had — so the defect was
visible only in the prose.

Three layers had to line up for that silence, and this gate holds each:

  1. RUNTIME — the sandboxed deck reported its scroll position only on the
     `scroll` event and on stageShow. A deck the member never scrolled reported
     nothing, so the parent's `viewportPage` stayed null. Fixed by reporting on
     ARRIVAL (and after a restore, which moves the document with no gesture).

  2. DECLARATION — with no selection and no viewport, StudioSurface fell
     through to `document` scope: "nothing finer than the artifact", while a
     slide filled the screen. On a KNOWN-paged artifact that is false, not
     merely quiet. The page grain is now the floor.

  3. RENDERER — `build_focus_line` renders `document` scope as the empty
     string. That is CORRECT and stays (Text and Strings both declare it
     honestly; they hardcode `viewport: null` because they have no page unit).
     It is what makes layer 2 load-bearing: a false declaration here is not a
     wrong sentence the member could catch, it is SILENCE.

Why the existing ADR-522 gate could not catch this: every focus dict it builds
already has `page_index` set. It never exercises the state the incident was —
a paged surface that declared nothing — so it certified the renderer's silence
as correct without ever asking whether a deck could reach it.

Run: python3 test_paged_focus_is_never_silent.py   (from api/)
"""

import re
import sys
from pathlib import Path

from services.authoring import build_focus_line

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


WEB = Path(__file__).resolve().parent.parent / "web"
PROJECTION = WEB / "components/workspace/viewers/projection.ts"
STUDIO = WEB / "components/authoring/StudioSurface.tsx"
TEXT = WEB / "components/text/TextEditor.tsx"

projection_src = PROJECTION.read_text()
studio_src = STUDIO.read_text()


def _strip_comments(src: str) -> str:
    """Assertions must read CODE, not the prose explaining it — this file's own
    rationale names every symbol it guards, and a comment-blind grep would pass
    on the explanation of a defect as readily as on its fix."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)


projection_code = _strip_comments(projection_src)
studio_code = _strip_comments(studio_src)


# ── 1. RUNTIME: the position is reported on arrival, not only on change ──────
#
# Pinned as "a deferred call that is not inside the scroll listener", never as
# a literal line — the fix is `setTimeout(reportScroll, 0)` today, but a
# requestAnimationFrame or a load handler is the same guarantee and must pass.
_scroll_listener = re.search(
    r"addEventListener\(\s*['\"]scroll['\"].*?\}\s*,\s*true\s*\)",
    projection_code,
    flags=re.DOTALL,
)
check("the scroll listener is still present", _scroll_listener is not None)

_outside_listener = projection_code
if _scroll_listener:
    _outside_listener = (
        projection_code[: _scroll_listener.start()]
        + projection_code[_scroll_listener.end() :]
    )

check(
    "RUNTIME reports its position on ARRIVAL, outside the scroll listener",
    re.search(
        r"(setTimeout\(\s*reportScroll|requestAnimationFrame\(\s*reportScroll"
        r"|['\"](?:load|DOMContentLoaded)['\"]\s*,\s*reportScroll)",
        _outside_listener,
    )
    is not None,
    "a deck the member never scrolls must still declare the slide on screen",
)

# The restore path moves the document with no member gesture, and its
# non-stage branches lean on a scroll event that does not fire when the
# restored position equals the current one.
_restore = re.search(
    r"yarnnn-restore-scroll(.*?)\n\s{4}\}\s*\n", projection_code, flags=re.DOTALL
)
check("the restore-scroll handler is still present", _restore is not None)
check(
    "RUNTIME reports where a RESTORE landed",
    _restore is not None and "reportScroll()" in _restore.group(1),
    "a structural reload must not leave the parent's viewport reading stale",
)

# reportScroll is a `var` function expression declared BELOW both call sites:
# hoisting covers the declaration, not the assignment, so every caller must be
# deferred (inside a handler or a timer) rather than running at init.
_decl = projection_code.find("var reportScroll")
check("reportScroll is still declared", _decl != -1)
if _decl != -1:
    # Brace depth, not a text window: a call is deferred iff it sits inside a
    # nested function body (a handler or a timer callback). Measuring the
    # ENCLOSING scope is the structural question; a fixed lookback answers a
    # proximity question that merely correlates with it, and my first cut
    # false-flagged the restore call because its `function` sat 2KB up.
    for m in re.finditer(r"reportScroll\(\)", projection_code):
        if m.start() > _decl:
            continue
        prefix = projection_code[:m.start()]
        depth = prefix.count("{") - prefix.count("}")
        check(
            f"a reportScroll() call above its declaration (char {m.start()}) is deferred",
            depth > 1,
            "calling it at init would throw on an unassigned var",
        )


# ── 2. DECLARATION: a known-paged surface never falls to `document` ──────────
_focus_memo = re.search(
    r"const focus = useMemo<SurfaceFocus \| null>\((.*?)\n  \}, \[",
    studio_code,
    flags=re.DOTALL,
)
check("the Studio focus declaration is still a useMemo", _focus_memo is not None)

if _focus_memo:
    body = _focus_memo.group(1)
    check(
        "DECLARATION floors a paged artifact at the page grain",
        re.search(r"resolvedMode\s*===\s*['\"]paged['\"]\s*\?\s*0\s*:", body)
        is not None,
        "with no selection and no viewport a deck must still name a slide",
    )
    # `layoutMode` defaults to 'flow' until the vocabulary answers; asserting a
    # page grain off it would claim one for an artifact not yet known to have
    # one. This is the ADR-480 reasoning applied to the same seam.
    _floor = re.search(r"(\w+)\s*===\s*['\"]paged['\"]\s*\?\s*0\s*:", body)
    check(
        "the floor reads resolvedMode, never the flow-defaulted layoutMode",
        _floor is not None and _floor.group(1) == "resolvedMode",
        f"reads {_floor.group(1) if _floor else '(absent)'}",
    )
    # A value newly read inside the memo that is missing from the dep array is
    # a stale-closure defect the compiler will not report.
    _deps = studio_code[_focus_memo.end() : studio_code.find("]", _focus_memo.end())]
    check(
        "resolvedMode is in the focus memo's dependency array",
        "resolvedMode" in _deps,
    )


# ── 3. RENDERER: document scope stays silent, and page scope never is ────────
#
# Driven, not grepped — the renderer is Python and this gate can call it.
check(
    "RENDERER: document scope renders nothing (the honest no-page-unit case)",
    build_focus_line({"scope": "document", "label": "deck"}, "deck") == "",
)
check(
    "RENDERER: the floor index renders as slide 1, never slide 0",
    build_focus_line(
        {"scope": "page", "page_index": 0, "viewport_page_index": 0, "label": "slide"},
        "deck",
    )
    == "- The member is viewing slide 1.",
)
# The incident's own shape, end to end: the member is on the 7th slide and the
# colleague must be told SEVEN. A gate that asserted only "non-empty" here
# would pass on an off-by-one, which is the exact defect.
check(
    "RENDERER: the incident's turn now names slide 7",
    build_focus_line(
        {"scope": "page", "page_index": 6, "viewport_page_index": 6, "label": "slide"},
        "deck",
    )
    == "- The member is viewing slide 7.",
)


# ── 4. The rule is Studio's alone — a page-unit-less surface stays silent ────
#
# Text and Strings declare `document` scope truthfully. If this gate ever grew
# to demand a page grain everywhere, it would force those two to invent a page
# they do not have.
check(
    "a surface with no page unit still declares viewport: null",
    re.search(r"viewport:\s*null", _strip_comments(TEXT.read_text())) is not None,
    "Text has no page unit; its document scope is correct silence",
)


if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("PASS — a paged surface always names the page the member is standing on")
