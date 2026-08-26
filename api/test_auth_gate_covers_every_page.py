"""Every authenticated page is behind the middleware gate (2026-08-26).

WHY THIS EXISTS
`middleware.ts` derives its protected set from KERNEL_SURFACE_SLUGS, so a
surface is gated because it is a surface. That derivation is correct and stays
— but it is blind to exactly one class: a route whose slug has NO surface row.
Redirect stubs are that class, and they accumulate (a surface is deleted, its
route is kept for bookmark safety, the slug leaves the roster, and the gate
leaves with it).

ADR-592 NAMED this obligation ("the route must become a redirect stub in the
SAME change") and its own gate could not enforce it: `test_adr592_app_stage`
iterates the `internal` surfaces, and NOTHING resolves to `internal`, so the
loop body runs zero times. The obligation was stated in prose, checked by a
loop over an empty list, and 8 routes were ungated when this was written:
/budget /delegation /expected-output /identity /mandate /pace /principles
/program.

WHAT IT ASSERTS
For every directory under web/app/(authenticated) that has a page.tsx, some
prefix in (SURFACE_PREFIXES ∪ LEGACY_AND_STUB_PREFIXES) covers it. Reads the
TS sources as text — deliberately: this must hold for the file the bundler
compiles, not for a Python mirror of it that could itself drift.

Severity note: these are all redirect stubs, so the leak is a 302 to a gated
page rather than data exposure. It is still the gate saying "protected" about
routes it does not protect.

Run: python3 api/test_auth_gate_covers_every_page.py
"""
from __future__ import annotations

import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WEB = os.path.join(_REPO, "web")

_passed = 0
_failed = 0


def check(cond, msg):
    global _passed, _failed
    if cond:
        print(f"  ok   {msg}")
        _passed += 1
    else:
        print(f"  FAIL {msg}")
        _failed += 1


def _authenticated_routes() -> set[str]:
    base = os.path.join(_WEB, "app", "(authenticated)")
    out = set()
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if name.startswith("[") or not os.path.isdir(d):
            continue
        if os.path.exists(os.path.join(d, "page.tsx")):
            out.add("/" + name)
    return out


def _protected_prefixes() -> tuple[set[str], set[str]]:
    mw = open(os.path.join(_WEB, "lib", "supabase", "middleware.ts"), encoding="utf-8").read()
    block = mw.split("LEGACY_AND_STUB_PREFIXES")[1].split("];")[0]
    stubs = set(re.findall(r'"(/[a-z0-9-]+)"', block))

    desk = open(os.path.join(_WEB, "types", "desk.ts"), encoding="utf-8").read()
    arr = desk.split("KERNEL_SURFACE_SLUGS: readonly KernelSurfaceSlug[] = [")[1].split("] as const")[0]
    surfaces = {"/" + s for s in re.findall(r"'([a-z0-9-]+)'", arr)}
    return surfaces, stubs


def main() -> int:
    routes = _authenticated_routes()
    surfaces, stubs = _protected_prefixes()
    protected = surfaces | stubs

    check(len(routes) > 20, f"found {len(routes)} authenticated pages to check")
    check(len(surfaces) > 5, f"parsed {len(surfaces)} surface slugs from desk.ts")
    check(len(stubs) > 5, f"parsed {len(stubs)} stub prefixes from middleware.ts")

    uncovered = sorted(
        r for r in routes
        if not any(r == p or r.startswith(p + "/") for p in protected)
    )
    check(
        not uncovered,
        "every authenticated page is covered by a protected prefix"
        + (f" — UNGATED: {uncovered}" if uncovered else ""),
    )

    # The inverse is hygiene, not security: a prefix naming no page and no
    # next.config redirect is dead weight that makes the list harder to trust.
    nextcfg = open(os.path.join(_WEB, "next.config.js"), encoding="utf-8").read()
    unauth_pages = {
        "/" + n for n in os.listdir(os.path.join(_WEB, "app"))
        if os.path.isdir(os.path.join(_WEB, "app", n)) and not n.startswith(("(", "["))
    }
    dangling = sorted(
        p for p in stubs
        if p not in routes
        and p not in unauth_pages
        and f"'{p}'" not in nextcfg
        and p != "/desktop"
    )
    check(
        not dangling,
        "no stub prefix names a route that does not exist"
        + (f" — DANGLING: {dangling}" if dangling else ""),
    )

    print()
    print("=" * 62)
    print(f"auth-gate coverage: {_passed} passed, {_failed} failed")
    print("=" * 62)
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
