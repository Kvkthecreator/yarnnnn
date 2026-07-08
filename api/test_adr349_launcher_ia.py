"""ADR-349 gate — Launcher IA re-sort.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies
the at-rest launcher = the standing loop + two settings doors, and the
operation → notifications rename.

IMPORTANT: run as a SCRIPT (`python test_adr349_launcher_ia.py`), not under
pytest — check() records failures via globals + sys.exit, which pytest does
not surface.

Usage:
    cd api
    python test_adr349_launcher_ia.py
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


def test_at_rest_launcher() -> None:
    print("\n[at-rest] standing loop + two settings doors (D1/D3/D4)")
    from services.kernel_surfaces import KERNEL_SURFACES

    tiers = {e["slug"]: e.get("launcher_tier") for e in KERNEL_SURFACES if e.get("route")}
    # D1/D3 — Workspace tier = the standing loop. Agents upgraded (D3).
    # ADR-370 (2026-06-25): the boundary composition joins the primary tier,
    # inheriting the slot the Feed vacated. ADR-385 (2026-06-29): that surface
    # is `channels` (renamed from `context`). ADR-385 follow-on (2026-06-30):
    # the legacy `context`/`feed` alias rows are DELETED, so the live primary
    # perception surface is `channels`.
    # 2026-07-01 (operator re-sort): Notifications LEAVES the primary loop for
    # its own bottom group (`notifications` tier) — it's the always-present
    # top-bar bell, so its at-rest primary tile was redundant. The Workspace
    # loop is now Home · Channels · Files · Agents.
    check(
        # ADR-412 D3 (2026-07-06): Chat joins the primary tier — the lanes
        # surface (Altitude 2's chrome home), a new capability's home, not a
        # re-sort of the ADR-349 set.
        # 2026-07-08 (operator focus): Agents LEAVES the primary loop → search-only
        # (see test_agents_deferred_from_primary). A3 "hire an agent" is the
        # deferred horizon (ADR-380 Rung-2 launch line); the launch AI surface is
        # the A2 chat lanes. So the primary loop is Home · Chat · Channels · Files.
        "primary == {home, chat, channels, files}",
        {s for s, t in tiers.items() if t == "primary"} == {"home", "chat", "channels", "files"},
        str(sorted(s for s, t in tiers.items() if t == "primary")),
    )
    # 2026-07-04 (operator re-sort, step 2): Notifications leaves the at-rest
    # launcher entirely — the top-bar bell is the always-present door, so any
    # launcher tile was redundant chrome. Search-only; summon by name.
    check(
        "notifications == search-only (2026-07-04 re-sort)",
        tiers.get("notifications") == "search-only",
        str(tiers.get("notifications")),
    )
    # D4 — two settings doors.
    check("workspace-config == {workspace-settings}",
          {s for s, t in tiers.items() if t == "workspace-config"} == {"workspace-settings"})
    check("system-config == {settings}",
          {s for s, t in tiers.items() if t == "system-config"} == {"settings"})
    # D6 — Utilities + the ADR-347 `configure` lump are gone.
    check("no `utilities` tier (dissolved, D6)", not any(t == "utilities" for t in tiers.values()))
    check("no `configure` tier (ADR-347 lump retired)", not any(t == "configure" for t in tiers.values()))


def test_mirrors_and_setup_search_only() -> None:
    print("\n[search-only] mirrors + Setup off the at-rest launcher (D1/D5/D6)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # D1/D6 — the fronted mirrors go search-only (summon by name, not browse).
    # ADR-385 follow-on (2026-06-30): `feed` is no longer a mirror row — it was
    # DELETED with `context` (full alias deletion); the narrative lives in the
    # Channels Flow pane and `/feed` is a next.config redirect. Removed from the
    # mirror loop.
    check("feed is no longer a registry slug (alias deleted, 2026-06-30)",
          "feed" not in by_slug)
    for slug in ("queue", "recurrence"):
        check(f"{slug} is search-only (fronted by Notifications)",
              by_slug[slug].get("launcher_tier") == "search-only")
        # Mirrors NOT deleted (ADR-346 D1) — still real windowed surfaces.
        check(f"{slug} keeps its route (not deleted)", bool(by_slug[slug].get("route")))
        check(f"{slug} stays window-grade (not absorbed)", not by_slug[slug].get("pane_of"))
    # D5 — Setup off the launcher, route preserved (re-enterable).
    check("setup is search-only (a motion you re-enter, D5)",
          by_slug["setup"].get("launcher_tier") == "search-only")
    check("setup keeps its route", bool(by_slug["setup"].get("route")))


def test_notifications_rename() -> None:
    print("\n[rename] operation → notifications (D2)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    check("notifications surface registered", "notifications" in by_slug)
    check("no 'operation' surface slug remains", "operation" not in by_slug)
    n = by_slug.get("notifications", {})
    check("notifications route == /notifications", n.get("route") == "/notifications")
    check("notifications title == 'Notifications'", n.get("title") == "Notifications")
    # 2026-07-04 re-sort: Notifications is off the at-rest launcher entirely
    # (search-only) — the top-bar bell is the one always-present door.
    check("notifications is search-only", n.get("launcher_tier") == "search-only")
    # FE wiring renamed.
    desk = _read("types/desk.ts")
    check("desk.ts slug union renamed to 'notifications'", "'notifications'" in desk and "| 'operation'" not in desk)
    reg = _read("components/shell/SurfaceRegistry.tsx")
    check("SurfaceRegistry maps notifications", "notifications: NotificationsPage" in reg)
    # Page moved; /operation is a redirect stub.
    check("notifications page exists", bool(_read("app/(authenticated)/notifications/page.tsx")))
    stub = _read("app/(authenticated)/operation/page.tsx")
    check("/operation → /notifications redirect stub (ADR-308)",
          "redirect('/notifications')" in stub and "'use client'" not in stub)


def test_bell_one_name() -> None:
    print("\n[bell] the topbar bell renamed to Notifications (D2 — one name)")
    src = _read("components/shell/AttentionCenter.tsx")
    check("bell title attr reads 'Notifications'", 'title="Notifications"' in src)
    check("bell footer reads 'Open Notifications →'", "Open Notifications →" in src)
    check("bell routes to the notifications surface", "navigateToSurface('notifications'" in src)
    check("no stale 'Open Operation' / route to operation",
          "Open Operation" not in src and "navigateToSurface('operation'" not in src)


def test_agents_deferred_from_primary() -> None:
    # ADR-349 D3 raised agents to the Workspace/primary tier. 2026-07-08 the
    # operator deferred it back to search-only: Altitude-3 "hire an agent" is the
    # deferred horizon (ADR-380 Rung-2 launch line; ADR-414 already removed
    # Freddie from this roster), and a second AI door beside /chat confused the
    # A2-hands-vs-A3-hire story. Roster stays URL-reachable + searchable; it just
    # leaves the launcher tiles + the dock. One-word revert re-surfaces A3.
    print("\n[agents] deferred from the primary tier → search-only (2026-07-08)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    check("agents launcher_tier == search-only", by_slug["agents"].get("launcher_tier") == "search-only")
    # NOT deleted — still a real windowed surface reachable by /agents.
    check("agents keeps its route (not deleted)", bool(by_slug["agents"].get("route")))
    check("agents stays window-grade", not by_slug["agents"].get("pane_of"))


def test_launcher_groups() -> None:
    print("\n[launcher] three at-rest groups; Utilities gone (D4/D6)")
    src = _read("components/shell/Launcher.tsx")
    check("Workspace group", "label: 'Workspace'" in src and "tier: 'primary'" in src)
    check("Workspace Settings group", "label: 'Workspace Settings'" in src and "tier: 'workspace-config'" in src)
    check("User Settings group", "label: 'User Settings'" in src and "tier: 'system-config'" in src)
    # 2026-07-04 re-sort: the Notifications launcher group is deleted — the
    # top-bar bell is the door; the surface is search-only.
    check("Notifications group deleted", "tier: 'notifications'" not in src)
    check("Utilities group removed", "label: 'Utilities'" not in src)
    check("un-tiered fallback hides at rest (no dead-group tile)", "?? null" in src)


def main() -> int:
    print("ADR-349 gate — launcher IA re-sort")
    test_at_rest_launcher()
    test_mirrors_and_setup_search_only()
    test_notifications_rename()
    test_bell_one_name()
    test_agents_upgraded()
    test_launcher_groups()
    print(f"\n{'=' * 60}")
    print(f"  {PASSED} passed, {FAILED} failed")
    print(f"{'=' * 60}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
