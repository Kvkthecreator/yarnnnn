"""ADR-370 gate — Context: the operation's boundary surface (In · Out · Flow).

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies:
  - the `context` kernel surface exists (primary tier, composition, /context route)
  - the `feed` mirror folded in (default_pinned False, still registered as the Flow body)
  - the prior /context → /files redirect stub is gone (route reclaimed)
  - /feed is now a redirect stub → /context?context.pane=flow
  - the FE wiring (desk slug union/array, SurfaceRegistry feed→ContextPage,
    /context page lenses, EmissionsView, api.emissions, in-Feed button rename)
  - the read-only GET /api/emissions route exists + is registered (no write path)

IMPORTANT: run as a SCRIPT (`python test_adr370_context_surface.py`), not under
pytest — check() records failures via globals + sys.exit.

Usage:
    cd api
    python test_adr370_context_surface.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
_WEB = _API_ROOT.parent / "web"

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


def _read(rel: str, root: Path = _WEB) -> str:
    p = root / rel
    return p.read_text() if p.exists() else ""


def test_kernel_surface_registry() -> None:
    print("\n[kernel] context surface declared; feed folded in (D1/D4)")
    from services.kernel_surfaces import KERNEL_SURFACES, kernel_surface_slugs

    slugs = kernel_surface_slugs()
    check("`context` in kernel surface slugs", "context" in slugs)
    check("`feed` still in slugs (Flow body survives)", "feed" in slugs)

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    ctx = by_slug.get("context", {})
    check("context launcher_tier == primary", ctx.get("launcher_tier") == "primary",
          str(ctx.get("launcher_tier")))
    check("context route == /context", ctx.get("route") == "/context", str(ctx.get("route")))
    check("context register == application (a composition window)",
          ctx.get("register") == "application", str(ctx.get("register")))
    check("context default_pinned True (inherits Feed's slot)",
          ctx.get("default_pinned") is True)

    feed = by_slug.get("feed", {})
    check("feed default_pinned flipped False (slot inherited by context)",
          feed.get("default_pinned") is False, str(feed.get("default_pinned")))
    check("feed route still /feed (redirect-stub transport)", feed.get("route") == "/feed")


def test_routes_reclaimed() -> None:
    print("\n[routes] /context reclaimed; /feed → /context?context.pane=flow (D4/D5)")
    ctx_page = _read("app/(authenticated)/context/page.tsx")
    check("/context page is the real surface (SettingsPaneShell), not a /files redirect",
          "SettingsPaneShell" in ctx_page and "windowSlug=\"context\"" in ctx_page)
    check("/context page no longer redirects to /files",
          "redirect(" not in ctx_page or "/files" not in ctx_page)

    feed_page = _read("app/(authenticated)/feed/page.tsx")
    check("/feed page is a redirect stub", "redirect(" in feed_page)
    check("/feed redirects to /context", "/context" in feed_page)
    check("/feed merges to the flow pane", "context.pane" in feed_page and "flow" in feed_page)
    check("/feed redirect is pure server transport (no 'use client')",
          "'use client'" not in feed_page)


def test_three_lenses() -> None:
    print("\n[lenses] In · Out · Flow (D2)")
    ctx_page = _read("app/(authenticated)/context/page.tsx")
    for key in ('"in"', '"out"', '"flow"'):
        check(f"context page declares pane {key}", key in ctx_page)
    check("In mounts ConnectedIntegrationsSection (connectors)",
          "ConnectedIntegrationsSection" in ctx_page)
    check("In mounts SourcesCard (sources/RSS)", "SourcesCard" in ctx_page)
    check("Out mounts EmissionsView", "EmissionsView" in ctx_page)
    check("Flow mounts FeedSurface (narrative intact)", "FeedSurface" in ctx_page)
    check("default pane is flow (the full narrative)", 'defaultPane="flow"' in ctx_page)


def test_fe_wiring() -> None:
    print("\n[fe] desk union/array, registry feed→ContextPage, icon, api method")
    desk = _read("types/desk.ts")
    check("desk.ts KernelSurfaceSlug includes 'context'", "| 'context'" in desk)
    check("desk.ts KERNEL_SURFACE_SLUGS array includes 'context'", "'context'," in desk)

    reg = _read("components/shell/SurfaceRegistry.tsx")
    check("SurfaceRegistry maps context: ContextPage", "context: ContextPage" in reg)
    check("SurfaceRegistry maps feed → ContextPage (Flow default, not redirect)",
          "feed: ContextPage" in reg)
    check("SurfaceRegistry no longer imports FeedPage", "import FeedPage" not in reg)

    icons = _read("lib/shell/surface-icons.tsx")
    check("surface-icons registers arrow-left-right (the boundary glyph)",
          "'arrow-left-right'" in icons and "ArrowLeftRight" in icons)

    client = _read("lib/api/client.ts")
    check("api client has emissions() method", "emissions:" in client and "/api/emissions" in client)

    emissions_view = _read("components/context/EmissionsView.tsx")
    check("EmissionsView reads api.emissions (read-only Out lens)",
          "api.emissions" in emissions_view)

    feed_surface = _read("components/feed-surface/FeedSurface.tsx")
    check("in-Feed 'Context' button renamed → 'Substrate'",
          "Substrate" in feed_surface and ">\n      Context\n" not in feed_surface)


def test_emissions_route() -> None:
    print("\n[backend] GET /api/emissions — read-only union, no write path (D Out)")
    import routes.emissions as em
    check("emissions router imports cleanly", hasattr(em, "router"))
    src = (_API_ROOT / "routes" / "emissions.py").read_text()
    check("reads destination_delivery_log", "destination_delivery_log" in src)
    check("reads notifications", '"notifications"' in src)
    check("no write path (no .insert/.update/.upsert/.delete)",
          not any(w in src for w in (".insert(", ".update(", ".upsert(", ".delete(")))

    main_src = (_API_ROOT / "main.py").read_text()
    check("emissions router registered in main.py",
          "emissions.router" in main_src and "/api/emissions" in main_src)


def main() -> int:
    print("=" * 64)
    print("ADR-370 — Context boundary surface (In · Out · Flow)")
    print("=" * 64)
    test_kernel_surface_registry()
    test_routes_reclaimed()
    test_three_lenses()
    test_fe_wiring()
    test_emissions_route()
    print("\n" + "=" * 64)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 64)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
