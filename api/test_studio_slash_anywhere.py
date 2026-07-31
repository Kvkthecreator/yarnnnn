#!/usr/bin/env python3
"""Gate: the slash palette is the Notion gesture — anywhere, iconed, dismissable.

Three faults, one surface (operator, 2026-07-15):

  1. '/' fired ONLY in an empty context. The runtime gated on slashContextEmpty()
     and preventDefault()'d the key, so the character never landed. Notion opens
     on ANY '/', lets the character land as text, and filters as you type —
     "and/or" and URLs still type because a no-match menu dismisses itself. The
     empty-gate also stranded a literal '...' in the operator's document: the
     block was left mid-sentence while the palette opened elsewhere.

  2. The rows carried a label + a truncated description and NO icon. Notion's
     palette is scannable because the icon is the primary key — you hit the shape
     before you read the word.

  3. Click-away did not dismiss. The handler existed but listened on the PARENT
     document, while the content is a sandboxed iframe — a click on the content
     (i.e. the whole visual page) never reaches the parent's document, so the
     palette only closed by clicking the thin chrome around the frame.

The inversion: the '/' now LANDS as text and the palette filters live. Dismissal
is therefore load-bearing (every typed URL opens it), so it must close on:
Esc, click-away in EITHER document, a no-match filter, and caret exit.

Static/structural checks (no DB, no LLM — this repo has no FE test runner).
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


WEB = Path(__file__).resolve().parent.parent / "web"


def _script_body(src: str, name: str) -> str:
    """The body of a `const NAME = \\`…\\`` runtime template, brace-blind.

    The runtimes are TEMPLATE STRINGS, so "is X inside script Y" is a real
    question a substring search cannot answer — and ADR-505 D6's lesson is that
    a reader who cannot see which script holds what deletes the wrong thing.
    """
    marker = f"const {name} = `"
    i = src.find(marker)
    if i < 0:
        return ""
    i += len(marker)
    j = i
    while j < len(src):
        if src[j] == "`" and src[j - 1] != "\\":
            return src[i:j]
        j += 1
    return ""


def run() -> bool:
    proj = (WEB / "components/workspace/viewers/projection.ts").read_text()
    palette = (WEB / "components/studio/StudioSlashPalette.tsx").read_text()
    surface = (WEB / "components/studio/StudioSurface.tsx").read_text()
    canvas = (WEB / "components/studio/StudioCanvas.tsx").read_text()
    toolbar = (WEB / "components/studio/StudioToolbar.tsx").read_text()

    # ── 1. the trigger fires ANYWHERE ───────────────────────────────────────
    print("\n-- the trigger --")
    _check(
        "the empty-context gate is GONE (the whole point — '/' works mid-sentence)",
        "slashContextEmpty" not in proj,
    )
    _check(
        "'/' is NOT preventDefault'd — the character lands as text like Notion",
        "if (e.key !== '/'" not in proj or "slash-open" in proj,
    )
    # ADR-506 D1 re-cut this from a PROXIMITY PROXY to the actual path. It used
    # to regex `e.key !== '/' … yarnnn-slash-open` within a char window (1200,
    # widened to 2000 by ADR-480) — a stand-in for "the path is intact" that was
    # really a length budget, and it broke the moment the opener was EXTRACTED
    # so the typed '/' and the toolbar's Insert could share one body. The code
    # was correct; the proxy described a shape it no longer had.
    #
    # Now it asserts the two hops by name: the keydown guard delegates to the
    # opener, and the opener is what posts the message. A window still bounds
    # each hop (a hop that grows past its own function is worth a look), but a
    # refactor that keeps the path honest no longer fails for its distance.
    # Window widened by ADR-509: the keydown now carries the FLOW_MODE gate and
    # the evidence for it, so the hop is longer in prose while unchanged in path.
    hop1 = re.search(r"e\.key !== '/'[\s\S]{0,2600}?openSlashAtCaret\(caret\)", proj)
    hop2 = re.search(
        r"function openSlashAtCaret\([\s\S]{0,4000}?yarnnn-slash-open", proj
    )
    _check("the '/' keydown delegates to the shared opener", bool(hop1))
    _check("the shared opener reaches the slash-open message", bool(hop2))
    if hop1 and hop2:
        body = hop1.group(0) + hop2.group(0)
        _check(
            "the trigger does NOT preventDefault (the '/' must reach the text)",
            "e.preventDefault()" not in body,
        )
        _check(
            "the trigger does NOT exit the edit (the caret keeps typing the filter)",
            "exit(true)" not in body,
        )
    _check(
        "the runtime reports the caret offset so the '/' can be removed on pick",
        "slashStart" in proj,
    )

    # ── 1b. the toolbar's Insert is a DOOR, not a second mechanism (ADR-506) ─
    # The falsifier's shape is ADR-482 §10's lesson: assert the ACT completes,
    # not that the affordance appears. So the load-bearing check here is that
    # there is still exactly ONE sender of yarnnn-slash-open — the button has
    # to route INTO the gesture, and a second sender would mean it grew its own
    # insert path (the ADR-466 D4 / ADR-505 D4 refusal).
    print("\n-- the toolbar door (ADR-506 D1) --")
    _check(
        "the button asks the runtime to TYPE the '/' (it cannot place a caret "
        "in an opaque-origin frame itself)",
        "yarnnn-slash-invoke" in proj
        and "yarnnn-slash-invoke" in canvas
        and "slashInvoke" in surface,
    )
    _check(
        "the door routes into the ONE gesture — still a single slash-open sender",
        proj.count("type: 'yarnnn-slash-open'") == 1,
    )
    _check(
        "the door reuses the shared opener rather than posting its own message",
        bool(
            re.search(
                r"function slashFromToolbar\([\s\S]{0,2500}?openSlashAtCaret\(\)", proj
            )
        ),
    )
    # The check used to pin `onClick={onInsert}` verbatim, which broke the moment
    # the handler grew a body (D4 gave it a `setOpen(null)` — see below). A
    # literal is not the invariant; "the button is reachable in every type" is.
    # Assert it by SHAPE: the button calls onInsert, and no mode/isPaged test
    # guards it.
    # The button's JSX, sliced from its label back to the enclosing tag — the
    # region a mode guard would have to appear in to gate it.
    _ins = toolbar.rfind("<button", 0, toolbar.find('/> Insert'))
    _insert_btn = toolbar[_ins : toolbar.find('/> Insert')] if _ins > 0 else ""
    # RE-PINNED by ADR-509. The old check asserted that NO mode test touches the
    # button — true while '/' was universal and the button was purely its door.
    # ADR-509 made the slash flow's, so the button now forks by medium: on flow
    # it types the '/', on paged it opens the native menu.
    #
    # The invariant that SURVIVES, and the one that was always the point: the
    # button RENDERS AND ACTS IN EVERY TYPE. It is never withheld, never
    # disabled, never conditional on the mode having resolved — only its
    # destination differs. That is what this now asserts, plus the fork living in
    # exactly ONE place (the surface), never smeared across the toolbar.
    _check(
        "Insert renders and acts in EVERY type — the button is never withheld",
        "onInsert" in _insert_btn
        # no conditional RENDER and no disabled state around the button itself
        and "isPaged &&" not in _insert_btn
        and "disabled" not in _insert_btn,
    )
    _check(
        "the medium fork lives in the SURFACE, not the toolbar (one fork, one place)",
        "const onInsertPressed" in surface
        and "if (resolvedMode === 'flow') { invokeSlash(); return; }" in surface
        # the toolbar may READ the mode for its tooltip; it must not ROUTE on it
        and "invokeSlash()" not in toolbar,
    )
    # ADR-506 D4 — Insert sits LAST IN THE LEFT CLUSTER, not centred on the row.
    # It shipped absolutely-centred; rendered, that detached it from the controls
    # it belongs with (a lone button in dead space on a document; across a gap
    # from Re-arrange on a deck). The negative half is what a reader needs: the
    # absolute-centring wrapper must not come back.
    _check(
        "Insert is laid out in the left cluster, NOT absolutely centred (D4)",
        "absolute inset-x-0 flex justify-center" not in toolbar,
    )
    _check(
        "moving INTO the cluster took on the cluster's dismissal duty — Insert "
        "closes an open gallery (menuRef no longer counts it as 'outside')",
        # ADR-509 gave onInsert an argument (the button's own rect, so the paged
        # menu drops from the control pressed), so the argless literal went
        # stale. The DUTY is what matters and is unchanged: close, then act.
        "setOpen(null);" in toolbar and "onInsert({ x:" in toolbar,
    )
    _check(
        "the slash runtime still rides EDIT_SCRIPT (injected on opts.edit alone, "
        "with no paged/flow branch) — so the door is ungated STRUCTURALLY",
        "function slashFromToolbar" in _script_body(proj, "EDIT_SCRIPT"),
    )

    # ── 2. dismissal is load-bearing ────────────────────────────────────────
    print("\n-- dismissal (now that every URL opens it) --")
    _check(
        "the runtime tells the parent to CLOSE (caret left / filter broke)",
        "yarnnn-slash-close" in proj,
    )
    _check("the canvas routes the close message", "yarnnn-slash-close" in canvas)
    _check("the surface handles the close message", "onSlashClose" in surface)
    _check(
        "a click INSIDE the iframe closes it (the parent-document listener is blind here)",
        "yarnnn-slash-close" in proj and "mousedown" in proj,
    )
    _check(
        "the parent-document click-away survives (clicks on the chrome)",
        "mousedown" in palette,
    )
    # Esc lives in the RUNTIME, not the palette: the document owns the caret
    # while the filter is typed, so the palette never sees the keystroke.
    #
    # RE-PINNED 2026-07-31 to `slashOpen`. The guard used to be
    # `if (slashStart < 0) return;` — the ANCHOR, a DOM fact — and this gate
    # pinned that spelling. But `hideSlash()` deliberately keeps the anchor
    # through a dismiss (a pointer press may BE the pick), so after a click-away
    # the anchor was live while nothing was on screen, and these three keys were
    # stolen from the document exactly once: the member's next Enter produced no
    # newline and no chrome explained where it went. The interception now follows
    # the VISIBLE palette. Pinning the old spelling would pin the defect.
    _check(
        "Esc still dismisses (intercepted in the runtime, which has the keyboard)",
        re.search(r"if \(!slashOpen\) return;[\s\S]{0,200}?'Escape'[\s\S]{0,120}?closeSlash", proj)
        is not None,
    )
    _check(
        "the key interception follows the VISIBLE palette, never the bare anchor",
        # The anchor alone must not gate the keyboard steal again. Both the
        # keydown steal and the keyup re-filter ask `slashOpen`.
        proj.count("if (!slashOpen) return;") >= 2
        and re.search(r"if \(slashStart < 0\) return;[\s\S]{0,200}?'Escape'", proj) is None,
    )
    _check(
        "a dismiss keeps the anchor (a pointer press may BE the pick) but hides",
        re.search(r"function hideSlash\(\)[\s\S]{0,220}?slashOpen = false", proj) is not None
        and re.search(r"function hideSlash\(\)[\s\S]{0,220}?slashStart = -1", proj) is None,
    )
    _check(
        "a filter with no match self-dismisses (typing a URL must not strand a menu)",
        re.search(r"items\.length === 0[\s\S]{0,200}?onClose\(\)", palette) is not None,
    )

    # ── 3. the rows are Notion-shaped ───────────────────────────────────────
    # RE-HOMED by ADR-509: the row markup + icon map moved OUT of the palette
    # into `blockRows.tsx`, because the paged Insert menu renders the same rows.
    # These checks follow the code — the invariant (every kind wears an icon
    # resolved from its KIND, with a fallback) is unchanged and now defends BOTH
    # doors at once instead of only the slash palette.
    rows = (WEB / "components/studio/blockRows.tsx").read_text()
    print("\n-- the rows --")
    _check("the palette renders the shared row component", "BlockRow" in palette)
    _check("the shared row renders an icon per row", "Icon" in rows)
    _check(
        "the icon is resolved from the block KIND (the kernel ships no icon field)",
        "BLOCK_ICONS[item.kind]" in rows,
    )
    _check(
        "the icon map is SINGULAR — the palette no longer keeps its own copy",
        "SLASH_ICONS" not in palette,
    )
    _check(
        "every offered kind has an icon mapped (no silent blank)",
        "fallback" in palette.lower() or "??" in palette or "||" in palette,
    )
    _check(
        "the description is NOT truncated to one clipped line (Notion shows the whole hint)",
        "truncate" not in palette,
    )

    # ── 4. the pick still routes through ONE door ───────────────────────────
    print("\n-- the pick --")
    # The pick is a two-step handshake: onSlashPick asks the runtime to consume
    # the '/'+filter run (only it knows the text node), and the op lands in
    # onSlashTaken from the halves it reports back.
    pick = re.search(r"const onSlashPick = useCallback\(([\s\S]*?)\n  \);", surface)
    taken = re.search(r"const onSlashTaken = useCallback\(([\s\S]*?)\n  \);", surface)
    _check("the slash pick handler is findable", bool(pick))
    _check("the slash taken handler is findable", bool(taken))
    pick_body = pick.group(1) if pick else ""
    taken_body = taken.group(1) if taken else ""
    _check(
        "the pick asks the runtime to consume the '/'+filter run (it LANDED as text)",
        "setSlashTake" in pick_body and "filterLen" in pick_body,
    )
    _check(
        "the pick itself writes NOTHING (one gesture, one op — the take answers)",
        "applyOp" not in pick_body,
    )

    # ── the click-pick race (fixed 2026-07-15) ──────────────────────────────
    # The palette rendered and highlighted, but CLICKING a row inserted nothing
    # (the keyboard path worked — the tell). The runtime's in-frame mousedown
    # dismissal fires in the CAPTURE phase on the very press that IS the pick,
    # and it used to null the anchor on both sides before the click resolved:
    #   runtime: closeSlash() → slashStart=-1 → the take guard bails, SILENT
    #   parent:  yarnnn-slash-close → setSlash(null) → `if (!s) return` swallows
    # Both nulling paths are asserted dead here. A grep for the identifiers
    # (above) passes on the broken code — these two are what actually bite.
    _check(
        "the pick survives the close that RACES it (reads the ref, not just state)",
        "lastSlashRef" in pick_body,
    )
    press = re.search(
        r"document\.addEventListener\('mousedown', function \(\) \{([\s\S]*?)\}, true\);",
        proj,
    )
    press_body = press.group(1) if press else ""
    _check("the runtime's in-frame mousedown dismissal is findable", bool(press))
    _check(
        "a pointer press HIDES the palette without forgetting the run",
        "hideSlash()" in press_body and "closeSlash()" not in press_body,
    )
    hide = re.search(r"function hideSlash\(\) \{([\s\S]*?)\n  \}", proj)
    hide_body = hide.group(1) if hide else ""
    _check(
        "hideSlash posts the close but keeps the anchor (the take re-validates)",
        bool(hide) and "yarnnn-slash-close" in hide_body and "slashStart = -1" not in hide_body,
    )
    _check(
        "a MID-TEXT pick SPLITS (the sentence keeps its tail)",
        "splitBlockAndInsert" in taken_body,
    )
    _check("an empty block still CONVERTS in place", "convertBlock" in taken_body)
    _check(
        "an uncomputable split (citation island) still falls back to insert-after",
        "insertBlock(" in taken_body,
    )
    _check(
        "the surface still routes chart to the composer (the generative ask)",
        "seedComposer" in surface,
    )

    # ── 5. one gesture, ONE op ──────────────────────────────────────────────
    # The palette's keys are intercepted in the DOCUMENT (it owns the caret while
    # the filter is typed). The Enter-split handler is registered on the same
    # element in the same phase, so preventDefault alone would still let it run
    # and split the very block being picked into — two ops, one head, one loses.
    print("\n-- one gesture, one op --")
    # RE-PINNED 2026-07-31 alongside the Esc check above — the handler is now
    # located by the visibility guard, not the anchor guard.
    nav = re.search(r"if \(!slashOpen\) return;[\s\S]{0,700}?yarnnn-slash-enter", proj)
    _check("the palette's key handler is findable", bool(nav))
    if nav:
        _check(
            "Enter STOPS the sibling Enter-split handler (stopImmediatePropagation)",
            "stopImmediatePropagation" in nav.group(0),
        )
    _check(
        "the take exits SILENT (the parent's op is the sole writer of the result)",
        "exit(false, true)" in proj,
    )
    ops = (WEB / "components/studio/artifactOps.ts").read_text()
    _check(
        "split+insert is ONE op, not two (they would race on the same head)",
        "export function splitBlockAndInsert" in ops,
    )
    _check(
        "the split's new block is where the caret lands (what the member asked for)",
        re.search(
            r"function splitBlockAndInsert[\s\S]*?landedId: inserted\.getAttribute", ops
        )
        is not None,
    )

    # ── 6. the standing trap ────────────────────────────────────────────────
    print("\n-- the standing trap --")
    # The injected runtimes are JS-in-template-STRINGS: one literal backtick in a
    # comment terminates the template early (tsc TS1005). It has bitten 4 times.
    for m2 in re.finditer(r"const (\w+_SCRIPT) = `(.*?)\n`;", proj, re.S):
        _check(f"no literal backtick inside {m2.group(1)}", m2.group(2).count("`") == 0)

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
