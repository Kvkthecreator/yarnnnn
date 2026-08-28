"""ADR-522 — the focus declaration: what the member is looking at.

The gate defends the INVARIANTS, not a count of call sites (a counting gate
cannot defend a per-site rule — the lesson from ADR-511's audit):

  1. No focus declared → the posture is byte-identical to pre-ADR-522.
  2. The originating failure is fixed: a staged deck with nothing selected
     still names the slide on screen.
  3. Page numbers reach the member 1-indexed (state is 0-indexed).
  4. "viewing" (on screen) and "selected" (picked) stay distinguishable.
  5. The heading-as-section reading is FLOW-only (ADR-522 D4) — on a paged
     medium the page is already the unit.
  6. The wire carries focus end-to-end, and it is read off the REQUEST, never
     off the durable lane binding.

Run: python3 test_adr522_focus_declaration.py   (from api/)
"""

import ast
import re
import sys
from pathlib import Path

from services.authoring import build_focus_line, build_studio_posture
from services.lane_runner import _compose_focus_section

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


DECK = (
    '<html data-template="deck"><body>'
    '<section class="slide"><h1 data-block="heading" data-block-id="t1">Q3</h1></section>'
    "</body></html>"
)

# ── 1. Silence costs nothing (re-anchored: ADR-606 D1 moved the rendering to
#       ONE kernel site — the posture builder no longer sees focus at all) ───
base = build_studio_posture("operation/q3/deck.html", DECK)
check("606 D1 the posture never carries a focus line", "The member is" not in base)
check(
    "606 D1 focus renders at the kernel site, exactly one line, additive",
    _compose_focus_section(
        "operation/q3/deck.html", DECK,
        {"scope": "page", "page_index": 3, "viewport_page_index": 3},
    ).strip().count("\n") == 0
    and "slide 4" in _compose_focus_section(
        "operation/q3/deck.html", DECK,
        {"scope": "page", "page_index": 3, "viewport_page_index": 3},
    ),
)
check("D5 empty declaration renders nothing",
      build_focus_line(None, "deck") == ""
      and _compose_focus_section("operation/q3/deck.html", DECK, None) == "")
check(
    # The rationale is TRUE for a surface with no page unit (Text's flow
    # document, a Strings desk — both hardcode viewport: null) and FALSE for a
    # paged one, where a slide is always on screen. This assertion pins the
    # RENDERER's behaviour only; that a paged surface must never REACH this
    # scope is the declaration's obligation, gated in
    # test_paged_focus_is_never_silent.py.
    "D5 document scope renders nothing (the declarer had no finer grain)",
    build_focus_line({"scope": "document", "label": "deck"}, "deck") == "",
)
# ── 1b. ADR-606 D2 — on a bound lane the BINDING is the authority ───────────
check(
    "606 D2 a focus naming a DIFFERENT file than the binding is silence",
    _compose_focus_section(
        "operation/q3/deck.html", DECK,
        {"scope": "page", "page_index": 3, "viewport_page_index": 3,
         "path": "operation/other/notes.md"},
    ) == "",
)
check(
    "606 D2 a focus naming the bound file (either spelling) renders",
    "slide 4" in _compose_focus_section(
        "operation/q3/deck.html", DECK,
        {"scope": "page", "page_index": 3, "viewport_page_index": 3,
         "path": "/workspace/operation/q3/deck.html"},
    ),
)
check(
    "606 D1 the unbound lane keeps the default-target line",
    "they mean THIS one" in _compose_focus_section(
        None, "", {"app": "text", "path": "operation/q3/notes.md",
                   "scope": "document"},
    ),
)
check(
    "606 D4 a text selection gets its own sentence, never a fake block",
    "has this text selected" in build_focus_line(
        {"scope": "block", "label": "selection", "excerpt": "the closing ask"},
        "document",
    ),
)
# Found by driving production (2026-08-25): an unmarked clip reads as the
# whole selection — the Editor asserted the 120-char boundary as where the
# member's selection ended. A clipped excerpt must say it is one.
_long = build_focus_line(
    {"scope": "block", "label": "selection", "excerpt": "x" * 200}, "document")
_short = build_focus_line(
    {"scope": "block", "label": "selection", "excerpt": "short"}, "document")
check("606 D4 a clipped excerpt carries a truncation mark", "…" in _long, _long)
check("606 D4 an unclipped excerpt carries none", "…" not in _short, _short)

