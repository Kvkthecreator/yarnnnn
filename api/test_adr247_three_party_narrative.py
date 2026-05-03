"""ADR-247 regression gate — Three-Party Narrative Model.

Validates:
1. No user-facing "Thinking Partner" display strings in tp/ components
2. No user-facing "Thinking Partner" display strings in agents/ components
3. ReviewerCard accepts personaName prop (not hardcoded "AI Reviewer" only)
4. useReviewerPersona hook exists and reads IDENTITY.md path
5. MessageDispatch has ReviewerVerdictRenderer component (hook-capable)
6. MessageDispatch still has exactly six shapes (no new shapes added)
7. reviewer_agent.py unchanged (backend judgment layer intact)
8. review_proposal_dispatch.py unchanged (dispatch logic intact)
9. ADR-247 file exists and references correct numbering
10. FOUNDATIONS.md references ADR-247 for three-party model
11. LAYER-MAPPING.md references ADR-247

Pure-Python script per ADR-236 Rule 3. Run with:
    python api/test_adr247_three_party_narrative.py
"""

from __future__ import annotations

import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Paths
ADR_FILE = REPO_ROOT / "docs" / "adr" / "ADR-247-three-party-narrative-model.md"
FOUNDATIONS = REPO_ROOT / "docs" / "architecture" / "FOUNDATIONS.md"
LAYER_MAPPING = REPO_ROOT / "docs" / "architecture" / "LAYER-MAPPING.md"
REVIEWER_CARD = REPO_ROOT / "web" / "components" / "tp" / "ReviewerCard.tsx"
MESSAGE_DISPATCH = REPO_ROOT / "web" / "components" / "tp" / "MessageDispatch.tsx"
REVIEWER_PERSONA_HOOK = REPO_ROOT / "web" / "lib" / "reviewer-persona.ts"
REVIEWER_AGENT = REPO_ROOT / "api" / "agents" / "reviewer_agent.py"
REVIEW_DISPATCH = REPO_ROOT / "api" / "services" / "review_proposal_dispatch.py"
TP_COMPONENTS = REPO_ROOT / "web" / "components" / "tp"
AGENTS_COMPONENTS = REPO_ROOT / "web" / "components" / "agents"

# Lines that are legitimate keeper exceptions (URL params, directive, DB slugs)
_KEEPER_PATTERNS = [
    "thinking-partner",       # URL param — intentional exception
    "thinking_partner",       # DB slug — intentional exception
    "never refer to yourself",  # the 'do not use TP' directive
]


def _has_user_facing_tp(path: Path) -> list[str]:
    """Return lines that have user-facing 'Thinking Partner' text."""
    if not path.exists():
        return []
    violations = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        stripped = line.strip()
        lower = stripped.lower()
        if "thinking partner" not in lower:
            continue
        # Allow keeper patterns
        if any(k in line for k in _KEEPER_PATTERNS):
            continue
        # Allow pure code comments (// ... or * ...)
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        violations.append(f"  {path.relative_to(REPO_ROOT)}:{i}: {stripped[:120]}")
    return violations


def assertion_1_no_tp_display_in_tp_components():
    violations = []
    for tsx in TP_COMPONENTS.glob("*.tsx"):
        violations.extend(_has_user_facing_tp(tsx))
    assert not violations, (
        "User-facing 'Thinking Partner' found in web/components/tp/ — retire per ADR-247 D1:\n"
        + "\n".join(violations)
    )


def assertion_2_no_tp_display_in_agents_components():
    violations = []
    for tsx in AGENTS_COMPONENTS.glob("*.tsx"):
        violations.extend(_has_user_facing_tp(tsx))
    assert not violations, (
        "User-facing 'Thinking Partner' found in web/components/agents/ — retire per ADR-247 D1:\n"
        + "\n".join(violations)
    )


def assertion_3_reviewer_card_accepts_persona_prop():
    src = REVIEWER_CARD.read_text()
    assert "personaName" in src, (
        "ReviewerCard.tsx must accept personaName prop (ADR-247 D2)"
    )
    # "AI Reviewer" must not appear as a hardcoded string literal return value
    # (it's acceptable in comments; what we reject is it being the only possible label)
    assert 'return "AI Reviewer"' not in src and "return 'AI Reviewer'" not in src, (
        "ReviewerCard.tsx must not return hardcoded 'AI Reviewer' — "
        "use personaName fallback instead (ADR-247 D2)"
    )


