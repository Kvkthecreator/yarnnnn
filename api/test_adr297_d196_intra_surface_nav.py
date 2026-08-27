"""ADR-297 D19.6 gate — intra-surface deep-link updates preserve the pathname baseline.

Operator-observed (KVK 2026-06-12): a surface running as a window on the Desktop
(pathname /desktop) wrote its deep-link param via router.push/replace('/{slug}?param=X'),
which flipped pathname → /{slug} and disrupted the launcher/topbar (tripped the
pathname→foreground effect + SurfaceViewport pathnameSlug resolution + closeSurface
URL-sync, all of which branch on the /desktop baseline).

D19.6 adds the third navigation verb — `setSurfaceParams(params)` — which updates the
foregrounded surface's URL params under the CURRENT pathname via history.replaceState
(no pathname flip, no navigation event; Next 14.2 syncs useSearchParams). Surfaces keep
reading useSearchParams() as their single source of truth.

This gate locks:
  - the verb exists in the window manager (interface + impl + context wiring),
  - the impl uses history.replaceState (NOT router.push) and preserves pathname,
  - Agents/Recurrence/Activity migrated their intra-surface writes to setSurfaceParams,
  - those three surfaces no longer import useRouter for intra-surface param writes,
  - Files stays off the URL entirely (no setSurfaceParams, no router param-write).

Source-assertion gate (the behavior is FE; same Python-over-source pattern as ADR-237/238).

Usage:
    cd api
    python test_adr297_d196_intra_surface_nav.py
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


def _read(rel: str) -> str:
    p = _WEB / rel
    return p.read_text() if p.exists() else ""


def test_verb_exists() -> None:
    print("\n[verb] setSurfaceParams in the window manager")
    src = _read("lib/shell/useSurfacePreferences.tsx")
    check("setSurfaceParams declared in the interface", "setSurfaceParams: (params:" in src)
    check("setSurfaceParams implemented", "const setSurfaceParams = useCallback(" in src)
    check("impl uses history.replaceState (no pathname flip)",
          "window.history.replaceState(" in src)
    check("impl preserves current pathname (url.pathname)", "url.pathname" in src)
    check("impl does NOT router.push inside setSurfaceParams",
          "router.push" not in src.split("const setSurfaceParams")[1].split("const ")[1]
          if "const setSurfaceParams" in src else False)
    check("impl guards server (typeof window)",
          "typeof window === 'undefined'" in src.split("const setSurfaceParams")[1]
          if "const setSurfaceParams" in src else False)
    check("setSurfaceParams wired into context value",
          src.count("setSurfaceParams,") >= 2)  # value object + deps array


def test_agents_migrated() -> None:
    # ADR-358 D6: intra-surface params are window-NAMESPACED. The Agents
    # window reads/writes its own `agents.agent` via useSurfaceParam('agents')
    # — p.get/p.set — which wraps setSurfaceParams under the hood.
    print("\n[agents] intra-surface agent= via useSurfaceParam('agents')")
    src = _read("app/(authenticated)/agents/page.tsx")
    check("uses useSurfaceParam('agents')", "useSurfaceParam('agents')" in src)
    check("writes namespaced agent via p.set({ agent: ... })", "p.set({ agent:" in src)
    check("no router.push('/agents?agent= write", "router.push(`/agents?agent=" not in src
          and "router.push('/agents?agent=" not in src)
    check("no useRouter import (intra-surface only)", "useRouter" not in src)


def test_recurrence_migrated() -> None:
    # ADR-358 D6: the Recurrence window reads/writes its own task/agent/pane/
    # slug via useSurfaceParam('recurrence') — p.get/p.set.
    print("\n[recurrence] intra-surface task/agent via useSurfaceParam('recurrence')")
    src = _read("app/(authenticated)/recurrence/page.tsx")
    check("uses useSurfaceParam('recurrence')", "useSurfaceParam('recurrence')" in src)
    check("select writes namespaced task via p.set({ task: slug })", "p.set({ task: slug })" in src)
    check("back-to-list deletes task (null)", "p.set({ task: null })" in src)
    check("clear-agent deletes agent (null)", "p.set({ agent: null })" in src)
    check("no router.push('/recurrence? write", "router.push(`/recurrence?" not in src)
    check("no router.replace('/recurrence write", "router.replace(" not in src)
    check("no useRouter import", "useRouter" not in src)


def test_activity_migrated() -> None:
    # ADR-340 D8 (2026-06-18): Activity folded to pane-grade under Recurrence —
    # the Runs lens. The /activity page is now an ADR-308 server redirect stub
    # (no intra-surface nav of its own); the slug clear moved into the
    # Recurrence window, where the Runs lens owns it.
    # ADR-358 D6: stub + writes use the window-NAMESPACED recurrence params.
    print("\n[activity] folded to the Recurrence Runs lens (ADR-340 D8)")
    stub = _read("app/(authenticated)/activity/page.tsx")
    check("/activity is a redirect stub → /recurrence?recurrence.pane=activity",
          "/recurrence?recurrence.pane=activity" in stub)
    check("/activity stub is server transport (no 'use client')", "'use client'" not in stub)
    # The intra-surface slug clear now lives in the Recurrence window's Runs
    # lens (the host owns the filter param; ActivityLog is host-driven).
    rec = _read("app/(authenticated)/recurrence/page.tsx")
    check("Runs lens clear writes namespaced slug via p.set({ slug: null })", "p.set({ slug: null })" in rec)
    check("Recurrence uses useSurfaceParam('recurrence')", "useSurfaceParam('recurrence')" in rec)


def test_files_off_url() -> None:
    print("\n[files] the OPEN location is addressable; SELECTION is not")
    src = _read("app/(authenticated)/files/page.tsx")
    # THE INVARIANT IS THE PATHNAME, NOT THE WRITE (re-cut 2026-08-27).
    #
    # This block used to assert `setSurfaceParams not in src` — banning the
    # whole mechanism. That over-shot: the operator-observed 2026-06-12 bug was
    # a PATHNAME FLIP off /desktop, and D19.6 (filed the same day, same report)
    # repairs it by writing the query through history.replaceState with the
    # pathname held verbatim. Banning the repair alongside the bug is why Files
    # could not remember where you stood for two months: browse into a folder,
    # refresh, and you were back at the default view, with nothing in the
    # address bar to copy. Settings has written its own params this way
    # throughout, with no shell breakage.
    #
    # So the ban is replaced by the real thing it was standing in for.
    check("no router.replace('/files?path= write", "router.replace(`/files?path=" not in src)
    check("no router.push('/files? write (the pathname flip IS the bug)",
          "router.push(`/files?" not in src)
    check("no useRouter import (the surface never navigates itself)", "useRouter" not in src)
    # The param is written through the namespaced hook, whose setter is
    # setSurfaceParams → replaceState. Asserted POSITIVELY: the location must
    # actually be addressable, so a silent revert to a drained one-shot param
    # fails here rather than passing by absence.
    check("the open location IS written to the URL (fp.set via useSurfaceParam)",
          "fpRef.current.set({ path" in src)
    check("and RETRACTED when the surface leaves it (leavePath)",
          "fpRef.current.set({ path: null" in src)
    # The drain is what made a refresh lose your place; its return would be the
    # regression. The arrival effect guards re-entry by comparing against where
    # we already stand instead.
    check("the arrival param is NOT drained after use",
          "fp.set({ path: null, domain: null });" not in src)
    check("re-entry is guarded by an already-there check, not a drain",
          "viewPathRef.current" in src)
    # Repointed 2026-07-07: the cold-load seed read moved to the namespaced
    # surface-param hook (useSurfaceParam('files').get('path')) — the D6
    # namespacing this gate's sibling requires; the raw searchParams read
    # is gone by design.
    check(
        "cold-load pathParam read preserved",
        "useSurfaceParam('files')" in src and ".get('path')" in src,
    )


def main() -> int:
    print("=" * 70)
    print("ADR-297 D19.6 — intra-surface deep-link nav (pathname baseline preserved)")
    print("=" * 70)
    test_verb_exists()
    test_agents_migrated()
    test_recurrence_migrated()
    test_activity_migrated()
    test_files_off_url()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
