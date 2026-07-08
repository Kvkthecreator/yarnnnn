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
        # ADR-349 D1/D3: primary == the standing loop — Home + Files + Agents
        # (the judgment seat upgraded to first-class).
        # ADR-370 (2026-06-25): the boundary composition joins the primary tier,
        # inheriting the slot the Feed vacated. ADR-385 (2026-06-29): renamed
        # `context` → `channels`. ADR-385 follow-on (2026-06-30): the legacy
        # `context`/`feed` alias rows are deleted; the live primary is `channels`.
        # 2026-07-01 operator re-sort: Notifications LEAVES the primary loop for
        # its own bottom launcher group (it's the always-present top-bar bell).
        # The Workspace loop is now Home · Channels · Files · Agents.
        # ADR-412 D3 (2026-07-06): Chat joins the primary tier — the lanes
        # surface (Altitude 2's chrome home), a NEW capability's home, not a
        # re-sort. Home · Chat · Channels · Files · Agents.
        # 2026-07-08 (operator focus): Agents LEAVES the primary loop → search-only.
        # A3 "hire an agent" is the deferred horizon (ADR-380 Rung-2 launch line;
        # ADR-414 already removed Freddie from this roster); the launch AI surface
        # is the A2 chat lanes, not a second door.
        # ADR-415 (2026-07-08): Channels DISSOLVED. Home · Chat · Files.
        "primary == the standing loop (home/chat/files)",
        {s for s, t in tiers.items() if t == "primary"} == {"home", "chat", "files"},
    )
    # ADR-349 D4: two settings doors re-split — Workspace Settings (operation)
    # + System Settings (account). The `configure` lump (ADR-347) is retired.
    check(
        "workspace-config == {workspace-settings} (the operation door)",
        {s for s, t in tiers.items() if t == "workspace-config"} == {"workspace-settings"},
    )
    check(
        "system-config == {settings} (the account/System Settings door)",
        {s for s, t in tiers.items() if t == "system-config"} == {"settings"},
    )
    check("legacy `configure` lump retired", not any(t == "configure" for t in tiers.values()))
    check("Utilities tier dissolved (no member carries it)",
          not any(t == "utilities" for t in tiers.values()))
    check(
        # ADR-349: the fronted mirrors (queue/recurrence), Setup, and all panes
        # go search-only. Agents upgraded to primary (D3). ADR-385 follow-on
        # (2026-06-30): `feed` (and `context`) deleted — the narrative is the
        # Channels Flow pane; `/feed` is a next.config redirect, not a surface.
        "search-only == mirrors + Setup + panes (the at-rest-hidden set)",
        # 2026-07-04: notifications joins the set — the top-bar bell is its
        # always-present door, so its at-rest launcher tile was deleted.
        # 2026-07-08: `agents` joins (deferred from launch chrome — ADR-414 /
        # commit 6d2d216). connectors/sources stay search-only panes (ADR-415
        # re-homed them pane_of workspace-settings; panes are always search-only).
        # ADR-418 (2026-07-08): `expected-output` LEFT (dormant, route="").
        # ADR-421 (2026-07-08): `mandate`/`identity`/`principles` LEAVE too — a
        # workspace has no constitution of its own; they went dormant (route=""),
        # so they drop out of the navigable tier map (surfaced on the agent detail).
        {s for s, t in tiers.items() if t == "search-only"}
        == {"budget", "autonomy",
            "program", "connectors", "sources", "activity", "agents",
            "queue", "recurrence", "setup", "notifications"},
    )
    chrome = [e for e in KERNEL_SURFACES if not e.get("route")]
    check("chrome entries carry no tier", all(not e.get("launcher_tier") for e in chrome))


def test_launcher_two_modes() -> None:
    print("\n[launcher] act-tier groups at rest; flat when searching")
    src = _read("components/shell/Launcher.tsx")
    # ADR-349 D4: at-rest groups are Workspace / Workspace Settings / User
    # Settings (the Utilities tier dissolved; two settings doors re-split).
    # 2026-07-08 naming-coherence pass (4c0518c): "System Settings" → "User Settings".
    check("KERNEL_TIER_GROUPS declared (Workspace/Workspace Settings/User Settings)",
          "'Workspace'" in src and "'Workspace Settings'" in src
          and "'User Settings'" in src and "KERNEL_TIER_GROUPS" in src)
    check("search-only hidden at rest", "search-only" in src and "return null" in src)
    check("flat list when searching (Spotlight role)", "isSearching" in src)
    check("pane rows labeled as Settings panes in search", "Settings pane" in src)
    check("register grouping deleted (superseded)", "KERNEL_REGISTER_GROUPS" not in src)
    check("Surface type declares launcher_tier", "launcher_tier?:" in _read("lib/compositor/types.ts"))


def test_constitution_band_removed() -> None:
    # ADR-421 (2026-07-08): the Home constitution band (the mandate/principles/
    # identity mirror-link trio) is REMOVED — a workspace has no constitution of
    # its own (ADR-414 D6); those are per-agent, surfaced on the agent detail.
    print("\n[band] Home constitution-link trio removed (ADR-421)")
    src = _read("components/library/HomeHeader.tsx")
    check("ConstitutionLinks component deleted", "function ConstitutionLinks" not in src)
    for slug in ("mandate", "principles", "identity"):
        check(f"band no longer links {slug}", f"slug: '{slug}'" not in src)
    # The autonomy badge still resolves via the navigation-enactment verb.
    check("autonomy badge → foregroundSurface('autonomy')", "foregroundSurface('autonomy')" in src)


def main() -> int:
    print("ADR-340 P3 gate — launcher re-sort")
    test_registry_tiers()
    test_launcher_two_modes()
    test_constitution_band_removed()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
