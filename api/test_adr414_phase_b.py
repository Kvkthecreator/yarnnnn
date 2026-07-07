"""ADR-414 Phase B regression gate — the steward's constitution is kernel-sourced.

D2: the envelope substitutes the kernel steward constants for the three
constitution keys (mandate_md / identity_md / principles_md) whenever the
workspace file is absent or still carries STEWARD_DEFAULT_MARKER. Operator-
or program-authored content (no marker) always wins.

Also gates B1's fix shape: the freddie-activity proposal feed must match
BOTH the live `freddie:` prefix and legacy `reviewer:` rows.
"""

from pathlib import Path

API = Path(__file__).resolve().parent


def _src(rel: str) -> str:
    return (API / rel).read_text()


def test_envelope_substitutes_kernel_constants():
    src = _src("services/freddie_envelope.py")
    for needle in (
        "STEWARD_DEFAULT_MARKER",
        "DEFAULT_STEWARD_MANDATE_MD",
        "DEFAULT_STEWARD_IDENTITY_MD",
        "DEFAULT_STEWARD_PRINCIPLES_MD",
    ):
        assert needle in src, (
            f"freddie_envelope.py lost the ADR-414 D2 kernel-constant "
            f"substitution ({needle} missing)"
        )


def test_substitution_guard_preserves_authored_content():
    """The guard must be marker-or-empty — authored content always wins."""
    src = _src("services/freddie_envelope.py")
    assert "not _val.strip() or STEWARD_DEFAULT_MARKER in _val" in src, (
        "the D2 substitution guard changed shape — it must replace ONLY "
        "absent-or-marker content, never operator/program-authored files"
    )


def test_substitution_covers_the_three_constitution_keys():
    src = _src("services/freddie_envelope.py")
    for key in ('"mandate_md"', '"identity_md"', '"principles_md"'):
        assert src.count(key) >= 1, f"{key} missing from the substitution table"


def test_freddie_activity_feed_matches_both_prefixes():
    """B1: the proposal feed matches freddie: (live) + reviewer: (legacy)."""
    src = _src("routes/agents.py")
    assert "source.like.freddie:%" in src and "source.like.reviewer:%" in src, (
        "the freddie-activity proposal feed must match both the live "
        "freddie: prefix and legacy reviewer: rows (ADR-414 B1)"
    )
    assert '.like("source", "reviewer:%")' not in src, (
        "the reviewer:-only filter regressed (ADR-414 B1 bug)"
    )


def test_roster_synthesis_is_gone():
    """B1: the ADR-214 Freddie pseudo-agent roster card stays deleted."""
    src = _src("routes/agents.py")
    assert 'id="freddie"' not in src, (
        "the Freddie roster-card synthesis reappeared — the roster is "
        "Altitude 3 only (ADR-412 D5 / ADR-414 D3)"
    )


def test_init_never_scaffolds_the_thinking_partner_row():
    """B3 (ADR-414 D3): one system agent — genesis never creates a second.

    Migration 205 deleted the live rows; this keeps the scaffold deleted.
    The `session_type='thinking_partner'` chat-sessions slug is data-compat
    and allowed; the agents-table ROW creation is not.
    """
    src = _src("services/workspace_init.py")
    assert "create_agent_record" not in src, (
        "workspace_init regressed to scaffolding an agents-table row at "
        "genesis (ADR-414 D3: the thinking_partner row is retired; "
        "migration 205)"
    )
    assert 'eq("role", "thinking_partner")' not in src, (
        "workspace_init re-grew a thinking_partner row lookup (ADR-414 D3)"
    )
