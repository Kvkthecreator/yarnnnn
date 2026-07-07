"""ADR-284 Phase 1 regression gate: standing intent + OCCUPANT envelope.

Asserts the Phase 1 contracts:
  - PERSONA_STANDING_INTENT_PATH constant exists + value
  - PERSONA_STANDING_INTENT_PATH is in PERSONA_FILES tuple
  - freddie_envelope `_UNIVERSAL_ENVELOPE_DECLS` includes both OCCUPANT
    and standing_intent at the kernel-universal level
  - `_PERSONA_FRAME` mentions standing_intent.md + the write contract
  - `_build_user_message` renders both new envelope keys with appropriate
    section headings (when present) + empty-state hint when absent
  - `services.programs._populate_occupant_for_runtime` exists and is wired
    into `fork_reference_workspace` (OCCUPANT runtime-truth alignment)
  - Canon docs reference the new substrate (FOUNDATIONS Axiom 2 amendment +
    GLOSSARY entries + reviewer-substrate.md inventory update)

Per ADR-284 D8 Phase 1 — canon + kernel only. Bundle amendments (Phase 2)
have their own gate in the Phase 2 commit.

Per discipline rule: AST + source-string assertions. No live LLM call.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent


def _read_api(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _read_repo(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# 1. workspace_paths.py — PERSONA_STANDING_INTENT_PATH constant
# -----------------------------------------------------------------------------

def test_review_standing_intent_path_defined() -> None:
    src = _read_api("services/workspace_paths.py")
    assert 'PERSONA_STANDING_INTENT_PATH = "persona/standing_intent.md"' in src, (
        "PERSONA_STANDING_INTENT_PATH constant missing — workspace_paths.py "
        "must declare the canonical relative path per ADR-284"
    )


def test_standing_intent_in_review_files_tuple() -> None:
    src = _read_api("services/workspace_paths.py")
    # Find the PERSONA_FILES tuple literal and assert membership.
    idx = src.find("PERSONA_FILES = (")
    assert idx != -1, "PERSONA_FILES tuple must be defined"
    end = src.find(")", idx)
    block = src[idx:end]
    assert "PERSONA_STANDING_INTENT_PATH" in block, (
        "PERSONA_STANDING_INTENT_PATH must be included in PERSONA_FILES tuple"
    )


# -----------------------------------------------------------------------------
# 2. freddie_envelope.py — kernel-universal envelope additions
# -----------------------------------------------------------------------------

def test_envelope_universal_decls_include_occupant_and_standing_intent() -> None:
    src = _read_api("services/freddie_envelope.py")
    # Confirm imports were added
    assert "PERSONA_OCCUPANT_PATH" in src, (
        "PERSONA_OCCUPANT_PATH must be imported from workspace_paths"
    )
    assert "PERSONA_STANDING_INTENT_PATH" in src, (
        "PERSONA_STANDING_INTENT_PATH must be imported from workspace_paths"
    )
    # Confirm declarations are in the universal list — skip past the type
    # annotation `list[tuple[str, str]]` to find the actual `[ ... ]` body.
    idx = src.find("_UNIVERSAL_ENVELOPE_DECLS")
    assert idx != -1, "_UNIVERSAL_ENVELOPE_DECLS must be defined"
    body_start = src.find("= [", idx)
    assert body_start != -1, "_UNIVERSAL_ENVELOPE_DECLS assignment must use list literal"
    end = src.find("\n]", body_start)
    block = src[body_start:end]
    assert '"occupant_md"' in block, (
        "_UNIVERSAL_ENVELOPE_DECLS must include occupant_md entry per ADR-284"
    )
    assert '"standing_intent_md"' in block, (
        "_UNIVERSAL_ENVELOPE_DECLS must include standing_intent_md entry per ADR-284"
    )
    assert "PERSONA_OCCUPANT_PATH" in block, (
        "occupant_md entry must point at PERSONA_OCCUPANT_PATH"
    )
    assert "PERSONA_STANDING_INTENT_PATH" in block, (
        "standing_intent_md entry must point at PERSONA_STANDING_INTENT_PATH"
    )


def test_envelope_universal_decls_count() -> None:
    """Kernel-universal envelope entries.

    Growth ledger (count + the ADR that grew it):
      - Pre-ADR-284: 6 governance entries.
      - ADR-284 (+2 = 8): occupant_md + standing_intent_md.
      - ADR-298 D11 (+1 = 9): pace_yaml (Trigger-dimension operator dial).
      - ADR-301 pulse envelope (+2 = 11): schedule_index_md +
        recent_execution_md (Reviewer's own cadence + recent fires).
      - ADR-327: pace_yaml → budget_yaml (rename, count unchanged at 11);
        (+1 = 12): calibration_md (D6 self-improving loop).

    2026-06-04 (ADR-315 carry-over): retargeted == 8 → == 11 + key-set
    expanded to current reality. 2026-06-08 (ADR-327): == 11 → == 12,
    pace_yaml → budget_yaml + calibration_md. The assertion's job is
    unchanged — pin the kernel-universal envelope to its declared,
    ADR-attributed entries so a silent add/drop trips the gate.
    """
    from services.freddie_envelope import _UNIVERSAL_ENVELOPE_DECLS

    # ADR-390 removal pass (re-anchored 2026-07-02 during ADR-403): the
    # pulse/calibration entries (schedule_index_md, recent_execution_md,
    # calibration_md) moved OUT of universal to the program_active-gated
    # block — operation machinery a bare steward doesn't run. 12 → 9.
    # (This gate had been stale since ADR-390; caught in the ADR-403 sweep.)
    assert len(_UNIVERSAL_ENVELOPE_DECLS) == 9, (
        f"Expected 9 kernel-universal envelope entries "
        f"(6 pre-284 + ADR-284 occupant/standing_intent + ADR-327 budget; "
        f"pulse/calibration are program-gated per ADR-390), "
        f"found {len(_UNIVERSAL_ENVELOPE_DECLS)}"
    )
    keys = {entry[0] for entry in _UNIVERSAL_ENVELOPE_DECLS}
    expected = {
        "identity_md", "principles_md", "precedent_md",
        "mandate_md", "autonomy_md", "preferences_yaml",
        "occupant_md", "standing_intent_md",  # ADR-284
        "budget_yaml",                         # ADR-327 (was pace_yaml, ADR-298 D11)
    }
    assert keys == expected, (
        f"Envelope keys mismatch. Expected {expected}, got {keys}"
    )


def test_envelope_docstring_documents_new_entries() -> None:
    src = _read_api("services/freddie_envelope.py")
    assert "occupant_md" in src and "(ADR-284)" in src, (
        "Envelope load function docstring must document occupant_md + ADR-284 citation"
    )
    assert "standing_intent_md" in src, (
        "Envelope load function docstring must document standing_intent_md"
    )


# -----------------------------------------------------------------------------
# 3. freddie_agent.py — persona prompt + envelope rendering
# -----------------------------------------------------------------------------

def test_persona_frame_includes_standing_intent_section() -> None:
    """Post-ADR-306 collapse: the verbose 'standing intent has a substrate
    home' SECTION is substrate pedagogy and relocates to `_workspace_guide.md`
    (ADR-281's home). The minimal frame still NAMES standing_intent.md as the
    close-cycle channel (action-grammar) and cites ADR-284's substrate file —
    but the pedagogy of what the file is for lives in the guide.

    ADR-284 D5 ("standing intent has a substrate home") is preserved and
    sharpened: the home is the file + the guide teaches its purpose.
    """
    # Re-anchored (ADR-403, 2026-07-02): the envelope renders the file every
    # wake (the volatile suffix's standing-intent section) + cites ADR-284.
    src = _read_api("agents/freddie_agent.py")
    assert "standing_intent.md" in src, (
        "The envelope must render standing_intent.md (ADR-284 substrate home)"
    )
    assert "ADR-284" in src, (
        "freddie_agent.py must cite ADR-284 (standing_intent substrate home)"
    )
    # The substrate-home pedagogy lives in the workspace guides (both bundles).
    for bundle in ("alpha-trader", "alpha-author"):
        guide = _read_repo(
            f"docs/programs/{bundle}/reference-workspace/_workspace_guide.md"
        )
        assert "is where your forward-looking" in guide, (
            f"{bundle} _workspace_guide.md must carry the standing-intent "
            "substrate-home pedagogy (relocated from the persona frame per "
            "ADR-306 D3 + ADR-284 D5)"
        )
        assert "ADR-284" in guide, (
            f"{bundle} _workspace_guide.md standing-intent section must cite ADR-284"
        )


def test_persona_frame_enforces_every_cycle_write_contract() -> None:
    """Post-ADR-306 collapse: the verbose every-cycle write contract relocates
    to `_workspace_guide.md` (substrate pedagogy). The frame keeps only the
    compressed action-grammar line. Single-instance preserved.
    """
    # Re-anchored (ADR-397 → ADR-403, 2026-07-02): the close contract is the
    # frame's ReturnVerdict paragraph (DP22 interface — the Rung-3 Arm-B
    # silent-exit finding); the standing-intent WRITE habit is principles.md
    # content per agent-composition.md §3.2.1, no longer kernel prompt text.
    src = _read_api("agents/freddie_agent.py")
    assert "Close the turn by calling ReturnVerdict" in src, (
        "Minimal frame must carry the ReturnVerdict close contract (ADR-403)"
    )
    # The verbose every-cycle commitment lives in the workspace guides.
    for bundle in ("alpha-trader", "alpha-author"):
        guide = _read_repo(
            f"docs/programs/{bundle}/reference-workspace/_workspace_guide.md"
        )
        assert "Every judgment-mode cycle produces a `standing_intent.md` write" in guide, (
            f"{bundle} _workspace_guide.md must declare the every-cycle write "
            "contract including no-fire cycles (relocated per ADR-306 D3, "
            "ADR-284 D2 + D5)"
        )


def test_build_user_message_renders_occupant_envelope_key() -> None:
    src = _read_api("agents/freddie_agent.py")
    # OCCUPANT.md envelope rendering
    assert 'ctx.get("occupant_md")' in src, (
        "_build_user_message must read occupant_md from context"
    )
    assert "## OCCUPANT.md — Your current seat" in src, (
        "_build_user_message must render OCCUPANT.md with section heading"
    )


def test_build_user_message_renders_standing_intent_with_empty_hint() -> None:
    src = _read_api("agents/freddie_agent.py")
    assert 'ctx.get("standing_intent_md")' in src, (
        "_build_user_message must read standing_intent_md from context"
    )
    # ADR-414 §9a: the section header names the REAL path — per-agent when a
    # hire exists (agents/{slug}/standing_intent.md), the steward-era persona/
    # path otherwise — via ctx["judgment_home"]. So the header is dynamic; the
    # invariant is that it renders standing_intent.md with the "What you were
    # watching for last cycle" framing.
    assert "— What you were watching for last cycle" in src, (
        "_build_user_message must render standing_intent.md with the "
        "'What you were watching for last cycle' section framing"
    )
    assert "standing_intent.md" in src, (
        "_build_user_message must name the standing_intent.md substrate file"
    )
    assert "judgment_home" in src, (
        "the standing-intent header must resolve the per-agent judgment home "
        "(ADR-414 §9a) so the agent's own WriteFile lands where the next wake reads"
    )
    # Empty-state hint when no prior cycle has written
    assert "empty — first cycle, author it as part of this judgment" in src, (
        "_build_user_message must include first-cycle empty-state hint"
    )


# -----------------------------------------------------------------------------
# 4. programs.py — the occupant-fork is RETIRED (ADR-414 §9a / D2)
# -----------------------------------------------------------------------------
# The ADR-284 occupant-fork (`_populate_occupant_for_runtime`) is DELETED: the
# occupant fact is kernel data (ADR-414 D2 — FREDDIE_MODEL_IDENTITY), no
# per-agent OCCUPANT.md exists, and the fork installs the bundle's agent home
# verbatim. These three tests invert to assert the retirement (the phase_e gate
# `test_occupant_fork_is_deleted` is the primary ratchet; this keeps the ADR-284
# suite coherent with the ADR-414 world rather than testing a deleted symbol).

def test_populate_occupant_for_runtime_is_retired() -> None:
    src = _read_api("services/programs.py")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        assert not (
            isinstance(node, ast.AsyncFunctionDef)
            and node.name == "_populate_occupant_for_runtime"
        ), (
            "_populate_occupant_for_runtime must be DELETED — the occupant fact "
            "is kernel data (ADR-414 D2 / §9a); a hired agent has no OCCUPANT.md"
        )


def test_fork_reference_workspace_does_not_stamp_occupant() -> None:
    src = _read_api("services/programs.py")
    assert "_populate_occupant_for_runtime(um" not in src, (
        "fork_reference_workspace must NOT stamp the seat's OCCUPANT — the "
        "conflation ADR-284 papered over no longer exists (ADR-414 §9a)"
    )


# -----------------------------------------------------------------------------
# 5. Canon doc amendments
# -----------------------------------------------------------------------------

def test_foundations_axiom_2_declares_standing_intent_substrate() -> None:
    src = _read_repo("docs/architecture/FOUNDATIONS.md")
    assert "Standing intent has a substrate home" in src, (
        "FOUNDATIONS Axiom 2 must include 'Standing intent has a substrate "
        "home' section per ADR-284 amendment"
    )
    assert "standing_intent.md" in src, (
        "FOUNDATIONS Axiom 2 amendment must name the canonical file"
    )
    assert "ADR-284" in src, (
        "FOUNDATIONS Axiom 2 amendment must cite ADR-284"
    )


def test_foundations_reviewer_identity_inventory_updated() -> None:
    src = _read_repo("docs/architecture/FOUNDATIONS.md")
    # Reviewer identity inventory row must list standing_intent + judgment_log
    # (the latter is a pre-ADR-281 cascade catch-up bundled with ADR-284)
    assert "standing_intent.md" in src, (
        "FOUNDATIONS Reviewer identity row must include standing_intent.md"
    )
    assert "judgment_log.md" in src, (
        "FOUNDATIONS Reviewer identity row must include judgment_log.md "
        "(post-ADR-281 vocabulary)"
    )


def test_glossary_standing_intent_entry_exists() -> None:
    src = _read_repo("docs/architecture/GLOSSARY.md")
    assert "**Standing intent**" in src, (
        "GLOSSARY must include a 'Standing intent' entry per ADR-284 amendment"
    )
    assert "reviewer-workbench" in src.lower() or "reviewer-workbench" in src, (
        "GLOSSARY standing-intent entry must declare the reviewer-workbench role"
    )


def test_glossary_occupant_entry_runtime_truth_aligned() -> None:
    src = _read_repo("docs/architecture/GLOSSARY.md")
    assert "**OCCUPANT.md**" in src, (
        "GLOSSARY must include a sharpened OCCUPANT.md entry per ADR-284"
    )
    assert "runtime-truth-aligned" in src, (
        "GLOSSARY OCCUPANT entry must declare runtime-truth-alignment per ADR-284 D3"
    )


def test_reviewer_substrate_doc_includes_standing_intent() -> None:
    # 2026-06-04 (ADR-315 carry-over): reviewer-substrate.md was split into
    # three domain docs; the seat-file inventory (incl. standing_intent.md)
    # lives in reviewer-seat-substrate.md now. The doc-coverage invariant is
    # unchanged; only the file it reads from moved.
    src = _read_repo("docs/architecture/reviewer-seat-substrate.md")
    assert "standing_intent.md" in src, (
        "reviewer-seat-substrate.md must inventory standing_intent.md per ADR-284"
    )
    assert "forward-looking" in src.lower(), (
        "reviewer-seat-substrate.md standing-intent section must declare the "
        "forward-looking semantic"
    )


# -----------------------------------------------------------------------------
# 6. Sibling-ADR regression — no breakage of ADR-281 single-writer contract
# -----------------------------------------------------------------------------

def test_judgment_log_single_writer_preserved() -> None:
    """Adding standing_intent.md must NOT regress ADR-281 §3 single-writer
    contract for judgment_log.md. Standing intent is its own file, its own
    role, its own write path — they compose, they don't compete (ADR-284 D7).
    """
    src = _read_api("services/freddie_audit.py")
    assert "render_lineage_entry_if_material" in src, (
        "freddie_audit.render_lineage_entry_if_material must still be the "
        "single canonical writer for judgment_log.md per ADR-281 §3"
    )


if __name__ == "__main__":
    test_review_standing_intent_path_defined()
    test_standing_intent_in_review_files_tuple()
    test_envelope_universal_decls_include_occupant_and_standing_intent()
    test_envelope_universal_decls_count()
    test_envelope_docstring_documents_new_entries()
    test_persona_frame_includes_standing_intent_section()
    test_persona_frame_enforces_every_cycle_write_contract()
    test_build_user_message_renders_occupant_envelope_key()
    test_build_user_message_renders_standing_intent_with_empty_hint()
    test_populate_occupant_for_runtime_is_retired()
    test_fork_reference_workspace_does_not_stamp_occupant()
    test_foundations_axiom_2_declares_standing_intent_substrate()
    test_foundations_reviewer_identity_inventory_updated()
    test_glossary_standing_intent_entry_exists()
    test_glossary_occupant_entry_runtime_truth_aligned()
    test_reviewer_substrate_doc_includes_standing_intent()
    test_judgment_log_single_writer_preserved()
    print("ADR-284 Phase 1: 18/18 PASS")
