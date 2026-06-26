"""Global locator strip gate (2026-06-26).

The per-window title-bar breadcrumb was conditional three ways — only in
desktop multi-window mode (WindowFrame had a title bar), only in detail mode
(segments registered), and on 3 surfaces — and was SUPPRESSED entirely in
canvas mode (`chromeless`, ADR-358). The operator saw NO locator at all in
canvas. A locator that hides most of the time is more confusing than none.

Fix: ONE global locator strip (GlobalLocatorStrip), mounted once in the shell
chrome, ALWAYS visible (every layout, list + detail), showing the FOREGROUNDED
surface's location (`Title › segments`). The per-slug crumb REGISTRATION
(`useWindowCrumb`) is unchanged as the segment source; only the RENDER moves —
keyed on `foregrounded`, not per-window. Singular Implementation: the strip is
the ONE consumer of getCrumb.

FE-only — source-guard style (no JS test runner); `tsc --noEmit` is the
companion type gate run in web/.

Invariants:
  1. GlobalLocatorStrip exists, reads `foregrounded`, and consumes getCrumb
     keyed on the foregrounded slug (getCrumb(foregrounded)).
  2. It is mounted in ShellCompositor between the top region and <main>.
  3. WindowFrame no longer carries the `crumb` prop or renders crumb segments.
  4. SurfaceViewport no longer threads getCrumb to WindowFrame.
  5. getCrumb is consumed in EXACTLY ONE component file (the strip) — no two
     crumb renderers.
  6. The 3 detail surfaces still REGISTER segments via useWindowCrumb (the
     source is preserved, only the render moved).
  7. The slug->title helper is shared (surfaceTitleFor) — not duplicated
     between SurfaceViewport and the strip.

Run: pytest test_global_locator_strip.py -q
"""
from __future__ import annotations

import glob
import os

_WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


def test_strip_exists_and_keys_on_foregrounded():
    src = _read_web("components/shell/GlobalLocatorStrip.tsx")
    assert "export function GlobalLocatorStrip" in src
    # reads the foregrounded slug from the window manager
    assert "useSurfacePreferences" in src and "foregrounded" in src
    # consumes the crumb registry keyed on the FOREGROUNDED slug (not per-window)
    assert "getCrumb(foregrounded)" in src
    # shared title helper (not a private duplicate)
    assert "surfaceTitleFor" in src


def test_strip_is_seamless_no_border_no_tint():
    """Operator: the strip should look continuous, not a separate bar. No
    bottom border, no tinted background — it sits in the same plane (bg-
    background) as the content below."""
    src = _read_web("components/shell/GlobalLocatorStrip.tsx")
    assert "border-b" not in src, "the locator strip must not carry a bottom border (seamless)."
    assert "bg-muted" not in src, "the locator strip must not carry a tinted background (seamless)."
    assert "bg-background" in src


def test_root_title_is_navigational_when_drilled_in():
    """When there are detail segments, the ROOT surface-title is a clickable
    'back to list' link (fires the leaf's onClick = clear the deep-link
    param). Previously the root was a plain non-clickable span."""
    src = _read_web("components/shell/GlobalLocatorStrip.tsx")
    assert "backToList" in src
    # the root renders as a <button> when backToList is present
    assert "backToList ? (" in src and "onClick={() => backToList()}" in src


def test_mobile_is_leaf_only_chip():
    """Mobile drops the redundant root name (the surface header already names
    it) and shows a leaf-only back-chip; list mode collapses to nothing."""
    src = _read_web("components/shell/GlobalLocatorStrip.tsx")
    assert "viewport.isMobile" in src
    # mobile branch returns null in list mode (no segments)
    assert "if (crumb.length === 0) return null;" in src
    # leaf-only chip uses a back chevron
    assert "ChevronLeft" in src


def test_strip_mounted_in_shell_between_top_and_main():
    src = _read_web("components/shell/ShellCompositor.tsx")
    assert "import { GlobalLocatorStrip }" in src
    assert "<GlobalLocatorStrip />" in src
    # mounted BEFORE the <main> content row (so it sits below the top bar,
    # above the surface column, in every layout)
    assert src.index("<GlobalLocatorStrip />") < src.index("<main"), (
        "the locator strip must mount above the <main> content row."
    )


def test_windowframe_no_longer_renders_crumb():
    src = _read_web("components/shell/WindowFrame.tsx")
    # the `crumb` prop is gone from the props interface
    assert "crumb?: BreadcrumbSegment[]" not in src
    # the crumb-segment import + render markers are gone
    assert "ChevronRight" not in src
    assert "getCrumb" not in src
    assert "TITLE_CRUMB_COLLAPSE_PX" not in src


def test_surfaceviewport_no_longer_threads_crumb():
    src = _read_web("components/shell/SurfaceViewport.tsx")
    assert "getCrumb" not in src
    assert "crumb={" not in src
    assert "useWindowCrumbRegistry" not in src


def test_getcrumb_has_exactly_one_component_consumer():
    """Singular Implementation: only the strip renders the crumb."""
    consumers = []
    for path in glob.glob(os.path.join(_WEB, "components", "**", "*.tsx"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            if "getCrumb(" in fh.read():
                consumers.append(os.path.basename(path))
    assert consumers == ["GlobalLocatorStrip.tsx"], (
        f"getCrumb must be consumed by exactly one component (the strip); found {consumers}"
    )


def test_segment_registration_preserved_on_three_surfaces():
    """The render moved; the SOURCE (useWindowCrumb registration) stays."""
    for rel in (
        "app/(authenticated)/agents/page.tsx",
        "app/(authenticated)/files/page.tsx",
        "app/(authenticated)/recurrence/page.tsx",
    ):
        assert "useWindowCrumb" in _read_web(rel), (
            f"{rel} must still register its in-window crumb segments."
        )


def test_title_helper_is_shared_not_duplicated():
    helper = _read_web("lib/compositor/surfaceTitle.ts")
    assert "export function surfaceTitleFor" in helper
    # both consumers import it
    assert "surfaceTitleFor" in _read_web("components/shell/SurfaceViewport.tsx")
    assert "surfaceTitleFor" in _read_web("components/shell/GlobalLocatorStrip.tsx")


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
