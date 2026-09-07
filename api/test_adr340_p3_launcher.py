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
    # ADR-592: `internal` rows are RETAINED in the raw KERNEL_SURFACES constant
    # (hide-not-delete — the slug must still resolve for its redirect stub) and
    # REMOVED by kernel_surface_entries(). The tier contract is about what a
    # member can actually reach, so it reads the SERVED roster. Reading the raw
    # constant is how `sources` looks like a violation while behaving correctly.
    from services.kernel_surfaces import kernel_surface_entries

    KERNEL_SURFACES = kernel_surface_entries()
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
        #
        # RULING 2026-09-07: the literal stops here. `home` was DELETED by
        # ADR-435 and the authoring apps + `reach` (ADR-642) joined the tier, so
        # the set had drifted five members. CLAUDE.md's own warning applies to
        # this file: "the surface roster churns fast — do not trust a surface
        # list written here." ADR-592 made the tier DERIVED from `stage`; assert
        # the derivation in BOTH directions instead (a one-directional check
        # catches a forgotten deletion and never a forgotten addition).
        "primary tier is DERIVED from stage == primary (both directions, ADR-592)",
        {s for s, t in tiers.items() if t == "primary"}
        == {e["slug"] for e in navigable if e.get("stage") == "primary"},
        f'tier={sorted(s for s, t in tiers.items() if t == "primary")} '
        f'stage={sorted(e["slug"] for e in navigable if e.get("stage") == "primary")}',
    )
    check("a deleted surface holds no tier (ADR-435 home, ADR-415 channels)",
          not ({"home", "channels", "context", "feed"} & set(tiers)))
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
    # RULING 2026-09-07: this hand-spelled literal drifted in BOTH directions —
    # it named six slugs that no longer exist (`budget`/`autonomy`/`activity`
    # dormant, `recurrence` retired by ADR-603 D5, `setup` by ADR-414 D4,
    # `agents` re-promoted 2026-07-16) and missed three that do
    # (`billing`/`notification-settings`/`usage`). Re-spelling it just resets
    # the drift clock. ADR-592 made the tier DERIVED from `stage`, so assert the
    # derivation and the two structural rules ADR-340 actually owns.
    # ADR-592 governs APPS via `stage`; a PANE carries no stage and is
    # search-only because of what it is — it is entered through its parent
    # window, never browsed on its own. Those are the two populations, and the
    # search-only tier is exactly their union.
    search_only = {s for s, t in tiers.items() if t == "search-only"}
    panes = {e["slug"] for e in KERNEL_SURFACES if e.get("route") and e.get("pane_of")}
    # ADR-349 D4's two settings doors are the one intentional exception: they
    # declare stage=search-only (unpromoted — no Dock tile) but carry their own
    # dedicated tiers (`system-config` / `workspace-config`) so the launcher can
    # group them as doors rather than list them among summon-by-name surfaces.
    SETTINGS_DOORS = {"settings", "workspace-settings"}
    staged_search = {
        e["slug"] for e in KERNEL_SURFACES
        if e.get("route") and not e.get("pane_of")
        and e.get("stage") == "search-only"
        and e["slug"] not in SETTINGS_DOORS
    }
    check(
        "search-only == panes + stage-search-only apps (both directions, ADR-592)",
        search_only == (panes | staged_search),
        f"tier={sorted(search_only)} "
        f"expected={sorted(panes | staged_search)}",
    )
    check("every pane is search-only (a pane is entered through its window)",
          panes <= search_only,
          str(sorted(panes - search_only)))
    # ADR-592: `internal` REMOVES the row from the served roster — that IS the
    # hide, because nav is backend-driven. A row that declares `internal` and is
    # still served contradicts its own declaration.
    served_internal = {
        e["slug"] for e in KERNEL_SURFACES
        if e.get("route") and e.get("stage") == "internal"
    }
    check("no served row declares stage=internal (ADR-592: internal leaves the roster)",
          not served_internal,
          f"served but declared internal: {sorted(served_internal)}")
    # And a retired/dormant slug carries no tier at all.
    check("dormant + retired slugs hold no launcher tier",
          not ({"recurrence", "setup", "queue", "program", "expected-output",
                "mandate", "identity", "principles"} & set(tiers)))
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
    from services.kernel_surfaces import kernel_surface_entries

    # ADR-421 (2026-07-08): the Home constitution band (the mandate/principles/
    # identity mirror-link trio) is REMOVED — a workspace has no constitution of
    # its own (ADR-414 D6); those are per-agent, surfaced on the agent detail.
    # RULING 2026-09-07: ADR-435 DELETED the Home surface, and HomeHeader.tsx
    # with it. `_read` returns "" for a missing file, so the three "deleted"
    # checks below were passing VACUOUSLY against an empty string while the one
    # positive check (the autonomy badge) failed — and `autonomy` is itself no
    # longer a registry slug. A gate whose subject is deleted cannot be
    # re-anchored; what it protected (no workspace-level constitution links) is
    # now assertable against the roster itself, which is where the rule lives.
    print("\n[band] no workspace-level constitution surface (ADR-421 + ADR-435)")
    check("HomeHeader is gone with the Home surface (ADR-435)",
          not (_WEB / "components/library/HomeHeader.tsx").exists())
    # ADR-421 + ADR-414 D6: a workspace has no constitution of its own — these
    # are per-agent and surfaced on the agent detail, so no slug may be served.
    by_slug = {e["slug"] for e in kernel_surface_entries()}
    for slug in ("mandate", "principles", "identity", "autonomy"):
        check(f"`{slug}` is not a served surface (a workspace has no constitution)",
              slug not in by_slug)


def main() -> int:
    print("ADR-340 P3 gate — launcher re-sort")
    test_registry_tiers()
    test_launcher_two_modes()
    test_constitution_band_removed()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
