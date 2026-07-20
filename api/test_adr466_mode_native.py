"""ADR-466 — the mode-native carve: one grammar, N native editors.

Static/structural gate (no DB, no LLM). What it pins:

  1. Arrangement intelligence (D5): role-aware slot mapping; the slotless
     refusal resolves by MOVING content (never a dead-end); the galleries
     forewarn; the toolbar pairs New ‹noun› with Layout.
  2. Insert located with no exceptions (D4): the palette lists every kind;
     picker-backed kinds route to StudioCitablePicker at the parked located
     point; Media ▾ and the implicit caret-anchor are gone.
  3. The deck object layer (D2): x/y position measures, DECK-ONLY (the ADR-461
     boundary extended — falsifier: no continuous position admitted on a flow
     layout); kernel pre-declares the ONE position rule (v10); the move grip
     posts percents and structurally clamps to the frame only; re-arranging
     returns a positioned block to flow; the posture teaches preservation.

Run:  cd api && python3 test_adr466_mode_native.py
Exit code is authoritative (0 = pass).
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    repo = Path(__file__).resolve().parent.parent
    web = repo / "web"

    sys.path.insert(0, str(repo / "api"))
    from services.studio import (  # noqa: E402
        STUDIO_KERNEL_CSS,
        STUDIO_KERNEL_CSS_VERSION,
        STUDIO_MEASURES,
        build_studio_posture,
    )

    ops = (web / "components/studio/artifactOps.ts").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    toolbar = (web / "components/studio/StudioToolbar.tsx").read_text()
    design = (web / "components/studio/StudioDesignTab.tsx").read_text()
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    proj = (web / "components/workspace/viewers/projection.ts").read_text()

    # ── D5: arrangement intelligence ─────────────────────────────────────
    _check(
        "applyArrangement is role-aware (media seeks media, flow never fills it)",
        "slotRoles?: Record<string, string>" in ops
        and "mediaSlot" in ops
        and "roleOf(from) !== 'media'" in ops,
    )
    _check(
        "the slotless refusal RESOLVES by moving content (one compound revision)",
        "export function applyArrangementMovingContent" in ops
        and "applyArrangementMovingContent(html, a.fragment, anchor, receiver.fragment)" in surface,
    )
    _check(
        "the galleries forewarn (one shared carry note, both mounts)",
        "export function arrangementCarryNote" in toolbar
        and "arrangementCarryNote(a, carriedCount, pageNoun)" in toolbar
        and "arrangementCarryNote(a, carriedCount, pageNoun)" in design,
    )
    _check(
        "the toolbar pairs New ‹noun› with Layout (the PowerPoint pair)",
        "New {pageNoun}" in toolbar and "'layout'" in toolbar and "hasPageAnchor" in toolbar,
    )
    _check(
        "countCarriedBlocks serves the pre-filter from ONE carried definition",
        "export function countCarriedBlocks" in ops and "carriedBlocksOf" in ops,
    )

    # ── D4: insert located, no exceptions ────────────────────────────────
    picker = (web / "components/studio/StudioCitablePicker.tsx").read_text()
    palette = (web / "components/studio/StudioSlashPalette.tsx").read_text()
    _check(
        "the palette lists every kind; the picker is its host for cited kinds",
        "SLASH_EXCLUDED" not in palette
        and "PICKER_KINDS" in picker
        and "PICKER_KINDS.has(p.kind)" in surface,
    )
    _check(
        "Media ▾ and the implicit caret-anchor are gone",
        "Media <" not in toolbar
        and "lastCaretBlockId" not in surface
        and "insertAnchor" not in surface,
    )
    _check(
        "the located landing: empty replaces (headings survive), mid-text splits",
        "landAtLocatedPoint" in surface
        and "anchorKind === 'heading'" in surface
        and "splitBlockAndInsert(html, blockId, beforeInner, afterInner, fragment)" in surface,
    )

    # ── D2: the object layer (staged frames) ─────────────────────────────
    # ADR-471 D-a redefined the grain: `block-deck` = a block on a STAGED
    # frame (the `.slide` class — a deck slide OR a canvas artboard). The
    # string is unchanged (FE compat); the falsifier now guards that position
    # stays confined to the ONE staged grain — never media, never flow.
    _check(
        "x/y measures exist and are STAGED-FRAME-only (the ADR-461 boundary, ADR-471 grain)",
        STUDIO_MEASURES.get("x", {}).get("applies") == ["block-deck"]
        and STUDIO_MEASURES.get("y", {}).get("applies") == ["block-deck"]
        and STUDIO_MEASURES["x"]["css_var"] == "--yx"
        and STUDIO_MEASURES["y"]["css_var"] == "--yy",
    )
    _check(
        "no continuous position admitted outside the staged frame",
        all(
            g == "block-deck"
            for key in ("x", "y")
            for g in STUDIO_MEASURES[key]["applies"]
        ),
    )
    _check(
        "the kernel pre-declares the ONE position rule (mechanism, not values)",
        '.slide [data-block][data-x][data-y]' in STUDIO_KERNEL_CSS
        and "var(--yx, auto)" in STUDIO_KERNEL_CSS
        and "var(--yy, auto)" in STUDIO_KERNEL_CSS
        and "section.slide, .slide .col, .slide [data-slot] { position: relative; }"
        in STUDIO_KERNEL_CSS,
    )
    _check("kernel CSS bumped for the retrofit (v10+)", STUDIO_KERNEL_CSS_VERSION >= 10)
    _check(
        "setPosition writes BOTH measures as one revision and clears both",
        "export function setPosition" in ops
        and "el.setAttribute('data-x', '')" in ops
        and "el.removeAttribute('data-y')" in ops,
    )
    _check(
        "re-arranging returns a positioned block to flow (both carry paths)",
        "function returnToFlow" in ops and ops.count("returnToFlow(b)") >= 2,
    )
    # P8: the grips grew into the BOUNDING BOX (body-drag move, corner-handle
    # resize, dblclick passes through to edit, hidden while editing) and every
    # gesture posts ONE yarnnn-geometry message → ONE setGeometry revision.
    _check(
        "the bounding box: body-drag deck-gated, corner handles, dblclick-through",
        "yarnnn-selbox" in proj
        and "positionable(selBlock)" in proj
        and "'yarnnn-geometry'" in proj
        and "dispatchEvent(new MouseEvent('dblclick'" in proj
        and "closest('.slide')" in proj,
    )
    _check(
        "the box never reads as a margin click (selection survives a press)",
        ".yarnnn-selbox')" in proj,
    )
    _check(
        "one gesture = one geometry revision, clamped from the SERVED bound",
        "geometrySpecs" in surface
        and "onGeometry={handleGeometry}" in surface
        and "export function setGeometry" in ops,
    )
    _check(
        "empty deck slots wear their bounds always (the placeholder grammar)",
        "yarnnn-slot-open" in proj,
    )
    _check(
        "the box hides while editing (a live caret owns the block)",
        "if (editing == null && sel && sel.isConnected && isMeasurable(sel)) showBox(sel);" in proj,
    )
    _check(
        "the Properties escape hatch: a positioned block can return to flow",
        "onReturnToFlow" in design and "hasAttribute('data-x')" in design,
    )
    _check(
        "no literal backtick inside the new runtime additions",
        "`" not in proj.split("const GUTTER_SCRIPT = `", 1)[1].split("`;", 1)[0],
    )

    # ── D6: Export in the Properties document scope ──────────────────────
    _check(
        "Export lives beside Share (print + AI reference, one settings home)",
        "exportVerbs" in design
        and "Print / PDF" in design
        and "Copy AI reference" in design,
    )
    _check(
        "print export is a PROJECTION over the one resolver (no render engine)",
        "exportPrint" in surface
        and "resolveArtifactHtml(file.content, artifactPath, {})" in surface
        and "break-after: page" in surface,
    )

    # ── D7: the fluidity floor — a 409 never loses typed text ────────────
    _check(
        "courteous 409: refetch the authoritative head, recompute, retry ONCE",
        "e.status === 409" in surface
        and "compute(fresh.content ?? '')" in surface
        and "setLocalOverride({ anchorHead, content: html2" in surface,
    )

    # ── The posture teaches geometry preservation (CHANGELOG 2026.07.20.1) ─
    posture = build_studio_posture("operation/x/deck.html", "deck")
    flat = " ".join(posture.split())
    _check(
        "posture: the lane preserves member-authored measures",
        "data-x/data-y" in flat and "--yx/--yy" in flat and "preserve" in flat.lower(),
    )

    # ── P9: the chrome made grain- and coordinate-honest ─────────────────
    # The operator's live read of P8: the box anchored on a SLOT, drifted past
    # the slide's edge under the deck's fit-zoom, and vanished after every
    # optimistic write. Three structural fixes, each a falsifiable pin.
    _check(
        "P9 grain gate: only a [data-block] is measurable — never a slot/page",
        "if (!block.hasAttribute || !block.hasAttribute('data-block')) return false;" in proj,
    )
    _check(
        "P9 geometry senders refuse a missing data-block-id (no dead red banner)",
        proj.count("if (!id || !frame) return;") >= 2,
    )
    _check(
        "P9 one zoom accessor: chrome divides visual rects by body.style.zoom",
        "window.__yarnnnZf = function ()" in proj
        and "function zf() { return window.__yarnnnZf ? window.__yarnnnZf() : 1; }" in proj
        and "(r.left + window.scrollX) / z" in proj,
    )
    _check(
        "P9 selection survives re-projection (parent re-commands by id on load)",
        "yarnnn-select-block" in proj
        and "selectedRef" in canvas
        and "yarnnn-select-block" in canvas
        and "selectedBlockId={selection?.blockId ?? null}" in surface,
    )
    _check(
        "P9 frame-aware clamp: the trailing edge is bounded too (x ≤ 100 − w%)",
        "var xMax = Math.max(0, 100 - wPct);" in proj
        and "Math.min(Math.max(1, maxPct), pct)" in proj,
    )

    # ── ADR-471: the canvas mode (a staged frame for composed visuals) ────
    from services.studio import STUDIO_ARRANGEMENTS, STUDIO_LAYOUTS, _SCAFFOLD_TITLES
    _cv = STUDIO_LAYOUTS.get("canvas", {})
    _check(
        "the canvas layout exists and is paged (artboards, ADR-471 D-b)",
        _cv.get("mode") == "paged" and _cv.get("label") == "Canvas",
    )
    _check(
        "the artboard IS a .slide (D-a — the object layer inherited, not rebuilt)",
        'class="slide"' in _cv.get("scaffold", "")
        and 'class="slide"' in STUDIO_ARRANGEMENTS.get("canvas", {}).get("free", {}).get("fragment", ""),
    )
    _check(
        "the scaffold teaches everything-positioned (D-e — positioned blocks by example)",
        'data-x="8"' in _cv.get("scaffold", "") and "--yx:8%" in _cv.get("scaffold", ""),
    )
    _check(
        "aspect is a root token in the canvas skin (D-c — marker data-aspect, value --stage-aspect)",
        'html[data-aspect="16:9"]' in _cv.get("skin", "")
        and "var(--stage-aspect, 1 / 1)" in _cv.get("skin", ""),
    )
    _check(
        "…and deck keeps its identity 16:9 (no aspect token there)",
        "data-aspect" not in STUDIO_LAYOUTS["deck"]["skin"]
        and "16 / 9" in STUDIO_LAYOUTS["deck"]["skin"],
    )
    _check(
        "the canvas scaffold title participates in the derived overwrite set",
        "The visual statement." in _SCAFFOLD_TITLES,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
