"""
The Files centre pane is a FILE BROWSER — the selection model gate.

Run directly: `python3 test_files_selection_model.py` from `api/`.
(Script-style, like test_adr452_studio_landing.py. Running it under pytest
collects nothing and reports a silent green — check how a gate runs before
trusting its colour.)

WHAT THIS DEFENDS, and why it is load-bearing rather than cosmetic:

In every conventional OS a file browser's grid has a selection model — a single
click SELECTS and nothing else happens; the selection is a SET; the selection is
the NOUN the verbs then act on; a double click OPENS. Until 2026-08-20 this
surface had none of that: ONE piece of state (`selectedPath`) meant both "the
highlighted item" and "the document the centre pane renders", so naming a file
rendered its whole body. A click that always goes somewhere is not a selection,
and with no selection there is no multi-select, no shift-range, no bulk verb and
no drag-a-group — the entire vocabulary of file operations was unreachable
through the surface. That is the defect these assertions hold closed.

The nine claims:
  1. TWO STATES exist and are distinct — `viewPath` (shown) vs `selection`
     (picked) — and the fused `selectedPath` / `alsoSelected` / `selectionSet`
     shape is DELETED, not kept beside them.
  2. A plain single click on a FILE reaches a select-only branch that moves
     NOTHING the centre pane renders.
  3. ⌘/Ctrl-click TOGGLES membership.
  4. Shift-click takes a RANGE, over the listing's own published visual order.
  5. Double-click OPENS, through the one funnel.
  6. Coarse pointer (touch) opens on a SINGLE tap — capability, never width.
  7. Escape clears at ANY selection size, and a background click clears too.
  8. Enter opens the selection (double-click's keyboard peer).
  9. The verbs act on the SELECTION — the set-Move and drag-a-group both take it.

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
    # The modifier must reach the surface from BOTH renderers, or the range
    # works in one pane and silently not the other — the drift class the shared
    # FileClickIntent declaration exists to prevent.
    passed &= _check(
        "4c. shiftKey is declared on the intent and forwarded by the tree",
        "shiftKey?: boolean;" in types and "shiftKey: e.shiftKey" in tree,
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
    # And the tree shows the two states DIFFERENTLY — picked vs shown. One
    # treatment for both is the conflation the split removed, re-entering
    # through the renderer.
    passed &= _check(
        "9d. the tree distinguishes picked from shown",
        "const isSelected = selectedSet.has(node.path);" in tree
        and "const isShown = viewPath === node.path;" in tree
        and "isShown && !isSelected" in tree,
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
