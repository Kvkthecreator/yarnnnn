"""ADR-323 regression gate — finish the persona-frame collapse (DP22).

Asserts the cockpit_awareness collapse:
  (a) build_filesystem_block is DELETED (no caller, no function).
  (b) _OPERATING_POSTURE is DELETED.
  (c) the composed system prompt (minimal frame + surviving cockpit tool block)
      is under a char ceiling (~10K — headroom; the pre-collapse was ~16.5K).
  (d) no substrate-pedagogy term ("When substrate is missing", "What NOT to
      write", "How you operate") appears in the composed system prompt — they
      live in _workspace_guide.md / principles.md now.
  (e) the action-grammar invariants survive in the minimal frame (tool-call-IS-
      action, anti-confabulation, close-with-verdict) + the migrated write
      boundary (governance/ + system/ EXCEPT).
  (f) the tool block is preserved (generated from REVIEWER_PRIMITIVES).

Run: python -m pytest api/test_adr323_frame_collapse_finished.py -q
"""
from __future__ import annotations


def _system_body() -> str:
    from agents.reviewer_agent import _compute_minimal_frame
    from agents.cockpit_awareness import build_cockpit_section
    return _compute_minimal_frame() + "\n\n" + build_cockpit_section()


def test_filesystem_block_deleted():
    import agents.cockpit_awareness as ca
    assert not hasattr(ca, "build_filesystem_block"), (
        "build_filesystem_block must be deleted (ADR-323 — substrate pedagogy → _workspace_guide.md)."
    )


def test_operating_posture_deleted():
    import agents.cockpit_awareness as ca
    assert not hasattr(ca, "_OPERATING_POSTURE"), (
        "_OPERATING_POSTURE must be deleted (ADR-323 — posture → principles.md / frame)."
    )


def test_system_prompt_under_ceiling():
    body = _system_body()
    # Pre-collapse was ~16.5K. Ceiling at 11K gives headroom over the ~9.5K target.
    assert len(body) < 11_000, (
        f"Composed system prompt is {len(body)} chars — must be < 11000 after the "
        f"ADR-323 collapse (was ~16.5K)."
    )


def test_no_substrate_pedagogy_in_system_prompt():
    body = _system_body()
    banned = [
        "When substrate is missing",
        "What NOT to write",
        "How you operate",
        "### Filesystem (canonical paths",
        "rolling 7d/30d/90d",  # the alpha-trader ground-truth pedagogy
    ]
    offenders = [b for b in banned if b in body]
    assert not offenders, (
        f"These substrate-pedagogy phrases must NOT be in the system prompt "
        f"(they live in _workspace_guide.md / principles.md per DP22): {offenders}"
    )


def test_action_grammar_survives_in_frame():
    from agents.reviewer_agent import _compute_minimal_frame
    frame = _compute_minimal_frame()
    # The interface contract the frame MUST carry (DP22).
    assert "A tool call IS your action" in frame
    assert "Close every cycle with a verdict" in frame
    # Anti-confabulation.
    assert "Describe only what your tool" in frame
    # The migrated write boundary (ADR-323 — up from the deleted filesystem block).
    assert "governance/" in frame and "system/" in frame
    assert "EXCEPT two roots" in frame


def test_tool_block_preserved():
    from agents.cockpit_awareness import build_tools_block
    block = build_tools_block()
    # The tool surface is the one thing this section still owns.
    assert "tool surface" in block.lower()
    # The load-bearing posture-correction framing survives.
    assert "Not in your curated tool surface" in block
    assert "Schedule is in your tool surface" in block
