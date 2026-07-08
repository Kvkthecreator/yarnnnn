"""ADR-412 regression gate — three altitudes, three chromes (steps 1+2: D2–D5).

FE source-guards (the web/ package has no JS runner — ADR-350/367 gate shape):

  (a) The chat DRAWER is steward-only — no lane strip, no LanePanel import,
      no lanes API usage; exactly the steward ConversationPanel renders.
  (b) /chat is a real windowed surface — kernel registry row (primary tier,
      application register), FE union + SurfaceRegistry entry, the page
      renders ChatSurface (the redirect-stub lineage ended). The surface is
      work-first recents (updated_at sort, model as CHIP + filter facet,
      never model-first folders) and lists lanes via GET /api/lanes (the
      viewer's lanes in the acting workspace).
  (c) /agents renders no Freddie card and carries the governor frame line
      (step 2 — D5 roster purification).
  (d) The System Agent panes resolve into Workspace Settings (step 2 — the
      five registry rows re-homed pane_of agents → workspace-settings;
      redirect stubs + page mount follow).
  (e) ADR-411 lane MECHANICS untouched is asserted by test_adr411_lanes.py
      staying green — run both.
  (f) D6 ambient context — homed in the USERMENU (operator ruling
      2026-07-07: the menu, not fixed top-bar chrome): the Workspace
      section always renders once resolved (N=1 shows the single binding)
      with the who's-here roster read (membership, never presence) +
      Manage-access door, all off the module-cached viewer-layer fetches.
  (g) D6 grant-derived affordances — authoring/consequential affordances
      render per the viewer's WRITE-REGION coverage (useViewerGrant +
      GrantGate), NEVER a role enum: constitution-band drafts, the
      activation CTA, the Workspace Settings constitutional panes.

Run: .venv/bin/python api/test_adr412_chat_surface.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


def _read(rel: str) -> str:
    with open(os.path.join(REPO, rel)) as f:
        return f.read()


# =============================================================================
# (a) The drawer purified to the steward (D2)
# =============================================================================


def test_drawer_steward_only() -> None:
    print("\n[a] ChatDrawer is steward-only (ADR-412 D2)")
    src = _read("web/components/shell/chrome/ChatDrawer.tsx")

    _assert("LanePanel" not in src.replace("+ LanePanel", ""),
            "Drawer does not import/render LanePanel (comment mention allowed)")
    _assert("import { LanePanel }" not in src, "No LanePanel import")
    _assert("api.lanes" not in src, "No lanes API usage in the drawer")
    _assert("activeLane" not in src, "No lane-selection state in the drawer")
    _assert("ConversationPanel" in src, "The steward ConversationPanel renders")
    _assert("ADR-412 D2" in src, "The purification is attributed in-source")

    _assert(
        not os.path.exists(
            os.path.join(REPO, "web/components/shell/chrome/LanePanel.tsx")
        ),
        "LanePanel no longer lives in shell chrome",
    )


# =============================================================================
# (b) /chat is the lanes surface (D3 + D4)
# =============================================================================


def test_kernel_registry_row() -> None:
    print("\n[b1] Kernel registry — the `chat` surface row (D3)")
    from services.kernel_surfaces import KERNEL_SURFACES

    row = next((s for s in KERNEL_SURFACES if s["slug"] == "chat"), None)
    _assert(row is not None, "`chat` kernel surface declared")
    if row is None:
        return
    _assert(row["launcher_tier"] == "primary", "Chat is a primary launcher tile")
    _assert(row["register"] == "application", "Chat is an application-register window")
    _assert(row["route"] == "/chat", "Route is /chat (slug reclaimed)")
    _assert(row["substrate_paths"] == [], "Member-experience scope — no authored substrate paths")

    # D3's launcher note: Home · Chat · … — chat sits directly after home in
    # array order (array position within a tier is the at-rest display order).
    slugs = [s["slug"] for s in KERNEL_SURFACES]
    _assert(
        slugs.index("chat") == slugs.index("home") + 1,
        "Chat is second in the Workspace tier (immediately after Home)",
    )


def test_fe_registration() -> None:
    print("\n[b2] FE registration — union, registry, page")
    src = _read("web/types/desk.ts")
    union = src.split("export type KernelSurfaceSlug =", 1)[1].split(";", 1)[0]
    _assert("'chat'" in union, "`chat` in the KernelSurfaceSlug union")

    reg = _read("web/components/shell/SurfaceRegistry.tsx")
    _assert("chat: ChatPage" in reg, "SurfaceRegistry maps chat → ChatPage")

    page = _read("web/app/(authenticated)/chat/page.tsx")
    _assert("redirect(" not in page, "The redirect-stub lineage ended (no redirect())")
    _assert("ChatSurface" in page, "The page renders ChatSurface")


def test_surface_work_first() -> None:
    print("\n[b3] ChatSurface — work-first recents, model as chip (D4)")
    src = _read("web/components/chat-surface/ChatSurface.tsx")

    _assert("api.lanes" in src, "Surface lists lanes via the lanes API (viewer-scoped)")
    _assert("updated_at" in src, "Recency sort keys on updated_at (touched per turn)")
    _assert("modelFilter" in src, "Model FILTER facet exists (by-engine view on demand)")
    _assert(
        "groupBy" not in src and "modelGroups" not in src,
        "No model-first grouping (D4 — the model is never the namespace)",
    )
    _assert("modelLabel" in src, "The model renders as a labeled chip")
    _assert(
        "useSurfaceParam('chat')" in src,
        "Active lane deep-links via the window-namespaced chat.lane param",
    )
    _assert(
        os.path.exists(os.path.join(REPO, "web/components/chat-surface/LanePanel.tsx")),
        "LanePanel relocated to the chat-surface home",
    )
    _assert(
        "the shared memory" in src,
        "The ADR-411 contract is restated on the surface (guardrail copy)",
    )


# =============================================================================
# (c) The Agents roster purified (D5)
# =============================================================================


def test_roster_purified() -> None:
    print("\n[c] /agents roster is Altitude 3 only (ADR-412 D5)")
    page = _read("web/app/(authenticated)/agents/page.tsx")

    _assert("Systemic" not in page, "No Systemic section on the roster")
    _assert(
        "agent: 'freddie'" not in page and 'agent: "freddie"' not in page,
        "No Freddie card selection on the roster",
    )
    _assert("FREDDIE_PANE_KEYS" not in page, "The ADR-387 pane inference is gone")
    _assert(
        "governed by Freddie" in page,
        "The governor frame line renders (ADR-381 D5 — a line, not a seat)",
    )
    _assert(
        "!== 'freddie'" in page,
        "The freddie class is filtered from the roster (stale deep-links fall to list mode)",
    )

    view = _read("web/components/agents/AgentContentView.tsx")
    _assert(
        "function ReviewerDetail" not in view and "<ReviewerDetail" not in view,
        "ReviewerDetail deleted from AgentContentView (comment mentions allowed)",
    )
    _assert(
        "FREDDIE_PANE_GROUPS: PaneGroup" not in view and "renderFreddiePane" not in view,
        "The grouped Freddie pane shell left the view (comment mentions allowed)",
    )


# =============================================================================
# (d) The System Agent panes resolve into Workspace Settings (D5)
# =============================================================================


def test_system_agent_rehome() -> None:
    print("\n[d] System Agent panes live in Workspace Settings (ADR-412 D5)")
    from services.kernel_surfaces import KERNEL_SURFACES

    # ADR-418 (2026-07-08) purified the System Agent group to the steward's DIALS.
    # autonomy/budget stay pane_of workspace-settings + grouped System Agent;
    # identity/principles moved to the Constitution group (still pane_of
    # workspace-settings); expected-output went dormant (no pane_of).
    dials = {"autonomy", "budget"}
    for slug in sorted(dials):
        row = next((r for r in KERNEL_SURFACES if r["slug"] == slug), None)
        _assert(
            row is not None and row.get("pane_of") == "workspace-settings",
            f"`{slug}` is pane_of workspace-settings (was agents, ADR-387 §6.4 reversed)",
        )
        if row is not None:
            _assert(
                row.get("pane_group") == "System Agent",
                f"`{slug}` sits in the System Agent group (ADR-418: the steward's dials)",
            )
    for slug in ("identity", "principles"):
        row = next((r for r in KERNEL_SURFACES if r["slug"] == slug), None)
        _assert(
            row is not None and row.get("pane_of") == "workspace-settings"
            and row.get("pane_group") == "Constitution",
            f"`{slug}` moved to the Constitution group (ADR-418 — constitution mirror, not the steward's persona)",
        )
    eo = next((r for r in KERNEL_SURFACES if r["slug"] == "expected-output"), None)
    _assert(
        eo is not None and eo.get("pane_of") is None and not eo.get("route"),
        "`expected-output` is dormant (no pane_of, no route — ADR-418)",
    )
    _assert(
        not any(r.get("pane_of") == "agents" for r in KERNEL_SURFACES),
        "No registry pane is homed on the agents window anymore",
    )

    ws = _read("web/app/(authenticated)/workspace-settings/page.tsx")
    _assert("SYSTEM_AGENT_PANE_GROUP" in ws, "Workspace Settings mounts the System Agent group")
    _assert("renderSystemAgentPane" in ws, "Pane bodies render via the shared module")
    _assert(
        "const MOVED_TO_FREDDIE" not in ws,
        "The ADR-387 stale-bookmark net is deleted (comment mentions allowed)",
    )

    _assert(
        os.path.exists(os.path.join(REPO, "web/components/agents/SystemAgentPanes.tsx")),
        "SystemAgentPanes module exists (the extracted Singular Implementation)",
    )

    # ADR-418: autonomy/budget/principles/identity still deep-link to their pane.
    for route in ["autonomy", "budget", "principles", "identity"]:
        stub = _read(f"web/app/(authenticated)/{route}/page.tsx")
        _assert(
            f"workspace-settings.pane={route}" in stub and "agents.agent=freddie" not in stub,
            f"/{route} stub redirects into Workspace Settings",
        )
    # ADR-418: the /expected-output stub survives for bookmark safety but its pane
    # is gone (dormant) — it redirects to the Settings door with NO dead pane param.
    eo_stub = _read("web/app/(authenticated)/expected-output/page.tsx")
    _assert(
        "redirect('/workspace-settings')" in eo_stub
        and "workspace-settings.pane=expected-output" not in eo_stub,
        "/expected-output stub redirects to the Settings door (no dead pane param — ADR-418)",
    )


# =============================================================================
# (f) D6 — ambient commons context (which-workspace + who's-here)
# =============================================================================


def test_ambient_context() -> None:
    print("\n[f] D6 ambient context — which-workspace + who's-here, in the UserMenu")
    _assert(
        not os.path.exists(os.path.join(REPO, "web/components/shell/WorkspaceIndicator.tsx")),
        "the top-bar chip is deleted (operator ruling 2026-07-07 — menu, not fixed chrome)",
    )
    top = _read("web/components/shell/chrome/TopBarSurface.tsx")
    _assert("WorkspaceIndicator" not in top or "<WorkspaceIndicator" not in top,
            "no ambient chip mounts in the top bar")

    menu = _read("web/components/shell/UserMenu.tsx")
    _assert("memberships.length > 0" in menu and "memberships.length > 1" not in menu,
            "the Workspace section always renders once resolved (N=1 shows the single binding)")
    _assert("useWorkspaceMemberships" in menu and "useWorkspaceMembers" in menu,
            "both reads ride the module-cached viewer layer")
    _assert("peopleLabel" in menu, "the compact people-count sub-label exists (replaced the who's-here list 2026-07-08)")
    _assert("never presence" in menu, "membership-not-presence is stated in-source (ADR-373 rejection stands)")
    _assert("WebSocket" not in menu and "setInterval" not in menu,
            "no realtime/polling — membership is a slow fact")
    _assert("pane: 'members'" in menu or 'pane: "members"' in menu,
            "depth deep-links to Workspace Settings → Members (glance vs mirror)")

    viewer = _read("web/lib/workspace/viewer.ts")
    _assert("membershipsPromise" in viewer and "membersPromise" in viewer,
            "module-level caches — one fetch per page life")


# =============================================================================
# (g) D6 — grant-derived affordances (never a role enum)
# =============================================================================


def test_grant_derived_affordances() -> None:
    print("\n[g] D6 grant-derived affordances")
    viewer = _read("web/lib/workspace/viewer.ts")
    _assert("useViewerGrant" in viewer and "write_regions" in viewer,
            "the viewer's grant coverage derives from write_regions")
    _assert("covers" in viewer, "coverage check is region-based")

    gate = _read("web/components/workspace-concepts/GrantGate.tsx")
    _assert("useViewerGrant" in gate, "GrantGate rides the viewer grant")
    _assert("fieldset disabled" in gate or "<fieldset disabled" in gate,
            "read-only panes disable controls natively")
    _assert("Read-only" in gate, "the gap is EXPLICIT (banner names the region)")

    # The no-species-law twin: no affordance keys on the role enum.
    for rel in (
        "web/components/workspace-concepts/GrantGate.tsx",
        "web/components/library/HomeHeader.tsx",
        "web/components/library/kernel-home/HomeFrontPage.tsx",
    ):
        src = _read(rel)
        _assert("role ===" not in src and "role !==" not in src,
                f"{rel.split('/')[-1]} never keys on a role enum")

    home = _read("web/components/library/HomeHeader.tsx")
    _assert("useViewerGrant" in home and "constitution/" in home,
            "constitution-band drafts gate on constitution/ coverage")
    front = _read("web/components/library/kernel-home/HomeFrontPage.tsx")
    _assert("useViewerGrant" in front and "canActivate" in front,
            "the activation CTA gates on constitution/ coverage")
    ws = _read("web/app/(authenticated)/workspace-settings/page.tsx")
    _assert('GrantGate region="constitution/"' in ws,
            "the Mandate pane is grant-gated")
    # ADR-418: the System Agent panes are the steward's DIALS (governance/); the
    # persona/ panes (identity/principles) moved to the workspace-settings
    # Constitution group, where they gate on persona/ directly.
    sap = _read("web/components/agents/SystemAgentPanes.tsx")
    _assert("PANE_REGIONS" in sap and "governance/" in sap,
            "System Agent dial panes gate on governance/ (ADR-418)")
    _assert('GrantGate region="persona/"' in ws,
            "the constitution Identity/Principles panes gate on persona/ (ADR-418)")


if __name__ == "__main__":
    test_drawer_steward_only()
    test_kernel_registry_row()
    test_fe_registration()
    test_surface_work_first()
    test_roster_purified()
    test_system_agent_rehome()
    test_ambient_context()
    test_grant_derived_affordances()
    print("\n" + "=" * 60)
    print(f"ADR-412 gate: {_passed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
