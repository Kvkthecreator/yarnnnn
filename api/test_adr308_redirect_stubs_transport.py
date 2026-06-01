"""Regression guard — ADR-308: redirect stubs as pure transport.

Enforces the invariant that closes the OS-shell bimodality seam:

  A redirect stub is TRANSPORT, not a surface. It must never render inside
  the OS shell. Every authenticated-interior redirect stub uses
  `redirect()` from next/navigation (a server redirect, fired before any
  layout mounts) — NOT the client pattern (`'use client'` + `useEffect` +
  `router.replace`/`router.push` returning null/spinner).

Why: a client redirect stub mounts inside AuthenticatedLayout →
ShellCompositor → SurfaceViewport and paints ONE orphaned frame (no
Desktop layer, dead dock) before redirecting. That frame is the
"looks fine, breaks" seam (ADR-297 D19.4 declared the fallback branch
auth-boundary-only; the stubs violated it). Server `redirect()` never
enters the shell.

Two banned classes inside web/app/(authenticated)/*/page.tsx:

  1. A page that is `'use client'` AND performs a router redirect
     (`router.replace`/`router.push`) in a `useEffect` — the client-stub
     shape. Such a page is a redirect stub wearing client clothes; it
     must be a server `redirect()` instead.

  2. A server-`redirect()` stub whose target does NOT resolve to a live
     route (dead/stale target — the `/docs` "Redirecting to Context…"
     class). Targets are checked against live Next.js route segments.

Scope: web/app/(authenticated)/{slug}/page.tsx only (the route pages).
Nested dynamic routes ([id]) and non-page files are out of scope.

Run: cd api && python test_adr308_redirect_stubs_transport.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"
AUTH_DIR = WEB / "app" / "(authenticated)"

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


def _top_level_page_files() -> list[Path]:
    """`app/(authenticated)/{slug}/page.tsx` — top-level route pages only."""
    out: list[Path] = []
    if not AUTH_DIR.is_dir():
        return out
    for child in AUTH_DIR.iterdir():
        if child.is_dir():
            p = child / "page.tsx"
            if p.is_file():
                out.append(p)
    return out


def _live_route_segments() -> set[str]:
    """First path-segments of every live Next.js route under web/app."""
    app = WEB / "app"
    live: set[str] = {"llms.txt", "sitemap.xml", "robots.txt"}
    auth = app / "(authenticated)"
    if auth.is_dir():
        live |= {p.name for p in auth.iterdir() if p.is_dir()}
    for p in app.iterdir():
        if p.is_dir() and p.name not in ("(authenticated)", "api"):
            live.add(p.name)
    return live


# =============================================================================
# Group 1 — no client-stub redirect pattern inside (authenticated) pages
# =============================================================================


def test_no_client_redirect_stubs() -> None:
    print("\n[1] no client-stub redirect pattern in (authenticated)/*/page.tsx")

    violations: list[str] = []
    for page in _top_level_page_files():
        src = page.read_text()
        rel = str(page.relative_to(WEB))
        is_client = bool(re.match(r"^\s*['\"]use client['\"]", src))
        does_router_redirect = bool(
            re.search(r"router\.(replace|push)\s*\(", src)
        )
        # A real surface page may use router.push for intra-surface
        # deep-link writes; the stub shape is the COMBINATION of
        # client + a router redirect inside a useEffect + a trivial body
        # (returns null or a "Redirecting" spinner with no real surface).
        uses_effect_redirect = bool(
            re.search(r"useEffect\([^)]*router\.(replace|push)", src, re.DOTALL)
        )
        if is_client and does_router_redirect and uses_effect_redirect:
            violations.append(rel)

    _assert(
        not violations,
        "No client-stub redirect pattern (use server redirect()). Violations:\n      "
        + "\n      ".join(violations)
        if violations
        else "All redirect stubs are server transport (no client-stub shape)",
    )


# =============================================================================
# Group 2 — every server redirect() target resolves to a live route
# =============================================================================


def test_server_redirect_targets_resolve() -> None:
    print("\n[2] server redirect() targets resolve to a live route")

    live = _live_route_segments()
    violations: list[str] = []

    for page in _top_level_page_files():
        src = page.read_text()
        rel = str(page.relative_to(WEB))
        # Find redirect('/target...') / redirect(`/target...`) — literal
        # string targets only. redirect(HOME_ROUTE) / redirect(CONST) are
        # constant refs resolved elsewhere; skip (the routes.ts constants
        # are guarded by the ADR-297 nav test's live-route group).
        for m in re.finditer(r"redirect\(\s*[`'\"]/([a-z][a-z0-9-]*)", src):
            seg = m.group(1)
            if seg not in live:
                violations.append(f"{rel}: redirect → /{seg} (no live route)")

    _assert(
        not violations,
        "No dead/stale server-redirect targets. Violations:\n      "
        + "\n      ".join(violations)
        if violations
        else "All literal server-redirect targets resolve to live routes",
    )


# =============================================================================
# Group 3 — the historically-broken stubs are server transport
# =============================================================================


def test_known_stubs_are_server_transport() -> None:
    print("\n[3] the converted stubs use server redirect() (not client)")

    # The 12 authenticated-interior stubs converted by ADR-308. Each must
    # NOT be 'use client' and MUST call redirect().
    converted = [
        "backend", "brand", "chat", "context", "docs", "memory",
        "operation", "orchestrator", "system", "team", "workfloor",
    ]
    for slug in converted:
        p = AUTH_DIR / slug / "page.tsx"
        if not p.is_file():
            _assert(False, f"/{slug} stub page exists")
            continue
        src = p.read_text()
        is_client = bool(re.match(r"^\s*['\"]use client['\"]", src))
        uses_server_redirect = "redirect(" in src and "next/navigation" in src
        _assert(
            (not is_client) and uses_server_redirect,
            f"/{slug} is server transport (redirect(), not 'use client')",
        )


def main() -> int:
    print("=" * 70)
    print("ADR-308 — Redirect Stubs as Pure Transport — regression guard")
    print("=" * 70)

    test_no_client_redirect_stubs()
    test_server_redirect_targets_resolve()
    test_known_stubs_are_server_transport()

    print("\n" + "=" * 70)
    print(f"  {_passed} passed, {_failed} failed")
    print("=" * 70)
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
