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


def _backtick_in_scripts(src: str) -> list:
    """Script/CSS bodies whose text contains a raw backtick.

    Each `const NAME_SCRIPT = \`…\`;` is a template literal: one backtick in a
    comment inside it ends the template early and the file stops parsing. The
    nested `${…}` interpolations are legitimate and stay — only a BARE backtick
    is the bug.
    """
    bad = []
    for m in re.finditer(r"const ([A-Z_]+(?:_SCRIPT|_CSS)) = `(.*?)\n`;", src, re.S):
        body = m.group(2)
        # Strip legitimate nested template literals before looking for strays.
        stripped = re.sub(r"`[^`]*\$\{[^`]*`", "", body)
        if "`" in stripped:
            bad.append(m.group(1))
    return bad


def _fn(src: str, name: str) -> str:
    """One exported function's body — so a ban means "not in THIS function"
    rather than "not in this file". `el.querySelector('[data-slot]')` is wrong
    inside applyArrangement and perfectly correct inside defaultFlow."""
    i = src.find(f"export function {name}(")
    if i < 0:
        return ""
    j = src.find("\nexport ", i + 1)
    return src[i : j if j > 0 else len(src)]


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
        "const r = iframeRef.current?.getBoundingClientRect();" in canvas,
    )
    # REGRESSION GUARD (fixed 2026-07-18): the menu mapping multiplied d.x by the
    # zoom. But `body.style.zoom` rescales the artifact's LAYOUT, not the iframe
    # element's viewport — a pointer's clientX stays in [0, iframeWidth] at every
    # zoom. The multiply put the menu at ~37% of the offset on a deck (auto-fit
    # zoom ~0.37), landing it up-left of the cursor. The offset is now 1:1.
    _check(
        "the context-menu coord is NOT re-scaled by zoom (clientX is already iframe-box px)",
        "(r?.left ?? 0) + (d.x as number)," in canvas
        and "(d.x as number) * z" not in canvas,
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
        # ADR-466 P8 supersedes the neutral-GRIP ruling for FRAMED blocks: an
        # object wears an accented bounding box (the PowerPoint read). The
        # FLOW selection outline stays neutral — that half of D5 stands.
        "framed selection = the accented box; flow selection stays neutral",
        ".yarnnn-selbox {" in proj
        and "outline: 1px solid rgba(60,58,54,0.5) !important" in proj,
    )
    _check(
        "the EDITING state keeps its accent (typing-into-this is a different fact)",
        "[data-block][contenteditable=\"true\"] {\n  outline: 2px solid #6366f1" in proj,
    )
    _check(
        "transient gesture chrome keeps its accent (drop-line = a prediction)",
        "background: #6366f1;\n  border-radius: 2px; pointer-events: none;" in proj,
    )

    print("\n── D8: the frame is NAMED while it is being measured against ──")
    _check(
        "a frame indicator exists (a measure is a percent OF something, and "
        "that something was invisible)",
        # showFrame's 2nd arg became TEXT (ADR-466 D2), then P10 made the
        # indicator PERSISTENT: it rides the selection (name alone, txt null)
        # and a live resize overlays its numbers ("62% × 40%", joined per axis).
        ".yarnnn-frame {" in proj
        and "showFrame(frame, label.join(' × '));" in proj
        and "function syncFrameContext()" in proj,
    )
    _check(
        "it is shown only DURING the drag (hidden on release, never chrome "
        "that lingers)",
        "hideFrame();" in proj and "function hideFrame()" in proj,
    )
    _check(
        "the label speaks the frame's OWN name, in operator words (never a "
        "class name or a selector — ADR-443 D3)",
        "var slot = frame.getAttribute && frame.getAttribute('data-slot');" in proj
        and "return 'column';" in proj and "return 'slide';" in proj,
    )
    _check(
        "it borrows the slot label's grammar rather than inventing a second "
        "vocabulary for the same idea",
        "rgba(16,185,129" in proj,
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

    print("\n── D9: a layout change never destroys content ──")
    _check(
        "the carry sweeps EVERY target slot, not querySelector's first "
        "(a two-column's `side` used to collapse into `main`)",
        "const targetSlots = Array.from(el.querySelectorAll('[data-slot]'));" in _fn(ops, "applyArrangement")
        and "const slot = el.querySelector('[data-slot]');" not in _fn(ops, "applyArrangement"),
    )
    _check(
        "content is distributed by SOURCE slot name (side → side)",
        "const from = b.closest('[data-slot]')?.getAttribute('data-slot') ?? null;" in ops
        and "byName.get(from)" in ops,
    )
    _check(
        "a slotless target REFUSES rather than deleting (title/section-header/"
        "closing/hero/cta carry no slot — replaceWith used to eat the page)",
        "if (carried.length && !targetSlots.length) return null;" in ops,
    )
    _check(
        "the refusal reaches the member in THEIR words, not applyOp's generic "
        "'select something first'",
        "has no place for this slide's content" in surface,
    )
    _check(
        "placeholders yield only in a slot that actually receives",
        "if (!receiving.has(target)) {" in ops,
    )
    _check(
        "the carry sweeps only TOP-LEVEL blocks (a nested block rides its parent, "
        "never torn out and appended as a sibling)",
        "!b.parentElement?.closest('[data-block]')" in _fn(ops, "applyArrangement"),
    )

    print("\n── Turn-into never flattens a citation ──")
    # REGRESSION GUARD (fixed 2026-07-18): the citation-refusal used
    # querySelector (DESCENDANTS only). A figure/table wears data-ref on its OWN
    # root, so it slipped past and the attribute-carry copied the live pin onto
    # a flattened text shell — a text block dangling a reference. The guard now
    # checks the block's own ref too.
    _check(
        "convertBlock refuses a block wearing data-ref on its OWN root, not just a descendant",
        "block.hasAttribute('data-ref') || block.querySelector('[data-ref]')" in _fn(ops, "convertBlock"),
    )

    print("\n── The add gesture says what it does ──")
    _check(
        "'+ Add' names a choice, not a place ('+ Add here' promised nothing "
        "about what would arrive)",
        "btn.textContent = '+ Add';" in proj,
    )
    _check(
        "adding text to a slot adds TEXT, not a heading nobody asked for "
        "(the registry markup keeps its h2 — this is the GESTURE's business)",
        "const bare = proseFragment.replace(/<h[1-6][^>]*>.*?<\\/h[1-6]>/i, '');" in surface,
    )

    print("\n── D10: the selected block has a keyboard ──")
    _check(
        "the runtime listens for verb keys on the SELECTED block (the menu "
        "shipped shortcut hints and NOTHING listened — pure decoration)",
        "type: 'yarnnn-key-verb'" in proj and "function selectedBlock()" in proj,
    )
    _check(
        "it refuses while the caret has a CLAIM on the key (editing owns its "
        "own keys). ADR-477 re-cut the seam: the guard was 'is anything "
        "editing', which ADR-466 P11 (the box persists through editing) made "
        "routinely true while a block was selected — so every verb key went "
        "dead. The invariant is unchanged; assert it, not the old line.",
        "function caretOwnsKeyIn" in proj and "caretOwnsKeyIn(sel) ? null : sel" in proj,
    )
    _check(
        "Cmd/Ctrl-C over selected TEXT still copies the text (the platform's "
        "job; we only claim the key when nothing is selected)",
        "if (k === 'c' && s && !s.isCollapsed && String(s)) return;" in proj,
    )
    _check(
        "the key verbs dispatch the SAME implementation the menu uses (one "
        "body, two entrances — copyBlock/pasteAfter take an explicit id)",
        "const copyBlock = useCallback(" in surface
        and "const menuCopy = useCallback(() => copyBlock(ctxMenu?.blockId ?? null)" in surface
        and "if (verb === 'copy') return copyBlock(blockId);" in surface,
    )

    print("\n── The runtime is a template string, not a file ──")
    # The backtick trap bit FOUR times in this arc: a literal backtick in a
    # comment inside a `const X_SCRIPT = \`…\`` body terminates the template
    # early (TS1005). tsc catches it, but only after a build; this catches it
    # at gate time, and names the rule so the next author doesn't rediscover it.
    _check(
        "no stray backtick inside any injected script/CSS body",
        not _backtick_in_scripts(proj),
    )

    print("\n── D13: the skin's cited binaries resolve ──")
    _check(
        "a marked skin's url()s are resolved (a workspace path is not a URL a "
        "browser can fetch)",
        "async function resolveStyleUrls" in proj
        and "if (el.hasAttribute('data-skin')) await resolveStyleUrls" in proj,
    )
    _check(
        "it rewrites the TEXT's url()s, never resolves INTO the element "
        "(that was the ADR-456 W3 skin-stomp)",
        "el.textContent = css.replace(CSS_WORKSPACE_URL" in proj,
    )
    _check(
        "a style element is never data-src-html stamped (it would URI-encode "
        "the whole skin, and hand signed URLs to the restore path)",
        "if (el.tagName === 'STYLE') return;\n      el.setAttribute('data-src-html'" in proj,
    )
    _check(
        "a missing cited asset degrades to the font's own fallback",
        "/* a missing cited asset degrades to the fallback — never a broken skin */" in proj,
    )

    print("\n── The honesty checks ──")
    # ADR-471 D-d flipped this check's premise BY THE RULE IT NAMED: the old
    # assertion was "no z-order row until the kernel ships a stacking token,
    # if it ever earns one" — the token landed (--yz, kernel v11), so the
    # honest form inverts: Bring forward/backward may exist ONLY gated on the
    # positioned state and beside an unrenamed flow verb. Flow order and
    # stacking order stay two distinct, honestly-labeled acts.
    _check(
        "z rows are positioned-gated and flow verbs keep their honest names "
        "(Move up = flow order; Bring forward = the ADR-471 z token)",
        "Move up" in menu and "Bring forward" in menu and "target.positioned" in menu,
    )
    _check(
        "the two rows no reference can ship are present",
        "Copy link to block" in menu and "History" in menu,
    )
    _check(
        "the block link carries the block's ADDRESS (what makes it ours)",
        "studio.block=${encodeURIComponent(id)}" in surface,
    )

    # ── Dismissal across the IFRAME BOUNDARY (operator, 2026-07-22) ─────────
    # The menu hung open when clicking the artifact. Its outside-click listener
    # is on the PARENT window, but the canvas is a sandboxed iframe: an
    # in-artifact click fires in the frame's own document and never reaches the
    # parent. The canvas's point message is the signal that DOES arrive, so the
    # surface closes the menu there.
    _check(
        "a click in the CANVAS dismisses the menu (the iframe blind spot)",
        "setCtxMenu(null)" in surface
        and surface.count("setCtxMenu(null)") >= 2,  # onPoint AND onPointClear
    )
    _check(
        "the menu also dismisses on a second right-click / scroll / resize",
        "'contextmenu', close" in menu
        and "'scroll', close" in menu
        and "'resize', close" in menu,
    )

    print()
    ok = all(c for _, c in _results)
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
