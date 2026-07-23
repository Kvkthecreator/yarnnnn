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
    gutter_start = proj.index("const GUTTER_SCRIPT = `")
    gutter = proj[gutter_start : proj.index("`;", gutter_start)]
    pointer_start = proj.index("const POINTER_SCRIPT = `")
    pointer = proj[pointer_start : proj.index("`;", pointer_start)]
    _check(
        "D2 the keyboard verb handler LEFT GUTTER_SCRIPT",
        "yarnnn-key-verb" not in gutter,
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
    _check(
        "D2 flow left-click applies the neutral selection cue",
        "if (cur) cur.classList.add('yarnnn-pointed');" in proj,
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
    _check("D3 the gutter injects only when paged", "if (opts?.edit && paged) {" in proj)
    _check("D3 add-here injects only when paged", "if (paged) {" in proj)

    # ── D4 — the edit outline is paged-only; the blues share one token ────
    _check(
        "D4 EDIT_CSS is applied only on paged",
        "(opts?.edit && paged ? EDIT_CSS : '')" in proj,
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
    _check("D6 File is still the first section within it", design.index("File</p>") < design.index("Share</p>"))

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

    # ── Preserved — paged is untouched ────────────────────────────────────
    _check(
        "PRESERVED the selection box + handles still live in GUTTER_SCRIPT",
        "yarnnn-selbox" in gutter,
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
