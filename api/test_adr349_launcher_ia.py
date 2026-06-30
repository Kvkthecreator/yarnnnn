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
    # D1/D3 — Workspace tier = the standing loop (Home + Notifications + Files
    # + Agents). Agents upgraded (D3).
    # ADR-370 (2026-06-25): the boundary composition joins the primary tier,
    # inheriting the slot the Feed vacated. ADR-385 (2026-06-29): that surface
    # is `channels` (renamed from `context`). ADR-385 follow-on (2026-06-30):
    # the legacy `context`/`feed` alias rows are DELETED, so the live primary
    # perception surface is `channels`.
    check(
        "primary == {home, channels, notifications, files, agents}",
        {s for s, t in tiers.items() if t == "primary"} == {"home", "channels", "notifications", "files", "agents"},
        str(sorted(s for s, t in tiers.items() if t == "primary")),
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
    check("notifications stays primary (Workspace tier)", n.get("launcher_tier") == "primary")
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


def test_agents_upgraded() -> None:
    print("\n[agents] upgraded to the Workspace tier (D3)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    check("agents launcher_tier == primary", by_slug["agents"].get("launcher_tier") == "primary")


def test_launcher_groups() -> None:
    print("\n[launcher] three at-rest groups; Utilities gone (D4/D6)")
    src = _read("components/shell/Launcher.tsx")
    check("Workspace group", "label: 'Workspace'" in src and "tier: 'primary'" in src)
    check("Workspace Settings group", "label: 'Workspace Settings'" in src and "tier: 'workspace-config'" in src)
    check("System Settings group", "label: 'System Settings'" in src and "tier: 'system-config'" in src)
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
