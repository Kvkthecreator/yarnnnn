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

    # Re-anchored 2026-09-01: this gate imported `services.apps.docs`, deleted
    # by ADR-599 D5, so it ERRORED at import (red, unrun) from that commit
    # until ADR-627 resurrected the outward medium as blogger's `post`. The
    # seam it defends (flow vs paged; paged-without-geometry) is unchanged.
    import services.apps  # noqa: F401 — registers every app's rows (ADR-562)
    from services.apps.blogger import BLOGGER_LAYOUTS, POST_SLUG
    from services.authoring import (
        RETIRED_LAYOUT_SLUGS,
        STUDIO_ARRANGEMENTS,
        STUDIO_LAYOUTS,
        STUDIO_LAYOUT_MODES,
        STUDIO_MEASURES,
        all_layouts,
        canonical_layout_slug,
    )

    surface = (web / "components/authoring/StudioSurface.tsx").read_text()
    toolbar = (web / "components/authoring/StudioToolbar.tsx").read_text()
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    ops = (web / "components/authoring/artifactOps.ts").read_text()
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
    # ADR-505 D1/D2 → ADR-599 D5 → ADR-627: `document` (flow) left with Docs
    # (capture prose is the Text app's medium, not a Studio layout — its
    # legacy artifacts render via the FE's flow default); the outward type
    # returned as blogger's `post` (paged). `canvas` belongs to IMAGES.
    _check(
        "the seam matches the registry's own shape: container-native = paged",
        STUDIO_LAYOUTS["deck"]["mode"] == "paged"
        and BLOGGER_LAYOUTS[POST_SLUG]["mode"] == "paged",
    )
    _check(
        # ADR-599 D5: Studio's own table carries the deck alone; the outward
        # medium is registered by the blogger module (the app boundary is the
        # MODULE, ADR-473 D2). `document` stays UNREGISTERED — creation
        # stopped with Docs, reading did not.
        "the media are housed one-and-one; document stays unregistered",
        set(STUDIO_LAYOUTS) == {"deck"}
        and set(all_layouts()) >= {"deck", POST_SLUG}
        and "document" not in all_layouts(),
    )
    _check(
        "the retired slugs resolve to `post` but are never OFFERED (ADR-627 D1)",
        canonical_layout_slug("article") == "post"
        and canonical_layout_slug("page") == "post"
        and canonical_layout_slug("web") == "post"
        and "article" not in all_layouts()
        and "page" not in all_layouts()
        and "web" not in all_layouts(),
    )
    _check(
        "`canvas` is NOT a Studio layout — it left for IMAGES (ADR-472 D1)",
        "canvas" not in STUDIO_LAYOUTS and "canvas" not in RETIRED_LAYOUT_SLUGS,
    )
    _check(
        "mode is NOT the geometry seam: post is paged yet reaches no x/y/z",
        # Position gates on a FRAME grain, not on mode — which is exactly why
        # `post` can share `paged` with `deck` and still have no coordinate
        # space (ADR-505 D3 / ADR-461 D4: a page has a viewport).
        #
        # ADR-544 D3 narrowed that grain from `staged` (either frame) to
        # `artboard` (IMAGES only), so the claim this gate defends is now TRUE
        # OF DECKS TOO — a deck block holds a place in its Area, not a
        # coordinate. What must not regress is a band medium reaching position.
        all(
            "artboard" in STUDIO_MEASURES[m]["grains"]
            for m in ("x", "y", "z")
        )
        and "section[data-arrange]" in BLOGGER_LAYOUTS[POST_SLUG]["skin"]
        and ".slide" not in BLOGGER_LAYOUTS[POST_SLUG]["skin"],
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
        "{isPaged && (" in surface and "<PagedNavigator" in surface,
    )
    # (Re-anchored 2026-09-01 with the import fix: the strip's state moved to
    # the shared pane-slot machinery — `usePaneSlot` in lib/shell/pane-layout —
    # while this gate was unrunnable. The invariants survive; the spellings
    # moved with their owner.)
    _check(
        "the navigator toggle is PAGED-only (it would toggle nothing in flow)",
        "onClick={toggleNav}" in surface
        and re.search(r"\{isPaged && threeColumn && \(", surface) is not None,
    )
    _check(
        "the nav default derives from mode, not from template === 'deck'",
        "defaultShown: !!file?.content && isPaged" in surface
        and "template !== 'deck'" not in surface,
    )
    # ── 2a2. the strip is RESIZABLE (drag its divider), width persisted ──────
    pane_layout = (web / "lib/shell/pane-layout.ts").read_text()
    _check(
        "the strip width is slot-driven + clamped + persisted (one shared module)",
        "{ width: rail.width }" in surface
        and "localStorage" in pane_layout
        and "clamp" in pane_layout,
    )
    _check(
        "a resize divider drives it (cursor-col-resize on the slot's own handle)",
        "cursor-col-resize" in surface
        and "onPointerDown={rail.startResize}" in surface,
    )

    # ── 2b. the slide thumbnail is RESPONSIVE (fixed 2026-07-20) ─────────────
    # The old preview pinned THUMB_W=200 while the rail (w-56 minus its padding +
    # the number column) is only ~176px — so the 200px iframe was CLIPPED on the
    # right by its overflow-hidden parent and read as a squished portrait strip.
    # The thumbnail now MEASURES its container and scales the natural 992px slide
    # to fit, so the 16:9 preview is undistorted and never clipped.
    navigator = (web / "components/authoring/PagedNavigator.tsx").read_text()
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
        # Re-anchored 2026-09-01: ADR-586 folded the page-unit entrance into
        # the one Add door; the seam survives as the door naming the page
        # noun ONLY when the medium is paged.
        "the Add door names the page unit only when PAGED (flow has none)",
        "isPaged\n            ? `Add — a ${pageNoun}" in toolbar,
    )
    # ADR-506 D2 — the toolbar takes the TRI-STATE mode, not a boolean. The
    # boolean was derived with `?? 'flow'`, so it could not tell "this is a
    # document" from "the vocabulary has not landed yet", and a deck's toolbar
    # rendered empty for the first frames and then grew two buttons. This is
    # ADR-482 D3 (chrome waits for the mode) reaching the toolbar. The
    # affirmative test — `mode === 'paged'` — is what makes an unresolved mode
    # withhold rather than guess.
    _check(
        "the toolbar takes the TRI-STATE mode as kernel-derived data",
        "mode: 'flow' | 'paged' | undefined;" in toolbar,
    )
    _check(
        "and derives isPaged by the AFFIRMATIVE test (unresolved withholds)",
        "const isPaged = mode === 'paged';" in toolbar,
    )
    _check(
        "the surface hands it the RESOLVED mode, never the ?? 'flow' default",
        "mode={resolvedMode}" in surface,
    )

    # ── 3. the located insert ───────────────────────────────────────────────
    # ADR-466 D4 completed the arc: insert is located with NO exceptions. The
    # general "+ Insert" AND "Media ▾" are both gone — the located palette
    # lists every kind, and the picker-backed ones (figure/table/gallery) open
    # StudioCitablePicker at the insertion point (chart seeds the lane). What
    # must hold is the SEAM: no un-located insert entrance in the toolbar, and
    # no kind stranded without a home.
    _check(
        "the toolbar carries NO insert entrance (Insert and Media both gone)",
        "> Insert <" not in toolbar and re.search(r"Media <\w+\b", toolbar) is None
        and "openPicker" not in toolbar,
    )
    _check(
        "the located palette lists every kind (no excluded set)",
        "SLASH_EXCLUDED"
        not in (web / "components/authoring/StudioSlashPalette.tsx").read_text(),
    )
    # ADR-539 D2 re-cut: the picker set is DERIVED from the served `cites`
    # field (the literal Set — which this gate pinned at its pre-ADR-538
    # spelling and went stale — is deleted; that staleness is the argument).
    _check(
        "nothing stranded: picker-backed kinds route to the cited-file picker",
        "cites === 'source'"
        in (web / "components/authoring/StudioCitablePicker.tsx").read_text()
        and "kindCites(p.kind)"
        in (web / "components/authoring/StudioSurface.tsx").read_text(),
    )

    # ── 4. the row band is GONE (ADR-505 D4) ────────────────────────────────
    # This section used to assert the gutter's row geometry (rowAt + a 64px left
    # lane). The gutter is deleted on every mode, so the checks INVERT: the block
    # grain's one route is `/` at the caret and the page grain's is New ‹noun›.
    # The full negative surface lives in test_studio_no_gutter_and_arrows.py.
    _check(
        "no row-band geometry survives (rowAt / BAND_*_REACH)",
        "function rowAt(" not in proj
        and "BAND_LEFT_REACH" not in proj
        and "BAND_RIGHT_REACH" not in proj,
    )
    # `/` is the block grain's one route on BOTH modes. The invariant that makes
    # it ungated: the slash runtime rides EDIT_SCRIPT, which is injected on
    # `opts.edit` alone — no `paged`/`flow` branch. A mode gate here would be the
    # ADR-482 D3 race (chrome conditioned on an async mode value) rebuilt.
    _check(
        "`/` is mode-UNGATED: its runtime (EDIT_SCRIPT) injects on opts.edit alone",
        "yarnnn-slash-open" in proj
        and "editScript.textContent = EDIT_SCRIPT;" in proj
        and "if (paged) {\n      const addHere" in proj,  # the paged gate exists, but for add-here
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
