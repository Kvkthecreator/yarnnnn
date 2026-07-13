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
    # ADR-349 D4 re-split into two launcher doors: `settings` is the account /
    # User Settings door; `workspace-settings` is the operation door.
    # Renamed "System Settings" → "User Settings" (2026-07-08 naming-coherence
    # pass): the content is billing/usage/account (user_id-scoped, the human),
    # so the render name matches its content + the UserMenu item. Slug + route
    # unchanged (naming-drift policy — rename stops at the render layer).
    check("settings titled 'User Settings' (2026-07-08 rename)", by_slug["settings"]["title"] == "User Settings")
    check("workspace-settings titled 'Workspace Settings' (ADR-349 D4)", by_slug["workspace-settings"]["title"] == "Workspace Settings")
    # Containers are window-grade (not panes themselves).
    check("settings is window-grade (no pane_of)", not by_slug["settings"].get("pane_of"))
    check("workspace-settings is window-grade (no pane_of)", not by_slug["workspace-settings"].get("pane_of"))


def test_two_settings_tiers() -> None:
    print("\n[tier] two settings doors re-split (ADR-349 D4)")
    from services.kernel_surfaces import KERNEL_SURFACES

    tiers = {e["slug"]: e.get("launcher_tier") for e in KERNEL_SURFACES if e.get("route")}
    # ADR-349 D4: Workspace Settings (operation, workspace-config) above
    # System Settings (account, system-config). The ADR-347 `configure` lump
    # is retired.
    check(
        "workspace-settings → workspace-config tier (operation door)",
        tiers.get("workspace-settings") == "workspace-config",
        str({s: t for s, t in tiers.items() if "config" in str(t)}),
    )
    check("settings → system-config tier (account door)", tiers.get("settings") == "system-config")
    check("ADR-347 `configure` lump retired", not any(t == "configure" for t in tiers.values()))
    launcher = _read("components/shell/Launcher.tsx")
    check("Launcher group: Workspace Settings (workspace-config)",
          "label: 'Workspace Settings'" in launcher and "tier: 'workspace-config'" in launcher)
    check("Launcher group: User Settings (system-config)",
          "label: 'User Settings'" in launcher and "tier: 'system-config'" in launcher)


def test_pane_homing() -> None:
    print("\n[panes] panes fold into the one door (ADR-347, supersedes D6)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # ADR-387 §6.4 (2026-06-30) moved the agent-scoped governance panes to
    # Freddie's roster pane; ADR-412 D5 (2026-07-06) REVERSED it — the panes
    # live on the Settings door as the System Agent group. ADR-418 (2026-07-08)
    # PURIFIED that group to what the STEWARD actually owns (ADR-414 D2): the
    # two dials only.
    # ADR-426 (2026-07-09): the System Agent group carved out into its OWN door.
    # ADR-454 D4 (2026-07-13): that door is REVERSED (the ambient steward) —
    # budget/autonomy re-home pane_of → workspace-settings in the unbranded
    # "System" group; the system-agent row goes hidden (hide-not-delete).
    for slug in ("autonomy", "budget"):
        check(f"{slug} → Workspace Settings (ADR-454 D4)", by_slug[slug].get("pane_of") == "workspace-settings")
        check(f"{slug} grouped System (ADR-454 D4)", by_slug[slug].get("pane_group") == "System")
    check("system-agent row hidden (ADR-454 D4)", by_slug["system-agent"].get("hidden") is True)
    # ADR-421 — mandate/identity/principles are DORMANT: a workspace has no
    # constitution of its own (ADR-414 D6). They are per-agent concepts (surfaced
    # on the agent detail), so they leave the navigable set (no route, no pane_of).
    # ADR-418 — expected-output is likewise dormant (a hired agent's contract).
    # ADR-432 D2d (2026-07-09): `program` joins the dormant set — the
    # operator-facing hire pane is retired (zero hired-program grants; the hire
    # machinery stays, but the surface is non-navigable, like the constitution
    # surfaces above).
    for slug in ("mandate", "identity", "principles", "expected-output", "program"):
        check(f"{slug} is dormant (no pane_of)", by_slug[slug].get("pane_of") is None)
        check(f"{slug} is dormant (no route)", not by_slug[slug].get("route"))
    # ADR-425 (2026-07-09): Perception left Workspace Settings — `connectors` is
    # now pane_of settings (the account door: a credential is a human's account
    # object), grouped "Connections"; `sources` is HIDDEN (no pane_of, no operator
    # door — redirect stub only). (Was ADR-415 Perception-in-workspace-settings.)
    check("connectors → the account door (ADR-425)", by_slug["connectors"].get("pane_of") == "settings")
    check("connectors grouped Connections (ADR-425)", by_slug["connectors"].get("pane_group") == "Connections")
    check("sources is hidden (no pane_of — ADR-425 D2)", by_slug["sources"].get("pane_of") is None)
    check("sources is hidden (ADR-425 D2)", by_slug["sources"].get("hidden") is True)


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
    # ADR-358 D6: the pane is window-NAMESPACED (`{windowSlug}.pane`), synced
    # via useSurfaceParam(windowSlug).set({ pane }) — not the flat ?pane=.
    check("shell owns window-namespaced pane sync", "surfaceParam.set({ pane })" in shell)
    sys_src = _read("app/(authenticated)/settings/page.tsx")
    ws_src = _read("app/(authenticated)/workspace-settings/page.tsx")
    check("System Settings mounts the shell", "SettingsPaneShell" in sys_src)
    check("Workspace Settings mounts the shell", "SettingsPaneShell" in ws_src)
    # FE allowlist + registry cover workspace-settings (else the door can't open).
    desk = _read("types/desk.ts")
    check("desk.ts union includes 'workspace-settings'", "'workspace-settings'" in desk)
    reg = _read("components/shell/SurfaceRegistry.tsx")
    check("SurfaceRegistry maps workspace-settings", "'workspace-settings':" in reg and "WorkspaceSettingsPage" in reg)


def test_constitution_band_removed() -> None:
    # ADR-421 (2026-07-08): the Home constitution-link trio is REMOVED — a
    # workspace has no constitution of its own (ADR-414 D6); mandate/identity/
    # principles are per-agent, surfaced on the agent detail. The stubs survive
    # for bookmark safety but redirect to the bare Settings door (no dead pane).
    print("\n[band] constitution-link trio removed from Home (ADR-421)")
    home = _read("components/library/HomeHeader.tsx")
    check("HomeHeader no longer renders the ConstitutionLinks trio", "function ConstitutionLinks" not in home)
    for slug in ("mandate", "identity", "principles"):
        stub = _read(f"app/(authenticated)/{slug}/page.tsx")
        check(f"/{slug} → bare Settings door (no dead pane param, ADR-421)",
              "redirect('/workspace-settings')" in stub
              and f"pane={slug}" not in stub)
        check(f"/{slug} stub is server-side (no 'use client')", "'use client'" not in stub)


if __name__ == "__main__":
    test_two_container_surfaces()
    test_two_settings_tiers()
    test_pane_homing()
    test_registers_unchanged()
    test_shared_shell_singular_impl()
    test_constitution_band_removed()
    print(f"\n{'=' * 60}")
    print(f"  {PASSED} passed, {FAILED} failed")
    print(f"{'=' * 60}")
    sys.exit(1 if FAILED else 0)
