"""ADR-385 — Channels: the perception + principal surface.

Source-guard gate. Supersedes test_adr370_context_surface.py +
test_adr377_context_perception_home.py (both asserted the pre-385 `context`
surface). Asserts:

  1. The live primary kernel surface is `channels` (/channels route); `context`
     + `feed` survive only as search-only legacy alias entries.
  2. /context + /feed are ADR-308 redirect stubs → /channels (pure server
     transport, no 'use client').
  3. The Channels page has two groups (CHANNELS · ACTIVITY), six panes
     (connectors · sources · external-agents · flow · in · out), defaults to
     Flow.
  4. External Agents is a FILTERED VIEW of WorkspaceMembersCard
     (roleFilter=foreign-llm/a2a/platform) — NOT a new data source.
  5. In/Out/Flow preserved: In = filtered FeedSurface (isInbound), Flow =
     unfiltered, Out = EmissionsView (a distinct source).
  6. Singular Implementation: ConnectedIntegrationsSection mounts ONLY on the
     Channels page (never Workspace-Settings).
  7. D4: Workspace-Settings has no Perception group.
  8. connectors + sources kernel surfaces are pane_of: channels.
  9. DEFAULT_KEPT_SURFACES is ['channels']; legacy feed/context title-alias to
     channels; registry maps all three.

Run: pytest test_adr385_channels_surface.py -q
"""

import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEB = os.path.normpath(os.path.join(_HERE, "..", "web"))


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


def _read_api(rel: str) -> str:
    with open(os.path.join(_HERE, rel), encoding="utf-8") as fh:
        return fh.read()


_CHANNELS = "app/(authenticated)/channels/page.tsx"
_CONTEXT_STUB = "app/(authenticated)/context/page.tsx"
_FEED_STUB = "app/(authenticated)/feed/page.tsx"
_WSETTINGS = "app/(authenticated)/workspace-settings/page.tsx"


# ---- 1. live primary surface is `channels` -------------------------------

def test_kernel_surface_is_channels():
    from services.kernel_surfaces import KERNEL_SURFACES

    by_slug = {e["slug"]: e for e in KERNEL_SURFACES}
    chan = by_slug["channels"]
    assert chan["route"] == "/channels"
    assert chan["title"] == "Channels"
    assert chan["launcher_tier"] == "primary"
    # the operator-preferred in/out arrows glyph is preserved
    assert chan["icon_key"] == "arrow-left-right"
    # ADR-385 follow-on (2026-06-30): the `context` (and `feed`) legacy alias
    # ROWS are DELETED (full alias deletion). They were search-only registry
    # rows still carrying an `icon_key` + no `pane_of`, so any stale persisted
    # dock entry rendered a SECOND `arrow-left-right` icon next to `channels`
    # (the operator-observed duplicate + confusing /context→/channels redirect).
    # The slugs are retired from the registry entirely; bookmark safety moved to
    # next.config.js redirects, and persisted dock state is normalized →
    # `channels` on read (web/lib/shell/surface-preferences.ts).
    assert "context" not in by_slug, "context legacy alias row should be deleted"
    assert "feed" not in by_slug, "feed legacy alias row should be deleted"


# ---- 2. /context + /feed are next.config redirects (alias deletion) -------

def test_context_and_feed_route_stubs_deleted():
    # The page-component redirect stubs are removed (full alias deletion); the
    # route directories should no longer hold a page.
    assert not os.path.exists(os.path.join(_HERE, _CONTEXT_STUB)), \
        "/context page stub should be deleted (next.config redirect now)"
    assert not os.path.exists(os.path.join(_HERE, _FEED_STUB)), \
        "/feed page stub should be deleted (next.config redirect now)"


def test_context_and_feed_redirects_in_next_config():
    src = _read_web("next.config.js")
    # Bookmark safety for the old URLs lives in next.config.js redirects().
    assert "redirects()" in src
    assert "'/feed'" in src and "/channels?channels.pane=flow" in src
    assert "'/context'" in src


# ---- 3. Channels page shape ----------------------------------------------

