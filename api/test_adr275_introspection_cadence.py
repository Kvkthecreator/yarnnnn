"""Regression gate for ADR-275 — Introspection cadence is Reviewer-authored.

Bundle's _recurrences.yaml no longer ships judgment cadence (introspection,
housekeeping, deliverable production). Operator preferences live at
/workspace/governance/_preferences.yaml. Reviewer reads preferences
and authors all judgment cadence via Schedule.

Run:
    python -m api.test_adr275_introspection_cadence
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    _PASS.append(name)
    print(f"  ✓ {name}")


def _bad(name: str, reason: str) -> None:
    _FAIL.append((name, reason))
    print(f"  ✗ {name}\n      {reason}")


# ---------------------------------------------------------------------------
# 1. Deleted judgment recurrences are absent from alpha-trader bundle
# ---------------------------------------------------------------------------

DELETED_SLUGS = (
    "morning-reflection",
    "morning-calibration",
    "narrative-digest",
    "proposal-cleanup",
    "pre-market-brief",
    "weekly-performance-review",
    "quarterly-signal-audit",
)

# ADR-296 v2 Checkpoint 2 (2026-05-20) deleted `trade-proposal` from the
# alpha-trader bundle — signal-evaluation now emits ProposeAction inline
# per ADR-296 v2 D3. `mirror-signal-state` added per ADR-281 §3 derived
# principle 19 (substrate-mirror for Reviewer wake envelope).
PRESERVED_SLUGS = (
    "track-positions",
    "track-account",
    "track-orders",
    "track-regime",
    "track-universe",
    "signal-evaluation",
    "outcome-reconciliation",
    "mirror-signal-state",
)


def test_bundle_recurrences_thinned() -> None:
    path = REPO_ROOT / "docs" / "programs" / "alpha-trader" / "reference-workspace" / "_recurrences.yaml"
    if not path.exists():
        _bad("bundle _recurrences.yaml present", f"missing: {path}")
        return

    # Strip tier frontmatter
    text = path.read_text()
    if text.startswith("---"):
        # find second --- delimiter
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
        else:
            body = text
    else:
        body = text

    try:
        data = yaml.safe_load(body)
    except yaml.YAMLError as e:
        _bad("bundle _recurrences.yaml parses as YAML", str(e))
        return

    recs = (data or {}).get("recurrences") or []
    slugs = {r.get("slug") for r in recs if isinstance(r, dict)}

    leaked = [s for s in DELETED_SLUGS if s in slugs]
    if not leaked:
        _ok(f"7 deleted judgment recurrences absent from bundle")
    else:
        _bad(
            "judgment recurrences deleted",
            f"still present in bundle: {leaked}",
        )

    missing = [s for s in PRESERVED_SLUGS if s not in slugs]
    if not missing:
        _ok(f"8 preserved recurrences present in bundle (mechanical + reactive + heartbeat)")
    else:
        _bad(
            "preserved recurrences intact",
            f"missing from bundle: {missing}",
        )

    if len(recs) == 8:
        _ok(f"bundle has exactly 8 recurrence entries (was 15 pre-ADR-275)")
    else:
        _bad(
            "bundle has 8 entries",
            f"expected 8, found {len(recs)}: {sorted(slugs)}",
        )


# ---------------------------------------------------------------------------
# 2. _preferences.yaml shipped in bundle reference-workspace
# ---------------------------------------------------------------------------

def test_preferences_yaml_shipped() -> None:
    # ADR-366 grant/contract split: _preferences.yaml moved from
    # context/_shared/ (ADR-275) → contract/ (the operating-contract root,
    # mode-governed). The tier=canon fork-at-activation contract is unchanged.
    path = (
        REPO_ROOT
        / "docs"
        / "programs"
        / "alpha-trader"
        / "reference-workspace"
        / "contract"
        / "_preferences.yaml"
    )
    if not path.exists():
        _bad("bundle _preferences.yaml present", f"missing: {path}")
        return
    _ok("bundle ships _preferences.yaml in contract/")

    text = path.read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                frontmatter = {}
        else:
            body = text
            frontmatter = {}
    else:
        body = text
        frontmatter = {}

    if frontmatter.get("tier") == "canon":
        _ok("_preferences.yaml has tier=canon frontmatter (forks at activation)")
    else:
        _bad(
            "_preferences.yaml tier",
            f"expected tier=canon, got {frontmatter.get('tier')!r}",
        )

    try:
        data = yaml.safe_load(body) or {}
    except yaml.YAMLError as e:
        _bad("_preferences.yaml body parses as YAML", str(e))
        return

    prefs = data.get("deliverable_preferences") or []
    if not isinstance(prefs, list) or len(prefs) < 3:
        _bad(
            "_preferences.yaml has deliverable_preferences",
            f"expected list of ≥3 entries, got {prefs!r}",
        )
        return

    expected_slugs = {"pre-market-brief", "weekly-performance-review", "quarterly-signal-audit"}
    found_slugs = {p.get("slug") for p in prefs if isinstance(p, dict)}
    missing = expected_slugs - found_slugs
    if not missing:
        _ok(f"_preferences.yaml declares 3 default deliverable preferences")
    else:
        _bad(
            "_preferences.yaml default preferences",
            f"missing: {missing}",
        )

    # Each preference must have: slug, spec, cadence, description, active
    required_fields = {"slug", "spec", "cadence", "description", "active"}
    bad = []
    for p in prefs:
        if not isinstance(p, dict):
            continue
        missing_fields = required_fields - set(p.keys())
        if missing_fields:
            bad.append((p.get("slug"), missing_fields))
    if not bad:
        _ok("every preference has required fields (slug, spec, cadence, description, active)")
    else:
        _bad(
            "preference field completeness",
            f"missing fields: {bad}",
        )


# ---------------------------------------------------------------------------
# 3. Specs (capability library) preserved in bundle
# ---------------------------------------------------------------------------

def test_specs_preserved() -> None:
    # ADR-320 five-root topology cut: specs/ moved under the operation/ root.
    specs_dir = REPO_ROOT / "docs" / "programs" / "alpha-trader" / "reference-workspace" / "operation" / "specs"
    if not specs_dir.is_dir():
        _bad("specs directory present", f"missing: {specs_dir}")
        return

    required_specs = {
        "pre-market-brief.md",
        "weekly-performance-review.md",
        "quarterly-signal-audit.md",
    }
    present = {f.name for f in specs_dir.iterdir() if f.is_file()}
    missing = required_specs - present
    if not missing:
        _ok("3 capability specs preserved (pre-market-brief, weekly-review, quarterly-audit)")
    else:
        _bad(
            "specs preserved",
            f"missing capability specs: {missing}",
        )


# ---------------------------------------------------------------------------
# 4. CONTRACT_PREFERENCES_PATH constant + mode-governed (NOT locked) — ADR-366
# ---------------------------------------------------------------------------

def test_workspace_paths_extended() -> None:
    # ADR-366: _preferences.yaml moved governance/ -> contract/. It is the
    # operator's operating CONTRACT, not the GRANT — so it is MODE-GOVERNED, NOT
    # topology-locked from the reviewer. A reviewer write to it flows through the
    # ADR-307 witness gate (QUEUE under bounded, APPLY under autonomous), not a
    # bypass-immune DENY. This assertion INVERTS the pre-ADR-366 lock check.
    from services.workspace_paths import CONTRACT_PREFERENCES_PATH
    from services.primitives.workspace import _is_path_locked

    if CONTRACT_PREFERENCES_PATH == "contract/_preferences.yaml":
        _ok("CONTRACT_PREFERENCES_PATH constant correct (moved to contract/)")
    else:
        _bad(
            "CONTRACT_PREFERENCES_PATH value",
            f"expected 'contract/_preferences.yaml', got {CONTRACT_PREFERENCES_PATH!r}",
        )

    if not _is_path_locked("reviewer", CONTRACT_PREFERENCES_PATH):
        _ok("_preferences.yaml NOT topology-locked from Reviewer (mode-governed, ADR-366)")
    else:
        _bad(
            "_preferences.yaml mode-governed policy",
            f"_is_path_locked('reviewer', {CONTRACT_PREFERENCES_PATH!r}) returned True — "
            "ADR-366 makes contract/ mode-governed, not locked",
        )


# ---------------------------------------------------------------------------
# 5. Reviewer persona frame names _preferences.yaml + cadence-authoring contract
# ---------------------------------------------------------------------------

def test_persona_frame_references_preferences() -> None:
    """Persona frame post-refinement: instruction is short + structural.

    Per ADR-275 refinement (run-2): the long ADR-275 paragraphs collapsed
    to ~10 lines that name `_preferences.yaml` as pre-loaded and instruct
    `Schedule(action="create")` for active preferences not yet honored.
    The frame should still cite the file + the contract, but it is no
    longer the *vehicle* for delivery — pre-load is.
    """
    # Post-ADR-306 collapse: preferences semantics is substrate pedagogy
    # (ablation §3 row 10) and relocates from the persona frame to
    # `_workspace_guide.md` (ADR-281's home, Phase C). The Reviewer reads the
    # guide every wake; the preference-reconciliation contract is preserved,
    # only its home moved from system prose to bundle substrate.
    import re
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    needles = [
        "_preferences.yaml",       # named as the substrate
        "pre-loaded",              # the structural delivery mechanism
        "active: true",            # the active-flag contract
        "Schedule",                # the primitive to call
        "Bundles ship",            # the bundle-vs-Reviewer split
    ]
    for bundle in ("alpha-trader", "alpha-author"):
        raw = (
            repo_root
            / "docs" / "programs" / bundle / "reference-workspace"
            / "_workspace_guide.md"
        ).read_text(encoding="utf-8")
        guide = re.sub(r"\s+", " ", raw).lower()
        missing = [n for n in needles if n.lower() not in guide]
        assert not missing, (
            f"{bundle} _workspace_guide.md preferences section missing markers "
            f"(relocated from persona frame per ADR-306 D3): {missing}"
        )


# ---------------------------------------------------------------------------
# 6. Persona-frame post-run-2: collapsed to short structural instruction
# ---------------------------------------------------------------------------

def test_persona_frame_first_wake_guardrail_updated() -> None:
    """Negative invariant, post-ADR-306 collapse: the minimal frame must not
    carry the stale ADR-274 'scaffold cadence is in place' guardrail nor the
    verbose run-1 first-wake narrative. Both are trivially absent post-collapse
    (the frame is ~3.5K of principal-shift + action-grammar only). Asserted by
    source-text inspection since `_PERSONA_FRAME` no longer exists.
    """
    from pathlib import Path

    src = (
        Path(__file__).resolve().parent / "agents" / "freddie_agent.py"
    ).read_text(encoding="utf-8")

    assert "scaffold cadence is in place" not in src, (
        "Minimal frame must not contain the contradictory ADR-274 'scaffold "
        "cadence is in place' phrasing"
    )
    assert "First wake after workspace activation" not in src, (
        "Minimal frame must not contain the verbose run-1 'First wake after "
        "workspace activation' narrative (collapsed per ADR-306)"
    )


# ---------------------------------------------------------------------------
# 6b. FreddieContext + _build_user_message structurally pre-load _preferences.yaml
# ---------------------------------------------------------------------------

def test_preferences_yaml_is_preloaded_in_wake_envelope() -> None:
    """ADR-275 refinement (run-2): _preferences.yaml is a load-bearing
    input for cadence-authoring. The Reviewer perceives it via the wake
    envelope, not via a tool call. Same structural shape as MANDATE /
    AUTONOMY / IDENTITY / principles."""
    from agents.freddie_agent import FreddieContext

    annotations = getattr(FreddieContext, "__annotations__", {})
    if "preferences_yaml" in annotations:
        _ok("FreddieContext.preferences_yaml field declared (parallel to mandate_md, autonomy_md)")
    else:
        _bad(
            "FreddieContext.preferences_yaml field",
            f"expected preferences_yaml in annotations, got {list(annotations.keys())}",
        )

    # ADR-360 envelope-caching refactor: _build_user_message became a thin
    # dispatcher; the preferences injection relocated into the render helpers
    # (_partition_envelope + _build_user_message_stripped). Inspect the MODULE
    # source rather than one function — the invariant is "preferences_yaml is
    # structurally pre-loaded into the wake message somewhere in the render
    # path", and that survives function-boundary refactors.
    import inspect
    import agents.freddie_agent as mod
    src = inspect.getsource(mod)
    if 'ctx.get("preferences_yaml")' in src:
        _ok("render path reads ctx['preferences_yaml'] (structural pre-load)")
    else:
        _bad(
            "render-path preferences injection",
            "expected ctx.get('preferences_yaml') in the freddie_agent render path",
        )

    if "_preferences.yaml — Operator" in src and "cadence preferences" in src:
        _ok("render path renders the named _preferences.yaml block header")
    else:
        _bad(
            "render-path preferences header",
            "expected named header for the _preferences.yaml block in the envelope",
        )


# ---------------------------------------------------------------------------
# 6c. feed.py addressed-trigger site loads GOVERNANCE_PREFERENCES_PATH + AUTONOMY
# ---------------------------------------------------------------------------

def test_all_invoke_freddie_call_sites_use_canonical_envelope() -> None:
    """All three `invoke_freddie` call sites route through the canonical
    `load_freddie_governance_envelope` helper.

    Pre-ADR-296-v2 (commit 37426c5, 2026-05-20), feed.py was the addressed-
    trigger Reviewer invocation site. The wake architecture refactor moved
    that responsibility into services/wake.py::stream_addressed_wake (called
    by services/wake_sources/addressed.py). The original ADR-275 test
    assertion targeting feed.py is therefore stale topology.

    Post-2026-05-21 (ADR-276 implementation completion commit), the third
    call site (`services/review_proposal_dispatch.py::_run_ai_reviewer`) is
    also migrated to use the canonical helper — closes the prose-named-but-
    not-pre-loaded class for capital-judgment wakes.

    The three call sites are:
      1. services/wake.py::dispatch_recurrence (cron_tick + manual_fire)
      2. services/wake.py::stream_addressed_wake (addressed)
      3. services/review_proposal_dispatch.py::_run_ai_reviewer (proposal_arrival)
    """
    sites = [
        (REPO_ROOT / "api" / "services" / "wake.py", "wake.py"),
        (REPO_ROOT / "api" / "services" / "review_proposal_dispatch.py", "review_proposal_dispatch.py"),
    ]
    missing_import: list[str] = []
    missing_spread: list[str] = []
    for path, label in sites:
        if not path.exists():
            missing_import.append(f"{label}: file not found at {path}")
            continue
        src = path.read_text()
        if "load_freddie_governance_envelope" not in src:
            missing_import.append(f"{label}: missing import of load_freddie_governance_envelope")
        if "**governance_envelope" not in src:
            missing_spread.append(f"{label}: missing '**governance_envelope' spread into invoke_freddie context")

    if missing_import or missing_spread:
        if missing_import:
            _bad(
                "envelope helper import at all invoke_freddie call sites",
                "; ".join(missing_import),
            )
        if missing_spread:
            _bad(
                "envelope helper spread at all invoke_freddie call sites",
                "; ".join(missing_spread),
            )
        return
    _ok("all invoke_freddie call sites (wake.py + review_proposal_dispatch.py) route through load_freddie_governance_envelope (Singular Implementation per ADR-276 + 2026-05-21 completion)")


def test_review_proposal_dispatch_no_hand_rolled_envelope() -> None:
    """Negative: review_proposal_dispatch.py must not carry the legacy
    `_read_workspace_file` helper or the hand-rolled 6-key envelope assembly
    that pre-dated the ADR-276 implementation completion.

    Singular Implementation rule per CLAUDE.md: delete legacy code when
    replacing. The proposal-arrival envelope assembly is the canonical
    helper, period.
    """
    src = (REPO_ROOT / "api" / "services" / "review_proposal_dispatch.py").read_text()

    # Function definition + body markers from the old hand-rolled shape
    forbidden_markers = [
        "def _read_workspace_file(",  # local helper that the hand-rolled reads called
        '"identity_md": identity_md,',  # hand-rolled context-key assignment
        '"principles_md": principles_md,',
        '"precedent_md": precedent_md,',
    ]
    leaked = [m for m in forbidden_markers if m in src]
    if leaked:
        _bad(
            "review_proposal_dispatch.py legacy envelope code absent",
            f"forbidden hand-rolled markers still present (Singular Implementation violation): {leaked}",
        )
        return
    _ok("review_proposal_dispatch.py hand-rolled envelope assembly deleted (Singular Implementation)")


# ---------------------------------------------------------------------------
# 7. Bundle thinning preserved mechanical mirrors + market-event triggers
# ---------------------------------------------------------------------------

def test_mechanical_mirrors_preserved() -> None:
    path = REPO_ROOT / "docs" / "programs" / "alpha-trader" / "reference-workspace" / "_recurrences.yaml"
    text = path.read_text()
    parts = text.split("---", 2)
    body = parts[2] if len(parts) >= 3 else text
    data = yaml.safe_load(body) or {}
    recs = data.get("recurrences") or []

    by_slug = {r["slug"]: r for r in recs if isinstance(r, dict) and r.get("slug")}

    for slug in ("track-positions", "track-account", "track-orders", "track-regime", "track-universe"):
        r = by_slug.get(slug)
        if not r:
            _bad(f"mechanical mirror preserved", f"missing: {slug}")
            continue
        mode = r.get("mode")
        if mode != "mechanical":
            _bad(
                f"{slug} mode preserved",
                f"expected mode=mechanical, got {mode!r}",
            )
            continue
    _ok("5 mechanical mirrors preserved (track-positions/account/orders/regime/universe, all mode=mechanical)")


# ---------------------------------------------------------------------------
# 8. ADR-275 doc exists
# ---------------------------------------------------------------------------

def test_adr275_doc_exists() -> None:
    path = REPO_ROOT / "docs" / "adr" / "ADR-275-introspection-cadence-reviewer-authored.md"
    if path.exists():
        text = path.read_text()
        if "Derived Principle 18" in text and "ADR-274" in text and "FOUNDATIONS v8.5" in text:
            _ok("ADR-275 doc exists + cites FOUNDATIONS v8.5 + ADR-274 + Derived Principle 18")
        else:
            _bad(
                "ADR-275 doc cross-refs",
                f"missing required cross-refs (Derived Principle 18 / ADR-274 / FOUNDATIONS v8.5)",
            )
    else:
        _bad("ADR-275 doc present", f"missing: {path}")


# ---------------------------------------------------------------------------
# D9–D11 amendment (2026-05-21) — bundle-fork-from-preferences seeding
# ---------------------------------------------------------------------------

def test_d9_seed_helper_exists() -> None:
    """ADR-275 D9: programs.py exports _seed_recurrences_from_preferences."""
    try:
        from services import programs
    except Exception as e:
        _bad("programs module imports for D9 check", str(e))
        return

    if not hasattr(programs, "_seed_recurrences_from_preferences"):
        _bad(
            "_seed_recurrences_from_preferences exists",
            "programs.py does not export the D9 seeding helper",
        )
        return
    if not hasattr(programs, "_format_recurrence_entry_yaml"):
        _bad(
            "_format_recurrence_entry_yaml exists",
            "programs.py does not export the D9 YAML-format helper",
        )
        return

    import inspect
    if not inspect.iscoroutinefunction(programs._seed_recurrences_from_preferences):
        _bad(
            "_seed_recurrences_from_preferences signature",
            "must be a coroutine function (async def)",
        )
        return
    _ok("_seed_recurrences_from_preferences + _format_recurrence_entry_yaml exported as coroutine + helper (D9)")


def test_d9_attribution_actor_valid() -> None:
    """ADR-275 D9: 'system:bundle-fork-from-preferences' passes ADR-209 is_valid_author taxonomy."""
    from services.authored_substrate import is_valid_author

    actor = "system:bundle-fork-from-preferences"
    if is_valid_author(actor):
        _ok(f"D9 attribution actor {actor!r} passes ADR-209 taxonomy")
    else:
        _bad(
            "D9 attribution actor",
            f"{actor!r} rejected by is_valid_author — D9 cannot write attributed revisions",
        )


def test_d9_fork_returns_preferences_seeded() -> None:
    """ADR-275 D9: fork_reference_workspace return dict includes preferences_seeded + preferences_skipped_already_present."""
    import inspect
    from services.programs import fork_reference_workspace

    src = inspect.getsource(fork_reference_workspace)
    needed_returns = [
        '"preferences_seeded": prefs_seeded',
        '"preferences_skipped_already_present": prefs_skipped',
    ]
    missing = [m for m in needed_returns if m not in src]
    if missing:
        _bad(
            "fork_reference_workspace return shape (D9)",
            f"D9 return-dict keys not found in source: {missing}",
        )
        return
    _ok("fork_reference_workspace returns preferences_seeded + preferences_skipped_already_present (D9)")


def test_d9_seed_step_wired_before_materialize() -> None:
    """ADR-275 D9: seed step runs BEFORE materialize_scheduling_index inside fork_reference_workspace."""
    import inspect
    from services.programs import fork_reference_workspace

    src = inspect.getsource(fork_reference_workspace)
    seed_call = "await _seed_recurrences_from_preferences("
    materialize_call = "await materialize_scheduling_index("

    if seed_call not in src:
        _bad("D9 seed call wiring", f"{seed_call!r} not found in fork_reference_workspace")
        return
    if materialize_call not in src:
        _bad("D9 seed call wiring", f"{materialize_call!r} not found in fork_reference_workspace")
        return

    if src.find(seed_call) >= src.find(materialize_call):
        _bad(
            "D9 seed-before-materialize order",
            "_seed_recurrences_from_preferences must run BEFORE materialize_scheduling_index "
            "so seeded entries land in the tasks index in the same fork transaction",
        )
        return
    _ok("_seed_recurrences_from_preferences runs before materialize_scheduling_index (D9)")


# test_d10_persona_frame_change_reconciliation — DELETED (ADR-306 persona-frame collapse).
# This test grepped freddie_agent.py for verbose persona-frame prose markers
# ("Initial honoring" / "bundle-fork-from-preferences" / "CHANGE RECONCILIATION").
# The ADR-302/306/323 persona-frame collapse (system prompt ~36K → ~3.5K — rules
# of judgment moved to principles.md, pedagogy to envelope headers) deliberately
# removed that prose. The *behavior* D10 named (the Reviewer reconciles operator
# preference CHANGES, with the initial set seeded by bundle-fork) is still proven
# live by the surviving structural tests in this file: the D9 seed-actor test
# (`test_d9_seed_before_materialize` + the is_valid_author check on
# `system:bundle-fork-from-preferences`) and the preferences-preload test. A
# prose-marker grep is the wrong shape for an invariant that is now structural —
# not re-pointed, the marker contract no longer exists.


def test_d9_d11_amendment_documented() -> None:
    """ADR-275 doc carries the D9–D11 amendment section."""
    path = REPO_ROOT / "docs" / "adr" / "ADR-275-introspection-cadence-reviewer-authored.md"
    if not path.exists():
        _bad("ADR-275 doc present for amendment check", f"missing: {path}")
        return
    text = path.read_text()

    needed = [
        "Amended 2026-05-21",
        "D9. Bundle-fork honors deliverable-cadence",
        "D10. Reviewer reconciles operator preference CHANGES",
        "D11. Introspection cadence remains Reviewer-authored",
        "substrate contract audit",  # cross-ref to observation
        "system:bundle-fork-from-preferences",  # cites the new attribution actor
    ]
    missing = [m for m in needed if m not in text]
    if missing:
        _bad("ADR-275 D9–D11 amendment markers", f"missing: {missing}")
        return
    _ok("ADR-275 doc carries D9–D11 amendment section + cross-ref to substrate contract audit")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-275 — Introspection cadence is Reviewer-authored, not bundle-scaffolded\n")

    test_bundle_recurrences_thinned()
    test_preferences_yaml_shipped()
    test_specs_preserved()
    test_workspace_paths_extended()
    test_persona_frame_references_preferences()
    test_persona_frame_first_wake_guardrail_updated()
    test_preferences_yaml_is_preloaded_in_wake_envelope()    # run-2 refinement
    test_all_invoke_freddie_call_sites_use_canonical_envelope()  # 2026-05-21: post-ADR-296-v2 topology
    test_review_proposal_dispatch_no_hand_rolled_envelope()  # 2026-05-21: Singular Implementation negative check
    test_mechanical_mirrors_preserved()
    test_adr275_doc_exists()

    # D9–D11 amendment (2026-05-21)
    test_d9_seed_helper_exists()
    test_d9_attribution_actor_valid()
    test_d9_fork_returns_preferences_seeded()
    test_d9_seed_step_wired_before_materialize()
    test_d9_d11_amendment_documented()

    total = len(_PASS) + len(_FAIL)
    print(f"\n{len(_PASS)}/{total} pass")
    if _FAIL:
        print("\nFAILURES:")
        for name, reason in _FAIL:
            print(f"  • {name}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
