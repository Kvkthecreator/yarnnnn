"""Regression gate for ADR-275 — Introspection cadence is Reviewer-authored.

Bundle's _recurrences.yaml no longer ships judgment cadence (introspection,
housekeeping, deliverable production). Operator preferences live at
/workspace/context/_shared/_preferences.yaml. Reviewer reads preferences
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

PRESERVED_SLUGS = (
    "track-positions",
    "track-account",
    "track-orders",
    "track-regime",
    "track-universe",
    "signal-evaluation",
    "trade-proposal",
    "outcome-reconciliation",
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
    path = (
        REPO_ROOT
        / "docs"
        / "programs"
        / "alpha-trader"
        / "reference-workspace"
        / "context"
        / "_shared"
        / "_preferences.yaml"
    )
    if not path.exists():
        _bad("bundle _preferences.yaml present", f"missing: {path}")
        return
    _ok("bundle ships _preferences.yaml in context/_shared/")

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
    specs_dir = REPO_ROOT / "docs" / "programs" / "alpha-trader" / "reference-workspace" / "specs"
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
# 4. SHARED_PREFERENCES_PATH constant + default lock
# ---------------------------------------------------------------------------

def test_workspace_paths_extended() -> None:
    from services.workspace_paths import (
        SHARED_PREFERENCES_PATH,
        DEFAULT_REVIEWER_WRITE_LOCKS,
    )

    if SHARED_PREFERENCES_PATH == "context/_shared/_preferences.yaml":
        _ok("SHARED_PREFERENCES_PATH constant correct")
    else:
        _bad(
            "SHARED_PREFERENCES_PATH value",
            f"expected 'context/_shared/_preferences.yaml', got {SHARED_PREFERENCES_PATH!r}",
        )

    if SHARED_PREFERENCES_PATH in DEFAULT_REVIEWER_WRITE_LOCKS:
        _ok("_preferences.yaml in DEFAULT_REVIEWER_WRITE_LOCKS")
    else:
        _bad(
            "_preferences.yaml lock policy",
            f"SHARED_PREFERENCES_PATH not in DEFAULT_REVIEWER_WRITE_LOCKS: "
            f"{DEFAULT_REVIEWER_WRITE_LOCKS}",
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
    from agents.reviewer_agent import _PERSONA_FRAME

    needles = [
        "_preferences.yaml",       # named as the substrate
        "pre-loaded",              # frame names the structural delivery mechanism
        "active: true",            # the active-flag contract
        "Schedule",                # the primitive to call
        "Bundles ship",            # the bundle-vs-Reviewer split
    ]
    # Case-insensitive
    lower = _PERSONA_FRAME.lower()
    missing = []
    for n in needles:
        if n.lower() not in lower:
            missing.append(n)
    if not missing:
        _ok("persona frame names _preferences.yaml as pre-loaded + Schedule contract (refined to ~10 lines)")
    else:
        _bad("persona frame ADR-275 section", f"missing markers: {missing}")


# ---------------------------------------------------------------------------
# 6. Persona-frame post-run-2: collapsed to short structural instruction
# ---------------------------------------------------------------------------

def test_persona_frame_first_wake_guardrail_updated() -> None:
    from agents.reviewer_agent import _PERSONA_FRAME

    # ADR-274's old "scaffold cadence is in place" guardrail must be gone
    # (post-ADR-275 there is no scaffold judgment cadence to observe).
    if "scaffold cadence is in place" not in _PERSONA_FRAME:
        _ok("legacy ADR-274 'scaffold cadence is in place' phrasing removed")
    else:
        _bad(
            "persona frame first-wake guardrail",
            "still contains contradictory 'scaffold cadence is in place'",
        )

    # ADR-275-refinement: the long narrative "first-wake bootstrap" /
    # "ADR-275 in plain terms" paragraphs are collapsed. The persona
    # frame is no longer the *vehicle* for telling the Reviewer about
    # _preferences.yaml — pre-loading is. So phrases like "First wake
    # after workspace activation: there is no scaffold judgment cadence"
    # from the run-1 verbose version should NOT be there.
    long_run1_phrase = "First wake after workspace activation"
    if long_run1_phrase not in _PERSONA_FRAME:
        _ok("verbose run-1 first-wake narrative collapsed (delivery via pre-load, not prose)")
    else:
        _bad(
            "persona frame collapse",
            "still contains verbose run-1 'First wake after workspace activation' narrative",
        )


# ---------------------------------------------------------------------------
# 6b. ReviewerContext + _build_user_message structurally pre-load _preferences.yaml
# ---------------------------------------------------------------------------

def test_preferences_yaml_is_preloaded_in_wake_envelope() -> None:
    """ADR-275 refinement (run-2): _preferences.yaml is a load-bearing
    input for cadence-authoring. The Reviewer perceives it via the wake
    envelope, not via a tool call. Same structural shape as MANDATE /
    AUTONOMY / IDENTITY / principles."""
    from agents.reviewer_agent import ReviewerContext

    annotations = getattr(ReviewerContext, "__annotations__", {})
    if "preferences_yaml" in annotations:
        _ok("ReviewerContext.preferences_yaml field declared (parallel to mandate_md, autonomy_md)")
    else:
        _bad(
            "ReviewerContext.preferences_yaml field",
            f"expected preferences_yaml in annotations, got {list(annotations.keys())}",
        )

    import inspect
    import agents.reviewer_agent as mod
    src = inspect.getsource(mod._build_user_message)
    if 'ctx.get("preferences_yaml")' in src:
        _ok("_build_user_message reads ctx['preferences_yaml']")
    else:
        _bad(
            "_build_user_message preferences injection",
            "expected ctx.get('preferences_yaml') in _build_user_message body",
        )

    if "_preferences.yaml — Operator's deliverable cadence preferences" in src:
        _ok("_build_user_message renders the named _preferences.yaml block header")
    else:
        _bad(
            "_build_user_message preferences header",
            "expected named header for the _preferences.yaml block in the envelope",
        )


# ---------------------------------------------------------------------------
# 6c. feed.py addressed-trigger site loads SHARED_PREFERENCES_PATH + AUTONOMY
# ---------------------------------------------------------------------------

def test_feed_addressed_site_loads_preferences_and_autonomy() -> None:
    """Addressed-trigger envelope (feed.py) delivers _preferences.yaml +
    AUTONOMY.md via the shared `load_reviewer_governance_envelope` helper.

    Post-ADR-276 (run-2 refinement), the inline 9-path gather in feed.py
    is migrated to call the canonical helper at
    `services/reviewer_envelope.py`. The helper's gate
    (test_adr276_reactive_envelope.py) verifies the substrate actually
    reaches the envelope. This gate now verifies the structural delegation
    is in place.
    """
    src = (REPO_ROOT / "api" / "routes" / "feed.py").read_text()
    if "from services.reviewer_envelope import load_reviewer_governance_envelope" in src:
        _ok("feed.py imports the shared governance-envelope helper (ADR-276)")
    else:
        _bad(
            "feed.py envelope helper",
            "expected import of load_reviewer_governance_envelope from "
            "services.reviewer_envelope (Singular Implementation per ADR-276)",
        )
    if "**governance_envelope" in src:
        _ok("feed.py context bag dict-spreads governance_envelope (incl. preferences + AUTONOMY)")
    else:
        _bad(
            "feed.py context bag delegation",
            "expected '**governance_envelope' in invoke_reviewer call",
        )


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
    test_feed_addressed_site_loads_preferences_and_autonomy()  # run-2 refinement + audit fix
    test_mechanical_mirrors_preserved()
    test_adr275_doc_exists()

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
