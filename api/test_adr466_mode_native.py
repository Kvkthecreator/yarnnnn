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
    # (Re-pinned 2026-07-21: the Properties page-scope gallery was DELETED as
    #  a full duplicate of the toolbar's — one act, one mount (DP29). The
    #  toolbar button relabeled Layout → "Re-arrange"; the carry note now has
    #  exactly one consumer, and the design tab must NOT regrow a gallery.)
    _check(
        "the gallery forewarns (one shared carry note, ONE mount — the toolbar)",
        "export function arrangementCarryNote" in toolbar
        and "arrangementCarryNote(a, carriedCount, pageNoun)" in toolbar
        and "arrangementCarryNote" not in design
        and "ArrangementThumb" not in design,
    )
    _check(
        "the toolbar pairs New ‹noun› with Re-arrange (the PowerPoint pair)",
        "New {pageNoun}" in toolbar
        and "'layout'" in toolbar
        # ADR-479 D1 made the label conditional ("Re-arranging…" while the
        # placement judgment resolves), so assert the LABEL exists rather than
        # a literal `> Re-arrange` render position.
        and "'Re-arrange'" in toolbar
        and "hasPageAnchor" in toolbar,
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
    # ADR-472 D2 renamed the grain: `block-staged` = a block on a STAGED
    # frame (the `.slide` class — a deck slide OR a canvas artboard). The
    # string is unchanged (FE compat); the falsifier now guards that position
    # stays confined to the ONE staged grain — never media, never flow.
    _check(
        "x/y measures exist and are STAGED-FRAME-only (the ADR-461 boundary, ADR-471 grain)",
        STUDIO_MEASURES.get("x", {}).get("applies") == ["block-staged"]
        and STUDIO_MEASURES.get("y", {}).get("applies") == ["block-staged"]
        and STUDIO_MEASURES["x"]["css_var"] == "--yx"
        and STUDIO_MEASURES["y"]["css_var"] == "--yy",
    )
    _check(
        "no continuous position admitted outside the staged frame",
        all(
            g == "block-staged"
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
    # (Re-pinned for P10: the whole-box drag + dblclick-dispatch hack became
    #  the conventional carve — interior pointer-transparent, move on the four
    #  BORDER BAND strips, dblclick reaches the block natively.)
    _check(
        "the bounding box: interior transparent, border-band move (staged-gated)",
        "yarnnn-selbox" in proj
        and "pointer-events: none" in proj
        and "yarnnn-selmove" in proj
        and "positionable(selBlock)" in proj
        and "'yarnnn-geometry'" in proj
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
    # (REVERSED by P11 — the PowerPoint convention: the box PERSISTS through
    #  text editing (handles stay reachable; the border goes dashed as the
    #  text-mode cue). "Hidden while editing" was the P8 rule from the
    #  click-trapping box; the pointer-transparent interior retired its cause.)
    _check(
        "the box persists through editing, dashed as the text-mode cue (P11)",
        "yarnnn-selbox-editing" in proj
        and "border-style: dashed" in proj
        and "if (editing != null) box.className += ' yarnnn-selbox-editing';" in proj
        and "} else hideBox();" in proj,
    )
    _check(
        "the Properties escape hatch: a positioned block can return to flow",
        "onReturnToFlow" in design and "hasAttribute('data-x')" in design,
    )
    _check(
        "no literal backtick inside the new runtime additions",
        "`" not in proj.split("const GUTTER_SCRIPT = `", 1)[1].split("`;", 1)[0],
    )

    # ── D6: the boundary projections (relocated 2026-07-24: Export lives
    #    beside Share as HEADER verbs — StudioShareExport, right of zoom —
    #    and the Properties pane no longer mounts either) ──────────────────
    share_export = (web / "components/studio/StudioShareExport.tsx").read_text()
    _check(
        "Export lives beside Share in the header cluster (print + AI reference)",
        "Print / PDF" in share_export
        and "Copy AI reference" in share_export
        and "<StudioShareExport" in surface
        and "exportVerbs" not in design
        and "Print / PDF" not in design,
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
    # (Re-pinned for P10: the guards now restore the at-rest frame context on
    #  their refusal path instead of bare-returning.)
    _check(
        "P9 geometry senders refuse a missing data-block-id (no dead red banner)",
        # Counts the REFUSAL, not one spelling of it: resizeEnd's path also
        # clears the group capture (an aborted gesture must not leave a stale
        # one), so a literal-match check went red on a change that preserved
        # the invariant exactly. Both senders still bail and restore the
        # at-rest frame context.
        len([
            ln for ln in proj.splitlines()
            if "if (!id || !frame) {" in ln and "syncFrameContext(); return; }" in ln
        ]) >= 2,
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
        # ADR-485 re-pin: the clamp still bounds the trailing edge, but both of
        # its percentages are now percentages of the SAME rectangle (they were
        # not — x was a percent of the border box and width of the content box,
        # so `100 - wPct` compared unlike units), and the floor comes from the
        # SERVED bound rather than a hardcoded 1 (the kernel serves w.min=10,
        # so a 3% width previewed at 3% and landed at 10%).
        "P9 frame-aware clamp: the trailing edge is bounded too (x ≤ 100 − w%)",
        "var xMax = Math.max(0, 100 - wPct);" in proj
        and "Math.min(Math.max(MEASURE_MIN.w, Math.min(MEASURE_MAX.w, maxPct)), pct)" in proj,
    )

    # ── ADR-472: the stage LEFT Studio (the canvas doc type was carved into
    # the IMAGES app). Its layout/scaffold/dimension assertions live in
    # test_adr472_images.py; what stays here is the Studio-side invariant the
    # carve must not disturb — the deck keeps its identity 16:9 and never
    # grows a dimension/aspect knob of its own.
    from services.studio import STUDIO_LAYOUTS, _SCAFFOLD_TITLES
    _check(
        "the canvas doc type is GONE from Studio (ADR-472 D1/D7)",
        "canvas" not in STUDIO_LAYOUTS and "image" not in STUDIO_LAYOUTS,
    )
    _check(
        "deck keeps its identity 16:9 (no aspect/dimension token there)",
        "data-aspect" not in STUDIO_LAYOUTS["deck"]["skin"]
        and "16 / 9" in STUDIO_LAYOUTS["deck"]["skin"],
    )
    _check(
        "the derived scaffold-title set no longer carries the stage's title",
        "The visual statement." not in _SCAFFOLD_TITLES,
    )
    # D-d: z earned its token (StudioBlockMenu's own comment was the
    # pre-written justification — "z-order arrives with a token").
    _z = STUDIO_MEASURES.get("z", {})
    _check(
        "the z measure exists — staged-frame, integer band, --yz",
        _z.get("applies") == ["block-staged"] and _z.get("css_var") == "--yz"
        and _z.get("unit") == "" and _z.get("min") == 0 and isinstance(_z.get("max"), int),
    )
    _check(
        "the kernel pre-declares the ONE stacking rule (mechanism, not values)",
        ".slide [data-block][data-z] { z-index: var(--yz, auto); }" in STUDIO_KERNEL_CSS,
    )
    _check(
        "kernel CSS bumped for the z retrofit (v11+ — existing decks light up too)",
        STUDIO_KERNEL_CSS_VERSION >= 11,
    )

    # ── P10: the conventional carve (the PowerPoint grammar completed) ───
    # Operator read of P9: the move affordance was "practically impossible to
    # select" (click-to-caret consumed every first click on a slide, and the
    # whole-box drag trapped the interior), and "I don't know what I'm
    # resizing against" (the frame reference appeared only mid-gesture).
    _check(
        "P10 staged click grammar: first click SELECTS, click-again enters text",
        "(!staged || cur === blk)" in proj
        and "closest('.slide') : false" in proj,
    )
    _check(
        "P10 move lives on the border band, interior is pointer-transparent",
        "yarnnn-selmove-n" in proj
        and "cursor: move" in proj
        and "yarnnn-selbox-static" in proj
        and "dispatchEvent(new MouseEvent('dblclick'" not in proj,
    )
    _check(
        "P10 eight handles with directional cursors (edges one axis, corners two)",
        "['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w']" in proj
        and "cursor: ns-resize" in proj
        and "cursor: ew-resize" in proj
        and "function sideAxes(side)" in proj,
    )
    _check(
        # ADR-485 D1 re-pin: height divides by the frame's CONTENT box (what
        # `height: var(--yh)` resolves against), not its border box — the same
        # correction as width, and worse before it (a 20% loss per drag against
        # width's 13%, because vertical padding is a larger fraction of 558px).
        "P10 height is wired end-to-end (runtime → canvas → surface → op)",
        "msg.h = Math.round(clampMeasure('h', (br.height / f.contentH) * 100));" in proj
        and "h: typeof d.h === 'number' ? d.h : undefined," in canvas
        and "...(sh ? { h: spec(sh) } : {})" in surface
        and "'h'" in ops.split("export function setGeometry", 1)[1].split("\n}", 1)[0],
    )
    _check(
        # ADR-485 D1 re-pin: y is a percent of the frame's PADDING box (what
        # `top: %` resolves against on an absolutely-positioned child), and it
        # measures FROM the padding edge — a different rectangle than width's,
        # which is the distinction the single `fr` rect could not express.
        "P10 north/west on a positioned block anchor the opposite edge (one revision)",
        "if (ax.north && positioned) {" in proj
        and "msg.y = Math.round(clampMeasure('y', ((br.top - f.padTop) / f.padH) * 100));" in proj,
    )
    _check(
        "P10 the frame reference rides the selection (name at rest, numbers live)",
        "function syncFrameContext()" in proj
        and "txt ? frameLabel(frame) + ' · ' + txt : frameLabel(frame)" in proj,
    )

    # ── P12: the flow-mouse pass (operator read, 2026-07-21) ─────────────
    # The dashed-box noise on documents: every pointable element (h3, p)
    # outlined individually with cursor:pointer, INSIDE the very block being
    # edited, with the slot label firing over it. The cue now lights the
    # click GRAIN, text invites the caret, and chrome rests while typing.
    _check(
        "P12 hover cue lights the enclosing block, innermost only",
        "[data-block]:hover:not(:has([data-block]:hover))" in proj,
    )
    _check(
        "P12 text blocks wear the I-beam; the cursor follows the click's meaning",
        "{ cursor: text; }" in proj and "TEXT_KINDS_JS).map" in proj,
    )
    _check(
        "P12 quiet while typing: no hover chrome inside a live edit; slots rest",
        '[contenteditable="true"] :hover' in proj
        and 'body:has([contenteditable="true"]) [data-slot]:hover { outline: none; }' in proj,
    )

    # ── A slot is chrome only where it is a distinguishable region ────────
    # 13 of 17 arrangements declare one flow slot that fills its own page, so
    # hovering drew a dashed box around the whole slide and clicking selected
    # it — the layout master offered as an object with none of an object's
    # affordances. The premise being corrected is POINTER_CSS's own comment
    # ("the Wix section-hover"): Wix builds pages of BANDS where a section is
    # the unit; a slide's unit is the OBJECT. Both premises lived in one sheet.
    tab = (web / "components/studio/StudioDesignTab.tsx").read_text()
    _check(
        "the projection MARKS the page-filling slot inert (paged only)",
        "data-slot-inert" in proj and "opts?.mode === 'paged'" in proj,
    )
    _check(
        "a 2+-slot page keeps its slots (a real sub-region: two-column, comparison)",
        "if (slots.length >= 2) return;" in proj,
    )
    _check(
        "a MEDIA slot keeps its chrome (full-bleed's picker home would vanish)",
        "=== 'media') return;" in proj,
    )
    _check(
        "an EMPTY slot keeps its bounds (the ADR-466 P8 click-to-add placeholder)",
        "if (!slot.querySelector('[data-block]')) return;" in proj,
    )
    _check(
        "hover chrome is gated on the marker, not deleted outright",
        "[data-slot]:not([data-slot-inert]):hover {" in proj,
    )
    _check(
        "the click ladder SKIPS an inert slot (it falls through to the page)",
        "closest('[data-slot]:not([data-slot-inert])')" in proj,
    )
    _check(
        "the Design tab derives the same predicate from the SERVED registry",
        "slotIsRegion" in tab and "row.slots.length >= 2" in tab,
    )
    _check(
        "an unknown arrangement KEEPS the grain (never hide a real slot)",
        "if (!row) return true;" in tab,
    )

    # ── The GROUP is a transient selection, never markup ──────────────────
    # The substrate decides this, not taste: applyArrangement calls
    # returnToFlow() on every carried block (stripping x/y/w/h/z), so a
    # persisted <div data-group> would be orphaned by the next re-arrange; and
    # carriedBlocksOf skips any block nested inside another block, so a wrapper
    # would hide its own children from every sweep. A group that survived in
    # the file would be a second structural layer competing with the
    # arrangement — the confusion the slot pass just removed.
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    # Tests CODE, not prose: `data-group` appears in setGeometryMany's comment
    # explaining why the wrapper does NOT exist, so a bare substring check
    # matches its own rationale. Assert no element ever CARRIES the attribute.
    _check(
        "no group WRAPPER is ever written (a group is selection, not structure)",
        "setAttribute('data-group" not in ops
        and "setAttribute('data-group" not in proj
        and 'querySelector("[data-group' not in ops,
    )
    _check(
        "the group's cue is a CLASS the runtime paints",
        "yarnnn-grouped" in proj,
    )
    _check(
        "…and the ONE serializer strips it (the ADR-484 leak, generalized)",
        "CHROME_CLASSES = ['yarnnn-pointed', 'yarnnn-grouped']" in proj,
    )
    _check(
        "group membership rides ALONGSIDE cur (the one-selection rule holds)",
        "__yarnnnGroup" in proj and "window.__yarnnnSelected = function () { return cur; }" in proj,
    )
    _check(
        "a modifier-click is intercepted BEFORE the ladder (never places a caret)",
        "if (e.shiftKey || e.metaKey || e.ctrlKey) {" in proj,
    )
    _check(
        "grouping is STAGED-only (a set needs a frame to move in — ADR-461 D4)",
        "gstaged" in proj,
    )
    _check(
        "the riders' offsets are captured ONCE per gesture (no mid-drag drift)",
        "groupRide = [];" in proj and "dx: gr.left - br.left" in proj,
    )
    _check(
        "a group drop posts ONE message, and lands as ONE revision",
        "type: 'yarnnn-geometry-many'" in proj
        and "setGeometryMany" in ops
        and "setGeometryMany(html, moves, specs)" in surface,
    )
    _check(
        "setGeometryMany reuses setGeometry (one clamp, no second write path)",
        "const r = setGeometry(cur, m.blockId, m.geo, specs);" in ops,
    )
    _check(
        "an unresolved member is skipped, never aborting the gesture",
        "if (!r) continue;" in ops,
    )
    # The group's HANDLER, not just its props. The first cut of this feature
    # declared onGeometryMany, destructured it, and listed it in the deps array
    # while the message-handler BRANCH never landed — so the runtime posted
    # yarnnn-geometry-many and nothing listened. A prop that exists and is
    # never called is the shape of a half-applied patch, and only a check on
    # the listener catches it.
    _check(
        "the canvas LISTENS for the group message (a declared prop is not a wired one)",
        "d.type === 'yarnnn-geometry-many'" in canvas and "onGeometryMany?.(moves)" in canvas,
    )
    _check(
        "…and passes SIZE through, so a group resize is not silently a move",
        "w: typeof m.w === 'number'" in canvas,
    )
    # Group resize — the Figma model: proportional within the bounding box.
    _check(
        "group resize scales about the bounding box, captured once per gesture",
        "function captureGroupResize(primary)" in proj and "groupResize = {" in proj,
    )
    _check(
        "the handle's OPPOSITE edge anchors (a west drag pins the right edge)",
        "var ancX = gax.west ? b.left + b.width : b.left;" in proj,
    )
    _check(
        "members scale POSITION and SIZE together (relative layout preserved)",
        "anchorX + (m.r.left - anchorX) * sx" in proj and "m.r.width * sx" in proj,
    )
    _check(
        "commit reads each member's LANDED rect (what was seen is what is written)",
        "gel.getBoundingClientRect()" in proj and "type: 'yarnnn-geometry-many'" in proj,
    )
    _check(
        "the receipt distinguishes a resize from a move (ADR-485 D3)",
        "resized ? 'resized' : 'moved'" in surface,
    )
    _check(
        "no keyboard grouping (⌘G would imply a PERSISTED group)",
        "metaKey && (e.key === 'g'" not in proj and "'KeyG'" not in proj,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
