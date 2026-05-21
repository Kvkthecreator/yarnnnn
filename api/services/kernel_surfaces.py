"""Kernel surfaces — ADR-297 Phase 1.

The canonical list of surfaces that exist in every YARNNN workspace,
regardless of which program bundles are active. Per ADR-297:

- Surfaces mirror substrate. Each kernel surface corresponds 1:1 to a
  substrate concept that exists in every workspace.
- Substrate location determines surface tier. Files under
  `/workspace/...` that the kernel scaffolds (or always-present DB
  tables) are kernel surfaces. Per-bundle substrate produces program
  surfaces (see composition_resolver.py + SURFACES.yaml). Operator-
  authored arbitrary substrate produces composed surfaces (forward
  horizon, D10).
- Each surface declares its archetype per ADR-198 (Document / Dashboard
  / Queue / Stream / Briefing — plus the catalog extensions Browser
  and Roster called out in ADR-297 D1).

This module is the **declaration**, not the rendering. The frontend
consumes the `surfaces[]` array emitted by `composition_resolver` and
renders each surface using kernel-library components. No render logic
here — pure data.

Phase 1 discipline: this file is additive. Phase 2 (shell rebuild)
will route the launcher + dock against these declarations. Phase 3
(container deletion) will collapse the existing `tabs` composition
output once every consumer has migrated to `surfaces[]`.
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# Archetype enum — extends ADR-198's five with two catalog additions
# =============================================================================
#
# ADR-198 names five archetypes: document | dashboard | queue | briefing |
# stream. ADR-297 D1 names two catalog extensions for surfaces that don't
# fit cleanly into the original five:
#   - `browser` — interactive file/path navigation (the Files surface)
#   - `roster` — list-of-actors surface (the Agents surface)
# Both are operator-facing reading shapes that ADR-198's original five
# don't cover; both are kernel-only (no program-shipped browser or roster
# surfaces).
#
# The TS mirror in web/lib/compositor/types.ts extends `Archetype` to
# match.

ARCHETYPES = (
    "document",
    "dashboard",
    "queue",
    "briefing",
    "stream",
    "browser",
    "roster",
)


# =============================================================================
# Kernel surfaces declaration
# =============================================================================
#
# Order in this list is the **canonical display order in the launcher's
# Workspace section**. The launcher renders them in this order under the
# subtle "Workspace" group header (ADR-297 D4 subtle tier grouping).
#
# `default_pinned: True` means the surface ships pinned by default in the
# operator's dock. Per ADR-297 D5: Feed only. Every other surface is
# summon-only until the operator pins it.
#
# `route` is the URL the launcher navigates to when the operator selects
# the surface. Phase 1: routes either already exist (created in prior
# ADRs) or are placeholders for Phase 2 to create. Routes for surfaces
# that don't yet have a dedicated page are marked with a `_route_status`
# comment for the Phase 2 implementation; the frontend's launcher consumer
# tolerates 404s during the transitional state.
#
# `substrate_paths` lists the workspace files this surface reads. Used
# by:
#   - Phase 2: to know which files to subscribe to / refetch when a
#     surface is active.
#   - Phase 3: to validate that container deletion didn't orphan a
#     substrate concept (every substrate path here must have a surface
#     hosting it).
# Some surfaces (Feed, Queue, Activity) read DB tables, not files; their
# `substrate_paths` is empty and the substrate-class is documented in
# the comment.

KERNEL_SURFACES: list[dict[str, Any]] = [
    {
        "slug": "feed",
        "title": "Feed",
        "archetype": "stream",
        "substrate_paths": [],  # session_messages DB table
        "icon_key": "message-circle",
        "default_pinned": True,
        "route": "/feed",
        "summary": "Operator chat surface and multi-actor narrative timeline.",
    },
    {
        # ADR-297 D1 amendment (same-session 2026-05-21): cockpit added as
        # the 13th kernel surface to resolve the /work dissolution. ADR-228
        # already established cockpit-as-substrate-read (four-face stack:
        # Mandate / Money truth / Performance / Tracking, plus program-shipped
        # section overrides per ADR-273). The atomic Cockpit surface hosts
        # CockpitRenderer intact; no rewrite needed.
        "slug": "cockpit",
        "title": "Cockpit",
        "archetype": "dashboard",
        "substrate_paths": [
            "/workspace/context/_shared/MANDATE.md",
            "/workspace/context/_shared/_autonomy.yaml",
            "/workspace/context/_shared/_performance.md",
            "/workspace/context/_shared/_performance_summary.md",
        ],
        "icon_key": "layout-dashboard",
        "default_pinned": False,
        "route": "/cockpit",  # _route_status: NEW in Phase 2 — replaces /work?tab=dashboard
        "summary": "Live operating dashboard — mandate, money-truth, performance, tracking + program-shipped sections.",
    },
    {
        "slug": "cadence",
        "title": "Cadence",
        "archetype": "dashboard",
        "substrate_paths": [
            "/workspace/_recurrences.yaml",
            "/workspace/_hooks.yaml",
            "/workspace/review/standing_intent.md",
        ],
        "icon_key": "clock",
        "default_pinned": False,
        "route": "/cadence",  # _route_status: NEW in Phase 2 — Phase 1 emits the surface, route is built by shell-rebuild PR
        "summary": "Recurrences, substrate-event hooks, standing intent, and wake telemetry.",
    },
    {
        "slug": "delegation",
        "title": "Delegation",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/context/_shared/_autonomy.yaml",
        ],
        "icon_key": "shield-check",
        "default_pinned": False,
        "route": "/delegation",  # _route_status: NEW in Phase 2
        "summary": "Autonomy ceiling — how much the Reviewer can execute without operator approval.",
    },
    {
        "slug": "mandate",
        "title": "Mandate",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/context/_shared/MANDATE.md",
        ],
        "icon_key": "target",
        "default_pinned": False,
        "route": "/mandate",  # _route_status: NEW in Phase 2
        "summary": "Operator's standing intent — the Primary Action this workspace is built around.",
    },
    {
        "slug": "principles",
        "title": "Principles",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/review/principles.md",
            "/workspace/review/_principles.yaml",
        ],
        "icon_key": "scale",
        "default_pinned": False,
        "route": "/principles",  # _route_status: NEW in Phase 2
        "summary": "Reviewer's judgment framework and decision thresholds.",
    },
    {
        "slug": "identity",
        "title": "Identity",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/context/_shared/IDENTITY.md",
        ],
        "icon_key": "user-circle",
        "default_pinned": False,
        "route": "/identity",  # _route_status: NEW in Phase 2
        "summary": "Operator persona — voice, role, context the workspace reasons against.",
    },
    {
        "slug": "brand",
        "title": "Brand",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/context/_shared/BRAND.md",
        ],
        "icon_key": "palette",
        "default_pinned": False,
        "route": "/brand",  # _route_status: NEW in Phase 2
        "summary": "Brand voice and stylistic constraints applied to operator-facing outputs.",
    },
    {
        "slug": "files",
        "title": "Files",
        "archetype": "browser",
        "substrate_paths": [],  # All paths under workspace_files
        "icon_key": "folder",
        "default_pinned": False,
        "route": "/context",  # _route_status: EXISTING — the current /context page is the Files surface (legacy URL retained)
        "summary": "Raw substrate browser — every file in the workspace, with revision history.",
    },
    {
        "slug": "agents",
        "title": "Agents",
        "archetype": "roster",
        "substrate_paths": [],  # agents DB table + per-agent substrate
        "icon_key": "users",
        "default_pinned": False,
        "route": "/agents",  # _route_status: EXISTING — Reviewer detail + roster live here
        "summary": "Agent roster — Reviewer, specialists, platform integrations.",
    },
    {
        "slug": "program",
        "title": "Program",
        "archetype": "document",
        "substrate_paths": [
            "/workspace/_program.yaml",
        ],
        "icon_key": "package",
        "default_pinned": False,
        "route": "/program",  # _route_status: NEW in Phase 2 — replaces ProgramLifecycleDrawer
        "summary": "Active program bundle, phase, and capability gaps.",
    },
    {
        "slug": "queue",
        "title": "Queue",
        "archetype": "queue",
        "substrate_paths": [],  # action_proposals DB table (pending state)
        "icon_key": "inbox",
        "default_pinned": False,
        "route": "/queue",  # _route_status: NEW in Phase 2 — extracts proposal queue from /work or /agents context
        "summary": "Pending proposals awaiting Reviewer or operator decision.",
    },
    {
        "slug": "activity",
        "title": "Activity",
        "archetype": "stream",
        "substrate_paths": [],  # execution_events DB table
        "icon_key": "activity",
        "default_pinned": False,
        "route": "/activity",  # _route_status: NEW in Phase 2 — current /activity is deleted per ADR-163; reinstated as surface-mode
        "summary": "Execution-event log — every wake, every dispatch, every cost.",
    },
]


# =============================================================================
# Public helpers
# =============================================================================


def kernel_surface_entries() -> list[dict[str, Any]]:
    """Return the kernel surface list with `tier: "kernel"` added.

    This is the shape the compositor emits into `surfaces[]`. Always
    returns a deep copy so callers can mutate freely without affecting
    the canonical declaration.
    """
    from copy import deepcopy

    return [
        {**deepcopy(entry), "tier": "kernel"}
        for entry in KERNEL_SURFACES
    ]


def kernel_surface_slugs() -> set[str]:
    """Set of all kernel surface slugs. Useful for test gates and
    validation — every kernel surface must be present in every
    workspace's `surfaces[]` output."""
    return {entry["slug"] for entry in KERNEL_SURFACES}


__all__ = [
    "ARCHETYPES",
    "KERNEL_SURFACES",
    "kernel_surface_entries",
    "kernel_surface_slugs",
]
