"""ADR-443 regression gate — the Studio axiomatic model (blocks + layouts).

Static/structural checks (no DB, no LLM):
  1. The block vocabulary: 8 launch kinds, valid groups, teaching markup
     carrying data-block + data-block-id (the annotation spec, D4).
  2. The layout registry: 3 layouts with skin/flow/scaffold; skeleton assembly
     (template = layout × starter blocks); STUDIO_TEMPLATES derives from it.
  3. Posture v2: block grammar + id discipline + layout-switch rule composed
     from the registries (one home, R4).
  4. The served vocabulary endpoint (R4's FE half).
  5. Block-grain pointing: the projection pointer runtime carries blockId +
     blockKind (D6) — read as text from the FE file.
  6. Grammar-not-schema: no validation gate anywhere in the studio module.
  7. ADR-444: the mechanical layer (arrangements, the write door, FE ops).
  9. ADR-447: the arrangement layer — STUDIO_ARRANGEMENTS per-type (document/
     article filled), skeletons carry data-arrange, the reflow generalizes to
     [data-arrange] (any type), the "Arrange" menu, posture teaches it.
  8. ADR-446: the direct-edit runtime — editBlockText maps to the SOURCE by
     block id (id-preserving, sanitizing, no-op-safe); the projection edit
     runtime stamps citation islands + commits on blur/idle (the revision is
     the atom, never keystroke); the surface kills the seed spam and lands
     edits through the ONE mechanical write door.

Run:  cd api && ./venv/bin/python test_adr443_studio_model.py
Exit code is authoritative (0 = pass).
"""

