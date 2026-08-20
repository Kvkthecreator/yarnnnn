"""Regression guard — the auth gate covers EVERY live surface.

Operator-observed (KVK 2026-08-20): surfaces "glitched" on load — the page
appeared, then bounced to login.

ROOT CAUSE: `PROTECTED_PREFIXES` in web/lib/supabase/middleware.ts was a
HAND-KEPT list, while the surface roster it was supposed to mirror
(kernel_surfaces.py / KERNEL_SURFACE_SLUGS) kept growing. Eight live
authenticated surfaces were missing and served a full 200 to logged-out
visitors — probed against production 2026-08-20:

    /images /radar /strings /text /notifications /queue /billing /usage

No data leaked: AuthenticatedLayout's `onAuthStateChange` listener caught it
client-side. But that listener's OWN docblock says it is "live invalidation,
NOT an auth gate", and it fires only after the ~45KB shell has mounted and
painted — so the operator saw the surface flash, then bounce. Meanwhile
`(authenticated)/layout.tsx` states "middleware.ts (updateSession) is the SOLE
gate", which was true by intent and false for those eight.

THE INVARIANT: every navigable surface route is gated server-side, BY
CONSTRUCTION. The middleware now derives its protected set from
KERNEL_SURFACE_SLUGS rather than a list someone must remember to append to.

This gate checks the BE roster (the source of truth) against the FE derivation,
so a surface added on either side that escapes the gate fails here — the drift
that caused this bug, caught at its origin rather than at the eighth instance.

Run: cd api && python3 test_auth_gate_covers_every_surface.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB = REPO_ROOT / "web"
MIDDLEWARE = WEB / "lib" / "supabase" / "middleware.ts"
DESK = WEB / "types" / "desk.ts"
LAYOUT = WEB / "app" / "(authenticated)" / "layout.tsx"

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


def _fe_slugs() -> set[str]:
    """Parse KERNEL_SURFACE_SLUGS out of types/desk.ts (comments stripped —
    the array is comment-heavy and a quoted slug inside a comment is not a
    member; a gate that counted those would be reading its own prose)."""
    src = DESK.read_text()
    # Split at the ARRAY's opening bracket, not the `]` inside the type
    # annotation `readonly KernelSurfaceSlug[]` — splitting on a bare "]"
    # stopped at the annotation and returned an empty body, which read as
    # "every slug is missing". The literal starts at the `[` after `=`.
    tail = src.split("KERNEL_SURFACE_SLUGS", 1)[1]
    body = tail.split("=", 1)[1].split("[", 1)[1].split("]", 1)[0]
    body = re.sub(r"//[^\n]*", "", body)
    return set(re.findall(r"'([a-z0-9-]+)'", body))


def _resolved_protected_prefixes() -> set[str]:
    """Compute the prefix set the middleware ACTUALLY gates on.

    Not "is the slug in types/desk.ts" — that question passes even when the
    middleware ignores the roster entirely (the pre-fix state). This resolves
    both halves of the union the way the module does:

      SURFACE_PREFIXES        — derived, iff the map over the roster is present
      LEGACY_AND_STUB_PREFIXES — the string literals still hand-kept

    so removing the derivation makes this set shrink and the coverage checks
    fail, which is the falsification this gate is built to survive.
    """
    src = MIDDLEWARE.read_text()
    prefixes: set[str] = set()

    # The derived half — only if the roster is genuinely mapped into it.
    if re.search(
        r"const SURFACE_PREFIXES\s*=\s*KERNEL_SURFACE_SLUGS\.map\(", src
    ):
        prefixes |= {f"/{slug}" for slug in _fe_slugs()}

    # The hand-kept half — string literals inside the legacy array, comments
    # stripped so a route mentioned only in prose is not counted as gated.
    m = re.search(
        r"const LEGACY_AND_STUB_PREFIXES = \[(.*?)^\];", src, re.S | re.M
    )
    if m:
        body = re.sub(r"//[^\n]*", "", m.group(1))
        prefixes |= set(re.findall(r'"(/[a-z0-9-]+)"', body))

    return prefixes


def test_middleware_derives_rather_than_lists() -> None:
    print("\n[1] the protected set is DERIVED, not hand-kept")

    src = MIDDLEWARE.read_text()
    _assert(
        "KERNEL_SURFACE_SLUGS" in src,
        "middleware imports the surface roster (KERNEL_SURFACE_SLUGS)",
    )
    _assert(
        "KERNEL_SURFACE_SLUGS.map(" in src,
        "the surface prefixes are MAPPED from the roster, not retyped",
    )
    # The gate must read the union, not one half of it.
    _assert(
        re.search(r"const PROTECTED_PREFIXES = Array\.from\(\s*new Set\(", src)
        is not None,
        "PROTECTED_PREFIXES = derived ∪ legacy/stub, deduped",
    )
    _assert(
        "PROTECTED_PREFIXES.some((prefix) => path.startsWith(prefix))" in src,
        "the gate still reads PROTECTED_PREFIXES (the union) for its decision",
    )


def test_every_roster_surface_is_gated() -> None:
    """The invariant, executed against the BE roster (the source of truth)."""
    print("\n[2] every navigable surface route is gated server-side")

    from services.kernel_surfaces import KERNEL_SURFACES  # noqa: E402

    # RESOLVE the prefix set the middleware actually computes, rather than
    # asking the FE roster whether a slug exists. Those are different
    # questions: the slug can be present in types/desk.ts while the middleware
    # never derives from it — which is precisely the pre-fix state, and a
    # check that reads the roster would have passed all through the outage.
    protected = _resolved_protected_prefixes()
    _assert(
        len(protected) > 20,
        f"the resolved protected set is populated ({len(protected)} prefixes)",
    )

    navigable = [s for s in KERNEL_SURFACES if s.get("route")]
    _assert(len(navigable) > 10, f"roster has real navigable rows ({len(navigable)})")

    ungated = [
        f"{s['slug']} ({s['route']})"
        for s in navigable
        if not any(str(s["route"]).startswith(p) for p in protected)
    ]
    _assert(
        not ungated,
        "every navigable roster surface is covered by the gate. "
        f"UNGATED: {ungated or 'none'}",
    )

    # The eight this bug was about, named explicitly so a regression that
    # re-drops any of them says WHICH — the class recurred eight times before
    # anyone noticed, so the gate names them rather than counting.
    for slug in [
        "images", "radar", "strings", "text",
        "notifications", "queue", "billing", "usage",
    ]:
        _assert(
            any(f"/{slug}".startswith(p) for p in protected),
            f"'{slug}' — served 200 to logged-out visitors in production "
            f"2026-08-20 — is gated by the resolved prefix set",
        )


def test_the_sole_gate_claim_is_true() -> None:
    """The layout docblock asserts middleware is the SOLE gate. Either that is
    true, or the claim must go. It is now true — check the client listener has
    not quietly become the gate again."""
    print("\n[3] 'middleware is the SOLE gate' is a true claim")

    layout = LAYOUT.read_text()
    _assert(
        "SOLE gate" in layout,
        "the layout still claims middleware is the sole gate (the contract)",
    )

    shell = (WEB / "components" / "shell" / "AuthenticatedLayout.tsx").read_text()
    # The listener stays (live sign-out invalidation is legitimate) but it must
    # remain a LISTENER — no getUser()-based blocking gate reintroduced, which
    # would paper over an ungated route instead of exposing it.
    _assert(
        "onAuthStateChange" in shell,
        "the sign-out listener survives (live invalidation, legitimately)",
    )
    _assert(
        "await supabase.auth.getUser()" not in shell,
        "no blocking client-side getUser() gate reintroduced in the shell — "
        "an ungated route must surface as a bug, not be hidden by a spinner",
    )


if __name__ == "__main__":
    print("auth gate covers every surface — the 8-route drift of 2026-08-20")
    test_middleware_derives_rather_than_lists()
    test_every_roster_surface_is_gated()
    test_the_sole_gate_claim_is_true()

    print(f"\n{'='*60}")
    print(f"auth-gate coverage gate: {_passed} passed, {_failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if _failed == 0 else 1)
