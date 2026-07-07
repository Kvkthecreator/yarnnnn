"""ADR-340 P4 gate — legibility fixes forced by the Stage-1 evaluation.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3).
Verifies the four evidence-forced P4 deltas (Stage-1 eval findings
F1/F2/F3 + the D6 widget-contract audit):

  F1 — Activity + Recurrence launcher summaries speak operator
       vocabulary (the two PARTIAL rows in the C1 read).
  F2 — consequence previews: Sources chain caption (the §7.1 worked
       example) + Autonomy live-pending preview in the confirm modal
       (the Night-Shift pattern, derived from live substrate, no new
       state).
  F3 — ONE shared proposal labeler (lib/proposal-labels.ts); the two
       pre-existing parallel implementations consolidated; all three
       proposal-rendering sites import it.
  D6 — the kernel Home slots carry the widget contract (state +
       deep-link into the act's surface) — audit found this already
       satisfied; the gate pins it.

Usage:
    cd api
    python test_adr340_p4_legibility.py
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


def test_f1_operator_summaries() -> None:
    print("\n[F1] launcher summaries speak operator vocabulary")
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    activity = by_slug["activity"]["summary"]
    recurrence = by_slug["recurrence"]["summary"]
    check("activity summary de-jargoned", "wake" not in activity and "dispatch" not in activity)
    check("activity summary answers when-to-visit", "machinery" in activity or "what it cost" in activity)
    check(
        "recurrence summary de-jargoned",
        "telemetry" not in recurrence and "substrate-event hook" not in recurrence,
    )
    check("recurrence summary answers when-to-visit", "schedule" in recurrence)


def test_f3_single_labeler() -> None:
    print("\n[F3] one shared proposal labeler, three consumers")
    lib = _read("lib/proposal-labels.ts")
    check("lib/proposal-labels.ts exists", bool(lib))
    check("substrate family labeled by path", "'substrate'" in lib and "path" in lib)
    check(
        "capital verb phrases present",
        "Submit a trade order" in lib and "platform_trading_submit_order" in lib,
    )
    for rel, label in [
        ("components/library/kernel-home/KernelDecisionQueue.tsx", "Home decision slot"),
        ("components/tp/ProposalCard.tsx", "chat ProposalCard"),
        ("components/shell/AttentionCenter.tsx", "AttentionCenter"),
    ]:
        src = _read(rel)
        check(f"{label} imports shared labeler", "proposalActionLabel" in src)
    # The two parallel implementations are GONE (singular implementation).
    kdq = _read("components/library/kernel-home/KernelDecisionQueue.tsx")
    check("KernelDecisionQueue inline map deleted", "PRIMITIVE_LABELS" not in kdq)
    pc = _read("components/tp/ProposalCard.tsx")
    check(
        "ProposalCard inline implementation collapsed to shared call",
        "replace(/^platform_/" not in pc,
    )
    ac = _read("components/shell/AttentionCenter.tsx")
    check("AttentionCenter no longer renders raw primitive slug", "${p.primitive}${" not in ac)


def test_f2_consequence_previews() -> None:
    print("\n[F2] consequence previews (the Night-Shift pattern)")
    sources = _read("components/workspace-concepts/SourcesCard.tsx")
    check(
        "Sources pane teaches the chain (declare → perception → Queue)",
        "perception" in sources and "Queue" in sources,
    )
    autonomy = _read("components/workspace-concepts/AutonomyCard.tsx")
    check("Autonomy fetches live pending for the preview", "api.proposals" in autonomy)
    check("live consequence per target level", "liveConsequence" in autonomy)
    check(
        "preview reaches the confirm modal (the switch moment)",
        "liveConsequence(pendingLevel)" in autonomy,
    )
    check(
        "derivation-only (no stored preview state)",
        "localStorage" not in autonomy,
    )


def test_d6_widget_contract_pinned() -> None:
    print("\n[D6] kernel Home slots: state + deep-link into the act")
    # Repointed 2026-07-07: the slots now deep-link via the SurfaceLink verb
    # (window-manager navigation), not raw href URLs. The decision slot's
    # /queue mirror was deliberately retired (ADR-367 D5) — depth lives at
    # Notifications → resolve.
    kdq = _read("components/library/kernel-home/KernelDecisionQueue.tsx")
    check(
        "decision slot deep-links to the resolve workbench",
        'to="notifications"' in kdq and "pane: 'resolve'" in kdq,
    )
    kra = _read("components/library/kernel-home/KernelRecentArtifacts.tsx")
    check("artifacts slot deep-links to Files", 'to="files"' in kra)
    kjt = _read("components/library/kernel-home/KernelJudgmentTrail.tsx")
    check(
        "judgment trail deep-links to its substrate",
        'to="files"' in kjt and "params={{ path:" in kjt,
    )
    hh = _read("components/library/HomeHeader.tsx")
    check("constitution band carries the mirror trio (P3)", "ConstitutionLinks" in hh)


def main() -> int:
    print("ADR-340 P4 gate — legibility fixes (Stage-1 eval F1/F2/F3 + D6 pin)")
    test_f1_operator_summaries()
    test_f3_single_labeler()
    test_f2_consequence_previews()
    test_d6_widget_contract_pinned()
    print(f"\n{PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
