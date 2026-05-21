"""ADR-297 Phase 1 — atomic surfaces registry regression gate.

Asserts the compositor extension emits the `surfaces[]` field with:
- All kernel surfaces always present (12 entries, every slug from
  kernel_surfaces.KERNEL_SURFACES)
- Each kernel surface carries tier="kernel"
- Each entry has the required fields (slug, title, archetype, tier,
  substrate_paths, icon_key, default_pinned, route, summary)
- Archetype is one of the canonical ARCHETYPES enum values
- default_pinned is True only for Feed (per ADR-297 D5)
- Program surfaces emit only when their bundle is active and only
  when the bundle's SURFACES.yaml declares a top-level surfaces[] block
- The existing `composition` field is unchanged (Phase 1 is additive)
- Bad bundle surfaces[] entries are skipped, not raised — kernel
  surfaces still emit

Run: .venv/bin/python api/test_adr297_phase1.py
"""

from __future__ import annotations

import os
import sys

# Make `services.*` importable when running from project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from services.kernel_surfaces import (
    ARCHETYPES,
    KERNEL_SURFACES,
    kernel_surface_entries,
    kernel_surface_slugs,
)

REQUIRED_SURFACE_FIELDS = {
    "slug",
    "title",
    "archetype",
    "substrate_paths",
    "icon_key",
    "default_pinned",
    "route",
    "summary",
    "tier",
}


# =============================================================================
# Test helpers
# =============================================================================

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


# =============================================================================
# Group 1 — kernel_surfaces module hygiene
# =============================================================================


def test_kernel_surfaces_module() -> None:
    print("\n[1] kernel_surfaces module hygiene")

    _assert(
        len(KERNEL_SURFACES) >= 10,
        f"At least 10 kernel surfaces declared (found {len(KERNEL_SURFACES)})",
    )

    slugs = [s["slug"] for s in KERNEL_SURFACES]
    _assert(
        len(slugs) == len(set(slugs)),
        "Kernel surface slugs are unique",
    )

    # Spot-check critical surfaces exist
    expected_slugs = {
        "feed",
        "cadence",
        "delegation",
        "mandate",
        "principles",
        "identity",
        "brand",
        "files",
        "agents",
        "program",
        "queue",
        "activity",
    }
    actual = set(slugs)
    missing = expected_slugs - actual
    _assert(
        not missing,
        f"All canonical kernel surfaces present (missing: {missing or 'none'})",
    )

    # Required fields
    for entry in KERNEL_SURFACES:
        present = set(entry.keys())
        missing_fields = (REQUIRED_SURFACE_FIELDS - {"tier"}) - present
        _assert(
            not missing_fields,
            f"Surface '{entry.get('slug', '?')}' has all required fields "
            f"(missing: {missing_fields or 'none'})",
        )

    # Archetype enum compliance
    for entry in KERNEL_SURFACES:
        _assert(
            entry.get("archetype") in ARCHETYPES,
            f"Surface '{entry['slug']}' archetype '{entry.get('archetype')}' "
            f"is canonical",
        )

    # Feed-only default pin per ADR-297 D5
    pinned_by_default = [s["slug"] for s in KERNEL_SURFACES if s["default_pinned"]]
    _assert(
        pinned_by_default == ["feed"],
        f"Only Feed is default_pinned (found: {pinned_by_default})",
    )


# =============================================================================
# Group 2 — kernel_surface_entries() shape
# =============================================================================


def test_kernel_surface_entries_shape() -> None:
    print("\n[2] kernel_surface_entries() shape")

    entries = kernel_surface_entries()

    _assert(
        len(entries) == len(KERNEL_SURFACES),
        f"Returns one entry per declared surface ({len(entries)} == {len(KERNEL_SURFACES)})",
    )

    # All entries carry tier="kernel"
    tiers = {e["tier"] for e in entries}
    _assert(
        tiers == {"kernel"},
        f"All entries tier='kernel' (found tiers: {tiers})",
    )

    # All required fields present (now including tier)
    for entry in entries:
        missing_fields = REQUIRED_SURFACE_FIELDS - set(entry.keys())
        _assert(
            not missing_fields,
            f"Entry '{entry.get('slug', '?')}' has all required fields "
            f"(missing: {missing_fields or 'none'})",
        )

    # Deep-copy isolation: mutating a returned entry doesn't mutate canonical declaration
    if entries:
        entries[0]["title"] = "MUTATED"
        re_fetched = kernel_surface_entries()
        _assert(
            re_fetched[0]["title"] != "MUTATED",
            "Returned entries are deep-copied (caller mutations don't leak)",
        )


# =============================================================================
# Group 3 — composition_resolver emits surfaces[] (no live bundles)
# =============================================================================


