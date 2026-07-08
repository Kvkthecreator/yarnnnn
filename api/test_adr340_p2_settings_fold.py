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
# ADR-387 §6.4 (2026-06-30) moved the agent-scoped governance panes to
# Freddie's roster pane; ADR-412 D5 (2026-07-06) REVERSED it — Freddie left
# the /agents roster, and the panes re-homed to Workspace Settings as the
# System Agent group.
# ADR-421 (2026-07-08): the Constitution group is REMOVED — a workspace has no
# constitution of its own (ADR-414 D6). mandate/identity/principles are dormant
# (per-agent concepts, surfaced on the agent detail). Only Program remains a
# workspace-content pane here.
WORKSPACE_SETTINGS_PANES = {
    "program",   # Operation
}
# ADR-418 (2026-07-08) PURIFIED the System Agent group to the STEWARD's dials
# (ADR-414 D2): autonomy + budget only.
FREDDIE_PANES = {
    "autonomy", "budget",              # governance/ dials — the steward's own
}
# ADR-421: the Constitution pane set is EMPTY — a workspace has no constitution.
CONSTITUTION_PANES = set()
# ADR-415 (2026-07-08): connectors + sources re-home from the dissolved
# Channels surface back to Workspace Settings → Perception (pane-grade).
PERCEPTION_PANES = {"connectors", "sources"}
# ADR-418: expected-output dormant. ADR-421: mandate/identity/principles dormant.
EXPECTED_PANES = WORKSPACE_SETTINGS_PANES | FREDDIE_PANES | CONSTITUTION_PANES | PERCEPTION_PANES


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
    # ADR-387 §6.4: Mandate + Program remain Workspace-Settings panes.
    for slug in sorted(WORKSPACE_SETTINGS_PANES):
        check(f"{slug}: pane_of == 'workspace-settings'", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    # ADR-412 D5 + ADR-418: the system agent's DIALS fold into Workspace Settings.
    for slug in sorted(FREDDIE_PANES):
        check(f"{slug}: pane_of == 'workspace-settings' (ADR-412 D5)", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    # ADR-418: identity + principles are pane_of workspace-settings (Constitution group).
    for slug in sorted(CONSTITUTION_PANES):
        check(f"{slug}: pane_of == 'workspace-settings' (ADR-418)", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    # ADR-418: expected-output dormant. ADR-421: mandate/identity/principles
    # dormant too (a workspace has no constitution of its own) — none pane-grade.
    for slug in ("expected-output", "mandate", "identity", "principles"):
        check(f"{slug} not pane-grade (dormant)", by_slug[slug].get("pane_of") is None)
    # ADR-415: connectors + sources re-home to Workspace Settings → Perception.
    for slug in sorted(PERCEPTION_PANES):
        check(f"{slug}: pane_of == 'workspace-settings' (ADR-415)", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug}: carries pane_group", bool(by_slug[slug].get("pane_group")))
    check(
        "settings is a container window (no pane_of on itself)",
        not by_slug["settings"].get("pane_of"),
    )
    check(
        "workspace-settings is a container window (no pane_of on itself)",
        not by_slug["workspace-settings"].get("pane_of"),
    )
    # ADR-349 D4: `settings` = the account door; `workspace-settings` = the operation door.
    # 2026-07-08 naming-coherence pass (commit 4c0518c): "System Settings" → "User Settings".
    check("settings titled 'User Settings'", by_slug["settings"]["title"] == "User Settings")
    check("workspace-settings titled 'Workspace Settings' (ADR-349 D4)", by_slug["workspace-settings"]["title"] == "Workspace Settings")
    check(
        "setup stays window-grade (Sequence surface, ADR-331)",
        not by_slug["setup"].get("pane_of"),
    )
    # ADR-418 grouping — the System Agent group is the steward's DIALS only.
    for slug in sorted(FREDDIE_PANES):
        check(f"{slug} grouped System Agent (ADR-418)", by_slug[slug]["pane_group"] == "System Agent")
    # ADR-415 (2026-07-08): Perception RETURNS to Workspace Settings —
    # connectors + sources re-home to the Perception group (Channels dissolved).
    check("connectors grouped Perception (ADR-415)", by_slug["connectors"]["pane_group"] == "Perception")
    check("sources grouped Perception (ADR-415)", by_slug["sources"]["pane_group"] == "Perception")
    # ADR-421: Workspace Settings keeps Program (Operation). The Constitution
    # group is removed (mandate/identity/principles dormant — per-agent, ADR-414 D6).
    check("program grouped Operation", by_slug["program"]["pane_group"] == "Operation")


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
    # ADR-421: Workspace Settings keeps Brand (D3 interim) + Program. The
    # Constitution panes (Mandate/Identity/Principles) were removed — a workspace
    # has no constitution of its own; those render on the agent detail.
    for needle, label in [
        ("ProgramLifecycleDrawer", "Program pane body"),
    ]:
        check(f"Settings door: {label}", needle in ws_src)
    check("Settings door Program pane carries re-run-setup door", "Re-run setup" in ws_src)
    # ADR-412 D5: the agent-scoped cards render on the Settings door again —
    # via the shared SystemAgentPanes module (a MOVE back, not a copy; the
    # AgentContentView mount is deleted — Singular Implementation).
    check(
        "Settings door mounts the System Agent group (ADR-412 D5)",
        "SYSTEM_AGENT_PANE_GROUP" in ws_src and "renderSystemAgentPane" in ws_src,
    )
    # ADR-418: SystemAgentPanes renders only the steward's DIALS (Autonomy,
    # Budget) + the read-only Freddie panels. Principles moved to the
    # workspace-settings Constitution group; Expected Output went dormant.
    panes_src = _read("components/agents/SystemAgentPanes.tsx")
    for needle, label in [
        ("BudgetCard", "Budget"),
        ("AutonomyCard", "Autonomy"),
    ]:
        check(f"SystemAgentPanes renders {label} (ADR-418)", needle in panes_src)
    for needle, label in [
        ("PrinciplesCard", "Principles (per-agent, ADR-421)"),
        ("ExpectedOutputCard", "Expected Output (dormant)"),
    ]:
        check(f"SystemAgentPanes no longer renders {label} (ADR-418)", needle not in panes_src)
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
    print("\n[stubs] old routes are ADR-308 server redirects to their pane home")
    # ADR-387 §6.4: Mandate + Program stubs still point to Workspace Settings.
    for slug in sorted(WORKSPACE_SETTINGS_PANES):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        if not stub:
            continue
        # ADR-358 D6: stubs redirect with the window-NAMESPACED pane param.
        target = f"/workspace-settings?workspace-settings.pane={slug}"
        check(f"/{slug} → {target}", f"redirect('{target}')" in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)
    # ADR-412 D5: the agent-scoped governance route stubs redirect into the
    # Settings door's System Agent group (the ADR-387 Freddie-pane targets
    # reversed).
    for slug in sorted(FREDDIE_PANES):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        if not stub:
            continue
        target = f"/workspace-settings?workspace-settings.pane={slug}"
        check(f"/{slug} → {target} (ADR-412 D5)", f"redirect('{target}')" in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)
    # ADR-415: the Perception routes redirect to Workspace Settings.
    for slug in sorted(PERCEPTION_PANES):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        if not stub:
            continue
        target = f"/workspace-settings?workspace-settings.pane={slug}"
        check(f"/{slug} → {target} (ADR-415)", f"redirect('{target}')" in stub)
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
