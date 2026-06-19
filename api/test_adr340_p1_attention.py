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


def test_balance_chip_absorbed() -> None:
    print("\n[merge] Budget chip absorbs Balance chip (ADR-340 P1 Build A)")
    check(
        "BalanceStatusItem.tsx deleted",
        not (_WEB / "components/shell/system-status/BalanceStatusItem.tsx").exists(),
    )
    budget = _read("components/shell/system-status/BudgetStatusItem.tsx")
    check("BudgetStatusItem fetches the envelope (api.budget)", "api.budget()" in budget)
    check(
        "BudgetStatusItem fetches the balance (api.integrations.getLimits)",
        "api.integrations.getLimits()" in budget,
    )
    check("BudgetStatusItem keeps the /budget surface footer", "slug: 'budget'" in budget)
    check(
        "BudgetStatusItem carries the billing secondary footer",
        "secondaryFooterTarget" in budget and "/settings?pane=billing" in budget,
    )
    check(
        "low-balance thresholds preserved from the absorbed chip",
        "LOW_BALANCE_THRESHOLD_USD" in budget and "CRITICAL_BALANCE_THRESHOLD_USD" in budget,
    )


def test_cluster_is_three_chips() -> None:
    print("\n[cluster] SystemStatusCluster renders three chips, no Balance import")
    src = _read("components/shell/system-status/SystemStatusCluster.tsx")
    check("imports AutonomyStatusItem", "import { AutonomyStatusItem }" in src)
    check("imports BudgetStatusItem", "import { BudgetStatusItem }" in src)
    check("imports ConnectionsStatusItem", "import { ConnectionsStatusItem }" in src)
    check("no BalanceStatusItem import", "BalanceStatusItem" not in src)
    check(
        "cluster docstring names the AttentionCenter as a distinct chrome role",
        "AttentionCenter" in src,
    )


def test_popover_secondary_footer() -> None:
    print("\n[popover] StatusItemPopover supports an optional second footer")
    src = _read("components/shell/system-status/StatusItemPopover.tsx")
    check("secondaryFooterTarget prop declared", "secondaryFooterTarget?:" in src)
    check("secondaryFooterLabel prop declared", "secondaryFooterLabel?:" in src)
    check(
        "secondary footer renders conditionally",
        "secondaryFooterTarget && secondaryFooterLabel" in src,
    )


def test_attention_center() -> None:
    print("\n[attention] AttentionCenter — derived, never stored (DP29)")
    src = _read("components/shell/AttentionCenter.tsx")
    check("AttentionCenter.tsx exists", bool(src))
    check("derives Decide from api.proposals.list", "api.proposals.list" in src)
    check("derives Read from feed history", "globalHistory" in src)
    check(
        "Read derivation uses the ADR-219 weight taxonomy (material)",
        "weight !== 'material'" in src or "weight === 'material'" in src,
    )
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
        # ADR-346: rows now deep-link into the Operation composition (the
        # surface that CARRIES controls) via navigateToSurface, which writes
        # the ?pane= param — instead of bare foregroundSurface to the mirrors.
        "rows deep-link into Operation via navigateToSurface (ADR-346)",
        "navigateToSurface('operation'" in src,
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
          "proposals.length + unseenMaterial.length" in src)


def test_topbar_mounts_attention() -> None:
    print("\n[topbar] TopBarSurface mounts cluster + AttentionCenter + UserMenu")
    src = _read("components/shell/chrome/TopBarSurface.tsx")
    check("imports AttentionCenter", "import { AttentionCenter }" in src)
    check("mounts AttentionCenter", "<AttentionCenter />" in src)
    check(
        "order: cluster before AttentionCenter before UserMenu",
        src.find("<SystemStatusCluster />") < src.find("<AttentionCenter />") < src.find("<UserMenu"),
    )


def main() -> int:
    print("ADR-340 P1 gate — attention center + status-cluster consolidation")
    test_balance_chip_absorbed()
    test_cluster_is_three_chips()
    test_popover_secondary_footer()
    test_attention_center()
    test_topbar_mounts_attention()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
