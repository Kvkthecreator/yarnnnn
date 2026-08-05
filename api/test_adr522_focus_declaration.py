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

from services.studio import build_focus_line, build_studio_posture

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{label}{(': ' + detail) if detail else ''}")


DECK = (
    '<html data-template="deck"><body>'
    '<section class="slide"><h1 data-block="heading" data-block-id="t1">Q3</h1></section>'
    "</body></html>"
)

# ── 1. Silence costs nothing ────────────────────────────────────────────────
base = build_studio_posture("operation/q3/deck.html", DECK, None)
check("D5 no-focus posture carries no focus line", "The member is" not in base)
check(
    "D5 focus is purely additive (exactly one line)",
    len(build_studio_posture("operation/q3/deck.html", DECK,
                             {"scope": "page", "page_index": 3,
                              "viewport_page_index": 3}).splitlines())
    - len(base.splitlines()) == 1,
)
check("D5 empty declaration renders nothing", build_focus_line(None, "deck") == "")
check(
    "D5 document scope renders nothing (no finer grain to report)",
    build_focus_line({"scope": "document", "label": "deck"}, "deck") == "",
)

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
    "D2 focus is read off the REQUEST, not the durable lane binding",
    "focus=req.focus.model_dump()" in lanes_src
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
check("D2 the posture receives the focus",
      "build_studio_posture(artifact_path, artifact, focus)" in runner_src)

# ── 7. The grain vocabulary is ADR-519's, not ADR-453's dissolved ladder ────
studio_src = Path("services/studio.py").read_text()
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
