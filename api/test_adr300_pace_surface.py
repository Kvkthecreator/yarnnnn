"""ADR-300 regression gate — Pace as Atomic Kernel Surface.

Validates that pace is registered as the sixteenth atomic kernel surface
per ADR-297 D1, that the content-shape registry covers it per ADR-245 D3,
that the FE PaceCard + /pace page exist, and that PaceBadge has been
simplified to a read-only deep-link per ADR-300 D5.

Pure-Python script per ADR-236 Rule 3 (no JS test runner). Run with:
    python -m api.test_adr300_pace_surface
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ─── Files ─────────────────────────────────────────────────────────────────

ADR_FILE = REPO_ROOT / "docs" / "adr" / "ADR-300-pace-as-atomic-kernel-surface.md"
KERNEL_SURFACES = REPO_ROOT / "api" / "services" / "kernel_surfaces.py"
WORKSPACE_PATHS = REPO_ROOT / "api" / "services" / "workspace_paths.py"
PACE_SERVICE = REPO_ROOT / "api" / "services" / "pace.py"
COCKPIT_ROUTE = REPO_ROOT / "api" / "routes" / "cockpit.py"

# FE
DESK_TYPES = REPO_ROOT / "web" / "types" / "desk.ts"
SURFACE_REGISTRY = REPO_ROOT / "web" / "components" / "shell" / "SurfaceRegistry.tsx"
CONTENT_SHAPES_INDEX = REPO_ROOT / "web" / "lib" / "content-shapes" / "index.ts"
PACE_SHAPE_MODULE = REPO_ROOT / "web" / "lib" / "content-shapes" / "pace.ts"
PACE_CARD = REPO_ROOT / "web" / "components" / "workspace-concepts" / "PaceCard.tsx"
PACE_PAGE = REPO_ROOT / "web" / "app" / "(authenticated)" / "pace" / "page.tsx"
PACE_BADGE = REPO_ROOT / "web" / "components" / "work" / "PaceBadge.tsx"


# ─── Assertions ────────────────────────────────────────────────────────────


def assertion_1_adr_exists():
    """ADR-300 doc is committed with the right supersession + amendment links."""
    assert ADR_FILE.exists(), f"ADR-300 missing: {ADR_FILE}"
    body = ADR_FILE.read_text()
    assert "Supersedes" in body, "ADR-300 must declare what it supersedes"
    assert "ADR-298" in body, "ADR-300 must cite ADR-298 (pace substrate origin)"
    assert "ADR-297" in body, "ADR-300 must cite ADR-297 (atomic-substrate-mirror)"


def assertion_2_kernel_surfaces_entry():
    """`pace` is registered in KERNEL_SURFACES with the right shape."""
    assert KERNEL_SURFACES.exists(), f"missing: {KERNEL_SURFACES}"
    src = KERNEL_SURFACES.read_text()
    # The pace block: slug + path + archetype + icon + route
    assert '"slug": "pace"' in src, "pace slug not registered in KERNEL_SURFACES"
    assert '"archetype": "document"' in src, "pace must be Document archetype (kind editor on substrate)"
    assert '"/workspace/context/_shared/_pace.yaml"' in src, \
        "pace must declare /workspace/context/_shared/_pace.yaml as its substrate path"
    assert '"route": "/pace"' in src, "pace must declare route /pace"
    assert '"icon_key": "gauge"' in src, "pace must use the gauge icon (speedometer metaphor)"


def assertion_3_pace_path_in_reviewer_locks():
    """SHARED_PACE_PATH is in DEFAULT_REVIEWER_WRITE_LOCKS — operator-only substrate.

    Imports the tuple at runtime and asserts membership; the source-text
    parse is fragile against intervening comment blocks (which the lock
    tuple has, by design).
    """
    assert WORKSPACE_PATHS.exists(), f"missing: {WORKSPACE_PATHS}"
    sys.path.insert(0, str(REPO_ROOT / "api"))
    try:
        from services.workspace_paths import (
            DEFAULT_REVIEWER_WRITE_LOCKS,
            SHARED_PACE_PATH,
        )
    finally:
        sys.path.pop(0)
    assert SHARED_PACE_PATH in DEFAULT_REVIEWER_WRITE_LOCKS, (
        f"SHARED_PACE_PATH={SHARED_PACE_PATH!r} must be in DEFAULT_REVIEWER_WRITE_LOCKS "
        f"(operator-only per ADR-298 D11). Current locks: {DEFAULT_REVIEWER_WRITE_LOCKS}"
    )


def assertion_4_pace_service_unchanged_no_new_write_helper():
    """ADR-300 V1 writes through FE writeShape(); no server-side write_pace_kind helper.

    Singular Implementation per ADR-245 D5: configuration shapes route through
    writeShape() → api.workspace.editFile, not a dedicated REST endpoint.
    """
    assert PACE_SERVICE.exists(), f"missing: {PACE_SERVICE}"
    src = PACE_SERVICE.read_text()
    assert "async def read_pace" in src, "read_pace helper must remain"
    assert "def parse_pace_yaml" in src, "parse_pace_yaml helper must remain"
    # Anti-assertion: no separate write helper / no PUT endpoint
    assert "def write_pace_kind" not in src, \
        "write_pace_kind helper must NOT exist — ADR-300 V1 uses writeShape() per ADR-245 D5"
    assert "async def write_pace" not in src, "no async write_pace helper either"


def assertion_5_no_put_pace_route():
    """Cockpit route exposes GET /pace only — no PUT endpoint per ADR-300 D5+ADR-245."""
    assert COCKPIT_ROUTE.exists(), f"missing: {COCKPIT_ROUTE}"
    src = COCKPIT_ROUTE.read_text()
    assert '@router.get("/pace"' in src, "GET /api/cockpit/pace must exist"
    assert '@router.put("/pace"' not in src, \
        "PUT /api/cockpit/pace must NOT exist — writes go via writeShape() per ADR-245 D5"


def assertion_6_fe_kernel_surface_slug_includes_pace():
    """`pace` is in KernelSurfaceSlug union + KERNEL_SURFACE_SLUGS array."""
    assert DESK_TYPES.exists(), f"missing: {DESK_TYPES}"
    src = DESK_TYPES.read_text()
    assert "| 'pace'" in src, "KernelSurfaceSlug union must include 'pace'"
    assert "'pace'," in src or "'pace'" in src.split("KERNEL_SURFACE_SLUGS")[-1], \
        "KERNEL_SURFACE_SLUGS array must include 'pace'"


def assertion_7_fe_surface_registry_mounts_pace_page():
    """SurfaceRegistry imports PacePage + maps pace slug."""
    assert SURFACE_REGISTRY.exists(), f"missing: {SURFACE_REGISTRY}"
    src = SURFACE_REGISTRY.read_text()
    assert "import PacePage from '@/app/(authenticated)/pace/page'" in src, \
        "SurfaceRegistry must import PacePage"
    assert "pace: PacePage," in src, "KERNEL_SURFACE_REGISTRY must map pace → PacePage"


def assertion_8_content_shape_registered():
    """`pace` is in CONTENT_SHAPES registry."""
    assert CONTENT_SHAPES_INDEX.exists(), f"missing: {CONTENT_SHAPES_INDEX}"
    src = CONTENT_SHAPES_INDEX.read_text()
    assert "import { META as paceMeta } from './pace'" in src, \
        "content-shapes/index.ts must import paceMeta"
    assert "pace: paceMeta," in src, "CONTENT_SHAPES must register pace → paceMeta"


def assertion_9_pace_shape_module_well_formed():
    """content-shapes/pace.ts exports the right contract metadata + hook."""
    assert PACE_SHAPE_MODULE.exists(), f"missing: {PACE_SHAPE_MODULE}"
    src = PACE_SHAPE_MODULE.read_text()
    assert "export const SHAPE_KEY = 'pace'" in src, "SHAPE_KEY must be 'pace'"
    assert "export const PATH_GLOB = '**/_shared/_pace.yaml'" in src, "PATH_GLOB must match the substrate path"
    assert "export const WRITE_CONTRACT = 'configuration'" in src, \
        "pace is configuration class per ADR-245 D5"
    assert "export const CANONICAL_L3 = 'PaceCard'" in src, \
        "PaceCard is the canonical L3 per ADR-245 D4"
    assert "export function useCockpitPace" in src, "useCockpitPace hook must be exported"
    assert "writeShape('pace'" in src, \
        "setKind() must route through writeShape('pace', ...) per ADR-245 D5"


def assertion_10_pace_card_full_variant():
    """PaceCard exposes full variant + uses useCockpitPace."""
    assert PACE_CARD.exists(), f"missing: {PACE_CARD}"
    src = PACE_CARD.read_text()
    assert "useCockpitPace" in src, "PaceCard must use useCockpitPace hook"
    assert "setKind" in src, "PaceCard must call setKind() for kind mutation"
    # Four kind options surfaced
    for kind in ("hourly", "daily", "weekly", "continuous"):
        assert f"'{kind}'" in src, f"PaceCard must surface '{kind}' as an option"


def assertion_11_pace_page_mounts_card():
    """/pace page is a thin wrapper around PaceCard variant=full."""
    assert PACE_PAGE.exists(), f"missing: {PACE_PAGE}"
    src = PACE_PAGE.read_text()
    assert "PaceCard" in src and 'variant="full"' in src, \
        "/pace page must mount <PaceCard variant=\"full\" />"
    assert "iconKey=\"gauge\"" in src, "/pace page must use gauge icon (matches kernel_surfaces.py)"


def assertion_12_pace_badge_is_link_not_span():
    """PaceBadge simplified to read-only deep-link to /pace per ADR-300 D5."""
    assert PACE_BADGE.exists(), f"missing: {PACE_BADGE}"
    src = PACE_BADGE.read_text()
    assert "import Link from 'next/link'" in src, "PaceBadge must import next/link"
    assert 'href="/pace"' in src, "PaceBadge must deep-link to /pace"
    # Anti-assertion: no edit hooks
    assert "setKind" not in src, "PaceBadge must NOT carry edit semantics (lives on /pace)"


# ─── Runner ────────────────────────────────────────────────────────────────


ASSERTIONS = [
    assertion_1_adr_exists,
    assertion_2_kernel_surfaces_entry,
    assertion_3_pace_path_in_reviewer_locks,
    assertion_4_pace_service_unchanged_no_new_write_helper,
    assertion_5_no_put_pace_route,
    assertion_6_fe_kernel_surface_slug_includes_pace,
    assertion_7_fe_surface_registry_mounts_pace_page,
    assertion_8_content_shape_registered,
    assertion_9_pace_shape_module_well_formed,
    assertion_10_pace_card_full_variant,
    assertion_11_pace_page_mounts_card,
    assertion_12_pace_badge_is_link_not_span,
]


def main() -> int:
    passed = 0
    failed: list[tuple[str, str]] = []
    for fn in ASSERTIONS:
        try:
            fn()
            passed += 1
            print(f"  PASS  {fn.__name__}")
        except AssertionError as exc:
            failed.append((fn.__name__, str(exc)))
            print(f"  FAIL  {fn.__name__}: {exc}")
        except Exception as exc:  # pragma: no cover
            failed.append((fn.__name__, f"unexpected error: {exc!r}"))
            print(f"  ERROR {fn.__name__}: {exc!r}")
    total = len(ASSERTIONS)
    print(f"\nADR-300 gate: {passed}/{total} passed")
    if failed:
        print("\nFailures:")
        for name, msg in failed:
            print(f"  - {name}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
