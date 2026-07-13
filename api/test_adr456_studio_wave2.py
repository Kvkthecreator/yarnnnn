"""ADR-456 Wave-2 regression gate — the Notion core: inline format bar,
slash-insert, turn-into.

Static/structural checks (no DB, no LLM — Wave 2 is FE-only; the backend
registries and the posture are untouched):
  1. The format bar: in-frame injected chrome (body-appended, .yarnnn-fmt,
     never inside a block); B/I via execCommand with styleWithCSS off; code =
     a range wrap; link = the bar's input with the blur GUARD (focus in the
     bar must not end the edit session); the pointer runtime ignores the
     bar's clicks; b/i normalize to strong/em at the write door.
  2. Slash-insert: '/' only in an EMPTY context (a literal '/' in flowing
     text is untouched); the runtime commits + exits BEFORE the palette opens
     (no uncommitted-buffer race); the parent palette excludes the
     picker-backed kinds; an empty block CONVERTS in place, a non-empty one
     inserts after.
  3. Turn-into: convertBlock preserves the block id + its data-* tokens,
     refuses blocks containing citations (a data-ref never flattens), no-ops
     same-kind; the Design tab's block scope carries the row, text kinds only.

Run:  cd api && python3 test_adr456_studio_wave2.py
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
    ops = (web / "components/studio/artifactOps.ts").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    design = (web / "components/studio/StudioDesignTab.tsx").read_text()
    palette = (web / "components/studio/StudioSlashPalette.tsx").read_text()

    # ── 1. The inline format bar ─────────────────────────────────────────
    _check("format bar is body-appended injected chrome (never inside a block)",
           "document.body.appendChild(fmtBar)" in proj
           and ".yarnnn-fmt" in proj)
    _check("B/I ride execCommand with styleWithCSS off (tags, not styles)",
           "execCommand('bold')" in proj and "execCommand('italic')" in proj
           and "'styleWithCSS', false, 'false'" in proj)
    _check("code is a range wrap (surround, extract+insert fallback)",
           "wrapSelection('code')" in proj and "surroundContents" in proj
           and "extractContents()" in proj)
    _check("link = the bar's input; createLink on the SAVED range",
           "execCommand('createLink', false, url)" in proj
           and "savedRange" in proj)
    _check("the blur GUARD: focus in the bar keeps the edit session alive",
           "closest('.yarnnn-fmt')) return; // bar owns focus" in proj
           and "__yarnnnBlur" in proj)
    _check("the once-blur is gone (guarded named handler, removed on exit)",
           "{ once: true }" not in proj)
    _check("bar buttons keep the selection (mousedown preventDefault)",
           "b.addEventListener('mousedown', function (e) { e.preventDefault(); })" in proj)
    _check("pointer runtime ignores the bar's clicks",
           "closest('.yarnnn-fmt')) return;" in proj)
    _check("b/i normalize to strong/em at the write door",
           "querySelectorAll('b, i')" in ops
           and "el.tagName === 'B' ? 'strong' : 'em'" in ops)

    # ── 2. Slash-insert ──────────────────────────────────────────────────
    _check("'/' fires only in an EMPTY context (literal slashes still type)",
           "slashContextEmpty" in proj
           and "if (!slashContextEmpty()) return;" in proj)
    _check("commit-then-palette: the runtime exits (commits) BEFORE opening",
           "exit(true); // commits current text" in proj
           and "yarnnn-slash-open" in proj)
    _check("canvas forwards yarnnn-slash-open with the block rect",
           "'yarnnn-slash-open'" in canvas and "onSlashOpen?." in canvas)
    _check("palette excludes the picker-backed kinds (they stay in Insert)",
           "SLASH_EXCLUDED" in palette
           and "'figure'" in palette and "'gallery'" in palette)
    _check("empty block CONVERTS in place; non-empty inserts after",
           "s.empty" in surface
           and "convertBlock(html, s.blockId, kind, fragment)" in surface
           and "insertBlock(html, fragment, { blockId: s.blockId })" in surface)
    _check("palette keyboard: Enter picks, Esc closes, arrows move",
           "'Enter'" in palette and "'Escape'" in palette
           and "'ArrowDown'" in palette)

    # ── 3. Turn-into ─────────────────────────────────────────────────────
    _check("convertBlock preserves the block id",
           "export function convertBlock" in ops
           and "shell.setAttribute('data-block-id', blockId)" in ops)
    _check("convertBlock carries the tokens across (data-* survive)",
           "attr.name.startsWith('data-')" in ops
           and "attr.name !== 'data-block-id'" in ops)
    _check("convertBlock refuses citations + no-ops same-kind",
           "block.querySelector('[data-ref]')" in ops
           and "block.getAttribute('data-block') === kind" in ops)
    _check("Design tab: Turn into, text kinds only",
           "TURN_INTO_KINDS" in design
           and "'prose', 'callout', 'quote', 'checklist', 'toggle'" in design
           and "onTurnInto" in design)
    _check("surface routes turn-into through the one door (applyOp)",
           "handleTurnInto" in surface
           and "Studio: turn block into" in surface)

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
