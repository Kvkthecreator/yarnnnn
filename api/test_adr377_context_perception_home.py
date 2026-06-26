"""Context-as-perception-home gate (ADR-377, 2026-06-26).

Context was a thin ADR-370 composition over mirrors: In = a SECOND MOUNT of the
Workspace-Settings → Perception panes (ConnectedIntegrationsSection + SourcesCard),
Out = EmissionsView, Flow = FeedSurface. The walk exposed the incoherence: In was
a borrowed config console (Connect buttons, API-key fields), the title bar read
"Feed" not "Context" (the feed→context cleanup was half-done), and connections
were mounted in BOTH Context and Workspace-Settings (a dual-home).

ADR-377 Option A: Context becomes a Settings-like section-nav perception home —
PERCEPTION[Connections · Sources] + BOUNDARY[Emissions · Flow], default
`connections`. Connections is the OWNED rich UI (status · coverage · freshness +
"View flow →"); Workspace-Settings keeps a thin pointer (Singular Implementation:
one real home). D3 folds in the title/dock fix (DEFAULT_KEPT ['feed']→['context']).

FE-only — source-guard style (no JS test runner); `tsc --noEmit` is the companion
type gate run in web/.

Invariants:
  1. Context page has the four Option-A panes in two groups, default connections.
  2. The In/Out/Flow lens triple is retired (no "in"/"out" pane keys).
  3. The Connections pane mounts ConnectedIntegrationsSection with showFreshness +
     redirectTo back to Context.
  4. Dual-home resolved: ConnectedIntegrationsSection mounted in exactly ONE page
     (Context), NOT in Workspace-Settings.
  5. Workspace-Settings connectors pane is a thin pointer → Context.
  6. D3 title/dock fix: DEFAULT_KEPT is ['context']; Desktop first-time check uses
     'context'.
  7. The freshness backend read already exists (getSyncStatus) — no new endpoint.
  8. /feed stub and /connectors stub both redirect into Context.

Run: pytest test_adr377_context_perception_home.py -q
"""
from __future__ import annotations

import glob
import os

_WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


_CONTEXT = "app/(authenticated)/context/page.tsx"
_WSETTINGS = "app/(authenticated)/workspace-settings/page.tsx"


def test_context_has_option_a_four_panes_two_groups():
    src = _read_web(_CONTEXT)
    # two groups
    assert 'label: "Perception"' in src
    assert 'label: "Boundary"' in src
    # four pane keys
    for key in ("connections", "sources", "emissions", "flow"):
        assert f'key: "{key}"' in src, f"missing pane key {key}"
    # default lands on the perception home
    assert 'defaultPane="connections"' in src
    # nav label no longer says "lenses"
    assert "Context lenses" not in src


def test_in_out_flow_lens_triple_retired():
    src = _read_web(_CONTEXT)
    # the old lens pane keys are gone (case-block markers)
    assert 'case "in":' not in src
    assert 'case "out":' not in src


def test_connections_pane_owns_rich_ui_with_freshness():
    src = _read_web(_CONTEXT)
    assert "ConnectedIntegrationsSection" in src
    assert "showFreshness" in src
    # OAuth round-trip lands back on Context, not Settings
    assert 'redirectTo="/context?context.pane=connections"' in src
    # the View-flow affordance switches to the Flow pane
    assert 'onViewFlow' in src and 'pane: "flow"' in src


def test_dual_home_resolved_single_mount():
    """The load-bearing Singular-Implementation invariant: ConnectedIntegrations-
    Section is mounted in exactly ONE page (Context), never Workspace-Settings."""
    context = _read_web(_CONTEXT)
    wsettings = _read_web(_WSETTINGS)
    assert "ConnectedIntegrationsSection" in context
    assert "ConnectedIntegrationsSection" not in wsettings, (
        "Workspace-Settings must NOT mount ConnectedIntegrationsSection — it keeps "
        "a thin pointer to Context (ADR-377 D2)."
    )


def test_workspace_settings_keeps_thin_pointer():
    src = _read_web(_WSETTINGS)
    # the connectors pane points at Context's connections pane
    assert 'navigateToSurface("context"' in src
    assert 'pane: "connections"' in src


def test_d3_title_dock_fix():
    prefs = _read_web("lib/shell/surface-preferences.ts")
    assert "DEFAULT_KEPT_SURFACES: string[] = ['context']" in prefs
    assert "DEFAULT_KEPT_SURFACES: string[] = ['feed']" not in prefs
    desktop = _read_web("components/shell/Desktop.tsx")
    assert "kept[0] !== 'context'" in desktop
    assert "kept[0] !== 'feed'" not in desktop


def test_freshness_backend_read_exists():
    """The per-platform freshness uses an EXISTING read — no new endpoint."""
    client = _read_web("lib/api/client.ts")
    assert "getSyncStatus" in client
    assert "sync-status" in client


def test_feed_and_connectors_stubs_redirect_into_context():
    feed = _read_web("app/(authenticated)/feed/page.tsx")
    assert "/context" in feed and "context.pane=flow" in feed
    connectors = _read_web("app/(authenticated)/connectors/page.tsx")
    assert "/context?context.pane=connections" in connectors
    # no longer routes to workspace-settings
    assert "workspace-settings" not in connectors


def test_connected_integrations_freshness_is_opt_in():
    """showFreshness defaults false so the prop is additive — any non-Context
    consumer keeps legacy behavior."""
    src = _read_web("components/settings/ConnectedIntegrationsSection.tsx")
    assert "showFreshness = false" in src
    # freshness only fans out to sync-registry providers
    assert "FRESHNESS_PROVIDERS" in src


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
