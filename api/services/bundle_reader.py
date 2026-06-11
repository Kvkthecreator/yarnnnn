"""Program bundle reader — minimal point-of-use helper.

Per ADR-224 v3: bundles are not loaded into runtime; they are consulted
at three specific moments (composition / scaffolding / display metadata).
This module is the helper used by the directory_registry, task_types,
and orchestration helpers when their kernel-only lookup misses — at which
point they consult active program bundles for the same key.

The runtime dispatch path (invocation_dispatcher, agent_pipeline, etc.) does
not consult bundles. Per Axiom 1 + ADR-188 + ADR-207 + ADR-231, runtime reads
the recurrence YAML (`_recurrences.yaml`) and `_domain.md` from the operator's
workspace. Bundles inform composition and scaffolding moments only.

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


def get_bundle_version(slug: str) -> Optional[str]:
    """Return the bundle's declared `version:` string, or None if absent.

    ADR-292: bundles ship a version stamp in MANIFEST.yaml. The operator-
    facing update flow consults this to compute "is an update available?"
    against the workspace's recorded `activated_bundle_version` in
    MANDATE.md frontmatter. Returns None for bundles that haven't been
    versioned yet — caller decides whether to treat as "no update" or
    "needs adoption."
    """
    manifest = _load_manifest(slug)
    if not manifest:
        return None
    version = manifest.get("version")
    return str(version) if version is not None else None


# ADR-327: get_minimum_pace DELETED — pace retires; a bundle no longer
# declares a frequency floor (frequency is not a concept). Cost governance
# is the dollar budget (_budget.yaml) with a kernel default; no activation
# pace gate. The `minimum_pace:` MANIFEST key is removed from all bundles.


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
        rows = None  # treat as no connections; connection-less bundles still resolve

    connected_platforms = {r["platform"] for r in (rows.data if rows else [])}

    # 2026-06-04: a bundle that requires NO platform connection
    # (e.g. alpha-author — read_uploads + websearch only) cannot be
    # resolved by the connected-platform filter. Its activation signal is
    # the operator's activated program (the MANDATE.md slug marker written
    # at fork time per ADR-226), not a platform connection. Read it once so
    # connection-less bundles resolve when the operator has activated them.
    activated_slug: Optional[str] = None
    try:
        mandate = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", "/workspace/constitution/MANDATE.md")
            .limit(1)
            .execute()
        )
        if mandate.data:
            from services.programs import parse_active_program_slug
            activated_slug = parse_active_program_slug(mandate.data[0].get("content"))
    except Exception as exc:
        logger.warning(f"[BUNDLE_READER] activated-program lookup failed: {exc}")

    # Map platform → oldest created_at so bundles can be ordered deterministically
    platform_age: dict[str, str] = {}
    for r in (rows.data if rows else []):
        p = r["platform"]
        ca = r.get("created_at") or ""
        if p not in platform_age or (ca and ca < platform_age[p]):
            platform_age[p] = ca

    matching: list[tuple[str, dict[str, Any]]] = []
    for bundle in all_active_bundles():
        caps = bundle.get("capabilities", []) or []
        required_platforms = {
            c.get("requires_connection") for c in caps if c.get("requires_connection")
        }

        if not required_platforms:
            # Connection-less bundle: active-for-workspace iff the operator
            # has activated it (MANDATE.md slug marker). No platform gate.
            # Sort key "" => oldest, so platform-bound bundles (which carry
            # a real connection age) order after it deterministically.
            if activated_slug and bundle.get("slug") == activated_slug:
                matching.append(("", bundle))
            continue

        # Platform-bound bundle: active iff any required platform is connected.
        if required_platforms & connected_platforms:
            ages = [
                platform_age.get(p, "")
                for p in required_platforms
                if p in connected_platforms
            ]
            bundle_age = min(a for a in ages if a) if any(ages) else ""
            matching.append((bundle_age, bundle))

    # Sort by oldest connection age (oldest first)
    matching.sort(key=lambda pair: pair[0] or "")
    return [b for _, b in matching]


def get_substrate_abi_for_workspace(user_id: str, client: Any) -> dict[str, Any]:
    """ADR-280: aggregate substrate_abi declarations across active bundles for a workspace.

    Returns a dict with two keys:
      - path_zones: list of all path-zone declarations across active bundles
      - reviewer_wake_envelope: list of all envelope declarations across active bundles

    Each entry preserves its original bundle declaration shape; consumers
    (workspace_guide composition at genesis, lock-policy at runtime) treat
    bundle origin as opaque — they care about the role + path, not which
    bundle shipped it.

    Multi-bundle workspaces: declarations from different bundles concatenate.
    Path-zone collisions (two bundles declaring the same path with different
    roles) are not currently resolved here — first-bundle-wins via the
    activation-date ordering of `bundles_active_for_workspace`. Future
    multi-program operator UX will need explicit resolution per ADR-280
    "Out of scope" §7.

    Returns empty dict when workspace has no active bundles.
    """
    bundles = bundles_active_for_workspace(user_id, client)
    if not bundles:
        return {"path_zones": [], "reviewer_wake_envelope": []}

    path_zones: list[dict[str, Any]] = []
    envelope_decls: list[dict[str, Any]] = []
    for bundle in bundles:
        abi = bundle.get("substrate_abi") or {}
        if not isinstance(abi, dict):
            continue
        # Tag each entry with origin bundle slug so genesis-by-Reviewer can
        # attribute the source in the workspace guide prose body.
        bundle_slug = bundle.get("slug")
        for zone in abi.get("path_zones", []) or []:
            if isinstance(zone, dict):
                zone_with_origin = {**zone, "_program_slug": bundle_slug}
                path_zones.append(zone_with_origin)
        for decl in abi.get("reviewer_wake_envelope", []) or []:
            if isinstance(decl, dict):
                decl_with_origin = {**decl, "_program_slug": bundle_slug}
                envelope_decls.append(decl_with_origin)

    return {
        "path_zones": path_zones,
        "reviewer_wake_envelope": envelope_decls,
    }


def get_ground_truth_for_workspace(user_id: str, client: Any) -> Optional[str]:
    """ADR-327 D6: return the active bundle's declared ground-truth file path
    (`substrate_abi.ground_truth`), workspace-relative, or None.

    The ground-truth file is the substrate the Reviewer's cadence judgment is
    calibrated against (the self-improving loop). The kernel calibration mirror
    correlates cadence-authoring history against outcome quality read from here.
    Returns the first active bundle's declaration (multi-program resolution is
    deferred per ADR-280 §7). None when no active bundle declares one — the
    calibration mirror then degrades to cadence-history-only evidence.
    """
    bundles = bundles_active_for_workspace(user_id, client)
    for bundle in bundles:
        abi = bundle.get("substrate_abi") or {}
        if isinstance(abi, dict):
            gt = abi.get("ground_truth")
            if isinstance(gt, str) and gt.strip():
                return gt.strip()
    return None


def get_watches_for_workspace(user_id: str, client: Any) -> list[dict[str, Any]]:
    """ADR-335 D2: return the active bundles' declared watches
    (`substrate_abi.watches`) — the perception twin of
    `get_ground_truth_for_workspace` above.

    Each entry preserves its bundle declaration shape
    (`{id, shape, declaration, recurrence, distills_to}`) tagged with
    `_program_slug` (same origin-tagging convention as
    `get_substrate_abi_for_workspace`). A watch is a Layer-1 perception
    declaration: WHAT the operation watches (shape, not vendor), WHERE the
    operator edits it (declaration substrate), WHICH recurrence enacts its
    cadence (the Trigger pointer — cadence lives on the recurrence,
    singular), and WHERE observations distill to (attributed signal
    substrate per the ADR-335 D3 observation contract).

    Returns [] when no active bundle declares watches — perception is a
    flow, never a gate (ADR-332 §2); consumers (calibration mirror at Walk,
    setup surfaces) degrade gracefully on empty.
    """
    watches: list[dict[str, Any]] = []
    for bundle in bundles_active_for_workspace(user_id, client):
        abi = bundle.get("substrate_abi") or {}
        if not isinstance(abi, dict):
            continue
        for decl in abi.get("watches", []) or []:
            if isinstance(decl, dict):
                watches.append({**decl, "_program_slug": bundle.get("slug")})
    return watches


# ADR-293 (2026-05-19): `get_path_zone_locks_for_workspace` DELETED.
# Bundle path_zones `role: operator-canon` is preserved as informational
# metadata (declares author-of-origin for surface labeling + first-fork-
# write authority) but no longer confers Reviewer write-lock. The lock
# surface collapses to the governance file set; operator per-path overrides
# moved to `_autonomy.yaml::never_auto` with `path:` prefix.


def get_market_context_for_user(user_id: str, client: Any) -> Optional[dict[str, Any]]:
    """Return the workspace's active bundle's `market_context:` block (ADR-268).

    Returns None when:
      - workspace has no active bundle (no matching capability + connection)
      - the active bundle does not declare a `market_context:` block

    When multiple bundles are active for a workspace (rare; per ADR-244 D4
    one workspace activates one program at a time, but the registry allows
    multi-program operators conceptually), returns the FIRST bundle's
    market_context per the deterministic ordering of
    `bundles_active_for_workspace`. The semantic schedules in the
    workspace's `_recurrences.yaml` are bundle-shipped, so the bundle that
    shipped them is the bundle whose market_context they resolve against.
    """
    bundles = bundles_active_for_workspace(user_id, client)
    for bundle in bundles:
        mc = bundle.get("market_context")
        if isinstance(mc, dict):
            return mc
    return None


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
        "path": f"operation/{d.get('path')}",
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