import inspect
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    from services.studio import (
        STUDIO_BLOCKS,
        STUDIO_LAYOUTS,
        STUDIO_TEMPLATES,
        build_skeleton,
        build_studio_posture,
    )

    # ── 1. The vocabulary (D4) ───────────────────────────────────────────
    _check("12 block kinds (the 8 launch kinds + the ADR-456 W1 four)",
           set(STUDIO_BLOCKS) == {"prose", "callout", "quote", "checklist",
                                  "table", "metrics", "chart", "figure",
                                  "divider", "toggle", "button", "gallery"})
    for kind, b in STUDIO_BLOCKS.items():
        _check(f"block '{kind}': label/group/description/markup complete",
               all(b.get(k) for k in ("label", "group", "description", "markup")))
        _check(f"block '{kind}': group valid", b.get("group") in ("content", "data", "media"))
        _check(f"block '{kind}': markup teaches the annotation spec",
               f'data-block="{kind}"' in b["markup"] and "data-block-id=" in b["markup"])
    _check("citation-backed kinds cite, never paste",
           'data-ref' in STUDIO_BLOCKS["table"]["markup"]
           and 'data-ref' in STUDIO_BLOCKS["figure"]["markup"]
           and './assets/' in STUDIO_BLOCKS["chart"]["markup"])

    # ── 2. Layouts + skeleton assembly (D5) ──────────────────────────────
    # ADR-459 D3: the kernel SEEDS the four universal shapes; it does not BOUND
    # the set. `⊇` not `==` — a bundle shipping a fifth (alpha-trader's
    # `tearsheet`) must not turn this red (ADR-222: programs ship the templates).
    _check("kernel seeds 4 layouts: document/deck/article + page (ADR-456 W3)",
           set(STUDIO_LAYOUTS) >= {"document", "deck", "article", "page"})
    for slug, lay in STUDIO_LAYOUTS.items():
        _check(f"layout '{slug}': label/description/flow/skin/scaffold complete",
               all(lay.get(k) for k in ("label", "description", "flow", "skin", "scaffold")))
        sk = build_skeleton(slug)
        _check(f"skeleton '{slug}': self-describing + annotated + script-free",
               f'data-template="{slug}"' in sk
               and 'data-block=' in sk and 'data-block-id=' in sk
               and "<script" not in sk.lower())
    _check("STUDIO_TEMPLATES derives from layouts (template = layout × starters)",
           set(STUDIO_TEMPLATES) == set(STUDIO_LAYOUTS)
           and all(STUDIO_TEMPLATES[s]["skeleton"] == build_skeleton(s) for s in STUDIO_LAYOUTS))

    # ── 3. Posture v2 (one home, R4) ─────────────────────────────────────
    posture = build_studio_posture(
        "/workspace/operation/x/deck.html", STUDIO_TEMPLATES["deck"]["skeleton"]
    )
    _check("posture: block grammar section present",
           "Blocks (the component grammar)" in posture)
    _check("posture: every kind's grammar composed in",
           all(f"- {k} — " in posture for k in STUDIO_BLOCKS))
    _check("posture: id discipline (stamp + preserve)",
           "data-block-id" in posture and "PRESERVE" in posture)
    posture_flat = " ".join(posture.split())  # wrap-tolerant matching
    _check("posture: patch-within-block discipline",
           "WITHIN block boundaries" in posture_flat)
    _check("posture: layout-switch rule (preserve blocks, swap skin, update data-template)",
           "change the layout" in posture and "data-template" in posture)
    _check("posture: current layout's flow composed from the registry",
           STUDIO_LAYOUTS["deck"]["flow"][:40] in posture)
    _check("posture: grammar not schema (never rejects)",
           "never rejects" in posture or "may stay" in posture)

    # ── 4. The served vocabulary (R4 FE half) ────────────────────────────
    import routes.studio as studio_routes
    src = inspect.getsource(studio_routes)
    _check("GET /studio/vocabulary registered", '"/studio/vocabulary"' in src)
    _check("vocabulary serves blocks + layouts",
           "STUDIO_BLOCKS" in src and "STUDIO_LAYOUTS" in src)

    # ── 5. Block-grain pointing (D6) — FE receipts as text ───────────────
    repo = Path(__file__).parent.parent
    projection = (repo / "web/components/workspace/viewers/projection.ts").read_text()
    _check("pointer runtime walks to the enclosing block",
           "closest('[data-block]')" in projection)
    _check("pointer payload carries blockId + blockKind",
           "blockId" in projection and "blockKind" in projection)
    surface = (repo / "web/components/studio/StudioSurface.tsx").read_text()
    _check("selection informs the lane in operator words (About the … block)",
           "About the ${kind} block" in surface or "askAboutSelection" in surface)
    # ADR-447: the format-switcher ("Change layout") is DELETED — morphing a
    # deck into a document was a legacy misread; composition is WITHIN the type
    # (the Arrange menu). Guard the deletion.
    _check("Change-layout format-switcher is deleted (no type morph)",
           "Change layout" not in surface and "switchLayout" not in surface)
    # ADR-453: the toolbar realigned to its grains (Insert · New ‹noun›) and
    # the file took its honest name (StudioInsertMenu → StudioToolbar).
    menu = (repo / "web/components/studio/StudioToolbar.tsx").read_text()
    # ADR-466 D4: the block palette is the located StudioSlashPalette (Media ▾
    # deleted); the toolbar keeps only the page-grain pair and still renders
    # from the served vocabulary.
    palette_src = (repo / "web/components/studio/StudioSlashPalette.tsx").read_text()
    _check("palette renders from the served vocabulary",
           "StudioVocabulary" in menu and "StudioVocabulary" in palette_src
           and "vocabulary?.blocks" in palette_src)

    # ── 6. Grammar, not schema ───────────────────────────────────────────
    import services.studio as studio_mod
    studio_src = inspect.getsource(studio_mod)
    _check("studio module stays pure program (no DB, no write_revision)",
           "write_revision" not in studio_src and ".table(" not in studio_src)
    _check("no validation gate on blocks (grammar not schema — zero raises)",
           studio_src.count("raise") == 0)

    # ── 7. ADR-444/447: the mechanical layer + arrangements ──────────────
    from services.studio import STUDIO_ARRANGEMENTS
    _check("arrangements registry keyed by layout",
           set(STUDIO_ARRANGEMENTS) == set(STUDIO_LAYOUTS))
    _check("deck ships its page arrangements",
           {"title", "content", "two-column", "quote"} <= set(STUDIO_ARRANGEMENTS["deck"]))
    _check("arrangement fragments carry data-arrange + slots + grain metadata",
           all("data-arrange" in a["fragment"] and "grain" in a and "slots" in a
               for a in STUDIO_ARRANGEMENTS["deck"].values())
           and "data-slot" in STUDIO_ARRANGEMENTS["deck"]["content"]["fragment"])
    _check("mechanical write door registered (CAS)",
           '"/studio/artifacts/write"' in src and "expected_parent_version_id" in src
           and "StaleWriteError" in src)
    _check("vocabulary serves fragments + arrangements",
           '"fragment"' in src and "STUDIO_ARRANGEMENTS" in src)
    ops = (repo / "web/components/studio/artifactOps.ts").read_text()
    _check("FE ops: insert/arrangement reflow, ids preserved",
           "insertBlock" in ops and "insertArrangement" in ops and "applyArrangement" in ops
           and "freshBlockId" in ops)
    # The insert executor moved with the palette (ADR-466 D4): located picks
    # land through the same one write door.
    _check("toolbar/palette EXECUTES (not prompt-prefill)",
           "onAddArrangement" in surface and "writeArtifact" in surface
           and "landAtLocatedPoint" in surface)
    _check("posture: concurrent-writer contract (never renumber ids)",
           "never renumber" in " ".join(posture.split()))

    # ── 8. ADR-446: the direct-edit runtime ──────────────────────────────
    # (a) The source transform — a text edit maps back to the SOURCE by block
    #     id, id-preserving, sanitizing, no-op-safe.
    _check("editBlockText: source transform present, id-preserving",
           "export function editBlockText" in ops
           and "data-block-id" in ops and "CSS.escape" in ops)
    _check("editBlockText: sanitizes member-typed inner (no executables)",
           "sanitizeInner" in ops
           and "script, iframe, object, embed" in ops
           and "javascript:" in ops)
    _check("editBlockText: no-op edit lands no revision",
           "no-op — no revision" in ops or "byte-identical" in ops)
    # (b) The projection edit runtime — citation islands mapped to SOURCE, the
    #     revision is the atom (blur/idle, never keystroke), pointer suppressed.
    _check("projection: edit runtime injected under an `edit` option",
           "edit?: boolean" in projection and "EDIT_SCRIPT" in projection)
    _check("projection: citation islands stamped with SOURCE outerHTML (D3)",
           "data-src-html" in projection and "el.outerHTML" in projection)
    _check("projection: islands are non-editable + restored on commit",
           "contenteditable" in projection and "readSourceInner" in projection)
    _check("projection: the revision is the atom (blur/idle, not keystroke)",
           "blur" in projection and "2000" in projection)
    _check("projection: pointer suppressed while a block is being edited",
           "__yarnnnEditingId" in projection)
    # (c) The surface wiring — one door (mechanical write), the seed spam killed,
    #     the explicit ask restored.
    _check("surface: edits land through the ONE mechanical door (applyOp)",
           "editBlockText" in surface and "onEdit" in surface)
    _check("surface: selection no longer auto-seeds the composer (spam killed)",
           "no longer auto-seed" in surface.lower()
           and "seedComposer(`Selected the" not in surface)
    # ADR-453: the selection's VERBS moved from the toolbar chip to the Design
    # tab (the chip stays as identity + clear); the explicit-ask survives there.
    design_tab = (repo / "web/components/studio/StudioDesignTab.tsx").read_text()
    _check("surface: explicit 'Ask about this' affordance replaces the auto-seed",
           "askAboutSelection" in surface and "onAskAboutSelection" in design_tab)
    _check("Design tab: Ask-about-this verb; toolbar Edit button stays DELETED",
           "Ask about this" in design_tab and "onToggleEdit" not in menu
           and "Double-click the block" in design_tab)
    _check("canvas: renders in edit mode + forwards edit commits",
           "editingBlockId" in surface
           and "yarnnn-edit" in (repo / "web/components/studio/StudioCanvas.tsx").read_text())
    # ADR-446 follow-on: titles/headers are editable heading blocks — every
    # layout's scaffold stamps data-block="heading" on its title so the most
    # prominent element on the artifact is reachable by the edit path.
    for slug in STUDIO_LAYOUTS:
        sk = build_skeleton(slug)
        _check(f"scaffold '{slug}': title is an editable heading block",
               'data-block="heading"' in sk)
    _check("deck arrangements annotate their titles (heading blocks)",
           all('data-block="heading"' in a["fragment"]
               for a in STUDIO_ARRANGEMENTS["deck"].values()
               if "<h1" in a["fragment"] or "<h2" in a["fragment"]))
    _check("heading is NOT a palette-inserted vocabulary kind (grammar, not schema)",
           "heading" not in STUDIO_BLOCKS)
    _check("posture teaches the heading block (editable titles)",
           'data-block="heading"' in posture)
    _check("arrangement reflow does not sweep heading blocks into a slot",
           "'heading'" in ops and "data-block')" in ops)

    # ── 9. ADR-447: the arrangement layer (composition, per-type) ────────
    from services.studio import _arrangements_grammar
    _check("every layout has page arrangements (document/article filled)",
           all(len(STUDIO_ARRANGEMENTS[t]) >= 1 for t in STUDIO_LAYOUTS)
           and len(STUDIO_ARRANGEMENTS["document"]) >= 1
           and len(STUDIO_ARRANGEMENTS["article"]) >= 1)
    _check("arrangement slots carry name + role (flow vs heading)",
           all("name" in s and "role" in s
               for arr in STUDIO_ARRANGEMENTS.values()
               for a in arr.values() for s in a["slots"]))
    for slug in STUDIO_LAYOUTS:
        sk = build_skeleton(slug)
        _check(f"scaffold '{slug}': first page carries data-arrange (arrangeable from creation)",
               'data-arrange=' in sk)
    _check("reflow targets [data-arrange] (any type), not just section.slide",
           "arrangedPageAt" in ops and "[data-arrange]" in ops)
    _check("reflow lands the arrangement slug (data-arrange), not data-container",
           "getAttribute('data-arrange')" in ops and "data-container" not in ops)
    _check("posture: Arrangements section composed from the registry",
           "Arrangements (where content goes" in posture
           and STUDIO_ARRANGEMENTS["deck"]["comparison"]["description"] in posture)
    # ADR-453: the mixed-grain 'Arrange' menu split by grain — 'New ‹noun›'
    # (add a page, toolbar gallery) + 'Re-arrange' (this page, Design tab).
    _check("toolbar: 'New ‹slide|section›' gallery (page-grain add, all types)",
           "New {pageNoun}" in menu and "arrangements" in menu
           and "onAddArrangement" in menu)
    _check("Design tab: 'Re-arrange' gallery (selection-scoped re-lay)",
           "Re-arrange" in design_tab and "onApplyArrangement" in design_tab)
    _check("new-page gallery is not deck-gated (arrangements.length gate)",
           "arrangements.length > 0" in menu)
    _check("vocabulary endpoint serves arrangements with grain + slots",
           '"arrangements"' in src and '"grain"' in src and '"slots"' in src)

    # ── 10. ADR-447 workbench restructure (nav · canvas · chat) ──────────
    nav = (repo / "web/components/studio/StudioNavigator.tsx").read_text()
    _check("per-type navigator: deck slide previews + doc/article outline",
           "buildSlidePreviews" in nav and "extractOutline" in nav
           and "layout === 'deck'" in nav)
    _check("deck slides render as VISUAL previews (scaled projected iframe)",
           "resolveArtifactHtml" in nav and "transform: `scale(${scale})`" in nav
           and 'sandbox=""' in nav)
    _check("surface mounts the navigator + selects slides from it",
           "StudioNavigator" in surface and "selectSlideFromNavigator" in surface)
    # ADR-453 D4: the right column carries Chat | Design tabs (the lane stays
    # the chat tab's body; the column itself is unchanged — right, border-l).
    _check("chat lane is the RIGHT column (border-l on the lane column)",
           "Chat | Design tabs" in surface
           and "border-l border-border" in surface)
    desktop = (repo / "web/components/shell/Desktop.tsx").read_text()
    _check("Freddie FAB suppressed on the studio surface (own-chat carve)",
           "onOwnChatSurface" in desktop and "'studio'" in desktop)

    # ── 12. ADR-447 canvas view controls + mobile (2026-07-13) ───────────
    _check("navigator selection scrolls the canvas (yarnnn-scroll-to-slide)",
           "yarnnn-scroll-to-slide" in projection
           and "scrollToSlide" in surface and "scrollIntoView" in projection)
    _check("canvas zoom is a VIEW control (yarnnn-zoom, not a file write)",
           "yarnnn-zoom" in projection and "zoom={zoom}" in surface
           and "style.zoom" in projection)
    _check("mobile: pane switching (nav/canvas/chat) + a bottom tab bar",
           "mobilePane" in surface and "md:hidden" in surface
           and "setMobilePane" in surface)
    _check("mobile: columns are responsive (hidden below md, flex at md+)",
           # The slide strip moved from a fixed md:w-56 to a RESIZABLE width
           # (drag its divider; persisted) — mobile full-width via max-md:!w-full,
           # md+ via the navWidth inline style. The chat column stays md:w-[380px].
           "md:flex" in surface and "max-md:!w-full" in surface and "md:w-[380px]" in surface)

    # ── 11. ADR-447 Phase 4: direct manipulation ─────────────────────────
    _check("double-click enters edit mode (runtime dblclick → yarnnn-edit-entered)",
           "dblclick" in projection and "yarnnn-edit-entered" in projection)
    _check("surface syncs editingBlockId on double-click entry (onEditEntered)",
           "onEditEntered" in surface and "onEditEntered" in
           (repo / "web/components/studio/StudioCanvas.tsx").read_text())
    _check("empty-slot '+ Add here' runtime injects into empty [data-slot]",
           "ADD_HERE_SCRIPT" in projection and "yarnnn-add-here" in projection
           and "data-slot" in projection and "yarnnn-add-here" in projection)
    _check("empty-slot add: does NOT decorate slots that hold a block",
           "querySelector('[data-block]')" in projection)
    _check("slot-targeted insert op (insertBlockInSlot) + surface handler",
           "insertBlockInSlot" in ops and "onAddHere" in surface)
    _check("the injected + Add here button is NOT a [data-block] (no selection confusion)",
           "not [data-block]" in projection or "not a [data-block]" in projection)

    failed = [r for r in _results if not r[1]]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed"
          + (f" — {len(failed)} FAILED" if failed else ""))
    return not failed


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
