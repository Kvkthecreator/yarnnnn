"""ADR-346 gate — the Operation surface: a composition for Decide·Read·Tune.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies
the Operation composition is registered window-grade, fronts the three
operating-work mirrors as panes that REUSE the mirror bodies (one body, two
mounts — the ADR-340 D8 rule), the mirrors survive (NOT redirect stubs, NOT
pane-grade), Feed+Queue demoted to utilities, and the Attention bell lands on
the Operation panes (the surface that carries controls).

Usage:
    cd api
    python test_adr346_operation_composition.py
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


def _read(rel: str) -> str:
    p = _WEB / rel
    return p.read_text() if p.exists() else ""


def test_registry_window_grade() -> None:
    print("\n[registry] notifications is a window-grade primary composition")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # ADR-349 D2: operation → notifications (window + bell = one name).
    op = by_slug.get("notifications")
    check("notifications surface registered", op is not None)
    if not op:
        return
    check("window-grade (no pane_of — a composition, not a pane)", "pane_of" not in op)
    check("launcher_tier == primary (the default operating destination)", op.get("launcher_tier") == "primary")
    check("register == application (a windowed composition)", op.get("register") == "application")
    check("route == /notifications", op.get("route") == "/notifications")
    check("composes substrate (substrate_paths empty — owns no files)", op.get("substrate_paths") == [])
    check("archetype == dashboard", op.get("archetype") == "dashboard")


def test_mirrors_survive() -> None:
    print("\n[mirrors] Queue/Feed/Recurrence stay complete + reachable (ADR-346 D1)")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    # ADR-370 (2026-06-25): `feed` is no longer a standalone mirror window — it
    # folded into the Context boundary surface as its Flow lens (the renderer +
    # substrate survive; only the launcher home moved). So the "stays a real
    # window mirror" contract below now covers queue + recurrence only; feed's
    # new shape is asserted by the ADR-370 gate (`/feed` → redirect stub →
    # /context?context.pane=flow; the `feed` slug maps to ContextPage).
    for slug in ("queue", "recurrence"):
        e = by_slug.get(slug)
        check(f"{slug} still registered as a navigable surface", bool(e and e.get("route")))
        check(f"{slug} NOT pane-grade (stays a window mirror, not absorbed)", e is not None and "pane_of" not in e)

    # The mirrors must NOT become redirect stubs — they keep their real bodies.
    for slug in ("queue", "recurrence"):
        src = _read(f"app/(authenticated)/{slug}/page.tsx")
        check(f"/{slug} is a real surface, not a redirect stub",
              "'use client'" in src and "redirect(" not in src,
              "found redirect() — mirror was stubbed")

    # ADR-349: the fronted mirrors go search-only (summon by name, not browse)
    # — the Utilities tier dissolved; Notifications fronts them. ADR-385
    # follow-on (2026-06-30): `feed` was DELETED (full alias deletion with
    # `context`); the narrative is the Channels Flow pane and `/feed` is a
    # next.config redirect, so `feed` is no longer a registry slug.
    check("feed is no longer a registry slug (alias deleted, 2026-06-30)", "feed" not in by_slug)
    check("queue is search-only (fronted by Notifications)", by_slug["queue"].get("launcher_tier") == "search-only")
    check("recurrence is search-only (fronted by Notifications)", by_slug["recurrence"].get("launcher_tier") == "search-only")


def test_one_body_two_mounts() -> None:
    print("\n[reuse] panes reuse mirror bodies — one body, two mounts (ADR-340 D8 rule)")
    # QueueBody extracted + mounted by BOTH the mirror and the Operation pane.
    qbody = _read("components/queue/QueueBody.tsx")
    check("QueueBody component exists", "export function QueueBody" in qbody)
    check("QueueBody owns the proposal data-load", "api.proposals.list" in qbody)

    queue_page = _read("app/(authenticated)/queue/page.tsx")
    check("the /queue mirror mounts QueueBody", "QueueBody" in queue_page and "api.proposals.list" not in queue_page)

    # ADR-349 D2: the composition page renamed operation → notifications.
    op = _read("app/(authenticated)/notifications/page.tsx")
    check("Resolve pane mounts QueueBody", "QueueBody" in op)
    check("Understand pane mounts FeedSurface", "FeedSurface" in op)
    check("Tune pane mounts RecurrenceList", "RecurrenceList" in op)
    check("each pane offers an escape hatch into the full mirror",
          "Open full Queue" in op and "Open full Recurrence" in op)
    check("mounts the shared SettingsPaneShell (Singular Implementation)",
          "SettingsPaneShell" in op and "fullBleed" in op)
    check("three panes: resolve/understand/tune (keys unchanged through rename)",
          all(k in op for k in ('"resolve"', '"understand"', '"tune"')))


def test_registry_and_parity() -> None:
    print("\n[wiring] notifications in the FE registry + slug allowlist")
    reg = _read("components/shell/SurfaceRegistry.tsx")
    check("SurfaceRegistry maps notifications → NotificationsPage",
          "notifications: NotificationsPage" in reg and "NotificationsPage" in reg)
    desk = _read("types/desk.ts")
    check("notifications in KernelSurfaceSlug union", "'notifications'" in desk)
    check("notifications in KERNEL_SURFACE_SLUGS array", "'notifications'" in desk and "KERNEL_SURFACE_SLUGS" in desk)
    # /operation is an ADR-308 redirect stub → /notifications (bookmark safety).
    stub = _read("app/(authenticated)/operation/page.tsx")
    check("/operation → /notifications redirect stub", "redirect('/notifications')" in stub)


def test_attention_lands_on_operation() -> None:
    print("\n[bell] the Notifications bell routes into the Notifications panes")
    src = _read("components/shell/AttentionCenter.tsx")
    check("uses navigateToSurface (writes ?pane=)", "navigateToSurface('notifications'" in src)
    check("Decide rows → Resolve pane", "goTo('resolve')" in src)
    check("Read rows → Understand pane", "goTo('understand')" in src)
    check("footer relabeled Open Notifications →", "Open Notifications →" in src)
    check("billing warning still → System Settings billing pane", "/settings?pane=billing" in src)
    check("no longer routes to the bare queue/feed mirrors",
          "goTo('queue')" not in src and "goTo('feed')" not in src)


def main() -> int:
    print("ADR-346 gate — the Operation composition surface")
    test_registry_window_grade()
    test_mirrors_survive()
    test_one_body_two_mounts()
    test_registry_and_parity()
    test_attention_lands_on_operation()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