# ── 2. The originating failure: staged deck, nothing selected ───────────────
staged = build_focus_line(
    {"scope": "page", "page_index": 3, "viewport_page_index": 3, "label": "slide"},
    "deck",
)
check("D3 staged deck names the slide on screen", "slide 4" in staged, staged)
check("D3 an on-screen page reads as 'viewing'", "is viewing" in staged, staged)

# ── 3. 1-indexed for the member ─────────────────────────────────────────────
check("D5 page 0 renders as 1, never 0", "slide 1" in build_focus_line(
    {"scope": "page", "page_index": 0, "viewport_page_index": 0}, "deck"))
check("D5 no zero-indexed leak", "slide 0" not in build_focus_line(
    {"scope": "page", "page_index": 0, "viewport_page_index": 0}, "deck"))

# ── 4. viewing vs selected stay distinct ────────────────────────────────────
picked = build_focus_line(
    {"scope": "page", "page_index": 3, "viewport_page_index": 7}, "deck")
check("D3 a picked page reads as 'selected'", "has selected" in picked, picked)
check("D3 viewing and selected differ", picked != staged)

# ── 5. Heading-as-section is FLOW-only (D4) ─────────────────────────────────
flow_head = build_focus_line(
    {"scope": "block", "label": "heading", "excerpt": "Pricing"}, "document")
deck_head = build_focus_line(
    {"scope": "block", "label": "heading", "excerpt": "Pricing"}, "deck")
check("D4 flow names the section by its heading",
      "writing under the heading" in flow_head, flow_head)
check("D4 paged does NOT claim a section (the page is the unit)",
      "writing under" not in deck_head, deck_head)
check("D4 paged heading is an ordinary selected block",
      "block selected" in deck_head, deck_head)

# ── 6. The wire, end to end ─────────────────────────────────────────────────
lanes_src = Path("routes/lanes.py").read_text()
check("D2 LaneFocus model exists", "class LaneFocus(BaseModel)" in lanes_src)
check("D2 LaneTurnRequest accepts focus",
      re.search(r"class LaneTurnRequest.*?focus: Optional\[LaneFocus\]",
                lanes_src, re.S) is not None)
check(
    # Two legal spellings — the route may dump the model or pass it through
    # (the runner dumps late); the INTENT is that focus comes off the request.
    "D2 focus is read off the REQUEST, not the durable lane binding",
    ("focus=req.focus.model_dump()" in lanes_src or "focus=req.focus" in lanes_src)
    and 'focus=lane_meta.get("focus")' not in lanes_src,
)

runner_src = Path("services/lane_runner.py").read_text()
tree = ast.parse(runner_src)
for fn in ("build_lane_conventions", "run_lane_turn", "run_lane_turn_stream"):
    node = next(
        (n for n in ast.walk(tree)
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fn),
        None,
    )
    check(f"D2 {fn} exists", node is not None)
    if node:
        args = [a.arg for a in node.args.args + node.args.kwonlyargs]
        check(f"D2 {fn} accepts focus", "focus" in args)
# ADR-606 D1 re-anchor: the posture no longer receives focus — the ONE kernel
# site does. The mechanism is the `_compose_focus_section` call inside
# build_lane_conventions with the threaded `focus` argument (AST, not grep).
_blc = next(
    n for n in ast.walk(tree)
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    and n.name == "build_lane_conventions"
)
_focus_calls = [
    c for c in ast.walk(_blc)
    if isinstance(c, ast.Call)
    and (getattr(c.func, "id", None) or getattr(c.func, "attr", None))
    == "_compose_focus_section"
]
check("606 D1 the kernel composes the focus section (one site)",
      len(_focus_calls) == 1)
check(
    "606 D1 …with the threaded focus, never a re-derivation",
    bool(_focus_calls)
    and any(isinstance(a, ast.Name) and a.id == "focus"
            for a in _focus_calls[0].args),
)
check(
    "606 D1 no posture builder is handed focus any more",
    "build_studio_posture(artifact_path, artifact, focus)" not in runner_src,
)

# ── 7. The grain vocabulary is ADR-519's, not ADR-453's dissolved ladder ────
studio_src = Path("services/authoring.py").read_text()
focus_fn = studio_src[studio_src.index("def build_focus_line"):]
focus_fn = focus_fn[: focus_fn.index("\ndef ", 1)]
check(
    "D1 no revival of the dissolved slot grain",
    '"slot"' not in focus_fn and "'slot'" not in focus_fn,
)
for scope in ("block", "container", "page"):
    check(f"D1 handles the {scope} grain", f'"{scope}"' in focus_fn)

if failures:
    print(f"ADR-522 FAILED ({len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
print("ADR-522 focus declaration: all checks passed")
sys.exit(0)
