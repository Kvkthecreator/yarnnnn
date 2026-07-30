"""ADR-458 regression gate — the one settings home (the hover layer is RETIRED).

Static/structural checks (no DB, no LLM — FE-only; registries/posture
untouched):
  1. The hover gutter (ADR-458 D4) is **DELETED** — ADR-481 D2 on `flow`,
     ADR-489 D4 on `paged`. What this gate now asserts is the DELETION and the
     survival of what the deletion must not have taken (the shared pointer
     primitive, deck's object chrome). The full negative surface, including the
     `⋮⋮` drag and the row band, lives in test_studio_no_gutter_and_arrows.py;
     kept here is the ADR-458-specific half: the `+`/`⋮⋮` rail and the
     `design:true` handshake that flipped the right column.
  2. The one settings home (ADR-458 D3) — UNCHANGED and still live. This is the
     decision the ADR is now remembered for.
  3. The one settings home: the Design tab's document scope carries the File
     section (Copy link · Duplicate · Rename · Move · Trash) wired to the
     SHARED useFileOrganizeVerbs implementation (no forked flows, no direct
     API calls in the tab); the surface-bar "File actions" button + the
     Studio's FileContextMenu mount are DELETED; the organize dialogs stay
     mounted (trash falls back to the landing via onAfterMutate).

Run:  cd api && python3 test_adr458_studio_hover_layer.py
Exit code is authoritative (0 = pass).
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    web = Path(__file__).resolve().parent.parent / "web"
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    design = (web / "components/studio/StudioDesignTab.tsx").read_text()

    # ── 1. The hover gutter is DELETED (ADR-481 D2 + ADR-489 D4) ────────
    _check("no gutter rail: no .yarnnn-gutter, no bar append, no yg-handle",
           ".yarnnn-gutter" not in proj
           and "document.body.appendChild(bar)" not in proj
           and "yg-handle" not in proj)
    _check("the desktop-pointer gate SURVIVES (the object grammar still needs it)",
           "matchMedia('(hover: hover)')" in proj)
    _check("`/` remains the block grain's route (the palette kept its entrance)",
           "yarnnn-slash-open" in proj)
    _check("__yarnnnSelect survives — the box + the parent's select-by-id use it",
           "window.__yarnnnSelect = function" in proj
           and "window.__yarnnnSelect(curBlock)" not in proj)
    _check("the design:true handshake is GONE end to end (runtime → canvas → surface)",
           "design: true" not in proj
           and "design?: boolean" not in canvas
           and "design: d.design === true" not in canvas
           and "if (p.design) setRightTab('design');" not in surface)
    # The DECLARATION, not the word: the header comment names the old identifier
    # on purpose (it records why the rename happened).
    _check("the script is renamed to what it holds (OBJECT_SCRIPT)",
           "const OBJECT_SCRIPT = " in proj and "const GUTTER_SCRIPT = " not in proj)
    _check("bindGesture + the bounding box survive the deletion",
           "function bindGesture(" in proj and "yarnnn-selbox" in proj)

    # ── 3. The one settings home ─────────────────────────────────────────
    # (Re-presented 2026-07-24: the verb-chip row became a FILE CARD — the name
    #  shown with its type glyph, double-click renames in place, the remaining
    #  verbs behind a ⋯ menu. Same verbs, same section, same invariance.)
    _check("Design tab: the File card (name + ⋯ menu: Copy link/Duplicate/Rename/Move/Trash)",
           "Copy link" in design and "Rename…" in design and "Move…" in design
           and "Move to Trash" in design and "fileVerbs" in design
           and "onDoubleClick={() => setNameEditing(true)}" in design)
    # Rename left the shared leaf-rename modal by DESIGN (ADR-459: the artifact's
    # name is its meaning folder). The File card renames IN PLACE through the
    # SAME commit path the crumb uses (commitRename — one derivation, one write,
    # two entry fields), with the crumb's IME guard kept in lockstep.
    _check("the File verbs ride the SHARED implementation (useFileOrganizeVerbs)",
           "organizeVerbs.onMove({ path: artifactPath" in surface
           and "organizeVerbs.onDelete({ path: artifactPath" in surface
           and "useFileOrganizeVerbs" in surface
           and "onRenameCommit={commitRename}" in surface
           and "isComposing" in design)
    _check("the Design tab makes no organize API calls of its own (no fork)",
           "api.workspace" not in design and "api.files" not in design)
    # (Re-pinned 2026-07-21: ADR-473 made the Studio surface app-generic —
    #  the empty surface-actions registration keys on app.slug, not 'studio'.)
    _check("the surface-bar 'File actions' button is deleted (crumb-only bar)",
           "'File actions'" not in surface
           and "useSurfaceActions(app.slug, [])" in surface)
    # The WORKBENCH mount stays deleted; the LANDING's recents later gained a
    # legitimate per-card context menu (one hook call, one mount). The check
    # guards against the workbench menu returning, not against the landing's.
    _check("the Studio's workbench FileContextMenu mount is deleted",
           surface.count("useFileContextMenu(") == 1
           and "recentMenu" in surface)
    _check("the organize dialogs stay mounted (trash → landing via onAfterMutate)",
           "{organizeModals}" in surface
           and "newPath === null ? null : relPath(newPath)" in surface)

    print()
    failed = [label for label, ok in _results if not ok]
    print(f"{len(_results) - len(failed)}/{len(_results)} checks passed")
    if failed:
        print("FAILED:")
        for f in failed:
            print(f"  - {f}")
    return not failed


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
