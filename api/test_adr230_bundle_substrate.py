"""ADR-230 test gate — bundle substrate + persona-program registry contracts.

Per ADR-230 D8, these tests enforce as CI regression guards:
  · personas link to existing bundles (D1)
  · bundles carry their canonical substrate templates (D2)
  · the deleted orphan MANDATE stays deleted (D7 regression guard)
  · the deleted parallel scaffold stays deleted (D5 regression guard)

These tests do NOT spin up a database, do not call out to the network,
and do not depend on the workspace_init module — they're pure-fs
shape checks that any bundle author or persona-registry editor must
keep passing.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PROGRAMS_ROOT = REPO_ROOT / "docs" / "programs"
PERSONAS_YAML = REPO_ROOT / "docs" / "alpha" / "personas.yaml"
BANNED_ORPHAN_MANDATE = REPO_ROOT / "docs" / "alpha" / "personas" / "alpha-trader" / "MANDATE.md"
BANNED_PARALLEL_SCAFFOLD = REPO_ROOT / "api" / "scripts" / "alpha_ops" / "scaffold_trader.py"


# =============================================================================
# D1 — personas link to existing bundles
# =============================================================================


def test_personas_link_to_existing_bundles():
    """Every persona row in personas.yaml must declare a `program` field
    whose target bundle exists at docs/programs/{program}/MANIFEST.yaml."""
    raw = yaml.safe_load(PERSONAS_YAML.read_text())
    personas = raw.get("personas", [])
    assert personas, "personas.yaml has no personas — registry is empty"

    for p in personas:
        slug = p.get("slug")
        program = p.get("program")
        assert slug, f"persona row missing slug: {p}"
        assert program, (
            f"persona '{slug}' missing `program` field. "
            f"ADR-230 D1 requires every persona to declare which program it runs."
        )
        manifest = PROGRAMS_ROOT / program / "MANIFEST.yaml"
        assert manifest.exists(), (
            f"persona '{slug}' declares program='{program}' but "
            f"docs/programs/{program}/MANIFEST.yaml does not exist."
        )


# =============================================================================
# D2 — bundles carry canonical substrate templates
# =============================================================================


def _list_active_programs() -> list[Path]:
    """Find all programs with status=active in their MANIFEST.yaml."""
    active: list[Path] = []
    if not PROGRAMS_ROOT.is_dir():
        return active
    for program_dir in sorted(PROGRAMS_ROOT.iterdir()):
        manifest = program_dir / "MANIFEST.yaml"
        if not manifest.exists():
            continue
        try:
            data = yaml.safe_load(manifest.read_text())
        except Exception:
            continue
        if (data or {}).get("status") == "active":
            active.append(program_dir)
    return active


def test_bundle_carries_canonical_substrate():
    """Every authored_substrate path declared in an active bundle's
    MANIFEST.yaml context_domains must exist as a file in the bundle's
    reference-workspace/.

    Tier-frontmatter assertion removed per ADR-287 D3: tier system was
    operationally dissolved by ADR-261/262 D2 (fork strips frontmatter,
    doesn't gate on tier values). File-presence is the load-bearing
    assertion the test should preserve.
    """
    active_programs = _list_active_programs()
    assert active_programs, "no active programs found in docs/programs/"

    for program_dir in active_programs:
        manifest = yaml.safe_load((program_dir / "MANIFEST.yaml").read_text())
        ref_root = program_dir / "reference-workspace"
        assert ref_root.is_dir(), (
            f"active program '{program_dir.name}' has no reference-workspace/ "
            f"directory. ADR-230 D2 requires all program-shaped substrate "
            f"templates to live there."
        )

        for domain in manifest.get("context_domains", []):
            domain_path = domain.get("path")
            authored = domain.get("authored_substrate") or []
            for filename in authored:
                ref_file = ref_root / "operation" / domain_path / filename
                assert ref_file.exists(), (
                    f"program '{program_dir.name}' MANIFEST declares "
                    f"context_domains[{domain_path}].authored_substrate "
                    f"includes '{filename}', but the template file is "
                    f"missing at {ref_file.relative_to(REPO_ROOT)}. "
                    f"ADR-230 D2: bundle reference-workspace is the only "
                    f"source of program-shaped substrate templates."
                )


def test_alpha_trader_bundle_has_operator_profile_and_risk():
    """ADR-230 Commit 1 specifically shipped these two files. Pin them
    so a future regression that removes them surfaces here."""
    bundle = PROGRAMS_ROOT / "alpha-trader" / "reference-workspace"
    op_profile = bundle / "operation" / "trading" / "_operator_profile.md"
    risk = bundle / "operation" / "trading" / "_risk.md"
    assert op_profile.exists(), (
        "alpha-trader bundle missing _operator_profile.md template. "
        "Was added in ADR-230 Commit 1; do not remove without superseding ADR-230."
    )
    assert risk.exists(), (
        "alpha-trader bundle missing _risk.md template. "
        "Was added in ADR-230 Commit 1; do not remove without superseding ADR-230."
    )


# =============================================================================
# D5 + D7 — deletion regression guards
# =============================================================================


def test_no_orphan_alpha_mandate():
    """ADR-230 D7: docs/alpha/personas/alpha-trader/MANDATE.md was deleted
    in favor of the bundle's reference-workspace MANDATE.md as the single
    source of truth. Recreating it would re-introduce the dual-source bug
    ADR-230 fixed."""
    assert not BANNED_ORPHAN_MANDATE.exists(), (
        f"{BANNED_ORPHAN_MANDATE.relative_to(REPO_ROOT)} should not exist. "
        f"ADR-230 D7 deleted it; the bundle's reference-workspace MANDATE.md "
        f"is the single source of truth. If you need to override MANDATE for "
        f"a specific alpha persona, use docs/alpha/personas/{{slug}}/overrides/ "
        f"per ADR-230 D6."
    )


def test_no_parallel_scaffold():
    """ADR-230 D5: api/scripts/alpha_ops/scaffold_trader.py was deleted
    in favor of activate_persona.py as the single program-agnostic
    activation harness. Recreating it would re-introduce the parallel-
    scaffold bug ADR-230 fixed."""
    assert not BANNED_PARALLEL_SCAFFOLD.exists(), (
        f"{BANNED_PARALLEL_SCAFFOLD.relative_to(REPO_ROOT)} should not exist. "
        f"ADR-230 D5 deleted it; activate_persona.py is the single program-"
        f"agnostic activation harness. If alpha-trader needs program-shaped "
        f"task instances, edit docs/programs/alpha-trader/tasks.yaml — that's "
        f"the single source post-ADR-230."
    )


def test_activate_persona_exists():
    """Positive guard: the replacement harness must be present."""
    activate = REPO_ROOT / "api" / "scripts" / "alpha_ops" / "activate_persona.py"
    assert activate.exists(), (
        "api/scripts/alpha_ops/activate_persona.py is missing. ADR-230 D5 "
        "requires this file as the single activation harness."
    )


# =============================================================================
# D2 — program-default tasks live in tasks.yaml, not Python
# =============================================================================


def test_alpha_trader_recurrences_yaml_carries_default_recurrences():
    """ADR-230 D2 + ADR-231 cutover + ADR-393 split: program-default scheduled
    work lives at docs/programs/{program}/reference-workspace/ across TWO files.

    ADR-393: recurrences are JUDGMENT-only (_recurrences.yaml); deterministic
    intake is CAPTURES (_captures.yaml, run by the capture lane). The trader's
    mechanical mirrors (track-positions/account/orders, track-regime,
    track-universe, mirror-signal-state) moved from _recurrences.yaml to
    _captures.yaml — same primitives, same cadence, new dispatch home. This
    assertion pins the post-split shape.
    """
    ref = PROGRAMS_ROOT / "alpha-trader" / "reference-workspace"
    recurrences_yaml = ref / "_recurrences.yaml"
    captures_yaml = ref / "_captures.yaml"
    assert recurrences_yaml.exists(), "alpha-trader/reference-workspace/_recurrences.yaml missing"
    assert captures_yaml.exists(), (
        "alpha-trader/reference-workspace/_captures.yaml missing — ADR-393 "
        "requires the mechanical mirrors to ship as captures"
    )

    rec_slugs = {r.get("slug") for r in (yaml.safe_load(recurrences_yaml.read_text()) or {}).get("recurrences") or []}
    cap_entries = (yaml.safe_load(captures_yaml.read_text()) or {}).get("captures") or []
    cap_slugs = {c.get("slug") for c in cap_entries}

    # Judgment recurrences the bundle ships (deliverable cadence lives in
    # _preferences.yaml separately, Reviewer-authored per ADR-275).
    expected_recurrences = {"outcome-reconciliation", "signal-evaluation"}
    missing_rec = expected_recurrences - rec_slugs
    assert not missing_rec, (
        f"alpha-trader _recurrences.yaml missing judgment recurrences: {missing_rec}."
    )

    # Deterministic-intake captures the bundle ships (ADR-393).
    expected_captures = {
        "track-universe", "track-regime", "track-account",
        "track-orders", "track-positions", "mirror-signal-state",
    }
    missing_cap = expected_captures - cap_slugs
    assert not missing_cap, (
        f"alpha-trader _captures.yaml missing captures: {missing_cap}. "
        f"ADR-393: the mechanical mirrors ship as captures, not recurrences."
    )

    # The split is clean: no @primitive directive survives in a recurrence, and
    # no recurrence carries a `mode` field (retired by ADR-393).
    for r in (yaml.safe_load(recurrences_yaml.read_text()) or {}).get("recurrences") or []:
        assert "@primitive:" not in (r.get("prompt") or ""), (
            f"recurrence '{r.get('slug')}' still carries a @primitive directive — "
            f"it must move to _captures.yaml (ADR-393)"
        )
        assert "mode" not in r, (
            f"recurrence '{r.get('slug')}' still carries a `mode` field — retired by ADR-393"
        )
    # Every capture carries a @primitive directive (that's what the lane runs).
    for c in cap_entries:
        assert "@primitive:" in (c.get("primitive") or ""), (
            f"capture '{c.get('slug')}' missing a @primitive directive"
        )


# =============================================================================
# D6 — override directories are opt-in
# =============================================================================


def test_alpha_trader_2_overrides_present():
    """alpha-trader-2 dogfoods kvk's stat-arb voice; per ADR-230 D6 the
    differing files live in the persona overrides directory."""
    overrides = REPO_ROOT / "docs" / "alpha" / "personas" / "alpha-trader-2" / "overrides"
    assert overrides.is_dir(), "alpha-trader-2 overrides directory missing"
    assert (overrides / "context" / "_shared" / "MANDATE.md").exists()
    assert (overrides / "context" / "trading" / "_operator_profile.md").exists()
    assert (overrides / "context" / "trading" / "_risk.md").exists()
    assert (overrides / "README.md").exists(), (
        "alpha-trader-2 overrides should include a README documenting "
        "which files differ from the bundle template and why."
    )


# test_alpha_trader_no_overrides_directory removed per ADR-287 D3.
# Original assertion ("alpha-trader runs bundle as-is") was an
# operator-preference statement, not an architectural invariant.
# Subsequent ADRs (notably ADR-284 Phase 3) led to legitimate
# operator overrides landing for alpha-trader. The conformance test
# this file ships post-ADR-287 doesn't assert the absence of overrides;
# it asserts presence of required substrate per ADR.
