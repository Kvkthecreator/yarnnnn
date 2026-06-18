"""ADR-341 gate — Two Settings Doors: System Settings + Workspace Settings.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies
the ADR-340 D4 "one door" consolidation splits into two coherent doors:
System Settings (the OS governing the agent — governance/ root) and Workspace
Settings (this operation — constitution/ + operation/ + persona/ roots). The
split is substrate-backed (ADR-320 roots), expressed as `pane_of` membership
(registers unchanged, ADR-340 principle), Singular-Implementation via one
shared SettingsPaneShell.

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
    print("\n[registry] two Settings container surfaces (D1)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    check("settings surface present", "settings" in by_slug)
    check("workspace-settings surface present", "workspace-settings" in by_slug)
    check("settings titled 'System Settings'", by_slug["settings"]["title"] == "System Settings")
    check("workspace-settings titled 'Workspace Settings'", by_slug["workspace-settings"]["title"] == "Workspace Settings")
    # Containers are window-grade (not panes themselves).
    check("settings is window-grade (no pane_of)", not by_slug["settings"].get("pane_of"))
    check("workspace-settings is window-grade (no pane_of)", not by_slug["workspace-settings"].get("pane_of"))


def test_two_settings_tiers() -> None:
    print("\n[tier] two separate Settings groups, Operation above System (D3)")
    from services.kernel_surfaces import KERNEL_SURFACES

    tiers = {e["slug"]: e.get("launcher_tier") for e in KERNEL_SURFACES if e.get("route")}
    check(
        "workspace-settings → workspace-config tier",
        tiers.get("workspace-settings") == "workspace-config",
        str({s: t for s, t in tiers.items() if "config" in str(t) or t == "system"}),
    )
    check("settings → system-config tier", tiers.get("settings") == "system-config")
    check("legacy single-member `system` tier retired", not any(t == "system" for t in tiers.values()))
    check("the old `configure` lump retired", not any(t == "configure" for t in tiers.values()))
    # Launcher renders two separate groups, Operation ordered above System.
    launcher = _read("components/shell/Launcher.tsx")
    check("Launcher group: Operation (workspace-config)",
          "label: 'Operation'" in launcher and "tier: 'workspace-config'" in launcher)
    check("Launcher group: System (system-config)",
          "label: 'System'" in launcher and "tier: 'system-config'" in launcher)
    check(
        "Operation group ordered above System group",
        launcher.index("tier: 'workspace-config'") < launcher.index("tier: 'system-config'"),
    )


def test_pane_homing() -> None:
    print("\n[panes] panes fold into the right door (D6)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # System Settings — Governance (the governance/ root, agent-can't-write).
    for slug in ("budget", "autonomy"):
        check(f"{slug} → System Settings", by_slug[slug].get("pane_of") == "settings")
        check(f"{slug} grouped Governance", by_slug[slug].get("pane_group") == "Governance")
    # Workspace Settings — Operation + Perception (constitution/ + operation/).
    for slug in ("program",):
        check(f"{slug} → Workspace Settings", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug} grouped Operation", by_slug[slug].get("pane_group") == "Operation")
    for slug in ("connectors", "sources"):
        check(f"{slug} → Workspace Settings", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug} grouped Perception", by_slug[slug].get("pane_group") == "Perception")
    # Workspace Settings — Constitution (the persona/ + constitution/ roots).
    for slug in ("mandate", "identity", "principles"):
        check(f"{slug} → Workspace Settings", by_slug[slug].get("pane_of") == "workspace-settings")
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
