"""ADR-414 Phase D+E-2 regression gate — the file re-homing to agents/{slug}/.

§9a: a hired agent's judgment load-out lives in `agents/{slug}/`; the
workspace-root seat paths (persona/, constitution/, contract/) stop being the
operation's home. The envelope, witness dial, judgment-log writer, and surface
reads all branch on `resolve_judgment_home` (the hire grant), never on
`program_active` (a platform connection alone raises the latter). The per-agent
grant sidecars are locked (ADR-366 per-agent). The occupant-fork is deleted
(the occupant fact is kernel data, D2).
"""

from pathlib import Path

import yaml

API = Path(__file__).resolve().parent
REPO = API.parent


def _src(rel: str) -> str:
    return (API / rel).read_text()


# ---------------------------------------------------------------------------
# Kernel: the judgment-home resolver + envelope re-point
# ---------------------------------------------------------------------------

def test_resolve_judgment_home_exists_and_keys_on_hire_grant():
    src = _src("services/programs.py")
    assert "def resolve_judgment_home" in src, "the judgment-home resolver is gone"
    # It must key on the hire-grant slug (resolve_hired_program_slug), the
    # activation record — NOT on a platform connection / program_active.
    body = src.split("def resolve_judgment_home", 1)[1].split("\ndef ", 1)[0]
    assert "resolve_hired_program_slug" in body, (
        "resolve_judgment_home must key on the hire grant (resolve_hired_"
        "program_slug), not program_active — a connection is not a hire"
    )
    assert "agent_home" in body, "resolve_judgment_home must return the agent_home prefix"


def test_envelope_re_points_to_judgment_home():
    src = _src("services/freddie_envelope.py")
    assert "resolve_judgment_home" in src, (
        "the wake envelope must re-point the judgment load-out to the hired "
        "agent's home (ADR-414 §9a)"
    )
    assert "_JUDGMENT_HOME_FILES" in src, (
        "the envelope must carry the judgment-home file map"
    )


def test_occupant_fork_is_deleted():
    """§9a: `_populate_occupant_for_runtime` is deleted — the occupant fact is
    kernel data (D2), no per-agent OCCUPANT.md exists."""
    src = _src("services/programs.py")
    assert "async def _populate_occupant_for_runtime" not in src, (
        "the occupant-fork function must be deleted (ADR-414 §9a)"
    )
    # And its call site inside fork_reference_workspace is gone.
    assert "_populate_occupant_for_runtime(um" not in src, (
        "the occupant-fork call site survives inside the fork"
    )


def test_judgment_log_writer_resolves_the_home():
    src = _src("services/freddie_audit.py")
    assert "_judgment_log_path" in src, (
        "the judgment-log writer must resolve the per-agent home (ADR-414 §9a)"
    )
    assert "resolve_judgment_home" in src


def test_witness_dial_resolves_per_agent():
    src = _src("services/review_policy.py")
    assert "resolve_judgment_home" in src, (
        "load_autonomy must resolve the hired agent's per-agent witness dial "
        "before falling back to the workspace dial (ADR-414 §9a)"
    )


# ---------------------------------------------------------------------------
# Permission topology: the per-agent grant sidecars are locked
# ---------------------------------------------------------------------------

def test_agent_grant_sidecar_helpers_exist():
    src = _src("services/workspace_paths.py")
    assert "def is_agent_grant_sidecar" in src
    assert "def agent_home" in src
    assert "AGENT_GRANT_SIDECAR_LEAVES" in src


def test_gate_locks_agent_grant_sidecars():
    src = _src("services/primitives/workspace.py")
    assert "is_agent_grant_sidecar" in src, (
        "the write gate must lock the per-agent grant sidecars "
        "(agents/{slug}/_autonomy.yaml + _budget.yaml) — ADR-366 per-agent"
    )


def test_is_agent_grant_sidecar_behaviour():
    import sys
    if str(API) not in sys.path:
        sys.path.insert(0, str(API))
    from services.workspace_paths import is_agent_grant_sidecar

    assert is_agent_grant_sidecar("agents/alpha-trader/_autonomy.yaml")
    assert is_agent_grant_sidecar("/workspace/agents/alpha-trader/_budget.yaml")
    # NOT a sidecar: the agent's own judgment files stay writable by the agent.
    assert not is_agent_grant_sidecar("agents/alpha-trader/IDENTITY.md")
    assert not is_agent_grant_sidecar("agents/alpha-trader/principles.md")
    # NOT under an agent home at all.
    assert not is_agent_grant_sidecar("governance/_autonomy.yaml")


# ---------------------------------------------------------------------------
# Bundle trees: the seat-class files live in agents/{slug}/
# ---------------------------------------------------------------------------

_ACTIVE_BUNDLE_SLUGS = ("alpha-trader", "alpha-author")
_AGENT_HOME_LEAVES = (
    "IDENTITY.md", "MANDATE.md", "principles.md", "_principles.yaml",
    "AUTONOMY.md", "_autonomy.yaml", "_preferences.yaml", "_expected_output.yaml",
)


def test_bundle_trees_home_the_seat_class_files():
    for slug in _ACTIVE_BUNDLE_SLUGS:
        home = REPO / "docs" / "programs" / slug / "reference-workspace" / "agents" / slug
        assert home.is_dir(), f"bundle '{slug}' has no agents/{slug}/ home"
        for leaf in _AGENT_HOME_LEAVES:
            assert (home / leaf).exists(), (
                f"bundle '{slug}' agents/{slug}/{leaf} missing (ADR-414 §9a)"
            )


def test_bundle_trees_no_seat_era_roots():
    """The seat-era roots (persona/, constitution/, contract/) must not linger
    in the restructured bundle trees (Singular Implementation — the tree is the
    truth, not a fork-time remap)."""
    for slug in _ACTIVE_BUNDLE_SLUGS:
        ref = REPO / "docs" / "programs" / slug / "reference-workspace"
        for stale_root in ("persona", "constitution", "contract"):
            assert not (ref / stale_root).exists(), (
                f"bundle '{slug}' still has a seat-era {stale_root}/ root — "
                f"ADR-414 §9a homes the seat-class files in agents/{slug}/"
            )


def test_personas_yaml_no_occupant_attribution():
    """§9a #9: the occupant-fact-as-kernel-data means personas drop
    occupant_attribution + the OCCUPANT.md core_files entry."""
    doc = yaml.safe_load((REPO / "docs" / "alpha" / "personas.yaml").read_text())
    for p in doc.get("personas", []):
        expected = p.get("expected", {}) or {}
        assert "occupant_attribution" not in expected, (
            f"persona '{p.get('slug')}' still declares occupant_attribution "
            f"— retired by ADR-414 §9a #9"
        )
        core_files = expected.get("core_files", []) or []
        assert not any("OCCUPANT.md" in f for f in core_files), (
            f"persona '{p.get('slug')}' still lists OCCUPANT.md in core_files "
            f"— retired by ADR-414 §9a #9"
        )
