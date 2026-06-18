"""ADR-340 P2 gate — System Settings consolidation (window-grade → pane-grade).

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies
the one-door fold: five os-config surfaces (budget, autonomy, program,
connectors, sources) become PANE-GRADE — registry `pane_of: "settings"`,
sidebar panes inside the System Settings window, ADR-308 redirect stubs on
their old routes, pane-blind call sites via foregroundSurface resolution.

Usage:
    cd api
    python test_adr340_p2_settings_fold.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
_WEB = _API_ROOT.parent / "web"

PASSED = 0
FAILED = 0

# ADR-340 P2 folded five os-config surfaces into one door. ADR-341
# (2026-06-18) splits the door in two: Governance panes stay in System
# Settings; operation-config panes move to Workspace Settings (+ the
# constitution mirrors gain a pane door there). The pane *mechanism* is
# unchanged — only which door each pane folds into.
SYSTEM_SETTINGS_PANES = {"budget", "autonomy"}
WORKSPACE_SETTINGS_PANES = {"program", "connectors", "sources", "mandate", "identity", "principles"}
EXPECTED_PANES = SYSTEM_SETTINGS_PANES | WORKSPACE_SETTINGS_PANES


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


def test_registry_pane_model() -> None:
    print("\n[registry] pane_of model in kernel_surfaces.py (ADR-341 two-door)")
    from services.kernel_surfaces import KERNEL_SURFACES, kernel_pane_slugs

    panes = kernel_pane_slugs()
    # ADR-341: the pane set spans both doors (+ activity under recurrence,
    # ADR-340 D8). Assert each ADR-341 pane is present, not strict equality
    # (activity belongs to the D8 gate).
    for slug in sorted(EXPECTED_PANES):
        check(f"{slug} is pane-grade", slug in panes, f"panes={sorted(panes)}")

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # Governance panes fold into System Settings (the OS door).
    for slug in sorted(SYSTEM_SETTINGS_PANES):
        check(f"{slug}: pane_of == 'settings'", by_slug[slug].get("pane_of") == "settings")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    # Operation-config + constitution panes fold into Workspace Settings.
    for slug in sorted(WORKSPACE_SETTINGS_PANES):
        check(f"{slug}: pane_of == 'workspace-settings'", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    check(
        "settings is a container window (no pane_of on itself)",
        not by_slug["settings"].get("pane_of"),
    )
    check(
        "workspace-settings is a container window (no pane_of on itself)",
        not by_slug["workspace-settings"].get("pane_of"),
    )
    check("settings titled 'System Settings'", by_slug["settings"]["title"] == "System Settings")
    check("workspace-settings titled 'Workspace Settings'", by_slug["workspace-settings"]["title"] == "Workspace Settings")
    check(
        "setup stays window-grade (Sequence surface, ADR-331)",
        not by_slug["setup"].get("pane_of"),
    )
    # ADR-341 grouping (two doors, second-order sidebar sections)
    check("autonomy grouped Governance", by_slug["autonomy"]["pane_group"] == "Governance")
    check("budget grouped Governance", by_slug["budget"]["pane_group"] == "Governance")
    check("connectors grouped Perception", by_slug["connectors"]["pane_group"] == "Perception")
    check("sources grouped Perception", by_slug["sources"]["pane_group"] == "Perception")
    check("program grouped Operation", by_slug["program"]["pane_group"] == "Operation")
    for slug in ("mandate", "identity", "principles"):
        check(f"{slug} grouped Constitution", by_slug[slug]["pane_group"] == "Constitution")


def test_settings_container() -> None:
    print("\n[container] both Settings doors mount the shared shell (ADR-341)")
    # ADR-341: one shared SettingsPaneShell, two mounts.
    shell = _read("components/settings/SettingsPaneShell.tsx")
    check("SettingsPaneShell exists (Singular Implementation, ADR-341 D5)", "SettingsPaneShell" in shell)
    check("shell reads ?pane= (canonical)", 'searchParams.get("pane")' in shell)
    check("shell accepts ?tab= legacy alias", 'searchParams.get("tab")' in shell)
    check("shell syncs URL via setSurfaceParams", "setSurfaceParams({ pane" in shell)

    sys_src = _read("app/(authenticated)/settings/page.tsx")
    check("System Settings mounts SettingsPaneShell", "SettingsPaneShell" in sys_src)
    check("System Settings declares PANE_GROUPS", "PANE_GROUPS" in sys_src)
    for needle, label in [
        ("AutonomyCard", "Autonomy pane body"),
        ("BudgetCard", "Budget pane body"),
    ]:
        check(f"System Settings: {label}", needle in sys_src)

    ws_src = _read("app/(authenticated)/workspace-settings/page.tsx")
    check("Workspace Settings mounts SettingsPaneShell", "SettingsPaneShell" in ws_src)
    check("Workspace Settings declares PANE_GROUPS", "PANE_GROUPS" in ws_src)
    for needle, label in [
        ("MandateCard", "Mandate pane body"),
        ("IdentityBrandCard", "Identity pane body"),
        ("PrinciplesCard", "Principles pane body"),
        ("ConnectedIntegrationsSection", "Connectors pane body"),
        ("SourcesCard", "Sources pane body"),
        ("ProgramLifecycleDrawer", "Program pane body"),
    ]:
        check(f"Workspace Settings: {label}", needle in ws_src)
    check("Workspace Settings Program pane carries re-run-setup door", "Re-run setup" in ws_src)


def test_redirect_stubs() -> None:
    print("\n[stubs] old routes are ADR-308 server redirects to the right door (ADR-341)")
    door = {
        **{s: "settings" for s in SYSTEM_SETTINGS_PANES},
        **{s: "workspace-settings" for s in WORKSPACE_SETTINGS_PANES},
    }
    # Governance panes (budget/autonomy) have no standalone route file —
    # they were never window-grade with a stub. Only check slugs that have
    # a page.tsx stub (the re-homed + constitution routes).
    for slug in sorted(WORKSPACE_SETTINGS_PANES):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        if not stub:
            continue
        target = f"/{door[slug]}?pane={slug}"
        check(f"/{slug} → {target}", f"redirect('{target}')" in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)


def test_window_manager_resolution() -> None:
    print("\n[nav] foregroundSurface resolves pane-grade slugs")
    src = _read("lib/shell/useSurfacePreferences.tsx")
    check("pane resolution wrapper present", "pane_of" in src and "foregroundWindowGrade" in src)
    check("pane delivery via parent route + ?pane=", "?pane=${slug}" in src)
    viewport = _read("components/shell/SurfaceViewport.tsx")
    check("viewport filters pane-grade slugs from window mounting", "paneSlugs" in viewport)
    topbar = _read("components/shell/chrome/TopBarSurface.tsx")
    check("dock filters pane-grade surfaces", "pane_of" in topbar)
    types_src = _read("lib/compositor/types.ts")
    check("Surface type declares pane_of + pane_group", "pane_of?:" in types_src and "pane_group?:" in types_src)


def test_registry_prune() -> None:
    print("\n[prune] SurfaceRegistry holds window-grade components only")
    reg = _read("components/shell/SurfaceRegistry.tsx")
    for slug, comp in [
        ("budget", "BudgetPage"),
        ("autonomy", "AutonomyPage"),
        ("program", "ProgramPage"),
        ("connectors", "ConnectorsPage"),
        ("sources", "SourcesPage"),
    ]:
        check(f"{slug} not window-mounted", f"{slug}: {comp}" not in reg)
    check("settings still window-mounted", "settings: SettingsPage" in reg)
    check("registry is Partial (panes resolve undefined)", "Partial<Record<KernelSurfaceSlug" in reg)


def main() -> int:
    print("ADR-340 P2 gate — System Settings consolidation")
    test_registry_pane_model()
    test_settings_container()
    test_redirect_stubs()
    test_window_manager_resolution()
    test_registry_prune()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
