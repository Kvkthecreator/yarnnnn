"""ADR-290 regression gate — Reviewer Lifecycle Posture + standing-intent single-instance + kernel persona-frame de-bundling.

Three structural invariants:

1. D1 — kernel persona frame no longer contains the bundle-specific "signal
   hasn't fired" example bullet. Same anti-pattern shape as ADR-288 Phase 3.
2. D2 — standing-intent every-cycle write contract is singular-instance:
   authoritative declaration in the kernel persona frame; ZERO restatements
   in alpha-trader bundle's IDENTITY.md, principles.md, or recurrences.yaml
   recurrence prompts.
3. D3 — alpha-trader principles.md contains an explicit `## Lifecycle Posture`
   section organizing the bootstrap-vs-steady-state phase rules + phase gates.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Make repo paths importable
API_DIR = Path(__file__).resolve().parent
REPO_ROOT = API_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _file(*parts: str) -> Path:
    """Resolve a path under api/ (no leading slash)."""
    return API_DIR.joinpath(*parts)


def _bundle(*parts: str) -> Path:
    """Resolve a path under docs/programs/alpha-trader/reference-workspace/."""
    return REPO_ROOT.joinpath(
        "docs", "programs", "alpha-trader", "reference-workspace", *parts
    )


# -----------------------------------------------------------------------------
# D1 — kernel persona frame bundle-leak deleted
# -----------------------------------------------------------------------------

def test_kernel_persona_frame_no_signal_fired_bullet():
    """D1: The 'signal hasn't fired (decide: stand down ...)' bullet in
    `_PERSONA_FRAME` was alpha-trader instance vocabulary leaked into the
    kernel. Same anti-pattern as ADR-288 Phase 3.
    """
    src = _read(_file("agents", "reviewer_agent.py"))
    # Negative: bullet must be gone
    assert "signal hasn't fired" not in src.lower(), (
        "Kernel persona frame still contains 'signal hasn't fired' bullet — "
        "this is alpha-trader instance vocabulary leaked into the kernel "
        "per ADR-290 D1. Should be deleted."
    )


def test_kernel_persona_frame_clarify_rare_universal_bullets_preserved():
    """D1 invariant preservation: the universal bullets in the Clarify-rare
    list (data stale, track record thin, unsure-between-two-actions) must
    remain. Only the bundle-specific 'signal hasn't fired' bullet was deleted.
    """
    src = _read(_file("agents", "reviewer_agent.py"))
    # Positive assertions — universal reasoning shapes preserved
    assert "data is stale" in src, (
        "'data is stale' bullet must remain in Clarify-rare list "
        "(universal Identity-layer reasoning shape)."
    )
    assert "track record is thin" in src, (
        "'track record is thin' bullet must remain in Clarify-rare list "
        "(universal Identity-layer reasoning shape)."
    )
    assert "unsure between two reasonable actions" in src, (
        "'unsure between two reasonable actions' bullet must remain "
        "in Clarify-rare list (universal Identity-layer reasoning shape)."
    )


# -----------------------------------------------------------------------------
# D2 — standing-intent every-cycle contract single-instance
# -----------------------------------------------------------------------------

def test_kernel_persona_frame_carries_standing_intent_contract():
    """D2 positive: the canonical declaration of the every-cycle standing-intent
    write contract must live in the kernel persona frame. The kernel is the
    sole authoritative declaration site per ADR-290 D2.
    """
    src = _read(_file("agents", "reviewer_agent.py"))
    # The kernel persona frame's "Your standing intent has a substrate home"
    # section + the four-section schema must be present.
    assert "Your standing intent has a substrate home" in src, (
        "Kernel persona frame must carry the canonical 'Your standing "
        "intent has a substrate home' declaration (ADR-290 D2 — single-"
        "instance authoritative source)."
    )
    # The every-judgment-mode-cycle commitment statement
    assert "Every judgment-mode cycle produces a standing_intent.md write" in src, (
        "Kernel persona frame must carry the every-judgment-mode-cycle "
        "commitment statement (ADR-290 D2)."
    )


def test_bundle_identity_md_no_standing_intent_restatement():
    """D2 negative: alpha-trader bundle's IDENTITY.md must not restate the
    universal every-cycle standing-intent write contract. IDENTITY.md is the
    persona character (Simons-style numbers-first), not a substrate-contract
    restatement.
    """
    src = _read(_bundle("review", "IDENTITY.md"))
    # Negative: the "Every judgment-mode cycle updates" paragraph must be gone
    assert "Every judgment-mode cycle updates" not in src, (
        "Bundle IDENTITY.md still contains 'Every judgment-mode cycle "
        "updates standing_intent.md' — this is the kernel-Identity-layer "
        "contract restated. Per ADR-290 D2, kernel persona frame is "
        "authoritative; bundle IDENTITY.md is persona character only."
    )
    # Negative: the "Standing intent — my forward-looking substrate" section
    # header must be gone (the section restates substrate semantics that
    # kernel persona frame already declares).
    assert "Standing intent — my forward-looking substrate" not in src, (
        "Bundle IDENTITY.md still contains the 'Standing intent — my "
        "forward-looking substrate' section. Per ADR-290 D2, this content "
        "lives in the kernel persona frame; IDENTITY.md should not restate it."
    )


def test_bundle_principles_md_no_standing_intent_restatement():
    """D2 negative: alpha-trader bundle's principles.md must not restate the
    every-cycle standing-intent write contract. Principles.md houses the
    framework (decision rules, hard rejections, phase gates); the universal
    Identity-layer substrate contract lives in the kernel persona frame.
    """
    src = _read(_bundle("review", "principles.md"))
    # Negative: the "Every cycle authors" paragraph must be gone
    assert "Every cycle authors `/workspace/review/standing_intent.md`" not in src, (
        "Bundle principles.md still contains 'Every cycle authors "
        "/workspace/review/standing_intent.md' — per ADR-290 D2 this "
        "restates the universal Identity-layer contract that lives in "
        "the kernel persona frame. Principles.md is framework, not "
        "substrate-contract restatement."
    )


def test_bundle_recurrences_no_standing_intent_trailing_clauses():
    """D2 negative: alpha-trader bundle's recurrence prompts must not contain
    trailing 'AND update standing_intent.md ...' clauses. The recurrence
    prompt declares what THIS cycle produces; the universal every-cycle
    standing_intent write is kernel persona-frame responsibility.
    """
    src = _read(_bundle("_recurrences.yaml"))
    # Negative: no trailing "AND update ... standing_intent.md" clauses
    # in recurrence prompts. We pattern-match the specific phrasings used
    # pre-ADR-290 to be precise (don't match against comments mentioning
    # standing_intent as context).
    bad_patterns = [
        r"AND update /workspace/review/standing_intent\.md with what's\s+close to firing",
        r"AND update /workspace/review/standing_intent\.md with what would change\s+the assessment",
        r"Standing down without updating standing_intent\.md leaves",
        r"standing_intent\.md update is unconditional",
    ]
    for pat in bad_patterns:
        m = re.search(pat, src, re.DOTALL)
        assert m is None, (
            f"Bundle _recurrences.yaml still contains a per-recurrence "
            f"standing_intent restatement matching pattern: {pat!r}. "
            f"Per ADR-290 D2, the every-cycle standing_intent.md write "
            f"contract is governed by the kernel persona frame, not by "
            f"individual recurrence prompts."
        )


# -----------------------------------------------------------------------------
# D3 — principles.md gains explicit Lifecycle Posture section
# -----------------------------------------------------------------------------

def test_principles_md_has_lifecycle_posture_section():
    """D3: alpha-trader bundle principles.md must contain an explicit
    `## Lifecycle Posture` top-level section header organizing the
    bootstrap-vs-steady-state phase rules.
    """
    src = _read(_bundle("review", "principles.md"))
    assert "## Lifecycle Posture" in src, (
        "Bundle principles.md must contain '## Lifecycle Posture' section "
        "header per ADR-290 D3 (organizes existing Bootstrap clause + "
        "Capital-EV thresholds as explicit phase action archetypes)."
    )


def test_principles_md_lifecycle_section_names_both_phases():
    """D3: the Lifecycle Posture section must name both Bootstrap phase
    and Steady-state phase explicitly, plus declare phase gates.
    """
    src = _read(_bundle("review", "principles.md"))
    # The section must declare both phases
    assert "### Bootstrap phase" in src, (
        "Lifecycle Posture section must declare '### Bootstrap phase' header."
    )
    assert "### Steady-state phase" in src, (
        "Lifecycle Posture section must declare '### Steady-state phase' header."
    )
    assert "### Phase gates" in src, (
        "Lifecycle Posture section must declare '### Phase gates' header "
        "naming explicit transition conditions between phases."
    )


def test_principles_md_bootstrap_clause_preserved():
    """D3 invariant preservation: the Bootstrap clause section (the rule
    statement implementing bootstrap-phase action archetype) must remain.
    The reorganization adds the phase header; it does not delete the rule.
    """
    src = _read(_bundle("review", "principles.md"))
    assert "## Bootstrap clause" in src, (
        "Bundle principles.md must still contain '## Bootstrap clause' "
        "section (the rule statement for bootstrap-phase action archetype). "
        "ADR-290 D3 is reorganization, not rule deletion."
    )


# -----------------------------------------------------------------------------
# Test runner
# -----------------------------------------------------------------------------

def main() -> int:
    tests = [
        ("D1: kernel frame no 'signal hasn't fired' bundle leak",
         test_kernel_persona_frame_no_signal_fired_bullet),
        ("D1: universal Clarify-rare bullets preserved",
         test_kernel_persona_frame_clarify_rare_universal_bullets_preserved),
        ("D2: kernel frame carries standing-intent contract (authoritative)",
         test_kernel_persona_frame_carries_standing_intent_contract),
        ("D2: bundle IDENTITY.md no restatement",
         test_bundle_identity_md_no_standing_intent_restatement),
        ("D2: bundle principles.md no restatement",
         test_bundle_principles_md_no_standing_intent_restatement),
        ("D2: bundle recurrences.yaml no trailing clauses",
         test_bundle_recurrences_no_standing_intent_trailing_clauses),
        ("D3: principles.md has Lifecycle Posture section",
         test_principles_md_has_lifecycle_posture_section),
        ("D3: Lifecycle Posture names both phases + gates",
         test_principles_md_lifecycle_section_names_both_phases),
        ("D3: Bootstrap clause section preserved (reorganization not deletion)",
         test_principles_md_bootstrap_clause_preserved),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}")
            print(f"      {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {name} — unexpected error")
            print(f"      {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"ADR-290 regression gate: {passed}/{passed+failed} assertions passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
