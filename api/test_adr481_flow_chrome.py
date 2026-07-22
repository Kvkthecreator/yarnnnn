#!/usr/bin/env python3
"""Gate: ADR-481 — the flow chrome rebuild; a blank document is a blank page.

ADR-480 moved the editing GRAIN (contenteditable to the flow root). It did not
touch the chrome drawn AROUND the blocks, so a document's substrate went
continuous while its surface kept narrating a block structure nobody was
thinking in: a gutter floating in an empty gap, a dead vertical void, hover
boxes chasing the pointer across prose.

This ADR rebuilds the flow chrome from ADR-480's axiom rather than inheriting
it from the Notion benchmark:

  D1  flow layouts serve NO arrangements; document/article scaffolds go FLAT
      (the void was `<section data-arrange>` wrapping an empty `<div data-slot>`
      — a slot is a PAGED concept)
  D2  the caret IS the insertion point → the gutter is DELETED on flow; insert
      is `/` at the caret + right-click (both already built). Plus one CSS-only
      cold-start hint.
  D3  the block-hover outline retires on flow; objects stay selectable
  D4  the navigator is UNCHANGED (verified: extractOutline reads h1/h2 only)
  D5  legacy artifacts flatten at PROJECTION, never by migration — rewriting
      live content to fix chrome would manufacture revisions nobody authored

The LOGIC is validated EXECUTING against a real DOM (jsdom + esbuild), 32/32,
INCLUDING the real production PRD pulled from the live substrate (the artifact
whose void the operator screenshotted): zero body arrangements after
projection, zero block ids lost, zero citations lost. It was FALSIFIED twice
(disabling the flatten → 5 failures; ungating the chrome → 7). This committed
gate is the STATIC regression guard on the source's shape.
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "api"))
    web = root / "web"
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    nav = (web / "components/studio/StudioNavigator.tsx").read_text()
    toolbar = (web / "components/studio/StudioToolbar.tsx").read_text()

    from services.studio import (  # noqa: E402
        STUDIO_ARRANGEMENTS,
        STUDIO_LAYOUTS,
        build_skeleton,
    )

    # ── D1 — flow serves no arrangements; the scaffolds are flat ───────────
    _check(
        "D1 the arrangement registry serves PAGED layouts only",
        set(STUDIO_ARRANGEMENTS) == {"deck", "page"},
    )
    _check(
        "D1 deck/page arrangement rows are untouched (11 + 6)",
        len(STUDIO_ARRANGEMENTS["deck"]) == 11 and len(STUDIO_ARRANGEMENTS["page"]) == 6,
    )
    for slug in ("document", "article"):
        body = build_skeleton(slug)
        body = body[body.index("<body>") :]
        _check(f"D1 the {slug} scaffold BODY has no data-arrange", "data-arrange" not in body)
        _check(f"D1 the {slug} scaffold BODY has no data-slot", "data-slot" not in body)
        _check(f"D1 the {slug} scaffold still carries blocks", "data-block-id" in body)
    for slug in ("deck", "page"):
        body = build_skeleton(slug)
        body = body[body.index("<body>") :]
        _check(f"D1 the {slug} scaffold KEEPS its arrangement", "data-arrange" in body)
    _check(
        "D1 the mode seam still names both kinds",
        {v["mode"] for v in STUDIO_LAYOUTS.values()} >= {"flow", "paged"},
    )
    # The toolbar derives from the served set — no flag, no slug test.
    _check(
        "D1 the toolbar's arrangement affordances derive from the served set",
        "isPaged && arrangements.length > 0" in toolbar,
    )

    # ── D2 — the gutter is deleted on flow; insert is caret-located ────────
    _check(
        "D2 the gutter runtime is injected only when NOT flow",
        "if (opts?.edit && opts?.mode !== 'flow') {" in proj,
    )
    _check(
        "D2 the add-here runtime is injected only when NOT flow",
        "if (opts?.mode !== 'flow') {" in proj,
    )
    _check(
        "D2 the cold-start hint is CSS-only (a ::before on the empty root)",
        "main:empty::before, article:empty::before" in proj
        and "Type / for blocks" in proj,
    )
    # The two insert entrances that REPLACE the gutter must both still exist.
    _check("D2 slash-insert survives (the caret-located verb)", "yarnnn-slash-open" in proj)
    _check("D2 right-click survives (the structural verb)", "yarnnn-context" in proj)

    # ── D3 — the flow cue set ─────────────────────────────────────────────
    _check("D3 a flow-specific pointer sheet exists", "const FLOW_POINTER_CSS" in proj)
    _check(
        "D3 the sheet is chosen by MODE at projection",
        "opts?.mode === 'flow' ? FLOW_POINTER_CSS : POINTER_CSS" in proj,
    )
    flow_css = proj[proj.index("const FLOW_POINTER_CSS") : proj.index("const POINTER_CSS")]
    _check("D3 flow carries NO [data-block]:hover outline", "[data-block]:hover" not in flow_css)
    _check("D3 flow carries NO [data-slot] chrome", "[data-slot]" not in flow_css)
    _check("D3 flow gives text the I-beam", "[data-block] { cursor: text; }" in flow_css)
    _check(
        "D3 objects stay selectable (figure/table/chart/gallery keep a cue)",
        '[data-block="figure"]:hover' in flow_css and '[data-block="table"]:hover' in flow_css,
    )
    _check("D3 the neutral selection outline survives", ".yarnnn-pointed" in flow_css)
    # PAGED must keep everything this ADR removed from flow.
    paged_css = proj[proj.index("const POINTER_CSS") : proj.index("// ── The deck STAGE")]
    _check("D3 PAGED keeps its block-hover outline", "[data-block]:hover" in paged_css)
    _check("D3 PAGED keeps its slot chrome", "[data-slot]:hover" in paged_css)

    # ── D4 — the navigator is unchanged (verified, not assumed) ───────────
    outline = nav[nav.index("function extractOutline") :][:600]
    _check("D4 the outline reads h1/h2 only", "querySelectorAll('h1, h2')" in outline)
    _check(
        "D4 the outline never reads arrangements or slots",
        "data-arrange" not in outline and "data-slot" not in outline,
    )
    _check("D4 the outline still resolves block ids", "data-block-id" in outline)

    # ── D5 — legacy flattens at PROJECTION, never by migration ────────────
    _check("D5 the flatten is gated on flow", "if (opts?.mode === 'flow') {" in proj)
    _check(
        "D5 it LIFTS children (re-parents), never rewrites",
        "parent.insertBefore(section.firstChild, section)" in proj
        and "slot.parentNode?.insertBefore(slot.firstChild, slot)" in proj,
    )
    # The invariant that makes D5 safe to run on live content.
    _check(
        "D5 the flatten touches only structure — no id/ref rewriting",
        "setAttribute('data-block-id'" not in proj[
            proj.index("ADR-481 D5") : proj.index("if (opts?.pointer) {")
        ],
    )

    print()
    ok = sum(1 for _, c in _results if c)
    print(f"{ok}/{len(_results)} checks passed")
    return ok == len(_results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
