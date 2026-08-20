"""
The Files surface is TWO PANES with TWO GRAMMARS — the navigator/browser gate.

Run directly: `python3 test_files_selection_model.py` from `api/`.
(Script-style, like test_adr452_studio_landing.py. Running it under pytest
collects nothing and reports a silent green — check how a gate runs before
trusting its colour.)

WHAT THIS DEFENDS, and why it is load-bearing rather than cosmetic.

TWO defects, one after the other, in the same day.

  FIRST: ONE piece of state (`selectedPath`) meant both "the highlighted item"
  and "the document the centre pane renders", so naming a file rendered its
  whole body. A click that always goes somewhere is not a selection, and with
  no selection there is no multi-select, no shift-range, no bulk verb and no
  drag-a-group — the entire vocabulary of file operations was unreachable.

  SECOND (this gate's recut): the fix applied ONE grammar to BOTH panes. They
  are not two renderers of the same thing. The LEFT TREE is a NAVIGATOR — a
  folder hierarchy you move through, and in Explorer and Finder alike it shows
  FOLDERS ONLY, which is why "does clicking a file there open it?" never
  arises. The CENTRE PANE is the FILE BROWSER. Applying the browser's selection
  model to the navigator put a floating Move…/Open/Clear chip beside Properties
  when the operator clicked a FILE IN THE TREE (operator-observed on
  production).

The claims:
  1. TWO STATES exist and are distinct — `viewPath` (shown) vs `selection`
     (picked) — and the fused `selectedPath` / `alsoSelected` / `selectionSet`
     shape is DELETED, not kept beside them.
  2. A plain single click on a centre-pane FILE reaches a select-only branch
     that moves NOTHING the centre pane renders.
  3. ⌘/Ctrl-click TOGGLES membership.
  4. Shift-click takes a RANGE, over the listing's own published visual order.
  5. Double-click OPENS, through the one funnel.
  6. Coarse pointer (touch) opens on a SINGLE tap — capability, never width.
  7. Escape clears at ANY selection size, and a background click clears too.
  8. Enter opens the selection (double-click's keyboard peer).
  9. The verbs act on the SELECTION — the set-Move and drag-a-group both take it.
 10. THE TREE IS A FOLDER NAVIGATOR: it renders no file nodes at any depth, it
     neither reads nor writes the selection, and one click means navigate.
 11. THE SELECTION TOOLBAR IS GONE, and the verbs it carried live in the shared
     right-click menu — including Download, which carries the file's OWN name.

Assertions run over COMMENT-STRIPPED source. A gate that reads its own
explanatory prose is testing its documentation, not its code.
"""

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_WEB = os.path.normpath(os.path.join(_HERE, "..", "web"))


