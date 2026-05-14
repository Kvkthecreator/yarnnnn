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
    from agents.reviewer_agent import _PERSONA_FRAME

    needles = [
        "_preferences.yaml",
        "ADR-275",
        "Bundles do NOT ship judgment-cadence",
        "Operator declares",
        "you author",  # case-insensitive will be tested below
    ]
    # Case-insensitive
    lower = _PERSONA_FRAME.lower()
    missing = []
    for n in needles:
        if n.lower() not in lower:
            missing.append(n)
    if not missing:
        _ok("persona frame names _preferences.yaml + ADR-275 + cadence-authoring contract")
    else:
        _bad("persona frame ADR-275 section", f"missing markers: {missing}")


# ---------------------------------------------------------------------------
# 6. ADR-274 mention of "scaffold cadence is in place" must be gone
# ---------------------------------------------------------------------------

def test_persona_frame_first_wake_guardrail_updated() -> None:
    from agents.reviewer_agent import _PERSONA_FRAME

    # The old ADR-274 first-wake guardrail said "scaffold cadence is in
    # place" — this is now wrong (post-ADR-275 there's no scaffold
    # judgment cadence). Verify the contradictory phrasing was removed.
    if "scaffold cadence is in place" not in _PERSONA_FRAME:
        _ok("legacy 'scaffold cadence is in place' phrasing removed from persona frame")
    else:
        _bad(
            "persona frame first-wake guardrail",
            "still contains contradictory 'scaffold cadence is in place' from ADR-274 pre-ADR-275",
        )

    # The new first-wake framing should name "there is no scaffold judgment cadence"
    if "no scaffold judgment cadence" in _PERSONA_FRAME.lower() or "scaffold judgment" in _PERSONA_FRAME.lower():
        _ok("persona frame names new first-wake framing (no scaffold judgment cadence)")
    else:
        _bad(
            "persona frame new first-wake framing",
            "missing 'no scaffold judgment cadence' framing",
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