def test_channels_two_groups_six_panes_default_flow():
    src = _read_web(_CHANNELS)
    assert 'label: "Channels"' in src
    assert 'label: "Activity"' in src
    for key in ("connectors", "sources", "external-agents", "flow", "in", "out"):
        assert f'key: "{key}"' in src, f"missing pane key {key}"
    assert 'defaultPane="flow"' in src
    assert 'windowSlug="channels"' in src


# ---- 4. External Agents = filtered WorkspaceMembersCard -------------------

def test_external_agents_is_filtered_members_view():
    src = _read_web(_CHANNELS)
    assert "WorkspaceMembersCard" in src
    assert "roleFilter" in src
    for role in ("foreign-llm", "a2a", "platform"):
        assert role in src, f"missing external role {role}"


def test_members_card_supports_role_filter():
    src = _read_web("components/workspace-concepts/WorkspaceMembersCard.tsx")
    assert "roleFilter" in src
    assert "members.filter" in src
    assert "getMembers" in src


# ---- 5. In/Out/Flow preserved as distinct views --------------------------

def test_in_out_flow_distinct():
    src = _read_web(_CHANNELS)
    assert "isInbound" in src and "messageFilter" in src
    assert "FeedSurface" in src
    assert "EmissionsView" in src


def test_direction_helper_intact():
    src = _read_web("lib/feed-direction.ts")
    assert "export function isInbound" in src
    assert "recall" in src and "trace" in src
    assert "writtenTo" in src


# ---- 6. Singular Implementation: one ConnectedIntegrations mount ----------

def test_connected_integrations_single_mount():
    channels = _read_web(_CHANNELS)
    wsettings = _read_web(_WSETTINGS)
    assert "ConnectedIntegrationsSection" in channels
    assert "ConnectedIntegrationsSection" not in wsettings, (
        "Workspace-Settings must NOT mount ConnectedIntegrationsSection — "
        "perception is wholly owned by Channels (ADR-385 D4)."
    )


# ---- 7. D4: Workspace-Settings has no Perception group --------------------

def test_workspace_settings_drops_perception_group():
    src = _read_web(_WSETTINGS)
    assert 'label: "Perception"' not in src
    assert 'key: "connectors"' not in src
    assert 'key: "sources"' not in src
    assert "SourcesCard" not in src
    assert 'label: "Access"' in src
    assert "WorkspaceMembersCard" in src


# ---- 8. connectors + sources pane_of channels ----------------------------

def test_connectors_sources_pane_of_channels():
    src = _read_api("services/kernel_surfaces.py")
    assert src.count('"pane_of": "channels"') >= 2
    assert '"pane_group": "Perception"' not in src


# ---- 9. defaults + title aliases -----------------------------------------

def test_default_kept_is_channels():
    src = _read_web("lib/shell/surface-preferences.ts")
    assert "DEFAULT_KEPT_SURFACES: string[] = ['channels']" in src


def test_legacy_slugs_normalized_in_persisted_state():
    # ADR-385 follow-on (2026-06-30): full alias deletion. The legacy `feed`/
    # `context` slugs are normalized → `channels` ONCE, at the surface-
    # preferences read boundary (replacing the scattered title/registry alias
    # maps). The title-alias map is gone; the normalizer is the single point.
    prefs = _read_web("lib/shell/surface-preferences.ts")
    assert "LEGACY_SLUG_ALIASES" in prefs
    assert "context: 'channels'" in prefs and "feed: 'channels'" in prefs
    assert "normalizeSlugList" in prefs
    # The render-alias title map is deleted (no longer needed — nothing
    # foregrounds the legacy slugs after normalization).
    title = _read_web("lib/compositor/surfaceTitle.ts")
    assert "TITLE_ALIAS" not in title


def test_registry_drops_legacy_aliases():
    # ADR-385 follow-on (2026-06-30): the `feed`/`context` → ChannelsPage alias
    # keys are DELETED from the registry (full alias deletion). Only `channels`.
    src = _read_web("components/shell/SurfaceRegistry.tsx")
    assert "channels: ChannelsPage" in src
    assert "feed: ChannelsPage" not in src
    assert "context: ChannelsPage" not in src
