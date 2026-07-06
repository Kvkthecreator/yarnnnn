"""ADR-347 gate — One Settings Door; account → UserMenu.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies
ADR-347 reversed ADR-341's two-door split:
  - ONE Settings door (`workspace-settings`, titled "Settings") in the
    `configure` tier — the operation's settings (Constitution + Contract +
    Operation + Perception).
  - Governance (Budget=Rhythm, Autonomy=Witness) moved INTO the one door's
    "Contract" group (with Expected Output, ADR-348).
  - The account (Billing/Usage/Account) moved OUT to the UserMenu — the
    `settings` slug becomes the account window (titled "Account",
    search-only, UserMenu-reached), NOT a launcher door.

IMPORTANT: run as a SCRIPT (`python test_adr347_one_settings_door.py`), not
under pytest — the check() helper records failures via globals + sys.exit,
which pytest does not surface as test failures.

Usage:
    cd api
    python test_adr347_one_settings_door.py
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


def test_one_door_registry() -> None:
    print("\n[registry] one Settings door + account window (D1/D2)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # ADR-349 D4 re-split the launcher into two doors — the operation door
    # (workspace-settings) + the account/System Settings door (settings). The
    # ADR-347 SUBSTANCE persists (region split, editability rule §3,
    # account-region = the human/principal); only the launcher PROJECTION
    # changed (one tier → two). Titles/tiers below reflect the post-349 state.
    ws = by_slug["workspace-settings"]
    check("workspace-settings titled 'Workspace Settings' (the operation door)",
          ws["title"] == "Workspace Settings")
    check("workspace-settings in the workspace-config tier", ws.get("launcher_tier") == "workspace-config")
    check("workspace-settings is window-grade", not ws.get("pane_of"))
    # The account / System Settings door.
    acct = by_slug["settings"]
    check("settings titled 'System Settings' (the account/machine door)",
          acct["title"] == "System Settings")
    check("settings in the system-config tier (re-promoted to a door, ADR-349 D4)",
          acct.get("launcher_tier") == "system-config")
    check("settings is window-grade (account window)", not acct.get("pane_of"))


def test_contract_group() -> None:
    # ADR-387 §6.4 (2026-06-30) moved the agent-scoped governance panes
    # (Budget + Autonomy = governance/ GRANT, Expected Output = contract/
    # CONTRACT) to Freddie's roster pane; ADR-412 D5 (2026-07-06) REVERSED
    # it — Freddie left the /agents roster, and the panes returned to the
    # one Settings door as the System Agent group. The pane_of/pane_group
    # are also asserted in test_adr341.
    print("\n[contract] agent-scoped governance lives on the Settings door (ADR-412 D5)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    for slug in ("budget", "autonomy", "expected-output"):
        check(f"{slug} → the Settings door (ADR-412 D5)", by_slug[slug].get("pane_of") == "workspace-settings")
    # Governance is no longer in the dissolved System Settings door, and no
    # longer a 'Governance' OR 'Contract'-in-workspace-settings group.
    check("no pane homes to a 'Governance' group anymore",
          not any(e.get("pane_group") == "Governance" for e in KERNEL_SURFACES))


def test_settings_tiers() -> None:
    # ADR-347 D3 collapsed to one `configure` tier; ADR-349 D4 re-split into
    # two doors per operator decision. The ADR-347 account/operation SUBSTANCE
    # is intact — this asserts the post-349 launcher projection.
    print("\n[tiers] two settings doors (ADR-349 D4 re-split of ADR-347 D3)")
    from services.kernel_surfaces import KERNEL_SURFACES

    tiers = {e.get("launcher_tier") for e in KERNEL_SURFACES if e.get("route")}
    check("workspace-config tier present (operation door)", "workspace-config" in tiers)
    check("system-config tier present (account door)", "system-config" in tiers)
    check("the ADR-347 `configure` lump retired", "configure" not in tiers)
    launcher = _read("components/shell/Launcher.tsx")
    check("Launcher declares the Workspace Settings group",
          "label: 'Workspace Settings'" in launcher and "tier: 'workspace-config'" in launcher)
    check("Launcher declares the System Settings group",
          "label: 'System Settings'" in launcher and "tier: 'system-config'" in launcher)


def test_account_moved_to_usermenu() -> None:
    print("\n[usermenu] account reached from the avatar menu (D2)")
    um = _read("components/shell/UserMenu.tsx")
    check("UserMenu has an Account affordance", "Account" in um and "handleAccount" in um)
    check("Account opens the account window (`settings` slug)", "foregroundSurface('settings')" in um)
    check("Settings opens the one operation door (`workspace-settings`)",
          "foregroundSurface('workspace-settings')" in um)


def test_account_window_is_account_only() -> None:
    print("\n[account] the account window holds only billing/usage/account")
    sys_src = _read("app/(authenticated)/settings/page.tsx")
    check("account window has no AutonomyCard (moved to the one door)", "AutonomyCard" not in sys_src)
    check("account window has no BudgetCard (moved to the one door)", "BudgetCard" not in sys_src)
    check("account window keeps the Account pane group", '"Account"' in sys_src or "'Account'" in sys_src)
    check("account window keeps billing/usage/account panes",
          '"billing"' in sys_src and '"usage"' in sys_src and '"account"' in sys_src)


def test_redirect_stubs_point_to_one_door() -> None:
    # ADR-412 D5: the agent-scoped governance route stubs redirect into the
    # Settings door's System Agent group (the ADR-387 Freddie-pane targets
    # reversed).
    print("\n[stubs] governance routes redirect into the Settings door (ADR-412 D5)")
    for slug in ("budget", "autonomy", "expected-output"):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        target = f"/workspace-settings?workspace-settings.pane={slug}"
        check(f"/{slug} → {target}", f"redirect('{target}')" in stub)
        check(f"/{slug} stub is server-side (ADR-308)", "'use client'" not in stub)
    # The Home autonomy badge deep-links via the navigation-enactment verb
    # (ADR-297 D19.5). foregroundSurface('autonomy') is UNCHANGED — the registry
    # re-point (pane_of: workspace-settings) makes it resolve to the door.
    home = _read("components/library/HomeHeader.tsx")
    check("Home autonomy badge → foregroundSurface('autonomy')",
          "foregroundSurface('autonomy')" in home)


def test_expected_output_registered() -> None:
    print("\n[expected-output] the new pane is registered (ADR-348 dependency)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    check("expected-output surface present", "expected-output" in by_slug)
    eo = by_slug.get("expected-output", {})
    check("expected-output reads governance/_expected_output.yaml",
          any("_expected_output.yaml" in p for p in eo.get("substrate_paths", [])))
    desk = _read("types/desk.ts")
    check("desk.ts union includes 'expected-output'", "'expected-output'" in desk)


def main() -> int:
    print("ADR-347 gate — one Settings door; account → UserMenu")
    test_one_door_registry()
    test_contract_group()
    test_settings_tiers()
    test_account_moved_to_usermenu()
    test_account_window_is_account_only()
    test_redirect_stubs_point_to_one_door()
    test_expected_output_registered()
    print(f"\n{'=' * 60}")
    print(f"  {PASSED} passed, {FAILED} failed")
    print(f"{'=' * 60}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