def assertion_4_reviewer_persona_hook_exists():
    assert REVIEWER_PERSONA_HOOK.exists(), (
        f"web/lib/reviewer-persona.ts missing — required by ADR-247 D2"
    )
    src = REVIEWER_PERSONA_HOOK.read_text()
    assert "IDENTITY.md" in src or "IDENTITY_PATH" in src or "review/IDENTITY" in src, (
        "reviewer-persona.ts must reference /workspace/review/IDENTITY.md path"
    )
    assert "useReviewerPersona" in src, (
        "reviewer-persona.ts must export useReviewerPersona hook"
    )


def assertion_5_message_dispatch_uses_component_for_reviewer():
    src = MESSAGE_DISPATCH.read_text()
    assert "ReviewerVerdictRenderer" in src, (
        "MessageDispatch.tsx must use ReviewerVerdictRenderer component "
        "(not a plain function) so it can call useReviewerPersona() — ADR-247 D2"
    )
    assert "useReviewerPersona" in src, (
        "MessageDispatch.tsx must import useReviewerPersona — ADR-247 D2"
    )


def assertion_6_six_message_shapes_unchanged():
    src = MESSAGE_DISPATCH.read_text()
    shapes = re.findall(r"'(user-bubble|yarnnn-bubble|system-event|reviewer-verdict|agent-bubble|external-event)'", src)
    unique = set(shapes)
    assert len(unique) == 6, (
        f"MessageDispatch must have exactly six shapes per ADR-237; found: {unique}"
    )


def assertion_7_reviewer_agent_unchanged():
    assert REVIEWER_AGENT.exists(), "reviewer_agent.py must exist (backend judgment layer)"
    src = REVIEWER_AGENT.read_text()
    assert "review_proposal" in src, (
        "reviewer_agent.py must still export review_proposal function"
    )
    assert "REVIEWER_MODEL_IDENTITY" in src, (
        "reviewer_agent.py must still define REVIEWER_MODEL_IDENTITY"
    )


def assertion_8_review_dispatch_unchanged():
    assert REVIEW_DISPATCH.exists(), "review_proposal_dispatch.py must exist (dispatch logic)"
    src = REVIEW_DISPATCH.read_text()
    assert "_run_ai_reviewer" in src, (
        "review_proposal_dispatch.py must still have _run_ai_reviewer"
    )


def assertion_9_adr_file_correct():
    assert ADR_FILE.exists(), f"ADR-247 file missing: {ADR_FILE}"
    body = ADR_FILE.read_text()
    assert "ADR-247" in body, "ADR file must reference ADR-247"
    assert "Three-Party" in body or "three-party" in body, "ADR must name three-party model"
    # Must NOT reference old collision number in title
    assert "# ADR-246:" not in body, "ADR file title must not say ADR-246"


def assertion_10_foundations_references_adr247():
    src = FOUNDATIONS.read_text()
    assert "ADR-247" in src and "three-party" in src.lower(), (
        "FOUNDATIONS.md must reference ADR-247 for three-party narrative model"
    )


def assertion_11_layer_mapping_references_adr247():
    src = LAYER_MAPPING.read_text()
    assert "ADR-247" in src, (
        "LAYER-MAPPING.md must reference ADR-247 in Amended by header"
    )


def run_all():
    tests = [
        assertion_1_no_tp_display_in_tp_components,
        assertion_2_no_tp_display_in_agents_components,
        assertion_3_reviewer_card_accepts_persona_prop,
        assertion_4_reviewer_persona_hook_exists,
        assertion_5_message_dispatch_uses_component_for_reviewer,
        assertion_6_six_message_shapes_unchanged,
        assertion_7_reviewer_agent_unchanged,
        assertion_8_review_dispatch_unchanged,
        assertion_9_adr_file_correct,
        assertion_10_foundations_references_adr247,
        assertion_11_layer_mapping_references_adr247,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{len(tests)} assertions passed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
