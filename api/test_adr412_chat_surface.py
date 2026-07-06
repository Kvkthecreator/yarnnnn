"""ADR-412 step-1 regression gate — three altitudes, three chromes (D2 + D3 + D4).

FE source-guards (the web/ package has no JS runner — ADR-350/367 gate shape):

  (a) The chat DRAWER is steward-only — no lane strip, no LanePanel import,
      no lanes API usage; exactly the steward ConversationPanel renders.
  (b) /chat is a real windowed surface — kernel registry row (primary tier,
      application register), FE union + SurfaceRegistry entry, the page
      renders ChatSurface (the redirect-stub lineage ended). The surface is
      work-first recents (updated_at sort, model as CHIP + filter facet,
      never model-first folders) and lists lanes via GET /api/lanes (the
      viewer's lanes in the acting workspace).
  (e) ADR-411 lane MECHANICS untouched is asserted by test_adr411_lanes.py
      staying green — run both.

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


if __name__ == "__main__":
    test_drawer_steward_only()
    test_kernel_registry_row()
    test_fe_registration()
    test_surface_work_first()
    print("\n" + "=" * 60)
    print(f"ADR-412 step-1 gate: {_passed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
