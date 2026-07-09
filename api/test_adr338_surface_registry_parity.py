"""ADR-338 surface audit gate — backend ↔ frontend kernel-surface parity.

The ADR-338 management-plane FE audit surfaced a class of silent drift: a
kernel surface registered in the backend (`services/kernel_surfaces.py`) but
NOT wired into the frontend's three surface sources of truth is a DEAD LINK —
it appears in the Launcher (driven by the backend/compositor surface list) but
`isKernelSurfaceSlug(slug)` returns false, so clicking it is a no-op that just
closes the Launcher.

Two real instances were found and fixed:

  - `setup` (ADR-331 D1): a fully-built page + SetupSequence renderer that the
    OS shell could never open — missing from the FE type union, allowlist, and
    registry. The reported "setup link doesn't work" bug.

  - `pace` → `budget` (ADR-327 D7/Phase 5): pace was retired and `/budget`
    became the canonical surface FE-side (page + redirect stub + registry), but
    the BACKEND surface entry was never updated and kept the stale `pace`
    slug/route. Backend now registers `budget`.

This gate locks the invariant so the drift cannot recur silently: the set of
navigable backend kernel surfaces MUST equal the FE allowlist MUST equal the FE
component registry. (The `tsc` exhaustiveness check on
`Record<KernelSurfaceSlug, ComponentType>` already couples the type union to
the registry; this gate adds the third leg — the backend — which TypeScript
cannot see.)

Usage:
    cd api
    python test_adr338_surface_registry_parity.py
"""

from __future__ import annotations

import re
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


def _backend_navigable_slugs() -> set[str]:
    """Authoritative source: import the constant, don't regex it."""
    from services.kernel_surfaces import KERNEL_SURFACES

    # Navigable = has a non-empty route AND is not `hidden`. Chrome surfaces
    # (top-bar, launcher, chat-drawer) carry route="" and are not Launcher
    # navigation targets. ADR-425 D2 (2026-07-09): `hidden` surfaces (sources)
    # keep a bookmark-safe redirect-stub route but present NO operator door — so
    # they are not a real navigation target and must not require a window
    # component or an allowlist entry.
    return {
        e["slug"]
        for e in KERNEL_SURFACES
        if e.get("route") and not e.get("hidden")
    }


def _fe_allowlist_slugs() -> set[str]:
    ts = _read("types/desk.ts")
    m = re.search(r"KERNEL_SURFACE_SLUGS.*?=\s*\[(.*?)\]\s*as const", ts, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r"'([a-z-]+)'", m.group(1)))


def _fe_registry_slugs() -> set[str]:
    reg = _read("components/shell/SurfaceRegistry.tsx")
    m = re.search(r"KERNEL_SURFACE_REGISTRY.*?=.*?\{(.*?)\n\};", reg, re.DOTALL)
    if not m:
        return set()
    # ADR-341: hyphenated slugs (workspace-settings) require a quoted key in
    # JS; match both bare (`feed:`) and quoted (`'workspace-settings':`) keys.
    return set(re.findall(r"^\s*'?([a-z-]+)'?:", m.group(1), re.MULTILINE))


def _backend_pane_slugs() -> set[str]:
    """ADR-340 P2: pane-grade surfaces — registry entries with `pane_of`."""
    from services.kernel_surfaces import kernel_pane_slugs

    return kernel_pane_slugs()


def test_three_way_parity() -> None:
    print("\n[parity] backend navigable == FE allowlist; registry = window-grade only")
    backend = _backend_navigable_slugs()
    allow = _fe_allowlist_slugs()
    reg = _fe_registry_slugs()
    panes = _backend_pane_slugs()

    check("backend navigable slugs parse non-empty", bool(backend))
    check("FE allowlist parses non-empty", bool(allow))
    check("FE registry parses non-empty", bool(reg))

    check(
        "no backend surface missing from FE allowlist (dead launcher link)",
        backend <= allow,
        f"missing FE-side: {sorted(backend - allow)}",
    )
    check(
        "no FE allowlist slug absent from backend (phantom surface)",
        allow <= backend,
        f"not in backend: {sorted(allow - backend)}",
    )
    # ADR-340 P2: pane-grade surfaces (pane_of set) deliberately have NO
    # window component — they render as sidebar panes inside their parent.
    # The FE registry must cover exactly the WINDOW-GRADE navigable set.
    check(
        "registry == window-grade navigable set (allowlist minus panes)",
        reg == allow - panes,
        f"(allow-panes)∖reg={sorted((allow - panes) - reg)} reg∖(allow-panes)={sorted(reg - (allow - panes))}",
    )
    check(
        "no pane-grade slug carries a window component",
        not (reg & panes),
        f"pane slugs with window components: {sorted(reg & panes)}",
    )
    check(
        "pane set is the live fold (ADR-426 System Agent door + ADR-425 sources hidden)",
        panes == {
            # ADR-426 (2026-07-09): budget/autonomy are pane_of system-agent now
            # (the Freddie System Agent door), NOT workspace-settings — they are
            # still pane-grade, just under a different parent. ADR-418:
            # expected-output LEFT (dormant). ADR-421: mandate/identity/principles
            # LEFT (dormant) — a workspace has no constitution of its own.
            "budget", "autonomy",
            # Workspace Settings — Operation (program). ADR-425 (2026-07-09):
            # `connectors` is now pane_of settings (the account door); `sources` is
            # HIDDEN (no pane_of, no route) so it drops out of the pane set.
            "program", "connectors",
            # Recurrence (Machinery) — ADR-340 D8
            "activity",
        },
        f"panes={sorted(panes)}",
    )


def test_setup_wired() -> None:
    print("\n[setup] ADR-331 surface reachable from the OS shell")
    check("backend registers setup", "setup" in _backend_navigable_slugs())
    check("FE allowlist includes setup", "setup" in _fe_allowlist_slugs())
    check("FE registry maps setup → SetupPage",
          "setup:" in _read("components/shell/SurfaceRegistry.tsx")
          and "SetupPage" in _read("components/shell/SurfaceRegistry.tsx"))


def test_pace_retired_budget_canonical() -> None:
    print("\n[budget] ADR-327 pace→budget reconciled backend-side")
    backend = _backend_navigable_slugs()
    check("backend registers budget", "budget" in backend)
    check("backend no longer registers retired pace surface", "pace" not in backend)
    src = _read("services/kernel_surfaces.py", root=_API_ROOT)
    check("budget surface points at /budget route", '"route": "/budget"' in src)
    check("budget surface points at _budget.yaml substrate",
          "governance/_budget.yaml" in src)


def main() -> int:
    print("=" * 70)
    print("ADR-338 surface audit — backend ↔ frontend kernel-surface parity")
    print("=" * 70)
    test_three_way_parity()
    test_setup_wired()
    test_pace_retired_budget_canonical()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
