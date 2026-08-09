#!/usr/bin/env python3
"""ADR-509 — the insert route follows the medium.

`/` is FLOW's gesture; `paged` gets a native mouse menu with two mounts. The
checks below defend the three things that can silently break:

  1. the FLOW gate actually exists at both slash entrances (not just one);
  2. `paged` has a mouse route to EVERY registry kind — the coverage claim,
     asserted against the live registry rather than a hard-coded list, so a
     new kind cannot quietly become unreachable;
  3. the doors share ONE rendered list and ONE write path (no second insert
     mechanism, the thing ADR-506 D1's one-sender invariant existed to prevent).

Run:  cd api && python3 test_adr509_insert_route.py     (NOT pytest)
"""
import re
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
PROJ = (WEB / "components/workspace/viewers/projection.ts").read_text()
SURFACE = (WEB / "components/studio/StudioSurface.tsx").read_text()
MENU = (WEB / "components/studio/StudioBlockInsertMenu.tsx").read_text()
BLOCKMENU = (WEB / "components/studio/StudioBlockMenu.tsx").read_text()
PALETTE = (WEB / "components/studio/StudioSlashPalette.tsx").read_text()
ROWS = (WEB / "components/studio/blockRows.tsx").read_text()
TOOLBAR = (WEB / "components/studio/StudioToolbar.tsx").read_text()

passed = True
count = 0


def _check(label: str, ok: bool) -> None:
    global passed, count
    count += 1
    if not ok:
        passed = False
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")


