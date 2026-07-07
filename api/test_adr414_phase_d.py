"""ADR-414 Phase D+E-1 regression gate — the activation record is a grant row.

D5: activation mints a `principal_grants` row (role='own-agent',
principal_id='program:{slug}'); deactivation revokes it; every consumer
reads `resolve_hired_program_slug`. The prose marker (heading regex) is
deleted vocabulary — this is the ADR-414 CI ratchet #2 ("no prose
activation markers").
"""

from pathlib import Path

API = Path(__file__).resolve().parent


def _src(rel: str) -> str:
    return (API / rel).read_text()


def test_no_prose_activation_marker_anywhere():
    """Ratchet #2: the heading-marker regex never returns to live code.

    (The backfill one-shot legitimately carries the regex as a frozen
    migration artifact — scripts/oneshot is excluded.)
    """
    banned = "parse_active_program_slug"
    offenders = []
    for sub in ("services", "routes", "agents", "jobs", "mcp_server"):
        for py in (API / sub).rglob("*.py"):
            src = py.read_text()
            # docstring mentions of the DELETED name are allowed only in
            # services/programs.py (the deletion record); code references
            # anywhere are not.
            if banned in src and py.name != "programs.py":
                offenders.append(str(py.relative_to(API)))
    assert not offenders, (
        f"prose activation marker parsing reappeared in {offenders} — the "
        f"activation record is the hire grant row (ADR-414 D5)"
    )


def test_hire_lifecycle_symbols_exist():
    src = _src("services/programs.py")
    for needle in (
        "def resolve_hired_program_slug",
        "def mint_hire_grant",
        "def revoke_hire_grant",
        'HIRE_GRANT_ROLE = "own-agent"',
        'HIRE_GRANT_PREFIX = "program:"',
    ):
        assert needle in src, f"hire lifecycle lost: {needle}"


def test_fork_mints_and_deactivate_revokes():
    programs_src = _src("services/programs.py")
    assert "mint_hire_grant(user_id, program_slug)" in programs_src, (
        "fork_reference_workspace no longer mints the hire grant"
    )
    routes_src = _src("routes/programs.py")
    assert "revoke_hire_grant" in routes_src, (
        "deactivate no longer revokes the hire grant"
    )
    assert "strip_program_marker_from_mandate" not in routes_src, (
        "deactivate regressed to the prose-strip write (ADR-414 D5)"
    )


def test_consumers_read_the_grant_resolver():
    for rel in (
        "services/working_memory.py",
        "routes/workspace.py",
        "services/substrate_reapply.py",
        "services/workspace_purge.py",
        "services/bundle_reader.py",
    ):
        assert "resolve_hired_program_slug" in _src(rel), (
            f"{rel} lost its grant-resolver activation read (ADR-414 D5)"
        )
