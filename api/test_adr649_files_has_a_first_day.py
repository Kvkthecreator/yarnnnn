"""ADR-649 gate — the Files surface has a first day.

Born of a prod census (2026-09-12): five of the six newest workspaces held
exactly 17 files, all kernel mirrors under `system/`, and the Files surface
showed a new member (a) those 17 as "recent changes", (b) a sidebar whose only
node was "System files", and (c) no visible way to create anything on desktop.

Four decisions, each driven where it can be:

  §1  Recents excludes the kernel's mirrors (`system/`) — DRIVEN.
  §2  The roots always show the two homes, Documents + Downloads — DRIVEN
      against an EMPTY substrate through a fake client.
  §3  The create door is visible at every pointer, and the cold-start empty
      state carries both doors — STRUCTURAL (a gate that greps a gesture has
      not run it; the click-pass on a fresh workspace is the real check).
  §4  A new folder from nowhere lands in Documents — STRUCTURAL.

Run:  cd api && python3 -B -m pytest -q test_adr649_files_has_a_first_day.py
"""
from __future__ import annotations

import asyncio
import pathlib
import re
import sys
import types

import pytest

API = pathlib.Path(__file__).resolve().parent
ROOT = API.parent
WEB = ROOT / "web"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))

import routes.workspace as rw  # noqa: E402


# ── §1 Recents excludes the kernel's mirrors ─────────────────────────────────

@pytest.mark.parametrize("path, authored", [
    ("/workspace/system/skills/writing-a-spec/SKILL.md", False),   # kernel mirror (ADR-630)
    ("/workspace/system/agents/editor/face.png", False),           # kernel mirror (ADR-641 am.2)
    ("/workspace/system/skills/_manifest.yaml", False),
    ("/workspace/skills/my-own/SKILL.md", True),                   # a MEMBER's skill stays
    ("/workspace/operation/brief.md", True),
    ("/workspace/operation/signals/2026-09-12.md", False),         # the log the tree hides
    ("/workspace/inbound/uploads/operator/deck.pdf", True),
])
def test_s1_recents_is_what_members_and_agents_wrote(path, authored):
    assert rw._is_authored_substrate_path(path) is authored, path


def test_s1_the_stale_signals_literal_is_gone():
    # `context/` dissolved in ADR-320; the literal matched nothing on prod.
    assert "/workspace/context/signals" not in rw._RECENT_REV_EXCLUDE_DIRS
    assert "/workspace/system/" in rw._RECENT_REV_EXCLUDE_DIRS


# ── §2 The roots always show the two homes ───────────────────────────────────

class _Query:
    """A chainable PostgREST stand-in: every builder call returns self."""

    def __init__(self, rows):
        self._rows = rows

    def __getattr__(self, _name):
        return lambda *a, **k: self

    def execute(self):
        return types.SimpleNamespace(data=self._rows)


class _Client:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        assert name == "workspace_files", name
        return _Query(self._rows)


def _roots(rows, monkeypatch):
    # The placement decision is ADR-643's and has its own gate; pin it open.
    monkeypatch.setattr(rw, "_may_place", lambda auth, folder: True)
    auth = types.SimpleNamespace(user_id="u", workspace_id="w", client=_Client(rows))
    return asyncio.run(rw.get_workspace_roots(auth))


def test_s2_an_empty_workspace_still_has_documents_and_downloads(monkeypatch):
    out = _roots([], monkeypatch)
    by = {r["name"]: r for r in out}
    assert {"operation", "inbound", "agents"} <= set(by), sorted(by)
    docs, dl = by["operation"], by["inbound"]
    assert docs["display_name"] == "Documents" and docs["group"] == "work"
    assert docs["exists"] is False and docs["file_count"] == 0
    assert dl["display_name"] == "Downloads" and dl["group"] == "arrival"
    assert dl["exists"] is False and dl["file_count"] == 0
    # ADR-395 stands: the LEGACY arrival root shows only when it holds files.
    assert "uploads" not in by
    # Documents leads the sidebar (WORKSPACE_ROOTS order), so a fresh
    # workspace opens on its home, not on "System files".
    assert out[0]["name"] == "operation", [r["name"] for r in out]


def test_s2_a_populated_home_keeps_its_count(monkeypatch):
    rows = [
        {"path": "/workspace/operation/brief.md", "content_type": "text/markdown"},
        {"path": "/workspace/operation/deal/", "content_type": "inode/directory"},
    ]
    by = {r["name"]: r for r in _roots(rows, monkeypatch)}
    # ADR-588: the marker makes it exist but is not a file.
    assert by["operation"]["exists"] is True and by["operation"]["file_count"] == 1


# ── §3 / §4 the FE — structural ──────────────────────────────────────────────

def _code(src: str) -> str:
    """Strip block + line comments so a check never matches its own prose."""
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    return re.sub(r"(^|\s)//[^\n]*", r"\1", src, flags=re.M)


PAGE = _code((WEB / "app" / "(authenticated)" / "files" / "page.tsx").read_text())
RECENTS = _code((WEB / "components" / "workspace" / "RecentsView.tsx").read_text())
WRAPPER = _code((WEB / "components" / "workspace" / "RecentRevisions.tsx").read_text())


def test_s3_the_create_door_is_visible_at_every_pointer():
    # The touch-only gate on the header buttons is gone…
    assert "coarse &&" not in PAGE
    # …replaced by ONE "+" that opens the SAME canvas menu the right-click opens.
    plus = re.search(r"<button[^>]*?onClick=\{\(e\) => \{[\s\S]{0,300}?setCanvasMenu\(\{ x: r\.left, y: r\.bottom[\s\S]{0,400}?<Plus ", PAGE)
    assert plus, "the Explorer header must carry a + that anchors the canvas menu"
    assert "<CanvasContextMenu" in PAGE
    # The capability still governs the tap-to-open grammar (ADR-452) — only
    # the create door stopped depending on it.
    assert re.search(r"if \(coarse \|\|", PAGE)


def test_s3_the_empty_state_carries_both_doors():
    start = RECENTS.find("!loading && revisions.length === 0")
    assert start != -1
    end = RECENTS.find('<div className="flex flex-col">', start)
    branch = RECENTS[start:end]
    # Each door is a BUTTON wired to its act — not merely a name in scope.
    assert "onClick={onNewFolder}" in branch and "onClick={onAddFiles}" in branch, "the cold-start branch renders both doors"
    assert "hideWhenEmpty" in branch, "a self-hiding slot never shows them"
    # A narrow pane wraps them rather than overflowing.
    assert "flex-wrap" in branch
    # Threaded through the wrapper from the page, and scoped like the menu.
    assert "onNewFolder={onNewFolder}" in WRAPPER and "onAddFiles={onAddFiles}" in WRAPPER
    assert PAGE.count("onNewFolder={() => openNewFolder(newFolderScope())}") == 2  # menu + empty state
    assert PAGE.count("onAddFiles={() => openUpload()}") == 2


def test_s4_a_new_folder_from_nowhere_lands_in_documents():
    assert "const DOCUMENTS_ROOT_PATH = '/workspace/operation';" in PAGE
    i = PAGE.find("const newFolderScope = useCallback(")
    assert i != -1
    fn = PAGE[i:i + 700]
    assert "viewNode.path.startsWith('/workspace/')" in fn  # an open real folder wins
    assert "DOCUMENTS_ROOT_PATH" in fn                       # else Documents
    assert "documents?.name ?? 'Documents'" in fn            # label read off the served roots
    # No door on the surface passes the top-level-peer fallback any more.
    assert "openNewFolder(null)" not in PAGE


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
