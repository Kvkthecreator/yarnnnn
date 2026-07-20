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

    # ── D2: the deck object layer ────────────────────────────────────────
    _check(
        "x/y measures exist and are DECK-ONLY (the ADR-461 boundary extended)",
        STUDIO_MEASURES.get("x", {}).get("applies") == ["block-deck"]
        and STUDIO_MEASURES.get("y", {}).get("applies") == ["block-deck"]
        and STUDIO_MEASURES["x"]["css_var"] == "--yx"
        and STUDIO_MEASURES["y"]["css_var"] == "--yy",
    )
    _check(
        "no continuous position admitted outside the deck frame",
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
    _check(
        "the move grip: deck-gated, posts percents, structural clamp only",
        "yarnnn-mv" in proj
        and "positionable(block)" in proj
        and "'yarnnn-position'" in proj
        and "closest('.slide')" in proj,
    )
    _check(
        "the grips never read as a margin click (selection survives a press)",
        ".yarnnn-rz') || t.closest('.yarnnn-mv')" in proj,
    )
    _check(
        "the parent clamps from the SERVED bound (two-clamp rule)",
        "positionSpecs" in surface and "onPosition={handlePosition}" in surface,
    )
    _check(
        "the Properties escape hatch: a positioned block can return to flow",
        "onReturnToFlow" in design and "hasAttribute('data-x')" in design,
    )
    _check(
        "no literal backtick inside the new runtime additions",
        "`" not in proj.split("const GUTTER_SCRIPT = `", 1)[1].split("`;", 1)[0],
    )

    # ── The posture teaches geometry preservation (CHANGELOG 2026.07.20.1) ─
    posture = build_studio_posture("operation/x/deck.html", "deck")
    flat = " ".join(posture.split())
    _check(
        "posture: the lane preserves member-authored measures",
        "data-x/data-y" in flat and "--yx/--yy" in flat and "preserve" in flat.lower(),
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
