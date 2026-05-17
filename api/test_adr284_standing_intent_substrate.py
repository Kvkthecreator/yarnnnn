"""ADR-284 Phase 1 regression gate: standing intent + OCCUPANT envelope.

Asserts the Phase 1 contracts:
  - REVIEW_STANDING_INTENT_PATH constant exists + value
  - REVIEW_STANDING_INTENT_PATH is in REVIEW_FILES tuple
  - reviewer_envelope `_UNIVERSAL_ENVELOPE_DECLS` includes both OCCUPANT
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
# 1. workspace_paths.py — REVIEW_STANDING_INTENT_PATH constant
# -----------------------------------------------------------------------------

def test_review_standing_intent_path_defined() -> None:
    src = _read_api("services/workspace_paths.py")
    assert 'REVIEW_STANDING_INTENT_PATH = "review/standing_intent.md"' in src, (
        "REVIEW_STANDING_INTENT_PATH constant missing — workspace_paths.py "
        "must declare the canonical relative path per ADR-284"
    )


def test_standing_intent_in_review_files_tuple() -> None:
    src = _read_api("services/workspace_paths.py")
    # Find the REVIEW_FILES tuple literal and assert membership.
    idx = src.find("REVIEW_FILES = (")
    assert idx != -1, "REVIEW_FILES tuple must be defined"
    end = src.find(")", idx)
    block = src[idx:end]
    assert "REVIEW_STANDING_INTENT_PATH" in block, (
        "REVIEW_STANDING_INTENT_PATH must be included in REVIEW_FILES tuple"
    )


# -----------------------------------------------------------------------------
# 2. reviewer_envelope.py — kernel-universal envelope additions
# -----------------------------------------------------------------------------

def test_envelope_universal_decls_include_occupant_and_standing_intent() -> None:
    src = _read_api("services/reviewer_envelope.py")
    # Confirm imports were added
    assert "REVIEW_OCCUPANT_PATH" in src, (
        "REVIEW_OCCUPANT_PATH must be imported from workspace_paths"
    )
    assert "REVIEW_STANDING_INTENT_PATH" in src, (
        "REVIEW_STANDING_INTENT_PATH must be imported from workspace_paths"
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
    assert "REVIEW_OCCUPANT_PATH" in block, (
        "occupant_md entry must point at REVIEW_OCCUPANT_PATH"
    )
    assert "REVIEW_STANDING_INTENT_PATH" in block, (
        "standing_intent_md entry must point at REVIEW_STANDING_INTENT_PATH"
    )


def test_envelope_universal_decls_count_grew_to_8() -> None:
    """Pre-ADR-284: 6 governance entries. Post-ADR-284: 6 + 2 = 8."""
    from services.reviewer_envelope import _UNIVERSAL_ENVELOPE_DECLS

    assert len(_UNIVERSAL_ENVELOPE_DECLS) == 8, (
        f"Expected 8 kernel-universal envelope entries post-ADR-284, "
        f"found {len(_UNIVERSAL_ENVELOPE_DECLS)}"
    )
    keys = {entry[0] for entry in _UNIVERSAL_ENVELOPE_DECLS}
    expected = {
        "identity_md", "principles_md", "precedent_md",
        "mandate_md", "autonomy_md", "preferences_yaml",
        "occupant_md", "standing_intent_md",
    }
    assert keys == expected, (
        f"Envelope keys mismatch. Expected {expected}, got {keys}"
    )


def test_envelope_docstring_documents_new_entries() -> None:
    src = _read_api("services/reviewer_envelope.py")
    assert "occupant_md" in src and "(ADR-284)" in src, (
        "Envelope load function docstring must document occupant_md + ADR-284 citation"
    )
    assert "standing_intent_md" in src, (
        "Envelope load function docstring must document standing_intent_md"
    )


# -----------------------------------------------------------------------------
# 3. reviewer_agent.py — persona prompt + envelope rendering
# -----------------------------------------------------------------------------

def test_persona_frame_includes_standing_intent_section() -> None:
    src = _read_api("agents/reviewer_agent.py")
    assert "Your standing intent has a substrate home" in src, (
        "_PERSONA_FRAME must include the 'standing intent has a substrate "
        "home' section per ADR-284 D5"
    )
    assert "standing_intent.md" in src, (
        "_PERSONA_FRAME must name standing_intent.md as the canonical file"
    )
    assert "ADR-284" in src, (
        "_PERSONA_FRAME standing-intent section must cite ADR-284"
    )


def test_persona_frame_enforces_every_cycle_write_contract() -> None:
    src = _read_api("agents/reviewer_agent.py")
    assert "Every judgment-mode cycle produces a standing_intent.md write" in src, (
        "_PERSONA_FRAME must declare the every-cycle write contract — including "
        "no-fire cycles (per ADR-284 D2 + D5)"
    )


def test_build_user_message_renders_occupant_envelope_key() -> None:
    src = _read_api("agents/reviewer_agent.py")
    # OCCUPANT.md envelope rendering
    assert 'ctx.get("occupant_md")' in src, (
        "_build_user_message must read occupant_md from context"
    )
    assert "## OCCUPANT.md — Your current seat" in src, (
        "_build_user_message must render OCCUPANT.md with section heading"
    )


def test_build_user_message_renders_standing_intent_with_empty_hint() -> None:
    src = _read_api("agents/reviewer_agent.py")
    assert 'ctx.get("standing_intent_md")' in src, (
        "_build_user_message must read standing_intent_md from context"
    )
    assert "## standing_intent.md — What you were watching for last cycle" in src, (
        "_build_user_message must render standing_intent.md with section heading"
    )
    # Empty-state hint when no prior cycle has written
    assert "empty — first cycle, author it as part of this judgment" in src, (
        "_build_user_message must include first-cycle empty-state hint"
    )


# -----------------------------------------------------------------------------
# 4. programs.py — _populate_occupant_for_runtime + fork integration
# -----------------------------------------------------------------------------

def test_populate_occupant_for_runtime_exists() -> None:
    src = _read_api("services/programs.py")
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AsyncFunctionDef)
            and node.name == "_populate_occupant_for_runtime"
        ):
            found = True
            break
    assert found, (
        "_populate_occupant_for_runtime async helper must be defined in "
        "services/programs.py per ADR-284 D8"
    )


def test_populate_occupant_uses_reviewer_model_identity() -> None:
    src = _read_api("services/programs.py")
    assert "REVIEWER_MODEL_IDENTITY" in src, (
        "_populate_occupant_for_runtime must import REVIEWER_MODEL_IDENTITY "
        "from agents.reviewer_agent to align occupant identity with the "
        "runtime model the Reviewer's loop self-attributes as"
    )
    assert "occupant_class: ai" in src, (
        "_populate_occupant_for_runtime must declare occupant_class: ai for "
        "the current alpha state (AI runtime occupant)"
    )
    assert "delegation_charter" in src, (
        "_populate_occupant_for_runtime must include delegation_charter block "
        "per ADR-284 D3"
    )
    assert 'authored_by="system:occupant-fork"' in src, (
        "OCCUPANT runtime-population must attribute writes as "
        "system:occupant-fork per ADR-209 attribution"
    )


def test_fork_reference_workspace_calls_populate_occupant() -> None:
    src = _read_api("services/programs.py")
    # The fork function must invoke the occupant-population helper.
    assert "_populate_occupant_for_runtime(um, program_slug)" in src, (
        "fork_reference_workspace must call _populate_occupant_for_runtime "
        "after copying bundle files per ADR-284 D3"
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
    src = _read_repo("docs/architecture/reviewer-substrate.md")
    assert "standing_intent.md" in src, (
        "reviewer-substrate.md must inventory standing_intent.md per ADR-284"
    )
    assert "forward-looking" in src.lower(), (
        "reviewer-substrate.md standing-intent section must declare the "
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
    src = _read_api("services/reviewer_audit.py")
    assert "render_lineage_entry_if_material" in src, (
        "reviewer_audit.render_lineage_entry_if_material must still be the "
        "single canonical writer for judgment_log.md per ADR-281 §3"
    )


if __name__ == "__main__":
    test_review_standing_intent_path_defined()
    test_standing_intent_in_review_files_tuple()
    test_envelope_universal_decls_include_occupant_and_standing_intent()
    test_envelope_universal_decls_count_grew_to_8()
    test_envelope_docstring_documents_new_entries()
    test_persona_frame_includes_standing_intent_section()
    test_persona_frame_enforces_every_cycle_write_contract()
    test_build_user_message_renders_occupant_envelope_key()
    test_build_user_message_renders_standing_intent_with_empty_hint()
    test_populate_occupant_for_runtime_exists()
    test_populate_occupant_uses_reviewer_model_identity()
    test_fork_reference_workspace_calls_populate_occupant()
    test_foundations_axiom_2_declares_standing_intent_substrate()
    test_foundations_reviewer_identity_inventory_updated()
    test_glossary_standing_intent_entry_exists()
    test_glossary_occupant_entry_runtime_truth_aligned()
    test_reviewer_substrate_doc_includes_standing_intent()
    test_judgment_log_single_writer_preserved()
    print("ADR-284 Phase 1: 18/18 PASS")
