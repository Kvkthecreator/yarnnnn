"""Composition resolver — ADR-225.

Per ADR-225: this is the API-side resolution step that produces a
composition tree the FE renders. Reads active program bundles via
`bundle_reader.bundles_active_for_workspace`, applies phase overlays,
returns a stable JSON tree the FE compositor consumes.

The resolver:
1. Loads bundles active for the workspace (capability-implicit per ADR-224 §3).
2. Applies `phase_overlays` shallow-merge over each bundle's base `tabs` block.
3. Loads each bundle's SURFACES.yaml at `docs/programs/{slug}/SURFACES.yaml`.
4. Unions composition trees across bundles per the multi-bundle rules (ADR-225 §2).
5. Returns the full resolved tree + active_bundles metadata + chat_chips.

This service does NOT mutate substrate. It does NOT call out to platform
APIs. It only reads bundle YAML files (cached via bundle_reader's
lru_cache) and the workspace's `platform_connections` table.

Per ADR-225 §1: API-side resolution. FE-side rendering. Clean split.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Same root as bundle_reader — keep singular implementation.
_BUNDLE_ROOT = Path(__file__).resolve().parent.parent.parent / "docs" / "programs"


# =============================================================================
# Public API — single entry point
# =============================================================================


def resolve_workspace_composition(user_id: str, client: Any) -> dict[str, Any]:
    """The single function the API route calls. Returns the response shape
    documented in ADR-225 §2.

    Empty workspace (no platform connections, fresh signup) returns:
        {
            "schema_version": 1,
            "active_bundles": [],
            "composition": {"tabs": {}, "chat_chips": []},
        }

    Single-bundle workspace returns that bundle's resolved composition
    (with phase overlay applied).

    Multi-bundle workspace returns the union per ADR-225 §2 multi-bundle
    rules: pinned_tasks/pinned_shortcuts unioned, middles[] unioned in
    activation-date order (first match wins), chat_chips unioned and
    deduplicated.
    """
    from services.bundle_reader import bundles_active_for_workspace

    bundles = bundles_active_for_workspace(user_id, client)
    if not bundles:
        return {
            "schema_version": 1,
            "active_bundles": [],
            "composition": {"tabs": {}, "chat_chips": []},
        }

    active_bundles_meta = [_bundle_metadata(b) for b in bundles]
    composition = _resolve_composition_tree(bundles)
    return {
        "schema_version": 1,
        "active_bundles": active_bundles_meta,
        "composition": composition,
    }


# =============================================================================
# Internal helpers
# =============================================================================


def _bundle_metadata(manifest: dict[str, Any]) -> dict[str, Any]:
    """The active_bundles[] entry shape from ADR-225 §2."""
    current_phase = manifest.get("current_phase")
    phases = manifest.get("phases") or []
    current_label = next(
        (p.get("label") for p in phases if p.get("key") == current_phase),
        None,
    )
    return {
        "slug": manifest.get("slug"),
        "title": manifest.get("title"),
        "tagline": manifest.get("tagline"),
        "current_phase": current_phase,
        "current_phase_label": current_label,
        "phases": phases,
    }


def _load_surfaces(slug: str) -> Optional[dict[str, Any]]:
    """Load docs/programs/{slug}/SURFACES.yaml. Returns None if absent or
    unparseable."""
    path = _BUNDLE_ROOT / slug / "SURFACES.yaml"
    if not path.exists():
        return None
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except Exception as exc:
        logger.warning(f"[COMPOSITION_RESOLVER] Failed to parse {path}: {exc}")
        return None


def _resolve_composition_tree(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    """Resolve composition tree from active bundles.

    Per ADR-225 §2:
    - Single bundle: that bundle's tabs + phase overlay applied.
    - Multi-bundle: tabs union; lists union (pinned_tasks, pinned_shortcuts,
      middles[]); chat_chips union + deduplicated.
    """
    if not bundles:
        return {"tabs": {}, "chat_chips": []}

    merged_tabs: dict[str, Any] = {}
    merged_chips: list[str] = []
    seen_chips: set[str] = set()

    for bundle in bundles:
        slug = bundle.get("slug", "")
        surfaces = _load_surfaces(slug)
        if not surfaces:
            continue

        # Apply phase overlay to this bundle's tabs
        bundle_tabs = _apply_phase_overlay(
            base=surfaces.get("tabs") or {},
            phase_overlays=surfaces.get("phase_overlays") or {},
            current_phase=bundle.get("current_phase"),
        )

        # Merge into accumulator
        merged_tabs = _merge_tabs(merged_tabs, bundle_tabs)

        # Union chat chips (preserve order, dedupe)
        for chip in surfaces.get("chat_chips") or []:
            if chip not in seen_chips:
                merged_chips.append(chip)
                seen_chips.add(chip)

    return {"tabs": merged_tabs, "chat_chips": merged_chips}


def _apply_phase_overlay(
    base: dict[str, Any],
    phase_overlays: dict[str, Any],
    current_phase: Optional[str],
) -> dict[str, Any]:
    """Per ADR-225 §6: shallow merge — per-tab keys union; conflicts take
    the overlay value."""
    if not current_phase or not phase_overlays:
        return deepcopy(base) if base else {}
    overlay = phase_overlays.get(current_phase) or {}
    overlay_tabs = overlay.get("tabs") or {}
    if not overlay_tabs:
        return deepcopy(base) if base else {}

    result = deepcopy(base) if base else {}
    for tab_name, tab_overlay in overlay_tabs.items():
        if tab_name not in result:
            result[tab_name] = deepcopy(tab_overlay)
        else:
            result[tab_name] = _merge_tab_block(result[tab_name], tab_overlay)
    return result


def _merge_tab_block(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Within a single tab block (e.g., tabs.work), shallow merge the
    list/detail sub-blocks. Overlay wins on key conflicts.

    For lists (pinned_tasks, pinned_shortcuts, middles): overlay wins
    entirely if present (operator authored a complete list). Same logic as
    a YAML overlay convention — not a deep merge.
    """
    result = deepcopy(base)
    for k, v in (overlay or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _merge_tab_block(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


def _merge_tabs(
    accumulator: dict[str, Any], bundle_tabs: dict[str, Any]
) -> dict[str, Any]:
    """Multi-bundle composition merge. Per ADR-225 §2:
    - tabs.{tab}.list.pinned_tasks: union (preserve activation order, dedupe)
    - tabs.{tab}.list.pinned_shortcuts: union (preserve order, dedupe by path)
    - tabs.{tab}.detail.middles: union (first match wins at resolve time)
    - tabs.{tab}.list.featured: union, dedupe
    - tabs.{tab}.list.featured_domains: union, dedupe
    - other scalars (banner, group_default, filters_default): first-bundle
      wins (deterministic per oldest activation order)
    - bands[]: union (preserve order — first bundle's bands come first)
    """
    result = deepcopy(accumulator)
    for tab_name, bundle_tab in (bundle_tabs or {}).items():
        if tab_name not in result:
            result[tab_name] = deepcopy(bundle_tab)
            continue
        # Tab exists in both — merge sub-blocks
        existing = result[tab_name]
        for sub_name, sub_value in (bundle_tab or {}).items():
            if sub_name not in existing:
                existing[sub_name] = deepcopy(sub_value)
            elif sub_name == "bands" and isinstance(sub_value, list):
                existing["bands"] = (existing.get("bands") or []) + sub_value
            elif sub_name in ("list", "detail") and isinstance(sub_value, dict):
                existing[sub_name] = _merge_list_or_detail_block(
                    existing.get(sub_name) or {}, sub_value
                )
            else:
                # First-bundle wins on scalar conflicts
                pass
    return result


def _merge_list_or_detail_block(
    accumulator: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    """Merge tabs.{tab}.list or tabs.{tab}.detail blocks across bundles."""
    result = deepcopy(accumulator)
    for k, v in (incoming or {}).items():
        if k in ("pinned_tasks", "featured", "featured_domains") and isinstance(v, list):
            result[k] = _union_preserve_order(result.get(k) or [], v)
        elif k == "pinned_shortcuts" and isinstance(v, list):
            existing = result.get(k) or []
            existing_paths = {item.get("path") for item in existing if isinstance(item, dict)}
            for item in v:
                if isinstance(item, dict) and item.get("path") not in existing_paths:
                    existing.append(deepcopy(item))
                    existing_paths.add(item.get("path"))
            result[k] = existing
        elif k == "middles" and isinstance(v, list):
            result[k] = (result.get(k) or []) + deepcopy(v)
        elif k == "components" and isinstance(v, list):
            result[k] = (result.get(k) or []) + deepcopy(v)
        elif k == "cockpit_panes" and isinstance(v, list):
            # ADR-225 Phase 3: cockpit_panes union across bundles, first
            # bundle's panes come first (deterministic per oldest activation).
            result[k] = (result.get(k) or []) + deepcopy(v)
        elif k not in result:
            result[k] = deepcopy(v)
        # else: first-bundle wins on scalar conflicts (banner, group_default, etc.)
    return result


def _union_preserve_order(existing: list, incoming: list) -> list:
    """Concatenate two lists, preserving order, deduplicated."""
    seen = set()
    result = []
    for item in existing + incoming:
        # Use repr for hashability (handles dict items in pinned_shortcuts etc.)
        key = repr(item) if not isinstance(item, (str, int, float, bool, type(None))) else item
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result
