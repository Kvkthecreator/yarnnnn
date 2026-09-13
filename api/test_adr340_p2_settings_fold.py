"""ADR-340 P2 gate — System Settings consolidation (window-grade → pane-grade), recut 2026-09-12 to the live pane model.

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

# 2026-09-12 recut. ADR-340 P2 folded five os-config surfaces into one door;
# every one of them has since left: `autonomy` + `budget` (the steward's dials —
# deleted with the steward, ADR-632; /budget is a stub into Usage, ADR-491 D3),
# `connectors` + `sources` (`stage: internal`, ADR-592; Reach owns the connection
# acts, ADR-645), `program` (dormant, ADR-432 D2d). What the fold LEFT BEHIND is
# the live model this gate now pins: the pane MECHANISM (one SettingsPaneShell,
# window-namespaced panes) and the account panes that ride it.
ACCOUNT_PANES = {"notification-settings"}          # pane_of "settings" (the account window)
WORKSPACE_PANES = {"billing", "usage"}             # pane_of "workspace-settings" (ADR-491 D1)
INTERNAL_ROWS = {"connectors", "sources"}          # stage internal — off the roster, no pane_of
DORMANT_ROWS = {"program"}                         # no route, no pane_group
EXPECTED_PANES = ACCOUNT_PANES | WORKSPACE_PANES

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
    print("\n[registry] the live pane model (2026-09-12)")
    import sys
    sys.path.insert(0, str(_API_ROOT))
    from services.kernel_surfaces import KERNEL_SURFACES
    by_slug = {row["slug"]: row for row in KERNEL_SURFACES}
    panes = {slug for slug, row in by_slug.items() if row.get("pane_of")}
    check("the pane set is exactly the live panes", panes == EXPECTED_PANES, f"panes={sorted(panes)}")
    for slug in sorted(ACCOUNT_PANES):
        check(f"{slug}: pane_of == 'settings'", by_slug[slug].get("pane_of") == "settings")
    for slug in sorted(WORKSPACE_PANES):
        check(f"{slug}: pane_of == 'workspace-settings' (ADR-491 D1)", by_slug[slug].get("pane_of") == "workspace-settings")
    for slug in sorted(INTERNAL_ROWS):
        check(f"{slug}: stage internal (ADR-592)", by_slug[slug].get("stage") == "internal")
        check(f"{slug}: not pane-grade (Reach owns the acts, ADR-645)", by_slug[slug].get("pane_of") is None)
    for slug in sorted(DORMANT_ROWS):
        check(f"{slug}: dormant (no route, no pane_group — ADR-432 D2d)", not by_slug[slug].get("route") and not by_slug[slug].get("pane_group"))
    for slug in ("autonomy", "budget", "system-agent"):
        check(f"{slug}: no registry row (deleted with the steward, ADR-632)", slug not in by_slug)
    check("settings + workspace-settings are windows, not panes", not by_slug["settings"].get("pane_of") and not by_slug["workspace-settings"].get("pane_of"))

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
    # ADR-432 D1c/D2d (2026-07-09): the Workspace-Settings OPERATION group is GONE
    # — Brand retired (D1c), and the operator-facing Program pane retired (D2d, the
    # slug is dormant, the hire machinery stays). The door no longer mounts
    # ProgramLifecycleDrawer or the "Re-run setup" door — those were the Program
    # pane body. The drawer survives in SetupSequence; setup re-entry is the Setup
    # surface itself (ADR-331). The door is now Access (Members) alone.
    check("Settings door NO LONGER mounts the Program pane body",
          "ProgramLifecycleDrawer" not in ws_src)
    check("Settings door NO LONGER carries the re-run-setup door",
          "Re-run setup" not in ws_src)
    # 2026-09-12: the System group, its dial panes, SystemAgentPanes and the
    # /system-agent stub are deleted with the steward (ADR-632) — nothing to pin.
    # ADR-421: the Settings door NO LONGER renders the Constitution panes — a
    # workspace has no constitution of its own (mandate/identity/principles are
    # per-agent, surfaced on the agent detail via AgentConstitutionBlock).
    check("Settings door no longer renders MandateCard (ADR-421)", "MandateCard" not in ws_src)
    check("Settings door no longer renders PrinciplesCard (ADR-421)", "PrinciplesCard" not in ws_src)
    agent_src = _read("components/agents/AgentContentView.tsx")
    for needle, label in [
        ("PrinciplesCard", "Principles"),
        ("BudgetCard", "Budget"),
        ("AutonomyCard", "Autonomy"),
        ("ExpectedOutputCard", "Expected Output"),
    ]:
        check(f"AgentContentView no longer renders {label} (ADR-412 D5)", needle not in agent_src)


def test_redirect_stubs() -> None:
    print("\n[stubs] old routes are ADR-308 server redirects to their live home")
    # Every stub is pure server transport (ADR-308): `redirect()`, never 'use client'.
    # The targets are the LIVE homes (2026-09-12), one per retired route.
    STUBS = {
        "billing": "/workspace-settings?workspace-settings.pane=billing",          # ADR-491 D1
        "usage": "/workspace-settings?workspace-settings.pane=usage",              # ADR-491 D1
        "budget": "/workspace-settings?workspace-settings.pane=usage",             # ADR-491 D3: budget IS usage
        "notification-settings": "/settings?settings.pane=notification-settings",  # the account window
        "program": "/workspace-settings",                                          # dormant — bare door, no dead pane param
        "connectors": "/reach?reach.pane=connected",                               # ADR-645: Reach owns the connection acts
        "sources": "/chat",                                                        # stage internal (ADR-592)
    }
    for slug, target in sorted(STUBS.items()):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        check(f"/{slug} stub exists (a route that left the roster keeps its bookmark, ADR-592)", bool(stub))
        check(f"/{slug} → {target}", f"redirect('{target}')" in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)
    # ADR-421: the mandate/identity/principles route stubs survive for BOOKMARK
    # SAFETY only — their panes were removed (dormant), so they redirect to the
    # bare Settings door (default pane), NOT a dead ?pane= param.
    for slug in ("mandate", "identity", "principles"):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        check(f"/{slug} → /workspace-settings (no dead pane param — ADR-421)",
              "redirect('/workspace-settings')" in stub
              and f"pane={slug}" not in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)

def test_window_manager_resolution() -> None:
    print("\n[nav] foregroundSurface resolves pane-grade slugs")
    src = _read("lib/shell/useSurfacePreferences.tsx")
    check("pane resolution wrapper present", "pane_of" in src and "foregroundWindowGrade" in src)
    # ADR-358 D5+D6: the pane is delivered by setting the parent window's
    # NAMESPACED pane key (`{parent}.pane`) on the CURRENT pathname via
    # history.replaceState (preserving the /desktop baseline), not by
    # router.push-ing the parent's page route. Assert the durable behavior —
    # the pane is delivered to the PARENT window via reconcileUrl, which
    # namespaces it under {parent}.pane (scopeParamKey + searchParams.set
    # internally) and persists, without a pathname flip.
    check(
        "pane delivered via reconcileUrl(parentSlug, { pane: slug }) — namespaced, no pathname flip",
        "reconcileUrl(parentSlug, { pane: slug" in src,
    )
    check(
        "reconcileUrl namespaces params via scopeParamKey + searchParams.set",
        "url.searchParams.set(scopeParamKey(" in src,
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
