"""ADR-414 Phase C regression gate — genesis stays pure.

D4: `initialize_workspace` seeds exactly the two governance dials and
nothing else; it never forks a program; it never scaffolds an agents row,
a seat occupant, or steward constitution files. The ADR-209-pattern
ratchet: everything the deletion ledger killed stays dead.
"""

import inspect
from pathlib import Path

API = Path(__file__).resolve().parent
INIT_SRC = (API / "services" / "workspace_init.py").read_text()


def test_no_program_slug_parameter():
    """Genesis never forks — the program_slug parameter is deleted (D4/D5)."""
    import sys

    sys.path.insert(0, str(API))
    from services.workspace_init import initialize_workspace

    params = list(inspect.signature(initialize_workspace).parameters)
    assert params == ["client", "user_id"], (
        f"initialize_workspace grew parameters beyond (client, user_id): "
        f"{params} — genesis is pure (ADR-414 D4); program activation is a "
        f"post-genesis hire"
    )


def test_no_steward_constitution_seeding():
    """The steward's constitution is a kernel constant (D2), never seeded."""
    for banned in (
        "DEFAULT_STEWARD_MANDATE_MD",
        "DEFAULT_STEWARD_IDENTITY_MD",
        "DEFAULT_STEWARD_PRINCIPLES_MD",
    ):
        assert banned not in INIT_SRC, (
            f"workspace_init regressed to seeding {banned} — the steward's "
            f"constitution rides the envelope as a kernel constant "
            f"(ADR-414 D2 / freddie_envelope.py)"
        )


def test_no_skeleton_scaffolds():
    """The retired skeleton set stays deleted (the deletion ledger)."""
    for banned in (
        "DEFAULT_PRECEDENT_MD",
        "TP_ORCHESTRATION_PLAYBOOK",
        "DEFAULT_REVIEW_REFLECTION_MD",
        "DEFAULT_WORKSPACE_GUIDE_MD",
        "rotate_occupant",
        "PERSONA_PRINCIPLES_YAML_PATH",
        # the fork must never be imported here (pointer comments are fine):
        "from services.programs import",
    ):
        assert banned not in INIT_SRC, (
            f"workspace_init regressed to scaffolding {banned} — pure genesis "
            f"seeds ONLY the two governance dials (ADR-414 D4)"
        )


def test_the_two_dials_are_seeded():
    """What genesis DOES create: budget + witness dial (workspace-variable)."""
    assert "GOVERNANCE_BUDGET_PATH" in INIT_SRC, "budget dial seeding lost"
    assert "GOVERNANCE_AUTONOMY_YAML_PATH" in INIT_SRC, "witness dial seeding lost"
    assert "DEFAULT_AUTONOMY_YAML" in INIT_SRC, "witness dial default lost"


def test_refork_callers_fork_after_genesis():
    """L2/L4 reinit re-forks as the CALLER's post-genesis act (D4)."""
    for rel in ("services/workspace_purge.py", "routes/account.py"):
        src = (API / rel).read_text()
        assert "program_slug=prior_program_slug" not in src, (
            f"{rel} regressed to passing program_slug into genesis "
            f"(ADR-414 D4: the re-fork is the caller's own act)"
        )
        assert "fork_reference_workspace" in src, (
            f"{rel} lost its post-genesis re-fork (ADR-244 D4 behavior must "
            f"be preserved via the caller-side fork)"
        )
