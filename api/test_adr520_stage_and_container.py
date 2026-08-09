#!/usr/bin/env python3
"""Gate: ADR-520 — the stage view, the adjustable container, the pane as the
structure's home.

Four operator-named frictions on a live deck: the continuous scroll read as a
document (D1: a deck shows ONE slide — view state, never bytes); the slide's
main container answered a resize intent with nothing (D2: staged containers
gain w/h through the existing two-clamp machinery); the pane spoke text chips
where the benchmark is glanceable (D3: numeric fields + alignment glyphs);
the within-slide hierarchy hid in the sequence rail (D4: path + Contents move
to the pane's Identity; the navigator demotes to the filmstrip).

Static-source guard; the click-pass owns the rendered behavior.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

_pass = 0
_fail = 0


def _check(label: str, cond: bool) -> None:
    global _pass, _fail
    print(("[PASS] " if cond else "[FAIL] ") + label)
    if cond:
        _pass += 1
    else:
        _fail += 1


proj = (WEB / "components/workspace/viewers/projection.ts").read_text()
canvas = (WEB / "components/authoring/StudioCanvas.tsx").read_text()
surface = (WEB / "components/authoring/StudioSurface.tsx").read_text()
tab = (WEB / "components/authoring/StudioDesignTab.tsx").read_text()
nav = (WEB / "components/authoring/PagedNavigator.tsx").read_text()

# ── D1: the stage view ─────────────────────────────────────────────────────
_check("stage CSS: non-current slides hide (deck sheet, view state only)",
       "body.yarnnn-stage section.slide:not(.yarnnn-current) { display: none !important; }"
       in proj)
_check("the runtime owns the shown slide (stageShow toggles yarnnn-current + reports)",
       re.search(r"function stageShow\(index\) \{[\s\S]*?classList\.toggle\('yarnnn-current'",
                 proj) is not None and "reportScroll();" in proj.split("function stageShow(")[1].split("function ")[0])
_check("yarnnn-view-mode enables the stage (idempotent; parent re-commands per load)",
       "d.type === 'yarnnn-view-mode'" in proj
       and "document.body.classList.add('yarnnn-stage')" in proj)
_check("scroll-to-slide MEANS show on the stage",
       "if (stageMode()) { stageShow(d.index); return; }" in proj)
_check("the position restore restores the SHOWN slide on the stage",
       re.search(r"if \(stageMode\(\)\) \{[\s\S]{0,220}stageShow\(d\.slide\);", proj) is not None)
_check("scroll-pos reports the stage's own index (the anchoring unit made literal)",
       re.search(r"if \(stageMode\(\)\) \{ var sc = stageCurrent\(\); return sc >= 0 \? sc : null; \}",
                 proj) is not None)
_check("cross-slide reaches switch the stage first (select + scroll-to-block)",
       proj.count("stageShowFor(") >= 3)  # def + the two reach sites
_check("stage nav chrome + PgUp/PgDn page the stage",
       "ensureStageNav" in proj and "e.key !== 'PageUp' && e.key !== 'PageDown'" in proj)
_check("canvas re-commands the stage BEFORE the position restore",
       canvas.find("yarnnn-view-mode") >= 0
       and canvas.find("yarnnn-view-mode") < canvas.find("yarnnn-restore-scroll"))
_check("the stage is DECK-only (web stays a scroll — ADR-505's viewport truth)",
       "stage={template === 'deck'}" in surface)
_check("a new page lands ON the stage (add + duplicate follow to the new index)",
       surface.count("setScrollToSlide((s) => ({ index: at, nonce: (s?.nonce ?? 0) + 1 }))") == 2)

# ── D2: the adjustable staged container ────────────────────────────────────
_check("isMeasurable admits a STAGED container (identity, no vocabulary, on .slide)",
       re.search(r"if \(!block\.hasAttribute \|\| !block\.hasAttribute\('data-block'\)\) \{\s*\n\s*"
                 r"return !!\(block\.matches &&\s*\n\s*block\.matches\('div\[data-block-id\]:not\(\[data-block\]\)'\)",
                 proj) is not None)
_check("a staged container's box wears HANDLES, hides only the move band",
       "'yarnnn-selbox yarnnn-selbox-container-sizable'" in proj
       and ".yarnnn-selbox-container-sizable .yarnnn-selmove { display: none; }" in proj
       and ".yarnnn-selbox-container-sizable .yarnnn-selh" not in proj)
_check("off-stage containers keep the ADR-516 static box (no frame, no measure)",
       "'yarnnn-selbox yarnnn-selbox-static yarnnn-selbox-container'" in proj)
_check("a hidden-slide selection hides its box (no 0×0 lie at the origin)",
       "target.getClientRects && target.getClientRects().length > 0" in proj)
_check("the pane serves container w/h from the same served specs (staged only)",
       re.search(r"if \(scope === 'container'\) \{\s*\n\s*return framed", tab) is not None)

# ── D3: numeric fields + alignment glyphs ──────────────────────────────────
_check("MeasureField clamps to the served bounds (the field half of two-clamp)",
       "const v = Math.max(m.min, Math.min(m.max, Math.round(Number(raw))));" in tab)
_check("the surface routes numeric entry through the ONE id-addressed op",
       re.search(r"handleSetMeasureValue = useCallback\(\s*\n\s*\(key: 'w' \| 'h' \| 'x' \| 'y', "
                 r"value: number\) => \{[\s\S]{0,400}setMeasure\(html, id, key, value, s\)",
                 surface) is not None
       and "onSetMeasure={handleSetMeasureValue}" in surface)
_check("the alignment rows wear the conventional glyphs (labels survive as tooltips)",
       "Icon: AlignStartVertical" in tab and "Icon: AlignVerticalSpaceBetween" in tab
       and "Icon: AlignStartHorizontal" in tab
       and "{o.Icon ? <o.Icon className=" in tab)

# ── D4: the pane is the structure's home; the navigator is the filmstrip ───
_check("the navigator's structure tree is DELETED (no second tree, no node prop)",
       "buildStructure" not in nav and "onSelectNode" not in nav
       and "StructureEntry" not in nav)
_check("the pane derives the path with the breadcrumb's OWN climbChain",
       "import { climbChain } from './SelectionBreadcrumb';" in tab
       and "climbChain(selectedEl, pageEl)" in tab)
_check("Contents mounts at page AND container scope (walkContents, click-to-select)",
       "function walkContents(root: Element)" in tab
       and tab.count("<ContentsRows nodes={contents} onSelect={onSelectNode} />") == 2)
_check("the pane selects through the EXISTING reaches (no new op, no new state)",
       "onSelectNode={selectNodeFromNavigator}" in surface
       and "onSelectPage={selectSlideFromNavigator}" in surface)

print()
print(f"{_pass}/{_pass + _fail} checks passed")
if _fail:
    print("FAILED")
    sys.exit(1)
