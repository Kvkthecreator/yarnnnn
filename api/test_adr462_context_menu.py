"""ADR-462 — the block context menu, the metered badge, and the neutral page.

Source-guards over the FE. Each check pins an INVARIANT the ADR decides, not an
implementation line — the ADR-461 gate's "unframed block gets no handle" check
was pinned to a hover listener and went red when the listener was correctly
replaced, which is the failure mode this file tries not to repeat.

Run: python3 api/test_adr462_context_menu.py   (NOT pytest — see the repo's
check()-gates note; these print and return, they don't assert.)
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_results: list[tuple[str, bool]] = []

def _rendered(src: str) -> str:
    """The JSX a member can actually see: block comments and // lines stripped.

    A gate that greps raw source counts a comment EXPLAINING why a string is
    banned as an instance of the string. The label lives in the render; the
    reasoning lives in the prose. Assert on the render.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.M)
    return src



def _check(label: str, ok: bool) -> None:
    _results.append((label, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text()


def main() -> bool:
    proj = _read("web/components/workspace/viewers/projection.ts")
    menu_src = _read("web/components/studio/StudioBlockMenu.tsx")
    menu = _rendered(menu_src)
    surface = _read("web/components/studio/StudioSurface.tsx")
    canvas = _read("web/components/studio/StudioCanvas.tsx")
    ops = _read("web/components/studio/artifactOps.ts")

    print("\n── D7: right-click SELECTS, then menus ──")
    _check(
        "the runtime listens for contextmenu",
        "document.addEventListener('contextmenu'" in proj,
    )
    _check(
        "it SELECTS the block under the cursor (one gesture, not two)",
        "mark.classList.add('yarnnn-pointed');" in proj
        and "type: 'yarnnn-context-menu'," in proj,
    )
    _check(
        "injected chrome keeps its own menu (the gutter/format bar are not the page)",
        "t.closest('.yarnnn-gutter') || t.closest('.yarnnn-fmt')" in proj,
    )
    _check(
        "the runtime answers the FRAME gate (only it can see the DOM)",
        "framed: mark ? !!(mark.closest && mark.closest('.slide')) : false," in proj,
    )
    _check(
        "frame-local coords are mapped to the page by the CANVAS (the surface "
        "never learns iframe geometry)",
        "const r = iframeRef.current?.getBoundingClientRect();" in canvas
        and "zoomRef.current || 1" in canvas,
    )

    print("\n── D5: the page is the member's; the accent is the system's ──")
    _check(
        "selection is NEUTRAL, not the indigo accent",
        ".yarnnn-pointed {\n  outline: 1px solid rgba(60,58,54,0.5) !important;" in proj,
    )
    _check(
        "no saturated accent survives on the selection outline",
        "outline: 2px solid #6366f1 !important; outline-offset: 2px;" not in proj,
    )
    _check(
        "the grip matches the selection it belongs to (neutral, square)",
        "border: 1px solid rgba(60,58,54,0.55); background: #fff;" in proj,
    )
    _check(
        "the EDITING state keeps its accent (typing-into-this is a different fact)",
        "[data-block][contenteditable=\"true\"] {\n  outline: 2px solid #6366f1" in proj,
    )
    _check(
        "transient gesture chrome keeps its accent (drop-line = a prediction)",
        "background: #6366f1;\n  border-radius: 2px; pointer-events: none;" in proj,
    )

    print("\n── D4: the metered badge ──")
    _check(
        "the badge renders on metered rows",
        "meter &&" in menu and ">\n          AI\n        </span>" in menu,
    )
    _check(
        "BOTH AI rows are badged (meter passed, not decorative)",
        menu.count("meter>\n") == 2,
    )
    _check(
        "no free row carries a badge (silence is the signal)",
        "onClick={() => run(onDuplicate)} shortcut=\"⌘D\">" in menu
        and "onClick={() => run(onRearrange)}>" in menu,
    )
    _check(
        "the group header names the line in operator words",
        "Write with AI" in menu,
    )

    print("\n── D6: two AI verbs, and the seed is a sentence not a button ──")
    _check(
        "exactly TWO AI verbs — Rewrite + Check (shorter/expand were rewrites "
        "with a pre-typed adjective)",
        "Rewrite…" in menu and "Check this…" in menu
        and "Make shorter" not in menu and "Expand this" not in menu,
    )
    _check(
        "both SEED the composer and send nothing",
        "seedComposer(`Rewrite the ${kind} block" in surface
        and "seedComposer(`Check the ${kind} block" in surface,
    )
    _check(
        "neither AI row calls a send path (the member presses enter)",
        "sendMessage" not in menu and "onSend" not in menu,
    )

    print("\n── D1: a second ENTRANCE, never a second write path ──")
    _check(
        "the verbs dispatch the EXISTING handlers (no forked implementation)",
        "onDuplicate={() => handleBlockVerb('duplicate')}" in surface
        and "onDelete={() => handleBlockVerb('delete')}" in surface,
    )
    _check(
        "paste rides the ONE door (applyOp), like every other op",
        "(src) => pasteBlock(src, html, after)," in surface,
    )
    _check(
        "pasteBlock stamps FRESH ids (a paste is a new block, never a second "
        "element wearing one address)",
        "export function pasteBlock(" in ops
        and "const copy = materializeFragment(doc, fragment);" in ops,
    )
    _check(
        "Turn into / Re-arrange are DOORWAYS to their existing homes",
        "onTurnInto={menuOpenDesign}" in surface and "onRearrange={menuOpenDesign}" in surface,
    )

    print("\n── The honesty checks ──")
    _check(
        "no row claims z-order the kernel cannot do (moveBlock is FLOW order, "
        "so the label is 'Move up', never 'Bring forward')",
        "Bring forward" not in menu and "Bring to front" not in menu
        and "Move up" in menu,
    )
    _check(
        "the two rows no reference can ship are present",
        "Copy link to block" in menu and "History" in menu,
    )
    _check(
        "the block link carries the block's ADDRESS (what makes it ours)",
        "studio.block=${encodeURIComponent(id)}" in surface,
    )

    print()
    ok = all(c for _, c in _results)
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
