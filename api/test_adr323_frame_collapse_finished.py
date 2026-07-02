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
  (f) the tool block is preserved (generated from FREDDIE_PRIMITIVES).

Run: python -m pytest api/test_adr323_frame_collapse_finished.py -q
"""
from __future__ import annotations


def _system_body() -> str:
    from agents.freddie_agent import _compute_minimal_frame
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
    # Pre-collapse was ~16.5K. Ceiling raised 11K → 11.5K by ADR-344 (2026-06-18),
    # then 11.5K → 12K by ADR-365b (2026-06-24): the operator-facing structure
    # directive in _compute_minimal_frame (lead-with-takeaway / expand-codenames /
    # flowing-prose, with concrete bad→good examples) is the same CLASS of content
    # as the postures already here — interface-grammar (how the operator-addressed
    # channel is consumed), not a rule of judgment. It is the FIRST operator-facing-
    # voice content the frame has ever carried that is EVIDENCE-BACKED: an A/B eval
    # (docs/evaluations/2026-06-24-adr365b-composed-prose-VALIDATION.md;
    # probe_adr365b_composed_prose_ab_local.py) measured +49–79% readability on the
    # documents the Reviewer composes (standing_intent/judgment_log), scored by an
    # LLM judge on the three CC dimensions. The examples are load-bearing (cutting
    # one drops the effect) and cannot be trimmed under the previous 11.5K without
    # mangling principal-shift postures (ADR-352 witness-dial, absent-MANDATE
    # reasoning). This bump IS the "same-rationale" justification the prior comment
    # required — the directive earns its space with a measured win, not a silent
    # bump. 12K is still ~⅔ of the pre-collapse size.
    assert len(body) < 12_000, (
        f"Composed system prompt is {len(body)} chars — must be < 12000 (ADR-365b; "
        f"was 11500 at ADR-344, ~16.5K pre-collapse). If over, the fix is almost "
        f"always to move a rule-of-judgment to principles.md, not raise the ceiling."
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
    from agents.freddie_agent import _compute_minimal_frame, _TRIGGER_FRAMING
    frame = _compute_minimal_frame()
    # The interface contract the frame MUST carry (DP22).
    assert "A tool call IS your action" in frame
    # ADR-397 + Rung-3 finding (2026-07-02): the close CONTRACT is DP22
    # interface material and lives in the FRAME (the Arm-B probe proved a
    # framing-only close silently exits when the framing is stripped); the
    # verdict-close LITURGY (stand_down semantics etc.) stays on the
    # reactive trigger framing.
    assert "ReturnVerdict" in frame
    assert "Close every cycle with ReturnVerdict" in _TRIGGER_FRAMING["reactive"]
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
