"""ADR-369 gate — The Home Split (one surface, two tabs: kernel front page +
program cockpit).

ADR-369 is FE-only — the `home` surface gains an internal segmented control and
its slots redistribute across two composition bodies (kernel-shaped vs
program-shaped). No schema, primitive, backend, or Render-service change. The
web package has no JS test runner, so the load-bearing FE invariants are guarded
here by source-assertion (the same pattern as the ADR-350 / ADR-367 FE guards),
with `tsc --noEmit` as the companion type gate run in web/.

Invariants:
  1. Tab state is the window-namespaced param `home.tab` via useSurfaceParam,
     default 'home' (ADR-358 D6; SSR-safe initializer).
  2. The program tab is ADDITIVE — the segmented control + ProgramCockpit render
     only when an active bundle exists (gated on active_bundles). A Layer-1
     operator (no program) sees only the Home front page.
  3. The program tab is labeled from the active program (ADR-222 — the kernel
     hardcodes NO program noun; the label derives from the bundle's own MANIFEST
     title, with the generic "Operation" fallback).
  4. The kernel-shaped slots live in HomeFrontPage (constitution band, decision
     queue, recents, recent artifacts, judgment trail) — the §D4 order.
  5. The program-shaped slots live in ProgramCockpit: the relocated StandingBand
     (§D5) + the program_sections dispatch.
  6. HomeRecents is a DISTINCT kernel slot reusing the Files-recents data source
     (api.workspace.recentRevisions), separate from KernelRecentArtifacts (§D6).
  7. The `home` launcher tile is unchanged — the split is intra-surface, NOT a
     new launcher destination (§D2, §3).

Run: pytest test_adr369_home_split.py -q
"""
from __future__ import annotations

import os

