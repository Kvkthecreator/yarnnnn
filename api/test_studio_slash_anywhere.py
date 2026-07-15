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


def run() -> bool:
    proj = (WEB / "components/workspace/viewers/projection.ts").read_text()
    palette = (WEB / "components/studio/StudioSlashPalette.tsx").read_text()
    surface = (WEB / "components/studio/StudioSurface.tsx").read_text()
    canvas = (WEB / "components/studio/StudioCanvas.tsx").read_text()

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
    m = re.search(r"e\.key !== '/'[\s\S]{0,1200}?yarnnn-slash-open", proj)
    _check("the '/' handler still reaches the slash-open message", bool(m))
    if m:
        body = m.group(0)
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
    _check(
        "Esc still dismisses (intercepted in the runtime, which has the keyboard)",
        re.search(r"if \(slashStart < 0\) return;[\s\S]{0,200}?'Escape'[\s\S]{0,120}?closeSlash", proj)
        is not None,
    )
    _check(
        "a filter with no match self-dismisses (typing a URL must not strand a menu)",
        re.search(r"items\.length === 0[\s\S]{0,200}?onClose\(\)", palette) is not None,
    )

    # ── 3. the rows are Notion-shaped ───────────────────────────────────────
    print("\n-- the rows --")
    _check("the palette renders an icon per row", "Icon" in palette)
    _check(
        "the icon is resolved from the block KIND (the kernel ships no icon field)",
        "SLASH_ICONS" in palette,
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
    nav = re.search(r"if \(slashStart < 0\) return;[\s\S]{0,700}?yarnnn-slash-enter", proj)
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
