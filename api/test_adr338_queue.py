"""ADR-338 D4.3 gate — queue page de-stub + NULL-diff visibility.

Two gaps closed:
  1. /queue was a stub pointing to the Feed. It is now a real browse surface:
     pending proposals grouped by family, each row opening the SINGULAR
     ProposalDetail modal (useProposalModal) so the diff / order ticket +
     reviewer reasoning are visible BEFORE approval.
  2. SubstrateDiff rendered nothing when the diff was absent, and an empty
     <pre> when `after` was empty/whitespace — the NULL-content WriteFile
     failure class the journey week surfaced (approved blind, executed empty).
     Both cases now render an explicit warning.

Source-assertion gate (ADR-236 Rule 3 — no JS test runner). The
SubstrateDiff render branches + the queue de-stub are asserted in source;
tsc --noEmit (run separately) guards type-coherence of the modal wiring.

Usage:
    cd api
    python test_adr338_queue.py
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


def test_substrate_diff_null_visibility() -> None:
    print("\n[null-diff] SubstrateDiff surfaces absent + empty-content writes")
    src = _read("components/tp/ProposalCard.tsx")
    # No-diff branch now warns instead of returning null silently.
    check(
        "no-diff case renders a warning (not silent return null)",
        "No diff available for this write" in src,
    )
    # Empty `after` (the NULL-content class) is detected + warned.
    check(
        "empty `after` detected",
        "afterIsEmpty" in src and "diff.after.trim() === ''" in src,
    )
    check(
        "empty-content write renders an explicit empty-content warning",
        "empty content" in src and "Reject unless" in src,
    )
    # Regression guard: the old silent `if (!diff) return null;` shape is gone.
    check(
        "old silent `if (!diff) return null;` removed",
        "if (!diff) return null;" not in src,
    )


def test_queue_de_stubbed() -> None:
    print("\n[de-stub] /queue is a real browse surface")
    src = _read("app/(authenticated)/queue/page.tsx")
    check("queue fetches pending proposals", "api.proposals.list('pending'" in src)
    check(
        "queue uses the SINGULAR modal path (useProposalModal)",
        "useProposalModal" in src,
    )
    check("rows open the proposal detail modal", "openProposal(p)" in src)
    check("modalElement rendered", "{modalElement}" in src)
    check("grouped by family (capital / substrate)", "'capital', 'substrate'" in src)
    check(
        "refresh on resolve (resolved row drops)",
        "onResolved" in src and "void load()" in src,
    )
    check("honest empty state", "Nothing awaiting your decision" in src)
    # Regression guard: the old stub copy is gone.
    check(
        "old stub copy removed (no longer points operators to Feed as the only path)",
        "A dedicated queue browser" not in src
        and "A richer dedicated queue view is a follow-on" not in src,
    )


def test_batch_deferral_logged() -> None:
    print("\n[discipline] batch handling deferral is logged, not silently dropped")
    src = _read("app/(authenticated)/queue/page.tsx")
    check(
        "batch deferral noted in source (no silent cap)",
        "Batch handling" in src and "deferred" in src,
    )


def main() -> int:
    print("=" * 70)
    print("ADR-338 D4.3 — queue de-stub + NULL-diff visibility gate")
    print("=" * 70)
    test_substrate_diff_null_visibility()
    test_queue_de_stubbed()
    test_batch_deferral_logged()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
