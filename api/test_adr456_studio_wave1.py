"""ADR-456 Wave-1 regression gate — the builder/Notion registry growth.

Static/structural checks (no DB, no LLM):
  1. The four new block kinds (divider · toggle · button · gallery) with
     honest markup: toggle = native <details>/<summary> (script-free), button
     = a styled <a>, gallery cites (data-ref), divider is a bare <hr>.
  2. The new arrangements: deck agenda/big-number/full-bleed/closing (closing
     full-tone via data-tone; full-bleed's slot is media-role), document
     checklist-section/metrics-band.
  3. The new tokens: pad (page grain, presets not pixels) + pagenum (the new
     document-deck applies value); kernel CSS interprets both.
  4. Kernel CSS v3 + the ORDER discipline: block/arrangement rules live in the
     KERNEL element (they retrofit) and come BEFORE the token rules (a token
     wins at equal specificity); responsive stacking exempts the deck stage.
  5. FE: the palette routes gallery to a multi-select picker committing ONE
     block; the Design tab gates document-deck by layout; the pointer runtime
     lets a selected toggle's <summary> click through (first click selects,
     second click acts).

Run:  cd api && python3 test_adr456_studio_wave1.py
Exit code is authoritative (0 = pass).
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    from services.studio import (
        MEDIA_BLOCK_KINDS,
        STUDIO_ARRANGEMENTS,
        STUDIO_BLOCKS,
        STUDIO_KERNEL_CSS,
        STUDIO_KERNEL_CSS_VERSION,
        STUDIO_TOKENS,
        build_skeleton,
        build_studio_posture,
    )

    # ── 1. The four new block kinds ──────────────────────────────────────
    _check("new kinds present: divider/toggle/button/gallery",
           {"divider", "toggle", "button", "gallery"} <= set(STUDIO_BLOCKS))
    _check("toggle is the platform's toggle (<details>/<summary>, script-free)",
           "<details" in STUDIO_BLOCKS["toggle"]["markup"]
           and "<summary>" in STUDIO_BLOCKS["toggle"]["markup"]
           and "<script" not in STUDIO_BLOCKS["toggle"]["markup"])
    _check("button is a styled <a> (semantic, palette-themed — no raw style)",
           "<a href=" in STUDIO_BLOCKS["button"]["markup"]
           and "style=" not in STUDIO_BLOCKS["button"]["markup"])
    _check("gallery cites, never pastes (data-ref on its figures)",
           'data-ref' in STUDIO_BLOCKS["gallery"]["markup"]
           and STUDIO_BLOCKS["gallery"]["group"] == "media")
    _check("gallery joins the media-grain token kinds (height/fit apply)",
           "gallery" in MEDIA_BLOCK_KINDS)

    # ── 2. The new arrangements ──────────────────────────────────────────
    deck = STUDIO_ARRANGEMENTS["deck"]
    _check("deck rows: agenda/big-number/full-bleed/closing",
           {"agenda", "big-number", "full-bleed", "closing"} <= set(deck))
    _check("closing is a full-tone slide (reuses data-tone, no new mechanism)",
           'data-tone="inverse"' in deck["closing"]["fragment"])
    _check("full-bleed's slot is media-role (the picker gates the add)",
           deck["full-bleed"]["slots"] == [{"name": "media", "role": "media"}])
    # ADR-481 D1 (2026-07-22) RETIRED W1's document arrangements — a FLOWING
    # document has no page-grain unit, and the registry serving rows for one is
    # what produced the empty-slot void. The W1 pin flips from "these rows
    # exist" to "flow serves NO arrangements"; the deck rows above are the
    # surviving half of W1's arrangement work and still assert in full.
    _check("ADR-481 D1: flow layouts serve NO arrangements (W1's document rows retired)",
           "document" not in STUDIO_ARRANGEMENTS and "article" not in STUDIO_ARRANGEMENTS)

    # ── 3. The new tokens ────────────────────────────────────────────────
    _check("pad: page grain, presets (s/l) never pixels",
           STUDIO_TOKENS.get("pad", {}).get("applies") == ["page"]
           and {v["value"] for v in STUDIO_TOKENS["pad"]["values"]} == {"s", "l"})
    _check("pagenum: the document-deck applies value (root, deck only)",
           STUDIO_TOKENS.get("pagenum", {}).get("applies") == ["document-deck"])
    _check("kernel CSS interprets pad + pagenum (counters, script-free)",
           '[data-pad="s"]' in STUDIO_KERNEL_CSS
           and 'html[data-pagenum="on"]' in STUDIO_KERNEL_CSS
           and "counter(slide)" in STUDIO_KERNEL_CSS)

    # ── 4. Kernel CSS v3 + the order/retrofit discipline ────────────────
    _check("kernel CSS version >= 3 (skeletons bake the current version; W3 bumped to 4)",
           STUDIO_KERNEL_CSS_VERSION >= 3
           and f'data-kernel-v="{STUDIO_KERNEL_CSS_VERSION}"' in build_skeleton("deck"))
    _check("block/arrangement CSS lives in the KERNEL element (it retrofits)",
           'div[data-block="gallery"]' in STUDIO_KERNEL_CSS
           and '.slide[data-arrange="full-bleed"]' in STUDIO_KERNEL_CSS
           and '[data-arrange="big-number"]' in STUDIO_KERNEL_CSS)
    _check("order discipline: block rules BEFORE token rules (tokens win)",
           STUDIO_KERNEL_CSS.index('div[data-block="gallery"]')
           < STUDIO_KERNEL_CSS.index('[data-align="center"]'))
    _check("responsive stacking exempts the deck stage (:not(.slide))",
           "[data-arrange]:not(.slide) .cols" in STUDIO_KERNEL_CSS
           and "@media" in STUDIO_KERNEL_CSS)

    # ── posture derives the growth (one grammar, both hands) ────────────
    posture = build_studio_posture("/workspace/operation/x/deck.html", build_skeleton("deck"))
    _check("posture teaches the new kinds + tokens (registry-derived)",
           "- gallery — " in posture and "- toggle — " in posture
           and "data-pad=" in posture and "data-pagenum=" in posture)
    _check("posture lists the new deck arrangements",
           "agenda — " in posture and "closing — " in posture)

    # ── 5. The FE half (source checks) ───────────────────────────────────
    web = Path(__file__).resolve().parent.parent / "web"
    toolbar = (web / "components/studio/StudioToolbar.tsx").read_text()
    # ADR-466 D4 moved the gallery's multi-select from the toolbar's Media
    # panel into StudioCitablePicker (opened by the located palette).
    picker = (web / "components/studio/StudioCitablePicker.tsx").read_text()
    _check("palette routes gallery to the multi-select picker",
           "kind === 'gallery'" in picker and "setPicked" in picker
           and "onPickGallery(picked, pins)" in picker)
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    _check("gallery insert = ONE block from the registry fragment (one revision)",
           "galleryFragment(base, paths.map(relPath)" in surface)
    ops = (web / "components/studio/artifactOps.ts").read_text()
    _check("galleryFragment clones the registry prototype per picked path",
           "export function galleryFragment" in ops
           and "proto.cloneNode(true)" in ops)
    design = (web / "components/studio/StudioDesignTab.tsx").read_text()
    _check("Design tab gates document-deck by layout",
           "t.applies.includes('document-deck')" in design
           and "layout === 'deck'" in design)
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    _check("pointer runtime: selected toggle's summary clicks through",
           "closest('summary')" in proj
           and 'data-block="toggle"' in proj)

    print()
    failed = [label for label, ok in _results if not ok]
    print(f"{len(_results) - len(failed)}/{len(_results)} checks passed")
    if failed:
        print("FAILED:")
        for f in failed:
            print(f"  - {f}")
    return not failed


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