_HERE = os.path.dirname(__file__)
_WEB = os.path.join(_HERE, "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# 1 — tab state via the window-namespaced `home.tab` param, default 'home'
# ---------------------------------------------------------------------------

def test_tab_state_uses_home_namespaced_param_default_home():
    src = _read_web("components/library/HomeRenderer.tsx")
    # window-namespaced param via the canonical hook (ADR-358 D6)
    assert "useSurfaceParam" in src
    assert "useSurfaceParam(HOME_TAB)" in src or "useSurfaceParam('home')" in src
    # the param key is `tab` (→ `home.tab` after scopeParamKey)
    assert ".get('tab')" in src or '.get("tab")' in src
    assert ".set({ tab:" in src
    # default is 'home' (SSR-safe: state initializes to the default, the param
    # is applied post-mount)
    assert "const HOME_TAB = 'home'" in src
    assert "useState<string>(HOME_TAB)" in src


# ---------------------------------------------------------------------------
# 2 — the program tab is ADDITIVE (gated on active_bundles)
# ---------------------------------------------------------------------------

def test_program_tab_is_additive_gated_on_active_bundles():
    src = _read_web("components/library/HomeRenderer.tsx")
    # the program tab presence derives from an active bundle
    assert "active_bundles" in src
    assert "showProgramTab" in src
    # the segmented control renders only when there's a program tab to switch to
    assert "{showProgramTab && (" in src
    # ProgramCockpit only mounts on the program branch (additive view)
    assert "showProgramTab ? (" in src or "&& showProgramTab" in src


# ---------------------------------------------------------------------------
# 3 — the program tab is program-labeled (no hardcoded program noun)
# ---------------------------------------------------------------------------

def test_program_tab_labeled_from_program_not_kernel_noun():
    src = _read_web("components/library/HomeRenderer.tsx")
    # the label derives from the active bundle's own title
    assert "programTabLabel" in src
    assert "activeBundle?.title" in src
    # generic fallback only — no kernel-hardcoded program noun (ADR-222)
    assert "'Operation'" in src
    assert "Trader" not in src, (
        "ADR-222/ADR-369 §D2: the kernel must not hardcode a program noun in "
        "the Home tab label — it derives from the program's MANIFEST."
    )


# ---------------------------------------------------------------------------
# 4 — kernel-shaped slots live in HomeFrontPage (the §D4 order)
# ---------------------------------------------------------------------------

def test_kernel_slots_live_in_home_front_page():
    front = _read_web("components/library/kernel-home/HomeFrontPage.tsx")
    # constitution band + the kernel-universal slots + the visual recents
    for comp in (
        "HomeHeader",
        "KernelDecisionQueue",
        "HomeRecents",
        "KernelRecentArtifacts",
        "KernelJudgmentTrail",
    ):
        assert comp in front, f"HomeFrontPage must render the kernel slot {comp}."

    # §D4 order: decision queue → recents → recent artifacts → judgment trail.
    # Anchor on the JSX tags (not the bare token, which the import block + the
    # docstring both repeat) so the gate tracks the actual render order.
    assert front.index("<KernelDecisionQueue") < front.index("<HomeRecents")
    assert front.index("<HomeRecents") < front.index("<KernelRecentArtifacts")
    assert front.index("<KernelRecentArtifacts") < front.index("<KernelJudgmentTrail")

    # HomeRenderer dispatches to the body (it no longer inlines the slots)
    home = _read_web("components/library/HomeRenderer.tsx")
    assert "<HomeFrontPage" in home


# ---------------------------------------------------------------------------
# 5 — program-shaped slots live in ProgramCockpit (StandingBand + sections)
# ---------------------------------------------------------------------------

def test_program_cockpit_holds_standing_band_and_sections():
    cockpit = _read_web("components/library/kernel-home/ProgramCockpit.tsx")
    # the relocated standing band (§D5)
    assert "<StandingBand />" in cockpit
    # the program_sections dispatch (moved here from HomeRenderer)
    assert "dispatchComponent({ kind:" in cockpit
    assert "programSections" in cockpit
    # the band heads the cockpit — above the program-section dispatch (compare
    # against the JSX call site, not the import, which necessarily precedes JSX)
    assert cockpit.index("<StandingBand />") < cockpit.index("dispatchComponent({ kind:")

    # HomeRenderer dispatches to the cockpit body
    home = _read_web("components/library/HomeRenderer.tsx")
    assert "<ProgramCockpit" in home


# ---------------------------------------------------------------------------
# 6 — HomeRecents is distinct, reusing the Files-recents data source (§D6)
# ---------------------------------------------------------------------------

def test_home_recents_reuses_files_recents_data_source():
    src = _read_web("components/library/kernel-home/HomeRecents.tsx")
    # reuses the ADR-209 revision feed — the SAME data source the Files surface
    # Recents reads (Singular Implementation: one feed, two presentations)
    assert "recentRevisions" in src, (
        "HomeRecents must reuse api.workspace.recentRevisions (the Files-recents "
        "data source), not a parallel reader."
    )

    # the Files surface reads the same source — proves it's shared, not forked
    files = _read_web("components/workspace/RecentRevisions.tsx")
    assert "recentRevisions" in files

    # §D6: Recents (broad substrate changes) is DISTINCT from recent artifacts
    # (delivered outputs) — HomeRecents must not BE KernelRecentArtifacts.
    front = _read_web("components/library/kernel-home/HomeFrontPage.tsx")
    assert "HomeRecents" in front and "KernelRecentArtifacts" in front, (
        "ADR-369 §D6: Recents and recent artifacts are two distinct sections."
    )


# ---------------------------------------------------------------------------
# 7 — the `home` launcher tile is unchanged (intra-surface split, §D2/§3)
# ---------------------------------------------------------------------------

def test_home_launcher_tile_unchanged_no_new_destination():
    """ADR-369 §3: the split is intra-surface (`home.tab`); it adds NO launcher
    destination. The kernel surface registry still declares a single `home`
    surface with route `/home`, and no per-program home surface is added."""
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(_HERE)))
    from services.kernel_surfaces import KERNEL_SURFACES

    home_surfaces = [s for s in KERNEL_SURFACES if s["slug"] == "home"]
    assert len(home_surfaces) == 1, "exactly one `home` kernel surface."
    assert home_surfaces[0]["route"] == "/home", "the home tile route is unchanged."
    # no separate program-cockpit launcher destination crept in
    assert not any(
        s["slug"] in ("program-cockpit", "cockpit", "operation-home")
        for s in KERNEL_SURFACES
    ), "ADR-369 §3: the split adds no new launcher destination."


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
