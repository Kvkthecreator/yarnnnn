"""ADR-340 P3 gate — launcher re-sort: act-derived tiers, flat search.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies
the launcher's at-rest IA derives from the operator's standing loop
(launcher_tier on the kernel registry), search stays flat across every
navigable surface (D5), and the constitution band is the door to the three
constitution mirrors.

Usage:
    cd api
    python test_adr340_p3_launcher.py
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


def test_registry_tiers() -> None:
    print("\n[registry] launcher_tier on every navigable kernel surface")
    from services.kernel_surfaces import KERNEL_SURFACES

    navigable = [e for e in KERNEL_SURFACES if e.get("route")]
    tiers = {e["slug"]: e.get("launcher_tier") for e in navigable}

    check("every navigable surface declares a tier", all(tiers.values()), str({k: v for k, v in tiers.items() if not v}))
    check(
        # ADR-346: primary == the standing-loop COMPOSITIONS. Operation joins
        # Home as the second composition (Decide·Read·Tune); Feed + Queue
        # demote to utilities — Operation fronts them.
        "primary == the standing-loop compositions (home/operation/files)",
        {s for s, t in tiers.items() if t == "primary"} == {"home", "operation", "files"},
    )
    # ADR-347: the two-door split (ADR-341) is reversed — ONE Settings door
    # (the operation's settings) in the `configure` tier; the account window
    # (`settings` slug) is search-only (UserMenu-reached). The
    # workspace-config + system-config tier pair is retired.
    check(
        "configure == {workspace-settings} (the one Settings door)",
        {s for s, t in tiers.items() if t == "configure"} == {"workspace-settings"},
    )
    check("legacy workspace-config + system-config tiers retired",
          not any(t in ("workspace-config", "system-config", "system") for t in tiers.values()))
    check(
        # ADR-346: feed + queue join utilities (demoted from primary —
        # Operation fronts them; they stay complete + reachable mirrors).
        "utilities == setup/recurrence/agents/feed/queue (ADR-346 demotes feed+queue; activity is a recurrence pane per ADR-340 D8)",
        {s for s, t in tiers.items() if t == "utilities"}
        == {"setup", "recurrence", "agents", "feed", "queue"},
    )
    check(
        # ADR-347: the account window (`settings`) joins search-only
        # (UserMenu-reached, not a door); expected-output (ADR-348) joins as
        # a Contract pane.
        "search-only == constitution mirrors + Settings panes + account window + activity",
        {s for s, t in tiers.items() if t == "search-only"}
        == {"mandate", "principles", "identity", "budget", "autonomy", "expected-output",
            "program", "connectors", "sources", "settings", "activity"},
    )
    chrome = [e for e in KERNEL_SURFACES if not e.get("route")]
    check("chrome entries carry no tier", all(not e.get("launcher_tier") for e in chrome))


def test_launcher_two_modes() -> None:
    print("\n[launcher] act-tier groups at rest; flat when searching")
    src = _read("components/shell/Launcher.tsx")
    # ADR-347: at-rest groups are Workspace / Settings / Utilities (the
    # two-door split is reversed — one Settings door; account → UserMenu).
    check("KERNEL_TIER_GROUPS declared (Workspace/Settings/Utilities)",
          "'Workspace'" in src and "'Settings'" in src
          and "'Utilities'" in src and "KERNEL_TIER_GROUPS" in src)
    check("search-only hidden at rest", "search-only" in src and "return null" in src)
    check("flat list when searching (Spotlight role)", "isSearching" in src)
    check("pane rows labeled as Settings panes in search", "Settings pane" in src)
    check("register grouping deleted (superseded)", "KERNEL_REGISTER_GROUPS" not in src)
    check("Surface type declares launcher_tier", "launcher_tier?:" in _read("lib/compositor/types.ts"))


def test_constitution_band_door() -> None:
    print("\n[band] Home constitution band routes to the three mirrors")
    src = _read("components/library/HomeHeader.tsx")
    check("ConstitutionLinks component present", "ConstitutionLinks" in src)
    for slug in ("mandate", "principles", "identity"):
        check(f"band links to {slug}", f"slug: '{slug}'" in src)
    check("links open via foregroundSurface", "foregroundSurface(item.slug)" in src)
    check("autonomy badge points at the Contract pane (ADR-347)", "/workspace-settings?pane=autonomy" in src)


def main() -> int:
    print("ADR-340 P3 gate — launcher re-sort")
    test_registry_tiers()
    test_launcher_two_modes()
    test_constitution_band_door()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
