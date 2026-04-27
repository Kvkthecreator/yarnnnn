"""Program bundle reader — minimal point-of-use helper.

Per ADR-224 v3: bundles are not loaded into runtime; they are consulted
at three specific moments (composition / scaffolding / display metadata).
This module is the helper used by the directory_registry, task_types,
and orchestration helpers when their kernel-only lookup misses — at which
point they consult active program bundles for the same key.

The runtime dispatch path (task_pipeline, agent_pipeline, etc.) does not
consult bundles. Per Axiom 1 + ADR-188 + ADR-207, runtime reads TASK.md
and _domain.md from the operator's workspace. Bundles inform composition
and scaffolding moments only.

Caching: lru_cache on `_load_manifest`. Bundles are repo-tracked, change
at deploy time, not runtime. Process-lifetime cache is correct for now;
revisit when activation flow (ADR 5) needs runtime mutation.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# Repo-relative bundle root. Resolved from this file's location so the
# helper works regardless of CWD (tests, scheduler, scripts).
_BUNDLE_ROOT = Path(__file__).resolve().parent.parent.parent / "docs" / "programs"


@lru_cache(maxsize=64)
def _load_manifest(slug: str) -> Optional[dict[str, Any]]:
    """Cached read of docs/programs/{slug}/MANIFEST.yaml. Returns None if absent."""
    path = _BUNDLE_ROOT / slug / "MANIFEST.yaml"
    if not path.exists():
        return None
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except Exception as exc:  # corrupt YAML — log and skip rather than crash
        logger.warning(f"[BUNDLE_READER] Failed to parse {path}: {exc}")
        return None


@lru_cache(maxsize=1)
def _all_slugs() -> tuple[str, ...]:
    """Discover bundle slugs by listing docs/programs/ subdirectories."""
    if not _BUNDLE_ROOT.exists():
        return ()
    return tuple(
        sorted(
            entry.name
            for entry in _BUNDLE_ROOT.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        )
    )


def all_active_bundles() -> list[dict[str, Any]]:
    """Return all bundles with status='active'.

    Used by composition-moment and scaffolding-moment helpers (kernel
    lookup miss → consult bundles). Reference / deferred / archived
    bundles do NOT surface their templates here — they only constrain
    OS decisions per ADR-223 §6.

    Note: this does NOT filter by workspace's connected platforms.
    Templates are platform-agnostic — capability gating happens at
    dispatch time per ADR-207 P3, not at template-lookup time.
    For cockpit rendering (ADR-225), use `bundles_active_for_workspace`
    which adds the connected-platform filter.
    """
    bundles: list[dict[str, Any]] = []
    for slug in _all_slugs():
        m = _load_manifest(slug)
        if m and m.get("status") == "active":
            bundles.append(m)
    return bundles


def bundles_active_for_workspace(user_id: str, client: Any) -> list[dict[str, Any]]:
    """Return bundles active for a specific workspace per ADR-224 §3 + ADR-225.

    Active for workspace = bundle.status='active' AND workspace has at least
    one of the bundle's capabilities[*].requires_connection currently
    connected (`platform_connections` row with status='active').

    This is the cockpit-rendering filter: a workspace without alpaca
    connected does not get alpha-trader-shaped chrome, even though
    alpha-trader's MANIFEST has status='active' globally.

    Order: bundles ordered by their oldest matching platform_connection's
    created_at (oldest first — typically the program the operator
    activated first). Deterministic ordering matters for first-match-wins
    middle resolution (see ADR-225 §2).
    """
    if not user_id:
        return []
    try:
        rows = (
            client.table("platform_connections")
            .select("platform, status, created_at")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )
    except Exception as exc:
        logger.warning(f"[BUNDLE_READER] platform_connections lookup failed: {exc}")
        return []

    connected_platforms = {r["platform"] for r in (rows.data or [])}
    if not connected_platforms:
        return []
    # Map platform → oldest created_at so bundles can be ordered deterministically
    platform_age: dict[str, str] = {}
    for r in rows.data or []:
        p = r["platform"]
        ca = r.get("created_at") or ""
        if p not in platform_age or (ca and ca < platform_age[p]):
            platform_age[p] = ca

    matching: list[tuple[str, dict[str, Any]]] = []
    for bundle in all_active_bundles():
        # Bundle is active for this workspace if any of its capabilities'
        # required platforms is connected.
        for cap in bundle.get("capabilities", []) or []:
            req = cap.get("requires_connection")
            if req and req in connected_platforms:
                # Use the oldest connection age across this bundle's platforms
                ages = [
                    platform_age.get(c.get("requires_connection"), "")
                    for c in (bundle.get("capabilities") or [])
                    if c.get("requires_connection") in connected_platforms
                ]
                bundle_age = min(a for a in ages if a) if any(ages) else ""
                matching.append((bundle_age, bundle))
                break  # one matching capability is enough — don't double-list

    # Sort by oldest connection age (oldest first)
    matching.sort(key=lambda pair: pair[0] or "")
    return [b for _, b in matching]


def get_task_type_from_bundles(type_key: str) -> Optional[dict[str, Any]]:
    """Find a task_type definition across active bundles.

    Returns the first match (bundles do not currently declare conflicting
    keys; cross-program conflict resolution is deferred per ADR-224 §7).

    The shape returned mirrors what `task_types.get_task_type()` returns
    so callers can treat kernel-and-bundle results uniformly.
    """
    for bundle in all_active_bundles():
        for tt in bundle.get("task_types", []) or []:
            if tt.get("key") == type_key:
                return _normalize_bundle_task_type(tt, bundle)
    return None


def get_directory_from_bundles(key: str) -> Optional[dict[str, Any]]:
    """Find a context_domain definition across active bundles.

    Returns a dict shaped like WORKSPACE_DIRECTORIES entries so directory
    helpers can treat kernel-and-bundle results uniformly.
    """
    for bundle in all_active_bundles():
        for d in bundle.get("context_domains", []) or []:
            if d.get("path") == key:
                return _normalize_bundle_domain(d, bundle)
    return None


def get_capability_from_bundles(name: str) -> Optional[dict[str, Any]]:
    """Find a capability declaration across active bundles.

    Returns a dict shaped like CAPABILITIES entries so task_derivation
    can treat kernel-and-bundle results uniformly.
    """
    for bundle in all_active_bundles():
        for cap in bundle.get("capabilities", []) or []:
            if cap.get("key") == name:
                return _normalize_bundle_capability(cap, bundle)
    return None


def list_bundle_capabilities() -> dict[str, dict[str, Any]]:
    """Return the union of all active bundles' capability declarations.

    Used by task_derivation when composing the derivation report — kernel
    CAPABILITIES + this union = full capability surface visible to YARNNN
    composition reasoning.
    """
    result: dict[str, dict[str, Any]] = {}
    for bundle in all_active_bundles():
        for cap in bundle.get("capabilities", []) or []:
            key = cap.get("key")
            if key and key not in result:
                result[key] = _normalize_bundle_capability(cap, bundle)
    return result


# ---- Internal: shape normalizers ----------------------------------------
#
# Bundle MANIFEST.yaml uses a slightly different schema than the kernel
# in-code dicts (e.g., bundle declarations are list-of-dicts, kernel is
# dict-of-dicts). These normalizers translate so callers see one shape.

def _normalize_bundle_task_type(tt: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Convert bundle task_type entry → kernel-shape task_type dict.

    Surfaces all bundle-declared fields so callers (manage_task,
    agent_creation, compose/assembly, chat tool handler) can treat
    bundle-sourced templates identically to kernel-sourced templates.
    """
    result: dict[str, Any] = {
        "key": tt.get("key"),
        "output_kind": tt.get("output_kind"),
        "default_schedule": tt.get("cadence"),
        "purpose": tt.get("purpose"),
        # Bundle origin marker so callers can attribute the source if they care
        "_program_slug": bundle.get("slug"),
    }
    # Optional fields — only present on richer bundle entries
    pass_through = [
        "display_name", "default_title", "description",
        "output_format", "default_delivery", "context_sources",
        "default_mode", "context_reads", "context_writes",
        "requires_platform", "default_objective", "default_deliverable",
        "page_structure", "surface_type", "export_options",
        "delivery_requires_approval", "bootstrap", "custom_deliverable_md",
    ]
    for field in pass_through:
        if field in tt:
            result[field] = tt[field]
    if "default_team" in tt:
        # Kernel uses `registry_default_team` as the field name
        result["registry_default_team"] = tt["default_team"]
    if "instruction" in tt:
        # Build a minimal `process` block matching kernel TASK_TYPES shape so
        # build_task_md_from_type / resolve_process_agents can treat the
        # bundle-sourced instruction identically.
        team = tt.get("default_team") or ["analyst"]
        result["process"] = [
            {
                "agent_type": team[0],
                "step": tt["key"],
                "instruction": tt["instruction"],
            }
        ]
    return result


