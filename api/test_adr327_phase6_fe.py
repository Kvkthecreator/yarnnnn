"""ADR-327 Phase 6 gate — frontend pace→budget collapse.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3 + the
ADR-300 gate precedent). Verifies the FE pace surface is deleted end-to-end
and the budget surface is wired.

Usage:
    cd api
    python test_adr327_phase6_fe.py
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


def test_pace_fe_deleted() -> None:
    print("\n[delete] pace FE files removed")
    check("PaceCard.tsx deleted", not (_WEB / "components/workspace-concepts/PaceCard.tsx").exists())
    check("content-shapes/pace.ts deleted", not (_WEB / "lib/content-shapes/pace.ts").exists())
    check("PaceStatusItem.tsx deleted", not (_WEB / "components/shell/system-status/PaceStatusItem.tsx").exists())


def test_budget_fe_present() -> None:
    print("\n[create] budget FE files present")
    check("budget.ts shape exists", (_WEB / "lib/content-shapes/budget.ts").exists())
    check("BudgetCard.tsx exists", (_WEB / "components/workspace-concepts/BudgetCard.tsx").exists())
    check("BudgetStatusItem.tsx exists", (_WEB / "components/shell/system-status/BudgetStatusItem.tsx").exists())
    check("/budget page exists", (_WEB / "app/(authenticated)/budget/page.tsx").exists())


def test_pace_redirect_stub() -> None:
    print("\n[redirect] /pace → /budget server stub (ADR-308)")
    src = _read("app/(authenticated)/pace/page.tsx")
    check("/pace page still exists (stub)", bool(src))
    check("server redirect to /budget", "redirect('/budget')" in src)
    check("NOT a client component (pure transport)", "'use client'" not in src)


def test_api_client_swap() -> None:
    print("\n[api] api.budget replaces api.pace")
    src = _read("lib/api/client.ts")
    check("api.budget defined", "budget: () =>" in src and "/api/budget" in src)
    # Precise: the api.pace namespace key was `\n  pace: () =>` (2-space indent).
    # (Avoid matching `clearWorkspace: () =>` which ends in "…pace: () =>".)
    check("api.pace removed", "\n  pace: () =>" not in src)
    check("no /api/pace reference", "'/api/pace'" not in src)


def test_registries_swapped() -> None:
    print("\n[registry] surface + content-shape registries swapped")
    desk = _read("types/desk.ts")
    check("'budget' in KernelSurfaceSlug", "| 'budget'" in desk)
    check("'pace' removed from slug union", "| 'pace'" not in desk)
    surf = _read("components/shell/SurfaceRegistry.tsx")
    # ADR-340 P2: budget is PANE-GRADE — no window component. It renders
    # as a Governance pane inside System Settings; /budget is an ADR-308
    # redirect stub. The ADR-327 substance (BudgetCard as the canonical
    # budget rendering, pace retired) is unchanged.
    check("budget not window-mounted (pane-grade per ADR-340 P2)", "budget: BudgetPage" not in surf)
    settings_page = _read("app/(authenticated)/settings/page.tsx")
    check("System Settings renders BudgetCard pane", "BudgetCard" in settings_page)
    check("pace removed from registry map", "pace: PacePage" not in surf)
    shapes = _read("lib/content-shapes/index.ts")
    check("budget shape registered", "budget: budgetMeta" in shapes)
    check("pace shape removed", "pace: paceMeta" not in shapes)


def test_status_cluster_swapped() -> None:
    print("\n[cluster] SystemStatusCluster mounts BudgetStatusItem")
    src = _read("components/shell/system-status/SystemStatusCluster.tsx")
    check("imports BudgetStatusItem", "import { BudgetStatusItem }" in src)
    check("mounts BudgetStatusItem", "<BudgetStatusItem />" in src)
    check("no PaceStatusItem import", "PaceStatusItem" not in src)


def test_icon_registered() -> None:
    print("\n[icon] wallet glyph for /budget")
    src = _read("lib/shell/surface-icons.tsx")
    check("wallet icon registered", "wallet: Wallet" in src)


def test_budget_shape_contract() -> None:
    print("\n[shape] budget.ts content-shape contract")
    src = _read("lib/content-shapes/budget.ts")
    check("SHAPE_KEY = 'budget'", "SHAPE_KEY = 'budget'" in src)
    check("PATH_GLOB → _budget.yaml", "_budget.yaml" in src)
    check("CANONICAL_L3 = 'BudgetCard'", "CANONICAL_L3 = 'BudgetCard'" in src)
    check("useCockpitBudget exported", "export function useCockpitBudget" in src)
    check("reads api.budget for utilization", "api.budget()" in src)
    check("writeShape('budget' ...) on mutate", "writeShape('budget'" in src)


def main() -> int:
    print("=" * 64)
    print("ADR-327 Phase 6 — frontend pace→budget collapse")
    print("=" * 64)
    test_pace_fe_deleted()
    test_budget_fe_present()
    test_pace_redirect_stub()
    test_api_client_swap()
    test_registries_swapped()
    test_status_cluster_swapped()
    test_icon_registered()
    test_budget_shape_contract()
    print("\n" + "=" * 64)
    print(f"  PASSED={PASSED}  FAILED={FAILED}")
    print("=" * 64)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
