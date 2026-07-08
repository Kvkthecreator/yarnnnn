"""ADR-340 P1 gate — attention center + status-cluster consolidation.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3 + the
ADR-300/327 gate precedent). Verifies the two P1 builds:

  A. The money-chip merge — BudgetStatusItem absorbs BalanceStatusItem
     (cluster 4 → 3; the absorbed file is DELETED per Singular
     Implementation).
  B. The AttentionCenter — a separate top-bar chrome item (Notification
     Center role, distinct from the SystemStatusCluster's Control Center
     role) whose every row is DERIVED from existing substrate endpoints
     and never stored (Derived Principle 29).

Usage:
    cd api
    python test_adr340_p1_attention.py
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


def test_status_cluster_retired() -> None:
    # 2026-07-08 (operator ruling): the SystemStatusCluster (Budget +
    # Connections standing-state chips) is RETIRED and the whole
    # system-status/ dir DELETED. Both glances fold into the UserMenu
    # (Budget = a usage row, Connectors = a link) — the top bar keeps only
    # the load-bearing items (Dock, bell, avatar). Supersedes the ADR-340 P1
    # money-chip merge (the merge is moot once the chip is gone).
    print("\n[cluster] SystemStatusCluster retired; glances fold into the UserMenu")
    check("system-status/ dir deleted", not (_WEB / "components/shell/system-status").exists())
    menu = _read("components/shell/UserMenu.tsx")
    check("UserMenu carries the Budget glance", "handleBudget" in menu and "deriveUsageMeter" in menu)
    check("UserMenu carries the Connectors link", "handleConnectors" in menu)
    check("UserMenu opens the /budget surface", "foregroundSurface('budget')" in menu)
    # The billing link lives on the Budget pane (BudgetCard) — unchanged by the
    # cluster retirement; billing is account config, not a menu-bar glance.
    card = _read("components/workspace-concepts/BudgetCard.tsx")
    check(
        "BudgetCard carries the Balance & billing link",
        "navigateToSurface('settings', { pane: 'billing' })" in card,
    )


def test_attention_center() -> None:
    print("\n[attention] AttentionCenter — derived, never stored (DP29)")
    src = _read("components/shell/AttentionCenter.tsx")
    check("AttentionCenter.tsx exists", bool(src))
    check("derives Decide from api.proposals.list", "api.proposals.list" in src)
    # ADR-410 D1 (2026-07-06): the Read derivation re-sourced — the chat
    # history was the viewer's PRIVATE thread post-ADR-407-Phase-4 (self-echo
    # in, peers invisible). The bell now derives from the workspace timeline,
    # peer-first (actor != viewer via the ADR-412 D6 viewer layer).
    check("derives Read from the workspace timeline (ADR-410 D1)",
          "api.workspace.timeline" in src and "api.chat.globalHistory(" not in src)
    check("Read is peer-first — self excluded via the viewer layer",
          "resolveActorForViewer" in src and "isSelf" in src)
    check("derives warnings from api.integrations.getLimits", "api.integrations.getLimits" in src)
    check(
        "last-seen cursor is client-side localStorage (presentation state, not substrate)",
        "localStorage" in src and "LAST_SEEN_KEY" in src,
    )
    check(
        "no substrate writes from the center (derived, never stored)",
        ".post(" not in src and "request<" not in src and "fetch(" not in src,
    )
    check(
        # ADR-346/349: rows deep-link into the Notifications composition (the
        # surface that CARRIES controls) via navigateToSurface, which writes
        # the ?pane= param. ADR-349 D2 renamed operation → notifications.
        "rows deep-link into Notifications via navigateToSurface (ADR-346/349)",
        "navigateToSurface('notifications'" in src,
    )
    check("Decide rows → Resolve pane", "goTo('resolve')" in src)
    check("Read rows → Understand pane", "goTo('understand')" in src)
    # 2026-06-19 label/temporal pass: the bell is a TEMPORAL triad (past ·
    # present · future), the glanceable head of the Operation surface, and
    # speaks the SAME operator words as the Operation panes.
    check("derives 'Coming up' (future limb) from recurrences", "api.recurrences.list" in src)
    check("'Coming up' is future-only, non-paused, soonest-first",
          "next_run_at" in src and "!r.paused" in src)
    check("'Coming up' rows → Schedule pane (goTo('tune'))", "goTo('tune')" in src)
    check("'Coming up' is derivation-only — NO new state (next_run_at rides the list)",
          "setUpcoming" in src and "request<" not in src)
    check("section headers match the Operation pane labels (To do / Activity / Coming up)",
          "To do" in src and "Activity" in src and "Coming up" in src)
    check("badge stays demand-only — Coming up does NOT inflate it",
          "proposals.length + unseenPeer.length" in src)


def test_topbar_mounts_attention() -> None:
    print("\n[topbar] TopBarSurface mounts AttentionCenter + UserMenu (cluster retired)")
    src = _read("components/shell/chrome/TopBarSurface.tsx")
    check("imports AttentionCenter", "import { AttentionCenter }" in src)
    check("mounts AttentionCenter", "<AttentionCenter />" in src)
    # 2026-07-08: the SystemStatusCluster is gone; the right region is just
    # bell + avatar. Order: AttentionCenter before UserMenu.
    check("no SystemStatusCluster mount", "<SystemStatusCluster />" not in src)
    check(
        "order: AttentionCenter before UserMenu",
        src.find("<AttentionCenter />") < src.find("<UserMenu"),
    )


def main() -> int:
    print("ADR-340 P1 gate — attention center (status-cluster retired 2026-07-08)")
    test_status_cluster_retired()
    test_attention_center()
    test_topbar_mounts_attention()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
