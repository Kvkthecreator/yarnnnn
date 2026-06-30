"""ADR-388 — Files as a filesystem-native surface.

Source-guard gate. Asserts the derived tree (D1), the shared attribution
module (D2/D3), the surface-wide view mode (D4), and the Get-Info modal (D5).

D1 — tree derived from real FS roots (no hardcoded root array):
  1. WORKSPACE_ROOTS map + root_metadata() fallback in workspace_paths.py
  2. GET /workspace/roots endpoint exists
  3. files/page.tsx derives from getRoots() (buildRootNodes, not the deleted
     hardcoded buildContextNodes 7-group array)
  4. api.workspace.getRoots() client method
D2/D3 — one shared attribution module, all consumers route through it:
  5. lib/workspace/attribution.ts exports the helpers + the MCP-host form
  6. no LOCAL author-helper definitions remain in the Files surface components
D4 — surface-wide view mode (not Recents-only):
  7. useFilesViewMode hook exists; ContentViewer + page consume it
D5 — Get-Info modal with the revision chain:
  8. GetInfoModal exists, wraps NodeDetailsPanel; page mounts it; right-click
     wired on the tree + folder listing

Run: pytest test_adr388_files_surface.py -q
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


_PAGE = "app/(authenticated)/files/page.tsx"
_CONTENT = "components/workspace/ContentViewer.tsx"
_ATTRIB = "lib/workspace/attribution.ts"


# ---- D1: derived tree -----------------------------------------------------

def test_workspace_roots_map_and_fallback():
    src = _read_api("services/workspace_paths.py")
    assert "WORKSPACE_ROOTS" in src
    assert "def root_metadata" in src
    # known roots that were INVISIBLE before ADR-388 are mapped
    for root in ("constitution", "governance", "inbound"):
        assert f'"{root}"' in src, f"missing root {root} in WORKSPACE_ROOTS"


def test_roots_endpoint_exists():
    src = _read_api("routes/workspace.py")
    assert '@router.get("/workspace/roots")' in src
    assert "async def get_workspace_roots" in src
    # cheap depth-1 distinct scan, not a full subtree
    assert "split" in src or "/workspace/" in src


def test_page_derives_tree_from_roots():
    src = _read_web(_PAGE)
    # the new derive path
    assert "buildRootNodes" in src
    assert "api.workspace.getRoots()" in src
    # the hardcoded 7-group assembler is GONE
    assert "buildContextNodes" not in src


def test_client_has_getRoots():
    src = _read_web("lib/api/client.ts")
    assert "getRoots:" in src
    assert "/api/workspace/roots" in src


# ---- D2/D3: one shared attribution module ---------------------------------

def test_shared_attribution_module():
    src = _read_web(_ATTRIB)
    assert "export function formatAuthorLabel" in src
    assert "export function authorAccent" in src
    # the interop-wedge: MCP-host writes render by name, not collapsed to YARNNN
    assert "via MCP" in src
    assert "yarnnn:mcp:" in src


def test_no_duplicate_author_helpers_in_files_surface():
    """Every Files-surface component routes author classification/labeling
    through the ONE shared module (lib/workspace/attribution.ts). No LOCAL
    author-formatter functions. Pattern broadened (and RevisionHistoryPanel
    added) after the follow-up found `authorLayer`/`layerLabel` there still
    collapsed yarnnn:mcp:* → "yarnnn" — the gate's original narrow regex missed
    it. (RecentlyAuthored.tsx is another lane's file — excluded.)"""
    files = [
        _PAGE,
        _CONTENT,
        "components/workspace/RecentsView.tsx",
        "components/workspace/NodeDetailsPanel.tsx",
        "components/workspace/WorkspaceTree.tsx",
        "components/workspace/RevisionHistoryPanel.tsx",
    ]
    # Catch any locally-defined author classifier/labeler, by name shape.
    pat = re.compile(
        r"function\s+(formatAuthorLabel|formatAuthorLabelOrSystem|authorAccent|"
        r"formatHeadAuthor|authorLayer|layerLabel|authorClass)\b"
    )
    for f in files:
        src = _read_web(f)
        m = pat.search(src)
        assert m is None, f"{f} still defines a local author helper: {m.group(0) if m else ''}"


def test_revision_panel_uses_shared_attribution():
    """RevisionHistoryPanel labels rows via the shared module so an MCP write
    reads 'Claude (via MCP)' — matching the header (was 'yarnnn')."""
    src = _read_web("components/workspace/RevisionHistoryPanel.tsx")
    assert "from '@/lib/workspace/attribution'" in src
    assert "formatAuthorLabelOrSystem" in src
    assert "authorClass" in src


def test_folder_listing_shows_attribution():
    """DirectoryView showed NO author before ADR-388 (D3 gap)."""
    src = _read_web(_CONTENT)
    assert "authorAccent" in src
    assert "formatAuthorLabel" in src


# ---- D4: surface-wide view mode -------------------------------------------

def test_view_mode_hook_and_consumers():
    hook = _read_web("lib/workspace/useFilesViewMode.ts")
    assert "useFilesViewMode" in hook
    assert "yarnnn:files:view-mode" in hook
    page = _read_web(_PAGE)
    assert "useFilesViewMode" in page
    content = _read_web(_CONTENT)
    assert "viewMode" in content  # DirectoryView honors it


# ---- D5: Get-Info modal ----------------------------------------------------

def test_get_info_modal():
    modal = _read_web("components/workspace/GetInfoModal.tsx")
    assert "NodeDetailsPanel" in modal  # reuses the revision-chain panel
    page = _read_web(_PAGE)
    assert "GetInfoModal" in page
    # the old inline collapsible details panel is no longer mounted on the page
    assert "NodeDetailsPanel" not in page  # only the modal mounts it now


def test_right_click_get_info_wired():
    # tree already supported onGetInfo; the folder listing gains onContextMenu
    content = _read_web(_CONTENT)
    assert "onGetInfo" in content
    assert "onContextMenu" in content
    page = _read_web(_PAGE)
    assert "handleGetInfo" in page


# ---- follow-up (2026-06-30): single revision home, honest 404, no tree dots --

def test_revision_chain_single_home():
    """The revision chain was double-mounted (FileView inline + the modal).
    It now lives ONLY in the Get-Info modal (via NodeDetailsPanel)."""
    content = _read_web(_CONTENT)
    # FileView no longer renders RevisionHistoryPanel inline
    assert "RevisionHistoryPanel" not in content
    # the modal's panel still mounts it (single home) + the attribution synthesis
    nd = _read_web("components/workspace/NodeDetailsPanel.tsx")
    assert "RevisionHistoryPanel" in nd
    assert "FileAttributionSummary" in nd


def test_missing_file_honest_empty_state():
    """A 404 from getFile renders an honest 'this file isn't here' empty state,
    not a raw red 'API Error' — distinguished by APIError.status === 404."""
    content = _read_web(_CONTENT)
    assert "APIError" in content
    assert "status === 404" in content
    assert "notFound" in content


def test_tree_has_no_author_dots():
    """Author dots removed from the tree (unlabeled color is a riddle). The
    accent/label helpers are no longer imported there; attribution lives in the
    file header + Get-Info modal."""
    tree = _read_web("components/workspace/WorkspaceTree.tsx")
    assert "authorAccent" not in tree
    assert "formatAuthorLabel" not in tree