def test_resolver_empty_workspace() -> None:
    print("\n[3] resolver returns kernel surfaces for empty workspace")

    from unittest.mock import MagicMock, patch

    # Mock bundles_active_for_workspace to return [] (empty workspace)
    with patch(
        "services.bundle_reader.bundles_active_for_workspace",
        return_value=[],
    ):
        from services.composition_resolver import resolve_workspace_composition

        result = resolve_workspace_composition(
            user_id="test-user-id", client=MagicMock()
        )

    _assert(
        "surfaces" in result,
        "Result includes 'surfaces' key (additive Phase 1 field)",
    )
    _assert(
        "composition" in result,
        "Result still includes 'composition' key (existing Phase 1 contract preserved)",
    )
    _assert(
        result.get("schema_version") == 1,
        f"schema_version=1 (got: {result.get('schema_version')})",
    )

    surfaces = result.get("surfaces", [])
    surface_slugs = {s["slug"] for s in surfaces}
    expected_slugs = kernel_surface_slugs()
    _assert(
        surface_slugs == expected_slugs,
        f"Empty workspace emits exactly the kernel surfaces "
        f"(missing: {expected_slugs - surface_slugs}, extra: {surface_slugs - expected_slugs})",
    )

    # All surfaces in empty workspace are kernel-tier
    tiers = {s["tier"] for s in surfaces}
    _assert(
        tiers == {"kernel"},
        f"Empty workspace tiers all 'kernel' (got: {tiers})",
    )

    # Active bundles empty per the mock
    _assert(
        result.get("active_bundles") == [],
        "active_bundles == [] for empty workspace",
    )


# =============================================================================
# Group 4 — program surfaces emit when bundle SURFACES.yaml declares them
# =============================================================================


def test_resolver_program_surfaces_emit() -> None:
    print("\n[4] resolver appends program surfaces when bundle declares them")

    from unittest.mock import MagicMock, patch

    fake_bundle = {
        "slug": "test-program",
        "title": "Test Program",
        "current_phase": "active",
        "phases": [{"key": "active", "label": "Active"}],
    }

    fake_surfaces_yaml = {
        "schema_version": 1,
        "tabs": {},
        "chat_chips": [],
        "surfaces": [
            {
                "slug": "test-cockpit",
                "title": "Test Cockpit",
                "archetype": "dashboard",
                "substrate_paths": ["/workspace/test/data.yaml"],
                "icon_key": "chart-line",
                "default_pinned": False,
                "route": "/test-cockpit",
                "summary": "Test program cockpit surface.",
            },
            {
                # Bad entry: missing slug → should be skipped, not raised
                "title": "Bad Entry",
                "archetype": "document",
            },
            {
                # Bad entry: not a dict → should be skipped
                "this is not a dict",
            },
        ],
    }

    with patch(
        "services.bundle_reader.bundles_active_for_workspace",
        return_value=[fake_bundle],
    ), patch(
        "services.composition_resolver._load_surfaces",
        return_value=fake_surfaces_yaml,
    ):
        from services.composition_resolver import resolve_workspace_composition

        result = resolve_workspace_composition(
            user_id="test-user-id", client=MagicMock()
        )

    surfaces = result.get("surfaces", [])
    slugs = [s["slug"] for s in surfaces]

    # Kernel surfaces still present
    kernel_present = kernel_surface_slugs() <= set(slugs)
    _assert(
        kernel_present,
        "Kernel surfaces still emitted when bundle active",
    )

    # Program surface appears
    _assert(
        "test-cockpit" in slugs,
        "Program-tier surface 'test-cockpit' present in surfaces[]",
    )

    # Program surface tier annotated correctly
    program_entries = [s for s in surfaces if s["slug"] == "test-cockpit"]
    _assert(
        len(program_entries) == 1
        and program_entries[0]["tier"] == "program:test-program",
        f"Program surface tier='program:test-program' "
        f"(got: {program_entries[0]['tier'] if program_entries else 'missing'})",
    )

    # Bad entries skipped, not raised
    _assert(
        "Bad Entry" not in [s.get("title") for s in surfaces],
        "Bad bundle surface entry (missing slug) was skipped",
    )

    # Kernel order preserved at the head of the list
    expected_kernel_slug_order = [s["slug"] for s in KERNEL_SURFACES]
    actual_kernel_prefix = slugs[: len(expected_kernel_slug_order)]
    _assert(
        actual_kernel_prefix == expected_kernel_slug_order,
        "Kernel surfaces appear in canonical declaration order at head of surfaces[]",
    )


# =============================================================================
# Group 5 — schema-version bump check (canary for future schema changes)
# =============================================================================


def test_schema_version_stable() -> None:
    print("\n[5] schema_version stability canary")

    from unittest.mock import MagicMock, patch

    with patch(
        "services.bundle_reader.bundles_active_for_workspace",
        return_value=[],
    ):
        from services.composition_resolver import resolve_workspace_composition

        result = resolve_workspace_composition(
            user_id="test-user-id", client=MagicMock()
        )

    _assert(
        result["schema_version"] == 1,
        "schema_version == 1 (Phase 1 is additive; no bump warranted)",
    )


# =============================================================================
# Run
# =============================================================================


if __name__ == "__main__":
    test_kernel_surfaces_module()
    test_kernel_surface_entries_shape()
    test_resolver_empty_workspace()
    test_resolver_program_surfaces_emit()
    test_schema_version_stable()

    print(f"\n{'='*60}")
    print(f"ADR-297 Phase 1 regression gate: {_passed} passed, {_failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if _failed == 0 else 1)
