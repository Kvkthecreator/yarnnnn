#!/usr/bin/env python3
"""Gate: ADR-482 — the flow completion pass; insert parity, chrome scope, the mode race.

ADR-480 moved the editing grain to the document root. ADR-481 rebuilt the chrome
around it. Both were right in isolation, and the hole opened in the SEAM:

  D1  `/` had no working terminal step on flow. `yarnnn-slash-take` guarded on
      `editingEl`, which only enter() assigns — and ADR-480 D1 stopped calling
      enter() on flow. ADR-481 D2 then deleted the gutter '+' that was masking
      it, on the stated ground that "/ is already built". It was built, opened,
      and filtered; it never completed. Insert was unreachable on documents.
  D2  the keyboard verbs (⌘C/⌘V/⌘D/⌫) lived inside GUTTER_SCRIPT, which is not
      injected on flow — so the right-click menu advertised dead keys. Moved to
      the pointer runtime (injected in both grains) with a CARET-shaped guard,
      because __yarnnnEditingId is null on flow while a caret is very much live.
      Flow left-click also gains the neutral .yarnnn-pointed cue it omitted.
  D3  `mode` is undefined until the vocabulary answers, and every `!== 'flow'`
      test read that as PAGED — so a flow document's first frames projected the
      paged gutter/hover/edit chrome, then re-projected. That flash is the
      indigo box in the operator's screenshot. The chrome now WAITS for the
      mode; the editing grain keeps its conservative default (a deck must never
      get contenteditable on its root for even one frame).
  D4  EDIT_CSS's 2px indigo outline is paged-only, and the six #6366f1 literals
      collapse to one custom property.
  D5  StudioBlockMenu was mode-blind — Move up/down are enclosure verbs offered
      against continuous prose. Withdrawn on flow.
  D6  Properties is ordered by SCOPE: File/Share/Export lead, then the selection.
  D7  the breadcrumb carries the document-type glyph; `image` gains a registry
      row; the crumb's root label is app-aware.
  D11 the '/' palette dead-ended on a native flow line and Enter's bare divs
      never became blocks — the two halves of one seam. On a flow root the
      browser inserts a native <div>/<p> on Enter (no data-block) and does not
      guarantee the caret lands in a text node after input. The slash-open
      guard bailed on `nodeType !== 3` (so '/' on those element-node lines was
      dropped, landing as literal text — verified in prod), and normalizeBlockIds
      only ever touched already-annotated elements (so the bare divs saved
      un-addressable). Fix: slash-open resolves the '/'-bearing text node from
      wherever the caret settled; normalizeBlockIds promotes bare block-level
      flow lines to prose first. Both validated EXECUTING with falsifiers
      (adr482_slash_open_elementnode.mjs, adr482_flow_promote.mjs).

D1 is validated EXECUTING, not grepped — `web/scripts/gates/adr482_slash_take.mjs`
runs the real handler body in both grains (7/7) and includes a FALSIFIER that
restores the pre-fix guard and asserts flow breaks again. That distinction is the
lesson of this ADR: ADR-481's own gate was green while the surface was unusable,
because every check short of COMPLETING the gesture passed.

This committed gate is the static regression guard on the source's shape.
"""

