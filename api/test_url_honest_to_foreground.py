"""Honest-address-bar gate (2026-06-25).

Operator-observed: on Home (arrived from Settings), the URL still read
`yarnnn.com/desktop?settings.pane=account` — a stale namespaced param from a
surface no longer foregrounded. The window-namespacing (ADR-358 D6) solved param
COLLISION but left the address bar dishonest: params accumulated across every
surface visited and never reconciled to where the operator actually is.

Fix: the URL shows ONLY the foregrounded surface's params. On every foreground,
reconcileUrl strips all `{slug}.{key}` namespaced params and re-applies the
foregrounded surface's REMEMBERED params (persisted in WindowState.params,
lossless across backgrounding) merged with any just-delivered params. A cold-load
shared deep-link for the foregrounded surface is adopted, not blown away.

FE-only — source-guard style (no JS test runner); `tsc --noEmit` is the
companion type gate run in web/.

Invariants:
  1. WindowState carries a `params` field (the per-window remembered deep-link
     state — so a backgrounded surface's pane/tab survives the URL prune).
  2. A single reconcileUrl helper exists: strips all known-surface namespaced
     params, re-applies the foreground surface's remembered + delivered params,
     persists the merge into WindowState.
  3. foregroundSurface routes BOTH branches (pane-grade + window-grade) through
     reconcileUrl — bare navigation reconciles too (the prior bug: bare nav left
     the URL untouched, so stale params lingered).
  4. navigateToSurface is a thin pass-through to foregroundSurface (no second,
     additive replaceState that re-introduced cross-surface param accumulation).
  5. A cold-load incoming deep-link for the foregrounded surface is preserved
     (reconcile captures incoming params before stripping).
  6. setSurfaceParams mirrors in-surface param edits into WindowState.params
     (so an in-surface pane switch survives backgrounding).

Run: pytest test_url_honest_to_foreground.py -q
"""
from __future__ import annotations

import os

_WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


_HOOK = "lib/shell/useSurfacePreferences.tsx"


def test_windowstate_has_params_field():
    src = _read_web("lib/shell/surface-preferences.ts")
    assert "params?: Record<string, string>" in src, (
        "WindowState must carry a `params` field — a backgrounded surface's "
        "pane/tab must persist outside the URL once the URL only shows the "
        "foreground."
    )


def test_reconcile_helper_strips_and_reapplies():
    src = _read_web(_HOOK)
    assert "const reconcileUrl" in src, "the single reconcile helper must exist."
    # strips namespaced params of KNOWN surfaces
    assert "knownSlugs.has(" in src and "url.searchParams.delete(key)" in src
    # re-applies the foreground surface's remembered params
    assert "windowStatesRef.current[foregroundSlug]?.params" in src
    # persists the merge back into WindowState
    assert "persistWindowStates(next)" in src


def test_foreground_routes_both_branches_through_reconcile():
    src = _read_web(_HOOK)
    # pane-grade branch reconciles the PARENT with the pane delivered
    assert "reconcileUrl(parentSlug, { pane: slug" in src
    # window-grade branch reconciles too (bare nav no longer leaves URL as-is)
    assert "reconcileUrl(slug, deliverParams)" in src


def test_raise_window_reconciles_url_canvas_honesty():
    """The canvas-mode honesty fix (2026-06-26): raising an already-open window
    (Dock / TopBar / body-click — incl. canvas mode where the title bar is
    chromeless) must ALSO reconcile the URL. Without this, switching between
    open surfaces left the prior surface's namespaced params in the URL
    (operator saw `?workspace-settings.pane=principles&agents.agent=reviewer`
    while foregrounded on agents). reconcileUrl was previously only on the
    foregroundSurface path."""
    src = _read_web(_HOOK)
    raise_body = src[src.index("const raiseWindow"):]
    # bound the slice to the callback (its dep array close) so we assert on
    # raiseWindow's body, not a later occurrence.
    raise_body = raise_body[: raise_body.index("reconcileUrl]") + len("reconcileUrl]")]
    assert "reconcileUrl(slug)" in raise_body, (
        "raiseWindow must call reconcileUrl(slug) so the URL stays honest on "
        "every foreground change, not only foregroundSurface."
    )
    # reconcileUrl must be in the dep array (stale-closure guard).
    assert "reconcileUrl]" in raise_body


def test_navigate_is_thin_passthrough():
    src = _read_web(_HOOK)
    # navigateToSurface delegates to foregroundSurface(slug, params); it must NOT
    # re-introduce its own additive set-loop (the prior accumulation source).
    assert "return foregroundSurface(slug, params);" in src
    # the old additive per-key set inside navigateToSurface is gone
    assert "url.searchParams.set(scopeParamKey(slug, k), v)" not in src, (
        "navigateToSurface must not additively set params — that accumulated "
        "cross-surface params. It passes through to reconcileUrl."
    )


def test_cold_load_deep_link_is_adopted_not_stripped():
    src = _read_web(_HOOK)
    # reconcile captures the foreground slug's INCOMING url params before strip
    assert "const incoming" in src
    assert "key.startsWith(prefix)" in src
    # incoming is the lowest-priority layer of the merge (adopted, then
    # overridden by remembered/delivered if present)
    assert "...incoming" in src


def test_set_surface_params_mirrors_into_windowstate():
    src = _read_web(_HOOK)
    # setSurfaceParams persists the edit into WindowState.params so an in-surface
    # pane switch survives backgrounding.
    body = src[src.index("const setSurfaceParams"):]
    assert "params: merged" in body
    assert "persistWindowStates(next)" in body


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
