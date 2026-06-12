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

EXPECTED_PANES = {"budget", "autonomy", "program", "connectors", "sources"}


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
    print("\n[registry] pane_of model in kernel_surfaces.py")
    from services.kernel_surfaces import KERNEL_SURFACES, kernel_pane_slugs

    panes = kernel_pane_slugs()
    check("pane set is exactly the D4 fold", panes == EXPECTED_PANES, f"panes={sorted(panes)}")

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    for slug in sorted(EXPECTED_PANES):
        check(f"{slug}: pane_of == 'settings'", by_slug[slug].get("pane_of") == "settings")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    check(
        "settings is the one os-config window (no pane_of on itself)",
        not by_slug["settings"].get("pane_of"),
    )
    check("settings titled 'System Settings'", by_slug["settings"]["title"] == "System Settings")
    check(
        "setup stays window-grade (Sequence surface, ADR-331)",
        not by_slug["setup"].get("pane_of"),
    )
    # D4 grouping
    check("connectors grouped Perception & transports", by_slug["connectors"]["pane_group"] == "Perception & transports")
    check("sources grouped Perception & transports", by_slug["sources"]["pane_group"] == "Perception & transports")
    check("autonomy grouped Governance", by_slug["autonomy"]["pane_group"] == "Governance")
    check("budget grouped Governance", by_slug["budget"]["pane_group"] == "Governance")
    check("program grouped Program", by_slug["program"]["pane_group"] == "Program")


def test_settings_container() -> None:
    print("\n[container] System Settings sidebar renders all panes")
    src = _read("app/(authenticated)/settings/page.tsx")
    check("PANE_GROUPS sidebar declared", "PANE_GROUPS" in src)
    check("reads ?pane= (canonical)", 'searchParams.get("pane")' in src)
    check("accepts ?tab= legacy alias", 'searchParams.get("tab")' in src)
    for needle, label in [
        ("ConnectedIntegrationsSection", "Connectors pane body"),
        ("SourcesCard", "Sources pane body"),
        ("AutonomyCard", "Autonomy pane body"),
        ("BudgetCard", "Budget pane body"),
        ("ProgramLifecycleDrawer", "Program pane body"),
    ]:
        check(f"{label} renders in container", needle in src)
    check("Program pane carries re-run-setup door", "Re-run setup" in src)
    check("pane selection syncs URL via setSurfaceParams", "setSurfaceParams({ pane" in src)


def test_redirect_stubs() -> None:
    print("\n[stubs] old routes are ADR-308 server redirects")
    for slug in sorted(EXPECTED_PANES):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        check(
            f"/{slug} → /settings?pane={slug}",
            f"redirect('/settings?pane={slug}')" in stub,
        )
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
