"""ADR-331 — Setup-as-Rendering: the surviving surface invariants + harvest.

SCOPED DOWN 2026-07-22 (was 24 tests, 9 of them red). Two thirds of this gate
outlived what it guarded, so it asserted a deleted wizard and a moved upload
path — a red gate nobody could act on. What was removed, and why:

  Phase 1 wizard (4 tests, DELETED) — `/setup` as a navigable Sequence surface:
      its page, its renderer, its first-run redirect, its registry row. ADR-437
      DELETED the guided first-boot wizard (built on the pre-pure-workspace
      model; ADR-414 D4/D5 made genesis empty and programs anytime hires, so
      there is no sequence to walk). The `/setup` row survives as a DORMANT slug
      + a redirect stub → /chat, which is why the two remaining Phase-1 tests
      (middleware protection + the `rocket` icon) still hold and stay.

  Phase 3 upload (8 tests, DELETED as DUPLICATE) — not dead behavior: the
      upload pipeline is very much alive, but it MOVED from `routes/documents`
      to `services/documents` under ADR-395, and its live gate
      (test_adr395_model_consumable_projection.py) already covers the raw lane,
      the derived projection, no-clobber, and the deferred embed. Keeping a
      second copy pinned to the old import path was duplicate coverage that
      could only rot. Coverage is preserved THERE, not lost here.

What remains is what still guards live code:

  Phase 1 (D1, D2) — the sequence archetype is registered in both the Python
                     ARCHETYPES tuple and the TS Archetype union; the surface
                     owns no substrate; `/setup` stays auth-gated and its icon
                     resolves (no Box fallback).
  Phase 2 (D3, D4) — harvest is an ordinary attributed invocation: the
                     `agent:harvest` author string validates against the
                     existing is_valid_author taxonomy (no new author prefix);
                     the metadata-only dry-run endpoint performs no writes.

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


def test_phase2_harvest_caller_identity_is_agent_harvest():
    """D3: the harvest service attributes writes as agent:harvest (the
    caller_identity that flows to WriteFile's authored_by)."""
    from services.harvest import HARVEST_CALLER_IDENTITY

    assert HARVEST_CALLER_IDENTITY == "agent:harvest"


def test_phase2_harvest_dry_run_does_no_writes():
    """D4: the dry-run is metadata-only — no write/WriteFile/write_revision
    in the dry-run path. We assert the source never imports a write primitive
    in the dry-run function body (static guard against accidental writes)."""
    import inspect

    from services.harvest import harvest_dry_run

    src = inspect.getsource(harvest_dry_run)
    for banned in ("write_revision", "WriteFile", "handle_write_file"):
        assert banned not in src, (
            f"ADR-331 D4: harvest_dry_run must perform NO writes (found {banned!r})"
        )


def test_phase2_harvest_scope_normalization_drops_unknown_providers():
    """D4: the picker's ephemeral scope is normalized; unknown providers are
    dropped, known ones (slack/notion/github) survive with their range."""
    from services.harvest import _normalize_sources

    scope = {"sources": [
        {"provider": "slack", "id": "C1", "range_days": 30},
        {"provider": "bogus", "id": "x"},
        {"provider": "notion", "id": "p1"},
    ]}
    norm = _normalize_sources(scope)
    assert [s["provider"] for s in norm] == ["slack", "notion"]
    assert norm[0]["range_days"] == 30


def test_phase2_harvest_not_in_default_providers_or_new_primitive():
    """D3 anti-goal: harvest adds no new primitive. The harvest service uses
    execute_primitive + existing read tools; it does not register a primitive
    handler. Assert no 'harvest' handler in the primitive registry."""
    from services.primitives.registry import HANDLERS

    assert not any("harvest" in name.lower() for name in HANDLERS), (
        "ADR-331 D3: harvest must NOT register a new primitive — it's an "
        "invocation using existing read tools + WriteFile."
    )


def test_phase2_harvest_route_registered():
    """D3/D4: the /harvest/dry-run + /harvest/run endpoints are registered."""
    from routes import harvest as harvest_route

    paths = {r.path for r in harvest_route.router.routes}
    assert "/harvest/dry-run" in paths
    assert "/harvest/run" in paths


def test_phase2_changelog_entry_present():
    """Prompt-change protocol: the harvest prompt requires a CHANGELOG entry."""
    changelog = _read(REPO_ROOT / "api" / "prompts" / "CHANGELOG.md")
    assert "ADR-331 Phase 2: harvest invocation system prompt" in changelog, (
        "ADR-331 Phase 2 adds a harvest-shaped LLM prompt — CHANGELOG entry required."
    )


# =============================================================================
# Phase 3 — multi-file + .zip upload (D5)