def _read(rel: str) -> str:
    p = os.path.join(_WEB, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def _strip_comments(src: str) -> str:
    """Drop // line-comments and /* */ blocks.

    A JSX comment `{/* … */}` loses its body here and leaves a bare `{}`, which
    is inert for these assertions. Deliberately NOT a `\\{\\s*/\\*.*?\\*/\\s*\\}`
    pattern: `\\{` matches ANY brace, so with DOTALL that swallows everything
    from the first `interface X {` to the next `*/}` — 300 lines of real code,
    silently, and the gate then fails against correct source (observed while
    writing this file). Strip the comment, never the braces around it.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    passed = True

    page_raw = _read("app/(authenticated)/files/page.tsx")
    tree_raw = _read("components/workspace/WorkspaceTree.tsx")
    viewer_raw = _read("components/workspace/ContentViewer.tsx")
    types_raw = _read("types/index.ts")

    if not page_raw or not tree_raw or not viewer_raw:
        return _check("the three Files-surface modules are readable", False) or 1

    page = _strip_comments(page_raw)
    tree = _strip_comments(tree_raw)
    viewer = _strip_comments(viewer_raw)
    types = _strip_comments(types_raw)

    # ── 1. TWO STATES, and the fused one DELETED ──────────────────────────
    #
    # The inversion, stated exactly: `selectedPath` meant BOTH "highlighted" and
    # "what the centre pane renders". Splitting it is the fix, and keeping the
    # old shape beside the new one would be the dual-implementation failure that
    # makes the split meaningless. So both halves are asserted: the new states
    # exist, AND the old names are gone from the code.
    passed &= _check(
        "1a. the two states exist and are separately declared",
        re.search(r"const \[viewPath, setViewPath\] = useState<string \| null>\(null\)", page)
        is not None
        and re.search(r"const \[selection, setSelection\] = useState<string\[\]>\(\[\]\)", page)
        is not None,
    )
    # The bolted-on primary+extras shape (a SET carried BESIDE a primary) is
    # gone — not renamed, not kept as an alias. Checked on STRIPPED source so
    # the historical explanation in the comments does not satisfy the gate.
    dead = [n for n in ("selectedPath", "alsoSelected", "selectionSet", "clearSet")
            if n in page or n in tree or n in viewer]
    passed &= _check(
        "1b. the fused selectedPath / primary+extras shape is DELETED",
        not dead,
        f"still present: {dead}" if dead else "",
    )
    # What the pane renders comes from `viewPath`, and Properties is scoped
    # separately again — a selection must not decide what is rendered.
    passed &= _check(
        "1c. the centre pane renders from viewPath, not from the selection",
        re.search(r"const viewNode = viewPath\s*\?", page) is not None
        and "node={viewNode}" in page,
    )

    # ── 2. a plain single click SELECTS and renders nothing new ───────────
    #
    # The claim is behavioural: on the select branch, `setViewPath` must not be
    # reached. Asserted structurally — isolate the click callback's body, and
    # require that the select-only path is a bare selection setter while the
    # OPEN path is the funnel. If a future edit puts `setViewPath` back into the
    # select branch, the select-only setter would have to carry it, and this
    # trips.
    wrapper = re.search(
        r"const handleFileClick = useCallback\((.*?)\n  \);", page, re.DOTALL
    )
    body = wrapper.group(1) if wrapper else ""
    passed &= _check(
        "2a. one click grammar exists (handleFileClick)",
        bool(wrapper),
    )
    passed &= _check(
        "2b. the plain-click branch selects and does NOT move what is shown",
        "selectOne(node.path)" in body
        and "setViewPath" not in body
        and "activateBodyRef" not in body,
        f"setViewPath in body={'setViewPath' in body} activateBodyRef in body={'activateBodyRef' in body}",
    )
    # And `selectOne` itself is a pure selection move — set + anchor, nothing else.
    sel_one = re.search(
        r"const selectOne = useCallback\(\(path: string\) => \{(.*?)\}, \[\]\);",
        page,
        re.DOTALL,
    )
    passed &= _check(
        "2c. selectOne only touches the selection (no view move, no drill-in)",
        sel_one is not None
        and "setSelection([path])" in sel_one.group(1)
        and "setViewPath" not in sel_one.group(1)
        and "activateBodyRef" not in sel_one.group(1),
    )

    # ── 3. ⌘/Ctrl-click TOGGLES ───────────────────────────────────────────
    #
    # Toggle, not add: a modifier-click on an already-picked row must remove it,
    # or a member can enter a set they cannot narrow.
    toggle = re.search(
        r"const toggleSelected = useCallback\(\(path: string\) => \{(.*?)\n  \}, ",
        page,
        re.DOTALL,
    )
    tbody = toggle.group(1) if toggle else ""
    passed &= _check(
        "3. ⌘/Ctrl-click toggles membership (both directions)",
        toggle is not None
        and "selection.includes(path)" in tbody
        and "filter((p) => p !== path)" in tbody
        and "[...selection, path]" in tbody
        and re.search(r"if \(e\?\.metaKey \|\| e\?\.ctrlKey\) \{\s*toggleSelected\(node\.path\);", body)
        is not None,
    )

    # ── 4. shift-click takes a RANGE over the VISUAL order ────────────────
    #
    # The range must be over what the member SEES — the listing's sorted,
    # folders-first sequence — or the highlight and the rectangle the gesture
    # drew disagree. So the listing PUBLISHES its order and the range reads it;
    # a range computed from tree order would satisfy "a range exists" and still
    # be wrong on screen.
    rng = re.search(
        r"const selectRange = useCallback\(\(path: string\) => \{(.*?)\n  \}, ",
        page,
        re.DOTALL,
    )
    rbody = rng.group(1) if rng else ""
    passed &= _check(
        "4a. shift-click takes a range from the anchor",
        rng is not None
        and "orderRef.current" in rbody
        and "slice(lo, hi + 1)" in rbody
        and re.search(r"if \(e\?\.shiftKey\) \{\s*selectRange\(node\.path\);", body) is not None,
    )
    passed &= _check(
        "4b. the range is over the LISTING's published visual order",
        "onPublishOrder?.(children.map((c) => c.path))" in viewer
        and "onPublishOrder={publishOrder}" in page,
    )
    # The modifier must reach the surface from BOTH of the listing's view
    # modes — the icon grid and the details list — or the range works in one and
    # silently not the other. The listing hands the RAW mouse event straight
    # through (it is structurally a FileClickIntent), so the assertion counts
    # the forwarding call sites: two, one per view mode.
    #
    # RE-ANCHORED with the two-pane recut. This used to read
    # `"shiftKey: e.shiftKey" in tree` — the TREE's hand-built intent object.
    # The tree forwards no modifiers now, because it has no selection to modify
    # (claim 10), so that assertion would gate a behaviour the system
    # deliberately withdrew. The claim it was really making — "the modifier
    # reaches the grammar from every renderer that can select" — is unchanged,
    # and the renderers that can select are the listing's two.
    forwards = len(re.findall(r"onClick=\{\(e\) => onNavigate\(child, e\)\}", viewer))
    passed &= _check(
        "4c. shiftKey is declared on the intent, and BOTH listing view modes forward the event",
        "shiftKey?: boolean;" in types and forwards >= 2,
        f"forwarding sites in the listing={forwards} (icon grid + details list)",
    )

    # ── 5. double-click OPENS, through the ONE funnel ─────────────────────
    passed &= _check(
        "5. double-click opens via the funnel",
        re.search(r"const isDoubleClick = \(e\?\.detail \?\? 0\) >= 2;", body) is not None
        and re.search(r"if \(coarse \|\| isDoubleClick[^)]*\) \{\s*openPath\(node\.path\);", body)
        is not None,
    )

    # ── 6. coarse pointer opens on a SINGLE tap — capability, not width ───
    #
    # Double-tap is not a touch idiom. And the branch must read the pointer
    # CAPABILITY: a width branch hands a mouse user the touch grammar the moment
    # they narrow the window.
    passed &= _check(
        "6. coarse pointer opens on a single tap (capability, never width)",
        "useCoarsePointer()" in page
        and re.search(r"if \(coarse \|\|", body) is not None
        and "isMobile" not in body
        and "useViewport" not in body,
    )

    # ── 7. the way OUT — Escape at ANY size, and a background click ───────
    #
    # ADR-519 shipped an inescapable multi-selection once. Withdrawal is part of
    # the feature. Two exits, because a member reaching for the mouse is not
    # served by a key: Escape, and a click on the listing's empty ground.
    # FALSIFIER NOTE (2026-08-20): the first cut of this check anchored on
    # `useEffect(() => { if (selection.length === 0) return; … }, [selection.length,
    # clearSelection]);` with DOTALL — and did NOT catch a `< 2` guard, because
    # the ENTER effect above it opens with the identical line, so `.*?` simply
    # spanned from Enter's guard to Escape's deps and matched anyway. Anchor on
    # the Escape effect from its OWN body backwards instead: find the handler,
    # then read the guard that immediately precedes it.
    esc = re.search(
        r"if \(selection\.length ([^)]*?)\) return;\s*const onKey = \(e: KeyboardEvent\) => \{\s*"
        r"if \(e\.key === 'Escape'\) (\w+)\(\);",
        page,
    )
    passed &= _check(
        "7a. Escape clears at any selection size (armed from size 1, not 2)",
        esc is not None and esc.group(1).strip() == "=== 0" and esc.group(2) == "clearSelection",
        f"guard={esc.group(1)!r} handler={esc.group(2)!r}" if esc else "Escape effect not found",
    )
    passed &= _check(
        "7b. a click on the listing's empty ground clears the selection",
        "const onGroundClick" in viewer
        and "onClearSelection?.()" in viewer
        and viewer.count("onClick={onGroundClick}") >= 2,
        "both view modes (icon grid + details list) must offer the ground exit",
    )
    passed &= _check(
        "7c. clearSelection drops the anchor too (no stale range origin)",
        re.search(
            r"const clearSelection = useCallback\(\(\) => \{ setSelection\(\[\]\); setAnchorPath\(null\); \}",
            page,
        )
        is not None,
    )

    # ── 8. Enter opens the selection ──────────────────────────────────────
    #
    # Double-click has no keyboard equivalent; this is the a11y answer, and it
    # must be scoped off while the member is typing.
    ent = re.search(r"if \(e\.key !== 'Enter'(.*?)\n    \};", page, re.DOTALL)
    ebody = ent.group(1) if ent else ""
    passed &= _check(
        "8. Enter opens the selection, and is ignored while typing",
        ent is not None
        and "openPathRef.current(" in ebody
        and "isContentEditable" in ebody
        and "INPUT|TEXTAREA|SELECT" in ebody,
    )

    # ── 9. THE VERBS ACT ON THE SELECTION ─────────────────────────────────
    #
    # This is why selection is worth having at all. Two verbs must take the set:
    # the deliberate Move (the modal) and the direct one (drag). A drag that
    # moved only the row under the cursor while nine were highlighted would make
    # the selection read as decorative.
    # FALSIFIER NOTE (2026-08-20): a plain `"const paths = selection;" in page`
    # did NOT catch narrowing the modal's Move to a single file, because the
    # DRAG path declares the same line and one surviving occurrence satisfied a
    # substring test. Both call sites must take the whole selection, so COUNT
    # them — and the count is a floor, not a ceiling, so a third set-taking verb
    # does not read as a violation.
    set_takers = len(re.findall(r"const paths = selection;", page))
    passed &= _check(
        "9a. every set-taking Move acts on the WHOLE selection",
        set_takers >= 2 and page.count("organizeVerbs.commitMoveMany(paths, destFolder)") >= 2,
        f"sites taking the whole selection={set_takers} (the modal Move and the drag-a-group)",
    )
    passed &= _check(
        "9b. dragging a member of the selection drags the GROUP",
        re.search(
            r"if \(selection\.length > 1 && selection\.includes\(fromPath\)\) \{.*?commitMoveMany\(",
            page,
            re.DOTALL,
        )
        is not None,
    )
    # The listing must RENDER the set, or a selection the member cannot see is
    # not a selection. Both view modes.
    passed &= _check(
        "9c. the listing rings every member of the selection (both view modes)",
        viewer.count("selected={selectedSet.has(child.path)}") >= 2,
    )
    # ── 10. THE TREE IS A FOLDER NAVIGATOR ────────────────────────────────
    #
    # The second defect, stated as assertions. Each half is checked
    # independently because either one alone re-opens the door: a tree that
    # still rendered files but took no selection would still have to answer
    # "what does clicking this file do", and a tree that rendered folders only
    # but still carried the selection would still raise the chip.

    # 10a. NO FILE NODES, at any depth. Asserted on the FILTER — the one
    # construct that makes it true — rather than on the absence of a string,
    # because "the file branch is gone" is not something an absence can prove
    # (the branch could return under another name). The filter is recursive:
    # a depth-1-only prune would leave every nested file rendering.
    fo = re.search(
        r"function foldersOnly\(nodes: WorkspaceTreeNode\[\] \| undefined\): WorkspaceTreeNode\[\] \{(.*?)\n\}",
        tree,
        re.DOTALL,
    )
    fobody = fo.group(1) if fo else ""
    passed &= _check(
        "10a. the tree renders FOLDERS ONLY, recursively",
        fo is not None
        and "n.type === 'folder'" in fobody
        and "children: foldersOnly(n.children)" in fobody
        and "foldersOnly(nodes)" in tree,
    )
    # ...and the filter is applied to the RENDER, not handed in by the caller —
    # `treeNodes` also feeds the Move picker and resolves what the centre pane
    # shows, and pruning at the source would starve both.
    passed &= _check(
        "10b. the filter is applied at render, and the page still hands the WHOLE tree",
        "nodes={treeNodes}" in page and "moveRoots: treeNodes" in page,
    )
    # 10c. The tree neither READS nor WRITES the selection. Its props are the
    # statement: no `selection` prop in, and the page mounts it without one.
    tree_props = re.search(r"interface WorkspaceTreeProps \{(.*?)\n\}", tree, re.DOTALL)
    tp = tree_props.group(1) if tree_props else ""
    tree_mount = re.search(r"<WorkspaceTree(.*?)/>", page, re.DOTALL)
    tm = tree_mount.group(1) if tree_mount else ""
    passed &= _check(
        "10c. the tree takes no selection — neither in its props nor at its mount",
        tree_props is not None
        and tree_mount is not None
        and "selection" not in tp
        and "selection" not in tm
        and "selectedSet" not in tree,
        f"props mention selection={'selection' in tp} mount={'selection' in tm}",
    )
    # 10d. ONE gesture, ONE meaning: a tree click navigates. It must not carry a
    # click INTENT at all — an intent is the vocabulary of a pane that has more
    # than one thing a click could mean.
    passed &= _check(
        "10d. a tree click navigates, and carries no click-intent",
        "onNavigate: (node: WorkspaceTreeNode) => void;" in tp
        and "FileClickIntent" not in tree
        and re.search(r"const navigateToFolder = useCallback\(\(node: TreeNode\) => \{ openPath\(node\.path\); \}", page)
        is not None
        and "onNavigate={navigateToFolder}" in page,
    )
    # 10e. And the pane-discriminating parameter is GONE from the listing's
    # grammar. A handler that has to be told which pane called it is two
    # handlers wearing one name — the shape the whole recut removes.
    passed &= _check(
        "10e. the listing's click grammar has no pane discriminator",
        "source === 'tree'" not in page and "'tree' | 'listing'" not in page,
    )

    # ── 11. THE SELECTION TOOLBAR IS GONE; the verbs live in the MENU ─────
    #
    # A selection should LOOK selected. It does not need a chip announcing
    # itself — and the chip appeared beside Properties from a TREE click, which
    # is how the operator met it. Asserted as: the strip's own controls are
    # gone from the surface, while the exits it also carried survive elsewhere
    # (7a/7b already gate those, so losing the chip cannot lose the way out).
    passed &= _check(
        "11a. the floating selection strip is DELETED",
        "Move…" not in page
        and "Clear selection (Esc)" not in page
        and "title=\"Open (Enter, or double-click)\"" not in page,
    )
    # Its Move lives in the shared menu, and it still takes the SET when the
    # right-clicked row is part of one. A menu Move that silently narrowed to
    # one file would make the selection decorative again, one address over.
    move_verb = re.search(
        r"onMove: \(t: \{ path: string; name: string \}\) => \{(.*?)\n    \},", page, re.DOTALL
    )
    mv = move_verb.group(1) if move_verb else ""
    passed &= _check(
        "11b. Move is a MENU verb and still takes the whole set",
        move_verb is not None
        and "selection.length > 1 && selection.includes(t.path)" in mv
        and "setMoveSetOpen(true)" in mv
        and "openMove(t)" in mv,
    )
    # Right-clicking OUTSIDE the selection replaces it, or the menu names one
    # file while the set-taking verb moves nine.
    passed &= _check(
        "11c. a right-click outside the selection re-scopes it to the row",
        "if (!selectedSet.has(child.path)) onSelectRow?.(child.path);" in viewer
        and "onSelectRow={selectOne}" in page,
    )
    # 11d. DOWNLOAD is a menu verb, and it CARRIES THE FILENAME. The href is a
    # signed `workspace-cas` URL and the CAS is keyed by CONTENT ADDRESS, so a
    # bare `download` saved the blob as its 64-char SHA with no extension
    # (fixed in 1069fe3). Assert the ATTRIBUTE takes the resolved name — not
    # merely that the word "download" appears.
    menu = _strip_comments(_read("components/workspace/FileContextMenu.tsx"))
    passed &= _check(
        "11d. Download is in the shared menu and carries the file's own name",
        "download={download.filename}" in menu
        and "href={download.href}" in menu
        and "downloadFor" in menu
        and "downloadFor: async" in page,
    )
    # 11e. ...and the two buttons it replaced are DELETED, not left beside it.
    # A verb reachable from two places that disagree is the dual-implementation
    # failure; `FileActions` is gone from every mount.
    body = _strip_comments(_read("components/workspace/FileBody.tsx"))
    modal = _strip_comments(_read("components/chat-surface/FileOpenModal.tsx"))
    passed &= _check(
        "11e. the preview-header FileActions buttons are DELETED from every mount",
        "FileActions" not in body
        and "FileActions" not in viewer
        and "FileActions" not in modal,
    )

    # ── 12. RECENTS IS A FILE BROWSER TOO ─────────────────────────────────
    #
    # The THIRD defect of the same day, and the one this claim exists for.
    # Recents is a grid/list of FILES in the same centre pane, gathered by
    # recency instead of by folder — the only difference, and not one the
    # member's hands can feel. It was never brought into the model: the Files
    # mount handed it `onSelectPath={openPath}`, so a SINGLE CLICK on a Recents
    # tile went straight through the one door and OPENED the file. Exactly the
    # behaviour the split had just removed from the folder listing, surviving
    # one renderer over (operator-observed on production).
    #
    # Asserted as: (a) the open funnel is not handed in as a click handler,
    # (b) the surface routes Recents through the ONE grammar function, and
    # (c) Recents' rows report the raw event rather than deciding.
    recents = _strip_comments(_read("components/workspace/RecentsView.tsx"))
    wrapper_src = _strip_comments(_read("components/workspace/RecentRevisions.tsx"))

    # 12a. THE DEFECT ITSELF, asserted where it lived. The Recents MOUNT must
    # not hand the open funnel in as a click handler under ANY prop name — the
    # mount's own props are read, so `onSelectPath={openPath}` (the shipped
    # defect) and `onNavigate={openPath}` (the same defect wearing the new name)
    # both trip it. And the `onSelectPath` prop itself is gone from the two
    # Recents modules, so the old shape cannot be re-wired.
    #
    # DELIBERATELY NOT a page-wide `"onSelectPath" not in page` ban: the name is
    # also PropertiesModal's, where a path handed back genuinely IS an open, and
    # banning the spelling rather than the wiring failed against correct source
    # while writing this (the trap this file's 9a note already names once).
    mount = re.search(r"<RecentRevisions(.*?)/>", page, re.DOTALL)
    mount_props = mount.group(1) if mount else ""
    hands_the_door = re.search(r"=\{openPath\}", mount_props) is not None
    passed &= _check(
        "12a. the Recents mount does not hand the OPEN funnel in as a click handler",
        mount is not None
        and not hands_the_door
        and "onSelectPath" not in recents
        and "onSelectPath" not in wrapper_src,
        f"mount found={mount is not None} hands openPath={hands_the_door}",
    )

    # 12b. It routes through the SAME grammar function the folder listing does.
    # A second selection model for Recents is the dual implementation this
    # surface has already been burned by twice; the adapter must reach
    # `handleFileClick` and nothing else.
    adapter = re.search(
        r"const handleRecentsClick = useCallback\(\s*\((.*?)\n  \);", page, re.DOTALL
    )
    abody = adapter.group(1) if adapter else ""
    passed &= _check(
        "12b. Recents routes through the ONE click grammar (no second model)",
        adapter is not None
        and "handleFileClick(" in abody
        and "openPath(" not in abody
        and "setViewPath" not in abody
        and "setSelection" not in abody
        and "onNavigate={handleRecentsClick}" in page,
        f"adapter found={adapter is not None}",
    )

    # 12c. Its rows REPORT the event; they decide nothing. Counted per view
    # mode — a grammar that reached the icon grid and not the details list
    # would be a modifier that works until the member hits the toggle. Two
    # sites, one per mode; a floor, not a ceiling.
    recents_forwards = len(
        re.findall(r"onClick=\{\(e\) => onNavigate\(rev\.path, e\)\}", recents)
    )
    passed &= _check(
        "12c. BOTH Recents view modes forward the raw event to the grammar",
        recents_forwards >= 2,
        f"forwarding sites in Recents={recents_forwards} (icon grid + details list)",
    )

    # 12d. Recents RENDERS the set, publishes its OWN visual order, and offers
    # the ground exit — the three things that make a highlight a selection
    # rather than decoration. Its order is RECENCY, not the listing's
    # folders-first alphabetical, so a shift-range taken here must run over
    # what Recents drew; publishing is how the two browsers stay honest about
    # which sequence is on screen.
    passed &= _check(
        "12d. Recents rings the set, publishes its own order, and clears on ground",
        recents.count("selected={selectedSet.has(rev.path)}") >= 2
        and "onPublishOrder?.(orderedPaths)" in recents
        and "const onGroundClick" in recents
        and "onClearSelection?.()" in recents
        and recents.count("onClick={onGroundClick}") >= 2
        and "onPublishOrder={publishOrder}" in page,
    )

    # 12e. And the right-click re-scope rule holds here too, or the menu names
    # one file while a set-taking verb moves nine — the same half-rule the
    # folder listing needed (11c).
    passed &= _check(
        "12e. a right-click outside the selection re-scopes it, in Recents too",
        "if (!selectedSet.has(path)) onSelectRow?.(path);" in recents
        and "onSelectRow={selectOne}" in page,
    )

    # 12f. The DEAD deep-link branch is DELETED, not left beside the grammar.
    # `linkTo` served a Home mount that ADR-435 removed, so its ternary had been
    # permanently parked in the `undefined` arm — a branch no caller can reach
    # is not a second mode, it is dead code claiming to be one. Asserted across
    # the two shared renderers AND their consumers, so re-adding it anywhere
    # re-opens the "does a click here navigate or select?" question the whole
    # recut exists to close.
    tile = _strip_comments(_read("components/workspace/FileTile.tsx"))
    listrow = _strip_comments(_read("components/workspace/FileListView.tsx"))
    lingering = [
        n for n, s in (
            ("FileTile", tile), ("FileListView", listrow),
            ("RecentsView", recents), ("RecentRevisions", wrapper_src),
        ) if "linkTo" in s
    ]
    passed &= _check(
        "12f. the unreachable deep-link branch is DELETED from the file renderers",
        not lingering,
        f"linkTo still present in: {lingering}" if lingering else "",
    )

    # ── 13. THE SELECTED GROUND IS PAINTED ONCE ───────────────────────────
    #
    # Operator-observed: "the select highlight background shouldn't be so dark,
    # closer just to image screen." The cause was not the colour value — it was
    # that a selected tile stacked THREE treatments over the same pixels: the
    # shell's fill, the PREVIEW ZONE's own fill painted on top of it, and a ring
    # over both. Two washes at /10 do not read as one wash at /10.
    #
    # So the assertion is on the CONSTRUCT, not the colour: the preview zone
    # must not branch its ground on `selected` at all. A future palette change
    # is free to move every value; re-adding a second selected fill is not.
    # Anchored on the preview zone's own className block so the shell's single
    # (correct) selected fill does not satisfy it.
    preview_zone = re.search(
        r"'flex h-24 w-full items-center justify-center overflow-hidden transition-colors',(.*?)\)\s*\}",
        tile,
        re.DOTALL,
    )
    pz = preview_zone.group(1) if preview_zone else ""
    passed &= _check(
        "13a. the tile's preview zone does not paint a second selected ground",
        preview_zone is not None
        and "TILE_PREVIEW_GROUND" in pz
        and not re.search(r"selected\s*\?", pz),
        ""
        if preview_zone
        else "preview zone not found",
    )
    # ...and exactly ONE element in the whole tile paints a ground for the
    # SELECTED state. A COUNT, because the failure mode here is ADDITION: a
    # third fill added later would satisfy any "the shell has one" check while
    # reading darker again — which is precisely how this defect shipped.
    #
    # Counted over `selected ? '…' : '…'` TERNARY TRUE-ARMS only, so the
    # drop-target's own `bg-primary/10` (a different state, correctly its own
    # treatment) is not miscounted as a second selected wash.
    def _selected_arms(src: str):
        return re.findall(r"selected\s*\n?\s*\?\s*'([^']*)'", src)

    tile_arms = _selected_arms(tile)
    tile_selected_fills = sum(len(re.findall(r"bg-primary/\d+", a)) for a in tile_arms)
    passed &= _check(
        "13b. exactly one element carries the tile's selected ground",
        tile_selected_fills == 1,
        f"selected-state bg-primary fills in the tile={tile_selected_fills} (must be 1)",
    )
    # 13c. And the two VIEW MODES agree. A selection must look like the same
    # thing whichever toggle the member last hit; the details row carrying a
    # heavier fill than the tile would make one state read as two. Compared on
    # the OPACITY STEP rather than the full class string — the row is inset and
    # borderless, so the strings legitimately differ, but the wash must not.
    def _wash_step(arms):
        for a in arms:
            m = re.search(r"(?<!hover:)bg-primary/(\d+)", a)
            if m:
                return m.group(1)
        return None

    row_arms = _selected_arms(listrow)
    tile_step, row_step = _wash_step(tile_arms), _wash_step(row_arms)
    passed &= _check(
        "13c. icon view and list view carry the SAME selected wash",
        tile_step is not None and tile_step == row_step,
        f"tile=/{tile_step} row=/{row_step}",
    )
    # 13d. ...and both keep a RING. A wash light enough to read as "gentle" is
    # not, on its own, an unmistakable selected affordance — the ring is what
    # carries selection in Finder, and lightening the fill without it would
    # trade one defect for a quieter one.
    passed &= _check(
        "13d. both views keep a ring as the selected affordance",
        any("ring-primary/" in a for a in tile_arms)
        and any("ring-primary/" in a for a in row_arms),
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
