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
# (2026-06-18) split it in two; ADR-347 (2026-06-19) REVERSED the split —
# ALL operation panes (Governance/Contract included) fold into the ONE
# Settings door (`workspace-settings`); the account moves to the UserMenu
# (the `settings` slug is the account window, not a pane parent). The pane
# *mechanism* is unchanged — only which door each pane folds into.
# ACCOUNT_PANES (billing/usage/account) are page-local tabs on the account
# window, NOT registry pane-grade surfaces, so they are not in the registry.
ALL_SETTINGS_PANES = {
    "budget", "autonomy", "expected-output",  # Contract (ADR-347/348)
    "program",                                  # Operation
    "mandate", "identity", "principles",        # Constitution
}
# ADR-385: connectors + sources are still pane-grade, but pane_of: channels
# (Perception left Workspace Settings). They stay in the pane-grade set but
# NOT in the workspace-settings-parent set.
CHANNELS_PANES = {"connectors", "sources"}
EXPECTED_PANES = ALL_SETTINGS_PANES | CHANNELS_PANES


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
    # ADR-347: ALL operation panes fold into the ONE Settings door.
    for slug in sorted(ALL_SETTINGS_PANES):
        check(f"{slug}: pane_of == 'workspace-settings'", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    # ADR-385: connectors + sources re-home onto the Channels surface.
    for slug in sorted(CHANNELS_PANES):
        check(f"{slug}: pane_of == 'channels' (ADR-385)", by_slug[slug].get("pane_of") == "channels")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    check(
        "settings is a container window (no pane_of on itself)",
        not by_slug["settings"].get("pane_of"),
    )
    check(
        "workspace-settings is a container window (no pane_of on itself)",
        not by_slug["workspace-settings"].get("pane_of"),
    )
    # ADR-349 D4: `settings` = the account/System Settings door; `workspace-settings` = the operation door.
    check("settings titled 'System Settings' (ADR-349 D4)", by_slug["settings"]["title"] == "System Settings")
    check("workspace-settings titled 'Workspace Settings' (ADR-349 D4)", by_slug["workspace-settings"]["title"] == "Workspace Settings")
    check(
        "setup stays window-grade (Sequence surface, ADR-331)",
        not by_slug["setup"].get("pane_of"),
    )
    # ADR-347 grouping — the Contract group gathers Rhythm/Witness/Expected Output.
    for slug in ("budget", "autonomy", "expected-output"):
        check(f"{slug} grouped Contract", by_slug[slug]["pane_group"] == "Contract")
    # ADR-385 (2026-06-29): Perception left Workspace Settings — connectors +
    # sources re-home onto the Channels surface (group Channels).
    check("connectors grouped Channels (ADR-385)", by_slug["connectors"]["pane_group"] == "Channels")
    check("sources grouped Channels (ADR-385)", by_slug["sources"]["pane_group"] == "Channels")
    check("program grouped Operation", by_slug["program"]["pane_group"] == "Operation")
    for slug in ("mandate", "identity", "principles"):
        check(f"{slug} grouped Constitution", by_slug[slug]["pane_group"] == "Constitution")


def test_settings_container() -> None:
    print("\n[container] both Settings doors mount the shared shell (ADR-341)")
    # ADR-341: one shared SettingsPaneShell, two mounts.
    shell = _read("components/settings/SettingsPaneShell.tsx")
    check("SettingsPaneShell exists (Singular Implementation, ADR-341 D5)", "SettingsPaneShell" in shell)
    # ADR-358 D6: the pane is window-NAMESPACED (`{windowSlug}.pane`), read +
    # written via useSurfaceParam(windowSlug) so the two Settings doors never
    # collide on a flat `?pane=`.
    check("shell scopes pane by windowSlug (useSurfaceParam)", "useSurfaceParam(windowSlug)" in shell)
    check("shell reads its namespaced pane", 'surfaceParam.get("pane")' in shell)
    check("shell accepts ?tab= legacy flat alias", 'searchParams.get("tab")' in shell)
    check("shell writes its namespaced pane", "surfaceParam.set({ pane })" in shell)

    # ADR-347: the `settings` page is the ACCOUNT window (billing/usage/account).
    sys_src = _read("app/(authenticated)/settings/page.tsx")
    check("Account window mounts SettingsPaneShell", "SettingsPaneShell" in sys_src)
    check("Account window declares PANE_GROUPS", "PANE_GROUPS" in sys_src)
    check("Account window has no governance cards (moved to the one door)",
          "AutonomyCard" not in sys_src and "BudgetCard" not in sys_src)

    # ADR-347: the ONE Settings door carries Constitution + Contract +
    # Operation + Perception pane bodies.
    ws_src = _read("app/(authenticated)/workspace-settings/page.tsx")
    check("Settings door mounts SettingsPaneShell", "SettingsPaneShell" in ws_src)
    check("Settings door declares PANE_GROUPS", "PANE_GROUPS" in ws_src)
    for needle, label in [
        ("MandateCard", "Mandate pane body"),
        ("IdentityBrandCard", "Identity pane body"),
        ("PrinciplesCard", "Principles pane body"),
        ("BudgetCard", "Budget (Rhythm) pane body"),
        ("AutonomyCard", "Autonomy (Witness) pane body"),
        ("ExpectedOutputCard", "Expected Output pane body"),
        # ADR-385: Connectors + Sources pane bodies moved to the Channels surface.
        ("ProgramLifecycleDrawer", "Program pane body"),
    ]:
        check(f"Settings door: {label}", needle in ws_src)
    check("Settings door Program pane carries re-run-setup door", "Re-run setup" in ws_src)


def test_redirect_stubs() -> None:
    print("\n[stubs] old routes are ADR-308 server redirects to the one door (ADR-347)")
    # ADR-347: ALL panes fold into the one Settings door. Only check slugs
    # that have a page.tsx stub (budget/autonomy/expected-output + the
    # re-homed + constitution routes; some panes never had a window route).
    for slug in sorted(ALL_SETTINGS_PANES):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        if not stub:
            continue
        # ADR-358 D6: stubs redirect with the window-NAMESPACED pane param.
        target = f"/workspace-settings?workspace-settings.pane={slug}"
        check(f"/{slug} → {target}", f"redirect('{target}')" in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)
    # ADR-385: the re-homed Perception routes redirect to the Channels surface.
    for slug in sorted(CHANNELS_PANES):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        if not stub:
            continue
        target = f"/channels?channels.pane={slug}"
        check(f"/{slug} → {target} (ADR-385)", f"redirect('{target}')" in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)


def test_window_manager_resolution() -> None:
    print("\n[nav] foregroundSurface resolves pane-grade slugs")
    src = _read("lib/shell/useSurfacePreferences.tsx")
    check("pane resolution wrapper present", "pane_of" in src and "foregroundWindowGrade" in src)
    # ADR-358 D5+D6: the pane is delivered by setting the parent window's
    # NAMESPACED pane key (`{parent}.pane`) on the CURRENT pathname via
    # history.replaceState (preserving the /desktop baseline), not by
    # router.push-ing the parent's page route. Assert the durable behavior —
    # the namespaced pane key reaches the URL via searchParams.set.
    check(
        "pane delivered via namespaced {parent}.pane without a pathname flip",
        "searchParams.set(scopeParamKey(parentSlug, 'pane'), slug)" in src,
    )
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
        ("expected-output", "ExpectedOutputPage"),
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
