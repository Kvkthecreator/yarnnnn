"""ADR-297 Phase 1 + D11 + D12 — atomic surfaces registry regression gate.

Asserts the compositor extension emits the `surfaces[]` field with:
- All kernel surfaces always present (13 content surfaces + 3 chrome
  surfaces after D12 = 16 entries; every slug from
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

ADR-297 D11 additions (Universal Surface Application):
- ARCHETYPES contains `input`, `navigator`, `chrome`
- Every chrome-style surface (i.e., one with default_region set)
  declares both default_region and default_visibility
- Chrome surfaces are not navigable (route == "")
- Chrome surfaces are not pinnable (default_pinned == False)

ADR-297 D12 amendments (top-center merged dock-bar):
- D12 collapsed the prior 4-entry chrome set to 3 by deleting `dock`.

ADR-297 D16 amendments (universal summon chat drawer):
- D16 renamed `chat-composer` → `chat-drawer` and flipped its region
  bottom-fixed → floating-overlay/summon. The bottom-strip composer
  dissolves into a FAB + slide-over drawer.

Post-D16 chrome surface set (3 entries):
    `top-bar`    (chrome/top/always)        — merged dock-bar body
    `launcher`   (navigator/floating-overlay/summon) — overlay
    `chat-drawer`(input/floating-overlay/summon)    — FAB + drawer

Both `bottom-floating` and `bottom-fixed` LayoutRegions survive in the
type union but no kernel surface targets them today.

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
        len(KERNEL_SURFACES) >= 18,
        f"At least 18 kernel surfaces declared "
        f"(15 content + 3 D12 chrome) (found {len(KERNEL_SURFACES)})",
    )

    slugs = [s["slug"] for s in KERNEL_SURFACES]
    _assert(
        len(slugs) == len(set(slugs)),
        "Kernel surface slugs are unique",
    )

    # Spot-check critical surfaces exist
    expected_slugs = {
        "feed",
        "cockpit",  # ADR-297 D1 amendment (same-session 2026-05-21)
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
        # ADR-297 D19.4 (2026-05-22): settings + connectors promoted
        # from legacy pages to atomic kernel surfaces. Reverses D19.7.
        # Inside the authenticated workspace, every surface is a window.
        "settings",
        "connectors",
        # ADR-297 D11 chrome surfaces (D12 collapsed `dock` into top-bar;
        # D16 renamed `chat-composer` → `chat-drawer` and flipped its
        # region bottom-fixed → floating-overlay/summon).
        "top-bar",
        "launcher",
        "chat-drawer",
    }

    # ADR-297 D12: `dock` slug DELETED from registry. Singular
    # Implementation regression guard — fail if it sneaks back in.
    _assert(
        "dock" not in slugs,
        "D12: `dock` kernel surface absent (responsibilities absorbed into top-bar)",
    )

    # ADR-297 D16: `chat-composer` slug DELETED from registry.
    # Singular Implementation regression guard — chat is summon-style
    # via the universal drawer (chat-drawer slug), not a persistent
    # bottom-strip composer.
    _assert(
        "chat-composer" not in slugs,
        "D16: `chat-composer` kernel surface absent (replaced by `chat-drawer`)",
    )
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
# Group 5b — ADR-297 D11 archetype + chrome-surface invariants
# =============================================================================


def test_d11_archetype_catalog() -> None:
    print("\n[5b-archetypes] ADR-297 D11 archetype catalog")

    # All D1 + D11 archetypes present
    expected_archetypes = {
        # ADR-198 originals
        "document",
        "dashboard",
        "queue",
        "briefing",
        "stream",
        # ADR-297 D1 additions
        "browser",
        "roster",
        # ADR-297 D11 additions
        "input",
        "navigator",
        "chrome",
    }
    actual = set(ARCHETYPES)
    missing = expected_archetypes - actual
    _assert(
        not missing,
        f"ARCHETYPES contains all D1+D11 entries (missing: {missing or 'none'})",
    )


def test_d11_chrome_surfaces() -> None:
    print("\n[5b-chrome] ADR-297 D11+D12+D16 chrome-surface contract")

    # The three chrome surfaces (post-D12, post-D16) and their
    # declared (archetype, region, visibility).
    #   D12 deleted `dock` from this set.
    #   D16 renamed `chat-composer` → `chat-drawer` and flipped its
    #   region bottom-fixed → floating-overlay/summon (universal
    #   FAB + slide-over drawer replaces the bottom-strip composer).
    expected_chrome = {
        "top-bar": ("chrome", "top", "always"),
        "launcher": ("navigator", "floating-overlay", "summon"),
        "chat-drawer": ("input", "floating-overlay", "summon"),
    }

    by_slug = {s["slug"]: s for s in KERNEL_SURFACES}

    for slug, (archetype, region, visibility) in expected_chrome.items():
        entry = by_slug.get(slug)
        _assert(entry is not None, f"Chrome surface '{slug}' is declared")
        if entry is None:
            continue

        _assert(
            entry.get("archetype") == archetype,
            f"'{slug}' archetype is '{archetype}' "
            f"(got: {entry.get('archetype')})",
        )
        _assert(
            entry.get("default_region") == region,
            f"'{slug}' default_region is '{region}' "
            f"(got: {entry.get('default_region')})",
        )
        _assert(
            entry.get("default_visibility") == visibility,
            f"'{slug}' default_visibility is '{visibility}' "
            f"(got: {entry.get('default_visibility')})",
        )
        # Chrome surfaces are not launcher-navigable
        _assert(
            entry.get("route") == "",
            f"'{slug}' is not launcher-navigable (route == '')",
        )
        # Chrome surfaces are not dock-pinnable
        _assert(
            entry.get("default_pinned") is False,
            f"'{slug}' is not default_pinned",
        )

    # Every surface that declares default_region must also declare
    # default_visibility (and vice versa) — D11 layout policy is a
    # paired contract.
    for entry in KERNEL_SURFACES:
        has_region = "default_region" in entry
        has_visibility = "default_visibility" in entry
        _assert(
            has_region == has_visibility,
            f"'{entry['slug']}' D11 fields are paired "
            f"(region={has_region}, visibility={has_visibility})",
        )

    # Every declared region is one of the canonical five
    legal_regions = {"main", "top", "bottom-floating", "bottom-fixed", "floating-overlay"}
    for entry in KERNEL_SURFACES:
        region = entry.get("default_region")
        if region is not None:
            _assert(
                region in legal_regions,
                f"'{entry['slug']}' default_region '{region}' is canonical",
            )

    # Every declared visibility is one of the canonical three
    legal_visibility = {"always", "summon", "pinned-only"}
    for entry in KERNEL_SURFACES:
        visibility = entry.get("default_visibility")
        if visibility is not None:
            _assert(
                visibility in legal_visibility,
                f"'{entry['slug']}' default_visibility '{visibility}' is canonical",
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
    test_d11_archetype_catalog()
    test_d11_chrome_surfaces()
    test_schema_version_stable()

    print(f"\n{'='*60}")
    print(f"ADR-297 Phase 1 + D11 regression gate: {_passed} passed, {_failed} failed")
    print(f"{'='*60}")
    sys.exit(0 if _failed == 0 else 1)
