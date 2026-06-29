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
    src = _read(_file("agents", "freddie_agent.py"))
    # Negative: bullet must be gone
    assert "signal hasn't fired" not in src.lower(), (
        "Kernel persona frame still contains 'signal hasn't fired' bullet — "
        "this is alpha-trader instance vocabulary leaked into the kernel "
        "per ADR-290 D1. Should be deleted."
    )


def test_kernel_persona_frame_clarify_rare_universal_bullets_preserved():
    """Post-ADR-306 collapse: the when-to-Clarify universal bullets (data
    stale, track record thin, unsure-between-two-actions) are a *rule of
    judgment* and relocate from the persona-frame to `principles.md` (both
    bundles), per `agent-composition.md` §3.2.1 inverted boundary. The
    reasoning shapes are preserved — only their home moved from system prose
    to operator/bundle substrate (rendered every wake under "## principles.md
    — Your framework").

    The frame keeps only the compressed action-grammar line ("Close every
    cycle with a verdict or a standing_intent write"); the discipline that
    governs *when to Clarify rather than decide* now lives in principles.md.
    """
    bundles = {
        "alpha-trader": _bundle("review", "principles.md"),
        # alpha-author lives under a sibling bundle dir; resolve from repo root
        "alpha-author": REPO_ROOT.joinpath(
            "docs", "programs", "alpha-author", "reference-workspace",
            "review", "principles.md",
        ),
    }
    for name, path in bundles.items():
        src = _read(path).lower()
        assert "data is stale" in src, (
            f"{name} principles.md must carry the 'data is stale' Clarify-rare "
            "trigger (universal reasoning shape relocated from the persona "
            "frame per ADR-306)."
        )
        assert "track record is thin" in src, (
            f"{name} principles.md must carry the 'track record is thin' "
            "Clarify-rare trigger (relocated from the persona frame per ADR-306)."
        )
        assert "unsure between two reasonable actions" in src, (
            f"{name} principles.md must carry the 'unsure between two "
            "reasonable actions' Clarify-rare trigger (relocated from the "
            "persona frame per ADR-306)."
        )


# -----------------------------------------------------------------------------
# D2 — standing-intent every-cycle contract single-instance
# -----------------------------------------------------------------------------

def test_kernel_persona_frame_carries_standing_intent_contract():
    """D2 positive, post-ADR-306 collapse: the canonical declaration of the
    standing-intent substrate-home + every-cycle write contract is substrate
    pedagogy and relocates from the persona frame to `_workspace_guide.md`
    (ADR-281's home, Phase C). Single-instance is preserved — the verbose
    contract has exactly ONE home (the guide), the negative tests below still
    enforce zero restatement in IDENTITY.md / principles.md / recurrences.yaml.

    The frame retains only the compressed action-grammar line ("Close every
    cycle with a verdict or a standing_intent write") — the runtime-interface
    residue, not the substrate pedagogy.
    """
    guides = {
        "alpha-trader": REPO_ROOT.joinpath(
            "docs", "programs", "alpha-trader", "reference-workspace",
            "_workspace_guide.md",
        ),
        "alpha-author": REPO_ROOT.joinpath(
            "docs", "programs", "alpha-author", "reference-workspace",
            "_workspace_guide.md",
        ),
    }
    for name, path in guides.items():
        guide = _read(path)
        assert "is where your forward-looking" in guide, (
            f"{name} _workspace_guide.md must carry the standing-intent "
            "substrate-home declaration (relocated from the persona frame "
            "per ADR-306 D3 — substrate pedagogy lives in the workspace guide)."
        )
        assert "Every judgment-mode cycle produces a `standing_intent.md` write" in guide, (
            f"{name} _workspace_guide.md must carry the every-judgment-mode-"
            "cycle commitment (relocated from the persona frame per ADR-306)."
        )
    # The frame keeps only the compressed close-cycle action-grammar line.
    src = _read(_file("agents", "freddie_agent.py"))
    assert "Close every cycle with a verdict or a standing_intent write" in src, (
        "Minimal frame must retain the compressed close-cycle action-grammar "
        "line (the runtime-interface residue of the standing-intent contract, "
        "ADR-306 D2)."
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
    assert "Every cycle authors `/workspace/persona/standing_intent.md`" not in src, (
        "Bundle principles.md still contains 'Every cycle authors "
        "/workspace/persona/standing_intent.md' — per ADR-290 D2 this "
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
        r"AND update /workspace/persona/standing_intent\.md with what's\s+close to firing",
        r"AND update /workspace/persona/standing_intent\.md with what would change\s+the assessment",
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


def test_principles_md_bootstrap_active_principal_clause():
    """D2-followup (2026-05-18), AMENDED 2026-05-29 for ADR-296 v2 D3 supersession.

    The Bootstrap-phase action archetype must close the passive-observation gap
    (Reviewer interprets "scheduler shows no heartbeat" as a reason to wait) by
    declaring the active-principal posture. ORIGINAL D2-followup phrased the
    mechanism as "Commission substrate via FireInvocation" — but ADR-296 v2 D3
    (2026-05-20) REMOVED FireInvocation from FREDDIE_PRIMITIVES: the Reviewer's
    authority is over cadence preference + standing intent, NOT over invoking
    upstream recurrences directly. The original assertion is retired here (it
    would re-introduce the action-grammar overreach that ADR-296 + the 2026-05-29
    composite-coherence fix correct — see agent-composition.md §3.2.2). The
    alpha-trader bundle was already updated to the ADR-296-coherent mechanism;
    this test now asserts THAT canon.
    """
    src = _read(_bundle("review", "principles.md"))
    # Positive: active-principal clause, ADR-296-coherent mechanism (cadence +
    # standing intent, NOT FireInvocation-commissioning).
    assert "Author cadence + standing intent when upstream substrate is missing" in src, (
        "Bootstrap-phase action archetype must declare the active-principal "
        "clause via the ADR-296 v2 D3 mechanism — author cadence + standing "
        "intent (NOT FireInvocation). The clause closes the passive-observation "
        "gap while honoring that the Reviewer authors cadence, does not "
        "commission unit-of-work fires directly."
    )
    # Negative: the retired FireInvocation-commissioning mechanism must be ABSENT
    # (re-introducing it would violate ADR-296 v2 D3 + composite-coherence §3.2.2).
    assert "Commission substrate via FireInvocation" not in src, (
        "alpha-trader principles.md must NOT teach FireInvocation-commissioning "
        "(ADR-296 v2 D3 removed it from Reviewer authority). If this string "
        "reappears it is a regression to pre-ADR-296 action-grammar overreach."
    )
    # Positive: anti-pattern callout (survives — passivity-is-failure is canon,
    # independent of the retired mechanism).
    assert "Anti-pattern" in src and "passive observation, not judgment" in src, (
        "Principles.md must explicitly name passive-observation-while-substrate-"
        "is-missing as an anti-pattern. This survives ADR-296 — only the "
        "mechanism (cadence-authoring, not FireInvocation) changed."
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
        # 2026-05-18 follow-up — active-principal clause
        # (amended 2026-05-29: ADR-296 v2 D3 supersedes FireInvocation mechanism)
        ("D3+: Bootstrap-phase active-principal clause (ADR-296-coherent)",
         test_principles_md_bootstrap_active_principal_clause),
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
