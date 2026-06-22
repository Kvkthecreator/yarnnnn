"""ADR-284 Phase 2 regression gate: alpha-trader bundle amendments.

Phase 2 makes the standing-intent write contract load-bearing in the
bundle's IDENTITY + principles + judgment-mode recurrence prompts (per
ADR-284 D6). Phase 1 was kernel + canon; Phase 2 is bundle-side prose
amendments that direct the Reviewer to honor the canon clause in
practice.

Phase 2 scope confirmation per the ADR-284 D8 implementation table:
  - Bundle OCCUPANT.md template — N/A (kernel scaffolds via workspace_init
    Phase 5; ADR-284 Phase 1 helper overwrites with runtime occupant).
    The bundle does not ship OCCUPANT.md, so there's nothing to amend.
  - Bundle IDENTITY.md — amended with standing_intent.md reference
  - Bundle principles.md — amended with standing_intent.md under
    "Default posture: action"
  - Bundle _recurrences.yaml — judgment-mode prompts with stand-down
    clauses paired with "AND update standing_intent.md" instruction.
    Three sites: signal-evaluation, trade-proposal, outcome-reconciliation.

Deliverable-producing recurrences (pre-market-brief / weekly-performance-
review / quarterly-signal-audit) are not bundle-scaffolded post-ADR-275 —
the Reviewer authors them when reading _preferences.yaml. They don't have
stand-down clauses; each cycle produces a substantial composed deliverable
that IS the forward-looking artifact. Not in scope for Phase 2.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# ADR-320 constitution-region topological cut renamed review/ → persona/.
# This constant was stale (the dir no longer exists); fixed 2026-06-22 as part
# of the ADR-354 bundle-conformance impact sweep.
BUNDLE_REVIEW = REPO_ROOT / "docs/programs/alpha-trader/reference-workspace/persona"
BUNDLE_RECURRENCES = REPO_ROOT / "docs/programs/alpha-trader/reference-workspace/_recurrences.yaml"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# 1. IDENTITY.md — standing-intent reference
# -----------------------------------------------------------------------------

def test_identity_md_declares_standing_intent_substrate() -> None:
    src = _read(BUNDLE_REVIEW / "IDENTITY.md")
    assert "standing_intent.md" in src, (
        "bundle IDENTITY.md must reference standing_intent.md per ADR-284 D8"
    )
    assert "ADR-284" in src, (
        "bundle IDENTITY.md standing-intent section must cite ADR-284"
    )


def test_identity_md_enforces_every_cycle_update() -> None:
    src = _read(BUNDLE_REVIEW / "IDENTITY.md")
    assert "Every judgment-mode cycle updates standing_intent.md" in src, (
        "bundle IDENTITY.md must declare the every-cycle write contract — "
        "including no-fire cycles (per ADR-284 D2)"
    )


def test_identity_md_demands_specificity() -> None:
    """The whole point of standing_intent.md is forward-looking specificity
    (signal + ticker + threshold + distance). The IDENTITY must demand it
    explicitly — generic 'watching for opportunities' substrate defeats the
    purpose."""
    src = _read(BUNDLE_REVIEW / "IDENTITY.md")
    assert "Specifics matter" in src, (
        "bundle IDENTITY.md standing-intent section must demand specificity"
    )


def test_identity_md_lifecycle_no_actionable_branch_updated() -> None:
    """The 'no actionable conditions' branch of the lifecycle posture must
    now require a standing_intent.md update — the pre-ADR-284 'one sentence'
    answer alone is insufficient."""
    src = _read(BUNDLE_REVIEW / "IDENTITY.md")
    assert "update `standing_intent.md`" in src or "I update `standing_intent.md`" in src, (
        "IDENTITY.md no-actionable-conditions branch must direct a standing_intent update"
    )


# -----------------------------------------------------------------------------
# 2. principles.md — standing-intent under "Default posture: action"
# -----------------------------------------------------------------------------

def test_principles_md_declares_standing_intent_under_action_posture() -> None:
    src = _read(BUNDLE_REVIEW / "principles.md")
    # The amendment lives under the "Default posture: action" section.
    posture_idx = src.find("## Default posture: action")
    assert posture_idx != -1, "principles.md must have 'Default posture: action' section"
    # Look for the standing_intent declaration in the section body (within
    # the next ~3000 chars — section is short).
    section_window = src[posture_idx:posture_idx + 3000]
    assert "standing_intent.md" in section_window, (
        "principles.md 'Default posture: action' section must declare the "
        "standing_intent.md write contract per ADR-284 D8"
    )
    assert "ADR-284" in section_window, (
        "principles.md standing-intent declaration must cite ADR-284"
    )


def test_principles_md_distinguishes_judgment_from_observation() -> None:
    src = _read(BUNDLE_REVIEW / "principles.md")
    # The load-bearing semantic claim: a stand-down without updating
    # standing_intent.md is observation, not judgment.
    assert "not yet a judgment" in src.lower() or "is not yet" in src.lower(), (
        "principles.md must distinguish judgment (requires standing_intent "
        "update) from mere observation (no update)"
    )


# -----------------------------------------------------------------------------
# 3. _recurrences.yaml — judgment-mode prompts (SUPERSEDED by ADR-354)
# -----------------------------------------------------------------------------
# ADR-284 D6/D8 originally required each judgment-mode recurrence PROMPT to
# re-script "stand down → WriteFile standing_intent → ReturnVerdict". ADR-354
# (2026-06-22) INVERTED that: re-scripting the close in the prompt pre-empts the
# standing-obligation (DP30) reasoning the kernel frame owns (the concrete
# procedure beats the thin frame — the full-autonomy probe). ADR-284's GUARANTEE
# (no-fire cycles leave forward-looking evidence) is preserved — it now lives in
# the frame ("close every cycle with a verdict or a standing_intent write") and
# is enforced by `test_adr287_bundle_conformance.py::
# test_adr354_judgment_recurrences_do_not_rescript_the_close` (which asserts the
# INVERSE — the close-scripting markers are ABSENT). The three prompt-string
# tests that lived here (signal-evaluation / trade-proposal / outcome-
# reconciliation) are deleted per Singular Implementation; one of them already
# asserted on `trade-proposal`, a slug deleted by ADR-296. Enforcement moved
# home; the old home is removed, not duplicated.


# -----------------------------------------------------------------------------
# 4. Scope discipline — Phase 2 doesn't touch deliverable-producing recurrences
# -----------------------------------------------------------------------------

def test_deliverable_recurrences_unchanged() -> None:
    """Per ADR-275, deliverable-producing recurrences (pre-market-brief,
    weekly-performance-review, quarterly-signal-audit) are Reviewer-authored
    via _preferences.yaml, not bundle-scaffolded. ADR-284 Phase 2 must not
    re-introduce them to the bundle.
    """
    src = _read(BUNDLE_RECURRENCES)
    for slug in (
        "- slug: pre-market-brief",
        "- slug: weekly-performance-review",
        "- slug: quarterly-signal-audit",
    ):
        assert slug not in src, (
            f"Bundle _recurrences.yaml must not contain '{slug}' — it's "
            f"Reviewer-authored per ADR-275, not bundle-scaffolded. Phase 2 "
            f"scope discipline regression."
        )


# -----------------------------------------------------------------------------
# 5. Sibling-ADR regression — ADR-281 single-writer + Phase 1 envelope shape
# -----------------------------------------------------------------------------

def test_phase1_envelope_decls_still_present() -> None:
    """Phase 2 bundle amendments must not touch kernel envelope wiring."""
    api_root = REPO_ROOT / "api"
    src = (api_root / "services/reviewer_envelope.py").read_text(encoding="utf-8")
    from services.reviewer_envelope import _UNIVERSAL_ENVELOPE_DECLS
    keys = {entry[0] for entry in _UNIVERSAL_ENVELOPE_DECLS}
    assert "occupant_md" in keys, (
        "Phase 1's occupant_md envelope entry must still be present"
    )
    assert "standing_intent_md" in keys, (
        "Phase 1's standing_intent_md envelope entry must still be present"
    )


if __name__ == "__main__":
    test_identity_md_declares_standing_intent_substrate()
    test_identity_md_enforces_every_cycle_update()
    test_identity_md_demands_specificity()
    test_identity_md_lifecycle_no_actionable_branch_updated()
    test_principles_md_declares_standing_intent_under_action_posture()
    test_principles_md_distinguishes_judgment_from_observation()
    # Section 3 (prompt-string standing_intent tests) SUPERSEDED by ADR-354 —
    # enforcement moved to test_adr287_bundle_conformance.py (no-rescript invariant).
    test_deliverable_recurrences_unchanged()
    test_phase1_envelope_decls_still_present()
    print("ADR-284 Phase 2: 8/8 PASS (3 prompt-string tests superseded by ADR-354)")
