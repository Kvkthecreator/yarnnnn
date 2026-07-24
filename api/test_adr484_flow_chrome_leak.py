#!/usr/bin/env python3
"""Gate: ADR-484 — the cue that boxed prose, and leaked into the substrate.

Two defects from one class, `yarnnn-pointed`:

  D1  ADR-482 D2 applied the neutral selection cue to EVERY block on flow. The
      asymmetry it fixed was real (right-click outlined, left-click did not);
      the direction was wrong for prose. Clicking into a paragraph places a
      caret — the caret IS the feedback — and a rule drawn around the paragraph
      re-asserts the enclosure ADR-480 dissolved. FLOW_POINTER_CSS had already
      drawn the correct line for the HOVER cue (object kinds only); D2 applied
      the SELECTION cue without honouring it. Now object-only.

  D2  the class was being SERIALIZED INTO THE ARTIFACT. `readSourceInner` — the
      one serializer both commit paths use — restored citation islands and
      stripped no runtime chrome, so whichever block was selected at commit time
      carried its cue into the saved file. Worse than a live-session artifact:
      it renders for every future reader and is attributed as the member's own
      authored content. Found in prod on three artifacts (5 occurrences), one of
      them the operator's real `prd-for-yarnnn` document.

The generalization (ADR-484 §3), the substrate-side twin of ADR-482 §10:

    Runtime chrome painted onto the live DOM must be STRIPPED AT THE
    SERIALIZATION BOUNDARY, not merely styled correctly. A cue invisible in one
    mode is still PRESENT in the DOM, and any path that reads the DOM to persist
    it will write the cue into the artifact.

Both are validated EXECUTING, not grepped:
`web/scripts/gates/adr484_flow_chrome_leak.mjs` runs the real click branch and
the real `readSourceInner` body (14/14) with a FALSIFIER PER DEFECT. This
committed gate is the static regression guard.

Run: python3 test_adr484_flow_chrome_leak.py   (check()-style, NOT pytest)
"""

import subprocess
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    web = root / "web"
    proj = (web / "components/workspace/viewers/projection.ts").read_text()

    # ── D1 — the cue is object-scoped on flow ─────────────────────────────
    _check(
        "D1 the flow cue is guarded on the block kind, never unconditional",
        "if (cur && TEXT_KINDS.indexOf(cur.getAttribute('data-block')) === -1) {" in proj,
    )
    _check(
        "D1 ADR-482 D2's unconditional apply is GONE from the flow branch",
        "if (cur) cur.classList.add('yarnnn-pointed');" not in proj,
    )
    # The CSS boundary the JS now honours must still exist — if the hover rule's
    # object scoping were widened to prose, D1's guard would be inconsistent
    # with the sheet it was aligned to.
    flow_css = proj[proj.index("const FLOW_POINTER_CSS") : proj.index("const POINTER_CSS")]
    _check(
        "D1 the flow sheet still scopes the HOVER cue to object kinds only",
        '[data-block="figure"]:hover' in flow_css
        and '[data-block="prose"]:hover' not in flow_css,
    )
    _check(
        "D1 paged is untouched — its per-block outline is meaningful there",
        "const POINTER_CSS" in proj and '[data-block]:hover' in proj,
    )

    # ── D2 — the serializer strips runtime chrome ─────────────────────────
    rsi = proj.index("function readSourceInner(el)")
    rsi_body = proj[rsi : proj.index("\n  }", rsi)]
    # The strip is now ENUMERATED over a list rather than hard-coded to one
    # class (2026-07-24): `yarnnn-grouped` (the group's transient cue) is the
    # second member of the family, and ADR-484's defect was precisely that a
    # runtime class had no single place that knew it must be stripped. Assert
    # the list contains every cue the runtime paints, so adding a third without
    # adding it here turns this red.
    _check(
        "D2 readSourceInner strips EVERY runtime chrome class",
        "CHROME_CLASSES = ['yarnnn-pointed', 'yarnnn-grouped']" in rsi_body
        and "querySelectorAll('.' + CHROME_CLASSES[c])" in rsi_body,
    )
    _check(
        "D2 the strip list covers every cue the runtime actually paints",
        all(
            f"CHROME_CLASSES = ['yarnnn-pointed', 'yarnnn-grouped']" in rsi_body
            for cue in ("yarnnn-pointed", "yarnnn-grouped")
            if f"classList.add('{cue}')" in proj
        ),
    )
    _check(
        "D2 an emptied class attribute is dropped, never left as class=\"\"",
        "removeAttribute('class')" in rsi_body,
    )
    # The strip must live in the SHARED serializer, so neither commit path can
    # leak. Both flowCommit and commit() read through this one function.
    _check(
        "D2 both commit paths route through the one stripped serializer",
        "newInner: readSourceInner(root)" in proj and "readSourceInner(editingEl)" in proj,
    )

    # ── The repair is attributed, never a raw UPDATE ──────────────────────
    repair = root / "api/scripts/oneshot/adr484_strip_leaked_chrome_class.py"
    _check("the data repair is committed", repair.exists())
    if repair.exists():
        rsrc = repair.read_text()
        _check(
            "the repair writes through write_revision (ADR-209's one door)",
            "write_revision(" in rsrc and "system:adr484-chrome-strip" in rsrc,
        )
        _check(
            "the repair strips TOKEN-WISE (class=\"a X b\" must not fuse to \"ab\")",
            "split()" in rsrc and "yarnnn-pointed" in rsrc,
        )
        # Execute the repair's own strip against the real prod shapes.
        sys.path.insert(0, str(root / "api"))
        try:
            from scripts.oneshot.adr484_strip_leaked_chrome_class import strip_chrome

            cases = {
                '<h2 class="yarnnn-pointed">x</h2>': "<h2>x</h2>",
                '<p class="lede yarnnn-pointed">x</p>': '<p class="lede">x</p>',
                '<div class="a yarnnn-pointed b">x</div>': '<div class="a b">x</div>',
                '<div class="lede">x</div>': '<div class="lede">x</div>',
            }
            _check(
                "the repair's strip is correct on every real class shape",
                all(strip_chrome(k) == v for k, v in cases.items()),
            )
        except Exception as e:  # noqa: BLE001
            _check(f"the repair's strip is importable ({e})", False)

    # ── The EXECUTING gate is the load-bearing one ────────────────────────
    mjs = web / "scripts/gates/adr484_flow_chrome_leak.mjs"
    _check("executing gate present", mjs.exists())
    if mjs.exists():
        proc = subprocess.run(["node", str(mjs)], cwd=str(root), capture_output=True, text=True)
        for line in proc.stdout.strip().splitlines():
            print(f"    {line}")
        _check("executing gate passes (real bodies + falsifiers)", proc.returncode == 0)

    passed = sum(1 for _, ok in _results if ok)
    print(f"\nADR-484: {passed}/{len(_results)} passed")
    return passed == len(_results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
