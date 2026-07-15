"""Regression gate — Studio Enter-split / Backspace-merge (optimistic).

The audit's constrained tranche (F6): split/merge fight revision-is-the-atom —
each is a structural change that would normally reload the canvas (a stutter on
every Enter/Backspace at a boundary). The operator chose the OPTIMISTIC path:
mutate the DOM in-frame FIRST (caret stays put), then land the revision in the
background WITHOUT a reload — the same writeAndAdvance(reload:false) spine as
invisible-save.

  - Enter MID-block → SPLIT: the block keeps the before-half, a fresh block
    (newId) gets the after-half. Optimistic in-frame; caret into the new block.
    A caret inside a citation island refuses (splitHalves → null → native).
    A heading's tail becomes prose.
  - Backspace at block START → MERGE into the previous text block; caret at the
    join. Refuses across an island.
  - The runtime generates newId (checked vs the live DOM) so the source op
    (splitBlock) matches the shown DOM exactly.
  - Citation edge: if a half carries data-ref, the surface RE-PROJECTS
    (reload:true) so the citation resolves — plain-text splits stay optimistic.

Static/structural checks (no DB, no LLM):

Run:  cd api && python3 test_studio_split_merge.py
Exit code is authoritative (0 = pass).
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def _no_backticks_in_scripts(src: str) -> bool:
    in_script = False
    for line in src.split("\n"):
        s = line.strip()
        if s.endswith("_SCRIPT = `"):
            in_script = True
            continue
        if in_script and s.startswith("`;"):
            in_script = False
            continue
        if in_script and "`" in line:
            return False
    return True


def run() -> bool:
    web = Path(__file__).resolve().parent.parent / "web"
    ops = (web / "components/studio/artifactOps.ts").read_text()
    proj = (web / "components/workspace/viewers/projection.ts").read_text()
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()

    # ── 1. the source ops ────────────────────────────────────────────────
    _check(
        "splitBlock(html, blockId, newId, beforeInner, afterInner) exists",
        "export function splitBlock(" in ops and "afterInner: string," in ops,
    )
    _check(
        "splitBlock: the block keeps before, a tail block (newId) gets after",
        "block.innerHTML = beforeInner;" in ops
        and "tail.setAttribute('data-block-id', newId);" in ops
        and "block.insertAdjacentElement('afterend', tail);" in ops,
    )
    _check(
        "splitBlock: a heading's tail becomes prose; the tail never carries data-ref",
        "tail = doc.createElement('p');" in ops
        and "tail.removeAttribute('data-ref');" in ops,
    )
    _check(
        "mergeBlock(html, blockId, prevBlockId, mergedInner) exists + removes the block",
        "export function mergeBlock(" in ops
        and "prev.innerHTML = mergedInner;" in ops
        and "block.remove();" in ops,
    )
    _check(
        "mergeBlock refuses across parents (same parent only)",
        "block.parentElement !== prev.parentElement) return null;" in ops,
    )

    # ── 2. the runtime (optimistic in-frame) ─────────────────────────────
    _check(
        "Enter mid-block splits (splitHalves) instead of falling to native",
        "var halves = splitHalves();" in proj
        and "type: 'yarnnn-split-block'" in proj,
    )
    _check(
        "splitHalves refuses inside a citation island",
        "function splitHalves()" in proj
        and "if (caretInIsland()) return null;" in proj,
    )
    _check(
        "the split is OPTIMISTIC: DOM mutated in-frame + caret into the new block",
        "editingEl.innerHTML = halves.before;" in proj
        and "tail.innerHTML = halves.after;" in proj
        and "enter(newId);" in proj,
    )
    _check(
        "the runtime generates newId checked against the live DOM",
        "function freshId()" in proj
        and "document.querySelector('[data-block-id=\"' + id + '\"]')" in proj,
    )
    _check(
        "Backspace at block start merges into the previous text block",
        "if (e.key !== 'Backspace' || !editingEl) return;" in proj
        and "if (!caretAtBlockStart() || caretInIsland()) return;" in proj
        and "type: 'yarnnn-merge-block'" in proj,
    )
    _check(
        "merge is optimistic: prev gets both inners, this block removed, caret at join",
        "prev.innerHTML = prevInner + thisInner;" in proj
        and "editingEl.remove()" in proj,
    )
    _check(
        "no literal backtick inside any *_SCRIPT body",
        _no_backticks_in_scripts(proj) and proj.count("`") % 2 == 0,
    )

    # ── 3. canvas + surface wiring (reload:false = optimistic) ───────────
    _check(
        "the canvas forwards split + merge",
        "d.type === 'yarnnn-split-block'" in canvas
        and "onSplitBlock?.(" in canvas
        and "d.type === 'yarnnn-merge-block'" in canvas
        and "onMergeBlock?.(" in canvas,
    )
    _check(
        "the surface lands split/merge WITHOUT a reload (writeAndAdvance, false-by-default)",
        "const handleSplitBlock = useCallback(" in surface
        and "splitBlock(file.content, blockId, newId, beforeInner, afterInner)" in surface
        and "const handleMergeBlock = useCallback(" in surface,
    )
    _check(
        "a citation in a half forces a re-project (reload:true) so it resolves",
        "const hasCitation = /data-ref=/.test(beforeInner)" in surface
        and bool(re.search(r"`Studio: split block`,\s*\n\s*hasCitation", surface)),
    )
    _check(
        "both handlers are wired into the canvas mount",
        "onSplitBlock={handleSplitBlock}" in surface
        and "onMergeBlock={handleMergeBlock}" in surface,
    )
    # ── The stale-half race (the op-carrying exits must be SILENT) ──────────
    # exit() commits the block it detaches from. On split/merge the DOM is
    # already mutated when we exit, so that commit describes a HALF of the
    # result and races the op message — both anchored on the same head, so it
    # either clobbers the op (data loss) or spuriously 409s it (error flash).
    _check(
        "exit() supports a silent mode (detach without emitting a commit)",
        "function exit(notify, silent) {" in proj and "if (!silent) {" in proj,
    )
    _check(
        "the SPLIT detaches silently — the split op carries both halves",
        "exit(false, true);\n    enter(newId);" in proj,
    )
    _check(
        "the MERGE detaches silently — the merge op carries the joined inner",
        "exit(false, true);\n    prev.innerHTML = prevInner + thisInner;" in proj,
    )
    _check(
        "arrow traversal still COMMITS on exit (no op of its own carries the text)",
        "exit(false); // commit silently (parent keeps editingBlockId in sync below)" in proj,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