def _normalize_bundle_domain(d: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Convert bundle context_domain entry → kernel-shape directory dict.

    Surfaces all bundle-declared fields so directory_registry helpers
    (get_domain, get_synthesis_content, has_entity_tracker, etc.) treat
    bundle-sourced domains identically to kernel-sourced domains.
    """
    result: dict[str, Any] = {
        "path": f"context/{d.get('path')}",
        "type": "context",
        "purpose": d.get("purpose"),
        "managed_by": "agent",
        "_program_slug": bundle.get("slug"),
    }
    # Optional rich fields — present when the bundle declaration is full
    if "display_name" in d:
        result["display_name"] = d["display_name"]
    if "description" in d:
        result["description"] = d["description"]
    if "entity_type" in d:
        result["entity_type"] = d["entity_type"]
    if "entity_structure" in d:
        result["entity_structure"] = d["entity_structure"]
    if "synthesis_file" in d:
        result["synthesis_file"] = d["synthesis_file"]
    if "synthesis_template" in d:
        result["synthesis_template"] = d["synthesis_template"]
    if "tracker_file" in d:
        result["tracker_file"] = d["tracker_file"]
    if "authored_substrate" in d:
        result["authored_substrate"] = d["authored_substrate"]
    if "assets_folder" in d:
        result["assets_folder"] = d["assets_folder"]
    return result


def _normalize_bundle_capability(cap: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Convert bundle capability entry → kernel-shape CAPABILITIES dict.

    Bundle declares `requires_connection: <platform>`; kernel CAPABILITIES
    uses `platform_connection_requirement: {platform: ..., status: 'active'}`.
    Normalize plus surface tools list, runtime, and category so callers
    (task_derivation, tool surface assembly) treat bundle-sourced
    capabilities identically.
    """
    rc = cap.get("requires_connection")
    result: dict[str, Any] = {
        "category": cap.get("category", "tool"),
        "runtime": cap.get("runtime"),
        "platform_connection_requirement": (
            {"platform": rc, "status": "active"} if rc else None
        ),
        "_program_slug": bundle.get("slug"),
    }
    if "tools" in cap:
        result["tools"] = cap["tools"]
    return result
