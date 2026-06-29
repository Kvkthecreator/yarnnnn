"""ADR-314: Substrate-Conditional Posture — the frame indexes intent, never asserts it.

Regression gate for the index-not-assert invariant (ADR-314 D2) + the
anti-rebloat discipline it enforces (ADR-306 D5 / FOUNDATIONS Derived Principle 22).

The frame must:
  - NOT restate substrate content (no "the operator already told you what to do")
  - index the governing files instead ("act on what they declare")
  - carry the standby-state reasoning (absent MANDATE → reason honestly, don't invent)
  - preserve the principal-shift (installed judgment, not an assistant)
  - stay minimal (single section, well under the pre-ADR-306 ~36K bloat)
"""

import re

from agents.reviewer_agent import _compute_minimal_frame, _build_system_prompt


def _flat(s: str) -> str:
    """Collapse newlines/runs-of-whitespace so prose assertions survive line-wrap."""
    return re.sub(r"\s+", " ", s)


def test_frame_does_not_assert_intent_exists():
    """ADR-314 D2: the deleted substrate-assertion must not return."""
    frame = _compute_minimal_frame()
    assert "already told you what to do" not in frame, (
        "ADR-314 violation: the frame restates MANDATE content. "
        "It must INDEX governance ('read your files; act on what they declare'), "
        "never ASSERT intent exists. The asserted form is false in the standby state."
    )


def test_frame_indexes_governance():
    """ADR-314 D2: index-not-assert — point at the files, don't paraphrase them."""
    frame = _flat(_compute_minimal_frame())
    assert "from what your governing files declare" in frame, (
        "ADR-314: the principal-shift must index the governing files "
        "('decide and direct from what your governing files declare')."
    )
    assert "When a header is present, act on its content" in frame, (
        "ADR-314 D2: present headers direct behavior — the index resolves to "
        "acting on header content."
    )
    # The frame still promises not to restate substrate (ADR-306 D5 / DP22).
    assert "does not restate them" in frame


def test_frame_carries_standby_state_reasoning():
    """ADR-314 D3 + ADR-383: an absent/empty header is reasoned about honestly,
    not a cue to invent intent.

    ADR-383 amendment (2026-06-29): MANDATE is no longer expected absent — every
    agent's MANDATE is populated (the bare workspace carries the steward-mandate
    default per ADR-383 §3 D3; a program overwrites it). So the frame no longer
    carries the MANDATE-specific 'not yet declared / activating a program' standby
    prose (that premise is superseded). What MUST survive is the GENERAL honest-
    about-absent-headers index-not-assert behavior — the frame still teaches the
    agent to reason honestly when ANY header is absent or empty rather than
    inventing intent. The index-not-assert invariant is unchanged; only the
    MANDATE-is-typically-absent premise changed."""
    frame = _flat(_compute_minimal_frame())
    assert "absent or empty" in frame and "reason honestly about that absence" in frame, (
        "ADR-314 (index-not-assert) + ADR-383: the frame must still teach the "
        "agent to reason honestly about an absent/empty header rather than invent "
        "intent. (The MANDATE-specific standby prose was retired by ADR-383 — "
        "MANDATE is now always populated, steward-default for a bare workspace.)"
    )


def test_principal_shift_preserved():
    """ADR-306 D1 preserved: the one thing that fights the assistant prior survives."""
    frame = _compute_minimal_frame()
    assert "installed judgment" in frame
    assert "NOT an assistant awaiting instruction" in frame


def test_frame_stays_minimal():
    """ADR-306 / DP22 anti-rebloat: the frame is a single small section, not the
    pre-collapse ~36K, 13-section shape. ADR-314 is subtractive — it must not grow it."""
    frame = _compute_minimal_frame()
    assert len(frame) < 8000, (
        f"frame is {len(frame)} chars — ADR-314 is subtractive; if it grew past "
        "the minimal envelope, the anti-rebloat constraint (DP22) is at risk."
    )


def test_system_prompt_assembles():
    """The whole system prompt still builds with the edited frame."""
    sp = _build_system_prompt()
    assert sp, "system prompt failed to assemble after the ADR-314 frame edit"
