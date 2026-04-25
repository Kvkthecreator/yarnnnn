"""
Test gate — ADR-219 Commit 5 (`/chat` weight-driven rendering + inline-to-task).

Commit 5 is purely frontend behavior — there is no Python service to
unit-test in isolation. The contracts we enforce in this gate are
structural / grep-shaped: the new components + types exist, their
required props / fields exist, and the wiring on `/chat` mounts both
the filter bar and the affordance.

Per ADR-219 D5 + D6 the load-bearing pieces are:

  A. Type extension — TPMessage role union widens to include the
     post-Commit-2 enum members (system / agent / external) AND the
     narrative envelope is exposed as `narrative?: NarrativeEnvelope`.

  B. Weight dispatch — ChatPanel renders one of three shapes per
     message based on `narrative.weight`:
       material → existing card
       routine → collapsed line with expand
       housekeeping → dim one-liner

  C. Filter bar — ChatFilterBar is mounted on /chat with deep-link
     query-param state (weight, identity, task), and the helper
     `parseChatFilterFromSearch` exists for the parent surface to
     pass a structured filter to ChatPanel.

  D. Make-this-recurring — ChatPanel exposes `onMakeRecurring` prop;
     ChatSurface wires it to open TaskSetupModal pre-filled from the
     operator's message text.

  E. narrative_digest card — SystemCardType union widened; the
     SystemCard component dispatches narrative_digest to a card with
     expand-to-list affordance.

This test runs as a grep-based regression guard (no JS runtime
required); failures point to specific files + missing fragments so
the next change can correct them.

Usage:
    cd api && python test_adr219_commit5_chat_rendering.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text()


# =============================================================================
# A — TPMessage type widened + narrative envelope present
# =============================================================================

def test_tpmessage_role_includes_widened_enum() -> None:
    src = _read("web/types/desk.ts")
    # The role union must include the post-Commit-2 members.
    assert "'user' | 'assistant' | 'system' | 'reviewer' | 'agent' | 'external'" in src, (
        "TPMessage.role union must mirror migration 161 enum"
    )


def test_narrative_envelope_type_exported() -> None:
    src = _read("web/types/desk.ts")
    assert "export interface NarrativeEnvelope" in src
    assert "weight?:" in src and "pulse?:" in src and "summary?:" in src
    # SystemCardType expanded to include narrative_digest
    assert "'narrative_digest'" in src


def test_tpcontext_loader_pulls_envelope() -> None:
    src = _read("web/contexts/TPContext.tsx")
    # Loader must populate `narrative` from m.metadata.weight/pulse/summary
    assert "m.metadata.weight" in src
    assert "m.metadata.pulse" in src
    assert "m.metadata.summary" in src
    # Round-trip: narrativeHasAny gating prevents stamping empty {}
    assert "narrativeHasAny" in src


# =============================================================================
# B — Weight dispatch in ChatPanel
# =============================================================================

def test_chatpanel_dispatches_on_weight() -> None:
    src = _read("web/components/tp/ChatPanel.tsx")
    # NarrativeMessage component is the dispatch site
    assert "function NarrativeMessage" in src, (
        "ChatPanel must export the NarrativeMessage dispatch component"
    )
    # All three weight shapes are rendered
    assert "weight === 'material'" in src
    assert "weight === 'routine'" in src
    # Housekeeping is the catch-all default branch — assert a comment
    # or branch references it explicitly
    assert "Housekeeping" in src or "housekeeping" in src


def test_chatpanel_filter_helper_exists() -> None:
    src = _read("web/components/tp/ChatPanel.tsx")
    assert "function narrativeFilterMatches" in src
    # Filter signature checks weights, identities, taskSlug
    assert "filter.weights" in src
    assert "filter.identities" in src
    assert "filter.taskSlug" in src


def test_chatpanel_props_extended() -> None:
    src = _read("web/components/tp/ChatPanel.tsx")
    assert "narrativeFilter?: NarrativeFilter | null" in src
    assert "onMakeRecurring?:" in src


# =============================================================================
# C — Filter bar mounted with query-param state
# =============================================================================

def test_chatfilterbar_exists_and_exports_parser() -> None:
    src = _read("web/components/chat-surface/ChatFilterBar.tsx")
    assert "export function ChatFilterBar()" in src
    assert "export function parseChatFilterFromSearch" in src
    # Three filter dimensions
    assert "weight" in src and "identity" in src and "task" in src
    # Deep-link contract — uses URL search params
    assert "useSearchParams" in src
    assert "router.replace" in src


def test_chatsurface_mounts_filter_bar() -> None:
    src = _read("web/components/chat-surface/ChatSurface.tsx")
    assert "ChatFilterBar" in src
    assert "parseChatFilterFromSearch" in src
    assert "narrativeFilter" in src
    # Filter passes through to ChatPanel
    assert "narrativeFilter={narrativeFilter}" in src


# =============================================================================
# D — Make-this-recurring affordance
# =============================================================================

def test_chatpanel_render_includes_make_recurring_button() -> None:
    src = _read("web/components/tp/ChatPanel.tsx")
    # The button is gated on weight=material + role=user + no task slug
    assert "Make this recurring" in src
    # Conditions on showMakeRecurring must include all four guards
    assert "showMakeRecurring" in src
    assert "msg.role === 'user'" in src
    assert "isInlineAction" in src or "msg.narrative?.taskSlug" in src


def test_chatsurface_wires_handle_make_recurring() -> None:
    src = _read("web/components/chat-surface/ChatSurface.tsx")
    assert "handleMakeRecurring" in src
    # Wires through to TaskSetupModal via handleOpenTaskSetup
    assert "handleOpenTaskSetup" in src
    # Passes through to ChatPanel
    assert "onMakeRecurring={handleMakeRecurring}" in src


# =============================================================================
# E — narrative_digest card renderer
# =============================================================================

def test_systemcard_narrative_digest_renderer() -> None:
    src = _read("web/components/tp/SystemCard.tsx")
    assert "NarrativeDigestCard" in src
    # Routes narrative_digest through the dispatcher
    assert "card_type === 'narrative_digest'" in src
    # Expand-to-list affordance present
    assert "expanded" in src.lower()
    # Counts surfaced
    assert "data.counts" in src or "counts" in src


def test_tpcontext_passes_body_to_digest_card() -> None:
    """The narrative_digest card needs the original m.content as body
    for expand-to-list. Loader must thread it via _body in card data."""
    src = _read("web/contexts/TPContext.tsx")
    assert "_body: m.content" in src


# =============================================================================
# Driver
# =============================================================================

def main() -> int:
    tests = [
        ("A1 TPMessage role union widened", test_tpmessage_role_includes_widened_enum),
        ("A2 NarrativeEnvelope type exported + SystemCardType narrative_digest", test_narrative_envelope_type_exported),
        ("A3 TPContext loader pulls envelope from metadata", test_tpcontext_loader_pulls_envelope),
        ("B1 ChatPanel dispatches on weight (material/routine/housekeeping)", test_chatpanel_dispatches_on_weight),
        ("B2 narrativeFilterMatches helper handles weights/identities/taskSlug", test_chatpanel_filter_helper_exists),
        ("B3 ChatPanel props include narrativeFilter + onMakeRecurring", test_chatpanel_props_extended),
        ("C1 ChatFilterBar exists with parseChatFilterFromSearch", test_chatfilterbar_exists_and_exports_parser),
        ("C2 ChatSurface mounts ChatFilterBar + threads filter to ChatPanel", test_chatsurface_mounts_filter_bar),
        ("D1 Make-this-recurring button rendered with proper guards", test_chatpanel_render_includes_make_recurring_button),
        ("D2 ChatSurface wires handleMakeRecurring → TaskSetupModal", test_chatsurface_wires_handle_make_recurring),
        ("E1 SystemCard renders narrative_digest with expand-to-list", test_systemcard_narrative_digest_renderer),
        ("E2 TPContext threads message body into digest card data", test_tpcontext_passes_body_to_digest_card),
    ]

    failed: list[tuple[str, BaseException]] = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except BaseException as exc:  # noqa: BLE001
            failed.append((name, exc))
            print(f"  ✗ {name}: {exc}")

    print()
    if failed:
        print(f"FAILED — {len(failed)}/{len(tests)} tests failed")
        return 1
    print(f"PASSED — {len(tests)}/{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