def main() -> int:
    print("-- D1: the slash is FLOW's, at BOTH entrances --")
    # The typed gesture. Located by the '/' keydown, then asserted to carry the
    # gate — pinning the gate alone would pass if it drifted to another handler.
    typed = re.search(
        r"if \(e\.key !== '/' \|\| !editHost\(\)\) return;[\s\S]{0,2600}?openSlashAtCaret\(caret\)",
        PROJ,
    )
    _check("the '/' keydown handler is findable", bool(typed))
    if typed:
        _check(
            "the typed '/' is gated on FLOW_MODE",
            "if (!FLOW_MODE) return;" in typed.group(0),
        )
    door = re.search(r"function slashFromToolbar\(\)[\s\S]{0,2000}?\n  \}", PROJ)
    _check("slashFromToolbar is findable", bool(door))
    if door:
        _check(
            "the toolbar door is gated on FLOW_MODE too",
            "if (!FLOW_MODE) return;" in door.group(0),
        )
        # The deleted paged branch must not come back as a latent second route.
        _check(
            "the door's paged anchor ladder is DELETED (no enter()-the-last-block)",
            "blocks[blocks.length - 1]" not in door.group(0),
        )
    _check(
        "still exactly ONE sender of yarnnn-slash-open (ADR-506 D1 survives)",
        PROJ.count("type: 'yarnnn-slash-open'") == 1,
    )

    print("\n-- D2: paged has a mouse route, with TWO mounts --")
    _check("the native insert menu exists", (WEB / "components/studio/StudioBlockInsertMenu.tsx").exists())
    _check(
        "mount 1 — the toolbar Insert forks by medium in ONE place",
        "const onInsertPressed" in SURFACE
        and "if (resolvedMode === 'flow') { invokeSlash(); return; }" in SURFACE
        and "openInsertMenu(at.x, at.y)" in SURFACE,
    )
    _check(
        "mount 2 — the right-click row opens the SAME menu at the click point",
        "onInsert={() => openInsertMenu(ctxMenu.x, ctxMenu.y)}" in SURFACE,
    )
    # Pin the RENDER, not just the condition. A first cut of this check asserted
    # only that the string `onInsert && isPaged` appeared — and a falsifier that
    # short-circuited the branch to `{false && onInsert && isPaged && (` PASSED,
    # because the substring survived. Locate the JSX block and assert the Row is
    # actually inside it, with nothing disabling the branch.
    row = re.search(
        r"\{([^}]*?)onInsert && isPaged && \([\s\S]{0,400}?Insert block…[\s\S]{0,120}?</Row>",
        BLOCKMENU,
    )
    _check("the located Insert row is findable and renders a Row", bool(row))
    if row:
        _check(
            "the located row's branch is not short-circuited (no `false &&`)",
            "false" not in row.group(1),
        )
        _check(
            "the located row is gated on BOTH the callback and paged",
            "onInsert" in row.group(0) and "isPaged" in row.group(0),
        )
    _check(
        "a bare-canvas right-click on paged is no longer an empty menu",
        "const hasInsert = !!onInsert && isPaged;" in BLOCKMENU
        and "!hasBlock && !hasClipboard && !hasInsert" in BLOCKMENU,
    )

    print("\n-- D2: the target is resolved most-specific-first, and NAMED --")
    target = re.search(r"const resolveInsertTarget = useCallback\(\(\) => \{[\s\S]{0,1600}?\}, \[", SURFACE)
    _check("resolveInsertTarget is findable", bool(target))
    if target:
        body = target.group(0)
        # Order matters: block before slot before page-append. A slot-first
        # ladder would ignore a selected block and land in the wrong place.
        bi, si = body.find("sel?.blockId"), body.find("sel?.slot")
        _check("block anchor is resolved BEFORE slot", bi != -1 and si != -1 and bi < si)
        _check(
            "there is always a fallback (append to the current page — never 'nowhere')",
            "slot: null, blockId: null" in body,
        )
        _check(
            "the page noun follows the type (deck says slide, web says section)",
            "template === 'deck' ? 'slide' : 'section'" in body,
        )
    _check(
        "the menu STATES the destination",
        "Insert into {targetLabel}" in MENU,
    )

    print("\n-- D3: one list, three doors (no second mechanism) --")
    _check("the shared row module exists", (WEB / "components/studio/blockRows.tsx").exists())
    _check("the flow palette renders the shared row", "BlockRow" in PALETTE)
    _check("the paged menu renders the shared row", "BlockRow" in MENU)
    _check(
        "the palette no longer carries a private icon map (it moved, not copied)",
        "const SLASH_ICONS" not in PALETTE and "BLOCK_ICONS" in ROWS,
    )
    # The ADR-506 D3 refusal that must SURVIVE: no per-type subsetting anywhere.
    props = re.search(r"interface StudioSlashPaletteProps \{[\s\S]*?\n\}", PALETTE)
    _check("the palette's props block is findable", bool(props))
    if props:
        _check(
            "the palette still takes no `mode` prop (the ADR-482 D3 race stays closed)",
            "mode" not in props.group(0),
        )
    _check(
        "the paged menu does not filter kinds by type",
        "vocabulary?.blocks ?? []" in MENU and "applies" not in MENU,
    )

    print("\n-- the COVERAGE claim, against the LIVE registry --")
    # The reason this ADR exists: 10 of 13 kinds had no mouse route on paged.
    # Assert against the served registry, so a kind added later cannot silently
    # become unreachable — a hard-coded list would go stale and pass.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from services.studio import STUDIO_BLOCKS  # noqa: E402

    kinds = set(STUDIO_BLOCKS)
    _check(f"the registry ships kinds ({len(kinds)}) and the menu lists them ALL", len(kinds) >= 13)
    # The menu renders `vocabulary.blocks` unfiltered, and the vocabulary route
    # serves STUDIO_BLOCKS — so listing is proven by the absence of a filter
    # plus the served source. Pin both halves.
    _check(
        "the paged menu's list IS the served vocabulary (unfiltered)",
        re.search(r"const items: BlockRowItem\[\] = vocabulary\?\.blocks \?\? \[\];", MENU) is not None,
    )
    _check(
        # ADR-539 D2 re-cut: picker-backed is derived from the row's `cites`.
        "picker-backed + chart kinds route the SAME way from both doors",
        "kindCites(kind)" in SURFACE and "onInsertMenuPick" in SURFACE,
    )
    # The landing ops are the EXISTING ones — never a new write path (ADR-443 D2).
    pick = re.search(r"const onInsertMenuPick = useCallback\([\s\S]{0,2200}?\n  \);", SURFACE)
    _check("onInsertMenuPick is findable", bool(pick))
    if pick:
        _check(
            # ADR-511 Phase 2: the slot-name branch dissolved — insertBlock
            # handles every anchor (a container anchor appends INTO it).
            "it lands through insertBlock — no new op",
            "insertBlock(" in pick.group(0) and "insertBlockInSlot(" not in pick.group(0),
        )
        _check(
            "every landing goes through applyOp (the one attributed door)",
            pick.group(0).count("applyOp(") >= 1,
        )

    print("\n-- the toolbar tells the truth per medium --")
    _check(
        "the Insert tooltip stops promising a caret palette on paged",
        "isPaged" in TOOLBAR and "into the selected slot, or this page" in TOOLBAR,
    )
    _check(
        "the button hands its own rect up (so the paged menu drops from it)",
        "getBoundingClientRect()" in TOOLBAR and "onInsert({ x:" in TOOLBAR,
    )

    print()
    print(f"{'PASS' if passed else 'FAIL'}: {count} checks")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
