"""ADR-458 regression gate — the Studio hover layer and the one settings home.

Static/structural checks (no DB, no LLM — FE-only; registries/posture
untouched):
  1. The hover gutter: injected chrome (body-appended, .yarnnn-gutter),
     desktop-pointer-gated (hover: hover); + posts the SAME yarnnn-slash-open
     the slash trigger uses (one palette, two entrances); ⋮⋮ selects through
     the pointer runtime's OWN selection (__yarnnnSelect) and posts the point
     payload with design:true; the gutter hides for the editing block; the
     pointer runtime ignores gutter clicks (capture-phase requirement).
  2. The design flag: canvas passes it; the surface flips the right column to
     the Design tab on it.
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

    # ── 1. The hover gutter ──────────────────────────────────────────────
    _check("gutter is injected chrome (body-appended, .yarnnn-gutter)",
           "GUTTER_SCRIPT" in proj
           and "document.body.appendChild(bar)" in proj
           and ".yarnnn-gutter" in proj)
    _check("desktop-pointer only (hover: hover media gate)",
           "matchMedia('(hover: hover)')" in proj)
    _check("+ opens the SAME palette (posts yarnnn-slash-open — one palette, two entrances)",
           proj.count("yarnnn-slash-open") >= 2)
    _check("⋮⋮ selects through the pointer's OWN selection (__yarnnnSelect)",
           "window.__yarnnnSelect = function" in proj
           and "window.__yarnnnSelect(curBlock)" in proj)
    _check("⋮⋮ posts the point payload with design:true",
           "design: true" in proj)
    _check("gutter hides for the block being edited",
           "__yarnnnEditingId" in proj
           and "blk.getAttribute('data-block-id') === editingId) { hide(); return; }" in proj)
    _check("pointer runtime ignores gutter clicks (capture-phase requirement)",
           "closest('.yarnnn-gutter')) return;" in proj)
    _check("gutter injected only on the editing canvas (opts.edit)",
           "gutter.textContent = GUTTER_SCRIPT" in proj)

    # ── 2. The design flag ───────────────────────────────────────────────
    _check("canvas passes the design flag on the point payload",
           "design: d.design === true" in canvas
           and "design?: boolean" in canvas)
    _check("surface flips to the Design tab on the flag",
           "if (p.design) setRightTab('design');" in surface)

    # ── 3. The one settings home ─────────────────────────────────────────
    _check("Design tab: the File section (Copy link/Duplicate/Rename/Move/Trash)",
           "Copy link" in design and "Rename…" in design and "Move…" in design
           and "Trash" in design and "fileVerbs" in design)
    # Rename left the shared leaf-rename modal by DESIGN (ADR-459: the artifact's
    # name is its meaning folder; the rename affordance is the CRUMB) — the verb
    # focuses the crumb instead. Move/Trash still ride the shared implementation.
    _check("the File verbs ride the SHARED implementation (useFileOrganizeVerbs)",
           "organizeVerbs.onMove({ path: artifactPath" in surface
           and "organizeVerbs.onDelete({ path: artifactPath" in surface
           and "useFileOrganizeVerbs" in surface
           and "rename: () => setRenaming(true)" in surface)
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
