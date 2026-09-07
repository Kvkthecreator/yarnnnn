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
    # 2026-07-04 operator re-sort (step 2): Notifications is off the at-rest
    # launcher entirely (search-only) — the top-bar bell is the one
    # always-present door to this window on every screen size.
    check("launcher_tier == search-only (bell is the door)", op.get("launcher_tier") == "search-only")
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
    # ADR-642 (2026-09-07): `queue` LEFT this loop — the surface is ABSORBED by
    # Reach (its body mounts on Reach -> Leaving, boundary families only, and on
    # Notifications -> To do unfiltered; /queue is a redirect stub into that
    # pane).
    #
    # RULING 2026-09-07: the mirror loop is EMPTY and the concept is retired.
    # ADR-603 D5 (2026-08-24) deleted the recurrence concept and every member
    # surface of it (production held 0 declarations — retire-clean); standing
    # work is the standing declaration (ADR-639). This gate asserted for two
    # weeks that a deleted surface was still navigable, and was red the whole
    # time. There is nothing to re-anchor onto: a mirror this ADR fronts must
    # exist to be fronted. What survives is the ABSORPTION contract for the one
    # mirror that was genuinely absorbed rather than deleted.
    check("queue is ABSORBED by Reach (ADR-642 D4): no roster row, a stub route",
          "queue" not in by_slug and "reach" in by_slug
          and "redirect(" in _read("app/(authenticated)/queue/page.tsx"))
    # Retired is not the same as deleted: the slug leaves the ROSTER, and the
    # route survives as an ADR-308 redirect stub so old bookmarks land somewhere
    # and middleware (whose protected set is roster-derived) still authenticates
    # the path. That pairing IS the retirement contract.
    check("recurrence left the served roster (ADR-603 D5)",
          "recurrence" not in by_slug)
    check("/recurrence survives as a redirect stub, not a live window",
          "redirect(" in _read("app/(authenticated)/recurrence/page.tsx")
          and "'use client'" not in _read("app/(authenticated)/recurrence/page.tsx"),
          "the retired route is either gone (breaks bookmarks) or still a real surface")

    # ADR-349: the fronted mirrors go search-only (summon by name, not browse)
    # — the Utilities tier dissolved; Notifications fronts them. ADR-385
    # follow-on (2026-06-30): `feed` was DELETED (full alias deletion with
    # `context`); the narrative is the Channels Flow pane and `/feed` is a
    # next.config redirect, so `feed` is no longer a registry slug.
    check("feed is no longer a registry slug (alias deleted, 2026-06-30)", "feed" not in by_slug)
    # ADR-642: the queue slug is gone; Reach (its absorber) is PRIMARY.
    check("reach is primary (absorbed the queue mirror, ADR-642)", by_slug.get("reach", {}).get("launcher_tier") == "primary")


def test_one_body_two_mounts() -> None:
    print("\n[reuse] panes reuse mirror bodies — one body, two mounts (ADR-340 D8 rule)")
    # QueueBody extracted + mounted by BOTH the mirror and the Operation pane.
    qbody = _read("components/queue/QueueBody.tsx")
    check("QueueBody component exists", "export function QueueBody" in qbody)
    check("QueueBody owns the proposal data-load", "api.proposals.list" in qbody)

    # ADR-642: /queue is a redirect stub, so the second mount of QueueBody is
    # Reach -> Leaving, not the retired mirror. One body, still two mounts.
    reach_page = _read("app/(authenticated)/reach/page.tsx")
    check("Reach mounts QueueBody on its Leaving pane (the absorbed mirror)",
          "QueueBody" in reach_page)

    # ADR-349 D2: the composition page renamed operation → notifications.
    op = _read("app/(authenticated)/notifications/page.tsx")
    check("Resolve pane mounts QueueBody", "QueueBody" in op)
    # ADR-410 D5 (2026-07-06): the Understand pane re-mounted from the
    # chat-narrative FeedSurface to the workspace-timeline workbench
    # (ActivityLedger) — same one-body discipline, new (correct) body.
    check("Understand pane mounts the timeline workbench (ADR-410 D5)",
          "ActivityLedger" in op)
    # ADR-639 (2026-09-04): the Tune pane mounts StandingWork. `RecurrenceList`
    # died with the recurrence concept (ADR-603 D5) — standing work is the
    # standing declaration, and its roster + Run now/Pause live here.
    check("Tune pane mounts StandingWork (ADR-639)", "StandingWork" in op)
    check("RecurrenceList is not resurrected", "RecurrenceList" not in op)
    # ADR-642: the Decide pane's escape hatch leads into Reach -> Leaving (the
    # absorber), not the retired /queue mirror. The recurrence hatch went with
    # its concept.
    check("the Decide pane offers an escape hatch into the absorbing surface",
          "Open Reach" in op and 'navigateToSurface("reach"' in op)
    check("mounts the shared SettingsPaneShell (Singular Implementation)",
          "SettingsPaneShell" in op and "fullBleed" in op)
    # ADR-639 renamed the third pane `tune` -> `standing` when the recurrence
    # tuner became the standing-work roster.
    check("three panes: resolve/understand/standing (ADR-639 renamed tune)",
          all(k in op for k in ('"resolve"', '"understand"', '"standing"')))


def test_registry_and_parity() -> None:
    print("\n[wiring] notifications in the FE registry + slug allowlist")
    reg = _read("components/shell/SurfaceRegistry.tsx")
    check("SurfaceRegistry maps notifications → NotificationsPage",
          "notifications: NotificationsPage" in reg and "NotificationsPage" in reg)
    desk = _read("types/surface.ts")
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
    # ADR-491 D1 (2026-07-28): billing re-homed from the account door to the
    # WORKSPACE door (authority-gated workspace governance). The assertion below
    # pinned the pre-491 account href and had been red since that re-home.
    check("billing warning → the workspace billing pane (ADR-491 D1)",
          "navigateToSurface('workspace-settings', { pane: 'billing' })" in src)
    # ADR-639 renamed the third pane; the bell's target union must not keep
    # offering a pane key that no longer exists (a silent no-op navigation).
    check("the bell's pane targets match the live pane keys (ADR-639)",
          "'tune'" not in src and "'standing'" in src)
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
