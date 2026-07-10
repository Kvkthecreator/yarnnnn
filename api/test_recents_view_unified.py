"""Unified Recents view gate (2026-06-25).

The operator asked for a consistent Finder/Explorer view between the Files-recents
and the Home front-page recents: both should render the same component, with an
icon/list toggle (default icon) and per-file-type icons. Before this, the two had
diverged (Files = columnar table, Home = bespoke cards) with copy-pasted helpers.

This gate locks in the Singular Implementation: ONE shared <RecentsView>, mounted
in both surfaces, with the view toggle + the shared <FileIcon> covering the
workspace's file types (incl. the .yaml machine-config gap).

FE-only — source-guard style (no JS test runner), `tsc --noEmit` is the companion.

Invariants:
  1. RecentsView exists, reads the single data source (recentRevisions), and
     offers both icon + list modes with a persisted toggle defaulting to icon.
  2. Both mounts (Home HomeRecents + Files RecentRevisions) delegate to it — the
     two prior bespoke renderers are gone (no duplicated author/where helpers).
  3. FileIcon covers .yaml/.yml (the machine-config gap) so recents tiles get a
     real type glyph, and exposes an `xl` size for the icon grid.
  4. The icon view uses FileIcon (type-aware glyphs), not a bare dot.

Run: pytest test_recents_view_unified.py -q
"""
from __future__ import annotations

import os

_WEB = os.path.join(os.path.dirname(__file__), "..", "web")


def _read_web(rel: str) -> str:
    with open(os.path.join(_WEB, rel), encoding="utf-8") as fh:
        return fh.read()


def test_recents_view_exists_with_toggle_default_icon():
    src = _read_web("components/workspace/RecentsView.tsx")
    assert "export function RecentsView" in src
    # single data source
    assert "recentRevisions" in src
    # two view modes
    assert "'icon'" in src and "'list'" in src
    assert "function IconGrid" in src and "function ListTable" in src
    # persisted toggle, default icon
    assert "const DEFAULT_MODE: RecentsViewMode = 'icon'" in src
    assert "localStorage.setItem(VIEW_PREF_KEY" in src
    assert "function ViewToggle" in src


def test_both_mounts_delegate_to_shared_view():
    # ADR-435: the Home mount (HomeRecents) was deleted with the Home surface.
    # Files (RecentRevisions) remains the mount, and still delegates to the
    # shared RecentsView rather than re-fetching or re-declaring the helpers.
    files = _read_web("components/workspace/RecentRevisions.tsx")
    assert "RecentsView" in files, "Files mount must delegate to RecentsView."
    assert "recentRevisions(" not in files, (
        "RecentRevisions must not re-fetch the feed — it delegates to RecentsView."
    )
    assert "function authorAccent" not in files and "function formatAuthorLabel" not in files, (
        "RecentRevisions must not re-declare the recents helpers (deduped into RecentsView)."
    )


def test_fileicon_covers_yaml_and_has_xl_size():
    src = _read_web("components/workspace/FileIcon.tsx")
    # the machine-config gap is filled
    assert "'.yaml'" in src and "'.yml'" in src, (
        "FileIcon must map .yaml/.yml (ADR-254 machine-config) so recents tiles "
        "get a real type glyph instead of the generic File fallback."
    )
    # the icon-grid glyph size
    assert "xl" in src and "w-8 h-8" in src, "FileIcon must expose an xl size for the icon grid."


def test_icon_view_uses_type_aware_glyph():
    src = _read_web("components/workspace/RecentsView.tsx")
    assert "FileIcon" in src, "RecentsView must render the shared type-aware FileIcon."
    # the icon grid uses the xl glyph
    assert 'size="xl"' in src


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
