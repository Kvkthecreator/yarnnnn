"""ADR-331 — Setup-as-Rendering: the surviving surface invariants.

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
  Phase 2 (D3, D4) — DELETED. The harvest feature is removed (2026-08-18):
                     zero callers since ADR-437 deleted its FE client block,
                     and ADR-577 made its one execution path refuse
                     credentials. Its assertions are removed with it.

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
# =============================================================================


