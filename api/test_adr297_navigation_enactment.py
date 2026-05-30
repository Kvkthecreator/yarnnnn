"""Regression guard — ADR-297 navigation enactment (D19.5).

Permanent enforcement of the navigation layer boundary established by the
ADR-297 navigation-enactment plan (docs/design/ADR-297-NAVIGATION-ENACTMENT-PLAN.md):

  The compositor (window manager) owns navigation. The browser router is
  transport, not control. Cross-surface navigation flows through
  `navigateToSurface()` (useSurfacePreferences) — NOT through
  `router.push('/{kernel-surface-slug}')`.

Two banned classes:

  1. Reintroducing the deleted legacy Supervisor Desk system. `DeskContext`,
     `useDesk`, `DeskProvider`, and the dead desk types
     (`DeskState`/`DeskAction`/`AttentionItem`/`surfaceToParams`/
     `paramsToSurface`) were deleted in Phase 3. There is one window
     manager: `useSurfacePreferences`. (The `DeskSurface` *type* and
     `mapToolActionToSurface` survive as the TP-handoff payload + producer
     — they are NOT banned.)

  2. Cross-surface `router.push`/`replace` to a bare kernel-surface route
     (no query string) from outside the allowlist. Bare cross-surface
     navigation is the page-replacement gesture that breaks the window
     metaphor; it must go through `navigateToSurface`. Two legitimate
     exceptions are allowlisted:
       (a) redirect-stub route files — a legacy `(authenticated)/{x}/page.tsx`
           whose whole job is to redirect on mount (transport, not nav).
       (b) intra-surface query-param writes — `router.replace('/feed?...')`,
           `router.push('/agents?agent=X', {scroll:false})` — these write
           the surface's OWN deep-link state and carry a query string.

Why a query string is the discriminator: a `router.push('/cadence?task=X')`
is a window's internal deep-link state (Figma's `?node-id=`); a bare
`router.push('/cadence')` is a viewport-replace navigation that should be
`navigateToSurface('cadence')`. The presence of `?` distinguishes them.

Scope: web/ live code (app + components + lib + hooks + contexts).
Excludes: node_modules, .next, the navigateToSurface implementation itself,
and the allowlisted redirect-stub files.

Run: cd api && python test_adr297_navigation_enactment.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"

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


def _grep(pattern: str, *paths: str) -> list[str]:
    """grep -rnE over web/ live code, excluding build/vendor dirs.

    Returns matching "path:line:content" strings (empty list on no match)."""
    cmd = [
        "grep", "-rnE", pattern,
        "--include=*.tsx", "--include=*.ts",
        "--exclude-dir=node_modules", "--exclude-dir=.next",
        *[str(WEB / p) for p in paths],
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    # grep exit 1 = no matches (fine); exit >1 = real error
    if res.returncode > 1:
        raise RuntimeError(f"grep failed: {res.stderr}")
    return [ln for ln in res.stdout.splitlines() if ln.strip()]


# =============================================================================
# Group 1 — legacy Supervisor Desk system stays deleted
# =============================================================================

# Kernel-surface slugs the cross-surface ban applies to. Kept in sync with
# api/services/kernel_surfaces.py KERNEL_SURFACES (content surfaces with a
# real route) + the legacy/stub routes that resolve to a surface.
KERNEL_SLUGS = [
    "feed", "cadence", "mandate", "cockpit", "delegation", "autonomy",
    "principles", "identity", "brand", "queue", "activity", "program",
    "pace", "agents", "context", "files", "settings", "connectors",
    "desktop",
]


def test_legacy_desk_system_deleted() -> None:
    print("\n[1] legacy Supervisor Desk system stays deleted")

    # DeskContext.tsx file must not exist.
    _assert(
        not (WEB / "contexts" / "DeskContext.tsx").exists(),
        "web/contexts/DeskContext.tsx is deleted",
    )
    _assert(
        not (WEB / "hooks" / "useActiveDomain.ts").exists(),
        "web/hooks/useActiveDomain.ts (dead ADR-034 hook) is deleted",
    )

    # No live import of the deleted provider/hook.
    hits = _grep(
        r"(useDesk\b|DeskProvider|from ['\"]@/contexts/DeskContext['\"])",
        "app", "components", "lib", "hooks", "contexts",
    )
    # Doc-comment mentions are fine; only real code refs fail. A real ref
    # has the token NOT preceded by `* ` or `// ` on that line.
    code_hits = [h for h in hits if not re.search(r":\s*(\*|//)", h)]
    _assert(
        not code_hits,
        f"No live useDesk/DeskProvider/DeskContext-import refs "
        f"(found: {code_hits or 'none'})",
    )

    # The dead desk types stay removed from types/desk.ts.
    desk_types = (WEB / "types" / "desk.ts").read_text()
    for dead in ("export interface DeskState", "export type DeskAction",
                 "export interface AttentionItem", "export function surfaceToParams",
                 "export function paramsToSurface"):
        _assert(
            dead not in desk_types,
            f"types/desk.ts no longer exports '{dead.split()[-1]}'",
        )
    # The live handoff payload + producer survive.
    _assert(
        "export type DeskSurface" in desk_types,
        "types/desk.ts still exports DeskSurface (TP-handoff payload — not banned)",
    )
    _assert(
        "export function mapToolActionToSurface" in desk_types,
        "types/desk.ts still exports mapToolActionToSurface (handoff producer)",
    )


# =============================================================================
# Group 2 — the navigation primitive exists + is the single verb
# =============================================================================


def test_navigation_primitive_exists() -> None:
    print("\n[2] navigateToSurface primitive is the single cross-surface verb")

    hook = (WEB / "lib" / "shell" / "useSurfacePreferences.tsx").read_text()
    _assert(
        "navigateToSurface" in hook,
        "useSurfacePreferences declares navigateToSurface",
    )
    # The primitive must be exposed on the interface (callers can use it).
    _assert(
        re.search(r"navigateToSurface\s*:\s*\(", hook) is not None,
        "navigateToSurface is on the SurfacePreferences interface",
    )


# =============================================================================
# Group 3 — no bare cross-surface router.push to a kernel-surface route
# =============================================================================

# Allowlist: redirect-stub route files whose entire job is to redirect on
# mount (legitimate transport, not navigation). Phase 5 may delete some;
# until then, their single redirect is permitted.
ALLOWLIST_REDIRECT_STUBS = {
    "app/(authenticated)/operation/page.tsx",
    "app/(authenticated)/brand/page.tsx",
    "app/(authenticated)/memory/page.tsx",
    "app/(authenticated)/backend/page.tsx",
    "app/(authenticated)/docs/page.tsx",
    "app/(authenticated)/system/page.tsx",
    "app/(authenticated)/chat/page.tsx",
    "app/(authenticated)/workfloor/page.tsx",
    "app/(authenticated)/orchestrator/page.tsx",
    "app/(authenticated)/overview/page.tsx",
    "app/(authenticated)/team/page.tsx",
}


def _owning_surface_slug(rel_path: str) -> str | None:
    """The kernel-surface slug a route file 'owns', if it is one.

    `app/(authenticated)/agents/page.tsx` → 'agents'
    `app/(authenticated)/agents/[id]/page.tsx` → 'agents'
    Returns None for non-route files (components, lib)."""
    m = re.search(r"app/\(authenticated\)/([^/]+)/", rel_path)
    return m.group(1) if m else None


# Files that legitimately bare-route to a surface as part of owning the
# window-manager transport contract, OR write their own surface's bare
# state (filter-clear). These are NOT cross-surface navigation.
ALLOWLIST_TRANSPORT = {
    # The window manager itself owns URL-as-transport (doCloseSurface →
    # /desktop sync). This is the implementation of the contract, not a
    # violation of it.
    "lib/shell/useSurfacePreferences.tsx",
    # FeedFilterBar.clearAll() resets the Feed surface's OWN filter params
    # to bare /feed — intra-surface state reset, same surface.
    "components/feed-surface/FeedFilterBar.tsx",
}


def test_no_bare_cross_surface_router_push() -> None:
    print("\n[3] no bare cross-surface router.push to a kernel-surface route")

    slug_alt = "|".join(KERNEL_SLUGS)
    # BARE = route slug immediately followed by a closing quote (no `?`).
    # i.e. router.push('/cadence')  — banned (cross-surface viewport-replace).
    #      router.push('/cadence?task=x') — allowed (query = intra-surface state).
    bare_pattern = (
        rf"router\.(push|replace)\(\s*[`'\"]/(?:{slug_alt})[`'\"]"
    )
    hits = _grep(bare_pattern, "app", "components", "lib", "hooks", "contexts")

    violations = []
    for h in hits:
        # h = "<abs path>:<line>:<content>"
        abs_path = h.split(":", 1)[0]
        rel = str(Path(abs_path).relative_to(WEB))
        content = h.split(":", 2)[-1].strip()

        if rel in ALLOWLIST_REDIRECT_STUBS:
            continue
        if rel in ALLOWLIST_TRANSPORT:
            continue

        # A route file bare-redirecting to ITS OWN surface is intra-surface
        # (e.g. /agents/[id] → /agents), not cross-surface navigation.
        owns = _owning_surface_slug(rel)
        target = re.search(r"[`'\"]/([a-z-]+)[`'\"]", content)
        if owns and target and target.group(1) == owns:
            continue

        violations.append(f"{rel}: {content}")

    _assert(
        not violations,
        "No bare cross-surface router.push to kernel routes outside the "
        "redirect-stub allowlist (use navigateToSurface). Violations:\n      "
        + "\n      ".join(violations)
        if violations
        else "No bare cross-surface router.push to kernel routes (clean)",
    )


# =============================================================================
# Group 4 — every internal nav target resolves to a live route
# =============================================================================

# Non-directory routes that are legitimate destinations but have no
# `app/{seg}/` dir of their own (or are intentionally not page-backed).
# These are NOT dead — they're allowlisted live destinations.
ALLOWLIST_LIVE_NON_DIR = {
    # Next.js special / static public files served without a route dir.
    "llms.txt", "sitemap.xml", "robots.txt",
}


def _live_route_segments() -> set[str]:
    """First path-segments of every live Next.js route under web/app.

    A target `/{seg}` or `/{seg}/...` is live iff `app/(authenticated)/{seg}/`
    or `app/{seg}/` exists (the dir holds page.tsx + any dynamic [id] subroute).
    """
    app = WEB / "app"
    live: set[str] = set(ALLOWLIST_LIVE_NON_DIR)
    auth = app / "(authenticated)"
    if auth.is_dir():
        live |= {p.name for p in auth.iterdir() if p.is_dir()}
    for p in app.iterdir():
        if p.is_dir() and p.name not in ("(authenticated)", "api"):
            live.add(p.name)
    return live


# Patterns that capture an internal route target's first segment.
_TARGET_PATTERNS = [
    re.compile(
        r"""(?:router\.(?:push|replace)|redirect)\(\s*[`'"](/[a-z][a-z0-9-]*)"""
    ),
    re.compile(r"""href=\{?[`'"](/[a-z][a-z0-9-]*)"""),
]


def test_no_dead_nav_targets() -> None:
    print("\n[4] every internal nav target resolves to a live route")

    live = _live_route_segments()
    dead: dict[str, list[str]] = {}

    for path in WEB.rglob("*"):
        if path.suffix not in (".tsx", ".ts"):
            continue
        if "node_modules" in path.parts or ".next" in path.parts:
            continue
        try:
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                s = line.strip()
                if s.startswith("//") or s.startswith("*"):
                    continue
                for pat in _TARGET_PATTERNS:
                    for m in pat.finditer(line):
                        seg = m.group(1).split("/")[1]
                        if seg not in live:
                            rel = str(path.relative_to(WEB))
                            dead.setdefault(seg, []).append(f"{rel}:{i}")
        except (OSError, UnicodeDecodeError):
            continue

    detail = ""
    if dead:
        detail = " Dead targets:\n      " + "\n      ".join(
            f"/{seg} ({len(locs)}): {locs[0]}"
            + (f" +{len(locs)-1} more" if len(locs) > 1 else "")
            for seg, locs in sorted(dead.items())
        )
    _assert(
        not dead,
        "Every internal nav target resolves to a live route dir "
        "(no dead /work, /files, /tasks, etc.)." + detail
        if dead
        else "Every internal nav target resolves to a live route (clean)",
    )


# =============================================================================
# Group 5 — FE ↔ BE kernel-surface slug sync (the navigable contract)
# =============================================================================
#
# The navigable kernel surfaces are declared in THREE places that must agree:
#   1. BE: api/services/kernel_surfaces.py — KERNEL_SURFACES with route != "".
#   2. FE: web/types/desk.ts — the `KernelSurfaceSlug` TYPE UNION.
#   3. FE: web/types/desk.ts — the `KERNEL_SURFACE_SLUGS` RUNTIME ARRAY
#          (what isKernelSurfaceSlug() checks; drives the pathname watcher).
#
# Chrome surfaces (route == "" — top-bar/launcher/chat-drawer) are
# deliberately excluded from the FE navigable union: they have no route and
# never foreground via deep-link. They live in ChromeRegistry, not here.
#
# These are hand-maintained string lists across a Python↔TS boundary the
# type-checker cannot span. Without this guard, adding a 17th content
# surface to the backend silently leaves the FE union short — the new
# route's deep-link would be rejected by isKernelSurfaceSlug() and the
# surface would not foreground on cold-load. No compile error, no other
# test failure. This guard makes the boundary self-enforcing: the moment
# the three sets diverge, CI fails with the exact slug delta.
#
# Design note (why a guard, not codegen): at ~16 slugs the drift-elimination
# of build-time codegen isn't worth its maintenance surface (a generated
# file + a "did you regenerate?" failure mode). isKernelSurfaceSlug also
# runs synchronously in the cold-load pathname watcher, so a runtime API
# fetch is the wrong shape. A set-equality guard gives ~95% of the safety
# at ~10% of the cost and matches the dead-target guard's philosophy:
# catch the class, not the instance.


def _be_navigable_slugs() -> set[str]:
    """Backend navigable kernel surfaces (kernel_surfaces.py, route != '')."""
    sys.path.insert(0, str(REPO_ROOT / "api"))
    from services.kernel_surfaces import KERNEL_SURFACES

    return {s["slug"] for s in KERNEL_SURFACES if s.get("route")}


def _fe_slug_union() -> set[str]:
    """FE `KernelSurfaceSlug` type union members from types/desk.ts."""
    src = (WEB / "types" / "desk.ts").read_text()
    m = re.search(
        r"export type KernelSurfaceSlug\s*=\s*(.*?);", src, re.DOTALL
    )
    return set(re.findall(r"'([a-z][a-z0-9-]*)'", m.group(1))) if m else set()


def _fe_slug_array() -> set[str]:
    """FE `KERNEL_SURFACE_SLUGS` runtime array from types/desk.ts."""
    src = (WEB / "types" / "desk.ts").read_text()
    m = re.search(
        r"export const KERNEL_SURFACE_SLUGS[^=]*=\s*\[(.*?)\]", src, re.DOTALL
    )
    return set(re.findall(r"'([a-z][a-z0-9-]*)'", m.group(1))) if m else set()


def test_fe_be_slug_sync() -> None:
    print("\n[5] FE ↔ BE kernel-surface slug sync (navigable contract)")

    be = _be_navigable_slugs()
    fe_union = _fe_slug_union()
    fe_array = _fe_slug_array()

    _assert(be != set(), "BE navigable kernel slugs parsed (non-empty)")
    _assert(fe_union != set(), "FE KernelSurfaceSlug union parsed (non-empty)")
    _assert(fe_array != set(), "FE KERNEL_SURFACE_SLUGS array parsed (non-empty)")

    # The load-bearing assertion: all three agree.
    def _delta(a: set[str], b: set[str]) -> str:
        only_a = sorted(a - b)
        only_b = sorted(b - a)
        return f"(BE-only: {only_a or 'none'} | FE-only: {only_b or 'none'})"

    _assert(
        be == fe_union,
        f"BE navigable set == FE KernelSurfaceSlug union {_delta(be, fe_union)}",
    )
    _assert(
        be == fe_array,
        f"BE navigable set == FE KERNEL_SURFACE_SLUGS array {_delta(be, fe_array)}",
    )
    _assert(
        fe_union == fe_array,
        f"FE union == FE array (self-consistency) "
        f"{_delta(fe_union, fe_array)}",
    )


# =============================================================================
# Run
# =============================================================================

if __name__ == "__main__":
    test_legacy_desk_system_deleted()
    test_navigation_primitive_exists()
    test_no_bare_cross_surface_router_push()
    test_no_dead_nav_targets()
    test_fe_be_slug_sync()
    test_no_dead_nav_targets()

    print(f"\n{'='*60}")
    print(
        f"ADR-297 navigation-enactment regression gate: "
        f"{_passed} passed, {_failed} failed"
    )
    print(f"{'='*60}")
    sys.exit(0 if _failed == 0 else 1)
