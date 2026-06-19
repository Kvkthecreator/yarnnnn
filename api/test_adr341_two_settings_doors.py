"""ADR-341 gate — Settings doors.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3).

**ADR-347 (2026-06-19) SUPERSEDES ADR-341 D1/D3/D6** — the two-door split is
reversed. ADR-341's substrate-backed split (governance/ vs constitution/) was
cut on the wrong axis: the operator navigates by "machine vs operation," not
"agent-can-write vs can't." So Governance (Autonomy/Budget = per-operation
config) moves INTO the one operation-settings door (the "Contract" group),
and the account (Billing/Usage/Account = the human/principal, user_id-scoped)
moves OUT to the UserMenu. This gate is updated to the post-ADR-347 reality;
the parts ADR-341 still owns (shared SettingsPaneShell, constitution band
preserved, registers-as-code-taxonomy) are unchanged.

Usage:
    cd api
    python test_adr341_two_settings_doors.py
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


def test_two_container_surfaces() -> None:
    print("\n[registry] settings containers (D1, post-ADR-347)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    check("settings surface present", "settings" in by_slug)
    check("workspace-settings surface present", "workspace-settings" in by_slug)
    # ADR-347: `settings` is the account window (UserMenu-reached);
    # `workspace-settings` is THE one Settings door (titled "Settings").
    check("settings titled 'Account' (ADR-347)", by_slug["settings"]["title"] == "Account")
    check("workspace-settings titled 'Settings' (ADR-347 — the one door)", by_slug["workspace-settings"]["title"] == "Settings")
    # Containers are window-grade (not panes themselves).
    check("settings is window-grade (no pane_of)", not by_slug["settings"].get("pane_of"))
    check("workspace-settings is window-grade (no pane_of)", not by_slug["workspace-settings"].get("pane_of"))


def test_two_settings_tiers() -> None:
    print("\n[tier] one Settings door; account → UserMenu (ADR-347, supersedes D3)")
    from services.kernel_surfaces import KERNEL_SURFACES

    tiers = {e["slug"]: e.get("launcher_tier") for e in KERNEL_SURFACES if e.get("route")}
    # ADR-347: the one Settings door is in the `configure` tier; the account
    # window (`settings` slug) is search-only (UserMenu-reached, not a door).
    check(
        "workspace-settings → configure tier (the one door)",
        tiers.get("workspace-settings") == "configure",
        str({s: t for s, t in tiers.items() if "config" in str(t)}),
    )
    check("settings → search-only (account window, UserMenu-reached)", tiers.get("settings") == "search-only")
    check("legacy `workspace-config` tier retired", not any(t == "workspace-config" for t in tiers.values()))
    check("legacy `system-config` tier retired", not any(t == "system-config" for t in tiers.values()))
    # Launcher renders one Settings group.
    launcher = _read("components/shell/Launcher.tsx")
    check("Launcher group: Settings (configure)",
          "label: 'Settings'" in launcher and "tier: 'configure'" in launcher)
    check("the two-door Launcher groups retired (no workspace-config/system-config tiers)",
          "tier: 'workspace-config'" not in launcher and "tier: 'system-config'" not in launcher)


def test_pane_homing() -> None:
    print("\n[panes] panes fold into the one door (ADR-347, supersedes D6)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # ADR-347: Governance (Budget=Rhythm, Autonomy=Witness) + Expected Output
    # = the Contract group, in the ONE operation-settings door.
    for slug in ("budget", "autonomy", "expected-output"):
        check(f"{slug} → the one Settings door", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug} grouped Contract", by_slug[slug].get("pane_group") == "Contract")
    # Operation + Perception (constitution/ + operation/).
    for slug in ("program",):
        check(f"{slug} → the one Settings door", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug} grouped Operation", by_slug[slug].get("pane_group") == "Operation")
    for slug in ("connectors", "sources"):
        check(f"{slug} → the one Settings door", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug} grouped Perception", by_slug[slug].get("pane_group") == "Perception")
    # Constitution (the persona/ + constitution/ roots).
    for slug in ("mandate", "identity", "principles"):
        check(f"{slug} → the one Settings door", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug} grouped Constitution", by_slug[slug].get("pane_group") == "Constitution")


def test_registers_unchanged() -> None:
    print("\n[registers] doors are a view over registers; registers unchanged (D4)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # Governance panes keep os-config; constitution keeps intent; the door is
    # `pane_of`, orthogonal to register (ADR-340 P2 / ADR-341 D4).
    check("budget register unchanged (os-config)", by_slug["budget"].get("register") == "os-config")
    check("mandate register unchanged (intent)", by_slug["mandate"].get("register") == "intent")
    check("identity register unchanged (intent)", by_slug["identity"].get("register") == "intent")
    check("workspace-settings register == application (a windowed app)", by_slug["workspace-settings"].get("register") == "application")


def test_shared_shell_singular_impl() -> None:
    print("\n[impl] one shared SettingsPaneShell, two mounts (D5)")
    shell = _read("components/settings/SettingsPaneShell.tsx")
    check("SettingsPaneShell exists", "export function SettingsPaneShell" in shell)
    check("shell owns ?pane= sync", "setSurfaceParams({ pane" in shell)
    sys_src = _read("app/(authenticated)/settings/page.tsx")
    ws_src = _read("app/(authenticated)/workspace-settings/page.tsx")
    check("System Settings mounts the shell", "SettingsPaneShell" in sys_src)
    check("Workspace Settings mounts the shell", "SettingsPaneShell" in ws_src)
    # FE allowlist + registry cover workspace-settings (else the door can't open).
    desk = _read("types/desk.ts")
    check("desk.ts union includes 'workspace-settings'", "'workspace-settings'" in desk)
    reg = _read("components/shell/SurfaceRegistry.tsx")
    check("SurfaceRegistry maps workspace-settings", "'workspace-settings':" in reg and "WorkspaceSettingsPage" in reg)


def test_constitution_band_preserved() -> None:
    print("\n[band] constitution stays first-class on Home (D2, ADR-312 D5)")
    home = _read("components/library/HomeHeader.tsx")
    check("HomeHeader still renders the constitution band", "ConstitutionLinks" in home)
    # Constitution routes are now ADR-308 stubs → Workspace Settings panes;
    # the band consumes the cards directly, independent of these routes.
    for slug in ("mandate", "identity", "principles"):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        check(f"/{slug} is a server redirect stub", f"redirect('/workspace-settings?pane={slug}')" in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)


if __name__ == "__main__":
    test_two_container_surfaces()
    test_two_settings_tiers()
    test_pane_homing()
    test_registers_unchanged()
    test_shared_shell_singular_impl()
    test_constitution_band_preserved()
    print(f"\n{'=' * 60}")
    print(f"  {PASSED} passed, {FAILED} failed")
    print(f"{'=' * 60}")
    sys.exit(1 if FAILED else 0)