import subprocess
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    web = root / "web"
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    menu = (web / "components/studio/StudioBlockMenu.tsx").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    design = (web / "components/studio/StudioDesignTab.tsx").read_text()
    shapes = (web / "components/studio/studioShapes.ts").read_text()
    ops = (web / "components/studio/artifactOps.ts").read_text()

    # ── D1 — the slash-take path completes on flow ────────────────────────
    _check(
        "D1 slash-take guards on editHost(), never the per-block editingEl",
        "!slashNode || !editHost()) return;" in proj
        and "!slashNode || !editingEl) return;" not in proj,
    )
    _check(
        "D1 the target block is resolved from the caret under FLOW_MODE",
        "id = tblk ? (tblk.getAttribute('data-block-id') || null) : null;" in proj,
    )
    _check(
        "D1 exit() is called only when a per-block session is open",
        "if (!FLOW_MODE) exit(false, true);" in proj,
    )

    # The EXECUTING half — the check that would have caught the regression.
    gate = web / "scripts/gates/adr482_slash_take.mjs"
    _check("D1 the executing harness is committed", gate.exists())
    if gate.exists():
        proc = subprocess.run(
            ["node", str(gate)], cwd=str(root), capture_output=True, text=True
        )
        _check(
            "D1 the executing harness PASSES (real handler body, both grains)",
            proc.returncode == 0 and "7 passed, 0 failed" in proc.stdout,
        )

    # ── D2 — the keyboard verbs and the selection cue reach flow ──────────
    object_start = proj.index("const OBJECT_SCRIPT = `")
    objects = proj[object_start : proj.index("`;", object_start)]
    pointer_start = proj.index("const POINTER_SCRIPT = `")
    pointer = proj[pointer_start : proj.index("`;", pointer_start)]
    _check(
        "D2 the keyboard verb handler LEFT the gutter script",
        "yarnnn-key-verb" not in objects,
    )
    _check(
        "D2 the keyboard verb handler is in POINTER_SCRIPT (both grains)",
        "yarnnn-key-verb" in pointer,
    )
    _check(
        "D2 __yarnnnCaretLive exists — the caret question, not the session one",
        "window.__yarnnnCaretLive = function ()" in proj,
    )
    _check(
        "D2 text keys guard on caret-live, not on __yarnnnEditingId",
        "window.__yarnnnCaretLive && window.__yarnnnCaretLive()) return;" in pointer,
    )
    # AMENDED by ADR-484: D2 closed a real asymmetry (right-click outlined,
    # left-click did not) but resolved it the wrong direction on PROSE — on a
    # continuous writing surface the caret is the feedback, and boxing a
    # paragraph re-asserts the enclosure ADR-480 dissolved. The cue is now
    # OBJECT-ONLY on flow, matching the boundary FLOW_POINTER_CSS already drew
    # for the hover cue. The asymmetry D2 fixed stays fixed for objects.
    _check(
        "D2+484 flow left-click applies the selection cue to OBJECTS ONLY",
        "if (cur && TEXT_KINDS.indexOf(cur.getAttribute('data-block')) === -1) {" in proj,
    )

    # ── D3 — the chrome waits for the mode ────────────────────────────────
    _check(
        "D3 the projection derives affirmative mode flags",
        "const paged = opts?.mode === 'paged';" in proj
        and "const flow = opts?.mode === 'flow';" in proj,
    )
    _check(
        "D3 no mode-specific chrome is gated on `!== 'flow'` (undefined-as-paged)",
        "opts?.mode !== 'flow'" not in proj,
    )
    _check(
        "D3 an unresolved mode gets NO pointer sheet",
        "(flow ? FLOW_POINTER_CSS : paged ? POINTER_CSS : '')" in proj,
    )
    # ADR-489 D4: the gutter is deleted; what this gate now pins is that the
    # OBJECT grammar (box/handles/divider) is the paged-only injection.
    _check("D3 the object grammar injects only when paged", "if (opts?.edit && paged) {" in proj)
    _check("D3 add-here injects only when paged", "if (paged) {" in proj)

    # ── D4 — the edit outline is paged-only; the blues share one token ────
    _check(
        "D4 EDIT_CSS is applied only on paged",
        "(opts?.edit && paged ? EDIT_CSS : '')" in proj,
    )
    # (2026-07-25) D4's scoping orphaned the format bar's rules on flow — the
    # runtime builds the bar on both grains, so its sheet must ride the edit
    # runtime unconditionally: unstyled static B/I/<>/Link at the body's end
    # was the operator-photographed symptom.
    _check(
        "the format bar's sheet ships on BOTH grains (FMT_CSS ungated by mode)",
        "(opts?.edit ? FMT_CSS : '')" in proj
        and ".yarnnn-fmt" in proj.split("const FMT_CSS")[1].split("`;")[0]
        and ".yarnnn-fmt" not in proj.split("const EDIT_CSS")[1].split("`;")[0],
    )
    # (2026-07-25 → D11) The empty-line slash: the caret is re-read POST-input,
    # when the '/' has created the text node. D11 generalized this to element-
    # node carets too (see the D11 block below). And the take path's splitHalves
    # takes its HOST — it cloned editingEl (null on flow), crashing every pick.
    _check(
        "slash-open anchors POST-input (empty line included)",
        "var c2 = slashCaret();" in proj
        and "at = c2.startOffset - 1; // caret inside the text node" in proj,
    )
    _check(
        "splitHalves takes its host; flow passes the caret's block",
        "function splitHalves(host)" in proj
        and "splitHalves(editingEl)" in proj
        and "var halves = splitHalves(host)" in proj,
    )
    _check(
        "flow has NO per-block enter — the chokepoint and the dblclick both refuse",
        "if (FLOW_MODE) return;\n    // Idempotent" in proj.replace("\r", ""),
    )
    _check(
        "D4 the chrome accent is declared once as a custom property",
        "--yarnnn-chrome-accent: #6366f1;" in proj,
    )
    # Exactly two literals survive: the declaration and its explaining comment.
    _check(
        "D4 #6366f1 appears only in the token declaration + its comment",
        proj.count("#6366f1") == 2,
    )
    _check(
        "D4 no raw rgba(99,102,241,...) sites remain",
        "rgba(99,102,241," not in proj,
    )

    # ── D8 — the UA focus ring on the flow root is suppressed ─────────────
    flow_css = proj[proj.index("const FLOW_POINTER_CSS") : proj.index("const POINTER_CSS")]
    _check(
        "D8 the flow root's browser focus ring is suppressed",
        'main[contenteditable="true"]:focus' in flow_css
        and 'article[contenteditable="true"]:focus' in flow_css
        and "outline: none;" in flow_css,
    )
    paged_css = proj[proj.index("const POINTER_CSS") : proj.index("const EDIT_CSS")]
    _check(
        "D8 PAGED is untouched — no root focus suppression there",
        'main[contenteditable="true"]' not in paged_css,
    )

    # ── D10 — the slash run survives native node replacement ─────────────
    _check(
        "D10 slashRun re-anchors instead of failing on node identity",
        "if (caret.startContainer !== slashNode) {" in proj
        and "slashNode = cn; // re-anchored" in proj,
    )
    d10 = web / "scripts/gates/adr482_slash_run_reanchor.mjs"
    _check("D10 the executing harness is committed", d10.exists())
    if d10.exists():
        p2 = subprocess.run(["node", str(d10)], cwd=str(root), capture_output=True, text=True)
        _check(
            "D10 the executing harness PASSES (node replaced under the caret)",
            p2.returncode == 0 and "6 passed, 0 failed" in p2.stdout,
        )

    # ── D9 — prose is never boxed on flow; the menu offers no impossible act ──
    _check(
        "D9 right-click does NOT box a TEXT block on flow",
        "if (!flowNow || TEXT_KINDS.indexOf(markKind) === -1) {" in proj,
    )
    _check(
        "D9 left-click keeps the same boundary (objects only)",
        "if (cur && TEXT_KINDS.indexOf(cur.getAttribute('data-block')) === -1) {" in proj,
    )
    _check(
        "D9 Paste here is gated on there being something to paste",
        "{hasClipboard && (" in menu,
    )
    _check(
        "D9 a menu with no acts does not render",
        "if (!hasBlock && !hasClipboard) return null;" in menu,
    )
    _check(
        "D9 the surface passes the clipboard state",
        "hasClipboard={!!blockClip.current}" in surface,
    )

    # ── D5 — the menu is mode-scoped ──────────────────────────────────────
    _check("D5 StudioBlockMenu accepts a mode", "mode?: 'flow' | 'paged';" in menu)
    _check(
        "D5 the enclosure test is affirmative (paged), not negative",
        "const isPaged = mode === 'paged';" in menu,
    )
    _check(
        "D5 Move up/down render only on paged",
        "{hasBlock && isPaged && (" in menu,
    )
    _check(
        "D5 the surface passes the RESOLVED mode",
        "mode={resolvedMode}" in surface,
    )

    # ── D6 — Properties leads with file identity ──────────────────────────
    head = design.index("The artifact head")
    doc_scope = design.index("{/* ── DOCUMENT scope")
    _check("D6 the File/Share/Export block precedes the scope half", head < doc_scope)
    _check(
        "D6 the block is still scope- and mode-INVARIANT",
        "EVERY scope, every template" in design,
    )
    # (Re-pinned 2026-07-24/25: Share + Export relocated to the header cluster
    #  — StudioShareExport, right of zoom — so the pane's head is File alone.)
    _check("D6 File leads the head; Share/Export left for the header cluster",
           "File</p>" in design and "Share</p>" not in design
           and "Export</p>" not in design)

    # ── D7 — the crumb carries the type glyph ─────────────────────────────
    _check("D7 the IMAGES stage has a shape row", "image: { icon: ImageGlyph" in shapes)
    _check(
        "D7 the crumb renders the served type's glyph",
        "studioShapeStyle(template)" in surface,
    )
    _check(
        "D7 the crumb's root label is app-aware",
        "{app.slug === 'images' ? 'Images' : 'Studio'}" in surface,
    )

    # ── D11 — the '/' opens from an element-node caret; Enter's bare divs ──
    #          become real blocks ─────────────────────────────────────────────
    # The two halves of the same seam the operator hit: pressing '/' on a native
    # flow line (an element-node caret) dead-ended at the `nodeType !== 3` bail,
    # so the sentinel landed as literal text — and the native <div> lines that
    # caret sat on were never promoted to blocks, so they accumulated
    # un-addressable. Both validated EXECUTING (the D1 lesson), each with a
    # falsifier that restores the pre-fix body and asserts it breaks again.
    _check(
        "D11 slash-open resolves the '/' text node from an element-node caret",
        "if (node.nodeType === 3) {" in proj
        and "while (prev && prev.nodeType === 1) prev = prev.lastChild;" in proj,
    )
    _check(
        "D11 the pre-fix nodeType-3 bail is gone",
        "if (!c2 || c2.startContainer.nodeType !== 3) return;" not in proj,
    )
    open_gate = web / "scripts/gates/adr482_slash_open_elementnode.mjs"
    _check("D11 the slash-open executing harness is committed", open_gate.exists())
    if open_gate.exists():
        p3 = subprocess.run(
            ["node", str(open_gate)], cwd=str(root), capture_output=True, text=True
        )
        _check(
            "D11 slash-open harness PASSES (element-node caret opens the palette)",
            p3.returncode == 0 and "7 passed, 0 failed" in p3.stdout,
        )
    _check(
        "D11 normalizeBlockIds promotes bare block-level flow lines",
        "el.setAttribute('data-block', 'prose');" in ops
        and "const PROMOTABLE = new Set(['DIV', 'P']);" in ops,
    )
    _check(
        "D11 promotion skips <br>-only lines and citation islands",
        "if (el.hasAttribute('data-block') || el.hasAttribute('data-ref')) return;" in ops
        and "=== '') return; // a <br>-only / empty line" in ops,
    )
    promote_gate = web / "scripts/gates/adr482_flow_promote.mjs"
    _check("D11 the promotion executing harness is committed", promote_gate.exists())
    if promote_gate.exists():
        p4 = subprocess.run(
            ["node", str(promote_gate)], cwd=str(root), capture_output=True, text=True
        )
        _check(
            "D11 promotion harness PASSES (bare Enter divs become prose blocks)",
            p4.returncode == 0 and "8 passed, 0 failed" in p4.stdout,
        )

    # ── Preserved — paged is untouched ────────────────────────────────────
    _check(
        "PRESERVED the selection box + handles still live in GUTTER_SCRIPT",
        "yarnnn-selbox" in objects,
    )
    _check(
        "PRESERVED paste stays plain-text in BOTH grains (the §7 refusal)",
        proj.count("getData('text/plain')") == 2,
    )
    _check(
        "PRESERVED the flow root is still the editing host (ADR-480 D1)",
        "root.setAttribute('contenteditable', 'true');" in proj,
    )

    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    print(f"\n{passed}/{total} checks passed")
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
