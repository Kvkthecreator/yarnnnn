"""ADR-225 — Compositor Layer — composition resolver tests.

These tests exercise the API-side composition resolver:
- Empty workspace (no platform connections) returns empty composition.
- Workspace with alpaca connected gets alpha-trader's composition.
- Phase overlay banner is applied per active bundle's current_phase.
- Deferred bundle (alpha-commerce) does NOT surface even if its
  required_connection ('commerce') is connected — only `status: active`
  bundles surface.
- Multi-bundle workspaces union pinned_tasks, middles, chat_chips
  with deterministic ordering.

The resolver consumes only:
- Bundle YAML files (loaded via bundle_reader.lru_cache, real reads)
- platform_connections table (mocked here via a lightweight stub)

No FastAPI test client needed — the service is pure functions over a
client interface.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure api/ is on sys.path
_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))


# =============================================================================
# Test fixtures — minimal supabase client stub
# =============================================================================


class _StubResult:
    def __init__(self, data):
        self.data = data


class _StubSelect:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, _col, _val):
        # Naive filter — assumes the test sets up rows pre-filtered for the
        # combination the resolver queries. Resolver queries:
        #   .eq("user_id", uid).eq("status", "active")
        # Both criteria are pre-applied in the test fixture.
        return self

    def execute(self):
        return _StubResult(self._rows)


class _StubClient:
    def __init__(self, platform_connections_rows):
        self._rows = platform_connections_rows

    def table(self, name):
        if name == "platform_connections":
            return _StubSelect(self._rows)
        raise NotImplementedError(f"Unexpected table: {name}")


def _bust_caches():
    """Bust bundle_reader caches so test fixture changes propagate."""
    from services.bundle_reader import _load_manifest, _all_slugs
    _load_manifest.cache_clear()
    _all_slugs.cache_clear()


# =============================================================================
# Empty-workspace tests
# =============================================================================


def test_empty_workspace_returns_empty_composition():
    """Operator with no platform connections sees an empty composition tree."""
    _bust_caches()
    from services.composition_resolver import resolve_workspace_composition
    client = _StubClient(platform_connections_rows=[])
    result = resolve_workspace_composition("user-empty", client)

    assert result["schema_version"] == 1
    assert result["active_bundles"] == []
    assert result["composition"]["tabs"] == {}
    assert result["composition"]["chat_chips"] == []


def test_workspace_with_unrelated_platform_connection_returns_empty():
    """Operator connected to slack only — no bundle declares slack as
    requires_connection (slack is a capability-bundle-shaped kernel
    integration per ADR-224 §1, not a program-shape capability), so
    no bundle activates."""
    _bust_caches()
    from services.composition_resolver import resolve_workspace_composition
    client = _StubClient(platform_connections_rows=[
        {"platform": "slack", "status": "active", "created_at": "2026-01-01T00:00:00Z"},
    ])
    result = resolve_workspace_composition("user-slack-only", client)

    assert result["active_bundles"] == []
    assert result["composition"]["tabs"] == {}


# =============================================================================
# alpha-trader active tests
# =============================================================================


def test_alpaca_connected_workspace_gets_alpha_trader_bundle():
    """Workspace with alpaca connected → alpha-trader bundle activates and
    its composition surfaces (pinned_tasks, banner, middles, chat_chips)."""
    _bust_caches()
    from services.composition_resolver import resolve_workspace_composition
    client = _StubClient(platform_connections_rows=[
        {"platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
    ])
    result = resolve_workspace_composition("user-trader", client)

    # Bundle metadata surfaces
    bundles = result["active_bundles"]
    assert len(bundles) == 1
    assert bundles[0]["slug"] == "alpha-trader"
    assert bundles[0]["current_phase"] == "observation"
    assert bundles[0]["current_phase_label"] == "Phase 0 — Observation"
    assert bundles[0]["title"] == "alpha-trader"

    # Composition tree has the work tab populated
    tabs = result["composition"]["tabs"]
    assert "work" in tabs
    work_list = tabs["work"]["list"]
    assert "trading-signal" in work_list["pinned_tasks"]
    assert "portfolio-review" in work_list["pinned_tasks"]
    assert work_list["group_default"] == "output_kind"

    # chat_chips union includes alpha-trader's
    chips = result["composition"]["chat_chips"]
    assert any("signal" in c.lower() for c in chips)


def test_phase_overlay_banner_applied_to_observation():
    """alpha-trader's current_phase=observation triggers the
    'Paper-only. Live trading gated...' banner via phase_overlays."""
    _bust_caches()
    from services.composition_resolver import resolve_workspace_composition
    client = _StubClient(platform_connections_rows=[
        {"platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
    ])
    result = resolve_workspace_composition("user-trader", client)
    banner = result["composition"]["tabs"]["work"]["list"].get("banner")
    assert banner is not None
    assert "Paper-only" in banner


def test_alpha_trader_detail_middles_surface():
    """The bundle's task-detail middles are surfaced — portfolio-review
    declares a dashboard middle, trading-signal declares a queue middle."""
    _bust_caches()
    from services.composition_resolver import resolve_workspace_composition
    client = _StubClient(platform_connections_rows=[
        {"platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
    ])
    result = resolve_workspace_composition("user-trader", client)
    middles = result["composition"]["tabs"]["work"]["detail"]["middles"]
    matches = {(m.get("match", {}).get("task_slug"), m.get("archetype")) for m in middles}
    assert ("portfolio-review", "dashboard") in matches
    assert ("trading-signal", "queue") in matches


# =============================================================================
# Deferred bundle exclusion tests
# =============================================================================


def test_alpha_commerce_deferred_bundle_does_not_surface_even_when_commerce_connected():
    """Per ADR-225 §3: only status='active' bundles surface to the cockpit.
    alpha-commerce is status='deferred' — its templates never appear in
    the composition tree, regardless of platform connections."""
    _bust_caches()
    from services.composition_resolver import resolve_workspace_composition
    client = _StubClient(platform_connections_rows=[
        {"platform": "commerce", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
    ])
    result = resolve_workspace_composition("user-commerce", client)
    slugs = [b["slug"] for b in result["active_bundles"]]
    assert "alpha-commerce" not in slugs
    assert result["composition"]["tabs"] == {}


# =============================================================================
# Bundle reader workspace-scoped helper tests
# =============================================================================


def test_bundles_active_for_workspace_filters_by_platform_connection():
    """bundle_reader.bundles_active_for_workspace returns alpha-trader only
    when 'trading' platform is connected — not for unrelated platforms."""
    _bust_caches()
    from services.bundle_reader import bundles_active_for_workspace

    no_conn_client = _StubClient(platform_connections_rows=[])
    assert bundles_active_for_workspace("user", no_conn_client) == []

    slack_client = _StubClient(platform_connections_rows=[
        {"platform": "slack", "status": "active", "created_at": "2026-01-01T00:00:00Z"},
    ])
    assert bundles_active_for_workspace("user", slack_client) == []

    trading_client = _StubClient(platform_connections_rows=[
        {"platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
    ])
    bundles = bundles_active_for_workspace("user", trading_client)
    assert len(bundles) == 1
    assert bundles[0]["slug"] == "alpha-trader"


def test_bundles_active_for_workspace_excludes_deferred_bundles():
    """Even when commerce is connected, alpha-commerce (status: deferred)
    is excluded — deferred bundles are not active per ADR-225 §3."""
    _bust_caches()
    from services.bundle_reader import bundles_active_for_workspace

    commerce_client = _StubClient(platform_connections_rows=[
        {"platform": "commerce", "status": "active", "created_at": "2026-04-01T00:00:00Z"},
    ])
    bundles = bundles_active_for_workspace("user", commerce_client)
    slugs = [b.get("slug") for b in bundles]
    assert "alpha-commerce" not in slugs


# =============================================================================
# Schema invariant tests
# =============================================================================


def test_response_always_carries_schema_version_1():
    """schema_version: 1 is required on every response per ADR-225 §2."""
    _bust_caches()
    from services.composition_resolver import resolve_workspace_composition
    for rows in (
        [],
        [{"platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"}],
        [{"platform": "slack", "status": "active", "created_at": "2026-01-01T00:00:00Z"}],
    ):
        result = resolve_workspace_composition("user", _StubClient(rows))
        assert result["schema_version"] == 1


def test_response_keys_are_stable():
    """The top-level response shape is stable — schema_version /
    active_bundles / composition. Used by FE TS types."""
    _bust_caches()
    from services.composition_resolver import resolve_workspace_composition
    result = resolve_workspace_composition("user", _StubClient([]))
    assert set(result.keys()) == {"schema_version", "active_bundles", "composition"}
    assert set(result["composition"].keys()) == {"tabs", "chat_chips"}
