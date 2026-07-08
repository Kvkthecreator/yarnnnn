"""ADR-415 — Dissolve Channels: Activity is the one "what happened" surface.

Source-guard gate. Supersedes test_adr385_channels_surface.py (deleted — it
asserted the Channels IA this ADR dissolves). Asserts:

  1. The `channels` kernel surface is GONE (no registry row, no slug in the
     FE union, no page component, no registry-map entry).
  2. connectors + sources panes are re-homed pane_of: workspace-settings, group
     "Perception" (reverses ADR-385 D4).
  3. Workspace Settings mounts the Perception group (Connectors · Sources),
     always-present — ConnectedIntegrationsSection + SourcesCard live here now.
  4. The Activity workbench (ActivityLedger) carries the Out lens (EmissionsView).
  5. /channels + /context are next.config.js redirect stubs → /home; the
     connectors/sources stub pages point at /workspace-settings.
  6. DEFAULT_KEPT_SURFACES is ['home']; channels/context/feed normalize → home.
  7. No live `navigateToSurface('channels')` / `to="channels"` call sites remain.

Run: pytest test_adr415_channels_dissolved.py -q
"""

import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEB = os.path.normpath(os.path.join(_HERE, "..", "web"))


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


def _read_api(rel: str) -> str:
    with open(os.path.join(_HERE, rel), encoding="utf-8") as fh:
        return fh.read()


_WSETTINGS = "app/(authenticated)/workspace-settings/page.tsx"
_ACTIVITY = "components/notifications/ActivityLedger.tsx"


# ---- 1. the channels surface is gone -------------------------------------

def test_channels_surface_deleted_from_registry():
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    assert "channels" not in by_slug, "channels kernel surface row must be deleted"


def test_channels_page_component_deleted():
    assert not os.path.exists(os.path.join(_HERE, "app/(authenticated)/channels/page.tsx")), \
        "channels page component must be deleted"


def test_channels_removed_from_fe_union_and_registry():
    desk = _read_web("types/desk.ts")
    # No quoted 'channels' slug literal in the union or the slug array.
    assert "'channels'" not in desk, "channels must be removed from the KernelSurfaceSlug union + array"
    registry = _read_web("components/shell/SurfaceRegistry.tsx")
    assert "channels: ChannelsPage" not in registry
    assert "ChannelsPage" not in registry, "the ChannelsPage import must be removed"


# ---- 2. connectors + sources re-homed to workspace-settings --------------

def test_connectors_sources_pane_of_workspace_settings():
    src = _read_api("services/kernel_surfaces.py")
    assert '"pane_of": "channels"' not in src, "no pane may still point at the dissolved channels"
    # Both connectors + sources now home to workspace-settings, group Perception.
    assert src.count('"pane_of": "workspace-settings"') >= 2
    assert src.count('"pane_group": "Perception"') >= 2


# ---- 3. Workspace Settings mounts the Perception group --------------------

def test_workspace_settings_has_perception_group():
    src = _read_web(_WSETTINGS)
    assert 'label: "Perception"' in src
    assert 'key: "connectors"' in src
    assert 'key: "sources"' in src
    assert "ConnectedIntegrationsSection" in src
    assert "SourcesCard" in src
    # Access group survives.
    assert 'label: "Access"' in src


# ---- 4. Activity carries the Out lens ------------------------------------

def test_activity_has_out_lens():
    src = _read_web(_ACTIVITY)
    assert "EmissionsView" in src, "ActivityLedger must mount EmissionsView as the Out lens"
    assert "DirectionLens" in src or "DIRECTION_LENSES" in src
    # the lens keys
    assert "'out'" in src and "'timeline'" in src


# ---- 5. redirects re-homed -----------------------------------------------

def test_channels_context_redirect_to_home():
    src = _read_web("next.config.js")
    assert "redirects()" in src
    assert "'/channels'" in src and "'/home'" in src
    assert "'/context'" in src


def test_connectors_sources_stubs_point_at_workspace_settings():
    conn = _read_web("app/(authenticated)/connectors/page.tsx")
    srcs = _read_web("app/(authenticated)/sources/page.tsx")
    assert "workspace-settings.pane=connectors" in conn
    assert "workspace-settings.pane=sources" in srcs
    assert "/channels" not in conn and "/channels" not in srcs


# ---- 6. defaults + normalization -----------------------------------------

def test_default_kept_is_home():
    src = _read_web("lib/shell/surface-preferences.ts")
    assert "DEFAULT_KEPT_SURFACES: string[] = ['home']" in src


def test_legacy_slugs_normalize_to_home():
    prefs = _read_web("lib/shell/surface-preferences.ts")
    assert "channels: 'home'" in prefs
    assert "context: 'home'" in prefs
    assert "feed: 'home'" in prefs


# ---- 7. no live channels call sites --------------------------------------

def test_no_live_channels_nav_call_sites():
    # Scan the whole web/{app,components,lib} tree for a live navigateToSurface
    # or SurfaceLink to the dissolved surface. Comments are allowed (historical
    # lineage); only the code forms matter.
    offenders = []
    for root_rel in ("app", "components", "lib"):
        root = os.path.join(_WEB, root_rel)
        for dirpath, _dirs, files in os.walk(root):
            if "node_modules" in dirpath:
                continue
            for fn in files:
                if not (fn.endswith(".tsx") or fn.endswith(".ts")):
                    continue
                path = os.path.join(dirpath, fn)
                with open(path, encoding="utf-8") as fh:
                    txt = fh.read()
                if re.search(r"navigateToSurface\(\s*['\"]channels['\"]", txt):
                    offenders.append(f"{path}: navigateToSurface('channels')")
                if re.search(r"to=\"channels\"|to='channels'", txt):
                    offenders.append(f"{path}: SurfaceLink to=channels")
    assert not offenders, "live channels nav call sites remain:\n" + "\n".join(offenders)
