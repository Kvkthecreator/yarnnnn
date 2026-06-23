"""Regression guard — ADR-358: layout mode (Canvas vs Desktop).

Enforces the operator-chosen-spatial-paradigm decision. The shell runs in
one of two whole arrangements; the operator picks at the UserMenu:

  CANVAS  — chat-LEFT + one full-bleed surface-RIGHT, side-to-side divider
            only (the ChatGPT/Claude convention). DEFAULT.
  DESKTOP — the ADR-297 D15 free-floating window manager + ADR-316
            right-docked rail.

The invariant ADR-358 protects: within a mode, chat and surfaces speak the
SAME spatial language (the contradiction it fixes was cross-mode welding —
a fixed rail beside a floating-window field). And: it is Singular
Implementation — one compositor, one chat component, one window manager,
with a mode discriminator over them, NOT a fork.

These are SOURCE assertions over the six touched .tsx files (the repo has
no JS test runner outside node_modules; this matches the ADR-316 gate
pattern — read the files, assert on their content).

Run: cd api && python test_adr358_layout_mode.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"

_passed = 0
_failed = 0


def _assert(cond: bool, label: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
    else:
        _failed += 1
        print(f"  FAIL: {label}")


def _read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def main() -> None:
    # --- 1. layoutMode is operator state in ShellChromeContext ---
    ctx = _read("components/shell/ShellChromeContext.tsx")
    _assert("ADR-358" in ctx, "ShellChromeContext cites ADR-358")
    _assert(
        "export type LayoutMode = 'canvas' | 'desktop'" in ctx,
        "LayoutMode union is exactly {canvas, desktop}",
    )
    _assert(
        "yarnnn:shell:layout-mode" in ctx,
        "layout mode persists to its own localStorage key",
    )
    _assert(
        "DEFAULT_LAYOUT_MODE: LayoutMode = 'canvas'" in ctx,
        "the DEFAULT layout mode is canvas (the chat-interface convention)",
    )
    _assert(
        "layoutMode: LayoutMode" in ctx and "setLayoutMode" in ctx,
        "the context exposes layoutMode + setLayoutMode",
    )
    # SSR-safety: state initializes to the DEFAULT (not a localStorage read)
    # so the server render matches the first client render. The stored value
    # is applied in a post-mount effect, mirroring drawerOpen.
    _assert(
        "useState<LayoutMode>(DEFAULT_LAYOUT_MODE)" in ctx,
        "layoutMode SSR-initializes to the default (no hydration mismatch)",
    )

    # --- 2. UserMenu carries the Canvas/Desktop toggle, desktop-only ---
    menu = _read("components/shell/UserMenu.tsx")
    _assert("ADR-358" in menu, "UserMenu cites ADR-358")
    _assert(
        "useShellChrome" in menu and "setLayoutMode" in menu,
        "UserMenu reads layoutMode + setLayoutMode from chrome context",
    )
    _assert(
        "setLayoutMode('canvas')" in menu and "setLayoutMode('desktop')" in menu,
        "UserMenu offers BOTH Canvas and Desktop choices",
    )
    # Mode is desktop-only — inert on mobile (one arrangement is possible),
    # so the control is hidden below the breakpoint.
    _assert(
        "!isMobile &&" in menu,
        "the layout toggle is hidden on mobile (mode is desktop-only)",
    )

    # --- 3. ShellCompositor: child order IS the spatial paradigm ---
    comp = _read("components/shell/ShellCompositor.tsx")
    _assert("ADR-358" in comp, "ShellCompositor cites ADR-358")
    _assert(
        "useShellChrome" in comp and "layoutMode" in comp,
        "ShellCompositor reads layoutMode",
    )
    _assert(
        "layoutMode === 'canvas'" in comp,
        "ShellCompositor branches the flex row on canvas mode",
    )
    # In canvas the chatRail must render BEFORE the surface column (left
    # dock); in desktop AFTER (right dock). The canvas branch is the first
    # ternary arm — assert chatRail precedes surfaceColumn there.
    canvas_branch_start = comp.find("layoutMode === 'canvas' ? (")
    _assert(canvas_branch_start != -1, "ShellCompositor has the canvas ternary")
    if canvas_branch_start != -1:
        # Within the canvas arm (up to the `: (` desktop arm), chatRail first.
        desktop_arm = comp.find(") : (", canvas_branch_start)
        canvas_arm = comp[canvas_branch_start:desktop_arm]
        _assert(
            canvas_arm.find("{chatRail}") < canvas_arm.find("{surfaceColumn}"),
            "canvas mode docks the rail LEFT (chatRail before surfaceColumn)",
        )
        desktop_arm_text = comp[desktop_arm:comp.find("</main>", desktop_arm)]
        _assert(
            desktop_arm_text.find("{surfaceColumn}") < desktop_arm_text.find("{chatRail}"),
            "desktop mode docks the rail RIGHT (surfaceColumn before chatRail)",
        )

    # --- 4. ChatDrawer: dock side + resize edge flip on layoutMode ---
    drawer = _read("components/shell/chrome/ChatDrawer.tsx")
    _assert("ADR-358" in drawer, "ChatDrawer cites ADR-358")
    _assert(
        "useShellChrome" in drawer and "layoutMode === 'canvas'" in drawer,
        "ChatDrawer derives dockLeft from canvas mode",
    )
    _assert("const dockLeft" in drawer, "ChatDrawer computes dockLeft")
    # Resize math is anchored-edge-aware: left dock measures from the
    # viewport left (e.clientX), right dock from the right (innerWidth − x).
    _assert(
        "dockLeft ? e.clientX : window.innerWidth - e.clientX" in drawer,
        "resize width is measured from the anchored edge (dock-side aware)",
    )
    # Border + handle flip: right border + handle-after-body when left-docked.
    _assert(
        "dockLeft ? 'border-r' : 'border-l'" in drawer,
        "the rail's border edge flips with the dock side",
    )
    # One width store — the dragged width persists to the SAME key in both
    # modes (Singular width store, not per-mode state).
    _assert(
        drawer.count("DRAWER_WIDTH_KEY") >= 2,
        "one width store (DRAWER_WIDTH_KEY) shared across dock sides",
    )
    # Mobile overlay branch survives unchanged (ADR-316 preserved).
    _assert(
        "if (isMobile)" in drawer,
        "ChatDrawer keeps the mobile overlay branch (ADR-316 preserved)",
    )

    # --- 5. SurfaceViewport: canvas forces ONE full-bleed surface ---
    sv = _read("components/shell/SurfaceViewport.tsx")
    _assert("ADR-358" in sv, "SurfaceViewport cites ADR-358")
    _assert(
        "const canvasMode = layoutMode === 'canvas'" in sv,
        "SurfaceViewport derives canvasMode",
    )
    _assert(
        "const singleSurface = viewport.isMobile || canvasMode" in sv,
        "single-surface render fires on mobile OR canvas (reuses one branch)",
    )
    _assert(
        "if (singleSurface && hasWindows)" in sv,
        "the single-surface branch is gated on singleSurface, not just mobile",
    )
    # The multi-window manager (ADR-297 D15) survives for desktop mode —
    # the mountSlugs.map(...) branch is still present and unconditional.
    _assert(
        "mountSlugs.map(" in sv,
        "the desktop multi-window manager branch survives (ADR-297 D15)",
    )
    # Canvas passes chromeless to the single WindowFrame; mobile does not
    # (mobile keeps its frame per ADR-297 D15.2).
    _assert(
        "chromeless={canvasMode}" in sv,
        "canvas suppresses window chrome; mobile keeps it (chromeless=canvasMode)",
    )

    # --- 6. WindowFrame: chromeless prop suppresses title bar + border ---
    wf = _read("components/shell/WindowFrame.tsx")
    _assert("ADR-358" in wf, "WindowFrame cites ADR-358")
    _assert("chromeless?: boolean" in wf, "WindowFrame accepts a chromeless prop")
    _assert(
        "chromeless = false" in wf,
        "chromeless defaults false (existing windows unaffected)",
    )
    _assert(
        "{!chromeless && (" in wf,
        "the title bar is suppressed when chromeless",
    )
    _assert(
        "!chromeless && 'rounded-lg border shadow-sm'" in wf,
        "border + rounding + shadow are dropped when chromeless",
    )

    # --- 7. Singular Implementation: the binding is mode-INDEPENDENT ---
    # surfaceOverride + "Viewing: X" read `foregrounded` in BOTH modes —
    # the agent-context binding does not branch on layout mode.
    _assert(
        "surfaceOverride" in drawer and "foregrounded" in drawer,
        "the surfaceOverride/Viewing binding reads foregrounded (mode-independent)",
    )
    _assert(
        "layoutMode" not in _read("lib/shell/useSurfacePreferences.tsx"),
        "the window-manager core does NOT know about layoutMode (clean seam)",
    )

    print("\n" + "=" * 60)
    status = "PASS" if _failed == 0 else "FAIL"
    print(f"ADR-358 layout-mode regression gate: {_passed} passed, {_failed} failed [{status}]")
    print("=" * 60)
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
