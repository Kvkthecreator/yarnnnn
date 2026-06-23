"""Regression guard — ADR-316: chat as a dockable rail, not an occluding overlay.

Enforces the spatial-model decision:

  1. The chat-drawer kernel surface lives in the `main-rail` region, NOT
     `floating-overlay`. The rail reduces the surface area; it never
     occludes the surface it is "Viewing."

  2. `main-rail` is a legal LayoutRegion on both the backend
     (kernel_surfaces.py docstring + the test_adr297 legal set) and the FE
     (web/lib/compositor/types.ts LayoutRegion union).

  3. ShellCompositor mounts the `main-rail` region INSIDE the `main` flex
     row (a flex sibling of SurfaceViewport), not in the floating-overlay
     mount — so the surface genuinely reflows.

  4. Window geometry is relative to the DESKTOP, not the raw viewport:
     the Desktop reports its measured bounds and the geometry math
     (cascade / maximize) reads them. This keeps windows out from under
     the rail. We assert the seam exists (setDesktopBounds wired) rather
     than the pixels.

Run: cd api && python test_adr316_chat_rail.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"

sys.path.insert(0, str(REPO_ROOT / "api"))

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
    # --- 1. chat-drawer lives in main-rail, not floating-overlay ---
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {s["slug"]: s for s in KERNEL_SURFACES}
    chat = by_slug.get("chat-drawer")
    _assert(chat is not None, "chat-drawer kernel surface exists")
    if chat:
        _assert(
            chat.get("default_region") == "main-rail",
            f"chat-drawer region is main-rail (got {chat.get('default_region')})",
        )
        _assert(
            chat.get("default_region") != "floating-overlay",
            "chat-drawer is NOT in floating-overlay (no longer occludes)",
        )
        _assert(
            chat.get("default_visibility") == "summon",
            "chat-drawer is still FAB-summoned (visibility=summon)",
        )
        _assert(
            chat.get("archetype") == "input",
            "chat-drawer archetype unchanged (input)",
        )

    # --- 2. main-rail is a legal region on the FE union ---
    types = _read("lib/compositor/types.ts")
    _assert("'main-rail'" in types, "LayoutRegion union includes 'main-rail'")

    # --- 3. ShellCompositor mounts main-rail inside the main flex row ---
    compositor = _read("components/shell/ShellCompositor.tsx")
    _assert(
        "flex flex-row" in compositor or "flex-row" in compositor,
        "ShellCompositor main region is a flex row",
    )
    _assert(
        "mountRegion('main-rail')" in compositor,
        "ShellCompositor mounts the main-rail region",
    )
    # The main-rail mount must render INSIDE <main> ... </main>, not in the
    # floating-overlay tail. ADR-358 (2026-06-23) hoisted the mount to a
    # `chatRail` const so it can render on either side of the surface column
    # (left in canvas, right in desktop); the const is then placed inside
    # <main> via `{chatRail}`. Assert the durable BEHAVIOR (the rail renders
    # inside <main>) rather than the literal call-site position.
    main_open = compositor.find("<main")
    main_close = compositor.find("</main>")
    rail_render = compositor.find("{chatRail}")
    _assert(
        main_open != -1 and main_close != -1 and main_open < rail_render < main_close,
        "main-rail (chatRail) renders inside the <main> flex row",
    )

    # --- 4. Window geometry is desktop-relative (the D6 seam) ---
    prefs = _read("lib/shell/useSurfacePreferences.tsx")
    _assert("setDesktopBounds" in prefs, "provider exposes setDesktopBounds")
    _assert(
        "desktopBoundsRef" in prefs,
        "geometry reads desktopBoundsRef (cascade/maximize)",
    )
    _assert(
        "computeMaximizedGeometryFromBounds" in prefs,
        "maximize uses the desktop-bounds geometry helper",
    )
    desktop = _read("components/shell/Desktop.tsx")
    _assert(
        "setDesktopBounds" in desktop and "ResizeObserver" in desktop,
        "Desktop reports its measured bounds via ResizeObserver",
    )
    viewport = _read("components/shell/SurfaceViewport.tsx")
    _assert(
        "desktopBounds" in viewport and "clampWidth" in viewport,
        "SurfaceViewport clamps drag to desktop bounds, not raw viewport",
    )

    # --- 5. ChatDrawer carries a docked-rail AND an overlay layout mode ---
    # ADR-358 (2026-06-23) generalized the mobile-overlay branch into an
    # `overlayMode` branch (mobile + desktop layout mode); canvas keeps the
    # docked rail. Assert the durable BEHAVIOR (chat has both a docked-rail
    # path and a fixed-overlay path) rather than the old `if (isMobile)`
    # literal — the overlay still serves mobile, just via overlayMode.
    drawer = _read("components/shell/chrome/ChatDrawer.tsx")
    _assert("ADR-316" in drawer, "ChatDrawer cites ADR-316")
    _assert(
        "if (overlayMode)" in drawer and "railMode" in drawer,
        "ChatDrawer carries both a docked-rail and a fixed-overlay path",
    )

    print("\n" + "=" * 60)
    status = "PASS" if _failed == 0 else "FAIL"
    print(f"ADR-316 chat-rail regression gate: {_passed} passed, {_failed} failed [{status}]")
    print("=" * 60)
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
