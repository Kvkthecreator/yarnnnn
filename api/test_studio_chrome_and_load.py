#!/usr/bin/env python3
"""Gate: the Studio's chrome — one locator, controls that don't buckle, no
phantom file fetch.

Three defects observed together in one screenshot (operator, 2026-07-15):

  1. DUAL BREADCRUMB. `01ae144` shipped useSelfLocatedSurface (the PRODUCER, in
     BreadcrumbContext) but its two CONSUMERS — the GlobalLocatorStrip's
     suppression branch and ChatSurface's declaration — were left uncommitted in
     the working tree. So a surface declared "I render my own locator" and the OS
     strip, which never learned to listen, drew a second one. The producer/
     consumer split is exactly what a `tsc --noEmit` on a dirty tree cannot see.

  2. CRUSHED CONTROLS. StudioToolbar's shared `btn` class carried neither
     shrink-0 nor whitespace-nowrap. A flex child is shrinkable by DEFAULT, so
     with the chat panel open on a narrow viewport the triggers compressed below
     their text and the label wrapped mid-button ("New / — / slide" three lines
     tall). A control's label is its meaning: it never wraps. The selection chip
     (min-w-0 + truncate) is the elastic part that yields first.

  3. PHANTOM 404s. useFileLoad fetched `/api/workspace/file?path=` whenever a
     caller had no file yet (the Studio landing, the file modal opening empty) —
     a 404 per mount, doubled by StrictMode. Console noise that reads like a
     broken artifact, plus a `notFound` racing the real load.

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
    web = Path(__file__).resolve().parent.parent / "web"
    strip = (web / "components/shell/GlobalLocatorStrip.tsx").read_text()
    chat = (web / "components/chat-surface/ChatSurface.tsx").read_text()
    studio = (web / "components/studio/StudioSurface.tsx").read_text()
    ctx = (web / "contexts/BreadcrumbContext.tsx").read_text()
    toolbar = (web / "components/studio/StudioToolbar.tsx").read_text()
    loader = (web / "components/workspace/useFileLoad.ts").read_text()

    # ── 1. one locator, never two ───────────────────────────────────────────
    _check(
        "the PRODUCER exists (useSelfLocatedSurface + registry)",
        "export function useSelfLocatedSurface(slug: string, on: boolean = true): void" in ctx
        and "setSelfLocated" in ctx,
    )
    # The consumer is the half that was stranded — assert it SHIPS.
    _check(
        "the CONSUMER ships: the OS strip suppresses for a self-located surface",
        "isSelfLocated" in strip
        and "if (foregrounded && isSelfLocated(foregrounded)) return null;" in strip,
    )
    _check(
        "the strip hardcodes NO slug (surfaces declare; the strip only listens)",
        not re.search(r"isSelfLocated\(\s*['\"]", strip),
    )
    # (Re-pinned 2026-07-21: ADR-473 made the Studio surface app-generic — the
    #  self-located declaration keys on app.slug, not the 'studio' literal.)
    _check(
        "Studio declares self-located ONLY in the workbench (the start state keeps the strip)",
        "useSelfLocatedSurface(app.slug, Boolean(artifactPath));" in studio,
    )
    _check(
        "Chat declares self-located (lane column + conversation header name it)",
        "useSelfLocatedSurface('chat', true);" in chat,
    )
    _check(
        "Studio still RENDERS its own crumb (suppressing the strip must not orphan it)",
        'onClick={() => setParam({ file: null })}' in studio and ">\n                Studio\n              </button>" in studio,
    )

    # ── 2. controls don't buckle ────────────────────────────────────────────
    btn_decl = toolbar.split("const btn =", 1)[-1].split(";", 1)[0]
    _check(
        "toolbar triggers never shrink (shrink-0)",
        "shrink-0" in btn_decl,
    )
    _check(
        "toolbar trigger LABELS never wrap (whitespace-nowrap)",
        "whitespace-nowrap" in btn_decl,
    )
    # The selection chip was the elastic part of this row — it is GONE (2026-07-15,
    # b5495fc): ADR-458 moved the entrance to hover, so the chip's one job (the
    # receipt proving your click landed) lost its errand, and the navigator ring +
    # canvas marking + Design-tab scope already tell that fact. Nothing in the row
    # is elastic now; every trigger is shrink-0 + nowrap (checked above). The
    # selection STATE is untouched — only its third rendering went.
    _check(
        "the selection chip stays deleted (hover is the entrance, not a receipt)",
        "onClearSelection" not in toolbar,
    )
    # The row hosts absolute `top-full` panels — making it a scroll container
    # would clip every dropdown. This guards a tempting "fix" that breaks menus.
    root_row = toolbar.split("<div ref={rootRef}", 1)[-1].split(">", 1)[0]
    _check(
        "the toolbar row is NOT a scroll container (would clip the top-full panels)",
        "overflow-x-auto" not in root_row and "overflow-hidden" not in root_row,
    )

    # ── 3. no phantom fetch ─────────────────────────────────────────────────
    _check(
        "useFileLoad no-ops on an empty path (no `?path=` 404 per mount)",
        "if (!path) {" in loader and "setNotFound(false);" in loader,
    )
    _check(
        "the empty-path branch settles to IDLE, not loading (no spinner forever)",
        bool(re.search(r"if \(!path\) \{[^}]*setLoading\(false\);", loader, re.S)),
    )
    _check(
        "the empty-path branch returns BEFORE the fetch",
        loader.index("if (!path) {") < loader.index("api.workspace\n      .getFile(path)"),
    )

    # ── 4. the deck auto-fit actually measures ──────────────────────────────
    # A deck's stage is a fixed 992px. The canvas auto-fits it to the column by
    # measuring the iframe's clientWidth — but the measuring effect keyed only on
    # [isDeck], and on first mount the content hasn't loaded, so isDeck is false:
    # the effect settled fitScale=1 and NEVER re-ran (iframeRef is a ref — the
    # frame appearing re-renders nothing). The deck then drew its 992px stage 1:1
    # inside a ~370px column and the member saw a slide's blank left margin — a
    # canvas that reads as broken but is merely unfitted (the zoom chip still
    # says 100%, the tell). Re-running once `projected` lands fixes it.
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    # ADR-471: the fit generalized deck→staged (deck slides + canvas
    # artboards, per-template stage width) — the check's intent is unchanged:
    # `projected` must be a dependency so the fit re-measures once content
    # lands.
    _check(
        "the staged auto-fit re-measures once the projection lands (not [isStaged] alone)",
        "}, [isStaged, stageW, projected]);" in canvas,
    )
    _check(
        "the fit feeds the zoom the runtime applies (fitScale × zoom)",
        "const effectiveZoom = fitScale * zoom;" in canvas
        and "scale: effectiveZoom" in canvas,
    )
    _check(
        "a fresh load re-posts the current zoom (the runtime resets on reload)",
        "scale: zoomRef.current" in canvas and "onLoad={commandEdit}" in canvas,
    )
    # The projection must never fall back to raw content (the iframe allows
    # scripts; only the projection strips artifact-authored executables) — but a
    # silent blank is undiagnosable, so the failure path must leave a breadcrumb.
    _check(
        "a projection failure blanks the canvas AND logs (never falls back to raw)",
        "console.error('[STUDIO] projection failed" in canvas and "setProjected('')" in canvas,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
