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

    # --- 3. ShellCompositor: fixed order (surface, then rail) ---
    # ADR-358 revised — chat always renders RIGHT of the surface column. In
    # canvas it is a docked flex rail; in desktop/mobile it is a fixed
    # overlay (zero flex space). So the order is fixed and the compositor no
    # longer branches on layoutMode at all.
    comp = _read("components/shell/ShellCompositor.tsx")
    _assert("ADR-358" in comp, "ShellCompositor cites ADR-358")
    _assert(
        "layoutMode" not in comp,
        "ShellCompositor no longer reads layoutMode (order is fixed)",
    )
    main_open = comp.find("<main")
    main_close = comp.find("</main>")
    row = comp[main_open:main_close] if main_open != -1 else ""
    _assert(
        row.find("{surfaceColumn}") != -1
        and row.find("{chatRail}") != -1
        and row.find("{surfaceColumn}") < row.find("{chatRail}"),
        "surface column renders before the chat rail (chat docks RIGHT)",
    )

    # --- 4. ChatDrawer: railMode (canvas) vs overlayMode (desktop+mobile) ---
    drawer = _read("components/shell/chrome/ChatDrawer.tsx")
    _assert("ADR-358" in drawer, "ChatDrawer cites ADR-358")
    _assert(
        "useShellChrome" in drawer and "layoutMode === 'canvas'" in drawer,
        "ChatDrawer reads layoutMode",
    )
    # railMode is the ONLY docked posture: canvas on a wide viewport.
    _assert(
        "const railMode = !isMobile && layoutMode === 'canvas'" in drawer,
        "chat is a docked rail only in canvas on a wide viewport",
    )
    _assert(
        "const overlayMode = !railMode" in drawer,
        "everything else (desktop layout + mobile) is the summoned overlay",
    )
    # The overlay branch fires on overlayMode (not just isMobile) — this is
    # what un-pins Desktop-mode chat.
    _assert(
        "if (overlayMode)" in drawer,
        "the fixed-overlay branch fires on overlayMode (desktop un-pinned)",
    )
    # The Canvas rail docks RIGHT: border on the left edge, width measured
    # from the viewport's right edge. (No left/right flip — one geometry.)
    _assert(
        "window.innerWidth - e.clientX" in drawer
        and "dockLeft" not in drawer,
        "the canvas rail docks RIGHT (innerWidth − clientX; no dockLeft flip)",
    )
    _assert(
        "border-l border-border shadow-xl" in drawer,
        "the right-docked rail's border is on its left edge",
    )
    # Chat never becomes a window (ADR-316 Alternative A stays rejected).
    _assert(
        "WindowFrame" not in drawer,
        "chat is never a window — it is chrome in every mode",
    )
    # One width store across modes.
    _assert(
        drawer.count("DRAWER_WIDTH_KEY") >= 2,
        "one width store (DRAWER_WIDTH_KEY) shared across modes",
    )

    # --- 4b. Default-open posture is mode-aware ---
    # Rail (canvas, wide) defaults OPEN; overlay (desktop/mobile) defaults
    # CLOSED (it would otherwise pop open over the windows). And switching
    # mode re-derives the posture.
    ctx_open = ctx  # re-use the ShellChromeContext source read above
    _assert(
        "const railMode = !isMobile && mode === 'canvas'" in ctx_open,
        "drawer default-open is computed from railMode (canvas + wide)",
    )
    _assert(
        "setDrawerOpen(railMode); // unset → open only when docked rail" in ctx_open,
        "unset posture → open only when chat is the docked rail",
    )
    _assert(
        "setLayoutMode" in ctx_open
        and "setDrawerOpen(railMode)" in ctx_open.split("const setLayoutMode")[1],
        "switching mode re-derives the chat posture (open canvas / close desktop)",
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

    # --- 5b. Desktop layer fills with ONE surface in canvas (no wallpaper) ---
    # The operator's point: canvas's left is the PRIMARY SURFACE filling the
    # column, NOT a desktop with a floating window on gray wallpaper. So the
    # Desktop layer drops its padded gray wallpaper when a surface is mounted
    # in canvas mode; desktop mode keeps the D17 wallpaper.
    desktop = _read("components/shell/Desktop.tsx")
    _assert("ADR-358" in desktop, "Desktop cites ADR-358")
    _assert(
        "layoutMode === 'canvas' && hasWindows" in desktop,
        "Desktop derives canvasFill (canvas + a mounted surface)",
    )
    _assert(
        "canvasFill ? 'bg-background' : 'bg-muted/30 p-3 sm:p-4'" in desktop,
        "canvas fills edge-to-edge (no wallpaper/padding); desktop keeps it",
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
