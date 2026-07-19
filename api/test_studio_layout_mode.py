#!/usr/bin/env python3
"""Gate: the composition seam — `flow` vs `paged`, and the located insert.

Two honest kinds of artifact were wearing one workbench (operator, 2026-07-15):

  paged (deck, page) — the CONTAINER is the unit. A slide IS a page; a landing
    band IS a section. "New slide/section" is the primary act and the navigator
    strip is real navigation (PowerPoint).

  flow (document, article) — BLOCKS are the unit and they flow. There is no
    section to insert; the outline is a derived table of contents, not
    structure; insert belongs at the pointer (Notion/Docs).

The registry proved it: deck has 11 arrangements and page 6 (native), while
document has 4 and article 3 (bolted on). The code had already half-conceded —
the 2026-07-14 ruling shipped a document's outline COLLAPSED because it "doesn't
earn its width". An affordance defaulted off is one that doesn't belong.

So `mode` becomes kernel data and the chrome DERIVES from it. The kernel names
the category once; the FE never hardcodes a layout slug.

Also gated here: the LOCATED insert. "+ Insert" was the one insert affordance
with no location — it fell back to the last block the caret touched, or the
document end. It survives only as "Media" (the picker-backed kinds a located
entrance cannot serve), and the gutter resolves a ROW BY GEOMETRY rather than
hit-testing e.target — the old rule made the bar appear only inside the block's
text box, while the bar DRAWS in the left margin outside it, so reaching the +
left the region that summoned it.

Static/structural checks (no DB, no LLM — this repo has no FE test runner).
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    web = root / "web"
    sys.path.insert(0, str(root / "api"))

    from services.studio import STUDIO_ARRANGEMENTS, STUDIO_LAYOUTS, STUDIO_LAYOUT_MODES

    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    toolbar = (web / "components/studio/StudioToolbar.tsx").read_text()
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    ops = (web / "components/studio/artifactOps.ts").read_text()
    routes = (root / "api/routes/studio.py").read_text()

    def _fn(src: str, name: str) -> str:
        """The body of `export function <name>(` up to the next top-level close."""
        i = src.find(f"export function {name}(")
        return src[i : src.find("\n}", i)] if i >= 0 else ""

    # ── 1. the kernel names the seam ────────────────────────────────────────
    _check("the mode vocabulary is exactly (flow, paged)", STUDIO_LAYOUT_MODES == ("flow", "paged"))
    _check(
        "EVERY layout declares a mode (a new layout can't forget)",
        all("mode" in l for l in STUDIO_LAYOUTS.values()),
    )
    _check(
        "every declared mode is a known one",
        all(l["mode"] in STUDIO_LAYOUT_MODES for l in STUDIO_LAYOUTS.values()),
    )
    _check(
        "the seam matches the registry's own shape: container-native = paged",
        STUDIO_LAYOUTS["deck"]["mode"] == "paged"
        and STUDIO_LAYOUTS["page"]["mode"] == "paged"
        and STUDIO_LAYOUTS["document"]["mode"] == "flow"
        and STUDIO_LAYOUTS["article"]["mode"] == "flow",
    )
    _check(
        "the vocabulary endpoint serves mode (so the FE never hardcodes a slug)",
        '"mode": l["mode"],' in routes,
    )

    # ── 2. the chrome derives from it ───────────────────────────────────────
    _check(
        "the FE resolves mode from the served vocabulary, not from a slug test",
        "vocabulary?.layouts.find((l) => l.slug === template)?.mode ?? 'flow'" in surface
        and "const isPaged = layoutMode === 'paged';" in surface,
    )
    _check(
        "the FE defaults to flow before the vocabulary lands (show LESS, never flash)",
        "?.mode ?? 'flow'" in surface,
    )
    _check(
        "the navigator column is PAGED-only",
        "{isPaged && (" in surface and "<StudioNavigator" in surface,
    )
    _check(
        "the navigator toggle is PAGED-only (it would toggle nothing in flow)",
        bool(re.search(r"\{isPaged && \(\s*\n\s*<button[^>]*\n\s*type=\"button\"\s*\n\s*onClick=\{toggleNav\}", surface)),
    )
    _check(
        "the nav default derives from mode, not from template === 'deck'",
        "setNavCollapsed(!isPaged);" in surface and "template !== 'deck'" not in surface,
    )

    # ── 2b. the slide thumbnail is RESPONSIVE (fixed 2026-07-20) ─────────────
    # The old preview pinned THUMB_W=200 while the rail (w-56 minus its padding +
    # the number column) is only ~176px — so the 200px iframe was CLIPPED on the
    # right by its overflow-hidden parent and read as a squished portrait strip.
    # The thumbnail now MEASURES its container and scales the natural 992px slide
    # to fit, so the 16:9 preview is undistorted and never clipped.
    navigator = (web / "components/studio/StudioNavigator.tsx").read_text()
    _check(
        "the thumbnail measures its own width (ResizeObserver), no hardcoded THUMB_W",
        "new ResizeObserver(measure)" in navigator and "const THUMB_W = 200" not in navigator,
    )
    # The box shape is a STABLE CSS aspect-ratio — NOT height derived from the
    # measured width (which set height from width, a feedback loop that could
    # settle small — the "previews too small" report) and NOT an undefined→number
    # style swap (a hydration mismatch). The scale only sizes the iframe INSIDE
    # an already-correct box.
    _check(
        "the thumbnail box is a stable CSS aspect-ratio (no width→height loop, no hydration swap)",
        "aspectRatio: `${SLIDE_W} / ${SLIDE_H}`" in navigator
        and "height: w > 0 ? Math.round" not in navigator,
    )
    _check(
        "the preview scales the natural slide box to the measured width",
        "w / SLIDE_W" in navigator and "transform: `scale(${scale})`" in navigator,
    )

    # ── 2c. drag-to-reorder in the strip (PowerPoint) ───────────────────────
    _check(
        "the navigator drags a slide to a new position (onReorderSlide + drop-line)",
        "onReorderSlide" in navigator
        and "setDragIndex" in navigator
        and "bg-indigo-500" in navigator,  # the drop-line prediction
    )
    # The drag lives on WINDOW listeners, NOT setPointerCapture on the grip —
    # capture would route every move to the grip element so the list never hears
    # them and the drag appears dead (the "drag doesn't work" report).
    _check(
        "the drag uses window pointer listeners, never setPointerCapture on the grip",
        "window.addEventListener('pointermove', onMove)" in navigator
        and ".setPointerCapture(" not in navigator,  # the CALL, not the cautionary comment
    )
    _check(
        "the reorder rides the ONE write door (applyOp → movePageTo)",
        "movePageTo(html, from, to)" in surface and "reorderSlideFromNavigator" in surface,
    )
    _check(
        "movePageTo moves the slide NODE intact and no-ops on same/out-of-bounds",
        "export function movePageTo(html: string, from: number, to: number)" in ops
        and "from === to" in _fn(ops, "movePageTo")
        and "insertAdjacentElement('afterend', moving)" in _fn(ops, "movePageTo"),
    )
    _check(
        "New ‹noun› is PAGED-only (flow has no page unit to offer)",
        "{isPaged && arrangements.length > 0 && (" in toolbar,
    )
    _check("the toolbar takes isPaged as kernel-derived data", "isPaged: boolean;" in toolbar)

    # ── 3. the located insert ───────────────────────────────────────────────
    # "+ Insert" is gone as a GENERAL insert. It survives only as Media: the
    # picker-backed kinds open a file picker, so a located entrance can't serve
    # them — deleting the button outright would strand Image/Table/Gallery.
    # The glyph is deliberately NOT pinned here: b5495fc moved ▾ → + ("a chevron
    # promises a menu to pick among; a plus promises a thing appears"). What must
    # hold is the SEAM — no general Insert, and Media still present as the
    # picker-backed entrance.
    _check(
        "the general 'Insert' trigger is gone (every ordinary kind is located)",
        "> Insert <" not in toolbar and re.search(r"Media <\w+\b", toolbar) is not None,
    )
    _check(
        "the Media panel carries ONLY the picker-backed kinds",
        "const MEDIA_KINDS = new Set(['figure', 'table', 'gallery', 'chart']);" in toolbar
        and ".filter((b) => MEDIA_KINDS.has(b.kind))" in toolbar,
    )
    _check(
        "Media covers exactly what the slash palette excludes (nothing stranded)",
        # SLASH_EXCLUDED = figure/table/gallery; chart rides along (it seeds the
        # lane, so it has no located gesture either). If either list changes and
        # the other doesn't, a kind loses its only home — that is what this pins.
        "const SLASH_EXCLUDED = new Set(['figure', 'table', 'gallery']);"
        in (web / "components/studio/StudioSlashPalette.tsx").read_text(),
    )

    # ── 4. the gutter owns the ROW, by geometry ─────────────────────────────
    _check(
        "the gutter resolves a row by GEOMETRY (not e.target hit-testing)",
        "function rowAt(x, y) {" in proj and "var blk = rowAt(e.clientX, e.clientY);" in proj,
    )
    _check(
        "the band reaches LEFT of the block — the lane the bar draws in",
        "var BAND_LEFT_REACH = 64;" in proj,
    )
    _check(
        "a gap BETWEEN blocks still resolves to the nearest row (no flicker)",
        "return bestDist <= 24 ? best : null;" in proj,
    )
    _check(
        "the ROW is the outermost block (a checklist's li is not its own row)",
        "if (b.parentElement && b.parentElement.closest && b.parentElement.closest('[data-block]')) continue;" in proj,
    )
    _check(
        "open space owns no row (below the last block, a page margin)",
        "if (x < r.left - BAND_LEFT_REACH || x > r.right + BAND_RIGHT_REACH) continue;" in proj,
    )

    # ── 5. the standing trap ────────────────────────────────────────────────
    # The injected runtimes are JS-in-template-STRINGS: one literal backtick in a
    # comment terminates the template early (tsc TS1005). It has bitten three
    # times, including while writing THIS change.
    for m in re.finditer(r"const (\w+_SCRIPT) = `(.*?)\n`;", proj, re.S):
        _check(f"no literal backtick inside {m.group(1)}", m.group(2).count("`") == 0)

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
