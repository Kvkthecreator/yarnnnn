"""ADR-340 D8 gate — Machinery consolidation (Activity → Recurrence pane).

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies
the Machinery fold: the `activity` surface becomes PANE-GRADE under
`recurrence` — registry `pane_of: "recurrence"`, the Runs (execution) lens
rendered inside the Recurrence window via the shared `ActivityLog` body,
declaration-led (Schedule lens is the window default), an ADR-308 redirect
stub on `/activity`, and Singular Implementation (one Activity body, not two).

Mirror discipline (ADR-340 §11/§12): the substrate read + route + deep-link
all survive; only the launcher tile count drops (Utilities 4 → 3). This is
the D4 shape (window-grade → pane-grade) applied to a Utilities pair.

Usage:
    cd api
    python test_adr340_d8_machinery_fold.py
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


def test_registry_pane_model() -> None:
    print("\n[registry] activity is pane-grade under recurrence")
    from services.kernel_surfaces import KERNEL_SURFACES, kernel_pane_slugs

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    check("activity carries pane_of: recurrence", by_slug["activity"].get("pane_of") == "recurrence")
    check("activity carries pane_group", bool(by_slug["activity"].get("pane_group")))
    check("activity is in the pane set", "activity" in kernel_pane_slugs())
    check(
        "activity is search-only (hidden at rest, flat-search findable)",
        by_slug["activity"].get("launcher_tier") == "search-only",
    )
    # The parent stays window-grade.
    check("recurrence is window-grade (no pane_of)", not by_slug["recurrence"].get("pane_of"))
    check("recurrence stays Utilities tier", by_slug["recurrence"].get("launcher_tier") == "utilities")
    # Substrate read preserved (mirror discipline — §11/§12). Activity's
    # substrate is the execution_events DB table → empty substrate_paths,
    # documented in the comment, same as Feed/Queue.
    check("activity route preserved (redirect-stub transport)", by_slug["activity"].get("route") == "/activity")

    # Utilities tier is now 3 (Setup · Recurrence · Agents), not 4 — Activity
    # left the at-rest launcher.
    utilities = {e["slug"] for e in KERNEL_SURFACES if e.get("launcher_tier") == "utilities"}
    check("Utilities tier folded to 3 (no activity)", "activity" not in utilities, f"utilities={sorted(utilities)}")


def test_shared_activity_body() -> None:
    print("\n[singular] one Activity body — the shared ActivityLog component")
    body = _read("components/activity/ActivityLog.tsx")
    check("ActivityLog component exists", bool(body))
    check("ActivityLog exports the shared body", "export function ActivityLog" in body)
    check("ActivityLog reads execution_events", "executionEvents" in body)
    check("ActivityLog takes a slugFilter prop (host-driven filter)", "slugFilter" in body)
    # The body must NOT re-implement its own URL param reading — the host
    # (Recurrence window) owns ?slug= and hands it down. Keeps one body.
    check("ActivityLog is host-driven (no useSearchParams of its own)", "useSearchParams" not in body)


def test_recurrence_two_lens() -> None:
    print("\n[lens] Recurrence window renders the two lenses (declaration-led)")
    src = _read("app/(authenticated)/recurrence/page.tsx")
    check("Recurrence imports the shared ActivityLog", "import { ActivityLog }" in src)
    check("?pane=activity selects the Runs lens", "'activity'" in src and "pane" in src)
    check("Schedule ↔ Runs lens toggle present", "Runs" in src and "Schedule" in src)
    check("lens toggle syncs URL via setSurfaceParams", "p.set({ pane" in src)
    # Declaration-led: the default (no ?pane=) is the Schedule lens — the
    # RecurrenceList / WorkDetail declaration view is unchanged.
    check("declaration lens is the default (RecurrenceList retained)", "RecurrenceList" in src)


def test_redirect_stub() -> None:
    print("\n[stub] /activity is an ADR-308 server redirect")
    stub = _read("app/(authenticated)/activity/page.tsx")
    check("/activity → /recurrence?recurrence.pane=activity", "/recurrence?recurrence.pane=activity" in stub)
    check("/activity stub uses server redirect()", "redirect(" in stub)
    check("/activity stub is server-side (no 'use client')", "'use client'" not in stub)
    check("/activity stub preserves ?slug= bookmark", "searchParams" in stub and "slug" in stub)
    # /backend (legacy rename ancestor) points straight at the canonical
    # destination — no double redirect through the now-stub /activity.
    backend = _read("app/(authenticated)/backend/page.tsx")
    check("/backend → /recurrence?recurrence.pane=activity (no double redirect)", "/recurrence?recurrence.pane=activity" in backend)


def test_registry_prune() -> None:
    print("\n[prune] SurfaceRegistry holds window-grade components only")
    reg = _read("components/shell/SurfaceRegistry.tsx")
    check("activity not window-mounted", "activity: ActivityPage" not in reg)
    check("ActivityPage import removed", "import ActivityPage" not in reg)
    check("recurrence still window-mounted", "recurrence: RecurrencePage" in reg)


def test_deeplinks_repointed() -> None:
    print("\n[links] in-app deep-links target the Runs lens, not the stub")
    # The primary "View runs →" deep-link from a Schedule row.
    rlist = _read("components/work/RecurrenceList.tsx")
    check("RecurrenceList 'View runs →' → /recurrence?recurrence.pane=activity", "/recurrence?recurrence.pane=activity" in rlist)
    check("RecurrenceList no longer points at /activity?slug=", "/activity?slug=" not in rlist)
    # Reviewer panel deep-links.
    rpanel = _read("components/agents/ReviewerActivityPanel.tsx")
    check("ReviewerActivityPanel → /recurrence?recurrence.pane=activity", "/recurrence?recurrence.pane=activity" in rpanel)
    check("ReviewerActivityPanel no longer points at /activity?slug=", 'href={`/activity?slug=' not in rpanel)
    # Feed overlay link.
    overlay = _read("components/feed-surface/WorkspaceContextOverlay.tsx")
    check("WorkspaceContextOverlay → /recurrence?recurrence.pane=activity", "/recurrence?recurrence.pane=activity" in overlay)
    # routes.ts constant repointed.
    routes = _read("lib/routes.ts")
    check("ACTIVITY_ROUTE repointed to the Runs lens", 'ACTIVITY_ROUTE = "/recurrence?recurrence.pane=activity"' in routes)


def main() -> int:
    print("ADR-340 D8 gate — Machinery consolidation (Activity → Recurrence pane)")
    test_registry_pane_model()
    test_shared_activity_body()
    test_recurrence_two_lens()
    test_redirect_stub()
    test_registry_prune()
    test_deeplinks_repointed()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
