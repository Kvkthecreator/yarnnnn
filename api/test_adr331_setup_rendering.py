"""ADR-331 — Setup-as-Rendering: the /setup Sequence surface + harvest.

Regression gate for the three-phase ADR-331 implementation:

  Phase 1 (D1, D2) — `/setup` is a kernel atomic surface, Sequence archetype,
                     os-config register, owns no substrate (substrate_paths
                     == []); the sequence archetype is registered in both the
                     Python ARCHETYPES tuple and the TS Archetype union.
  Phase 2 (D3, D4) — harvest is an ordinary attributed invocation: the
                     `agent:harvest` author string validates against the
                     existing is_valid_author taxonomy (no new author prefix);
                     the metadata-only dry-run endpoint performs no writes.
  Phase 3 (D5)     — /documents/upload accepts a file list + .zip expansion,
                     writing N attributed /workspace/uploads/*.md rows from
                     one call.

Pure-Python / pure-fs assertions where possible. No DB, no network, no LLM.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(p: Path) -> str:
    return p.read_text() if p.exists() else ""


# =============================================================================
# Phase 1 — /setup surface + sequence archetype (D1, D2)
# =============================================================================


def test_phase1_setup_registered_as_sequence_os_config():
    """D1: `setup` is in KERNEL_SURFACES with archetype=sequence,
    register=os-config, route=/setup, summon-only (default_pinned False)."""
    from services.kernel_surfaces import KERNEL_SURFACES

    setup = next((s for s in KERNEL_SURFACES if s["slug"] == "setup"), None)
    assert setup is not None, "ADR-331 D1: `setup` not registered in KERNEL_SURFACES"
    assert setup["archetype"] == "sequence", (
        f"ADR-331 D1: setup archetype must be 'sequence', got {setup['archetype']!r}"
    )
    assert setup["register"] == "os-config", (
        f"ADR-331 D1: setup register must be 'os-config', got {setup['register']!r}"
    )
    assert setup["route"] == "/setup"
    assert setup["default_pinned"] is False, "ADR-331 D1: setup is summon-only after first run"


def test_phase1_setup_owns_no_substrate():
    """D1 (load-bearing): setup is a RENDERING over api.workspace.getState();
    it owns no file. substrate_paths == [] is the no-stored-state encoding."""
    from services.kernel_surfaces import KERNEL_SURFACES

    setup = next(s for s in KERNEL_SURFACES if s["slug"] == "setup")
    assert setup["substrate_paths"] == [], (
        "ADR-331 D1: setup must own no substrate path — it reads the "
        "workspace-state composition. A non-empty substrate_paths would "
        "imply stored wizard state, which the Sequence archetype forbids."
    )


def test_phase1_sequence_archetype_in_python_tuple():
    """D1: the `sequence` archetype is registered in the Python ARCHETYPES."""
    from services.kernel_surfaces import ARCHETYPES

    assert "sequence" in ARCHETYPES, "ADR-331 D1: 'sequence' missing from ARCHETYPES"


def test_phase1_sequence_archetype_in_ts_union():
    """D1: the TS Archetype union mirrors the Python tuple — `sequence`
    must be present in web/lib/compositor/types.ts (drift = regression)."""
    ts = _read(REPO_ROOT / "web" / "lib" / "compositor" / "types.ts")
    assert "'sequence'" in ts, (
        "ADR-331 D1: 'sequence' missing from the TS Archetype union — "
        "Python ARCHETYPES and the TS union must not drift."
    )


def test_phase1_setup_page_exists():
    """D1: the /setup route page exists and renders the SetupSequence."""
    page = _read(REPO_ROOT / "web" / "app" / "(authenticated)" / "setup" / "page.tsx")
    assert page, "ADR-331 D1: /setup route page missing"
    assert "SetupSequence" in page, "ADR-331 D1: /setup page must render SetupSequence"


def test_phase1_setup_renderer_reads_getstate_no_local_state():
    """D1: the SetupSequence renderer reads api.workspace.getState() and stores
    no progress of its own (the no-wizard-state rule). We assert it calls
    getState and does NOT persist any setup/wizard/progress to an API."""
    src = _read(REPO_ROOT / "web" / "components" / "library" / "SetupSequence.tsx")
    assert src, "ADR-331 D1: SetupSequence component missing"
    assert "api.workspace.getState()" in src, (
        "ADR-331 D1: SetupSequence must derive from api.workspace.getState()"
    )
    # No persisted wizard/setup/progress writes — derivation only.
    for banned in ("saveSetup", "setWizardState", "api.setup.save", "persistProgress"):
        assert banned not in src, (
            f"ADR-331 anti-goal: SetupSequence must not persist progress ({banned})"
        )


def test_phase1_first_run_redirect_points_to_setup():
    """D2: the first-run redirect target moved to /setup?first_run=1."""
    cb = _read(REPO_ROOT / "web" / "app" / "auth" / "callback" / "page.tsx")
    assert "/setup?first_run=1" in cb, (
        "ADR-331 D2: first-run redirect must target /setup?first_run=1"
    )
    # The old /program?first_run=1 target must be gone from the redirect.
    assert "/program?first_run=1" not in cb, (
        "ADR-331 D2: stale /program?first_run=1 redirect must be removed"
    )


def test_phase1_home_cta_points_to_setup():
    """D6: the home empty-state CTA repoints from /program to /setup."""
    src = _read(REPO_ROOT / "web" / "components" / "library" / "HomeRenderer.tsx")
    assert 'href="/setup"' in src, (
        "ADR-331 D6: UnactivatedHomeCTA must point to /setup"
    )


def test_phase1_setup_is_protected_route():
    """D2: /setup is auth-gated (first-run authenticated surface)."""
    mw = _read(REPO_ROOT / "web" / "lib" / "supabase" / "middleware.ts")
    assert '"/setup"' in mw, (
        "ADR-331: /setup must be in PROTECTED_PREFIXES — it is an "
        "authenticated first-run surface."
    )


def test_phase1_rocket_icon_registered():
    """D1: the setup surface's icon_key='rocket' resolves (no Box fallback)."""
    icons = _read(REPO_ROOT / "web" / "lib" / "shell" / "surface-icons.tsx")
    assert "rocket: Rocket" in icons, (
        "ADR-331 D1: 'rocket' icon must be registered for /setup — an "
        "unregistered icon_key falls back to Box (visible inconsistency)."
    )


# =============================================================================
# Phase 2 — harvest invocation attribution (D3)
# =============================================================================


def test_phase2_agent_harvest_author_validates():
    """D3: harvest writes attributed substrate with `agent:harvest` — this
    must validate against the existing is_valid_author taxonomy (the `agent:`
    prefix is already valid; harvest adds no new author prefix)."""
    from services.authored_substrate import is_valid_author

    assert is_valid_author("agent:harvest"), (
        "ADR-331 D3: `agent:harvest` must validate against is_valid_author — "
        "harvest is an ordinary attributed invocation, no new author prefix."
    )


# Phase 2 dry-run endpoint + Phase 3 multi-file upload assertions land with
# their respective implementation commits (this file extends per phase, per
# the ADR-287 conformance-gate discipline of one gate, extended in place).


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
